"""Phase 1 — extract the municipality 1404 account taxonomy (new + old coding) observed in the municipality journal.
Source: data/work/fe_model/journal_v4.pkl (the 337,268-row 1404 municipality journal used by the financial-event pipeline).
Output: WORK/municipality_chart.json  (distinct class/kol/moin with titles and row counts; observed, not authoritative)."""
import pickle, json, collections, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from common import *
d = pickle.load(open(f'{ROOT}/data/work/fe_model/journal_v4.pkl', 'rb'))
rows = d['rows']
def g(r, i): return r[1 + i]
def s(v): return '' if v is None else str(v).strip()
new = collections.Counter(); old = collections.Counter()
for r in rows:
    new[(s(g(r,23)), s(g(r,24)), s(g(r,25)), s(g(r,26)), s(g(r,27)), s(g(r,28)))] += 1
    old[(s(g(r,8)), s(g(r,12)), s(g(r,9)), s(g(r,13)))] += 1
out = {'rows': len(rows),
       'new_coding': [dict(cls=k[0], cls_title=k[1], kol=k[2], kol_title=k[3], moin=k[4], moin_title=k[5], n=v) for k, v in sorted(new.items())],
       'old_coding': [dict(okol=k[0], okol_title=k[1], omoin=k[2], omoin_title=k[3], n=v) for k, v in sorted(old.items())]}
json.dump(out, open(f'{WORK}/municipality_chart.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(len(rows), len(new), len(old))
for k, v in sorted(new.items())[:200]: print(k, v)
