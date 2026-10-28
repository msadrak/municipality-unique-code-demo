import zipfile, re, codecs, pickle, json, time, openpyxl
from collections import Counter
V3 = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_فعالیت_محور_v3.xlsx'
V4 = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_فعالیت_محور_v4.xlsx'
t0 = time.time()
P = pickle.load(open('zz_decisions.pkl', 'rb')); DEC, NATIVE = P['DEC'], P['NATIVE']
CHANGE = {rn: d for rn, d in DEC.items() if d.get('action') in ('WRITE', 'CORRECT', 'CLEAR')}
z3, z4 = zipfile.ZipFile(V3), zipfile.ZipFile(V4)
res = {}
# 1. ZIP integrity + member identity
res['zip_test_v4'] = z4.testzip()
n3 = [i.filename for i in z3.infolist()]; n4 = [i.filename for i in z4.infolist()]
res['same_members_same_order'] = n3 == n4
changed_members = [n for n in n3 if n != 'xl/worksheets/sheet1.xml' and z3.read(n) != z4.read(n)]
res['changed_members_other_than_sheet1'] = changed_members
# 2. row-level XML comparison of the main sheet
CELL = re.compile(r'<c r="([A-Z]+)\d+"(?:[^>]*?/>|[^>]*?>.*?</c>)', re.S)
def rows(z):
    dec = codecs.getincrementaldecoder('utf-8')(); buf = ''; head = None
    with z.open('xl/worksheets/sheet1.xml') as f:
        while True:
            ch = f.read(16 * 1024 * 1024)
            buf += dec.decode(ch, final=not ch)
            pos = 0
            while True:
                i = buf.find('<row ', pos)
                if i < 0: break
                j = buf.find('</row>', i)
                if j < 0: break
                if head is None: head = buf[:i]; yield ('HEAD', head)
                yield (int(re.match(r'<row r="(\d+)"', buf[i:i + 30]).group(1)), buf[i:j + 6]); pos = j + 6
            buf = buf[pos:]
            if not ch: yield ('TAIL', buf); return
stat = Counter(); bad = []
for (k3, r3), (k4, r4) in zip(rows(z3), rows(z4)):
    if k3 != k4: bad.append(('order', k3, k4)); break
    if k3 in ('HEAD', 'TAIL') or k3 not in CHANGE:
        if r3 != r4: bad.append(('diff', k3))
        stat['identical'] += 1; continue
    keep3 = [c.group(0) for c in CELL.finditer(r3) if c.group(1) not in ('AF', 'AG', 'AH', 'AI')]
    keep4 = [c.group(0) for c in CELL.finditer(r4) if c.group(1) not in ('AF', 'AG', 'AH', 'AI')]
    if keep3 != keep4 or r3.split('>', 1)[0] != r4.split('>', 1)[0]: bad.append(('nontarget', k3))
    stat['changed_rows_nontarget_identical'] += 1
res['xml_compare'] = dict(stat); res['xml_problems'] = bad[:20]; res['xml_problem_count'] = len(bad)
# 3. value-level checks via openpyxl
wb = openpyxl.load_workbook(V4, read_only=True, data_only=False)
res['sheets'] = wb.sheetnames
ws = wb['کدینگ جامع 1404 شهرداری']
pairs1 = {(v[0], v[1]) for v in NATIVE.values()}; pairs2 = {(v[2], v[3]) for v in NATIVE.values()}
vc = Counter(); probs = []; complete = 0; allpairs = Counter()
for rn, r in enumerate(ws.iter_rows(min_row=6, min_col=32, max_col=35, values_only=True), start=6):
    v = tuple('' if c is None else str(c) for c in r)
    if all(x.strip() for x in v): complete += 1
    if any('CC-' in x for x in v): probs.append(('cc_in_native', rn))
    d = CHANGE.get(rn)
    if not d: continue
    if d['action'] == 'CLEAR':
        vc['clear_ok' if not any(x.strip() for x in v) else 'clear_bad'] += 1; continue
    exp = NATIVE[d['native']]
    ok = v == tuple(exp) and (v[0], v[1]) in pairs1 and (v[2], v[3]) in pairs2 and v[2].startswith(v[0].zfill(2))
    vc['written_ok' if ok else 'written_bad'] += 1
    if not ok: probs.append(('value', rn, v, exp))
res['value_checks'] = dict(vc); res['value_problems'] = probs[:20]; res['v4_complete_AF_AI'] = complete
# 4. review sheet traceability
rv = wb['Cost_Center_Review']; seen = set(); rstat = Counter()
for r in rv.iter_rows(min_row=2, values_only=True):
    seen.add(int(r[0])); rstat[r[26]] += 1
res['review_rows'] = sum(rstat.values()); res['review_status'] = dict(rstat)
res['changed_rows_missing_from_review'] = len([rn for rn in CHANGE if rn not in seen])
res['secs'] = round(time.time() - t0)
json.dump(res, open('zz_verify.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
