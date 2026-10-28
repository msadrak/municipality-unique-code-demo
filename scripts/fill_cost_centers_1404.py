"""Fill AF:AI cost-center columns in the 1404 journal via streaming OOXML edit."""
from __future__ import annotations
import json, re, zipfile, copy
from xml.sax.saxutils import escape, quoteattr

SRC = r'C:/Users/sadra/Desktop/دفتر روزنامه 1404 - با اشخاص جدید.xlsx'
DST = r'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_تکمیل_شده.xlsx'
MAIN = 'xl/worksheets/sheet1.xml'

ROW = re.compile(rb'<row\b[^>]*>.*?</row>', re.S)
CELL = re.compile(rb'<c\b[^>]*?(?:/>|>.*?</c>)', re.S)
ADDR = re.compile(rb'\br="([A-Z]+)(\d+)"')
VALUE = re.compile(rb'<v>(.*?)</v>', re.S)

maps = json.load(open('cc_maps.json', encoding='utf-8'))
L1 = maps['l1']
l2full = json.load(open('l2_full.json', encoding='utf-8'))
BMAP = maps['bmap']
UNAM = set(maps['unam'])

def norm(s):
    return re.sub(r'\s+', ' ', str(s or '').replace('\xa0', ' ').replace('\u200c', ' ')
                  .replace('ي', 'ی').replace('ك', 'ک')).strip()

def load_shared(z):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(z.read('xl/sharedStrings.xml'))
    return [''.join(e.itertext()) for e in root]

def decode_row(raw, shared):
    out = {}
    for m in CELL.finditer(raw):
        cell = m.group(); a = ADDR.search(cell)
        if not a: continue
        v = VALUE.search(cell); col = a[1].decode()
        if b't="s"' in cell: out[col] = shared[int(v[1])] if v else None
        elif b't="inlineStr"' in cell:
            import xml.etree.ElementTree as ET
            e = ET.fromstring(cell)
            out[col] = ''.join(t.text or '' for t in e.iter() if t.tag.split('}')[-1] == 't')
        elif v: out[col] = v[1].decode()
        else: out[col] = None
    return out

def colkey(c):
    n = 0
    for ch in c: n = n * 26 + ord(ch) - 64
    return n

def inline_cell(address, value, style):
    return ('<c r=' + quoteattr(address) + ' s=' + quoteattr(style) +
            ' t="inlineStr"><is><t xml:space="preserve">' + escape(str(value)) +
            '</t></is></c>').encode('utf-8')

def mutate_row(raw, rn, changes):
    if not changes: return raw
    cells = list(CELL.finditer(raw))
    if not cells: return raw
    out = []; done = set()
    for m in cells:
        cell = m.group(); a = ADDR.search(cell)
        col = a[1].decode() if a else ''
        for c in sorted((c for c in changes if c not in done and colkey(c) < colkey(col)), key=colkey):
            v, st = changes[c]; out.append(inline_cell(f'{c}{rn}', v, st)); done.add(c)
        if col in changes:
            v, st = changes[col]; out.append(inline_cell(f'{col}{rn}', v, st)); done.add(col)
        else:
            out.append(cell)
    for c in sorted((c for c in changes if c not in done), key=colkey):
        v, st = changes[c]; out.append(inline_cell(f'{c}{rn}', v, st))
    head = raw[:cells[0].start()]
    return head + b''.join(out) + b'</row>'

stats = dict(eligible=0, pre_complete=0, codes_filled=0, name_filled=0,
             verified=0, proposed=0, unresolved=0, no_budget_rows=0)
review = []

zin = zipfile.ZipFile(SRC)
shared = load_shared(zin)

