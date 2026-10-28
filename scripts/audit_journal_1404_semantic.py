from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

CC = ('AF', 'AG', 'AH', 'AI')
SOURCE = ('I', 'N', 'O', 'P', 'T', 'W', 'X')
CATEGORIES = {
    'payroll_benefits': ('حقوق', 'دستمزد', 'مزایا', 'رفاه', 'جبران خدمات', 'کارکنان', 'کارگران'),
    'outsourced_services': ('پیمانکار', 'برون سپاری', 'خرید خدمات', 'شرکت', 'قرارداد'),
    'construction_infrastructure': ('احداث', 'ساخت', 'عمران', 'تملک', 'آسفالت', 'پل', 'جدول', 'پیاده رو'),
    'transportation': ('حمل و نقل', 'ترافیک', 'پارکینگ', 'پایانه', 'اتوبوس', 'مترو', 'تقاطع'),
    'urban_services': ('فضای سبز', 'پسماند', 'نظافت', 'رفت و روب', 'آتش', 'ایمنی', 'پارک'),
    'culture': ('فرهنگ', 'کتابخانه', 'موزه', 'ورزش', 'هنر', 'گردشگری', 'علمی'),
    'transfers': ('کمک', 'یارانه', 'حمایت', 'انتقال'),
    'administration': ('اداری', 'پشتیبانی', 'مدیریت', 'تدارکات', 'تجهیزات', 'ملزومات'),
}
DOMAINS = {
    'green_space': ('فضای سبز', 'درخت', 'باغ', 'نهال'),
    'waste_cleaning': ('پسماند', 'رفت و روب', 'نظافت', 'زباله'),
    'transport': ('ترافیک', 'اتوبوس', 'مترو', 'پایانه', 'حمل و نقل', 'پارکینگ'),
    'culture': ('فرهنگ', 'کتابخانه', 'موزه', 'هنری', 'علمی'),
    'sports': ('ورزش', 'استخر'),
    'roads': ('آسفالت', 'معابر', 'پیاده رو', 'روسازی', 'جدول گذاری'),
    'buildings': ('ساختمان', 'ابنیه'),
    'finance': ('خزانه', 'حسابرسی', 'حسابداری', 'تسهیلات', 'وام'),
}

def norm(value):
    s = '' if value is None else str(value)
    s = s.translate(str.maketrans({'ي': 'ی', 'ك': 'ک', '\u200c': ' ', '\xa0': ' '}))
    return ' '.join(s.split()).strip()

def has(text, words):
    return any(norm(word) in text for word in words)

def labels(text, groups):
    return {name for name, words in groups.items() if has(text, words)}

def read_budget(source):
    wb = openpyxl.load_workbook(source, read_only=True, data_only=True)
    sheet = wb['بودجه 1404 + مراکز هزینه']
    result = {}
    by_code = defaultdict(list)
    names = ('budget_code', 'description', 'type', 'domain', 'subject', 'l1_code', 'l1_name', 'l2_code', 'l2_name', 'owner')
    for rn, row in enumerate(sheet.iter_rows(max_col=10, values_only=True), 1):
        if rn < 3 or row[0] is None:
            continue
        rec = dict(zip(names, row))
        rec['reference_row'] = rn
        result[rn] = rec
        by_code[norm(row[0])].append(rec)
    wb.close()
    return result, by_code

def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row[key], ensure_ascii=False, sort_keys=True) if isinstance(row.get(key), (dict, list)) else row.get(key, '') for key in fields})

