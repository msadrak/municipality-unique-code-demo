# taxi_terminals_1404_1405

Pipeline that integrates the Taxi and Terminal organizations' FY1404-1405 accounting exports into the Unique Code
financial-event / cost-center / KPI architecture. Everything produced here is PROPOSED (layer B) or OBSERVED (layer A);
nothing is approved and nothing is activated in the application.

Run order (repository root): `01_load.py`, `02_extract_municipality_chart.py`, `03_build_core.py`, `04_classify_events.py`,
`05_classify_cost_centers.py`, `06_accounts.py`, `07_kpi_comparison.py`, `09_qa.py`, `08_build_outputs.py`, `10_reports.py`,
`11_postbuild_qa.py`, `10_reports.py`.  Then `pytest tests/test_taxi_terminals_mapping.py`.

Rules live in `rules.py` (event catalog of new candidates, expense subtype map) and in the `MZ`/`TEXT_CC` tables of
`05_classify_cost_centers.py`.  Outputs: `data/deliverables/taxi_terminals_1404_1405/`; scratch DB: `data/work/taxi_terminals/tt.sqlite`.


## v2 — audited, reconciled, decision-ready revision (`TT_VARIANT=v2`)

v2 never overwrites v1.  With `TT_VARIANT=v2` the pipeline uses `data/work/taxi_terminals/tt_v2.sqlite` (seeded by copying `tt.sqlite`)
and writes to `data/deliverables/taxi_terminals_1404_1405/revisions/v2/`.

Run order (repository root, set `TT_VARIANT=v2`): copy `tt.sqlite` → `tt_v2.sqlite`; `04_classify_events.py`; `05_classify_cost_centers.py`;
`07_kpi_comparison.py`; `09_qa.py`; `13_kpi_independent.py` (independent recomputation straight from the source xlsx);
`14_v2_audit.py` (ATTACHes v1: event review/crosswalk, CC proposal reconciliation, change log, terminal agency evidence);
`15_kpi_qa_v2.py` (KPI verification + status taxonomy + the named v2 QA tests); `08_build_outputs.py` (+ `v2_sheets.py`, `decisions_v2.py`);
`16_reports_v2.py docs`; `11_postbuild_qa.py`; `16_reports_v2.py docs`; `11_postbuild_qa.py`; `16_reports_v2.py qa`.
Source-archive verification (7-Zip) lives outside the repo; its result is `machine_readable/rar_verification.json`.


## v2.1 — final corrective pass (`TT_VARIANT=v21`)

Starts from a fresh copy of `tt_v2.sqlite` (v1 and v2 are never modified) and writes to `data/deliverables/taxi_terminals_1404_1405/revisions/v2.1/`.
Run order (repository root, `TT_VARIANT=v21`): `17_v21_corrections.py` (KPI duplicate fix, title masking, LOW-confidence cost-center audit with
`audit_rules_v21.py`, FE-70 split into PEO-01/PEO-02/TT-NE-11, population bridge, coverage by confidence) → `09_qa.py` → `13_kpi_independent.py` →
`15_kpi_qa_v2.py` → `19_kpi_status_v21.py` (Definition / Calculation / Verification / Governance status model, kpi_counts) → `18_qa_v21.py` →
`08_build_outputs.py` (+ `v2_sheets.py`, `v21_sheets.py`) → `20_docs_v21.py` → `11_postbuild_qa.py` → `21_final_v21.py` → `20_docs_v21.py` → `21_final_v21.py`.
The manual sample verdicts (`audit_samples_v21_round1/2.json`, `audit_postfix_v21.json` in `data/work/taxi_terminals/`) are inputs of 17; narration used by the reviewer stays in `data/work` only.
`qa_registry_v21.py` is the single source of QA totals (categories: V21_ACCEPTANCE / HISTORICAL_REGRESSION / WORKBOOK_FORMULA_CONTROL).