def process(raw):
    m = re.search(rb'<row\b[^>]*\br="(\d+)"', raw)
    rn = int(m[1])
    if rn < 6: return raw
    d = decode_row(raw, shared)
    if not any(v not in (None, '') for v in d.values()): return raw
    af, ag, ah, ai = norm(d.get('AF')), norm(d.get('AG')), norm(d.get('AH')), norm(d.get('AI'))
    bc = norm(d.get('W'))
    if bc in ('NULL', 'None'): bc = ''
    has_amt = bool(d.get('Q') or d.get('R'))
    if has_amt: stats['eligible'] += 1
    if af and ag and ah and ai:
        stats['pre_complete'] += 1
        return raw
    changes = {}
    if ag and ai and not af and not ah:
        c1 = L1.get(ag); l2 = l2full.get(ai)
        if c1 and l2 and l2[0] == c1:
            changes['AF'] = (c1, '0'); changes['AH'] = (l2[2], '0')
            stats['codes_filled'] += 1; stats['verified'] += 1
        elif c1 and l2:
            # inconsistent pair; fix both names+codes coherently (keep AI's L2 as truth)
            changes['AF'] = (l2[0], '0'); changes['AG'] = (l2[1], '0')
            changes['AH'] = (l2[2], '0')
            stats['codes_filled'] += 1; stats['proposed'] += 1
            review.append([rn, norm(d.get('T'))[:200], f'{l2[1]} / {ai}',
                           'AG/AI pair inconsistent; aligned L1 to L2', 'AG+AI names', 'Proposed'])
        else:
            stats['unresolved'] += 1
            if len(review) < 30000:
                review.append([rn, norm(d.get('T'))[:200], f'{ag} / {ai}',
                               'Name not found in cost center master', 'AG/AI names', 'Unresolved'])
    elif not ag and not ai:
        if bc and bc in BMAP:
            c1, n1, c2, n2 = BMAP[bc]
            changes['AF'] = (c1, '0'); changes['AG'] = (n1, '0')
            changes['AH'] = (c2, '0'); changes['AI'] = (n2, '0')
            stats['name_filled'] += 1
            if bc in UNAM:
                stats['verified'] += 1
            else:
                stats['proposed'] += 1
                if len(review) < 30000:
                    review.append([rn, norm(d.get('T'))[:200], f'{n1} / {n2}',
                                   'Budget code maps to multiple cost centers; majority assignment',
                                   f'Budget code {bc}', 'Proposed'])
        elif has_amt:
            stats['unresolved'] += 1
            if len(review) < 30000:
                review.append([rn, norm(d.get('T'))[:200], '',
                               'No budget code' if not bc else f'Budget code {bc} not in mapping',
                               f'kol={norm(d.get("M"))} | moein={norm(d.get("N"))}', 'Unresolved'])
        else:
            stats['no_budget_rows'] += 1
    else:
        # partial state (name only at one level) — try to repair via known maps
        stats['unresolved'] += 1
        if len(review) < 30000:
            review.append([rn, norm(d.get('T'))[:200], f'{ag} / {ai}',
                           'Partial cost center data', 'AF:AI', 'Unresolved'])
    return mutate_row(raw, rn, changes)

# --- stream sheet1, rewrite ---
out_path = 'sheet1_new.xml'
with zin.open(MAIN) as f, open(out_path, 'wb') as out:
    buf = b''
    started = False
    tail_done = False
    while True:
        chunk = f.read(8 * 1024 * 1024)
        if chunk: buf += chunk
        # find complete rows in buf; keep trailing partial
        last_end = 0
        for m in ROW.finditer(buf):
            last_end = m.end()
        if last_end:
            seg = buf[:last_end]
            # everything up to first row start is header prefix
            first = seg.find(b'<row')
            if first == -1:
                out.write(seg); buf = buf[last_end:]; continue
            out.write(seg[:first])
            pos = first
            for m in ROW.finditer(seg):
                # write any inter-row gap verbatim
                if m.start() > pos: out.write(seg[pos:m.start()])
                out.write(process(m.group()))
                pos = m.end()
            buf = seg[pos:] + buf[last_end:]
        if not chunk:
            out.write(buf); break
zin.close()
print(json.dumps(stats, ensure_ascii=False))
json.dump(review, open('cc_review.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('review rows:', len(review))
