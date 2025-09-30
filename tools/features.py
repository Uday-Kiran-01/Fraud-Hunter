# tools/features.py
import os
import pandas as pd
import numpy as np

def _safe_group_count(df: pd.DataFrame, by: str) -> pd.Series:
    try:
        return df.groupby(by)[by].transform("count")
    except Exception:
        return pd.Series(np.nan, index=df.index)

def _parse_time(df: pd.DataFrame):
    if "click_time" in df.columns and "click_dt" not in df.columns:
        s = pd.to_datetime(df["click_time"], errors="coerce")
        return {
            "click_dt": s,
            "hour": s.dt.hour,
            "minute": s.dt.minute,
            "dayofweek": s.dt.dayofweek,
        }
    return {}

def add_features(df: pd.DataFrame, output_dir: str = "outputs") -> pd.DataFrame:
    os.makedirs(output_dir, exist_ok=True)
    X = df.copy()

    # Frequencies
    if "ip" in X.columns:
        X["ip_freq"] = _safe_group_count(X, "ip")
    if "app" in X.columns:
        X["app_freq"] = _safe_group_count(X, "app")
    if {"ip","app"} <= set(X.columns):
        X["ip_app_freq"] = X.groupby(["ip","app"])["app"].transform("count")

    if "device" in X.columns:
        X["device_freq"] = _safe_group_count(X, "device")
    if "os" in X.columns:
        X["os_freq"] = _safe_group_count(X, "os")
    if "channel" in X.columns:
        X["channel_freq"] = _safe_group_count(X, "channel")

    # Time-based
    tcols = _parse_time(X)
    for k, v in tcols.items():
        X[k] = v

    # Signals
    if {"ip_freq","hour"}.issubset(X.columns):
        X["night_click"] = X["hour"].isin([0,1,2,3,4]).astype(int)
        X["ip_night_density"] = X["ip_freq"] * (1 + 2*X["night_click"])

    if {"ip","hour"}.issubset(X.columns):
        X["ip_hour_freq"] = X.groupby(["ip","hour"])["ip"].transform("count")

    if {"ip","channel"}.issubset(X.columns):
        X["ip_channel_freq"] = X.groupby(["ip","channel"])["channel"].transform("count")

    return X
