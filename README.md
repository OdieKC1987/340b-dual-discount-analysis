# 340B Dual Discount Risk Analysis

**CSI-4130/5130: Artificial Intelligence — Course Project**

An AI-powered analysis system that identifies and quantifies dual discount risk in the 340B Drug Pricing Program using publicly available federal data from HRSA and CMS.

## Problem Statement

The [340B Drug Pricing Program](https://www.hrsa.gov/opa) requires drug manufacturers to provide outpatient drugs at significantly reduced prices to eligible healthcare organizations ("covered entities"). A **dual discount** (or "duplicate discount") occurs when a manufacturer is subject to *both* a 340B discounted price *and* a Medicaid drug rebate on the same prescription — which is [prohibited by federal law](https://www.hrsa.gov/opa/program-requirements/medicaid-exclusion) but difficult to enforce.

The [GAO has found](https://www.gao.gov/products/gao-20-212) that CMS does not effectively track or prevent dual discounts, and states use inconsistent methods to identify 340B claims. This project applies AI techniques to analyze the scope of this problem using public data.

## Approach

This project follows **Path 1 (Application Development with LLM APIs)** from the course project description, combining data engineering with a Retrieval-Augmented Generation (RAG) system:

1. **Data Pipeline** (`src/data_processor.py`): Ingests and joins three federal datasets to identify where dual discount risk exists — specifically, which 340B contract pharmacies are "carved in" (billing Medicaid for 340B drugs) and what Medicaid spending flows through those states.

2. **RAG Engine** (`src/rag_engine.py`): Converts processed data into searchable text documents, embeds them with TF-IDF vectors, indexes them with FAISS, and retrieves relevant context for LLM-powered natural language queries about 340B dual discount risk.

3. **Interactive Dashboard** (`src/dashboard.py`): Generates a standalone HTML dashboard with Chart.js visualizations of state-level risk profiles, carve-in patterns, and high-exposure drugs.

## Key Findings

| Metric | Value |
|--------|-------|
| Active 340B covered entities | 62,548 |
| Contract pharmacy arrangements | 375,374 |
| **Carve-in arrangements (dual discount risk)** | **3,234 (0.86%)** |
| States with carve-in activity | 11 |
| Medicaid drug spend in carve-in states | $45.1 billion |
| Total US Medicaid drug spend (2023) | $99.7 billion |

**Notable findings:**
- **Minnesota** has 52% of all carve-in arrangements nationally (1,695), concentrated among 145 entities and just 23 pharmacies
- **New York** is second with 952 arrangements across 316 entities
- **83% of carve-in arrangements involve DSH (Disproportionate Share) hospitals**
- High-spend states like Virginia ($6.1B), Ohio ($4.8B), and Pennsylvania ($4.6B) have zero carve-in data — a potential oversight gap
- **Biktarvy** ($1.4B), **Humira** ($1.3B), and **Trulicity** ($1.1B) are the highest-exposure drugs in carve-in states

## Data Sources

All data is publicly available with no data use agreement required:

| Source | Dataset | Records | Link |
|--------|---------|---------|------|
| HRSA | 340B OPAIS Covered Entity Export | ~92K entities + ~457K contract pharmacies | [340bopais.hrsa.gov](https://340bopais.hrsa.gov/Reports) |
| CMS | State Drug Utilization Data (SDUD) 2023 | 5.3M rows | [data.medicaid.gov](https://data.medicaid.gov) |
| CMS | Medicaid Spending by Drug 2023 | ~17K drugs | [data.cms.gov](https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicaid-spending-by-drug) |

> **Note:** Raw data files are not included in this repository due to size (500MB+). See [Data Setup](#data-setup) below for download instructions.

## Project Structure

```
340b-dual-discount-analysis/
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore rules
├── data/
│   ├── raw/                      # Place downloaded data files here
│   │   ├── .gitkeep
│   │   └── DATA_SOURCES.md       # Download instructions
│   └── processed/                # Pipeline outputs
│       ├── state_risk_profile.csv
│       ├── top_drugs_carve_in_states.csv
│       ├── carve_in_arrangements.csv
│       ├── entity_summary_by_state_type.csv
│       └── pipeline_summary.json
├── src/
│   ├── data_processor.py         # Data ingestion & preprocessing pipeline
│   ├── rag_engine.py             # RAG system (TF-IDF + FAISS + LLM)
│   └── dashboard.py              # HTML dashboard generator
├── notebooks/                    # Jupyter notebooks for exploration
├── reports/
│   ├── 340B_Dual_Discount_Dashboard.html   # Interactive dashboard
│   └── Final_Report.pdf          # Academic report (PDF)
└── docs/
    └── images/                   # Screenshots and figures
```

## Quick Start

### Prerequisites

- Python 3.9+
- ~2GB disk space for raw data

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/340b-dual-discount-analysis.git
cd 340b-dual-discount-analysis
pip install -r requirements.txt
```

### Data Setup

Download the raw data files into `data/raw/`:

1. **340B OPAIS Export**: Go to [340bopais.hrsa.gov/Reports](https://340bopais.hrsa.gov/Reports) → download "Covered Entity Daily Export" (Excel). Save as `data/raw/340B_CoveredEntity_Export.xlsx`

2. **SDUD 2023**: Go to [data.medicaid.gov](https://data.medicaid.gov/dataset/d890d3a9-6b00-43fd-8b31-fcba4c8e2909) → download CSV. Save as `data/raw/sdud-2023.csv`

3. **Medicaid Spending by Drug**: Go to [data.cms.gov](https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicaid-spending-by-drug) → download 2023 CSV. Save as `data/raw/medicaid_spending_by_drug_2023.csv`

### Run the Pipeline

```bash
# Step 1: Process raw data
python src/data_processor.py --raw-dir data/raw --output-dir data/processed

# Step 2: Build the RAG index
python src/rag_engine.py --build --data-dir data/processed --index-dir rag_index

# Step 3: Generate the dashboard
python src/dashboard.py --data-dir data/processed --output reports/340B_Dual_Discount_Dashboard.html
```

### Query the System

```bash
# Retrieval-only (no API key needed)
python src/rag_engine.py --query "Which states have the highest dual discount risk?"

# With LLM-powered answers (requires API key)
export OPENROUTER_API_KEY="your-key-here"
python src/rag_engine.py --query "What drugs in Minnesota have the most Medicaid exposure?" --llm

# Interactive mode
python src/rag_engine.py --interactive
```

### Example Queries

- "Which states have the highest dual discount risk?"
- "What is Minnesota's carve-in situation?"
- "Which drugs have the most Medicaid spending in carve-in states?"
- "Are there states with high Medicaid spending but no carve-in tracking?"
- "How many DSH hospitals participate in 340B?"

## Methods & Architecture

### Data Pipeline
The pipeline joins three datasets at the state level:
- **340B OPAIS** provides entity registrations and the critical `Medicaid Billing` flag on contract pharmacies (Yes = carve-in = dual discount risk)
- **SDUD** provides the Medicaid claims volume per state
- **Medicaid Spending by Drug** identifies which drugs carry the most financial exposure

### RAG System
The RAG engine creates three types of searchable documents:
1. **State risk profiles** — one per state with 340B entity counts, carve-in activity, and Medicaid spending
2. **Drug exposure profiles** — top 50 drugs by Medicaid spending in carve-in states
3. **Entity carve-in details** — individual 340B entities with their carve-in contract pharmacies

Documents are embedded using TF-IDF (10K features, bigram) and indexed with FAISS for cosine similarity search. Retrieved context is formatted into structured prompts for LLM APIs (supporting OpenRouter and OpenAI).

> **Upgrade path:** Replace TF-IDF with `sentence-transformers` (`all-MiniLM-L6-v2`) for semantic embeddings. The architecture supports this as a drop-in replacement.

## Technologies Used

- **Python** (pandas, scikit-learn, numpy)
- **FAISS** — Facebook AI Similarity Search for vector indexing
- **TF-IDF** — Text embedding (prototype; swappable with neural embeddings)
- **Chart.js** — Interactive data visualizations
- **LLM APIs** — OpenRouter / OpenAI for natural language generation

## Citations & Acknowledgements

- HRSA Office of Pharmacy Affairs. *340B OPAIS Covered Entity Export*. March 2026. https://340bopais.hrsa.gov/
- CMS. *State Drug Utilization Data 2023*. Updated December 2025. https://data.medicaid.gov/
- CMS. *Medicaid Spending by Drug 2023*. https://data.cms.gov/
- GAO. *340B Drug Pricing Program: Oversight of the Intersection with the Medicaid Drug Rebate Program Needs Improvement* (GAO-20-212). https://www.gao.gov/products/gao-20-212
- HRSA. *340B Drug Pricing Program Duplicate Discount Prohibition*. https://www.hrsa.gov/opa/program-requirements/medicaid-exclusion
- Facebook Research. *FAISS: A Library for Efficient Similarity Search*. https://github.com/facebookresearch/faiss

## License

This project is for educational purposes (CSI-4130/5130 coursework). Data sourced from federal government websites (public domain).
