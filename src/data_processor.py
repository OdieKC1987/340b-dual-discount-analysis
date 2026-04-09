"""
data_processor.py — 340B Data Ingestion & Preprocessing Pipeline
================================================================
Reads raw HRSA 340B OPAIS and CMS Medicaid data, cleans and joins them,
and produces analysis-ready datasets.

Data Sources:
  1. HRSA 340B OPAIS Covered Entity Export (Excel)
     - Sheet 1: Covered Entity Details (~92K entities)
     - Sheet 2: Contract Pharmacy Details (~457K arrangements)
  2. CMS State Drug Utilization Data (SDUD) 2023 (~5.3M rows)
  3. CMS Medicaid Spending by Drug 2023 (~17K drugs)
"""

import pandas as pd
import os
import json
import sys


def load_340b_entities(filepath):
    """
    Load and clean 340B Covered Entity Details from OPAIS export.
    Returns DataFrame with active, participating entities.
    """
    print(f"  Loading 340B entities from {os.path.basename(filepath)}...")
    df = pd.read_excel(filepath, sheet_name="Covered Entity Details",
                       skiprows=4, engine="openpyxl")

    # Filter to active, participating entities
    active = df[(df['Organization Status'] == 'Active') & (df['Participating'] == True)].copy()

    # Clean up
    active['State'] = active['State'].astype(str).str.strip().str.upper()
    active['Entity Type'] = active['Entity Type'].astype(str).str.strip()
    active['340B ID'] = active['340B ID'].astype(str).str.strip()

    print(f"    {len(df):,} total -> {len(active):,} active participating entities")
    print(f"    {active['State'].nunique()} states, {active['Entity Type'].nunique()} entity types")
    return active


def load_contract_pharmacies(filepath):
    """
    Load Contract Pharmacy Details, identifying carve-in arrangements.
    The 'Medicaid Billing' field flags pharmacies billing Medicaid for 340B drugs.
    """
    print(f"  Loading contract pharmacies from {os.path.basename(filepath)}...")
    df = pd.read_excel(filepath, sheet_name="Contract Pharmacy Details",
                       skiprows=4, engine="openpyxl")

    df['State'] = df['State'].astype(str).str.strip().str.upper()
    df['Medicaid Billing'] = df['Medicaid Billing'].astype(str).str.strip()

    active = df[df['Participating'] == True].copy()
    carve_in = active[active['Medicaid Billing'] == 'Yes'].copy()

    print(f"    {len(df):,} total -> {len(active):,} active arrangements")
    print(f"    {len(carve_in):,} carve-in (Medicaid Billing = Yes)")
    return active, carve_in


def load_sdud(filepath, states=None):
    """
    Load CMS State Drug Utilization Data.
    Optionally filter to specific states.
    """
    print(f"  Loading SDUD from {os.path.basename(filepath)}...")
    df = pd.read_csv(filepath, low_memory=False)
    df['State'] = df['State'].astype(str).str.strip().str.upper()

    if states:
        df = df[df['State'].isin([s.upper() for s in states])]
        print(f"    Filtered to {len(states)} states: {len(df):,} rows")
    else:
        print(f"    {len(df):,} rows, {df['State'].nunique()} states")
    return df


def load_medicaid_spending(filepath):
    """Load CMS Medicaid Spending by Drug."""
    print(f"  Loading Medicaid Spending by Drug...")
    df = pd.read_csv(filepath, low_memory=False)
    print(f"    {len(df):,} drug records")
    return df


def build_state_risk_profile(entities, contract_pharm_active, carve_in, sdud):
    """
    Build a state-level risk profile by joining:
    - 340B entity counts by state
    - Carve-in contract pharmacy counts by state
    - Medicaid drug spending by state
    """
    print("  Building state-level risk profiles...")

    # Entity counts by state
    entity_state = entities.groupby('State').agg(
        total_entities=('CE ID', 'nunique'),
        dsh_count=('Entity Type', lambda x: (x == 'DSH').sum()),
        ch_count=('Entity Type', lambda x: (x == 'CH').sum()),
        fqhc_count=('Entity Type', lambda x: x.isin(['FQHCLA', 'FQHC638']).sum())
    ).reset_index()

    # Carve-in counts by state
    carve_state = carve_in.groupby('State').agg(
        carve_in_arrangements=('Contract ID', 'count'),
        carve_in_entities=('CE ID', 'nunique'),
        carve_in_pharmacies=('Pharmacy ID', 'nunique')
    ).reset_index()

    # Total contract pharmacy counts by state
    cp_state = contract_pharm_active.groupby('State').agg(
        total_cp_arrangements=('Contract ID', 'count')
    ).reset_index()

    # SDUD Medicaid spending by state (exclude national XX)
    sdud_state = sdud[sdud['State'] != 'XX'].groupby('State').agg(
        medicaid_spend=('Medicaid Amount Reimbursed', 'sum'),
        total_rxs=('Number of Prescriptions', 'sum'),
        unique_ndcs=('NDC', 'nunique')
    ).reset_index()

    # Merge all
    merged = sdud_state.merge(entity_state, on='State', how='outer')
    merged = merged.merge(carve_state, on='State', how='left')
    merged = merged.merge(cp_state, on='State', how='left')

    merged = merged.fillna(0)
    for col in ['carve_in_arrangements', 'carve_in_entities', 'carve_in_pharmacies',
                'total_cp_arrangements', 'total_entities', 'dsh_count']:
        merged[col] = merged[col].astype(int)

    # Derived risk metrics
    merged['carve_in_rate'] = merged.apply(
        lambda r: r['carve_in_arrangements'] / r['total_cp_arrangements'] * 100
        if r['total_cp_arrangements'] > 0 else 0, axis=1)
    merged['has_carve_in'] = merged['carve_in_arrangements'] > 0
    merged['medicaid_spend_M'] = merged['medicaid_spend'] / 1e6

    merged = merged.sort_values('medicaid_spend', ascending=False)
    print(f"    {len(merged)} states profiled, {merged['has_carve_in'].sum()} with carve-in activity")
    return merged


