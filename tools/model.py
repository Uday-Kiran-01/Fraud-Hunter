# tools/model.py
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import train_test_split
import lightgbm as lgb

FEATURES_DEFAULT = [
    "ip","app","device","os","channel",
    "ip_freq","app_freq","ip_app_freq","device_freq","os_freq","channel_freq",
    "hour","minute","dayofweek","night_click",
    "ip_night_density","ip_hour_freq","ip_channel_freq",
]

def _select_features(df: pd.DataFrame, features=None):
    feats = features or FEATURES_DEFAULT
    cols = [c for c in feats if c in df.columns]
    X = df[cols].fillna(0)
    return X, cols

def train_lgbm(df: pd.DataFrame, label_col: str = "is_attributed", model_path: str = "outputs/lgbm_model.pkl",
               test_size: float = 0.2, random_state: int = 42, features=None):
    if label_col not in df.columns:
        raise ValueError(f"Label column '{label_col}' not found.")
    y = df[label_col].astype(int).values
    X, used_cols = _select_features(df, features)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y if y.sum() > 0 else None
    )

    train_ds = lgb.Dataset(X_train, label=y_train, feature_name=list(X.columns))
    val_ds   = lgb.Dataset(X_val, label=y_val, reference=train_ds)

    params = dict(
        objective="binary",
        metric=["auc"],
        learning_rate=0.1,
        num_leaves=64,
        max_depth=-1,
        min_data_in_leaf=100,
        feature_fraction=0.8,
        bagging_fraction=0.8,
        bagging_freq=1,
        verbose=-1,
    )

    model = lgb.train(
        params,
        train_ds,
        valid_sets=[train_ds, val_ds],
        valid_names=["train","valid"],
        num_boost_round=500,
        early_stopping_rounds=50,
        verbose_eval=False
    )

    val_pred_proba = model.predict(X_val, num_iteration=model.best_iteration)
    auc = float(roc_auc_score(y_val, val_pred_proba)) if len(np.unique(y_val)) > 1 else float("nan")

    # threshold: max(prob>=0.2, top 0.5%)
    k = max(1, int(0.005 * len(val_pred_proba)))
    thr_quant = np.partition(val_pred_proba, -k)[-k] if len(val_pred_proba) > 0 else 0.5
    thr = max(0.2, float(thr_quant))
    val_pred = (val_pred_proba >= thr).astype(int)

    p, r, f1, _ = precision_recall_fscore_support(y_val, val_pred, average="binary", zero_division=0)
    cm = confusion_matrix(y_val, val_pred).tolist()

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump({"model": model, "features": used_cols, "threshold": thr}, model_path)

    metrics = {
        "auc": auc,
        "precision": float(p),
        "recall": float(r),
        "f1": float(f1),
        "threshold": thr,
        "confusion_matrix": cm,
        "val_size": int(len(y_val)),
        "pos_in_val": int(y_val.sum()),
    }
    return metrics, model_path

def predict_lgbm(df_features: pd.DataFrame, model_path: str) -> pd.Series:
    pack = joblib.load(model_path)
    model = pack["model"]
    used_cols = pack["features"]
    thr = float(pack.get("threshold", 0.5))
    X = df_features.reindex(columns=used_cols).fillna(0)
    proba = model.predict(X, num_iteration=getattr(model, "best_iteration", None))
    flags = (proba >= thr)
    return pd.Series(flags, index=df_features.index)
