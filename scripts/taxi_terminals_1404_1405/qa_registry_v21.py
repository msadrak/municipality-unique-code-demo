"""v2.1 canonical QA registry.  ONE dataset (the list returned by build_registry) is the source of every QA total printed anywhere
(QA report, corrective audit, management report, QA_Reconciliation sheet, registry CSV).  Totals are never typed by hand.
Categories: V21_ACCEPTANCE | HISTORICAL_REGRESSION | WORKBOOK_FORMULA_CONTROL
"""
import json, csv, collections, os

CATS = ('V21_ACCEPTANCE', 'HISTORICAL_REGRESSION', 'WORKBOOK_FORMULA_CONTROL')
STATUSES = ('PASS', 'REVIEW', 'FAIL', 'NOT_RUN')
POST_BUILD_NAMED = {'QA_CHANGELOG_CSV_XLSX_ROW_PARITY', 'QA_WORKBOOK_QA_MATCH_REPORT', 'QA_FORMULA_CACHE_VS_RECALCULATION'}
FINAL_NAMED = {'QA_TEST_REGISTRY_UNIQUENESS', 'QA_TEST_CATEGORY_SEPARATION', 'QA_SUMMARY_COUNTS_MATCH_DETAIL', 'QA_PRIVACY_CLIENT_PACKAGE', 'QA_OUTPUT_MANIFEST_INTEGRITY', 'QA_MD_KPI_COUNTS_MATCH'}
RELEVANCE = {'Lineage': 'HIGH', 'Totals': 'HIGH', 'Events': 'HIGH', 'CostCenter': 'HIGH', 'KPI': 'HIGH', 'Agency': 'HIGH', 'Privacy': 'HIGH', 'Provenance': 'MEDIUM', 'Deliverable': 'MEDIUM', 'Baseline': 'MEDIUM', 'V1_ARTIFACT': 'HISTORICAL'}
COLS = ['test_id', 'category', 'area', 'scope_sources', 'input_population', 'procedure', 'expected', 'actual', 'result', 'exception_detail', 'counts_toward_primary_summary',
        'is_formula_control', 'is_historical_regression', 'business_acceptance_relevance', 'embedded_in_workbook', 'execution_stage', 'reproduction_command']


def category_of(t):
    tid = t['test_id']
    if t.get('area') == 'V1_ARTIFACT' or tid.endswith('-V1'): return 'HISTORICAL_REGRESSION'
    if tid.startswith('P13-') or t.get('area') == 'FormulaControl' or tid.startswith('FC-') or tid == 'QA_FORMULA_CACHE_VS_RECALCULATION': return 'WORKBOOK_FORMULA_CONTROL'
    return 'V21_ACCEPTANCE'


def stage_of(tid):
    if tid in FINAL_NAMED: return 'FINAL_ASSEMBLY'
    if tid in POST_BUILD_NAMED or (tid.startswith('P') and tid[1:2].isdigit()): return 'POST_BUILD'
    return 'PRE_BUILD'


def build_registry(QA, embedded_ids=()):
    rows = []
    emb = set(embedded_ids)
    for t in QA['tests']:
        tid = t['test_id']; cat = category_of(t)
        rows.append(dict(test_id=tid, category=cat, area=t.get('area', ''), scope_sources=t.get('sources') or 'tt_v21.sqlite + source workbooks', input_population=t.get('population') or '—',
                         procedure=t.get('description', ''), expected=t.get('expected', ''), actual=t.get('actual', ''), result=t['status'], exception_detail=t.get('detail', ''),
                         counts_toward_primary_summary='Y' if cat == 'V21_ACCEPTANCE' else 'N', is_formula_control='Y' if cat == 'WORKBOOK_FORMULA_CONTROL' else 'N',
                         is_historical_regression='Y' if cat == 'HISTORICAL_REGRESSION' else 'N', business_acceptance_relevance=RELEVANCE.get(t.get('area', ''), 'MEDIUM') if cat == 'V21_ACCEPTANCE' else ('HISTORICAL' if cat == 'HISTORICAL_REGRESSION' else 'CONTROL'),
                         embedded_in_workbook='Y' if tid in emb else 'N', execution_stage=stage_of(tid), reproduction_command=t.get('command', '')))
    # builder formula block (live SUMIFS/COUNTIFS formulas with script-cached values)
    for i, fb in enumerate(QA.get('formula_block', []), 1):
        o, y, lab, want, got, st = fb
        rows.append(dict(test_id=f'FC-{o}-{y}-{i:02d}', category='WORKBOOK_FORMULA_CONTROL', area='FormulaControl', scope_sources='QA_Reconciliation formula block ↔ Source_Profile',
                         input_population=f'{o} {y}: {lab}', procedure='SUMIFS/COUNTIFS روی شیت‌های همین فایل در برابر Source_Profile؛ مقدار ذخیره‌شده (cached) توسط اسکریپت محاسبه شده است نه موتور اکسل', expected=str(want), actual=str(got), result=st,
                         exception_detail='', counts_toward_primary_summary='N', is_formula_control='Y', is_historical_regression='N', business_acceptance_relevance='CONTROL', embedded_in_workbook='Y', execution_stage='PRE_BUILD', reproduction_command='08_build_outputs.py (formula block)'))
    return rows


def summarize(rows):
    S = {c: collections.Counter() for c in CATS}
    for r in rows: S[r['category']][r['result']] += 1
    return S


def summary_table_md(rows, title_embedded=False):
    S = summarize(rows)
    out = ['| Category | PASS | REVIEW | FAIL | NOT_RUN | Total |', '|---|---|---|---|---|---|']
    for c in CATS:
        n = sum(S[c].values()); out.append(f"| {c} | {S[c]['PASS']} | {S[c]['REVIEW']} | {S[c]['FAIL']} | {S[c]['NOT_RUN']} | {n} |")
    return '\n'.join(out)


def write_csv(path, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(COLS)
        for r in rows: w.writerow([r[c] for c in COLS])
