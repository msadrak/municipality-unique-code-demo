# Deployment and Operational Plan — Region 14

This document describes the steps to prepare, validate and deploy the municipality-unique-code-demo system for Region 14, focusing on civil works (عمرانی) items.

## 1) Goal

- Align Region 14 budget data (capital/civil works) with system activity definitions.
- Produce mapping templates for domain experts to validate.
- Run operational scenarios with Region 14 data and document assumptions.

## 2) Files produced so far

- `scripts/Region14_Capital_Budget.xlsx` — extracted Region 14 rows (259 rows)
- `scripts/region14_analysis_summary.txt` — UTF-8 analysis of topics/subtopics and sample rows
- `scripts/region14_civil_items.csv` — (will be produced by `analyze_region14_civil.py`) filtered civil items
- `scripts/region14_activity_mapping_prefill.csv` — prefilled mapping template for review

## 3) Analysis steps (what we did)

1. Extract Region 14 rows from the main capital budget.
2. Inspect `موضوع`, `زیر موضوع`, `شرح ردیف`, and `متولی` columns to identify civil-related items.
3. Heuristically flagged civil works rows using keywords and topic lists; produced a prefilled mapping CSV for domain expert review.

## 4) Semantic alignment and mapping process

1. Domain expert workshop: review `region14_activity_mapping_prefill.csv`. For each row:
   - Confirm whether the budget line corresponds to an existing system activity or needs a new activity.
   - Fill `mapped_activity_code` and `mapped_activity_name` when resolved.
   - Add notes for ambiguous or combined items.

2. Import mappings into the system. The import script `scripts/import_region14_budget.py` can be extended to read mapping CSV and create `Activity` objects and links to `BudgetItem`.

## 5) Validation checks (data quality)

- Ensure `کد بودجه` is unique or normalized (strip suffixes like `01`/`0201` that indicate sub-lines).
- Numeric fields (مصوب، تخصیص، هزینه) should be parsed as floats and nulls respected.
- Verify `متولی` names match OrgUnit records; create missing org units during import.

## 6) Operational scenarios and tests

1. Scenario A (Planning to Execution): map approved budget lines to activities, simulate allocating funds and recording expenditures.
2. Scenario B (Maintenance): process recurring maintenance (`مستمر`) lines over a year and verify spend aggregation.
3. Scenario C (Project-based): multi-year capital projects (non-مستمر) and milestone-based spending.

For each scenario, run the import and then query aggregates (by activity, by trustee, by zone) to compare with expected totals.

## 7) Risks and assumptions

- Heuristic keyword matching may miss or misclassify items; domain validation is required.
- Budget descriptions are heterogeneous; some lines combine several activities.
- Local naming conventions (Persian variants, spacing) require normalization.

## 8) Next concrete steps for me (I will execute unless you object)

1. Run `analyze_region14_civil.py` to produce `region14_civil_items.csv` and `region14_activity_mapping_prefill.csv`.
2. Create an import extension to `import_region14_budget.py` to accept a filled mapping CSV and link budget items to activities in the DB.
3. Create 3 small test scenarios (scripts) that run end-to-end using Region 14 data and assert aggregate checks.

Please confirm if you'd like me to (A) run the analysis now and produce the CSVs, (B) proceed to implement the mapping-import extension, or (C) both. If you want domain-expert outputs in a particular CSV format, tell me the required columns.
