# ROI Calculator (Pilot and Annual Contract)

Use this worksheet during discovery and in final pilot readouts.

## 1) Input Variables

Customer inputs:

- Monthly ticket volume: `T`
- Percentage of tickets in repetitive categories: `R`
- Current average handle time in minutes: `AHT_current`
- Expected AHT reduction percent in assisted tickets: `AHT_reduction_pct`
- Loaded support cost per hour (fully loaded): `Cost_hour`
- Expected deflection percent in repetitive categories: `Deflection_pct`
- Tool annual cost (software + services): `Cost_annual`

## 2) Core Formulas

Repetitive monthly tickets:

- `T_rep = T * R`

Deflected monthly tickets:

- `T_deflected = T_rep * Deflection_pct`

Assisted handled tickets:

- `T_assisted = T - T_deflected`

Minutes saved from AHT improvements:

- `Minutes_saved_AHT = T_assisted * AHT_current * AHT_reduction_pct`

Minutes saved from deflection:

- `Minutes_saved_deflection = T_deflected * AHT_current`

Total monthly minutes saved:

- `Minutes_saved_total = Minutes_saved_AHT + Minutes_saved_deflection`

Monthly savings in EUR:

- `Savings_monthly = (Minutes_saved_total / 60) * Cost_hour`

Annual savings in EUR:

- `Savings_annual = Savings_monthly * 12`

Net annual benefit:

- `Net_annual = Savings_annual - Cost_annual`

ROI percent:

- `ROI_pct = (Net_annual / Cost_annual) * 100`

Payback period (months):

- `Payback_months = Cost_annual / Savings_monthly`

## 3) Example (Replace with Real Customer Data)

Assumptions:

- `T = 12000`
- `R = 0.45`
- `AHT_current = 11`
- `AHT_reduction_pct = 0.20`
- `Cost_hour = 32`
- `Deflection_pct = 0.15`
- `Cost_annual = 36000`

Results:

- `T_rep = 5400`
- `T_deflected = 810`
- `T_assisted = 11190`
- `Minutes_saved_AHT = 24618`
- `Minutes_saved_deflection = 8910`
- `Minutes_saved_total = 33528`
- `Savings_monthly = EUR 17,881.60`
- `Savings_annual = EUR 214,579.20`
- `Net_annual = EUR 178,579.20`
- `ROI_pct = 496%`
- `Payback_months = 2.01`

## 4) Commercial Decision Rules

Suggested approval thresholds:

- Payback under 6 months
- Positive ROI over 100 percent
- Improvement in at least 2 core KPIs (AHT, FRT, deflection)

## 5) Notes for Honest Forecasting

- Use conservative ranges for first pilot model
- Separate one-time setup from recurring software value
- Exclude unvalidated assumptions from executive summary
