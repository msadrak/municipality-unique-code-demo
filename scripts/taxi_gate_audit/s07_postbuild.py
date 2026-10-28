"""Step 7 — POST-BUILD verification.  Re-opens the delivered files and checks them against the step outputs and the
sources.  Results go to POSTBUILD_QA.md / .csv beside the deliverables (never inside the files under test).
"""
import csv
import os
import re
from collections import Counter

import openpyxl

from common import OUT, SOURCES, sha256, load, ro_sqlite, TT_DB
from decisions import DECISIONS
from s06_build import AUDIT_XLSX, DEC_XLSX, REPORT_MD, MEMO_MD

REQUIRED = ['README', 'Source_Inventory', 'Version_Diff', 'CoA_Normalized', 'CoA_Integrity_QA', 'Original_Mapping_Audit', 'Account_Crosswalk_Proposed',
            'Alternative_Candidates', 'Taxi_Terminal_Evidence', 'Account_Event_Crosswalk', 'Activity_CC_Crosswalk', 'Prior_Project_Comparison',
            'Governance_Decisions', 'QA_Reproducibility', 'Executive_KPIs']
DEC_COLS = ['Decision ID', 'Topic', 'Source evidence', 'Existing classification', 'Identified problem', 'Proposed alternatives', 'Analytical recommendation',
            'Potential financial impact', 'Priority', 'Responsible expert', 'Committee decision', 'Decision date', 'Approval reference', 'Final status']


