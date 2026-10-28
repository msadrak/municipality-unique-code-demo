"""v2 — independent recalculation of the source-calculable KPI numerators/denominators straight from the ORIGINAL Sanad workbooks.

Deliberately shares NO classification code with the pipeline: document kinds, fines, grants, school share and bank fees are re-derived here from
raw text/account fields with their own regular expressions.  Output: WORK/kpi_independent_v2.json  (metric -> window -> value)
"""
import sys, os, re, json, collections
import openpyxl
sys.path.insert(0, os.path.dirname(__file__))
from common import ORGS, YEARS, src_path, norm, WORK

R_OPEN, R_CLOSE = re.compile('افتتاح'), re.compile('اختتام')
R_TEMP = re.compile(r'بستن حساب\s?(?:ها|های)?\s?موقت')
R_PL = re.compile('سود و زیان جاری به انباشته')
R_NET = re.compile(r'بستن حساب\s?(?:ها|های)?\s?شهرداری')
R_PREREC = re.compile(r'بستن حساب\s?(?:ها|های)?\s?پیش ?دریافت')
R_BONUS = re.compile('پاداش بستن حساب')

def load(org, fy):
    wb = openpyxl.load_workbook(src_path(org, fy, 'Sanad'), read_only=True)
    it = wb.worksheets[0].iter_rows(values_only=True); hdr = next(it); ix = {h: i for i, h in enumerate(hdr)}
    rows = []
    for r in it:
        if all(c is None for c in r): continue
        rows.append(dict(num=str(r[ix['Sanad_Num']]).strip(), date=str(r[ix['Date']]).strip(), des=norm(r[ix['Des']]), sharh=norm(r[ix['Sharh']]), kol=str(r[ix['Kol']]).strip(),
                         moeen=str(r[ix['Moeen']]).strip(), t1=str(r[ix['Tafsili1']]).strip(), bed=int(r[ix['Bed']]), bes=int(r[ix['Bes']]), vahed=r[ix['CodeVahed']]))
    wb.close(); return rows

def kinds(rows):
    k = {}
    for r in rows:
        d = r['des']; kind = 'REGULAR'
        if R_OPEN.search(d): kind = 'OPENING'
        elif R_CLOSE.search(d): kind = 'CLOSING'
        elif R_TEMP.search(d) or R_PL.search(d): kind = 'CLOSING'
        elif R_NET.search(d): kind = 'NETTING'
        if kind != 'REGULAR' or r['num'] not in k: k[r['num']] = kind if kind != 'REGULAR' else k.get(r['num'], 'REGULAR')
    return k

out = collections.defaultdict(dict)
data = {}
for org in ORGS:
    for fy in YEARS:
        rows = load(org, fy); kk = kinds(rows)
        for r in rows: r['kind'] = kk[r['num']]
        data[(org, fy)] = rows

# window by posting density (same stated rule, own implementation): longest prefix m1..k with docs1405_m >= 50% docs1404_m and m < last month
win = {}
for org in ORGS:
    docs = {}
    for fy in YEARS:
        c = collections.defaultdict(set)
        for r in data[(org, fy)]:
            if r['kind'] == 'REGULAR': c[int(r['date'][5:7])].add(r['num'])
        docs[fy] = {m: len(v) for m, v in c.items()}
    last = max(int(r['date'][5:7]) for r in data[(org, '1405')])
    k = 0
    for m in range(1, 13):
        if m >= last: break
        a, b = docs['1404'].get(m, 0), docs['1405'].get(m, 0)
        if a > 0 and b >= 0.5 * a: k = m
        else: break
    win[org] = k

def S(rows, pred, f, kmax=12):
    return sum(f(r) for r in rows if r['kind'] == 'REGULAR' and int(r['date'][5:7]) <= kmax and pred(r))

