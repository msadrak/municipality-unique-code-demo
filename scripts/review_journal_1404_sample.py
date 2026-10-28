"""Review enrichment sample evidence; no human or committee approval is implied."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata


STRATA = {
    "payroll": ("حقوق", "دستمزد", "پرسنل", "کارکنان", "payroll"),
    "urban_services": ("خدمات شهری", "پسماند", "نظافت", "فضای سبز", "urban services"),
    "construction": ("عمران", "احداث", "ساخت", "آسفالت", "construction"),
    "culture": ("فرهنگ", "ورزش", "کتابخانه", "culture"),
    "traffic": ("ترافیک", "حمل و نقل", "پارکینگ", "traffic"),
    "grants": ("کمک", "انتقال به", "وابسته", "i114", "i115", "grants"),
    "administration": ("اداری", "مدیریت", "پشتیبانی", "administration"),
    "project": ("پروژه", "طرح", "project"),
    "contract": ("قرارداد", "پیمان", "contract"),
    "revenue_boundary": ("درآمد", "عوارض", "revenue"),
}
DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def norm(value):
    text = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join(text.translate(DIGITS).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ").lower().split())


def contains(text, words):
    return any(norm(word) in text for word in words)


def numeric_title(value):
    text = norm(value)
    return bool(text) and bool(re.fullmatch(r"[\d\s.,/+:_-]+", text))


def expense_class(value):
    return norm(value) in {"6", "6.0"}


def review(entries):
    if not isinstance(entries, list):
        raise ValueError("Sample must be a JSON list of row entries")
    grouped = {}
    duplicates = 0
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("source_values"), dict):
            raise ValueError("Every sample entry requires source_row and source_values dictionary")
        number = entry.get("source_row")
        if isinstance(number, bool) or not isinstance(number, int) or number < 6:
            raise ValueError("source_row must be an integer >= 6")
        changes = entry.get("changes")
        if not isinstance(changes, list) or not all(isinstance(c, dict) for c in changes):
            raise ValueError("Every sample entry requires a changes list of audit dictionaries")
        if not changes:
            continue
        if number in grouped:
            previous = grouped[number]
            if previous["source_values"] != entry["source_values"] or previous.get("reference_budget") != entry.get("reference_budget"):
                raise ValueError(f"Conflicting duplicate sample evidence for source row {number}")
            previous["changes"].extend(changes)
            duplicates += 1
        else:
            grouped[number] = {**entry, "changes": list(changes)}

    findings, rows = [], []
    strata_counts = Counter({key: 0 for key in STRATA})
    method_counts, confidence_counts = Counter(), Counter()
    for number, entry in sorted(grouped.items()):
        source, changes = entry["source_values"], entry["changes"]
        reference = entry.get("reference_budget") or {}
        if not isinstance(reference, dict):
            raise ValueError(f"reference_budget must be a dictionary or null: row {number}")
        native = " ".join(norm(source.get(column)) for column in ("N", "O", "P", "T", "W"))
        labels = " ".join(norm(change.get("new_value")) for change in changes)
        strata = [key for key, words in STRATA.items() if contains(native + " " + labels, words)]
        if norm(source.get("I")) in {"114", "115", "114.0", "115.0"} and "grants" not in strata:
            strata.append("grants")
        if norm(source.get("X")) and not expense_class(source.get("X")) and "revenue_boundary" not in strata:
            # Boundary includes balance-sheet rows; it does not reclassify them as revenue.
            strata.append("revenue_boundary")
        strata_counts.update(strata)
        issues = []

        def issue(decision, code, explanation, change=None):
            item = {"source_row": number, "decision": decision, "code": code, "explanation": explanation}
            if change is not None:
                item["target_column"] = change.get("target_column")
                item["method"] = change.get("method")
            issues.append(item)
            findings.append(item)

        ref_text = " ".join(norm(value) for value in reference.values())
        for change in changes:
            method = str(change.get("method") or "UNSPECIFIED")
            confidence = str(change.get("confidence") or "UNSPECIFIED")
            method_counts[method] += 1
            confidence_counts[confidence] += 1
            field = norm(change.get("field"))
            reason = norm(change.get("reason"))
            key = norm(change.get("match_key"))
            value = change.get("new_value")
            budget_map = method == "native_budget_account_composite" or contains(field, ("budget", "بودجه", "cost center", "cost_center", "مرکز هزینه"))
            if budget_map and not expense_class(source.get("X")):
                issue("FAIL", "EXPENSE_MAPPING_OUTSIDE_CLASS_6", "Expense/budget assignment conflicts with authoritative native source X (not 6).", change)
            if norm(change.get("old_value")):
                issue("FAIL", "POPULATED_TARGET_REPLACED", "Audit indicates a populated native target was replaced.", change)
            if not norm(value):
                issue("FAIL", "EMPTY_ENRICHMENT", "Audit new value is blank; this is not an enrichment.", change)
            name_method = "name" in method.lower() or contains(reason, ("name match", "name-to", "تطبیق نام"))
            title_field = contains(field, ("title", "name", "عنوان", "نام"))
            if name_method and title_field and numeric_title(value):
                issue("FAIL", "NUMERIC_NAME_RESULT", "Name-dependent mapping produced a numeric title, not a native authoritative name.", change)
            native_name_columns = [column for column in ("AF", "AG", "AH", "AI") if column.lower() in key]
            numeric_native_names = [column for column in native_name_columns if numeric_title(source.get(column))]
            if name_method and (numeric_title(key) or numeric_native_names):
                issue("REVIEW", "NUMERIC_NAME_MATCH_KEY", "Name-dependent mapping relies on a numeric-only key/native label; an authoritative name is not observable.", change)
            if not all(norm(change.get(k)) for k in ("reference_file", "reference_sheet", "reference_row", "match_key", "reason")):
                issue("REVIEW", "INCOMPLETE_REFERENCE_EVIDENCE", "Audit lacks a reference locator, match key, or mapping reason.", change)
            if contains(reason + " " + ref_text, ("نیازمند تصمیم کارشناسی",)):
                issue("FAIL", "UNRESOLVED_EXPERT_DECISION", "Mapping evidence explicitly requires an expert decision and cannot authorize a fill.", change)
            if budget_map:
                cc_names = " ".join(norm(reference.get(column)) for column in ("l1_name", "l2_name", "owner"))
                description = norm(reference.get('description'))
                native_l2 = norm(reference.get('l2_name'))
                if 'جبران خدمات' in native_l2 and norm(source.get('I')) in {'112', '114', '115'}:
                    issue('FAIL', 'CONTRACT_SERVICE_IS_NOT_PAYROLL', 'Contracted or transfer service cannot authorize direct employee payroll center.', change)
                if 'احداث' in native_l2 and contains(description, ('کرایه', 'اجاره', 'تخفیف', 'کمک به افراد', 'تجهیزات اداری')):
                    issue('FAIL', 'NONCONSTRUCTION_TO_CONSTRUCTION', 'Rental, relief or office equipment mapped to construction.', change)
                if 'مالی، خزانه' in native_l2 and not contains(description, ('مالی', 'بانک', 'خزانه', 'حسابداری', 'حسابرسی')):
                    issue('FAIL', 'NONFINANCE_TO_TREASURY', 'Budget line does not substantiate treasury-center assignment.', change)
                cc_payroll = contains(norm(value) + " " + reason + " " + cc_names, STRATA["payroll"])
                grants = (norm(source.get("I")) in {"114", "115", "114.0", "115.0"}
                          or contains(native + " " + ref_text, ("i114", "i115", "کمک به سازمان", "کمک به شرکت")))
                # W is the native budget code, not an expenditure-type label.
                budget_code = norm(reference.get("budget_code"))
                native_budget = bool(budget_code) and norm(source.get("W")) == budget_code and method == "native_budget_account_composite"
                if grants and cc_payroll and not native_budget:
                    issue("FAIL", "PAYROLL_CC_ON_AFFILIATED_TRANSFER", "Payroll assignment to an affiliated/grant transfer lacks an explicit native budget-code match.", change)
                context = norm(source.get("N"))
                for label, words in (("bank", ("بانک", "bank")), ("tax", ("مالیات", "tax"))):
                    if contains(context, words) and not contains(ref_text + " " + reason, words):
                        issue("REVIEW", "ACCOUNT_REFERENCE_CONTEXT_MISMATCH", f"Native account N has {label} context absent from budget reference/reason; compatibility needs source review.", change)
                if not reference and method == "native_budget_account_composite":
                    issue("REVIEW", "MISSING_BUDGET_REFERENCE", "Composite expense mapping has no reference_budget evidence to inspect.", change)
        decision = "FAIL" if any(i["decision"] == "FAIL" for i in issues) else "REVIEW" if issues else "PASS"
        rows.append({"source_row": number, "source_evidence": source, "reference_budget": reference or None,
                     "strata": strata, "stratum_hint": entry.get("stratum"), "changes": changes,
                     "decision": decision, "explanation": [i["explanation"] for i in issues] or [
                         "No specified semantic contradiction detected in supplied native evidence and audit references; this is an automated sample review, not source-master verification or committee approval."]})
    unavailable = [key for key, count in strata_counts.items() if not count]
    if len(rows) < 100:
        findings.append({"decision": "REVIEW", "code": "LIMITED_SAMPLE", "explanation": f"Only {len(rows)} distinct enriched rows were supplied; at least 100 are required when available. Total enriched population is not supplied, so availability cannot be verified."})
    if unavailable:
        findings.append({"decision": "REVIEW", "code": "UNAVAILABLE_STRATA", "explanation": "No observable source/new-label evidence for: " + ", ".join(unavailable) + ". Missing coverage is not fabricated."})
    if duplicates:
        findings.append({"decision": "REVIEW", "code": "DUPLICATE_SAMPLE_ROWS", "explanation": f"Merged {duplicates} duplicate entries; they do not increase distinct row coverage."})
    overall = "FAIL" if any(f["decision"] == "FAIL" for f in findings) else "REVIEW" if findings else "PASS"
    return {"records_reviewed": len(rows), "strata_counts": dict(strata_counts), "method_counts": dict(method_counts),
            "confidence_counts": dict(confidence_counts), "findings": findings, "rows": rows,
            "unavailable_strata": unavailable, "overall_status": overall}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        entries = json.loads(args.sample.read_text(encoding="utf-8-sig"))
        report = review(entries)
    except (OSError, ValueError) as error:
        parser.exit(2, f"Sample review input error: {error}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
