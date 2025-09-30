# main.py
import argparse
import os
import sys
import time
from pathlib import Path
import pandas as pd

from agents.data_analyst import DataAnalyst
from agents.feature_engineer import FeatureEngineer
from agents.fraud_detector import FraudDetector
from agents.reporter import Reporter
from tools import assist  # for --ask

DEFAULT_DATA_PATH = os.path.join("data", "train_sample.csv")
DEFAULT_OUTPUT_DIR = "outputs"

def parse_args():
    p = argparse.ArgumentParser(
        description="FraudHunterAI (Clean → EDA → Features → Detect → Report)"
    )
    p.add_argument("--data", type=str, default=DEFAULT_DATA_PATH,
                   help="Path to CSV (default: data/train_sample.csv)")
    p.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR,
                   help="Directory for artifacts (default: outputs/)")
    p.add_argument("--nrows", type=int, default=100_000,
                   help="Rows to load for quick run. Use 0 to stream full file.")
    p.add_argument("--chunksize", type=int, default=250_000,
                   help="Chunk size when --nrows=0 (streaming mode)")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    p.add_argument("--mode", type=str, default="hybrid",
                   choices=["rules", "ollama", "hybrid", "lgbm"],
                   help="Detector mode: rules | ollama | hybrid | lgbm")
    p.add_argument("--ask", type=str, default="",
                   help="Ask Ollama about the dataset (e.g., --ask 'what patterns look suspicious?').")
    return p.parse_args()

def safe_makedirs(path: str):
    os.makedirs(path, exist_ok=True)

def read_fast_sample(data_path: str, nrows: int, usecols=None) -> pd.DataFrame:
    print(f"📥 Reading sample: nrows={nrows:,} from {data_path}")
    df = pd.read_csv(
        data_path,
        nrows=nrows,
        low_memory=True,
        on_bad_lines="skip",
        encoding_errors="ignore",
        usecols=usecols
    )
    return df

def stream_and_process(data_path: str, chunksize: int,
                       analyst: DataAnalyst,
                       engineer: FeatureEngineer,
                       detector: FraudDetector):
    from pathlib import Path
    print(f"🌊 Streaming full dataset with chunksize={chunksize:,} ...")
    acc = analyst.init_stream()
    flagged_records = []
    total_rows = 0
    flagged_path = Path(detector.output_dir) / "flagged_stream.csv"
    if flagged_path.exists():
        try:
            flagged_path.unlink()
        except Exception:
            pass

    reader = pd.read_csv(
        data_path,
        chunksize=chunksize,
        low_memory=True,
        on_bad_lines="skip",
        encoding_errors="ignore"
    )

    for i, chunk in enumerate(reader):
        print(f"  • Processing chunk {i+1} (+{len(chunk):,} rows)")

        # clean BEFORE counting so totals match cleaned data
        if hasattr(analyst, "clean_data"):
            try:
                chunk = analyst.clean_data(chunk)
            except Exception as e:
                print(f"   ⚠️ clean_data() failed on chunk {i+1}: {e}. Continuing with raw chunk.")

        total_rows += len(chunk)

        analyst.update_stream(chunk, acc)
        df_feat = engineer.run(chunk)

        flags = detector.run(df_feat)
        if hasattr(flags, "astype"):
            mask = flags.astype(bool)
            idxs = df_feat.index[mask]
            flagged_records.extend([(i, int(j)) for j in idxs])

            flagged_chunk = df_feat.loc[mask].copy()
            if not flagged_chunk.empty:
                write_header = (i == 0)
                flagged_chunk.to_csv(flagged_path, mode="a", header=write_header, index=False)

    eda_summary = analyst.finalize_stream(acc)
    agg_stats = {
        "total_rows": total_rows,
        "flagged_count": len(flagged_records),
        "flag_rate": (len(flagged_records) / max(total_rows, 1)) if total_rows else 0.0,
    }
    return eda_summary, flagged_records, agg_stats

