"""Independently verify the native journal enrichment without rewriting either file.

Run only after enrichment completes. Exit 1 means at least one integrity failure;
REVIEW identifies an explicitly unverified reference or an unassigned dimension.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from hashlib import sha256
from itertools import zip_longest
import json
from pathlib import Path
import posixpath
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from enrich_journal_1404 import decode_row, is_blank, iter_raw_rows, load_shared

MAIN = "xl/worksheets/sheet1.xml"
TARGETS = ("X", "Y", "Z", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ", "AK", "AL", "AM", "AN", "AO", "AP", "AQ")
PERMITTED = {MAIN, "xl/workbook.xml", "xl/_rels/workbook.xml.rels", "[Content_Types].xml"}
STATUSES = {"EXACT_MATCH", "VALIDATED_COMPOSITE"}
CELL = re.compile(rb'<(?:\w+:)?c\b[^>]*?(?:/>|>.*?</(?:\w+:)?c\s*>)', re.S)
ADDRESS = re.compile(rb'\br="([A-Z]+)([0-9]+)"')
FORMULA = re.compile(rb'<(?:\w+:)?f(?:\s|/?>)')
ROW_START = re.compile(rb'<(?:\w+:)?row\b')
ROW_END = re.compile(rb'</(?:\w+:)?row\s*>')
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
LIMIT = 12


@dataclass(frozen=True, slots=True)
class Applied:
    value: str
    file: str
    sheet: str
    reference: str
    match_key: str
    method: str
    status: str


class Results:
    def __init__(self):
        self.items = {
            str(i): {"name": name, "status": "PASS", "failure_count": 0, "examples": []}
            for i, name in enumerate((
                "ZIP CRC integrity", "Original archive member preservation",
                "Original sheet membership and relationships", "Journal row count and order",
                "Original populated cells and formulas", "Original non-target cells and row bytes",
                "Document identity B and composite C/E", "Debit Q and credit R preservation",
                "Audit uniqueness and authorized statuses", "Changed cells are truly blank and formula-free",
                "Every change has exactly one audit and exact output value",
                "Per-column initial/added/final reconciliation", "Native internal reference values",
                "Reference availability and provenance", "Contract/project assignment coverage",
            ), 1)
        }

    def fail(self, number, detail):
        item = self.items[str(number)]
        item["status"] = "FAIL"
        item["failure_count"] += 1
        if len(item["examples"]) < LIMIT:
            item["examples"].append(detail)

    def review(self, number, detail):
        item = self.items[str(number)]
        if item["status"] != "FAIL":
            item["status"] = "REVIEW"
        item.setdefault("limitations", []).append(detail)


def payload_hash(archive, name):
    digest = sha256()
    with archive.open(name) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def outside_rows_hash(archive):
    """Hash sheet bytes outside row elements, using bounded streaming buffers."""
    digest = sha256()
    buffer = b""
    in_row = False
    with archive.open(MAIN) as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            buffer += chunk
            while buffer:
                if not in_row:
                    start = ROW_START.search(buffer)
                    if start is None:
                        if chunk:
                            digest.update(buffer[:-128])
                            buffer = buffer[-128:]
                        else:
                            digest.update(buffer)
                            buffer = b""
                        break
                    digest.update(buffer[:start.start()])
                    buffer = buffer[start.start():]
                    in_row = True
                close = ROW_END.search(buffer)
                opening_end = buffer.find(b">")
                self_close = opening_end >= 0 and buffer[opening_end - 1:opening_end] == b"/"
                if self_close:
                    buffer = buffer[opening_end + 1:]
                    in_row = False
                elif close:
                    buffer = buffer[close.end():]
                    in_row = False
                else:
                    if not chunk:
                        raise ValueError("Unterminated journal row")
                    break
            if not chunk:
                break
    return digest.hexdigest()


def cells(raw):
    result = {}
    row_address = re.search(rb'<(?:\w+:)?row\b[^>]*\br="([0-9]+)"', raw)
    if row_address is None:
        raise ValueError("Row XML has no explicit row number")
    for match in CELL.finditer(raw):
        address = ADDRESS.search(match.group())
        if address is None:
            raise ValueError("Cell XML has no explicit address")
        if int(address[2]) != int(row_address[1]):
            raise ValueError(f"Cell address {address[0]!r} does not belong to its row")
        column = address[1].decode("ascii")
        if column in result:
            raise ValueError(f"Duplicate cell column {column}")
        result[column] = match.group()
    return result


def without_cells(raw, columns):
    def replace(match):
        address = ADDRESS.search(match.group())
        return b"" if address and address[1].decode("ascii") in columns else match.group()
    return CELL.sub(replace, raw)


def sheet_manifest(archive):
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {}
    for rel in rels:
        target = rel.get("Target", "")
        path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        targets[rel.get("Id")] = path
    return [(s.get("name"), s.get("sheetId"), s.get(RID), targets.get(s.get(RID)))
            for s in workbook.findall(f"{{{NS}}}sheets/{{{NS}}}sheet")]


def same_source(filename, source):
    return filename.replace("\\", "/").rsplit("/", 1)[-1].casefold() == source.name.casefold()


def load_audit(path, results):
    applied = {}
    statuses = defaultdict(Counter)
    required = {"source_row", "target_column", "old_value", "new_value", "reference_file", "reference_sheet", "reference_row", "match_key", "method", "status"}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or ())
        if missing:
            results.fail(9, {"missing_audit_columns": sorted(missing)})
            return applied, statuses
        for line, record in enumerate(reader, 2):
            try:
                row = int(record["source_row"])
                column = record["target_column"]
                key = (row, column)
                status = record["status"]
                statuses[column][status] += 1
                if row < 6 or column not in TARGETS:
                    results.fail(9, {"line": line, "invalid_target": list(key)})
                if status not in STATUSES:
                    results.fail(9, {"line": line, "unauthorized_status": status})
                if not is_blank(record["old_value"]) or is_blank(record["new_value"]):
                    results.fail(10, {"line": line, "invalid_old_or_new_value": list(key)})
                if key in applied:
                    results.fail(9, {"line": line, "duplicate": list(key)})
                    continue
                applied[key] = Applied(record["new_value"], record["reference_file"], record["reference_sheet"], record["reference_row"], record["match_key"], record["method"], status)
            except (ValueError, TypeError, KeyError) as exc:
                results.fail(9, {"line": line, "error": str(exc)})
    return applied, statuses


def check_references(archive, source, applied, shared, manifest, results):
    native_columns = {
        "بودجه 1404 + مراکز هزینه": {"AF": "F", "AG": "G", "AH": "H", "AI": "I"},
        "واحد سازمانی": {"AD": "B", "AE": "C"},
    }
    wanted = defaultdict(dict)
    native = external = missing = 0
    for key, item in applied.items():
        if not all((item.file, item.sheet, item.reference, item.match_key, item.method)):
            missing += 1
            results.fail(14, {"cell": list(key), "missing_provenance": True})
        if same_source(item.file, source):
            native += 1
            if not re.fullmatch(r"[A-Z]+[1-9][0-9]*", item.reference):
                results.fail(13, {"cell": list(key), "invalid_reference": item.reference})
                continue
            expected_column = native_columns.get(item.sheet, {}).get(key[1])
            if item.sheet in native_columns and (
                expected_column is None or re.match(r"[A-Z]+", item.reference)[0] != expected_column
            ):
                results.fail(13, {"cell": list(key), "sheet": item.sheet, "reference": item.reference, "required_reference_column": expected_column})
            if key[1] == "AM" and (
                item.sheet != "کدینگ جامع 1404 شهرداری" or item.reference != f"O{key[0]}"
            ):
                results.fail(13, {"cell": list(key), "sheet": item.sheet, "reference": item.reference, "required_reference": f"کدینگ جامع 1404 شهرداری!O{key[0]}"})
            values = wanted[item.sheet].setdefault(item.reference, set())
            values.add(item.value)
        else:
            external += 1
    sheets = {name: path for name, _, _, path in manifest}
    for sheet, references in wanted.items():
        if sheet not in sheets:
            results.fail(13, {"missing_reference_sheet": sheet, "references": len(references)})
            continue
        by_row = defaultdict(dict)
        for address, expected in references.items():
            match = re.fullmatch(r"([A-Z]+)([0-9]+)", address)
            by_row[int(match[2])][match[1]] = (address, expected)
        for row, raw in iter_raw_rows(archive, sheets[sheet]):
            requested = by_row.pop(row, None)
            if requested:
                values = decode_row(raw, shared)
                for column, (address, expected) in requested.items():
                    if expected != {values.get(column)}:
                        results.fail(13, {"sheet": sheet, "reference": address, "expected": sorted(expected), "actual": values.get(column)})
            if not by_row:
                break
        for row, requested in by_row.items():
            for address, _ in requested.values():
                results.fail(13, {"sheet": sheet, "missing_reference": address})
    results.items["13"]["applied_native_references"] = native
    results.items["14"].update(applied_external_references=external, missing_provenance=missing)
    if external:
        results.review(14, {"unavailable_external_reference_cells": external, "reason": "CLI supplies no external reference workbooks; external cell values are not verified."})


def verify(source, output, audit, stats_path, results):
    applied, statuses = load_audit(audit, results)
    stats = json.loads(stats_path.read_text(encoding="utf-8-sig"))
    initial = Counter({c: 0 for c in TARGETS})
    final = initial.copy()
    added = initial.copy()
    identities = {"source_B_populated": 0, "output_B_populated": 0, "source_C_E_complete": 0, "output_C_E_complete": 0}
    matched = 0
    data_rows = source_rows = output_rows = 0
    with ZipFile(source) as original, ZipFile(output) as enriched:
        for label, archive in (("source", original), ("output", enriched)):
            duplicate_members = [n for n, count in Counter(archive.namelist()).items() if count > 1]
            if duplicate_members:
                results.fail(1, {"file": label, "duplicate_zip_members": duplicate_members[:LIMIT]})
            bad = archive.testzip()
            if bad:
                results.fail(1, {"file": label, "crc_failure": bad})
        old_names, new_names = set(original.namelist()), set(enriched.namelist())
        for member in sorted(old_names):
            if member not in new_names:
                results.fail(2, {"missing_original_member": member})
            elif member not in PERMITTED and payload_hash(original, member) != payload_hash(enriched, member):
                results.fail(2, {"changed_original_member": member})
        old_manifest, new_manifest = sheet_manifest(original), sheet_manifest(enriched)
        if new_manifest[:len(old_manifest)] != old_manifest:
            results.fail(3, {"original": old_manifest, "output": new_manifest})
        if len({s[0] for s in new_manifest}) != len(new_manifest):
            results.fail(3, "Duplicate output sheet names")
        if outside_rows_hash(original) != outside_rows_hash(enriched):
            results.fail(6, "Journal XML outside row elements changed")
        source_shared, output_shared = load_shared(original), load_shared(enriched)
        paired = zip_longest(iter_raw_rows(original, MAIN), iter_raw_rows(enriched, MAIN))
        for left, right in paired:
            source_rows += left is not None
            output_rows += right is not None
            if left is None or right is None or left[0] != right[0]:
                results.fail(4, {"source_row": left[0] if left else None, "output_row": right[0] if right else None})
                continue
            row, before = left
            after = right[1]
            if row < 6:
                if before != after:
                    results.fail(6, {"header_row_changed": row})
                continue
            data_rows += 1
            old_values, new_values = decode_row(before, source_shared), decode_row(after, output_shared)
            old_cells, new_cells = cells(before), cells(after)
            changed = {c for c in old_cells.keys() | new_cells.keys() if old_cells.get(c) != new_cells.get(c)}
            audited_columns = set()
            for column in old_cells.keys() | new_cells.keys():
                key = (row, column)
                item = applied.get(key)
                if item is not None:
                    matched += 1
                    audited_columns.add(column)
                    if not is_blank(old_values.get(column)) or FORMULA.search(old_cells.get(column, b"")):
                        results.fail(10, {"cell": list(key), "original_value": old_values.get(column), "original_formula": bool(FORMULA.search(old_cells.get(column, b"")))})
                    if column not in changed or new_values.get(column) != item.value or FORMULA.search(new_cells.get(column, b"")):
                        results.fail(11, {"cell": list(key), "expected": item.value, "actual": new_values.get(column), "xml_changed": column in changed})
                if column in changed:
                    if column not in TARGETS:
                        results.fail(6, {"non_target_cell": list(key)})
                    if item is None:
                        results.fail(11, {"unaudited_change": list(key)})
                    if not is_blank(old_values.get(column)) or FORMULA.search(old_cells.get(column, b"")):
                        results.fail(5, {"populated_or_formula_cell_changed": list(key)})
            if without_cells(before, audited_columns) != without_cells(after, audited_columns):
                results.fail(6, {"unaudited_row_bytes_changed": row})
            for column in ("B", "C", "E"):
                if old_cells.get(column) != new_cells.get(column) or old_values.get(column) != new_values.get(column):
                    results.fail(7, {"identity_cell_changed": f"{column}{row}"})
            for label, values in (("source", old_values), ("output", new_values)):
                identities[f"{label}_B_populated"] += not is_blank(values.get("B"))
                identities[f"{label}_C_E_complete"] += all(not is_blank(values.get(c)) for c in ("C", "E"))
            for column in ("Q", "R"):
                if old_cells.get(column) != new_cells.get(column) or old_values.get(column) != new_values.get(column):
                    results.fail(8, {"amount_cell_changed": f"{column}{row}"})
            for column in TARGETS:
                old_blank, new_blank = is_blank(old_values.get(column)), is_blank(new_values.get(column))
                initial[column] += not old_blank
                final[column] += not new_blank
                added[column] += old_blank and not new_blank
        if matched != len(applied):
            results.fail(11, {"audit_cells": len(applied), "encountered_audit_cells": matched, "missing_count": len(applied) - matched})
        if stats.get("rows") != data_rows:
            results.fail(12, {"stats_rows": stats.get("rows"), "observed_rows": data_rows})
        for column in TARGETS:
            observed = {"initial_population": initial[column], "added": added[column]}
            for field, count in observed.items():
                reported = stats.get(field, {}).get(column)
                if reported != count:
                    results.fail(12, {"column": column, "metric": field, "stats": reported, "observed": count})
            if final[column] != initial[column] + added[column]:
                results.fail(12, {"column": column, "initial": initial[column], "added": added[column], "final": final[column]})
            audit_count = sum(statuses[column].values())
            if audit_count != added[column]:
                results.fail(12, {"column": column, "audit_count": audit_count, "added": added[column]})
            reported_status = stats.get("status_counts", {}).get(column, {})
            applied_status = {k: v for k, v in reported_status.items() if k in STATUSES and v}
            if applied_status != dict(statuses[column]):
                results.fail(12, {"column": column, "stats_applied_status_counts": applied_status, "audit_status_counts": dict(statuses[column])})
            status_total = sum(reported_status.values())
            expected_empty = data_rows - initial[column]
            if status_total != expected_empty:
                results.fail(12, {"column": column, "stats_all_status_count": status_total, "initially_empty_cells": expected_empty})
            if sum(applied_status.values()) != added[column]:
                results.fail(12, {"column": column, "stats_applied_count": sum(applied_status.values()), "observed_added": added[column]})
            if "final_population" in stats and stats["final_population"].get(column) != final[column]:
                results.fail(12, {"column": column, "stats_final": stats["final_population"].get(column), "observed_final": final[column]})
        check_references(original, source, applied, source_shared, old_manifest, results)
    results.items["4"].update(source_xml_rows=source_rows, output_xml_rows=output_rows, data_rows=data_rows)
    results.items["7"].update(identities)
    coverage = {c: {"initial": initial[c], "added": added[c], "final": final[c]} for c in ("AN", "AO", "AP", "AQ")}
    results.items["15"]["coverage"] = coverage
    for name, columns in (("contracts", ("AN", "AO")), ("projects", ("AP", "AQ"))):
        if not any(added[c] for c in columns):
            results.review(15, {"dimension": name, "reason": "No new assignments; integrity checks do not establish that an authoritative matching source exists or that this dimension is complete."})
    return {"rows": data_rows, "audit_cells": len(applied), "initial_population": dict(initial), "added": dict(added), "final_population": dict(final), "status_counts": {c: dict(statuses[c]) for c in TARGETS}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "output", "audit", "stats", "result"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    # Never overwrite an input workbook or evidence file with the result JSON.
    if args.result.resolve() in {p.resolve() for p in (args.source, args.output, args.audit, args.stats)}:
        parser.error("--result must differ from every input path")
    results = Results()
    counts = {}
    try:
        counts = verify(args.source, args.output, args.audit, args.stats, results)
    except Exception as exc:
        results.fail(1, {"verification_aborted": type(exc).__name__, "error": str(exc)})
        for item in results.items.values():
            if item["status"] == "PASS":
                item["status"] = "REVIEW"
                item["limitations"] = ["Verification aborted; this check was not fully completed."]
    outcome = "FAIL" if any(x["status"] == "FAIL" for x in results.items.values()) else "REVIEW" if any(x["status"] == "REVIEW" for x in results.items.values()) else "PASS"
    report = {"status": outcome, "source": str(args.source), "output": str(args.output), "audit": str(args.audit), "stats": str(args.stats), "checks": results.items, "counts": counts, "failure_example_limit_per_check": LIMIT, "limits": ["Native reference cell values are verified exactly; this does not independently prove business-rule authority or semantic correctness of a match.", "Identity population counts are row occurrences, not distinct documents; ordered cell XML/value equality proves preservation.", "Population treats whitespace-only cached values as blank; formulas are never eligible for mutation regardless of their cached value."]}
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": outcome, "result": str(args.result), "counts": counts}, ensure_ascii=False))
    return 1 if outcome == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
