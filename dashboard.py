"""
dashboard.py — Generate the interactive 340B analysis dashboard (HTML)
======================================================================
Reads processed data and produces a standalone HTML file with Chart.js
visualizations of dual discount risk.
"""

import pandas as pd
import json
import os


def generate_dashboard(processed_dir, output_path):
    """Generate the interactive HTML dashboard from processed data."""
    state_df = pd.read_csv(os.path.join(processed_dir, "state_risk_profile.csv"))
    drug_df = pd.read_csv(os.path.join(processed_dir, "top_drugs_carve_in_states.csv"))

    with open(os.path.join(processed_dir, "pipeline_summary.json")) as f:
        summary = json.load(f)

    # Prepare chart data
    state_chart = state_df[state_df['medicaid_spend'] > 0].sort_values(
        'medicaid_spend', ascending=False).head(25)
    state_json = json.dumps(state_chart.to_dict('records'))

    carve_detail = state_df[state_df['carve_in_arrangements'] > 0].sort_values(
        'carve_in_arrangements', ascending=False)
    carve_json = json.dumps(carve_detail.to_dict('records'))

    drug_json = json.dumps(drug_df.head(20).to_dict('records'))

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>340B Dual Discount Risk Analysis</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; padding: 24px; }}
  .header {{ text-align: center; margin-bottom: 32px; }}
  .header h1 {{ font-size: 28px; color: #fff; margin-bottom: 8px; }}
  .header p {{ color: #888; font-size: 14px; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .kpi {{ background: #1a1d27; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #2a2d37; }}
  .kpi .value {{ font-size: 32px; font-weight: 700; color: #60a5fa; }}
  .kpi .label {{ font-size: 13px; color: #888; margin-top: 4px; }}
  .kpi.alert .value {{ color: #f59e0b; }}
  .kpi.risk .value {{ color: #ef4444; }}
  .section {{ background: #1a1d27; border-radius: 12px; padding: 24px; margin-bottom: 24px; border: 1px solid #2a2d37; }}
  .section h2 {{ font-size: 18px; margin-bottom: 16px; color: #fff; }}
  .section p.desc {{ font-size: 13px; color: #888; margin-bottom: 16px; line-height: 1.5; }}
  .chart-container {{ position: relative; width: 100%; }}
  .chart-tall {{ height: 500px; }}
  .chart-med {{ height: 400px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 10px 12px; background: #22252f; color: #aaa; font-weight: 600; border-bottom: 2px solid #333; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #2a2d37; }}
  tr:hover {{ background: #22252f; }}
  .tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
  .tag-high {{ background: #7f1d1d; color: #fca5a5; }}
  .tag-med {{ background: #78350f; color: #fcd34d; }}
  .tag-low {{ background: #14532d; color: #86efac; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  @media (max-width: 900px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
  .insight {{ background: #1e293b; border-left: 4px solid #60a5fa; padding: 16px; border-radius: 0 8px 8px 0; margin-top: 16px; font-size: 13px; line-height: 1.6; }}
  .insight strong {{ color: #93c5fd; }}
</style>
</head>
<body>
<div class="header">
  <h1>340B Dual Discount Risk Analysis</h1>
  <p>Carve-In Contract Pharmacy Analysis &middot; SDUD 2023 &middot; HRSA OPAIS March 2026</p>
</div>
<div class="kpi-row">
  <div class="kpi"><div class="value">{summary["total_active_entities"]:,}</div><div class="label">Active 340B Entities</div></div>
  <div class="kpi"><div class="value">{summary["total_cp_arrangements"]:,}</div><div class="label">Contract Pharmacy Arrangements</div></div>
  <div class="kpi alert"><div class="value">{summary["carve_in_arrangements"]:,}</div><div class="label">Carve-In Arrangements ({summary["carve_in_rate_pct"]}%)</div></div>
  <div class="kpi"><div class="value">{len(summary["carve_in_states"])}</div><div class="label">States with Carve-In Activity</div></div>
  <div class="kpi risk"><div class="value">${summary["carve_in_states_medicaid_spend_B"]}B</div><div class="label">Medicaid Spend in Carve-In States</div></div>
  <div class="kpi"><div class="value">${summary["total_medicaid_spend_B"]}B</div><div class="label">Total Medicaid Drug Spend 2023</div></div>
</div>
<div class="section">
  <h2>Carve-In States: Dual Discount Risk Profile</h2>
  <p class="desc">These states have contract pharmacies with Medicaid Billing = "Yes" (carve-in), meaning 340B-discounted drugs are dispensed to Medicaid patients through contract pharmacies — the scenario where dual discounts can occur.</p>
  <table><thead><tr><th>State</th><th>Medicaid Drug Spend</th><th>340B Entities</th><th>DSH Hospitals</th><th>Carve-In Arrangements</th><th>Risk Level</th></tr></thead>
  <tbody id="carve-table"></tbody></table>
</div>
<div class="two-col">
  <div class="section"><h2>Carve-In Arrangements by State</h2><div class="chart-container chart-med"><canvas id="carveChart"></canvas></div></div>
  <div class="section"><h2>Medicaid Spend vs. 340B Entity Density</h2><div class="chart-container chart-med"><canvas id="scatterChart"></canvas></div></div>
</div>
<div class="section">
  <h2>Top 20 Drugs by Medicaid Spend in Carve-In States</h2>
  <p class="desc">Highest-cost drugs flowing through Medicaid in carve-in states — representing the greatest dual discount financial exposure.</p>
  <div class="chart-container chart-tall"><canvas id="drugChart"></canvas></div>
</div>
<div class="section">
  <h2>Oversight Gap: High-Spend States Without Carve-In Tracking</h2>
  <table><thead><tr><th>State</th><th>Medicaid Drug Spend</th><th>340B Entities</th><th>Status</th></tr></thead>
  <tbody id="gap-table"></tbody></table>
</div>
<script>
const carveData = {carve_json};
const stateData = {state_json};
const drugData = {drug_json};
const ct = document.getElementById('carve-table');
carveData.sort((a,b) => b.carve_in_arrangements - a.carve_in_arrangements).forEach(r => {{
  const risk = r.carve_in_arrangements > 500 ? '<span class="tag tag-high">HIGH</span>' :
               r.carve_in_arrangements > 50 ? '<span class="tag tag-med">MEDIUM</span>' :
               '<span class="tag tag-low">LOW</span>';
  ct.innerHTML += `<tr><td><strong>${{r.State}}</strong></td>
    <td>${{r.medicaid_spend_M > 1000 ? '$'+(r.medicaid_spend_M/1000).toFixed(1)+'B' : '$'+r.medicaid_spend_M.toFixed(0)+'M'}}</td>
    <td>${{Math.round(r.total_entities).toLocaleString()}}</td><td>${{Math.round(r.dsh_count).toLocaleString()}}</td>
    <td>${{Math.round(r.carve_in_arrangements).toLocaleString()}}</td><td>${{risk}}</td></tr>`;
}});
const gt = document.getElementById('gap-table');
stateData.filter(r => r.carve_in_arrangements === 0 && r.medicaid_spend_M > 1000)
  .sort((a,b) => b.medicaid_spend_M - a.medicaid_spend_M).slice(0,10).forEach(r => {{
  gt.innerHTML += `<tr><td><strong>${{r.State}}</strong></td>
    <td>${{r.medicaid_spend_M > 1000 ? '$'+(r.medicaid_spend_M/1000).toFixed(1)+'B' : '$'+r.medicaid_spend_M+'M'}}</td>
    <td>${{Math.round(r.total_entities).toLocaleString()}}</td>
    <td><span class="tag tag-med">No Carve-In Data</span></td></tr>`;
}});
new Chart(document.getElementById('carveChart'), {{
  type:'bar', data:{{ labels:carveData.map(r=>r.State),
  datasets:[{{label:'Carve-In Arrangements',data:carveData.map(r=>r.carve_in_arrangements),backgroundColor:'#ef4444',borderRadius:4}},
  {{label:'Carve-In Entities',data:carveData.map(r=>r.carve_in_entities),backgroundColor:'#60a5fa',borderRadius:4}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#aaa'}}}}}},
  scales:{{x:{{ticks:{{color:'#aaa'}},grid:{{color:'#222'}}}},y:{{ticks:{{color:'#aaa'}},grid:{{color:'#222'}}}}}}}}
}});
const pts=stateData.filter(r=>r.medicaid_spend_M>100).map(r=>({{x:r.total_entities,y:r.medicaid_spend_M,label:r.State,carve:r.carve_in_arrangements>0}}));
new Chart(document.getElementById('scatterChart'), {{
  type:'scatter', data:{{datasets:[{{label:'Has Carve-In',data:pts.filter(p=>p.carve),backgroundColor:'#ef4444',pointRadius:8}},
  {{label:'No Carve-In',data:pts.filter(p=>!p.carve),backgroundColor:'#4b5563',pointRadius:6}}]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{color:'#aaa'}}}},
  tooltip:{{callbacks:{{label:ctx=>ctx.raw.label+': $'+ctx.raw.y.toLocaleString()+'M, '+ctx.raw.x+' entities'}}}}}},
  scales:{{x:{{title:{{display:true,text:'340B Entities',color:'#aaa'}},ticks:{{color:'#aaa'}},grid:{{color:'#222'}}}},
  y:{{title:{{display:true,text:'Medicaid Drug Spend ($M)',color:'#aaa'}},ticks:{{color:'#aaa'}},grid:{{color:'#222'}}}}}}}}
}});
new Chart(document.getElementById('drugChart'), {{
  type:'bar', data:{{labels:drugData.map(r=>r['Product Name'].trim()),
  datasets:[{{label:'Medicaid Spend ($M)',data:drugData.map(r=>r.medicaid_spend_M),
  backgroundColor:drugData.map(r=>r.medicaid_spend_M>500?'#ef4444':r.medicaid_spend_M>200?'#f59e0b':'#60a5fa'),borderRadius:4}}]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
  scales:{{x:{{title:{{display:true,text:'Medicaid Spend ($M)',color:'#aaa'}},ticks:{{color:'#aaa'}},grid:{{color:'#222'}}}},
  y:{{ticks:{{color:'#aaa',font:{{size:11}}}},grid:{{color:'#222'}}}}}}}}
}});
</script>
</body></html>'''

    with open(output_path, 'w') as f:
        f.write(html)
    print(f"Dashboard saved to {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/processed")
    parser.add_argument("--output", default="reports/340B_Dual_Discount_Dashboard.html")
    args = parser.parse_args()
    generate_dashboard(args.data_dir, args.output)
