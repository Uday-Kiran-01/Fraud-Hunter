# agents/fraud_detector.py
from tools import predict
from tools import model as mdl
import pandas as pd
import os

class FraudDetector:
    def __init__(self, output_dir: str = "outputs", seed: int = 42, mode: str = "hybrid", model_path: str = "outputs/lgbm_model.pkl"):
        """
        mode: "rules" | "ollama" | "hybrid" | "lgbm"
        """
        self.output_dir = output_dir
        self.seed = seed
        self.mode = mode
        self.model_path = model_path
        self.last_llm_notes = ""
        self.last_train_metrics = None

    def run(self, df_features: pd.DataFrame) -> pd.Series:
        if self.mode == "lgbm":
            # Ensure label exists for training (in this dataset it does)
            if not os.path.exists(self.model_path):
                print("📚 Training LightGBM model (no model found)...")
                if "is_attributed" not in df_features.columns:
                    raise ValueError("is_attributed label not found in dataframe for LGBM training.")
                self.last_train_metrics, path = mdl.train_lgbm(
                    df_features, label_col="is_attributed", model_path=self.model_path
                )
                print(f"💾 Model saved: {path} | Metrics: {self.last_train_metrics}")
            print("⚙️ Predicting with LightGBM...")
            return mdl.predict_lgbm(df_features, self.model_path).astype(bool)

        if self.mode == "rules":
            print("⚡ Using adaptive rules...")
            flags = predict.simple_rules(df_features)
            self.last_llm_notes = ""
            return flags.reindex(df_features.index, fill_value=False).astype(bool)

        if self.mode == "ollama":
            print("🤖 Using Ollama (Mistral) on a sample...")
            res = predict.ollama_detect(df_features, sample_size=150)
            self.last_llm_notes = res.get("notes", "")
            full = pd.Series(False, index=df_features.index)
            full.loc[res["series"].index] = res["series"].astype(bool)
            return full

        # default: hybrid
        print("🧠 Using hybrid (rules → LLM refinement)...")
        res = predict.hybrid_detect(df_features, sample_size=100)
        self.last_llm_notes = res.get("notes", "")
        return res["flags"].reindex(df_features.index, fill_value=False).astype(bool)
