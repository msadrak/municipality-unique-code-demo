import pickle, json
from collections import Counter
d = pickle.load(open('zz_v3.pkl', 'rb')); R = d['rows']
L = pickle.load(open('zz_lineage.pkl', 'rb'))
def b(v): return v is None or (isinstance(v, str) and v.strip() in ('', 'NULL'))
def s(v): return '' if v is None else str(v).strip()
cat = Counter(); v3add = []; mism = 0
for r in R:
    rn = r[0]; o = L[rn]
    v3 = r[23:27]
    if all(b(x) for x in v3):
        if not all(b(x) for x in o[4:8]): cat['v1_filled_but_v3_blank'] += 1
        continue
    src_names = not b(o[1]) or not b(o[3])
    v1_full = not any(b(x) for x in o[4:8])
    if src_names and v1_full: k = 'A_source_names+v1_codes'
    elif src_names: k = 'B_source_names+v3_codes'
    elif v1_full: k = 'C_v1_native_enrichment'
    else: k = 'D_v3_added'; v3add.append(rn)
    cat[(k, s(r[17]))] += 1
    if v1_full and tuple(s(x) for x in o[4:8]) != tuple(s(x) for x in v3): mism += 1
print(cat); print('v3 differs from v1 where v1 full:', mism)
# D population profile
D = [r for r in R if r[0] in set(v3add)]
print('D', len(D))
print(Counter(s(r[3]) for r in D).most_common(5))
print(Counter((s(r[25]), s(r[26])) for r in D).most_common(40))
print(Counter(s(r[11]) for r in D).most_common(40))
json.dump(v3add, open('zz_v3add.json', 'w'))
