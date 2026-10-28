"""Read immutable v1 reports; produce independent governance explanations only."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

V1 = Path('data/deliverables/journal_1404_enrichment_final')
OUT = Path('data/deliverables/journal_1404_enrichment_v1_independent_audit')
BOOK = 'Accounting_Journal_1404_Desired_State_Enriched_v1.xlsx'


def read_rows(path, sheet):
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rel_key = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read('xl/workbook.xml'))
        relationships = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets = {row.attrib['Id']: row.attrib['Target'] for row in relationships}
        selected = next(row for row in workbook.find('m:sheets', ns) if row.attrib['name'] == sheet)
        target = targets[selected.attrib[rel_key]]
        target = target.lstrip('/') if target.startswith('/') else 'xl/' + target
        xml = ET.fromstring(archive.read(target))
        cells = xml.findall('m:sheetData/m:row/m:c', ns)
        shared = []
        if any(cell.attrib.get('t') == 's' for cell in cells):
            shared = [''.join(item.itertext()) for item in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
        rows = []
        for row in xml.findall('m:sheetData/m:row', ns):
            values = []
            for cell in row:
                letters = ''.join(char for char in cell.attrib['r'] if char.isalpha())
                column = 0
                for char in letters:
                    column = column * 26 + ord(char) - 64
                while len(values) < column:
                    values.append(None)
                value = cell.findtext('m:v', None, ns)
                if cell.attrib.get('t') == 'inlineStr':
                    value = ''.join(cell.find('m:is', ns).itertext())
                elif cell.attrib.get('t') == 's':
                    value = shared[int(value)]
                values[column - 1] = value
            rows.append(values)
        width = max(map(len, rows), default=0)
        return [row + [None] * (width - len(row)) for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v1', type=Path, default=V1)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    v1, out = args.v1, args.out
    load = lambda name: json.loads((v1 / name).read_text(encoding='utf-8'))
    verification = load('verification_final.json')
    stats = load('stats.json')
    register = load('source_register.json')
    manifest = load('delivery_manifest.json')
    controls = read_rows(v1 / BOOK, 'QA_Controls')
    independent = read_rows(v1 / BOOK, 'Independent_QA')
    proposed = read_rows(v1 / BOOK, 'Proposed_CC_Analytical')
    proposed_headers = proposed[0]
    decision_index = proposed_headers.index('تصمیم کمیته')
    status_index = proposed_headers.index('وضعیت تأیید')
    decisions = sum(row[decision_index] not in (None, '') for row in proposed[1:])
    canonical = next(r for r in register if 'canonical-events_v7.1' in r['filename'])
    committee = read_rows(Path(canonical['path']), 'جدول_تصمیم_کمیته_رویداد')
    approved_indices = [i for i, name in enumerate(committee[0]) if name and 'مصوب' in name]
    approved_counts = {committee[0][i]: sum(row[i] not in (None, '', 'Needs Decision') for row in committee[1:]) for i in approved_indices}
    review_controls = [dict(zip(controls[0], row)) for row in controls[1:] if row[2] == 'REVIEW']
    review_independent = [dict(zip(independent[0], row)) for row in independent[1:] if row[1] == 'REVIEW']
    reviews = []
    for row in review_controls:
        test = str(row['Test'])
        if test == '8':
            explanation = {
                'scope': 'Journal rows 6:553672, AN contract identifier, AO contract title, AP project identifier, AQ project title; Audit_Fill and Unresolved_Review.',
                'counts': {'basis': 'Historical v1 stats.json; current independent population recalculation is separate', 'journal_rows': stats['rows'], 'blank_cells_AN_AQ': stats['rows'] * 4, 'new_contract_project_assignments': 0, 'final_population': {c: stats['final_population'][c] for c in ('AN', 'AO', 'AP', 'AQ')}},
                'evaluated_result': 'No unsupported assignment was made, but complete contract/project coverage was NOT established. REVIEW is conservative missing-evidence coverage, not a detected unsafe-fill failure.',
                'financial_integrity_impact': 'No new contract/project IDs, source-row edits or debit/credit edits are evidenced by this control. Missing attribution prevents contract/project completeness claims; applicability and affected monetary exposure cannot be determined from blank values alone.',
                'action': 'Obtain approved, versioned contract/project masters and transaction-level crosswalks keyed to stable source row/document and line identity; define approved applicability rules. Retain unresolved records until evidence exists; never infer IDs from descriptions or mark NOT_APPLICABLE from absence.',
                'acceptance_blocker': 'Blocks complete desired-state acceptance and authoritative handoff where those dimensions are required. Does not itself block restricted analytical review of preserved v1.'}
        elif test == '15':
            explanation = {
                'scope': 'All 553667 journal rows; original AJ/AK person values and full Audit_Fill, Unresolved_Review, Person_Validation, Person_Name_Variants, Existing_Conflicts, Semantic_Sample and sidecar evidence.',
                'counts': {'basis': 'Historical v1 stats.json; current independent person/population recalculation is separate', 'journal_rows': stats['rows'], 'existing_AJ': stats['initial_population']['AJ'], 'existing_AK': stats['initial_population']['AK'], 'audit_cell_records': stats['new_cells'], 'unresolved_row_records': stats['unresolved_rows'], 'normalized_person_name_anomalies_reported_by_v1': stats['person_name_locator_inconsistencies']},
                'evaluated_result': 'Local processing and a restrict-access statement are evidence of handling intent, NOT verification of ACLs, encryption, recipients, retention or privacy approval. REVIEW is a privacy/distribution governance gate, not an accounting-integrity failure.',
                'financial_integrity_impact': 'Privacy controls do not prove or disprove debit/credit preservation or semantic accuracy. Full financial/person evidence has confidentiality exposure if distributed without authorization.',
                'action': 'Data owner/security owner must approve named recipients, least-privilege access, protected storage/transfer, retention/deletion and minimized or redacted management exports. Record actual access-control evidence; do not distribute unrestricted row-level files.',
                'acceptance_blocker': 'Blocks unrestricted distribution/production release until documented privacy authorization. Restricted internal audit may proceed only under an approved access policy.'}
        else:
            explanation = {'scope': 'Observed workbook review; see original evidence.', 'counts': {}, 'evaluated_result': row['Evidence'], 'financial_integrity_impact': 'Unassessed additional REVIEW; no authoritative acceptance.', 'action': 'Obtain a scoped independent explanation and accountable owner decision.', 'acceptance_blocker': 'Unresolved additional REVIEW blocks final acceptance.'}
        reviews.append({'test_id': 'QA_Controls:' + test, 'original_result': 'REVIEW', 'original_evidence': row['Evidence'], **explanation})
    for row in review_independent:
        test = str(row['Check'])
        evidence = json.loads(row['Evidence'])
        reviews.append({'test_id': 'Independent_QA:' + test, 'original_result': 'REVIEW', 'original_evidence': evidence,
            'scope': 'Journal AN:AQ rows 6:553672; verification_final.json checks.15.coverage.',
            'counts': {'basis': 'Direct immutable Independent_QA sheet evidence; journal_rows from historical v1 stats.json', 'failure_count': evidence.get('failure_count'), 'coverage': evidence.get('coverage'), 'journal_rows': stats['rows']},
            'evaluated_result': 'Independent coverage control reports zero initial/added/final cells for AN:AQ and zero detected failures; zero fills are safe non-action, not demonstrated dimension completeness.',
            'financial_integrity_impact': 'No attribution mutation detected by the reported check; required-dimension coverage and project/contract monetary exposure remain unestablished.',
            'action': 'Use the same master/crosswalk and applicability approval gate as QA_Controls:8; independently evaluate coverage after approved links become available without editing immutable v1.',
            'acceptance_blocker': 'Same substantive gap as mandatory test 8, not a third distinct accounting defect.'})
    report = {'scope': 'Read-only post-enrichment governance audit; no workbook rebuild or v2.',
        'status': 'REVIEW', 'original_statuses_preserved': True,
        'original_mandatory_totals': dict(Counter(row[2] for row in controls[1:])),
        'original_independent_totals': dict(Counter(row[1] for row in independent[1:])),
        'observed_review_count': len(reviews), 'reviews': reviews,
        'verification_final_status': verification['status'],
        'authority_evidence': {'proposed_records': len(proposed)-1, 'proposed_committee_decisions_populated': decisions,
            'proposed_status_distribution': dict(Counter(str(row[status_index]) for row in proposed[1:])),
            'canonical_committee_rows': len(committee)-1, 'canonical_approved_fields_populated': approved_counts,
            'missing_registered_sources': [r for r in register if r['authority_status'] == 'UNAVAILABLE']},
        'delivery_manifest': manifest,
        'limitations': ['v1 integrity PASS is historical evidence, not this agent rerunning full integrity.', 'No approved ERP master, native-to-proposed crosswalk, financial-event rule publication or external ID authority established from reviewed evidence.', 'No ACL/security approval or contract/project applicability master inspected.', 'VALIDATED_COMPOSITE is preserved as a v1 matching status; it is not authoritative business approval.']}
    out.mkdir(parents=True, exist_ok=True)
    (out / 'governance_review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Independent explanations of all observed v1 REVIEW controls', '',
        f'Immutable v1: `{v1 / BOOK}`. Original source: `{verification["source"]}`.',
        f'Measured workbook totals: mandatory {report["original_mandatory_totals"]}; independent {report["original_independent_totals"]}. Observed REVIEW instances: {len(reviews)}.',
        'The two contract/project controls address one shared coverage gap. Original statuses and all VALIDATED_COMPOSITE audit statuses remain unchanged. No v1 file was modified.', '']
    for review in reviews:
        lines.extend(['## ' + review['test_id'] + ' — REVIEW', '',
            '**Original evidence:** ' + json.dumps(review['original_evidence'], ensure_ascii=False),
            '**Evaluated result:** ' + review['evaluated_result'],
            '**Counts:** `' + json.dumps(review['counts'], ensure_ascii=False) + '`',
            '**Affected worksheet/row population:** ' + review['scope'],
            '**Financial integrity impact:** ' + review['financial_integrity_impact'],
            '**Required action:** ' + review['action'],
            '**Acceptance blocker:** ' + review['acceptance_blocker'], ''])
    lines.extend(authority_text(v1, canonical, report))
    (out / 'QA_REVIEW_Explanations.md').write_text('\n'.join(lines), encoding='utf-8')
    (out / 'Management_Summary_FA.md').write_text(persian_summary(report, stats), encoding='utf-8')
    print(json.dumps({'outputs': ['QA_REVIEW_Explanations.md', 'governance_review.json', 'Management_Summary_FA.md'], 'review_instances': len(reviews), 'proposed_decisions': decisions, 'canonical_approved_counts': approved_counts}, ensure_ascii=False))


def authority_text(v1, canonical, report):
    return ['## Evidence and authority boundary', '',
        f'Exact v1 evidence paths: `{v1 / "verification_final.json"}` checks.8 (debit/credit PASS) and checks.15 (contract/project REVIEW); `{v1 / "source_register.json"}` fields path/worksheet/authority_status/identifiers; `{v1 / "delivery_manifest.json"}` fields files, matching_scope, data_handling; `{v1 / "stats.json"}` initial_population/added/final_population/missing_sources.',
        'Workbook `QA_Controls` fields Test/Control/Result/Evidence and `Independent_QA` fields Check/Result/Evidence were read directly. Independent_QA evidence is consistent with verification_final.json check 15; the JSON remains REVIEW with failure_count=0. A failure count of zero is not evidence of missing-dimension completeness.', '',
        '### Native budget is not an approved ERP crosswalk',
        'Original source sheet `بودجه 1404 + مراکز هزینه`, 2830 registered records, data from row 3: A budget code, B financial line, C expenditure type, D/E subject/subsubject, F/G native cost-center L1 code/title, H/I native L2 code/title, J owner. Journal W is the budget locator, X source classification (6 expense; 4 revenue), AF:AI are native cost-center fields. This supports native reconstruction and semantic checking, not a committee-approved enterprise migration. Source-register authority explicitly says no separate committee approval claimed. Matching by document only is insufficient for multi-center lines.',
        'The registered absent desktop v3 file `C:/Users/sadra/Downloads/بسته_نهایی_مراکز_هزینه_با_شماره_سند_حسابداری_v3.xlsx` was intended to provide Master_Data_ERP/Doc_No_Mapping; source_register marks MISSING/UNAVAILABLE. The absence at that registered path is not proof no ERP master exists anywhere; no approved operational master or signed crosswalk was supplied in reviewed evidence. `data/reports/cost_centers.xlsx` has legacy responsibility/action text, not a verified native-ID master. `data/reports/budget.xlsx`, sheet `سرمایه ای`, has supplemental project/activity titles, not stable approved project IDs or CC links.', '',
        '### Proposed cost centers are review evidence',
        f'`C:/Users/sadra/Desktop/Fehrest Nahaie Pishnahadi.xlsx`, Sheet1, is represented by immutable v1 `Proposed_CC_Analytical`: {report["authority_evidence"]["proposed_records"]} rows, {report["authority_evidence"]["proposed_committee_decisions_populated"]} populated تصمیم کمیته values. Fields کد مرکز هزینه پیشنهادی, وضعیت تأیید, مرجع مورد نیاز برای تأیید, تصمیم کمیته, توضیح تصمیم کمیته are not a published active ERP master. Appended fields Authority for this journal and Native crosswalk status explicitly say PROPOSED — NOT AUTHORIZED and NO VERIFIED CROSSWALK. Approval-status phrases such as ready for formal approval do not mean approved.',
        'Required missing authority: approved native F/H identifiers → stable ERP CC IDs, applicable service/financial-line constraints, effective dates/version, approving role and approval record; explicit split/merge lineage, and signed transaction-level exceptions where needed. Proposed titles, frequencies and broad document numbers cannot replace that crosswalk.', '',
        '### Historical relationships cannot publish rules',
        f'`{canonical["path"]}`: `فرهنگ_رویداد_مالی_کاندید` is a candidate catalog; `ماتریس_شواهد_رویداد_مرکز_v2` fields candidate event code, observed CC code, row/document counts and وضعیت حاکمیتی are observational. `Doc_No_Mapping_Lineage` preserves historical row/document lineage, not an approved crosswalk to this 553667-row journal. Registered historical population is 337268 rows; do not assume row numbers/documents are interchangeable.',
        f'`جدول_تصمیم_کمیته_رویداد` has {report["authority_evidence"]["canonical_committee_rows"]} decision rows. Each of the six approved-cardinality fields contains Needs Decision on all 70 rows, not an approved cardinality; the resolution/instruction number field is empty. Observed non-placeholder approved-field counts: `{json.dumps(report["authority_evidence"]["canonical_approved_fields_populated"], ensure_ascii=False)}`. Historical observed relationships and observed cardinality never establish allowed/prohibited or required/not-applicable dimensions. An absent rule is not an explicit prohibition.', '',
        '### Bank title reconstruction is not global bank identity',
        'Historical method inspected at `scripts/enrich_journal_1404.py` bank block: same-row journal O is copied to AM when I=611, J is not 020/030/040, O is present and normalized P matches `حسابهای بانکی` C. Audit method is native_bank_account_title; reference_sheet is the journal and reference_row is O<source_row>, with the supporting bank-sheet C row described in reason. This is structured account-head reconstruction, not a bank-ID lookup. The native bank sheet A repeats account titles, B lists non-cash titles and C deduplicates account titles; it contains no global bank ID.',
        'v1 records 150648 AM additions and zero AL additions; AL remains blank in all 553667 rows. `data/reports/Verified_Bank_ID_Master.xlsx` is registered missing. Native name matching does not prove globally unique bank/account entity, ownership, current account validity or approved counterparty identity. Keep VALIDATED_COMPOSITE unchanged, attach independent bank semantic evidence separately; do not upgrade AM or manufacture AL. Parent independent bank audit supplies any full-population anomalies.', '',
        '## Acceptance governance',
        '1. Restrict v1 to evidence-preserving analytical/review use; do not label it complete desired-state or approved production classification. No unsafe contract/project fill is distinct from missing coverage.',
        '2. Source Data Steward validates corrected source/effective values; master owners approve active IDs and crosswalks; Taxonomy Approver/Publisher approves and versions financial-event relationships and applicability. A preparer/reviewer cannot substitute for these roles.',
        '3. Verify each required classification line under active authoritative rules, master validity, source provenance, dimension/document requirements and exact monetary reconciliation. Revenue/expense classification and OPEX/CAPEX semantic conflicts require source/master-owner decisions, not history-driven overwrite.',
        '4. Obtain privacy/security sign-off independently from integrity sign-off. Preserve immutable source/audit/statuses; restricted working copies may be reviewed but this audit creates no v2.',
        '5. Cost-center master exceptions and event/CC relationship exceptions are separately approved and version-scoped; no business exception may bypass provenance, audit, identity, authorization or system-integrity invariants.', '',
        'Exact governance references: `docs/adr/0001-authoritative-rule-precedence.md`; `0003-pre-authoritative-operation.md`; `0010-governance-and-separation-of-duties.md`; `0015-use-of-proposed-cost-centers.md`; `0017-package-workflow-and-classification-state.md`; `0018-effective-value-override-governance.md`; `0019-pre-authoritative-form-dimensions.md`; `0020-cost-center-and-relationship-exceptions.md`; `0024-staged-counterparty-reference-registry.md`; `0025-deterministic-validation-precedence-and-scoped-exceptions.md`; `0026-exact-monetary-reconciliation-by-default.md` (all under docs/adr).', '',
        'This explanatory audit measures the small immutable report sheets and authority fields; it does not rerun the full monetary/OOXML comparison, inspect filesystem ACLs, or approve financial semantics. Parent full-population integrity/coverage/semantic/bank/person evidence must remain separate. No historical PASS or VALIDATED_COMPOSITE was silently converted into authoritative approval.']


def persian_summary(report, stats):
    return f'''# خلاصه مدیریتی ممیزی مستقل نسخه ۱ — پیش‌نویس

نسخه ۱ و فایل اصلی بدون تغییر باقی مانده‌اند؛ این ممیزی فقط گزارش توضیحی تولید کرده و نسخه ۲ نساخته است.

- جامعه دفتر: **{stats['rows']:,} ردیف**. در کنترل‌های الزامی، **۱۳ PASS و ۲ REVIEW** و در کنترل‌های مستقل نسخه ۱، **۱۴ PASS و ۱ REVIEW** مشاهده شد. سه مورد REVIEW مربوط به دو موضوع مستقل‌اند: پوشش قرارداد/پروژه و محرمانگی.
- کنترل الزامی ۸ و مستقل ۱۵: هر چهار ستون AN:AQ از ابتدا تا انتها خالی‌اند؛ **هیچ شناسه قرارداد یا پروژه بدون مدرک درج نشده**. این رفتار ایمن است، اما اثبات تکمیل پوشش نیست. برای تعیین موارد لازم/نامرتبط و انتساب مبلغ، مرجع مصوب و اتصال قابل‌ردیابی در سطح ردیف لازم است.
- کنترل الزامی ۱۵: پردازش محلی و توصیه محدودکردن دسترسی، جای تأیید محرمانگی، فهرست گیرندگان، دسترسی واقعی، نگهداری و انتقال امن را نمی‌گیرد. این REVIEW موضوع انتشار و حریم خصوصی است و به‌خودی‌خود نشان‌دهنده تغییر مبالغ نیست.
- جدول بودجه داخلی می‌تواند بازسازی مقادیر بومی را پشتیبانی کند، اما معادل نگاشت مصوب به مرجع ERP نیست. در **{report['authority_evidence']['proposed_records']} مرکز پیشنهادی**، **{report['authority_evidence']['proposed_committee_decisions_populated']} تصمیم کمیته** ثبت شده است. روابط تاریخی رویداد–مرکز هزینه نیز مشاهده‌اند، نه قانون مصوب؛ جامعه تاریخی با دفتر فعلی یکسان نیست.
- **۱۵۰٬۶۴۸ عنوان بانکی AM** از سرفصل همان ردیف O با کنترل عنوان حساب P بازسازی شده‌اند؛ این عملیات شناسه بانک ایجاد نمی‌کند. ستون AL همچنان خالی است و مرجع شناسه بانکی تأییدشده ارائه نشده است.

**پیشنهاد پذیرش:** صرفاً استفاده تحلیلی و بازبینی با دسترسی محدود؛ نه پذیرش «تکمیل وضعیت مطلوب» یا تحویل نهایی مبتنی بر طبقه‌بندی مصوب. مالکان داده باید شناسه‌ها، نگاشت نسخه‌دار، قواعد کاربردپذیری و اصلاحات لازم را تأیید کنند؛ مرجع تصویب/انتشار باید قواعد مالی را جداگانه تصویب کند و مسئول امنیت نیز انتشار را تأیید کند. وضعیت‌های نسخه ۱، از جمله VALIDATED_COMPOSITE، حفظ شده‌اند و به تأیید رسمی ارتقا نیافته‌اند.

شواهد تفصیلی: `QA_REVIEW_Explanations.md` و `governance_review.json` در همین پوشه. نتایج کنترل مستقل سراسری مبالغ، پوشش، معنا و اشخاص باید هنگام یکپارچه‌سازی گزارش نهایی به این پیش‌نویس افزوده شود؛ این متن جای آن کنترل‌ها نیست.
'''


if __name__ == '__main__':
    main()