def main():
    fx, mt, ig, qa = load('forensics.json'), load('matching.json'), load('integration.json'), load('qa_registry.json')
    res = []

    def t(tid, desc, ok, actual, status=None):
        res.append((tid, desc, status or ('PASS' if ok else 'FAIL'), str(actual)))

    for k, p in SOURCES.items():
        t(f'PB-SRC-{k}', f'{os.path.basename(p)} unchanged after build', sha256(p) == fx['container'][k]['sha256'], sha256(p))
    wb = openpyxl.load_workbook(AUDIT_XLSX, read_only=True)
    names = wb.sheetnames
    t('PB-WB-01', 'all 15 required sheets present', all(n in names for n in REQUIRED), [n for n in REQUIRED if n not in names] or f'{len(names)} sheets')

    def data_rows(ws):
        return sum(1 for r in ws.iter_rows(min_row=5, values_only=True) if any(v not in (None, '') for v in r))
    checks = [('Original_Mapping_Audit', len(mt['audit'])), ('Candidate_Audit', len(mt['candidates'])), ('Account_Crosswalk_Proposed', len(mt['crosswalk'])),
              ('Account_Event_Crosswalk', len(ig['account_event'])), ('Activity_CC_Crosswalk', len(ig['activity_cc'])), ('QA_Reproducibility', len(qa)),
              ('Lineage_Lines', ig['reconciliation']['lineage']['lines'])]
    for n, exp in checks:
        got = data_rows(wb[n])
        t(f'PB-ROWS-{n}', f'{n}: rows written = rows computed', got == exp, f'{got} / {exp}')
    # lineage totals inside the workbook
    ws = wb['Lineage_Lines']
    hdr = [c for c in next(ws.iter_rows(min_row=4, max_row=4, values_only=True))]
    di, ci = hdr.index('Debit'), hdr.index('Credit')
    sd = sc = 0
    for r in ws.iter_rows(min_row=5, values_only=True):
        sd += r[di] or 0
        sc += r[ci] or 0
    src = ro_sqlite(TT_DB).execute('SELECT sum(bed),sum(bes) FROM sanad').fetchone()
    t('PB-REC-01', 'Lineage_Lines debit/credit totals = Sanad totals', (sd, sc) == tuple(src), f'{sd:,} / {sc:,}')
    # approvals never invented
    bad = 0
    for n in ('Account_Crosswalk_Proposed', 'Account_Event_Crosswalk'):
        ws = wb[n]
        hdr = list(next(ws.iter_rows(min_row=4, max_row=4, values_only=True)))
        i = hdr.index('approval_status')
        bad += sum(1 for r in ws.iter_rows(min_row=5, values_only=True) if r[i] not in ('NOT_APPROVED', None))
    t('PB-GOV-01', 'no relationship labelled approved in the workbook', bad == 0, bad)
    # privacy scan: retiree names from hesab and long digit runs (bank accounts) must not appear in exported titles
    names_db = set()
    for (nm,) in ro_sqlite(TT_DB).execute("SELECT name FROM hesab WHERE name LIKE '%بازنشسته%' OR name LIKE '%بانشسته%'"):
        m = re.match(r'^(.*?)[-=]', nm.strip())
        if m and len(m.group(1).strip()) > 3:
            names_db.add(m.group(1).strip())
    leaks = Counter()
    for n in names:
        if n == 'Lineage_Lines':
            continue
        for r in wb[n].iter_rows(values_only=True):
            for v in r:
                if isinstance(v, str):
                    for p in names_db:
                        if p in v:
                            leaks[n] += 1
                    if re.search(r'(?<![0-9A-Fa-f.,])\d{9,}(?![0-9A-Fa-f.,])', v) and n not in ('Source_Inventory', 'README', 'QA_Reproducibility'):
                        leaks[n + ':digits'] += 1
    dwp = openpyxl.load_workbook(DEC_XLSX, read_only=True)
    for n in dwp.sheetnames:
        for r in dwp[n].iter_rows(values_only=True):
            for v in r:
                if isinstance(v, str) and any(p in v for p in names_db):
                    leaks['decision_workbook:' + n] += 1
    dwp.close()
    md_text = open(REPORT_MD, encoding='utf8').read()
    leaks.update({'report_md': sum(1 for p in names_db if p in md_text)} if any(p in md_text for p in names_db) else {})
    t('PB-PRIV-01', 'no personal names / unmasked account numbers in exported titles (audit, decision, report)', not leaks, dict(leaks) or 'none',
      None if not leaks else 'REVIEW')
    wb.close()
    # decision workbook
    dw = openpyxl.load_workbook(DEC_XLSX, read_only=True)
    ws = dw['تصمیمات']
    keys = list(next(ws.iter_rows(min_row=4, max_row=4, values_only=True)))
    t('PB-DEC-01', 'decision workbook has all 14 required columns', all(c in keys for c in DEC_COLS), [c for c in DEC_COLS if c not in keys] or 'ok')
    rows = [r for r in ws.iter_rows(min_row=5, values_only=True) if r[0]]
    t('PB-DEC-02', 'one row per decision', len(rows) == len(DECISIONS), f'{len(rows)} / {len(DECISIONS)}')
    filled = sum(1 for r in rows for c in ('Committee decision', 'Decision date', 'Approval reference') if r[keys.index(c)] not in (None, ''))
    t('PB-DEC-03', 'committee-only fields left blank', filled == 0, filled)
    dw.close()
    md = open(REPORT_MD, encoding='utf8').read()
    heads = re.findall(r'^## (.+)$', md, flags=re.M)
    t('PB-MD-01', 'Persian report has the 18 required sections', sum(1 for h in heads if re.match(r'^[۰-۹]+\.', h)) == 18, len(heads))
    memo = open(MEMO_MD, encoding='utf8').read() if os.path.exists(MEMO_MD) else ''
    t('PB-MD-02', 'CD-01 memo exists with alternatives table and blank decision fields', 'تفسیرهای جایگزین' in memo and 'تصمیم: ________' in memo, len(memo))
    with open(os.path.join(OUT, 'POSTBUILD_QA.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['test_id', 'description', 'status', 'actual'])
        w.writerows(res)
    with open(os.path.join(OUT, 'POSTBUILD_QA.md'), 'w', encoding='utf8') as fh:
        fh.write('# POSTBUILD QA — Taxi-Gate deep audit v1\n\nThese tests re-open the delivered files; they are intentionally not embedded in the files they test.\n\n')
        fh.write('| test | description | status | actual |\n|---|---|---|---|\n')
        for r in res:
            fh.write('| ' + ' | '.join(str(x).replace('|', '／') for x in r) + ' |\n')
    print(Counter(r[2] for r in res), [r for r in res if r[2] != 'PASS'])


if __name__ == '__main__':
    main()
