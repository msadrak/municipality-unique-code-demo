# Taxi-Gate deep audit (v1)

Independent, reproducible audit of `Taxi-Gate_Version1.xlsx` / `Taxi-Gate_version2.xlsx`
(`data/deliverables/taxi_terminals_1404_1405/`) and their integration with the Unique Code artefacts.

Run everything (read-only on every source; ~6 minutes):

```
python scripts/taxi_gate_audit/run_all.py
```

| step | script | output (data/work/taxi_gate_audit/) |
|---|---|---|
| 1 | `s01_forensics.py` — sheet inventory, OOXML facts, independent recomputation of every formula family, V1→V2 cell/formula/format/container diff | `forensics.json` |
| 2 | `s02_coa.py` — normalised new + old chart, integrity anomalies, Sheet1 provenance test against the 1404 municipality journal, usage of old accounts in the Taxi/Terminals ledger | `coa.json` |
| 3 | `s03_matching.py` — reproduces the colleague's Indel similarity and top-3 ranking, audits all 157 best matches and 471 candidates, constraint-first candidate generator, proposed crosswalk with cardinality, comparison with crosswalk v2.1 | `matching.json` |
| 4 | `s04_integration.py` — 111,600-line lineage + reconciliation, sub-account split evidence, account↔event, activity↔cost center, dimensional cardinality, domain evidence, CD-01 recomputation, prior-artefact inventory | `integration.json`, `lineage_lines.csv` |
| 5 | `s05_qa.py` — single PRE-BUILD QA registry (PASS / REVIEW / FAIL / NOT TESTABLE, every status computed) | `qa_registry.json` |
| 6 | `s06_build.py` — audit workbook, Persian decision workbook, Persian report, MANIFEST | `data/deliverables/taxi_terminals_1404_1405/taxi_gate_audit_v1/` |
| 7 | `s07_postbuild.py` — POST-BUILD checks on the delivered files (kept outside them) | `POSTBUILD_QA.md/.csv` |

Curated judgement lives in two reviewed modules, not in code paths:

* `expert_crosswalk.py` — per old account (and per organisation where the meaning differs): status, targets with
  relation type, verdict on the colleague's best match, reasoning, decision link; `SUB_SPLIT` gives the sub-account
  basis of every 1→N split.  Everything is PROPOSED; nothing is approved.
* `decisions.py` — TG-D-01 … TG-D-22 expert decisions (committee fields are left blank in the outputs).

Inputs from the prior project (read-only): `data/work/taxi_terminals/tt_v21.sqlite`, `municipality_chart.json`,
`journal_records.sqlite`, FE v7.1 workbook, `cc_master.json`, v2.1 crosswalk / events / decisions.
Privacy: person names and bank-account digits in titles are masked; ledger narration is not exported.

## Consolidated mapping (account → event → activity → cost center)

```
python scripts/taxi_gate_audit/m01_build_mapping.py   # builds account_event_cc_mapping_v1/Taxi_Terminals_Account_Event_CostCenter_Mapping.xlsx
python scripts/taxi_gate_audit/m02_qa_mapping.py      # QA against the delivered workbook → QA_log.md / QA_log.csv / summary.json
```

Requires the audit outputs `coa.json` and `matching.json` (steps s02–s03). Every ledger line falls into exactly one row that carries
amounts. Alternative cost centers, companion events of composite documents and analytical proposals are added as rows without amounts.
The workbook contains real document narrations (digit runs masked); treat it as internal.

## Final analyst table v2 (client version)

```
python scripts/taxi_gate_audit/m03_build_final_v2.py   # → account_event_cc_mapping_v2/Taxi_Terminals_Final_Mapping_v2.xlsx
python scripts/taxi_gate_audit/m04_qa_final_v2.py      # QA against that workbook → data/work/taxi_gate_audit/final_v2_QA_log.md, final_v2_summary.json
```

Run `m01` first: v2 reads the old→new coding per account from its `mapping_rows.json`. The workbook has two sheets: the 15-column
main table and `جزئیات_و_مستندات`, joined by the row id (TX-/TM-nnnn).

v2 changes the following relative to v1:

- **Relationship type.** Each relationship is marked primary, secondary, unknown or non-event. A component line that records its own
  event (`own_event` in v2.1) carries its amount on that event. The document's event then appears as a secondary row without amounts.
- **Observed cost centers.** A cost center counts as observed only when the line's activity supports it: an activity code or the document
  narration, with no conflict with the activity's center.
- **Expense lines without a center.** These are completed, as proposals, from the activity code, the event default in v2.1 or the same
  document. Where that is not possible, they get suggestion rows or are marked «نیازمند بررسی».

Each ledger line maps to exactly one amount row. The internal line-to-row lineage is in `data/work/taxi_gate_audit/final_v2_line_lineage.csv`.
The client workbook contains no narration text and no personal names.
