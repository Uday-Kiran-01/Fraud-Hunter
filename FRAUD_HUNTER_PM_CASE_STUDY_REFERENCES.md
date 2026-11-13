# Personal Product Case Study: FraudHunterAI (The Authentic PM Journey)

This document details the product thinking, technical trade-offs, and authentic motivations behind **FraudHunterAI**. As an aspiring Product Manager targeting FinTech, AdTech, and Data Platform roles, FraudHunterAI showcases my approach to large-scale data engineering, autonomous multi-agent orchestration, and actionable risk intelligence.

---

### 1. User Discovery (The Risk Analyst's "Data Drowning" Dilemma)
*   **The Raw Problem:** In high-volume clickstream environments, risk analysts are subjected to cognitive overload. Marketing teams demand instant traffic verification, but the raw clickstream file contains 20 million rows of IP addresses, device identifiers, and timestamps. Analysts run into a frustrating trade-off: fast heuristic rules catch obvious bots but flag thousands of false positives during organic traffic spikes, while advanced gradient-boosted ML models output opaque probability floats (`0.912`) that give an investigator zero context when preparing a partner dispute memo.
*   **The PM Discovery:** Fraud triage is not a single mathematical formula: it is an **Investigative Workflow**. A human investigator first inspects the distribution (EDA), creates domain-specific behavioral signals (Feature Engineering), evaluates suspicious clusters (Scoring), and writes an executive case report (Reporting). To build scalable fraud software, I had to model the software architecture after the **Human Investigation Lifecycle**.

---

### 2. Expectations vs Reality (The Monolithic Script Trap)

#### What I Expected:
*   **The Single-Pipeline Illusion:** My initial engineering plan was to write a monolithic Python script that piped raw data through preprocessing, trained an ensemble model, and dumped predictions into a spreadsheet.
*   **The Memory Trap:** I assumed loading sample files into memory was sufficient to validate the architecture.

#### What Reality Proved (The Memory Wall & Explainability Reality Check):
*   **The Big Data Memory Wall:** In real AdTech data testing, loading multi-gigabyte clickstream files caused repeated `MemoryError` crashes on standard workstations.
*   **Black-Box Rejection:** When commercial partners or internal teams were presented with raw model probabilities, they refused to issue affiliate clawbacks without clear evidence of *why* the traffic was fraudulent.
*   **The Multi-Agent Architectural Pivot:** I decomposed the monolithic script into an **Autonomous Multi-Agent Pipeline**:
    1.  *Data Analyst Agent:* Handles distribution analysis and anomaly scoping.
    2.  *Feature Engineer Agent:* Computes velocity and frequency metrics.
    3.  *Fraud Detector Agent:* Manages execution modes (`rules`, `hybrid`, `ollama`, `lgbm`).
    4.  *Reporter Agent:* Synthesizes technical findings into clean, executive-ready Markdown dossiers.

---

### 3. The Automation & Architecture Journey (From Memory Crashes to Local LLMs)

#### 1. Out-of-Core Streaming Engine
*   To eliminate out-of-memory crashes, I architected a chunked streaming generator (`--chunksize 250000`). The pipeline streams tens of millions of rows with a flat, predictable memory footprint (< 1.5 GB RAM).

#### 2. Local LLM Integration (Mistral via Ollama)
*   Cloud LLMs charge massive API fees and risk transmitting confidential clickstream data externally. I integrated local Mistral models via Ollama to generate natural-language forensic explanations (`outputs/ollama_insight.md`) completely on-premise at zero API cost.

#### 3. Adaptive Quantile Rules
*   Replaced fragile hardcoded thresholds with dynamic quantiles that adapt automatically to macro volume fluctuations.

#### 4. The `--ask` Conversational Dataset Interface
*   Built a natural-language query mechanism allowing analysts to ask questions directly via the CLI, synthesizing complex statistical tables into plain-English answers in seconds.

---

### 4. What the Project Taught Me (Speed vs Explainability)

#### 1. Explainability Over Micro-Optimizations
*   **The Academic Trap:** In data science, there is an obsession with squeezing another 0.5% F1-score out of complex black-box ensembles.
*   **The Operations Reality:** In a real operations room, if an algorithm flags an ad agency's traffic without a clear explanation, the commercial team revolts.
*   **The PM Action:** I prioritized **Operational Explainability**. That is why I built the `--mode hybrid` option: the rules engine swiftly isolates suspicious candidates, and the LLM agent automatically generates a human-readable diagnosis of *why* the traffic pattern is unnatural (e.g., *"IP subnet exhibits rapid 120ms click pacing across 40 disparate app categories, indicative of an emulated device farm"*).

#### 2. Privacy in Enterprise Risk Systems
*   **Local-First AI:** Risk teams deal with sensitive partner identifiers. Running local LLMs via Ollama provides complete data residency and zero external leak risks.

---

### 5. Future Value: Automated Ad Fraud Settlement Networks
*   **Automated Affiliate Dispute Memos:** Transforming flagged dossiers into legally defensible dispute letters with embedded forensic graphs ready for affiliate networks.
*   **Graph Network Bot Clustering:** Mapping device fingerprint entropy and IP subnet topologies to identify coordinated bot syndicates.

---

### 6. Product Management Retrospective & Intuition
1.  **Architecture Should Mirror Human Operations:** Decomposing software into multi-agent roles reflecting the human investigation lifecycle creates intuitive, maintainable software.
2.  **Product Craft Is Risk Communication:** A fraud detection system that outputs numbers without explanations is only half-built. Turning raw anomalies into plain-English forensic narratives empowers human teams to act with complete confidence.
3.  **Respecting Hardware Constraints:** Designing memory-safe out-of-core pipelines ensures tools remain accessible on modest developer laptops rather than requiring expensive cloud clusters.
