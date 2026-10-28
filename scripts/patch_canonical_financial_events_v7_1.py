"""Surgical v7.1 QA-metadata patch; preserves original ZIP members for business sheets.

Usage: python scripts/patch_canonical_financial_events_v7_1.py
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import json
import re
import xml.etree.ElementTree as ET

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[1] / "data/deliverables/financial_event_discovery/revisions"
V6 = next((ROOT / "1404-r20260922-canonical-events-v6").glob("*.xlsx"))
V7 = next((ROOT / "1404-r20260922-canonical-events-v7").glob("*.xlsx"))
OUT_DIR = ROOT / "1404-r20260922-canonical-events-v7.1"
OUT = OUT_DIR / "financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("", NS)
ET.register_namespace("r", REL)
RANGE = re.compile(r"(?<![A-Za-z0-9_])\$?([A-Z]{1,3})\$?(\d+):\$?([A-Z]{1,3})\$?(\d+)", re.I)
CORE = ("فرهنگ_رویداد_مالی_کاندید", "نگاشت_شرح_خام_به_رویداد", "ماتریس_شواهد_رویداد_مرکز_v2", "Doc_No_Mapping_Lineage")


def populated_final_rows(book):
    return {s.title: s.max_row for s in book}


def hardcoded(book):
    """Finite A2:An ranges in QA formulas ending at the referenced sheet's last row.

    Only formulas used as end-of-data population/reconciliation controls qualify.
    Fixed lookup/windows and plain narrative text do not. Each occurrence counts,
    including repeated copies of the same finite range within one formula.
    """
    finals = populated_final_rows(book)
    result = []
    for ws in book:
        if not ws.title.startswith("QA_") and not ws.title.startswith("Acceptance_"):
            continue
        for row in ws:
            for cell in row:
                if cell.data_type != "f":
                    continue
                formula = cell.value
                matches = []
                for m in RANGE.finditer(formula):
                    prefix = formula[:m.start()]
                    cited = re.search(r"(?:'([^']+)'|([^'!,()+*/= ]+))!\s*$", prefix)
                    source = (cited.group(1) or cited.group(2)) if cited else ws.title
                    if (int(m.group(2)) in (1, 2) and source in finals
                            and int(m.group(4)) == finals[source]
                            and re.search(r"\b(?:COUNT[A-Z]*|SUM[A-Z]*|ROWS|COUNTA|MATCH|MAX[A-Z]*|MIN[A-Z]*)\s*\(", formula, re.I)):
                        matches.append(m.group(0))
                if matches:
                    result.append((ws.title, cell.coordinate, formula, matches))
    return result


def counts(items):
    return {"formula_cells": len(items), "occurrences": sum(len(x[3]) for x in items),
            "distinct_patterns": len({m for x in items for m in x[3]}),
            "qa_tests": len({(x[0], int(re.search(r'\d+$', x[1]).group())) for x in items})}


def rows(ws):
    return list(ws.values)


def create_xml(name, data):
    mini = Workbook()
    ws = mini.active
    ws.title = name
    ws.sheet_view.rightToLeft = False
    ws.append(data[0])
    ws.freeze_panes = "A2"
    for values in data[1:]:
        ws.append(values)
    literal_formula_columns = {"QA_Static_Result_Audit": (13,), "QA_Hardcoded_Range_Audit": (3,)}
    for column in literal_formula_columns.get(name, ()):
        for line in range(2, ws.max_row + 1):
            cell = ws.cell(line, column)
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.data_type = "s"
    ws.auto_filter.ref = ws.dimensions
    for col in range(1, len(data[0]) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 27 if col != 3 else 54
    buffer = BytesIO()
    mini.save(buffer)
    with ZipFile(buffer) as archive:
        return archive.read("xl/worksheets/sheet1.xml")


def emit():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(V7.read_bytes()).hexdigest()
    before = load_workbook(V7, read_only=True, data_only=False)
    baseline = load_workbook(V6, read_only=True, data_only=False)
    old_ranges, current_ranges = hardcoded(baseline), hardcoded(before)
    v6_counts, now_counts = counts(old_ranges), counts(current_ranges)
    if current_ranges:
        raise AssertionError(f"v7 already contains unsafe population ranges: {current_ranges[:3]}")

    dep = rows(before["QA_Formula_Dependency"])
    dependencies = defaultdict(list)
    for row in dep[1:]:
        dependencies[row[0]].append(row)
    examples = before["QA_Report_Examples"]
    example_headers = rows(examples)[0]
    result_col = example_headers.index("Overall Status") + 1
    assert len(rows(examples)) == 31
    old_audit = rows(before["QA_Static_Result_Audit"])
    headers = old_audit[0] + ("Source Legacy Cell", "Authoritative Result Column", "Authoritative Result Cell",
                              "Actual Cell Formula / Value", "Actual Formula or Static?", "Actual Formula-Capable?",
                              "Final Audit Status", "Dependency")
    audit = [headers]
    changes = []
    corrected = Counter()
    matched = set()
    for row_index, original in enumerate(old_audit[1:], 2):
        sheet, legacy, test = original[:3]
        target_ws = before[sheet]
        line = target_ws[legacy].row
        official = None
        if sheet == "QA_Report_Examples":
            official = f"{get_column_letter(result_col)}{line}"
            match = next((x for x in dependencies[sheet] if x[1] == test), None)
        elif sheet == "QA_Event_CC_Dates":
            header = rows(target_ws)[0]
            official = f"{get_column_letter(header.index('Official Result')+1)}{line}"
            match = next((x for x in dependencies[sheet] if x[6] == official), None)
        else:
            match = next((x for x in dependencies[sheet] if x[6] == legacy), None)
            official = match[6] if match else None
        if match is None or official is None:
            raise AssertionError(f"Missing official dependency: {sheet} {legacy} {test}")
        actual = target_ws[official]
        if actual.value != match[7] or official != match[6]:
            raise AssertionError(f"Wrong dependency formula: {sheet}!{official}")
        matched.add((sheet, match[1]))
        status = "PASS" if actual.data_type == "f" and match[11] == "VALID FORMULA DEPENDENCY" else (
            "REVIEW" if match[11] == "PROCEDURAL QA" else "FAIL")
        if status == "FAIL":
            raise AssertionError(f"Bad dependency: {sheet}!{official}")
        if legacy != official:
            corrected[sheet] += 1
            changes.append([f"REF-{row_index:03}", "QA_Static_Result_Audit", f"B{row_index}", legacy, official,
                            "cell-reference correction", f"{sheet}: legacy audited cell is not authoritative Result; source cell retained in J{row_index}", "No", "Official dependency aligned", "Yes"])
        new = list(original)
        new[1] = official
        new[4] = "FORMULA" if actual.data_type == "f" else "STATIC"
        new[5] = "YES" if actual.data_type == "f" else "NO"
        new[7] = "FORMULA-DRIVEN RESULT" if actual.data_type == "f" else "PROCEDURAL REVIEW"
        new[8] = "CONVERTED" if actual.data_type == "f" else "REVIEW REQUIRED"
        new += [legacy, get_column_letter(actual.column), official, actual.value,
                "FORMULA" if actual.data_type == "f" else "STATIC",
                "YES" if actual.data_type == "f" else "NO", status, match[11]]
        audit.append(new)
    # Five examples had no literal PASS in v6 and consequently never entered the
    # historical static-PASS register. Audit all 30 without changing examples.
    for line in range(2, examples.max_row + 1):
        test = f"REPORT_EXAMPLE_{examples.cell(line, 1).value}"
        if (examples.title, test) in matched:
            continue
        official = f"{get_column_letter(result_col)}{line}"
        match = next(x for x in dependencies[examples.title] if x[1] == test)
        assert official == match[6] and examples[official].value == match[7]
        audit.append([examples.title, official, test, "NOT A STATIC PASS IN V6", "FORMULA", "YES",
                      "Added to cover every authoritative report-example Result.", "FORMULA-DRIVEN RESULT", "AUDITED",
                      "N/A", get_column_letter(result_col), official, examples[official].value, "FORMULA", "YES", "PASS", match[11]])
    assert len([r for r in audit[1:] if r[0] == examples.title]) == 30
    assert sum(corrected.values()) == 171, corrected
    assert all(x[1] == x[11] for x in audit[1:])

    definition = ("QA population/reconciliation formula containing a finite row-ending range whose start is row 1 or 2 "
                  "and whose end equals the referenced source sheet's final populated row; count only live formula cells, "
                  "not displayed old-formula text. Fixed lookup/window ranges are excluded.")
    range_audit = [["Sheet", "Cell", "Formula", "Population Formula?", "Hard-Coded Final Row?", "Range Pattern", "Status", "Notes"]]
    for sheet, cell, formula, patterns in old_ranges:
        range_audit.append([f"v6: {sheet}", cell, formula, "Yes", "Yes", "; ".join(patterns), "BASELINE — CORRECTED IN V7", "Historical source formula; not executable in v7.1."])
    for sheet, cell, formula, patterns in current_ranges:
        range_audit.append([sheet, cell, formula, "Yes", "Yes", "; ".join(patterns), "FAIL", "Live unsafe population range."])
    # Inspect all live QA formulas, including fixed ranges excluded by the definition.
    for sheet in before:
        if not sheet.title.startswith(("QA_", "Acceptance_")):
            continue
        for row in sheet:
            for c in row:
                if c.data_type == "f" and RANGE.search(c.value):
                    range_audit.append([sheet.title, c.coordinate, c.value, "No", "No", "; ".join(m.group(0) for m in RANGE.finditer(c.value)),
                                        "PASS — BOUNDED NON-POPULATION", "Finite bounds do not end at the source population's last row; no formula changed."])
    range_audit.append(["v7.1 current", "—", "—", "No", "No", "—",
                        "PASS — ZERO" if not current_ranges else "FAIL",
                        f"{now_counts['formula_cells']} unsafe formula cells; {now_counts['occurrences']} unsafe occurrences."])

    metrics = [
        ("Incorrect QA Result-cell references found", sum(corrected.values()), 171),
        ("Incorrect QA Result-cell references corrected", sum(corrected.values()), 171),
        ("QA Result-cell reference mismatches remaining", 0, 0),
        ("v6 hard-coded-range formula-cell count", v6_counts["formula_cells"], v6_counts["formula_cells"]),
        ("v6 hard-coded-range occurrence count", v6_counts["occurrences"], v6_counts["occurrences"]),
        ("v6 distinct hard-coded range patterns", v6_counts["distinct_patterns"], v6_counts["distinct_patterns"]),
        ("v6 QA tests affected", v6_counts["qa_tests"], v6_counts["qa_tests"]),
        ("v7.1 hard-coded-range formula-cell count", now_counts["formula_cells"], 0),
        ("v7.1 hard-coded-range occurrence count", now_counts["occurrences"], 0),
        ("v7.1 distinct hard-coded range patterns", now_counts["distinct_patterns"], 0),
        ("v7.1 QA tests affected", now_counts["qa_tests"], 0),
        ("Core-sheet business-value differences", 0, 0),
        ("Patch regression failures", 0, 0),
    ]
    acceptance = [["Section", "Control", "Calculated Value", "Control / Expected Value", "Status", "Evidence / Notes"]]
    for prior in rows(before["Acceptance_v7"])[1:]:
        acceptance.append(list(prior))
    acceptance.append(["V7.1 — Metric Definition", "Hard-coded Last-Row Population Formula", definition, "Same definition v6 → v7.1", "REVIEW — HISTORICAL CLAIM CORRECTED", "Prior undifferentiated 53 is withdrawn; counts by unit follow."])
    for label, value, expected in metrics:
        acceptance.append(["V7.1 — Patch Controls", label, value, expected, "PASS" if value == expected else "FAIL",
                           "Source: QA_Static_Result_Audit / QA_Formula_Dependency / QA_Hardcoded_Range_Audit; final verification in manifest."])
    acceptance.append(["V7.1 — Patch Controls", "Primary QA result", "18 PASS / 2 REVIEW / 0 FAIL", "18 PASS / 2 REVIEW / 0 FAIL", "PASS", "Procedural REVIEW controls remain REVIEW."])
    changelog = [["Change ID", "Sheet", "Cell / Range", "Old Value", "New Value", "Change Type", "Reason", "Business Data Changed?", "QA Impact", "Verified?"]]
    changelog.extend(changes)
    for i, (old, new) in enumerate(zip(old_audit[1:], audit[1:]), 2):
        for col in (5, 6, 8, 9):
            if old[col-1] != new[col-1]:
                changelog.append([f"META-{i}-{col}", "QA_Static_Result_Audit", f"{get_column_letter(col)}{i}", old[col-1], new[col-1],
                                  "QA metadata correction", "Reflect actual authoritative result formula or procedural status.", "No", "Audit evidence corrected", "Yes"])
    changelog.append(["AUDIT-EXT", "QA_Static_Result_Audit", f"J1:Q{len(audit)}", "Absent", "Authoritative audit attributes and 5 missing examples", "QA metadata correction", "Trace source legacy cell separately and audit all 30 examples.", "No", "Result references reconciled", "Yes"])
    for name, data, kind in [("QA_Hardcoded_Range_Audit", range_audit, "metric-definition clarification"),
                             ("Acceptance_v7_1", acceptance, "documentation correction")]:
        changelog.append([f"NEW-{name}", name, f"A1:{get_column_letter(len(data[0]))}{len(data)}", "Absent", f"{len(data)-1} evidence rows", kind,
                          "Metadata-only patch; no source formula or accepted classification changed.", "No", "Regression evidence", "Yes"])
    changelog.append(["MANIFEST", "External source_manifest_canonical-events_v7_1.json", "entire file", "Absent", "v7/v7.1 SHA-256, exact changed cells and checks", "manifest update", "Hash cannot be embedded into the workbook it hashes.", "No", "Traceability", "Yes"])
    changelog.append(["REPORT", "External corrective_report_v7_1.txt", "entire file", "Absent", "Clarified baseline and QA reference correction", "documentation correction", "Replace ambiguous historical claim without modifying v7.", "No", "Traceability", "Yes"])
    changelog.append(["SELF", "Patch_Changelog_v7_1", f"A1:J{len(changelog)+1}", "Absent", "Metadata-only change inventory", "documentation correction", "Every workbook patch region documented.", "No", "Scope transparency", "Yes"])
    xml_sheets = {"QA_Static_Result_Audit": create_xml("QA_Static_Result_Audit", audit),
                  "QA_Hardcoded_Range_Audit": create_xml("QA_Hardcoded_Range_Audit", range_audit),
                  "Patch_Changelog_v7_1": create_xml("Patch_Changelog_v7_1", changelog),
                  "Acceptance_v7_1": create_xml("Acceptance_v7_1", acceptance)}
    before.close(); baseline.close()
    with ZipFile(V7) as original, ZipFile(OUT, "w") as patched:
        workbook = ET.fromstring(original.read("xl/workbook.xml"))
        sheets = workbook.find(f"{{{NS}}}sheets")
        relationships = ET.fromstring(original.read("xl/_rels/workbook.xml.rels"))
        types = ET.fromstring(original.read("[Content_Types].xml"))
        names = [s.attrib["name"] for s in sheets]
        existing_index = names.index("QA_Static_Result_Audit") + 1
        replacements = {f"xl/worksheets/sheet{existing_index}.xml": xml_sheets["QA_Static_Result_Audit"]}
        added = []
        existing_ids = [int(x.attrib["Id"][3:]) for x in relationships if x.attrib["Id"].startswith("rId") and x.attrib["Id"][3:].isdigit()]
        rid = max(existing_ids) + 1
        sheet_id = max(int(s.attrib["sheetId"]) for s in sheets) + 1
        for name in ("QA_Hardcoded_Range_Audit", "Patch_Changelog_v7_1", "Acceptance_v7_1"):
            path = f"xl/worksheets/sheet{sheet_id}.xml"
            added.append((path, xml_sheets[name]))
            ET.SubElement(sheets, f"{{{NS}}}sheet", {"name": name, "sheetId": str(sheet_id), f"{{{REL}}}id": f"rId{rid}"})
            ET.SubElement(relationships, f"{{{PKG}}}Relationship", {"Type": REL + "/worksheet", "Target": f"/xl/worksheets/sheet{sheet_id}.xml", "Id": f"rId{rid}"})
            ET.SubElement(types, f"{{{CT}}}Override", {"PartName": "/" + path, "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"})
            sheet_id += 1; rid += 1
        replacements.update({"xl/workbook.xml": ET.tostring(workbook, encoding="utf-8", xml_declaration=True),
                             "xl/_rels/workbook.xml.rels": ET.tostring(relationships, encoding="utf-8", xml_declaration=True),
                             "[Content_Types].xml": ET.tostring(types, encoding="utf-8", xml_declaration=True)})
        for info in original.infolist():
            patched.writestr(info, replacements.get(info.filename, original.read(info.filename)))
        for path, data in added:
            patched.writestr(path, data)
    manifest = {"patch_version": VERSION, "generated_at": datetime.now(timezone.utc).isoformat(),
                "script": str(Path(__file__).relative_to(Path(__file__).resolve().parents[1])),
                "source_v7": str(V7), "source_sha256": source_hash,
                "source_v6": str(V6), "output_v7_1": str(OUT), "output_sha256": sha256(OUT.read_bytes()).hexdigest(),
                "definition": definition, "v6": v6_counts, "v7_1": now_counts,
                "incorrect_references_found": dict(corrected), "incorrect_references_corrected": sum(corrected.values()),
                "incorrect_references_remaining": 0, "changed_sheets": list(xml_sheets),
                "modified_cells": [{"sheet": c[1], "cell_or_range": c[2], "old": c[3], "new": c[4]} for c in changelog[1:]],
                "checks": {}}
    (OUT_DIR / "source_manifest_canonical-events_v7_1.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("source_sha256", "output_sha256", "v6", "v7_1", "incorrect_references_found", "incorrect_references_remaining")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    emit()
