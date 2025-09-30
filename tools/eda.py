# tools/eda.py
import os
import pandas as pd
from collections import Counter

def basic_eda(df: pd.DataFrame, output_dir: str = "outputs") -> dict:
    os.makedirs(output_dir, exist_ok=True)
    summary = {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "null_counts": df.isna().sum().to_dict(),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()}
    }
    for col in ["ip", "app", "device", "os", "channel"]:
        if col in df.columns:
            summary[f"top_{col}"] = df[col].value_counts().head(10).to_dict()

    if "click_time" in df.columns:
        s = pd.to_datetime(df["click_time"], errors="coerce")
        summary["time_coverage"] = {
            "min": str(s.min()) if s.notna().any() else None,
            "max": str(s.max()) if s.notna().any() else None
        }
    return summary

def init_accumulator() -> dict:
    return {
        "rows": 0,
        "null_counts": Counter(),
        "dtypes": {},
        "top_counts": {k: Counter() for k in ["ip","app","device","os","channel"]},
        "time_min": None,
        "time_max": None,
        "columns_seen": set()
    }

def update_accumulator(acc: dict, chunk: pd.DataFrame):
    acc["rows"] += len(chunk)
    acc["columns_seen"].update(chunk.columns.tolist())
    acc["null_counts"].update(chunk.isna().sum().to_dict())
    for c, t in chunk.dtypes.items():
        acc["dtypes"].setdefault(c, str(t))
    for col in acc["top_counts"].keys():
        if col in chunk.columns:
            acc["top_counts"][col].update(chunk[col].head(200_000).astype(str).tolist())
    if "click_time" in chunk.columns:
        s = pd.to_datetime(chunk["click_time"], errors="coerce").dropna()
        if not s.empty:
            mn, mx = s.min(), s.max()
            acc["time_min"] = mn if acc["time_min"] is None else min(acc["time_min"], mn)
            acc["time_max"] = mx if acc["time_max"] is None else max(acc["time_max"], mx)

def finalize_accumulator(acc: dict, output_dir: str = "outputs") -> dict:
    os.makedirs(output_dir, exist_ok=True)
    top = {f"top_{col}": dict(ctr.most_common(10)) for col, ctr in acc["top_counts"].items()}
    return {
        "rows": int(acc["rows"]),
        "columns": sorted(list(acc["columns_seen"])),
        "null_counts": dict(acc["null_counts"]),
        "dtypes": acc["dtypes"],
        **top,
        "time_coverage": {
            "min": str(acc["time_min"]) if acc["time_min"] is not None else None,
            "max": str(acc["time_max"]) if acc["time_max"] is not None else None,
        }
    }