def build_drug_exposure(sdud, carve_in_states):
    """
    Identify the highest-cost drugs in carve-in states —
    these represent the greatest dual discount financial exposure.
    """
    print("  Building drug exposure analysis...")
    sdud_ci = sdud[sdud['State'].isin(carve_in_states)]

    drug_exposure = sdud_ci.groupby('Product Name').agg(
        medicaid_spend=('Medicaid Amount Reimbursed', 'sum'),
        total_rxs=('Number of Prescriptions', 'sum'),
        states=('State', 'nunique')
    ).sort_values('medicaid_spend', ascending=False).reset_index()

    drug_exposure['medicaid_spend_M'] = drug_exposure['medicaid_spend'] / 1e6
    print(f"    {len(drug_exposure):,} drugs, top drug: {drug_exposure.iloc[0]['Product Name'].strip()} "
          f"(${drug_exposure.iloc[0]['medicaid_spend_M']:.1f}M)")
    return drug_exposure


def run_pipeline(raw_data_dir, output_dir):
    """
    Execute the full data processing pipeline.

    Args:
        raw_data_dir: Directory containing raw data files
        output_dir: Directory for processed output files
    """
    os.makedirs(output_dir, exist_ok=True)

    # Find files
    opais_file = None
    sdud_file = None
    spending_file = None

    for f in os.listdir(raw_data_dir):
        if '340B_CoveredEntity' in f and f.endswith('.xlsx'):
            opais_file = os.path.join(raw_data_dir, f)
        elif 'sdud' in f.lower() and f.endswith('.csv'):
            sdud_file = os.path.join(raw_data_dir, f)
        elif 'spending' in f.lower() and f.endswith('.csv'):
            spending_file = os.path.join(raw_data_dir, f)

    print("=" * 60)
    print("340B DUAL DISCOUNT DATA PIPELINE")
    print("=" * 60)

    # Step 1: Load 340B data
    print("\n[1/5] Loading 340B OPAIS data...")
    entities = load_340b_entities(opais_file)
    cp_active, carve_in = load_contract_pharmacies(opais_file)

    # Step 2: Load SDUD
    print("\n[2/5] Loading State Drug Utilization Data...")
    sdud = load_sdud(sdud_file)

    # Step 3: Load Medicaid Spending
    print("\n[3/5] Loading Medicaid Spending by Drug...")
    med_spending = load_medicaid_spending(spending_file) if spending_file else None

    # Step 4: Build state risk profiles
    print("\n[4/5] Building state risk profiles...")
    state_risk = build_state_risk_profile(entities, cp_active, carve_in, sdud)

    # Step 5: Build drug exposure analysis
    print("\n[5/5] Building drug exposure analysis...")
    carve_in_states = list(carve_in['State'].unique())
    drug_exposure = build_drug_exposure(sdud, carve_in_states)

    # Save outputs
    print("\nSaving processed data...")
    state_risk.to_csv(os.path.join(output_dir, "state_risk_profile.csv"), index=False)
    drug_exposure.head(100).to_csv(os.path.join(output_dir, "top_drugs_carve_in_states.csv"), index=False)

    # Save entity summary
    entity_summary = entities.groupby(['State', 'Entity Type']).size().reset_index(name='count')
    entity_summary.to_csv(os.path.join(output_dir, "entity_summary_by_state_type.csv"), index=False)

    # Save carve-in detail
    carve_in.to_csv(os.path.join(output_dir, "carve_in_arrangements.csv"), index=False)

    # Summary stats
    summary = {
        "total_active_entities": int(len(entities)),
        "total_cp_arrangements": int(len(cp_active)),
        "carve_in_arrangements": int(len(carve_in)),
        "carve_in_rate_pct": round(len(carve_in) / len(cp_active) * 100, 2),
        "carve_in_states": carve_in_states,
        "total_medicaid_spend_B": round(sdud[sdud['State'] != 'XX']['Medicaid Amount Reimbursed'].sum() / 1e9, 1),
        "carve_in_states_medicaid_spend_B": round(
            state_risk[state_risk['has_carve_in']]['medicaid_spend'].sum() / 1e9, 1),
    }
    with open(os.path.join(output_dir, "pipeline_summary.json"), 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 60}")
    print("PIPELINE COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Active entities:      {summary['total_active_entities']:,}")
    print(f"  CP arrangements:      {summary['total_cp_arrangements']:,}")
    print(f"  Carve-in:             {summary['carve_in_arrangements']:,} ({summary['carve_in_rate_pct']}%)")
    print(f"  Carve-in states:      {len(carve_in_states)}")
    print(f"  Medicaid spend:       ${summary['total_medicaid_spend_B']}B total, "
          f"${summary['carve_in_states_medicaid_spend_B']}B in carve-in states")
    print(f"\n  Output files in: {output_dir}")

    return state_risk, drug_exposure, summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="340B Data Processing Pipeline")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory with raw data files")
    parser.add_argument("--output-dir", default="data/processed", help="Output directory")
    args = parser.parse_args()

    run_pipeline(args.raw_dir, args.output_dir)
