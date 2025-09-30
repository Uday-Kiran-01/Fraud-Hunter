# tools/summarize.py
import json
from typing import Any, Dict, List

def _count_flags(fraud_flags) -> int:
    if hasattr(fraud_flags, "sum"):
        try:
            return int(fraud_flags.sum())
        except Exception:
            pass
    try:
        return sum(bool(x) for x in fraud_flags)
    except Exception:
        return 0

def write_report(path: str,
                 raw_df,
                 fraud_flags,
                 eda_summary: Dict[str, Any],
                 meta: Dict[str, Any] | None = None,
                 notes: str = ""):
    total = len(raw_df) if hasattr(raw_df, "__len__") else 0
    flagged = _count_flags(fraud_flags)
    rate = (flagged / max(total, 1)) if total else 0.0

    with open(path, "w", encoding="utf-8") as f:
        f.write("# Daily Fraud Report\n\n")
        f.write(f"**Rows processed**: {total:,}\n\n")
        f.write(f"**Suspected fraud**: {flagged:,}  (_flag rate: {rate:.2%}_)\n\n")

        if notes:
            f.write("## Model Notes\n")
            f.write(notes.strip() + "\n\n")

        f.write("## EDA Snapshot\n```json\n")
        f.write(json.dumps(eda_summary, indent=2, ensure_ascii=False))
        f.write("\n```\n\n")

        if meta:
            f.write("## Meta\n```json\n")
            f.write(json.dumps(meta, indent=2, ensure_ascii=False))
            f.write("\n```\n")

def write_streaming_report(path: str,
                           flagged_records: List[Any],
                           eda_summary: Dict[str, Any],
                           aggregate_stats: Dict[str, Any],
                           meta: Dict[str, Any] | None = None,
                           notes: str = ""):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Daily Fraud Report (Streaming)\n\n")
        f.write(f"**Total rows**: {aggregate_stats.get('total_rows', 0):,}\n\n")
        flg = aggregate_stats.get("flagged_count", 0)
        rate = aggregate_stats.get("flag_rate", 0.0)
        f.write(f"**Suspected fraud**: {flg:,}  (_flag rate: {rate:.2%}_)\n\n")

        if notes:
            f.write("## Model Notes\n")
            f.write(notes.strip() + "\n\n")

        f.write("## EDA Snapshot\n```json\n")
        f.write(json.dumps(eda_summary, indent=2, ensure_ascii=False))
        f.write("\n```\n\n")

        if meta:
            f.write("## Meta\n```json\n")
            f.write(json.dumps(meta, indent=2, ensure_ascii=False))
            f.write("\n```\n")