is_fine = lambda r: 'جریمه' in r['sharh']
is_share = lambda r: (('2%' in r['sharh'] or '2 %' in r['sharh']) and 'سهم سرویس' in (r['sharh'] + ' ' + r['des'])) or bool(R_PREREC.search(r['des']))
is_grant = lambda r: 'کمک بودجه' in (r['sharh'] + ' ' + r['des'])
for fy, wn in (('1404', 'FULL_YEAR'), ('1404', 'WINDOW'), ('1405', 'WINDOW'), ('1405', 'ALL_AVAILABLE')):
    kmax = 12
    k = win['Taxi'] if wn == 'WINDOW' else 12
    rows = data[('Taxi', fy)]
    rev = lambda p: S(rows, p, lambda r: r['bes'] - r['bed'], k)
    exp = lambda p: S(rows, p, lambda r: r['bed'] - r['bes'], k)
    T = {}
    T['T_REV_TOTAL'] = rev(lambda r: r['kol'] in ('413', '812'))
    share = rev(lambda r: r['kol'] == '413' and is_share(r))
    T['T_REV_SCHOOL_SHARE'] = share
    T['T_REV_FINES'] = rev(lambda r: r['kol'] == '413' and r['moeen'] == '1' and is_fine(r) and not is_share(r))
    T['T_REV_GRANT'] = rev(lambda r: r['kol'] == '413' and r['moeen'] == '8' and is_grant(r) and not is_share(r))
    T['T_REV_FEES_413_1'] = rev(lambda r: r['kol'] == '413' and r['moeen'] == '1' and not is_fine(r) and not is_share(r))
    T['T_EXP_OP'] = exp(lambda r: r['kol'] in ('611', '612', '613') and not (r['kol'] == '613' and r['moeen'] == '20'))
    T['T_EXP_PAYROLL'] = exp(lambda r: r['kol'] == '611')
    T['T_EXP_BANKFEE'] = exp(lambda r: r['kol'] == '612' and r['moeen'] == '5' and r['t1'] == '12' and re.search('کارمزد|کارزمد|کارمکزد', r['sharh'] or r['des']))
    T['T_EXP_BANKLEGAL_ACCOUNT'] = exp(lambda r: r['kol'] == '612' and r['moeen'] == '5' and r['t1'] == '12')
    for m, v in T.items(): out[m][f'Taxi|{fy}|{wn}'] = v
    rows = data[('Terminals', fy)]
    k = win['Terminals'] if wn == 'WINDOW' else 12
    out['M_BILLED'][f'Terminals|{fy}|{wn}'] = S(rows, lambda r: r['kol'] == '113' and r['moeen'] == '1' and r['t1'] in ('4', '8'), lambda r: r['bed'], k)
    out['M_COLLECTED'][f'Terminals|{fy}|{wn}'] = S(rows, lambda r: r['kol'] == '113' and r['moeen'] == '1' and r['t1'] in ('4', '8'), lambda r: r['bes'], k)
# stocks: deposits 212-6 = opening + regular (+ netting) movements; AR 113-1-4/8 (assessments receivable) likewise
for org in ORGS:
    for fy in YEARS:
        rows = data[(org, fy)]
        out['B_DEPOSITS'][f'{org}|{fy}|END_OF_AVAILABLE_DATA'] = sum(r['bes'] - r['bed'] for r in rows if r['kol'] == '212' and r['moeen'] == '6' and r['kind'] in ('OPENING', 'REGULAR', 'NETTING'))
        if org == 'Terminals':
            out['B_AR_ASSESSED'][f'{org}|{fy}|END_OF_AVAILABLE_DATA'] = sum(r['bed'] - r['bes'] for r in rows if r['kol'] == '113' and r['moeen'] == '1' and r['t1'] in ('4', '8') and r['kind'] in ('OPENING', 'REGULAR', 'NETTING'))
# terminal billed per facility (first CodeVahed segment), FULL 1404
fac = collections.Counter()
for r in data[('Terminals', '1404')]:
    if r['kind'] == 'REGULAR' and r['kol'] == '113' and r['moeen'] == '1' and r['t1'] in ('4', '8') and r['vahed']:
        fac[str(r['vahed']).split('-')[0]] += r['bed']
out['M_BILLED_BY_FACILITY']['Terminals|1404|FULL_YEAR'] = dict(fac)
json.dump(dict(window_k=win, metrics=out), open(f'{WORK}/kpi_independent_v2.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('window', win)
for m, d in out.items():
    if m != 'M_BILLED_BY_FACILITY': print(m, d)