def main():
    args = parse_args()
    start = time.time()

    safe_makedirs(args.output)

    analyst = DataAnalyst(output_dir=args.output, seed=args.seed)
    engineer = FeatureEngineer(output_dir=args.output, seed=args.seed)
    detector = FraudDetector(
        output_dir=args.output,
        seed=args.seed,
        mode=args.mode,
        model_path=os.path.join(args.output, "lgbm_model.pkl")
    )
    reporter = Reporter(output_dir=args.output, seed=args.seed)

    print("🚀 FraudHunterAI starting")
    print(f"   Data:     {os.path.abspath(args.data)}")
    print(f"   Outputs:  {os.path.abspath(args.output)}")
    print(f"   Mode:     {'STREAM (full file)' if args.nrows == 0 else f'SAMPLE ({args.nrows:,} rows)'}")
    print(f"   Detector: {args.mode}")

    if not os.path.exists(args.data):
        print(f"❌ Data file not found: {args.data}")
        sys.exit(1)

    if args.nrows > 0:
        # ------------------- Sample mode -------------------
        df = read_fast_sample(args.data, args.nrows)

        # Optional cleaning (whole sample)
        if hasattr(analyst, "clean_data"):
            try:
                print("🧽 Cleaning data (sample)...")
                df = analyst.clean_data(df)
            except Exception as e:
                print(f"⚠️ clean_data() failed: {e}. Proceeding without cleaning.")

        # Optional Q&A with Ollama about the (cleaned) dataset
        if args.ask:
            out_path = Path(args.output) / "ollama_insight.md"
            try:
                text = assist.describe_dataset(df, user_question=args.ask, sample_size=200)
                out_path.write_text(text, encoding="utf-8")
                print(f"💬 Ollama insight saved to: {out_path}")
            except Exception as e:
                print(f"⚠️ Ollama insight failed: {e}")

        print("🔎 Running Data Analyst (sample)...")
        eda_summary = analyst.run(df)

        print("🧬 Running Feature Engineer (sample)...")
        df_features = engineer.run(df)

        print("🚨 Running Fraud Detector (sample)...")
        fraud_flags = detector.run(df_features)

        # --- Save flagged rows (robust to misalignment) ---
        flags = fraud_flags
        if not isinstance(flags, pd.Series):
            flags = pd.Series(flags, index=df_features.index)
        flags = flags.reindex(df_features.index, fill_value=False).astype(bool)

        flagged_df = df_features.loc[flags].copy()
        flagged_path = Path(args.output) / "flagged_sample.csv"
        flagged_df.to_csv(flagged_path, index=False)
        print(f"💾 Saved flagged rows to: {flagged_path}")

        # --- Mini-evaluation (if label exists) ---
        eval_txt = ""
        if "is_attributed" in df.columns:
            y = (df["is_attributed"] == 1)
            tp = int((flags & y).sum())
            fp = int((flags & ~y).sum())
            fn = int((~flags & y).sum())
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            eval_txt = f"tp={tp}, fp= {fp}, fn={fn}, precision={precision:.4f}, recall={recall:.4f}"
            print(f"🧪 Eval: {eval_txt}")

        print("📊 Generating Report (sample)...")
        notes = getattr(detector, "last_llm_notes", "")
        train_metrics = getattr(detector, "last_train_metrics", None)
        meta = {"mode": "sample", "nrows": args.nrows, "detector": args.mode, "eval": eval_txt}
        if train_metrics:
            meta["lgbm_valid"] = train_metrics

        report_path = reporter.run(
            raw_df=df,
            fraud_flags=fraud_flags,
            eda_summary=eda_summary,
            meta=meta,
            notes=notes
        )
        print(f"✅ Done. Report: {report_path}")

    else:
        # ------------------- Streaming full file -------------------
        eda_summary, flagged_records, agg_stats = stream_and_process(
            data_path=args.data,
            chunksize=args.chunksize,
            analyst=analyst,
            engineer=engineer,
            detector=detector
        )

        print("📊 Generating Report (streaming)...")
        notes = getattr(detector, "last_llm_notes", "")
        report_path = reporter.run_streaming(
            flagged_records=flagged_records,
            eda_summary=eda_summary,
            aggregate_stats=agg_stats,
            meta={"mode": "stream", "chunksize": args.chunksize, "detector": args.mode},
            notes=notes
        )
        print(f"✅ Done. Report: {report_path}")

    elapsed = time.time() - start
    print(f"⏱️ Elapsed: {elapsed:.2f}s")

if __name__ == "__main__":
    main()
