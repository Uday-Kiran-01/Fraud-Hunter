# agents/reporter.py
from tools import summarize
import os
import pandas as pd

class Reporter:
    def __init__(self, output_dir: str = "outputs", seed: int = 42):
        self.output_dir = output_dir
        self.seed = seed

    def run(self, raw_df: pd.DataFrame, fraud_flags, eda_summary: dict, meta=None, notes: str = "") -> str:
        path = os.path.join(self.output_dir, "fraud_report.md")
        summarize.write_report(path, raw_df, fraud_flags, eda_summary, meta or {}, notes=notes)
        return path

    def run_streaming(self, flagged_records, eda_summary: dict, aggregate_stats: dict, meta=None, notes: str = "") -> str:
        path = os.path.join(self.output_dir, "fraud_report.md")
        summarize.write_streaming_report(path, flagged_records, eda_summary, aggregate_stats, meta or {}, notes=notes)
        return path
