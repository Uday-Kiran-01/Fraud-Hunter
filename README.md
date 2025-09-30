FraudHunterAI

A modular fraud-triage pipeline for large-scale clickstream data.
It automates the full workflow:

Clean → EDA → Feature Engineering → Detection → Report

Detection modes:

rules (deterministic, adaptive quantiles)

hybrid (rules + LLM refinement via Ollama/Mistral)

ollama (LLM-only analysis)

lgbm (optional ML baseline)

Streaming mode for multi-million row CSVs

Generates auditable artifacts: reports, flagged rows, and optional LLM insights

🚀 Quickstart
1) Setup
python -m venv .venv
# Windows
. .venv/Scripts/activate
pip install -r requirements.txt


Optional: for hybrid/ollama modes, install Ollama
 and pull Mistral:

ollama pull mistral

2) Run Examples

Rules only (fast):

python main.py --data .\data\train_sample.csv --nrows 50000 --mode rules


Hybrid (rules → LLM refinement):

# optional warmup
ollama run mistral <<< "hi"
python main.py --data .\data\train_sample.csv --nrows 20000 --mode hybrid


Ask the dataset a question (insight saved to outputs/ollama_insight.md):

python main.py --data .\data\train_sample.csv --nrows 20000 --mode rules --ask "What does this dataset represent and what suspicious patterns might exist?"


Stream full file (memory safe, chunked):

python main.py --data .\data\train_sample.csv --nrows 0 --chunksize 250000 --mode rules

📂 Outputs

outputs/fraud_report.md — Daily fraud report (rows processed, flag rate, EDA snapshot, meta, model notes)

outputs/flagged_sample.csv — Flagged rows for the current sample run

outputs/flagged_stream.csv — All flagged rows when running in streaming mode

outputs/ollama_insight.md — Natural-language dataset insight (when using --ask)

outputs/lgbm_model.pkl — Saved ML model (when using --mode lgbm)

📦 Project Structure
FraudHunterAI/
├── agents/
│   ├── data_analyst.py
│   ├── feature_engineer.py
│   ├── fraud_detector.py
│   ├── reporter.py
├── tools/
│   ├── eda.py
│   ├── features.py
│   ├── predict.py
│   ├── summarize.py
│   ├── assist.py
├── data/
│   └── train_sample.csv        # sample dataset
├── outputs/                    # generated reports + CSVs
├── tests/                      # unit tests
├── main.py                     # entry point
├── requirements.txt
└── README.md

💡 Notes

Rules provide a deterministic fraud baseline.

Hybrid mode adds explainability by consulting an LLM on a suspicious sample.

Streaming ensures the system scales to tens of millions of rows without memory blowup.

Designed to be easily extended (new rules, ML models, or detectors).