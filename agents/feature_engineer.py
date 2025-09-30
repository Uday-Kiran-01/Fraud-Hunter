# agents/feature_engineer.py
from tools import features
import pandas as pd

class FeatureEngineer:
    def __init__(self, output_dir: str = "outputs", seed: int = 42):
        self.output_dir = output_dir
        self.seed = seed

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        return features.add_features(df, output_dir=self.output_dir)
