340B Dual Discount Risk Analysis
CSI-4130/5130: Artificial Intelligence — Course Project (Path 1: Application Development with LLM APIs)
Author: Johann Odermann | Date: April 2026
An AI-powered analysis system that identifies and quantifies dual discount risk in the 340B Drug Pricing Program using publicly available federal data from HRSA and CMS.
Video Presentation
Watch the project presentation: [ and demo on YouTube](https://docs.google.com/presentation/d/10_8HHBVo9xhBsckgQOsQehKassIAN4Yl/edit?usp=sharing&ouid=101438158060080140692&rtpof=true&sd=true)

Note: Replace the link above with your actual YouTube/Google Drive URL after recording.

Problem Statement
The 340B Drug Pricing Program requires drug manufacturers to provide outpatient drugs at significantly reduced prices to eligible healthcare organizations ("covered entities"). A dual discount (or "duplicate discount") occurs when a manufacturer is subject to both a 340B discounted price and a Medicaid drug rebate on the same prescription — which is prohibited by federal law but difficult to enforce.
The GAO has found that CMS does not effectively track or prevent dual discounts, and states use inconsistent methods to identify 340B claims. This project applies AI techniques to analyze the scope of this problem using public data.
Approach
This project follows Path 1 (Application Development with LLM APIs) from the course project description, combining data engineering with a Retrieval-Augmented Generation (RAG) system:

Data Pipeline (src/data_processor.py): Ingests and joins three federal datasets to identify where dual discount risk exists — specifically, which 340B contract pharmacies are "carved in" (billing Medicaid for 340B drugs) and what Medicaid spending flows through those states.
RAG Engine (src/rag_engine.py): Converts processed data into searchable text documents, embeds them with TF-IDF vectors, indexes them with FAISS, and retrieves relevant context for LLM-powered natural language queries about 340B dual discount risk.
Interactive Dashboard (src/dashboard.py): Generates a standalone HTML dashboard with Chart.js visualizations of state-level risk profiles, carve-in patterns, and high-exposure drugs.

Key Findings
MetricValueActive 340B covered entities62,548Contract pharmacy arrangements375,374Carve-in arrangements (dual discount risk)3,234 (0.86%)States with carve-in activity11Medicaid drug spend in carve-in states$45.1 billionTotal US Medicaid drug spend (2023)$99.7 billion
Notable findings:

Minnesota has 52% of all carve-in arrangements nationally (1,695), concentrated among 145 entities and just 23 pharmacies
New York is second with 952 arrangements across 316 entities
83% of carve-in arrangements involve DSH (Disproportionate Share) hospitals
High-spend states like Virginia ($6.1B), Ohio ($4.8B), and Pennsylvania ($4.6B) have zero carve-in data — a potential oversight gap
Biktarvy ($1.4B), Humira ($1.3B), and Trulicity ($1.1B) are the highest-exposure drugs in carve-in states

Data Sources
All data is publicly available with no data use agreement required:
SourceDatasetRecordsLinkHRSA340B OPAIS Covered Entity Export~92K entities + ~457K contract pharmacies340bopais.hrsa.govCMSState Drug Utilization Data (SDUD) 20235.3M rowsdata.medicaid.govCMSMedicaid Spending by Drug 2023~17K drugsdata.cms.gov

Note: Raw data files are not included in this repository due to size (500MB+). See Data Setup below for download instructions.

Project Structure
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
├── rag_index/                    # Pre-built FAISS index
│   ├── 340b.faiss                # Vector index (737 docs)
│   ├── vectorizer.pkl            # Fitted TF-IDF model
│   ├── documents.json            # Document texts
│   └── metadata.json             # Document metadata
├── reports/
│   ├── 340B_Dual_Discount_Dashboard.html   # Interactive data dashboard
│   ├── 340B_RAG_Demo.html                  # AI query tool (interactive demo)
│   ├── 340B_Presentation.pptx              # Slide deck (15 slides)
│   ├── rag_data.json                       # Knowledge base for web demo
│   └── Final_Report.pdf                    # Academic report (14 pages, JAMA-style)
└── docs/
    └── images/                   # Screenshots and figures
Quick Start
Prerequisites

Python 3.9+
~2GB disk space for raw data

Installation
bashgit clone https://github.com/OdieKC1987/340b-dual-discount-analysis.git
cd 340b-dual-discount-analysis
pip install -r requirements.txt
Data Setup
Download the raw data files into data/raw/:

340B OPAIS Export: Go to 340bopais.hrsa.gov/Reports → download "Covered Entity Daily Export" (Excel). Save as data/raw/340B_CoveredEntity_Export.xlsx
SDUD 2023: Go to data.medicaid.gov → download CSV. Save as data/raw/sdud-2023.csv
Medicaid Spending by Drug: Go to data.cms.gov → download 2023 CSV. Save as data/raw/medicaid_spending_by_drug_2023.csv

Run the Pipeline
bash# Step 1: Process raw data
python src/data_processor.py --raw-dir data/raw --output-dir data/processed

# Step 2: Build the RAG index
python src/rag_engine.py --build --data-dir data/processed --index-dir rag_index

# Step 3: Generate the dashboard
python src/dashboard.py --data-dir data/processed --output reports/340B_Dual_Discount_Dashboard.html
Query the System
bash# Retrieval-only (no API key needed)
python src/rag_engine.py --query "Which states have the highest dual discount risk?"

# With LLM-powered answers (requires API key)
export OPENROUTER_API_KEY="your-key-here"
python src/rag_engine.py --query "What drugs in Minnesota have the most Medicaid exposure?" --llm

# Interactive mode
python src/rag_engine.py --interactive
Example Queries

"Which states have the highest dual discount risk?"
"What is Minnesota's carve-in situation?"
"Which drugs have the most Medicaid spending in carve-in states?"
"Are there states with high Medicaid spending but no carve-in tracking?"
"How many DSH hospitals participate in 340B?"

Interactive Demo
The project includes two interactive HTML tools:

Data Dashboard (reports/340B_Dual_Discount_Dashboard.html): Visualizations of state-level risk, carve-in patterns, and drug exposure using Chart.js.
AI Query Tool (reports/340B_RAG_Demo.html): A browser-based RAG interface where you can ask natural language questions about 340B dual discount risk. Works in two modes:

Retrieval only (no API key needed): Returns the most relevant data documents
LLM-powered (with OpenRouter API key): Generates natural language analysis grounded in the retrieved data



To run the demo locally, serve the reports/ directory:
bashcd reports
python -m http.server 8000
# Open http://localhost:8000/340B_RAG_Demo.html
Methods & Architecture
Data Pipeline
The pipeline joins three datasets at the state level:

340B OPAIS provides entity registrations and the critical Medicaid Billing flag on contract pharmacies (Yes = carve-in = dual discount risk)
SDUD provides the Medicaid claims volume per state
Medicaid Spending by Drug identifies which drugs carry the most financial exposure

RAG System
The RAG engine creates three types of searchable documents:

State risk profiles — one per state with 340B entity counts, carve-in activity, and Medicaid spending
Drug exposure profiles — top 50 drugs by Medicaid spending in carve-in states
Entity carve-in details — individual 340B entities with their carve-in contract pharmacies

Documents are embedded using TF-IDF (10K features, bigram) and indexed with FAISS for cosine similarity search. Retrieved context is formatted into structured prompts for LLM APIs (supporting OpenRouter and OpenAI).

Upgrade path: Replace TF-IDF with sentence-transformers (all-MiniLM-L6-v2) for semantic embeddings. The architecture supports this as a drop-in replacement.

Technologies Used

Python (pandas, scikit-learn, numpy)
FAISS — Facebook AI Similarity Search for vector indexing
TF-IDF — Text embedding (prototype; swappable with neural embeddings)
Chart.js — Interactive data visualizations
LLM APIs — OpenRouter / OpenAI for natural language generation

Citations & Acknowledgements

HRSA Office of Pharmacy Affairs. 340B OPAIS Covered Entity Export. March 2026. https://340bopais.hrsa.gov/
CMS. State Drug Utilization Data 2023. Updated December 2025. https://data.medicaid.gov/
CMS. Medicaid Spending by Drug 2023. https://data.cms.gov/
GAO. 340B Drug Pricing Program: Oversight of the Intersection with the Medicaid Drug Rebate Program Needs Improvement (GAO-20-212). https://www.gao.gov/products/gao-20-212
HRSA. 340B Drug Pricing Program Duplicate Discount Prohibition. https://www.hrsa.gov/opa/program-requirements/medicaid-exclusion
Facebook Research. FAISS: A Library for Efficient Similarity Search. https://github.com/facebookresearch/faiss

License
This project is for educational purposes (CSI-4130/5130 coursework). Data sourced from federal government websites (public domain).
