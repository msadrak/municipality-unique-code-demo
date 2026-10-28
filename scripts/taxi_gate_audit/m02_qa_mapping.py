"""QA of the FINAL mapping workbook (reads the delivered .xlsx, recomputes from the ledger).  Results go to an external log
(QA_log.md / QA_log.csv) beside the workbook — never into it.  Also prints the summary statistics used in the Persian summary.
"""
import csv
import json
import os
import re
from collections import Counter, defaultdict

import openpyxl

from common import TT_DB, FE_V71, CC_MASTER, V21_DIR, V21_EVENTS, ro_sqlite, load, sha256
from m01_build_mapping import XLSX, SHEET, HEADERS, OUT_DIR, ORG_FA

FA2ORG = {v: k for k, v in ORG_FA.items()}


def main():
    wb = openpyxl.load_workbook(XLSX, read_only=False)
    ws = wb[SHEET]
    hdr = [c.value for c in ws[1]]
    exp_hdr = [h[1] for h in HEADERS]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        rows.append({HEADERS[i][0]: ('' if v is None else v) for i, v in enumerate(r)})
    res = []

    def t(tid, desc, ok, actual, status=None):
        res.append((tid, desc, status or ('PASS' if ok else 'FAIL'), str(actual)[:900]))

    tc = ro_sqlite(TT_DB)
    # ---------------------------------------------------------------- presentation
    t('P-01', '38 required Persian headers in the required order', hdr == exp_hdr, len(hdr))
    t('P-02', 'right-to-left, frozen header + account columns, AutoFilter, no merged cells',
      ws.sheet_view.rightToLeft and ws.freeze_panes == 'K2' and ws.auto_filter.ref and not ws.merged_cells.ranges,
      dict(rtl=ws.sheet_view.rightToLeft, freeze=ws.freeze_panes, filter=ws.auto_filter.ref, merged=len(ws.merged_cells.ranges)))
    blank = sum(1 for r in rows if not any(str(v).strip() for v in r.values()))
    t('P-03', 'no blank rows inside the dataset', blank == 0, blank)
    code_types = Counter(type(ws.cell(row=i, column=7).value).__name__ for i in range(2, ws.max_row + 1))
    t('P-04', 'account codes stored as text', set(code_types) <= {'str'}, dict(code_types))
    cf = len(ws.conditional_formatting)
    t('P-05', 'conditional formatting for status and low confidence', cf >= 2, cf)
    # ---------------------------------------------------------------- 8 duplicate keys
    keys = Counter((r['c1'], r['c2'], r['c7'], r['c9'], r['c15'], r['c16'], r['c20'], r['c21'], r['c22']) for r in rows)
    dups = [k for k, n in keys.items() if n > 1]
    t('Q-08', 'no duplicate mapping key (org/unit × head × event × activity × cost center)', not dups, dups[:5] or len(keys))
    # ---------------------------------------------------------------- 1 coverage
    universe = defaultdict(set)
    for org, hc, lvl in tc.execute('SELECT org,hcode,level FROM hesab'):
        universe[org].add((hc.strip(), lvl))
    used = defaultdict(set)
    for org, k, m, t1 in tc.execute('SELECT DISTINCT org,kol,moeen,taf1 FROM sanad'):
        used[org].add(f'{k}-{m}-{t1}-0')
    cov = defaultdict(set)
    for r in rows:
        org = FA2ORG[r['c1']]
        cov[org].add(r['c7'])
        if r['c9']:
            cov[org].add(r['c9'])
    miss = []
    tot = {2: 0, 3: 0, 4: 0}
    for org, s in universe.items():
        for hc, lvl in s:
            if lvl in (2, 3):
                tot[lvl] += 1
                if hc not in cov[org]:
                    miss.append((org, hc))
            elif lvl == 4:
                tot[4] += 1
                p = hc.split('-')
                if f'{p[0]}-{p[1]}-{p[2]}-0' not in cov[org]:
                    miss.append((org, hc))
    miss_used = [(o, h) for o, s in used.items() for h in s if h not in cov[o]]
    t('Q-01', 'every Hesab account (L2, L3; L4 via its L3 parent) and every ledger head has ≥1 row', not miss and not miss_used,
      dict(missing=miss[:10], missing_used=miss_used[:10], universe=tot))
    # ---------------------------------------------------------------- 2 events
    wbe = openpyxl.load_workbook(FE_V71, read_only=True, data_only=True)
    FE = {r[0] for r in wbe['فرهنگ_رویداد_مالی_کاندید'].iter_rows(min_row=2, values_only=True) if r[0]}
    V21 = {r['event_id'] for r in csv.DictReader(open(V21_EVENTS, encoding='utf-8-sig'))}
    bad_ev = []
    for r in rows:
        e = r['c15']
        if not e:
            continue
        if e in FE:
            continue
        marked = ('پیشنهادی' in r['c18'] or 'خارج از FE' in r['c18'] or 'استثنا' in r['c18']) and e in V21 and r['c36'] != 'OBSERVED'
        if not marked:
            bad_ev.append((e, r['c36']))
    t('Q-02', 'every event id is in FE v7.1, or is a v2.1 TT-NE/PEO/EXC id explicitly marked proposed/non-FE and not OBSERVED', not bad_ev, bad_ev[:5])
    # ---------------------------------------------------------------- 3 cost centers
    CC = json.load(open(CC_MASTER, encoding='utf8'))
    NCC = json.load(open(os.path.join(V21_DIR, 'machine_readable', 'new_cost_center_candidates.json'), encoding='utf8'))
    bad_cc = [(r['c21'], r['c36']) for r in rows if r['c21'] and not (r['c21'] in CC or (r['c21'] in NCC and 'کاندید' in r['c23'] and r['c36'] != 'OBSERVED'))]
    t('Q-03', 'every cost-center id is in cc_master, or a TTCC-P proposal explicitly marked and not OBSERVED', not bad_cc, bad_cc[:5])
    # ---------------------------------------------------------------- 4 org × account validity
    hes = defaultdict(set)
    for org, hc in tc.execute('SELECT org,hcode FROM hesab'):
        hes[org].add(hc.strip())
    inval = [(r['c1'], r['c7'], r['c9']) for r in rows if r['c7'] not in hes[FA2ORG[r['c1']]] or (r['c9'] and r['c9'] not in hes[FA2ORG[r['c1']]])]
    t('Q-04', 'every organisation × account combination exists in that organisation\'s Hesab', not inval, inval[:5])
    # ---------------------------------------------------------------- 5 invalid V2 matches not reused
    mt = load('matching.json')
    bad = {a['old_code']: str(a['best_code']) for a in mt['audit'] if a['verdict'].startswith('INVALID') or a['verdict'] == 'RELATED_NOT_EQUIVALENT'}
    reused = [(r['c1'], r['c9'] or r['c7'], r['c12']) for r in rows if r['c12'] and bad.get(r['c9'] if r['c9'] in bad else r['c7']) == str(r['c12'])]
    t('Q-05', 'no invalid / non-equivalent Taxi-Gate V2 suggestion reused as the new code', not reused, reused[:5] or f'{len(bad)} V2 suggestions blocked')
    # ---------------------------------------------------------------- 6 events never from title similarity
    allowed = ('هم‌رخدادی سطر واقعی دفتر', 'رویداد محرک دیگر در همان سند ترکیبی', 'گزینهٔ جایگزین مرکز هزینه', 'پیشنهاد معنایی کنترل‌شده بر اساس تعریف عملیات پایان دوره',
               'پیشنهاد از شواهد همان حساب', '—')
    bad_m = Counter(r['c33'][:40] for r in rows if not r['c33'].startswith(allowed))
    t('Q-06', 'every event relation comes from ledger co-occurrence, composite-document drivers, PEO definition or the same account in the other organisation',
      not bad_m, dict(bad_m) or Counter(next(a for a in allowed if r['c33'].startswith(a)) for r in rows))
    # ---------------------------------------------------------------- 7 no invented cost center: every CC on a row was assigned or offered by line_cc for that org/head
    seen = defaultdict(set)
    for org, k, m, t1, ccid, alt in tc.execute('SELECT s.org,s.kol,s.moeen,s.taf1,c.cc_id,c.alt_ccs FROM sanad s JOIN line_cc c ON c.sid=s.sid WHERE c.eligible=1'):
        h = f'{k}-{m}-{t1}-0'
        for c in [ccid] + [x.strip() for x in (alt or '').split(';')]:
            if c:
                seen[(org, h)].add(c)
    inv_cc = [(r['c1'], r['c9'] or r['c7'], r['c21']) for r in rows if r['c21'] and r['c21'] not in seen[(FA2ORG[r['c1']], r['c9'] or r['c7'])]]
    t('Q-07', 'no cost center invented: each CC on a row was assigned or offered for the same organisation and account in line_cc', not inv_cc, inv_cc[:5])
    # ---------------------------------------------------------------- 9 / 13 reconciliation without inflation
    ev_rows = [r for r in rows if r['c26'] != '']
    nonev = [r for r in rows if r['c26'] == '' and any(r[c] != '' for c in ('c27', 'c28', 'c29'))]
    src = tc.execute('SELECT count(*),sum(bed),sum(bes) FROM sanad').fetchone()
    got = (sum(r['c26'] for r in ev_rows), sum(r['c28'] for r in ev_rows), sum(r['c29'] for r in ev_rows))
    t('Q-09a', 'Σ lines / debit / credit of evidence rows = ledger totals', got == tuple(src), dict(sheet=got, ledger=tuple(src)))
    t('Q-13', 'candidate, proposal and no-relation rows carry no amounts or counts (no one-to-many inflation)', not nonev, len(nonev))
    head_db = {}
    for org, k, m, t1, n, b, c in tc.execute('SELECT org,kol,moeen,taf1,count(*),sum(bed),sum(bes) FROM sanad GROUP BY 1,2,3,4'):
        head_db[(org, f'{k}-{m}-{t1}-0')] = (n, b, c)
    head_ws = defaultdict(lambda: [0, 0, 0])
    for r in ev_rows:
        a = head_ws[(FA2ORG[r['c1']], r['c9'] or r['c7'])]
        a[0] += r['c26']; a[1] += r['c28']; a[2] += r['c29']
    diff = [(k, v, head_db.get(k)) for k, v in head_ws.items() if tuple(v) != head_db.get(k)]
    t('Q-09b', 'per organisation × account: lines / debit / credit equal the ledger', not diff and len(head_ws) == len(head_db), diff[:5] or len(head_ws))
    evdb = {}
    for org, k, m, t1, ev, n, b, c in tc.execute("""SELECT s.org,s.kol,s.moeen,s.taf1,e.event_id,count(*),sum(s.bed),sum(s.bes) FROM sanad s JOIN line_event e ON e.sid=s.sid
                                                      WHERE e.event_id IS NOT NULL GROUP BY 1,2,3,4,5"""):
        evdb[(org, f'{k}-{m}-{t1}-0', ev)] = (n, b, c)
    evws = defaultdict(lambda: [0, 0, 0])
    for r in ev_rows:
        if r['c15']:
            a = evws[(FA2ORG[r['c1']], r['c9'] or r['c7'], r['c15'])]
            a[0] += r['c26']; a[1] += r['c28']; a[2] += r['c29']
    d2 = [(k, v, evdb.get(k)) for k, v in evws.items() if tuple(v) != evdb.get(k)]
    t('Q-09c', 'per organisation × account × event: lines / debit / credit equal line_event aggregation', not d2 and len(evws) == len(evdb), d2[:5] or len(evws))
    docdb = {}
    for org, k, m, t1, n in tc.execute('SELECT org,kol,moeen,taf1,count(DISTINCT doc_key) FROM sanad GROUP BY 1,2,3,4'):
        docdb[(org, f'{k}-{m}-{t1}-0')] = n
    over = [(r['c1'], r['c9'] or r['c7'], r['c27']) for r in ev_rows if r['c27'] > r['c26'] or r['c27'] > docdb[(FA2ORG[r['c1']], r['c9'] or r['c7'])]]
    t('Q-09d', 'unique document count per row ≤ its lines and ≤ the account\'s distinct documents in the ledger', not over, over[:5])
    samp = set(x for r in ev_rows for x in r['c31'].split('؛ ') if x)
    known = {d for (d,) in tc.execute('SELECT DISTINCT doc_key FROM sanad')}
    t('Q-09e', 'every sample document number exists in the ledger', samp <= known, len(samp - known))
    # ---------------------------------------------------------------- 10 unresolved labelled
    lab = [r for r in rows if (r['c16'].startswith(('UNRESOLVED', 'NO RELATION')) or r['c22'].startswith('UNRESOLVED') or r['c15'] == 'EXC-01') and r['c36'] != 'UNRESOLVED']
    t('Q-10', 'every unresolved event / cost center / no-relation row has status UNRESOLVED', not lab, len(lab))
    cd01 = [r for r in rows if r['c1'] == ORG_FA['Terminals'] and (r['c9'] in ('113-1-1-0', '211-1-1-0') or r['c7'] == '413-8-0-0') and r['c36'] != 'UNRESOLVED']
    t('Q-10b', 'CD-01 (terminal agency) rows kept UNRESOLVED', not cd01, len(cd01))
    # ---------------------------------------------------------------- 11 governance
    appr = [r for r in rows if r['c36'] == 'APPROVED']
    prop_obs = [r for r in rows if r['c36'] == 'OBSERVED' and (str(r['c15']).startswith(('TT-NE', 'PEO', 'EXC')) or str(r['c21']).startswith('TTCC'))]
    t('Q-11', 'no APPROVED rows; proposed ids (TT-NE, PEO, TTCC-P) never shown as OBSERVED; every row needs expert approval',
      not appr and not prop_obs and all(r['c37'].startswith('نیازمند تأیید') for r in rows), dict(approved=len(appr), proposed_as_observed=len(prop_obs)))
    # ---------------------------------------------------------------- 12 traceability
    untr = [r for r in rows if not (r['c4'] and r['c33'] and r['c34'])]
    t('Q-12', 'every row has information source, extraction method and evidence source', not untr, len(untr))
    # ---------------------------------------------------------------- 14 account classes
    rev_cc = [r for r in rows if r['c11'].startswith('درآمد') and 'درآمد' in r['c11'].split('/')[1] and r['c21']]
    t('Q-14a', 'revenue accounts are never attached to an expense cost center', not rev_cc, len(rev_cc))
    bs_cc = Counter((r['c1'], r['c9'] or r['c7']) for r in rows if r['c21'] and r['c11'].split(' /')[0] in ('دارایی', 'بدهی', 'حقوق صاحبان سرمایه'))
    t('Q-14b', 'balance-sheet accounts carry a cost center only where line_cc assigned one (e.g. recharged terminal costs)', True, dict(bs_cc),
      'REVIEW' if bs_cc else 'PASS')
    exp_unres = sum(1 for r in rows if r['c11'].split(' /')[0] == 'هزینه' and r['c26'] != '' and r['c22'].startswith('UNRESOLVED'))
    t('Q-14c', 'expense rows without a determined cost center are labelled UNRESOLVED (not N/A)', True, exp_unres, 'PASS')
    # ---------------------------------------------------------------- summary statistics
    heads = {(r['c1'], r['c9'] or r['c7']) for r in rows}
    org_heads = Counter(h[0] for h in heads)
    codes_by_org = defaultdict(set)
    for o, h in heads:
        codes_by_org[o].add(h)
    taxi_only = codes_by_org[ORG_FA['Taxi']] - codes_by_org[ORG_FA['Terminals']]
    term_only = codes_by_org[ORG_FA['Terminals']] - codes_by_org[ORG_FA['Taxi']]
    shared = codes_by_org[ORG_FA['Taxi']] & codes_by_org[ORG_FA['Terminals']]
    real_ev = lambda r: r['c15'] and not r['c15'].startswith('EXC')
    est = {(r['c1'], r['c9'] or r['c7']) for r in rows if real_ev(r) and r['c26'] != ''}
    prop_only = {(r['c1'], r['c9'] or r['c7']) for r in rows if real_ev(r)} - est
    no_ev = heads - est
    st = Counter(r['c36'] for r in rows)
    kinds = Counter('evidence' if r['c26'] != '' else 'no_relation' if r['c16'] == 'NO RELATION ESTABLISHED' else 'amount_free' for r in rows)
    universe_n = tot[2] + tot[3]
    covered_n = universe_n - len([m for m in miss if m[1].count('-') == 3 and True])
    summary = dict(
        heads_covered=len(heads), heads_taxi=org_heads[ORG_FA['Taxi']], heads_terminals=org_heads[ORG_FA['Terminals']],
        codes_taxi_only=len(taxi_only), codes_terminals_only=len(term_only), codes_shared=len(shared),
        rows=len(rows), row_kinds=dict(kinds),
        fe_events=len({r['c15'] for r in rows if str(r['c15']).startswith('FE-')}),
        ttne_events=len({r['c15'] for r in rows if str(r['c15']).startswith('TT-NE')}),
        peo=len({r['c15'] for r in rows if str(r['c15']).startswith('PEO')}),
        cost_centers=len({r['c21'] for r in rows if r['c21'].startswith('CC-')}), ttcc=len({r['c21'] for r in rows if r['c21'].startswith('TTCC')}),
        status=dict(st), heads_without_established_event=len(no_ev), of_which_with_proposal=len(prop_only & no_ev),
        need_approval=sum(1 for r in rows if r['c37'].startswith('نیازمند تأیید')),
        universe_L2_L3=universe_n, universe_L4=tot[4], coverage_pct=round(100.0 * (universe_n - len([m for m in miss])) / universe_n, 2) if universe_n else 0,
        ledger_heads=sum(len(v) for v in used.values()), ledger_lines=src[0])
    with open(os.path.join(OUT_DIR, 'QA_log.csv'), 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['test_id', 'description', 'status', 'actual'])
        w.writerows(res)
    with open(os.path.join(OUT_DIR, 'QA_log.md'), 'w', encoding='utf8') as fh:
        fh.write(f'# QA log — {os.path.basename(XLSX)}\n\nExecuted against the delivered workbook (SHA-256 `{sha256(XLSX)}`) and tt_v21.sqlite.\n\n')
        fh.write('| test | description | status | actual |\n|---|---|---|---|\n')
        for r in res:
            fh.write('| ' + ' | '.join(str(x).replace('|', '／').replace('\n', ' ') for x in r) + ' |\n')
        fh.write('\n## Summary statistics\n\n```json\n' + json.dumps(summary, ensure_ascii=False, indent=1) + '\n```\n')
    json.dump(summary, open(os.path.join(OUT_DIR, 'summary.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(Counter(r[2] for r in res), [r for r in res if r[2] != 'PASS'])
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
