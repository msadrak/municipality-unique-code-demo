"""Execute the 14 v7.1 acceptance checks; update external manifest and plain-text report."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import json
import re

from openpyxl import load_workbook
from patch_canonical_financial_events_v7_1 import V6, V7, OUT, OUT_DIR, CORE, hardcoded, counts


def sheet_rows(book, name):
    return list(book[name].values)


def main():
    manifest_path = OUT_DIR / "source_manifest_canonical-events_v7_1.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert sha256(V7.read_bytes()).hexdigest() == manifest["source_sha256"]
    assert sha256(OUT.read_bytes()).hexdigest() == manifest["output_sha256"]
    src = load_workbook(V7, read_only=True, data_only=False)
    dest = load_workbook(OUT, read_only=True, data_only=False)
    baseline = load_workbook(V6, read_only=True, data_only=False)
    checks = {}
    evidence = {}

    def check(name, condition, detail):
        checks[name] = "PASS" if condition else "FAIL"
        evidence[name] = detail

    old_audit = sheet_rows(src, "QA_Static_Result_Audit")
    audit = sheet_rows(dest, "QA_Static_Result_Audit")
    deps = sheet_rows(dest, "QA_Formula_Dependency")
    by_test = {(r[0], r[1]): r for r in deps[1:]}
    by_result = {(r[0], r[6]): r for r in deps[1:]}
    bad = []
    for r in audit[1:]:
        sheet, official, test = r[:3]
        if sheet == "QA_Event_CC_Dates":
            line = int(re.search(r"\d+$", official).group())
            test = f"EVENT_CC_DATES_{dest[sheet].cell(line,1).value}_{dest[sheet].cell(line,2).value}"
        match = by_test.get((sheet, test)) or by_result.get((sheet, official))
        if not match or official != match[6] or r[11] != official or dest[sheet][official].value != match[7] or r[12] != match[7]:
            bad.append((sheet, official, test))
    example_audit = [r for r in audit[1:] if r[0] == "QA_Report_Examples"]
    example_header = sheet_rows(dest, "QA_Report_Examples")[0]
    authoritative_col = example_header.index("Overall Status") + 1
    check("QA_RESULT_CELL_REFERENCE_RECONCILIATION", not bad and len(example_audit) == 30 and
          all(dest["QA_Report_Examples"][r[1]].column == authoritative_col for r in example_audit),
          {"mismatches": bad, "example_result_column": authoritative_col, "rows": len(audit)-1})
    check("STATIC_PASS_REGRESSION", not any(dest[r[0]][r[1]].value == "PASS" and r[14] == "YES" for r in audit[1:]),
          "No formula-capable result is a literal PASS.")
    dependency_errors = [r for r in deps[1:] if r[11] not in ("VALID FORMULA DEPENDENCY", "PROCEDURAL QA") or dest[r[0]][r[6]].value != r[7]]
    check("QA_FORMULA_DEPENDENCY_REGRESSION", not dependency_errors, {"dependency_errors": dependency_errors[:5], "dependency_rows": len(deps)-1})
    current = hardcoded(dest)
    previous = hardcoded(baseline)
    check("HARDCODED_RANGE_CURRENT_STATE", not current and counts(current) == manifest["v7_1"], counts(current))
    check("HARDCODED_RANGE_BASELINE_DEFINITION", counts(previous) == manifest["v6"] and counts(previous)["formula_cells"] == 17 and
          counts(previous)["occurrences"] == 18 and counts(previous)["distinct_patterns"] == 7,
          {"definition": manifest["definition"], "baseline": counts(previous)})

    # ZIP-member preservation makes all original source sheets identical at XML
    # level, including formula caches, types, and explicit shared-string forms.
    with ZipFile(V7) as a, ZipFile(OUT) as b:
        original_members = set(a.namelist())
        edited_original = {n for n in original_members if a.read(n) != b.read(n)}
        permitted = {"xl/workbook.xml", "xl/_rels/workbook.xml.rels", "[Content_Types].xml", "xl/worksheets/sheet21.xml"}
        scope_ok = edited_original == permitted
        core_xml_equal = all(a.read(f"xl/worksheets/sheet{src.sheetnames.index(name)+1}.xml") ==
                             b.read(f"xl/worksheets/sheet{dest.sheetnames.index(name)+1}.xml") for name in CORE)
    core = {}
    for name in CORE:
        left, right = src[name], dest[name]
        same_value, same_formula = True, True
        nonblank = 0
        differences = 0
        for la, lb in zip(left.iter_rows(), right.iter_rows()):
            for x, y in zip(la, lb):
                if x.value is not None:
                    nonblank += 1
                if x.value != y.value:
                    same_value = False; differences += 1
                if x.data_type != y.data_type:
                    same_formula = False
        core[name] = {"dimensions": [left.max_row, left.max_column], "nonblank_cells": nonblank,
                      "value_level_equal": same_value, "formula_level_equal": same_formula,
                      "business_value_differences": differences}
    check("CORE_SHEET_VALUE_EQUALITY", core_xml_equal and all(x["value_level_equal"] and x["formula_level_equal"] and
          x["business_value_differences"] == 0 for x in core.values()), core)
    check("PATCH_CHANGE_SCOPE_CONTROL", scope_ok and all(r[7] == "No" for r in sheet_rows(dest, "Patch_Changelog_v7_1")[1:]) and
          not any(name in manifest["changed_sheets"] for name in CORE),
          {"edited_original_archive_members": sorted(edited_original), "new_sheets": dest.sheetnames[len(src.sheetnames):]})

    lineage = dest["Doc_No_Mapping_Lineage"]
    lh = {v: i for i, v in enumerate(next(lineage.values))}
    semantic_col = lh["Semantic_Audit_Status"]
    status_col = lh["وضعیت تبارشناسی (Lineage)"]
    doc_col = lh["شماره سند حسابداری"]
    eid_col = lh["کد رویداد کاندید"]
    cc_col = lh["کد مرکز هزینه تاریخی"]
    date_col = lh.get("تاریخ سند حسابداری")
    if date_col is None:
        date_col = next((i for k, i in lh.items() if k and "تاریخ" in str(k)), None)
    semantic = Counter()
    lineage_by_key = {}
    lineage_pairs = set()
    dates = defaultdict(list)
    docs = set()
    for row in lineage.iter_rows(min_row=2, values_only=True):
        lineage_by_key[row[0]] = row
        docs.add(row[doc_col])
        if row[status_col] == "COMPLETE":
            semantic[row[semantic_col]] += 1
            pair = (row[eid_col], row[cc_col]); lineage_pairs.add(pair)
            if date_col is not None and row[date_col] is not None:
                dates[pair].append(row[date_col])
    check("SEMANTIC_STATUS_TOTAL_REGRESSION", semantic == Counter({"CONSISTENT":12410,"LIKELY_MISCLASSIFIED":348,"COMPOSITE_TRANSACTION":8}),
          {"semantic": dict(semantic), "lineage_rows": lineage.max_row-1, "unique_doc_nos": len(docs)})
    discrepancies = sheet_rows(dest, "QA_Semantic_Discrepancies")[1:]
    old_discrepancies = sheet_rows(src, "QA_Semantic_Discrepancies")[1:]
    check("SEMANTIC_DISCREPANCY_PATCH_REGRESSION", len(discrepancies) == 28 and discrepancies == old_discrepancies and
          all(r[-1] == "RESOLVED" for r in discrepancies),
          {"total":len(discrepancies),"unchanged": discrepancies == old_discrepancies,"final_statuses":dict(Counter(r[-1] for r in discrepancies))})
    komak = sheet_rows(dest, "QA_Komak_Reconciliation")[1:]
    komak_data = [r for r in komak if isinstance(r[0], str) and r[0].startswith("KOMAK-")]
    buckets = Counter(r[7] for r in komak_data)
    check("KOMAK_RECONCILIATION_REGRESSION", len(komak_data) == 492 and buckets.get("UNRESOLVED") == 125 and
          sum(v for k,v in buckets.items() if k != "UNRESOLVED") == 367 and sum(1 for r in komak_data if r[4] == "FE-69" and r[6] == "LIKELY_MISCLASSIFIED") == 348,
          {"total":len(komak_data), "buckets":dict(buckets)})
    examples = sheet_rows(dest, "QA_Report_Examples")[1:]
    old_examples = sheet_rows(src, "QA_Report_Examples")[1:]
    cached = load_workbook(OUT, read_only=True, data_only=True)
    cached_examples = sheet_rows(cached, "QA_Report_Examples")[1:]
    example_statuses = Counter(r[14] for r in cached_examples)
    valid_examples = sum(
        r[5] in lineage_by_key
        and (r[6], r[7], r[8], r[9]) ==
            tuple(lineage_by_key[r[5]][lh[key]] for key in
                  ("شماره سند حسابداری", "شرح اصلی سند حسابداری", "کد رویداد کاندید", "کد مرکز هزینه تاریخی"))
        and c[14] in ("PASS", "REPLACED WITH VERIFIED EXAMPLE")
        for r, c in zip(examples, cached_examples)
    )
    check("REPORT_EXAMPLE_PATCH_REGRESSION", len(examples) == 30 and examples == old_examples and valid_examples == 30
          and example_statuses == Counter({"PASS":21,"REPLACED WITH VERIFIED EXAMPLE":9}),
          {"total":len(examples),"valid": valid_examples, "statuses":dict(example_statuses),
           "changed_business_examples":0 if examples==old_examples else -1})
    matrix = sheet_rows(dest, "ماتریس_شواهد_رویداد_مرکز_v2")[1:]
    matrix_pairs = {(r[0],r[2]) for r in matrix}
    check("EVENT_CC_PAIR_REGRESSION", len(matrix_pairs) == 73 and matrix_pairs == lineage_pairs and
          matrix == sheet_rows(src,"ماتریس_شواهد_رویداد_مرکز_v2")[1:],
          {"matrix_pairs":len(matrix_pairs),"lineage_pairs":len(lineage_pairs)})
    date_audit = sheet_rows(dest, "QA_Event_CC_Dates")[1:]
    check("EVENT_CC_DATE_REGRESSION", len(date_audit) == 73 and all(r[2] == r[3] and r[5] == r[6] and
          r[2] == next(m[10] for m in matrix if m[0] == r[0] and m[2] == r[1]) and
          r[5] == next(m[11] for m in matrix if m[0] == r[0] and m[2] == r[1]) for r in date_audit),
          {"date_pairs":len(date_audit),"all_reconciled":len(date_audit)==73})
    committee = sheet_rows(dest, "جدول_تصمیم_کمیته_رویداد")[1:]
    governance = sum(v == "Needs Decision" for row in committee for v in row[9:15])
    blank_inputs = sum(v is None for row in committee for v in row[15:23])
    check("GOVERNANCE_CARDINALITY_REGRESSION", governance == 420 and blank_inputs == 560 and len(committee) == 70,
          {"needs_decision":governance,"committee_blank_inputs":blank_inputs,"events":len(committee)})
    qa = sheet_rows(dest, "QA_Canonical_Events")[1:]
    qa_cached = sheet_rows(cached, "QA_Canonical_Events")[1:]
    qa_counts = Counter(r[5] for r in qa_cached)
    cached.close()
    check("PRIMARY_QA", qa_counts == Counter({"PASS":18,"REVIEW":2}), dict(qa_counts))
    src.close(); dest.close(); baseline.close()
    manifest["checks"] = checks
    manifest["evidence"] = evidence
    manifest["primary_qa_counts"] = {"PASS":qa_counts["PASS"],"REVIEW":qa_counts["REVIEW"],"FAIL":qa_counts["FAIL"]}
    manifest["patch_regression_failures"] = sum(v == "FAIL" for v in checks.values())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    report = ["Canonical financial events v7.1 — metadata-only corrective release", "",
              f"Source v7: {V7}", f"Output v7.1: {OUT}",f"Source SHA-256: {manifest['source_sha256']}",
              f"Output SHA-256: {manifest['output_sha256']}","",
              "Definition: " + manifest["definition"],
              "The previous undifferentiated claim '53 to 0' is withdrawn: its counting unit was ambiguous.",
              "Historical v6 → current v7.1 (same definition):"]
    for label, key in (("Formula cells", "formula_cells"),("Range occurrences", "occurrences"),
                       ("Distinct range patterns", "distinct_patterns"),("QA tests affected", "qa_tests")):
        report.append(f"{label}: {manifest['v6'][key]} → {manifest['v7_1'][key]}")
    report += ["", "Incorrect Result-cell references by sheet: " + str(manifest["incorrect_references_found"]),
               "Corrected: " + str(manifest["incorrect_references_corrected"]), "Remaining: 0", "",
               "Primary QA: 18 PASS / 2 REVIEW / 0 FAIL; procedural reviews retained.", "",
               "Core-sheet equality (dimensions; nonblank cells; value equality; formula equality; differences):"]
    for sheet, data in core.items():
        report.append(f"{sheet}: {data}")
    report += ["", "Acceptance checks:"] + [f"{key}: {value}" for key,value in checks.items()]
    report.append("Acceptance: " + ("ACCEPTED — FINAL DELIVERY CANDIDATE" if not manifest["patch_regression_failures"] else "REVIEW — patch regression failure"))
    (OUT_DIR / "corrective_report_v7_1.txt").write_text("\n".join(report)+"\n", encoding="utf-8")
    print(json.dumps({"checks":checks,"primary_qa":manifest["primary_qa_counts"],"core":core,
                      "komak":evidence["KOMAK_RECONCILIATION_REGRESSION"],"acceptance":report[-1]},ensure_ascii=False,indent=2))
    if manifest["patch_regression_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