def main():
    parser = argparse.ArgumentParser(description='Independent semantic review; never changes any workbook.')
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    budget_rows, by_budget = read_budget(args.source)
    con = sqlite3.connect(args.db.resolve().as_uri() + '?mode=ro', uri=True)
    findings, candidates = [], []
    samples = {}
    buckets = defaultdict(list)
    first_applied = []
    counts, status_counts, category_counts, rule_counts = Counter(), Counter(), Counter(), Counter()
    applied_rule_counts = Counter()
    fields = ['source_row', 'assignment_origin', 'source_evidence', 'original_cc', 'enriched_cc', 'v1_applied_evidence', 'v1_statuses', 'native_budget_references', 'risk_categories', 'applicable_rules', 'independent_status', 'acceptance', 'evidence', 'corrective_authority_needed']
    fields += ['source_workbook', 'source_sheet', 'lookup_evidence_status', 'financial_domain_approval']
    for source_row, original_json, enriched_json, applied_json, unresolved_json in con.execute('SELECT source_row,original,enriched,applied,unresolved FROM journal ORDER BY source_row'):
        original, enriched, applied = map(json.loads, (original_json, enriched_json, applied_json))
        changes = [rec for rec in applied if rec.get('target_column') in CC]
        existing = any(norm(original.get(col)) for col in CC)
        assigned = any(norm(enriched.get(col)) for col in CC)
        counts['all_source_rows'] += 1
        if not assigned:
            continue
        counts['all_cc_present_rows'] += 1
        if changes:
            counts['cc_applied_rows'] += 1
            counts['cc_applied_cells'] += len(changes)
            counts['newly_recovered_code_rows'] += int(any(rec.get('target_column') in ('AF', 'AH') for rec in changes))
            counts['code_recovery_from_existing_name_rows'] += int(any(rec.get('method') == 'native_existing_name_to_code' for rec in changes))
        elif existing:
            counts['existing_cc_only_rows'] += 1
        if existing and norm(original.get('X')) in ('4', '4.0'):
            counts['revenue_existing_cc_rows_not_policy_validated'] += 1
        refs = {}
        for change in changes:
            if change.get('reference_sheet') == 'بودجه 1404 + مراکز هزینه':
                for value in re.findall(r'\d+', str(change.get('reference_row', ''))):
                    if int(value) in budget_rows:
                        refs[int(value)] = budget_rows[int(value)]
        for ref in by_budget.get(norm(original.get('W')), []):
            refs[ref['reference_row']] = ref
        matching = [ref for ref in refs.values() if all(not norm(enriched.get(col)) or norm(enriched.get(col)) == norm(ref[key]) for col, key in zip(CC, ('l1_code', 'l1_name', 'l2_code', 'l2_name')))]
        effective_refs = matching or list(refs.values())
        source_text = norm(' '.join(norm(original.get(col)) for col in ('N', 'O', 'P', 'T')))
        purpose = norm(' '.join(norm(original.get(col)) for col in ('O', 'P')))
        cc_text = norm(' '.join(norm(enriched.get(col)) for col in ('AG', 'AI')))
        budget_text = norm(' '.join(norm(ref.get(key)) for ref in effective_refs for key in ('description', 'type', 'domain', 'subject')))
        categories = labels(source_text + ' ' + budget_text + ' ' + cc_text, CATEGORIES)
        if len(categories) > 1:
            categories.add('overlapping_domains')
        rules, evidence = [], []
        fail = False
        def flag(code, explanation, contradiction=False):
            nonlocal fail
            rules.append(code)
            evidence.append(explanation)
            fail = fail or contradiction
        if changes and norm(original.get('X')) not in ('6', '6.0'):
            flag('CC_FILL_OUTSIDE_EXPENSE_CLASS', 'Applied expense center despite source X=' + norm(original.get('X')), True)
        if changes and not matching:
            direct_conflict = any(change.get('method') == 'native_budget_account_composite' and refs and not any(norm(change.get('new_value')) == norm(ref[dict(zip(CC, ('l1_code', 'l1_name', 'l2_code', 'l2_name')))[change['target_column']]]) for ref in refs.values()) for change in changes)
            flag('ASSIGNMENT_REFERENCE_CC_MISMATCH', 'No cited/native budget reference agrees with all populated enriched CC fields; inherited cross-level mismatch is REVIEW unless an applied field itself contradicts every reference.', direct_conflict)
        if existing and not changes and not matching:
            flag('EXISTING_CC_REFERENCE_NOT_CORROBORATED', 'Existing center retained; native budget evidence does not corroborate its complete code/name combination.')
        if existing and norm(original.get('X')) in ('4', '4.0'):
            flag('EXISTING_REVENUE_CC_USAGE_POLICY_UNVERIFIED', 'Existing source class 4 revenue row has cost-center fields; preserved native usage is not established as either valid or prohibited without field-usage policy.')
        payroll = has(cc_text, ('جبران خدمات', 'منابع انسانی'))
        l2_text = norm(enriched.get('AI'))
        description_text = norm(' '.join(norm(ref.get('description')) for ref in effective_refs))
        if payroll and has(description_text, ('تسهیلات', 'بازپرداخت', 'وام', 'سود بانکی', 'دیون بانکی')):
            flag('NATIVE_FINANCIAL_BUDGET_TO_PAYROLL', 'Native budget description identifies loans/repayment/financing while assigned center identifies payroll; distinguish employee welfare loans from municipal financing using approved responsibility evidence.')
        if payroll and norm(original.get('I')) in ('132', '132.0') and has(norm(original.get('N')), ('وام', 'تسهیلات', 'بازپرداخت', 'سود')):
            flag('LOAN_REPAYMENT_ACCOUNT_TO_PAYROLL', 'Source I=132 plus N financing terminology while CC describes human resources; approved employee-loan versus municipal-debt treatment is not established.')
        if has(l2_text, ('احداث', 'توسعه', 'تکمیل')) and has(description_text, ('اجاره', 'نگهداری', 'تعمیرات', 'تجهیزات', 'ملزومات')) and not has(description_text, ('احداث', 'ساخت', 'تکمیل')):
            flag('NATIVE_OPERATIONAL_BUDGET_TO_EXECUTION_CENTER', 'Native budget description is rental/maintenance/equipment rather than construction; the native reference itself does not establish construction-center eligibility.')
        if has(description_text, ('کمک به', 'حمایت از', 'یارانه')) and has(l2_text, ('احداث', 'نگهداری', 'پایانه', 'نظافت', 'عملیات')):
            flag('NATIVE_SUPPORT_BUDGET_TO_DIRECT_EXECUTION', 'Native budget reference describes a transfer/support while L2 describes direct execution; recipient and executing owner need independent authority.')
        if has(l2_text, ('ورزش', 'ورزشی')) and has(description_text, ('موزه', 'کتابخانه', 'خانه های علمی', 'علمی')):
            flag('NATIVE_CULTURAL_BUDGET_TO_SPORTS', 'Native description identifies cultural/scientific facilities but L2 identifies sports; multi-use purpose must be documented.')
        loans = has(purpose + ' ' + norm(original.get('N')), ('تسهیلات', 'بازپرداخت وام', 'اصل و سود', 'اقساط وام', 'وام دریافتی', 'بدهی بانکی'))
        if payroll and loans:
            flag('FINANCIAL_LIABILITY_TO_PAYROLL', 'Account/purpose explicitly identifies loans or financial liability while center identifies payroll/human resources; employee-loan and employer-benefit authority must be distinguished.')
        if payroll and has(source_text, ('کمک به سازمان', 'کمک به شرکت', 'یارانه سازمان')):
            flag('AFFILIATED_SUPPORT_TO_PAYROLL', 'Support to an affiliated organization/company does not prove direct municipal employee compensation.')
        if payroll and has(purpose, ('پیمانکار', 'خرید خدمات', 'برون سپاری')):
            flag('OUTSOURCED_SERVICE_TO_PAYROLL', 'Line purpose indicates outsourced service/contractor rather than direct employee compensation; contractor staff and municipal payroll require distinct evidence.')
        building = has(cc_text, ('ساختمان', 'ابنیه'))
        if building and has(purpose, ('تجهیزات', 'ملزومات', 'رایانه', 'کامپیوتر', 'ماشین آلات', 'خرید خودرو')) and not has(purpose, ('احداث', 'ساخت', 'بازسازی', 'تعمیر ساختمان')):
            flag('EQUIPMENT_TO_BUILDING_CENTER', 'Equipment/procurement purpose assigned to a building center; asset installation/project scope is not established by a unique budget join.')
        construction_purpose = has(purpose, ('احداث', 'تکمیل')) or bool(re.search(r'(?<!\w)ساخت(?!\w)', purpose))
        if building and construction_purpose and has(l2_text, ('نگهداری', 'تعمیر')):
            flag('CONSTRUCTION_TO_BUILDING_MAINTENANCE', 'O/P explicitly describes construction while assigned L2 describes maintenance; project lifecycle and capitalization scope require approved responsibility determination.')
        operational_purpose = has(purpose, ('نگهداری', 'اجاره', 'خدمات')) or bool(re.search(r'(?<!\w)جاری(?!\w)', purpose))
        if building and operational_purpose and has(budget_text, ('سرمایه', 'احداث')):
            flag('OPERATIONAL_SPENDING_TO_CAPITAL_BUILDING', 'Operational/rental/maintenance purpose conflicts with capital/construction reference context; project capitalization decision required.')
        if has(purpose, ('خرید ملزومات', 'ملزومات اداری', 'خرید تجهیزات', 'تدارکات', 'خرید کالا')) and has(cc_text, ('احداث', 'معابر', 'ترافیک', 'پایانه', 'فضای سبز')):
            flag('GENERAL_PROCUREMENT_TO_SPECIFIC_INFRASTRUCTURE', 'General procurement is assigned to a specific infrastructure/service center without explicit beneficiary/project attribution.')
        if has(source_text, ('کمک به سازمان', 'کمک به شرکت', 'حمایت از سازمان', 'کمک به موسسه')) and has(cc_text, ('احداث', 'نگهداری', 'پایانه', 'نظافت', 'اجرایی', 'عملیات')):
            flag('SUPPORT_TO_DIRECT_EXECUTION', 'Affiliated support is assigned to a direct execution/maintenance center; recipient subsidy versus executing cost owner is unresolved.')
        purpose_domains, ref_domains = labels(purpose, DOMAINS), labels(budget_text, DOMAINS)
        if purpose_domains and ref_domains and purpose_domains.isdisjoint(ref_domains):
            flag('PURPOSE_BUDGET_DOMAIN_DIVERGENCE', 'O/P domains=' + ','.join(sorted(purpose_domains)) + '; native budget domains=' + ','.join(sorted(ref_domains)) + '. Explicit multi-service/beneficiary evidence is required.')
        if has(cc_text, ('خزانه', 'مالی')) and has(purpose + ' ' + budget_text, ('ترافیک', 'حمل و نقل', 'پایانه', 'آسفالت')) and not has(purpose, ('تسهیلات', 'وام', 'حسابداری', 'بانک')):
            flag('SERVICE_PURPOSE_TO_FINANCE_CENTER', 'Transport/infrastructure purpose assigned to finance/treasury center; financial transaction mechanics do not establish service cost ownership.')
        if changes and not effective_refs:
            flag('NO_NATIVE_BUDGET_EVIDENCE', 'Center applied without independently observable native budget reference.')
        status = 'FAIL' if fail else 'REVIEW' if rules else 'NO_DETECTED_CONTRADICTION'
        status_counts[status] += 1
        if changes:
            counts['applied_' + status] += 1
            counts['applied_cells_' + status] += len(changes)
            for category in categories:
                category_counts[category] += 1
        for rule in set(rules):
            rule_counts[rule] += 1
            if changes:
                applied_rule_counts[rule] += 1
        row = dict(source_row=source_row, assignment_origin='NEW_CC_FILL_WITH_EXISTING_CONTEXT' if changes and existing else 'NEW_CC_FILL' if changes else 'EXISTING_UNCHANGED', source_evidence={col: original.get(col) for col in SOURCE}, original_cc={col: original.get(col) for col in CC}, enriched_cc={col: enriched.get(col) for col in CC}, v1_applied_evidence=changes, v1_statuses=sorted({rec.get('status', '') for rec in changes}), native_budget_references=list(refs.values()), risk_categories=sorted(categories), applicable_rules=sorted(set(rules)), independent_status=status, acceptance='HOLD_FOR_REVIEW' if rules else 'NO_AUTOMATED_OBJECTION_NOT_AUTHORITATIVE_APPROVAL', evidence=evidence or ['No configured contradiction detected. Unique budget matches and existing-name recovery are evidence, not approved responsibility rules.'], corrective_authority_needed='Source accounting owner and budget owner must confirm line purpose; approved cost-center steward must authorize allocation or source correction.' if rules else 'Approved scoped financial-event/cost-center rules remain necessary for authoritative acceptance.')
        row['source_workbook'] = str(args.source)
        row['source_sheet'] = 'کدینگ جامع 1404 شهرداری'
        row['lookup_evidence_status'] = 'NATIVE_CC_REFERENCE_CORROBORATED' if matching else 'NATIVE_CC_REFERENCE_NOT_CORROBORATED'
        row['financial_domain_approval'] = 'NOT_ESTABLISHED_BY_LOOKUP'
        if rules:
            findings.append(row)
        if changes:
            if len(first_applied) < 300:
                first_applied.append(row)
            for category in categories | {'all_applied'} | set(rules):
                if len(buckets[category]) < 40:
                    buckets[category].append(row)
        if changes and rules:
            candidate_refs = [ref for ref in by_budget.get(norm(original.get('W')), []) if labels(norm(ref.get('description')), DOMAINS) & purpose_domains and not payroll]
            tuples = {tuple(norm(ref.get(key)) for key in ('l1_code', 'l1_name', 'l2_code', 'l2_name')) for ref in candidate_refs}
            if len(tuples) == 1 and candidate_refs and any(norm(enriched.get(col)) != norm(candidate_refs[0][key]) for col, key in zip(CC, ('l1_code', 'l1_name', 'l2_code', 'l2_name'))):
                candidates.append({'source_row': source_row, 'current_cc': row['enriched_cc'], 'candidate_cc': {col: candidate_refs[0][key] for col, key in zip(CC, ('l1_code', 'l1_name', 'l2_code', 'l2_name'))}, 'evidence': 'Same W native candidate explicitly overlaps O/P service domain; this is a proposed candidate, not authority.', 'native_reference_rows': [ref['reference_row'] for ref in candidate_refs], 'required_authority': row['corrective_authority_needed'], 'status': 'PROPOSED_REVIEW_ONLY_NEVER_APPLIED'})
    con.close()
    for name in sorted(buckets):
        for row in buckets[name]:
            samples[row['source_row']] = row
    # Supplement with source-row ascending applied records, never fabricated rows.
    if len(samples) < 300:
        for row in first_applied:
            samples[row['source_row']] = row
            if len(samples) >= 300:
                break
    if len(samples) < min(300, counts['cc_applied_rows']):
        raise RuntimeError('Insufficient reproducible assignment sample.')
    sample_rows = [samples[key] for key in sorted(samples)]
    write_csv(args.output / 'Semantic_Cost_Center_Audit.csv', sample_rows, fields)
    write_csv(args.output / 'full_population_findings.csv', findings, fields)
    write_csv(args.output / 'proposed_cc_corrections.csv', candidates, ['source_row', 'current_cc', 'candidate_cc', 'evidence', 'native_reference_rows', 'required_authority', 'status'])
    metrics = {'counts': dict(counts), 'all_cc_population_status': dict(status_counts), 'applied_category_population': dict(category_counts), 'rule_affected_population': dict(rule_counts), 'distinct_sample_rows': len(sample_rows), 'sample_category_coverage': dict(Counter(category for row in sample_rows for category in row['risk_categories'])), 'sample_rule_coverage': dict(Counter(rule for row in sample_rows for rule in row['applicable_rules'])), 'full_population_finding_rows': len(findings), 'proposed_correction_candidates': len(candidates), 'sampling': 'Source-row ascending first 40 per category and per applicable rule; deduplicated, then affected-row supplementation to 300.', 'authority': 'Independent evidence review only. v1 statuses preserved, never upgraded. REVIEW is not proof of an erroneous cost center.', 'source': str(args.source), 'database': str(args.db)}
    metrics['applied_per_rule'] = dict(applied_rule_counts)
    metrics['expected_v1_applied_rows'] = 23243
    metrics['expected_v1_applied_cells'] = 47688
    metrics['v1_applied_totals_match_expectation'] = counts['cc_applied_rows'] == 23243 and counts['cc_applied_cells'] == 47688
    metrics['sampling'] = 'Source-row ascending first 40 per category and applicable rule, deduplicated; supplement first 300 applied rows if necessary.'
    metrics['eligibility_note'] = 'Lookup corroboration and no configured semantic objection are separate from approved financial-domain eligibility. Existing revenue CC usage is counted, not policy-certified.'
    metrics['source_field_meanings'] = {'I': 'native general account code', 'N': 'native subsidiary-account title', 'O': 'native detailed-account title; may be person/organization rather than purpose', 'P': 'native subaccount title; may be project/party rather than purpose', 'T': 'native document description; may be generic', 'W': 'native budget code'}
    for status in ('FAIL', 'REVIEW', 'NO_DETECTED_CONTRADICTION'):
        metrics['counts'].setdefault('applied_' + status, 0)
        metrics['counts'].setdefault('applied_cells_' + status, 0)
    (args.output / 'semantic_metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding='utf-8')
    report = ['# Independent semantic cost-center audit', '', '## Scope and evidence', '', 'Every shared-ledger row with a populated enriched cost center was evaluated, including unchanged native centers. All rows receiving AF/AG/AH/AI were evaluated, not only unique budget joins. Evidence is I/N/O/P/T/W/X, original and enriched CC, untouched v1 fill status, and independently read native budget A:J references. No original workbook or v1 deliverable was modified.', '', '## Decisions', '', 'FAIL is limited to direct expense-class/provenance contradictions. Loan/payroll, procurement/building, operational/capital, affiliate-support/direct-execution and O/P-budget domain differences are REVIEW: lexical evidence does not determine approved allocation rules. NO_DETECTED_CONTRADICTION is not committee approval or validation upgrade.', '', '## Full-population metrics', '', '```json', json.dumps(metrics, ensure_ascii=False, indent=2), '```', '', '## Outputs and reproducibility', '', '- Semantic_Cost_Center_Audit.csv: deterministic 300+ distinct applied-row evidence sample.', '- full_population_findings.csv: every row triggering any configured systemic rule, including existing native CC risk.', '- proposed_cc_corrections.csv: only native same-W candidates with explicit O/P domain overlap; proposal only, never applied. Empty output means no sufficiently evidenced candidate, not no risk.', '', 'Native budget titles/domains and source I account codes are shown as evidence, not treated as authoritative cross-domain eligibility rules. Multi-domain lines, payroll financing, project procurement and inter-organization support require documentary purpose, recipient/beneficiary, contract/project, budget-owner and cost-center-steward determination. Text rules can miss unexpressed context; no rule firing is not a comprehensive semantic certification.', '']
    report += ['## Source-description limitations', '', 'N is the subsidiary-account title, O the detailed-account title and P the subaccount title. O/P may identify a party or project rather than the expenditure purpose, and T may be generic. Keyword matches are reproducible expert-review triggers, not asserted financial-event verdicts. Existing class-4 cost-center use is preserved and flagged for field-policy determination, never automatically declared erroneous.', '']
    (args.output / 'semantic_findings_EN.md').write_text('\n'.join(report), encoding='utf-8')
    print(json.dumps(metrics, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
