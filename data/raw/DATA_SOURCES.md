# Data Download Instructions

Raw data files are not included in this repository due to size constraints. Download the following files and place them in this directory (`data/raw/`).

## Required Files

### 1. HRSA 340B OPAIS Covered Entity Export
- **Source:** [340bopais.hrsa.gov/Reports](https://340bopais.hrsa.gov/Reports)
- **Action:** Click "Covered Entity Daily Export" to download the Excel file
- **Expected filename:** `340B_CoveredEntity_Export_*.xlsx`
- **Size:** ~20 MB
- **Contents:** Two sheets — "Covered Entity Details" (~92K entities) and "Contract Pharmacy Details" (~457K arrangements)

### 2. State Drug Utilization Data (SDUD) 2023
- **Source:** [data.medicaid.gov](https://data.medicaid.gov/dataset/d890d3a9-6b00-43fd-8b31-fcba4c8e2909)
- **Action:** Download the full 2023 dataset as CSV
- **Expected filename:** `sdud-2023*.csv`
- **Size:** ~482 MB
- **Contents:** 5.3M rows of quarterly Medicaid drug utilization by state and NDC

### 3. Medicaid Spending by Drug 2023
- **Source:** [data.cms.gov](https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug/medicaid-spending-by-drug)
- **Action:** Download the 2023 data CSV
- **Expected filename:** `medicaid_spending_by_drug_2023.csv` (or similar)
- **Size:** ~5 MB
- **Contents:** ~17K drug-level spending records with 5-year trends

## After Downloading

Run the data pipeline:

```bash
python src/data_processor.py --raw-dir data/raw --output-dir data/processed
```

This will produce the processed files in `data/processed/`.
