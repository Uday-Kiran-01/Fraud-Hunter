# agents/data_analyst.py
import pandas as pd

class DataAnalyst:
    def __init__(self, output_dir: str = None, seed: int = 42):
        self.output_dir = output_dir
        self.seed = seed

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Simple cleaning step for clickstream dataset."""
        df = df.copy()

        # Convert datetime columns
        if "attributed_time" in df.columns:
            df["attributed_time"] = pd.to_datetime(df["attributed_time"], errors="coerce")

        if "click_time" in df.columns:
            df["click_time"] = pd.to_datetime(df["click_time"], errors="coerce")
            df["hour"] = df["click_time"].dt.hour
            df["minute"] = df["click_time"].dt.minute
            df["dayofweek"] = df["click_time"].dt.dayofweek

        # Drop duplicates
        df = df.drop_duplicates()

        # Fill nulls in categorical cols
        df = df.fillna({"device": -1, "os": -1, "channel": -1})

        return df

    def run(self, df: pd.DataFrame) -> dict:
        """Quick EDA summary (row count, nulls, dtypes)."""
        return {
            "rows": len(df),
            "columns": list(df.columns),
            "null_counts": df.isnull().sum().to_dict(),
            "dtypes": df.dtypes.astype(str).to_dict(),
        }

    # Stub methods for streaming (so main.py doesn’t break)
    def init_stream(self):
        return {"rows": 0}

    def update_stream(self, chunk, acc):
        acc["rows"] += len(chunk)

    def finalize_stream(self, acc):
        return acc
