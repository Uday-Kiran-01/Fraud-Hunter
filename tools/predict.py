# tools/predict.py
import json
import requests
import pandas as pd

OLLAMA_URL = "http://localhost:11434/api/generate"
MISTRAL_MODEL = "mistral"

def simple_rules(
    df: pd.DataFrame,
    ip_freq_quantile: float = 0.995,
    night_quantile: float = 0.995,
    hour_quantile: float = 0.997,
    channel_quantile: float = 0.997,
    target_rate: float | None = None
):
    """Adaptive thresholds over engineered features; optional coarse target rate control."""
    flags = pd.Series(False, index=df.index)

    if "ip_freq" in df.columns:
        freq = df["ip_freq"].fillna(0)
        thr = int(freq.quantile(ip_freq_quantile))
        flags = flags | (freq >= thr)

    if "ip_night_density" in df.columns:
        nd = df["ip_night_density"].fillna(0)
        flags = flags | (nd >= nd.quantile(night_quantile))

    if "ip_hour_freq" in df.columns:
        hf = df["ip_hour_freq"].fillna(0)
        flags = flags | (hf >= hf.quantile(hour_quantile))

    if "ip_channel_freq" in df.columns:
        cf = df["ip_channel_freq"].fillna(0)
        flags = flags | (cf >= cf.quantile(channel_quantile))

    # Optional coarse rate control: keep top-k by suspicion score
    if target_rate is not None and 0 < target_rate < 1:
        rank_keys = [k for k in ["ip_freq","ip_hour_freq","ip_channel_freq","ip_night_density"] if k in df.columns]
        if rank_keys:
            score = df[rank_keys].fillna(0).sum(axis=1)
            k = max(1, int(len(df) * target_rate))
            top_idx = score.sort_values(ascending=False).index[:k]
            flags = pd.Series(False, index=df.index)
            flags.loc[top_idx] = True

    return flags

def _ollama_generate(prompt: str, model: str = MISTRAL_MODEL, options: dict | None = None, timeout_s: int = 45) -> str:
    """
    Call Ollama with JSON-enforced output.
    Retries briefly; on failure returns a minimal JSON string with an error note.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    if options:
        payload["options"] = options

    last_err = None
    for _ in range(3):  # quick retries
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout_s)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
        except Exception as e:
            last_err = e
    # Hard failure: return a small JSON so callers can continue safely
    return json.dumps({"labels": {}, "notes": f"[ollama_error] {type(last_err).__name__}: {last_err}"})

def ollama_detect(df: pd.DataFrame, sample_size: int = 80) -> dict:
    """
    Score a small sample with Ollama. Never raises; always returns {series, notes}.
    """
    # Keep sample small to avoid timeouts
    cols = [c for c in [
        "click_id","ip","app","device","os","channel","is_attributed",
        "hour","minute","ip_freq","app_freq","ip_app_freq","device_freq","os_freq",
        "channel_freq","ip_night_density","ip_hour_freq","ip_channel_freq"
    ] if c in df.columns]
    slim = df.loc[:, cols].head(sample_size).copy()

    row_id_col = "click_id" if "click_id" in slim.columns else None
    if row_id_col is None:
        slim["row_id"] = slim.index.astype(str)
        row_id_col = "row_id"

    records = slim.to_dict(orient="records")
    prompt = (
        "Return ONLY a JSON object with two keys: "
        "`labels` (object mapping row_id to true/false) and `notes` (string). "
        "Label TRUE only for strongly suspicious rows.\n\n"
        f"rows: {json.dumps(records, ensure_ascii=False)}"
    )

    raw = _ollama_generate(prompt, model=MISTRAL_MODEL, options={"temperature": 0}, timeout_s=45)

    parsed = {"labels": {}, "notes": ""}
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(parsed, dict):
            parsed = {"labels": {}, "notes": "[ollama_parse_error] non-dict response"}
    except Exception as e:
        parsed = {"labels": {}, "notes": f"[ollama_parse_error] {e}"}

    labels_map = parsed.get("labels", {}) or {}
    label_series = pd.Series(False, index=slim.index)
    for idx, row in slim.iterrows():
        key = str(row[row_id_col])
        if key in labels_map:
            try:
                label_series.loc[idx] = bool(labels_map[key])
            except Exception:
                pass

    return {"series": label_series, "notes": parsed.get("notes", "")}

def hybrid_detect(
    df: pd.DataFrame,
    sample_size: int = 80,
    target_rate: float | None = None,
    quantiles: dict | None = None
) -> dict:
    """
    Rules over full data, LLM refinement over a small, ranked sample.
    If LLM fails/times out, we keep rules and record a note.
    """
    q = {"ip":0.995, "night":0.995, "hour":0.997, "chan":0.997}
    if isinstance(quantiles, dict):
        q.update(quantiles)

    rule_flags = simple_rules(
        df,
        ip_freq_quantile=q["ip"],
        night_quantile=q["night"],
        hour_quantile=q["hour"],
        channel_quantile=q["chan"],
        target_rate=target_rate
    )
    flagged_idx = df.index[rule_flags.astype(bool)]

    if len(flagged_idx) == 0:
        llm = ollama_detect(df, sample_size=sample_size)
        final = rule_flags.copy()
        final.loc[llm["series"].index] = llm["series"]
        note = llm.get("notes", "")
        return {"flags": final, "notes": note or "[hybrid] rules=0; consulted LLM sample", "mode": "llm_only_sample"}

    # Rank suspiciousness (so the LLM sees the “spikiest” rows first)
    subset = df.loc[flagged_idx].copy()
    rank_keys = [k for k in ["ip_freq","ip_hour_freq","ip_channel_freq","ip_night_density"] if k in subset.columns]
    if rank_keys:
        subset["_sus_score"] = subset[rank_keys].fillna(0).sum(axis=1)
        sample_df = subset.nlargest(min(sample_size, len(subset)), "_sus_score")
    else:
        sample_df = subset.head(sample_size)

    llm = ollama_detect(sample_df, sample_size=len(sample_df))

    final = rule_flags.copy()
    sampled_idx = llm["series"].index
    if sampled_idx.size > 0:
        final.loc[sampled_idx] = llm["series"].reindex(sampled_idx).fillna(False)

    note = llm.get("notes", "") or "[hybrid] LLM provided no notes"
    return {"flags": final, "notes": note, "mode": "hybrid"}
