# tools/assist.py
import json
import pandas as pd
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MISTRAL_MODEL = "mistral"

def _ollama_text(prompt: str, temperature: float = 0.3, timeout: int = 180) -> str:
    payload = {
        "model": MISTRAL_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        out = data.get("response", "")
        if isinstance(out, (dict, list)):
            try:
                return json.dumps(out, ensure_ascii=False)
            except Exception:
                return str(out)
        return str(out)
    except Exception as e:
        return f"(ollama_error) {e}"

def describe_dataset(df: pd.DataFrame, user_question: str = "", sample_size: int = 100) -> str:
    cols = list(df.columns)
    dtypes = {c: str(t) for c, t in df.dtypes.items()}
    preview = df.head(min(sample_size, max(10, sample_size))).to_dict(orient="records")

    prompt = f"""
You are a data analyst. I will give you dataset info; respond ONLY in Markdown with these sections:

# Ollama Insight
**Question:** <repeat the user's question>

## Summary
(2–4 sentences about what this dataset likely is, given the columns/dtypes/sample)

## Key Columns
- bullet list of 3–7 important fields

## Suspicion Heuristics
- 3–7 bullets of patterns that indicate ad click fraud

## Next Steps
- 3–7 bullets: what to do next (features, modeling, validation)

## Answer
(answer the user's question directly in 2–5 sentences)

Dataset columns:
{json.dumps(cols, ensure_ascii=False, default=str)}

Dtypes:
{json.dumps(dtypes, ensure_ascii=False, default=str)}

Head sample (trimmed):
{json.dumps(preview, ensure_ascii=False, default=str)[:4000]}

User question:
{user_question}
""".strip()

    text = _ollama_text(prompt, temperature=0.2).strip()
    if not text or text.lower() in {"{}", "null", "none"}:
        text = (
            "# Ollama Insight\n\n"
            f"**Question:** {user_question}\n\n"
            "## Summary\nThis looks like a mobile ad click dataset with IP, app, device/OS, channel, timestamps, and a sparse label (`is_attributed`).\n\n"
            "## Key Columns\n- ip\n- app\n- device\n- os\n- channel\n- click_time\n- is_attributed\n\n"
            "## Suspicion Heuristics\n- High repeated clicks from the same IP in short windows\n- Activity bursts at unusual/night hours\n- Single IP hitting many apps/channels rapidly\n\n"
            "## Next Steps\n- Engineer session/burst features\n- Train a supervised model on labeled positives\n- Monitor drift and recalibrate thresholds\n\n"
            "## Answer\nSuspicious behavior includes repeated rapid clicks from a single IP across many apps/channels and dense bursts at odd hours."
        )
    return text
