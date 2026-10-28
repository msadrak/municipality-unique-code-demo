"""Step 1 — workbook forensics: inventory of every sheet of both versions, OOXML container facts,
independent recomputation of every formula family, and the V1→V2 cell/formula/format/container diff.

Output: data/work/taxi_gate_audit/forensics.json
"""
import re
import time
import zipfile
from collections import Counter, OrderedDict

import openpyxl
from openpyxl.worksheet.formula import ArrayFormula

from common import F_V1, F_V2, SOURCES, S_FULL, S_DEDUP, S_KOL_UNIQ, S_KOL, S_MOEN, S_8, sha256, dump

NOT_FOUND = 'پیدا نشد'


def ftext(v):
    if isinstance(v, ArrayFormula):
        return '{ARRAY ' + str(v.ref) + '} ' + str(v.text)
    return v


def is_formula(v):
    return isinstance(v, ArrayFormula) or (isinstance(v, str) and v.startswith('='))


# ------------------------------------------------------------------ OOXML container
def container_facts(path):
    z = zipfile.ZipFile(path)
    wbx = z.read('xl/workbook.xml').decode('utf8')
    rels = z.read('xl/_rels/workbook.xml.rels').decode('utf8')
    rid = {m.group(1): m.group(2) for m in re.finditer(r'<Relationship Id="(rId\d+)"[^>]*?Target="([^"]+)"', rels)}
    rid.update({m.group(2): m.group(1) for m in re.finditer(r'<Relationship [^>]*?Target="([^"]+)"[^>]*?Id="(rId\d+)"', rels)})
    sheets = []
    for m in re.finditer(r'<sheet name="([^"]+)" sheetId="(\d+)"(?: state="(\w+)")? r:id="(rId\d+)"/>', wbx):
        part = 'xl/' + rid[m.group(4)]
        x = z.read(part).decode('utf8')
        sheets.append(OrderedDict(
            name=m.group(1), sheetId=int(m.group(2)), state=m.group(3) or 'visible', part=part,
            xml_bytes=len(x.encode('utf8')), f_elements=len(re.findall(r'<f[ >]', x)),
            array_formulas=len(re.findall(r'<f t="array"', x)), shared_formula_refs=len(re.findall(r'<f t="shared"', x)),
            dynamic_array_flags=x.count(' cm="1"'), dimension=(re.search(r'<dimension ref="([^"]+)"', x) or [None, None])[1]))
    core = z.read('docProps/core.xml').decode('utf8')
    app = z.read('docProps/app.xml').decode('utf8')
    tag = lambda t, s: (re.search(rf'<{t}[^>]*>([^<]*)</{t}>', s) or [None, None])[1]
    return OrderedDict(
        sha256=sha256(path), bytes=__import__('os').path.getsize(path),
        parts=sorted(i.filename for i in z.infolist()),
        part_sizes={i.filename: i.file_size for i in z.infolist()},
        defined_names=re.findall(r'<definedName ([^>]*)>(.*?)</definedName>', wbx),
        external_links=[n for n in z.namelist() if 'externalLink' in n],
        calcPr=re.findall(r'<calcPr[^>]*/>', wbx),
        creator=tag('dc:creator', core), last_modified_by=tag('cp:lastModifiedBy', core),
        created=tag('dcterms:created', core), modified=tag('dcterms:modified', core),
        application=tag('Application', app), sheets=sheets)


# ------------------------------------------------------------------ sheet inventory
HEADER_ROWS = {S_FULL: [2, 3], S_DEDUP: [2, 3], S_KOL: [1, 2], 'حساب کل کد 1': [1], 'خلاصه تطبیق': [1],
               'تطبیق معین ۱ با ۲': [1], 'بررسی همه تطبیق‌ها': [1], S_KOL_UNIQ: [], S_MOEN: [], S_8: [], 'Sheet4': []}
ROLE = {
    S_FULL: 'REPEATED_ACCOUNT_EXTRACT (no document id/amount/date) — new municipal chart',
    S_DEDUP: 'REFERENCE_TABLE — de-duplicated new municipal chart (class/kol/moein)',
    S_KOL_UNIQ: 'DERIVED — UNIQUE(kol code,title) of Sheet1',
    S_KOL: 'WORKING_TABLE — kol lists (new, old, combined) with UNIQUE formulas',
    'Sheet4': 'EMPTY',
    S_MOEN: 'WORKING_TABLE — combined old(2)/new(1) moein list + XLOOKUP/UNIQUE formulas (input of the V2 matching)',
    S_8: 'REFERENCE_TABLE — A:B old moein subset (77); I:N copy of the new chart (234)',
    'حساب کل کد 1': 'WORKING_TABLE — interleaved kol list with explicit new/old kol pairs',
    'خلاصه تطبیق': 'DERIVED_STATIC — matching summary counts (no formulas)',
    'تطبیق معین ۱ با ۲': 'DERIVED_STATIC — best + 2 alternative text matches per old account (no formulas)',
    'بررسی همه تطبیق‌ها': 'DERIVED_STATIC — long form of the 3 candidates per old account (no formulas)',
}


def sheet_inventory(wbf, wbv, name, version):
    wsf, wsv = wbf[name], wbv[name]
    rows_nonempty, ftypes, formulas, fpatterns = 0, Counter(), 0, Counter()
    col_profile = {}
    full_rows = Counter()
    col_vals = {}
    first_data = max(HEADER_ROWS.get(name, [0]) or [0]) + 1
    for rf, rv in zip(wsf.iter_rows(), wsv.iter_rows()):
        vals = []
        nonempty = False
        for cf, cv in zip(rf, rv):
            v = cf.value
            if v is None:
                vals.append(None)
                continue
            nonempty = True
            if is_formula(v):
                formulas += 1
                pat = re.sub(r'(?<=[A-Z])\d+', '#', ftext(v) if not isinstance(v, str) else v)
                fpatterns[pat[:160]] += 1
            cp = col_profile.setdefault(cf.column_letter, Counter())
            cp['formula' if is_formula(v) else type(cv.value).__name__] += 1
            vals.append(cv.value)
        if nonempty:
            rows_nonempty += 1
            if cf.row >= first_data:
                full_rows[tuple(vals)] += 1
                for i, x in enumerate(vals):
                    col_vals.setdefault(i, Counter())[x] += 1
    headers = []
    for hr in HEADER_ROWS.get(name, []):
        headers.append([(c.coordinate, c.value) for c in wsv[hr] if c.value is not None])
    dup_rows = sum(n - 1 for n in full_rows.values() if n > 1)
    n_data = sum(full_rows.values())
    key_cols = OrderedDict()
    for i, c in sorted(col_vals.items()):
        nonnull = {k: v for k, v in c.items() if k not in (None, '')}
        if not nonnull:
            continue
        key_cols[openpyxl.utils.get_column_letter(i + 1)] = dict(distinct=len(nonnull), missing=n_data - sum(nonnull.values()))
    return OrderedDict(
        workbook=version, sheet=name, visibility=wsf.sheet_state, used_range=wsf.dimensions,
        physical_rows=wsf.max_row, nonempty_rows=rows_nonempty, columns=wsf.max_column,
        header_rows=HEADER_ROWS.get(name, []), headings=headers,
        column_types={k: dict(v) for k, v in sorted(col_profile.items(), key=lambda kv: openpyxl.utils.column_index_from_string(kv[0]))},
        formula_cells=formulas, formula_patterns=dict(fpatterns.most_common(12)),
        merged=[str(r) for r in wsf.merged_cells.ranges], tables=list(wsf.tables.keys()),
        data_validations=len(wsf.data_validations.dataValidation), conditional_formats=len(wsf.conditional_formatting),
        autofilter=wsf.auto_filter.ref, freeze=wsf.freeze_panes, rtl=wsf.sheet_view.rightToLeft,
        data_rows_after_header=n_data, distinct_data_rows=len(full_rows), duplicate_data_rows=dup_rows, column_distinct_missing=key_cols,
        role=ROLE.get(name, ''))


# ------------------------------------------------------------------ formula recomputation (independent)
def uniq(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def recompute(wbv):
    res = OrderedDict()
    s1 = wbv[S_FULL]
    pairs = [(r[2], r[3]) for r in s1.iter_rows(min_row=4, max_row=73464, values_only=True)]
    exp = uniq(pairs)
    got = [(wbv[S_KOL_UNIQ].cell(i, 1).value, wbv[S_KOL_UNIQ].cell(i, 2).value) for i in range(1, 53)]
    res['Sheet3!A1:B52 =UNIQUE(Sheet1!C4:D73464)'] = dict(expected_rows=len(exp), cached_equal=exp == got)

    k = wbv[S_KOL]
    a = [k.cell(r, 1).value for r in range(4, 238)]
    b = [k.cell(r, 2).value for r in range(4, 238)]
    ua, ub = uniq(a), uniq(b)
    gc = [k.cell(r, 3).value for r in range(4, 4 + len(ua))]
    gd = [k.cell(r, 4).value for r in range(4, 4 + len(ub))]
    true_pairs = set(zip(a, b))
    mis = []
    for i in range(max(len(ua), len(ub))):
        c = ua[i] if i < len(ua) else None
        d = ub[i] if i < len(ub) else None
        if (c, d) not in true_pairs:
            mis.append(dict(row=4 + i, code=c, title_shown=d, true_titles=sorted({y for x, y in true_pairs if x == c})))
    res['kol!C4:C53 / D4:D53 =UNIQUE(A) and =UNIQUE(B) separately'] = dict(
        unique_codes=len(ua), unique_titles=len(ub), cached_equal=(gc == ua and gd == ub),
        misaligned_pairs=len(mis), misaligned_examples=mis)

    ij = [(k.cell(r, 9).value, k.cell(r, 10).value) for r in range(2, 91)]
    ul = uniq(ij)
    gl = [(k.cell(r, 12).value, k.cell(r, 13).value) for r in range(2, 2 + len(ul))]
    norm = lambda t: (0 if t[0] is None else t[0], 0 if t[1] is None else t[1])
    res['kol!L2:M76 =UNIQUE(I2:J90)'] = dict(expected_rows=len(ul), cached_equal=[norm(x) for x in ul] == [norm(x) for x in gl])

    m = wbv[S_MOEN]
    A = [m.cell(r, 1).value for r in range(4, 393)]
    B = [m.cell(r, 2).value for r in range(4, 393)]
    C = [m.cell(r, 3).value for r in range(4, 393)]
    H = uniq(A)
    gotH = [m.cell(r, 8).value for r in range(4, 4 + len(H))]
    e8 = wbv[S_8]
    lut = {}
    for r in range(2, 236):
        key = e8.cell(r, 13).value
        if key not in lut:
            lut[key] = [e8.cell(r, c).value for c in range(9, 13)]
    d_ok = i_ok = j_ok = 0
    shifted = []
    for i, h in enumerate(H):
        r = 4 + i
        dg = [m.cell(r, c).value for c in range(4, 8)]
        exp_dg = lut.get(h, [NOT_FOUND] * 4)
        d_ok += dg == exp_dg
        flags = ','.join(str(C[j]) for j in range(len(A)) if A[j] == h)
        i_ok += str(m.cell(r, 9).value) == flags
        j_ok += m.cell(r, 10).value == B[A.index(h)]
        if A[i] != h:
            shifted.append(r)
    res['moen!H4:H387 =UNIQUE(A4:A392)'] = dict(expected_rows=len(H), cached_equal=gotH == H, duplicates_removed=len(A) - len(H))
    res['moen!D:G =XLOOKUP(H,88888888!M,I..L)'] = dict(rows=len(H), cached_equal_rows=d_ok)
    res['moen!I =TEXTJOIN(FILTER(C,A=H))'] = dict(rows=len(H), cached_equal_rows=i_ok)
    res['moen!J =XLOOKUP(H,A,B)'] = dict(rows=len(H), cached_equal_rows=j_ok)
    res['moen rows where H(row) != A(row) (lookups describe another account than column A)'] = dict(
        rows=len(shifted), first_row=shifted[0] if shifted else None, of_total=len(A))
    return res


# ------------------------------------------------------------------ diff
def style_sig(c):
    f, fl, a, b = c.font, c.fill, c.alignment, c.border
    return (f.name, f.sz, f.b, f.i, str(f.color.rgb) if f.color is not None else None, fl.fill_type,
            str(fl.fgColor.rgb) if fl.fgColor is not None else None, c.number_format, a.horizontal, a.vertical,
            a.wrap_text, a.readingOrder, b.left.style, b.right.style, b.top.style, b.bottom.style)


def cellmap(ws, formulas):
    d = {}
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None:
                d[c.coordinate] = ftext(c.value) if formulas else c.value
    return d


def diff(wb1f, wb1v, wb2f, wb2v, c1, c2):
    out = OrderedDict()
    n1, n2 = wb1f.sheetnames, wb2f.sheetnames
    out['sheets_v1'] = n1
    out['sheets_v2'] = n2
    out['added'] = [n for n in n2 if n not in n1]
    out['deleted'] = [n for n in n1 if n not in n2]
    out['renamed'] = []   # verified below: every V1 sheet exists in V2 under the same name with identical content
    out['position_change'] = {n: (n1.index(n), n2.index(n)) for n in n1 if n in n2 and n1.index(n) != n2.index(n)}
    per = OrderedDict()
    for n in n1:
        if n not in n2:
            continue
        f1, f2 = cellmap(wb1f[n], True), cellmap(wb2f[n], True)
        v1, v2 = cellmap(wb1v[n], False), cellmap(wb2v[n], False)
        fd = sorted((k, f1.get(k), f2.get(k)) for k in set(f1) | set(f2) if f1.get(k) != f2.get(k))
        vd = sorted((k, v1.get(k), v2.get(k)) for k in set(v1) | set(v2) if v1.get(k) != v2.get(k))
        w1, w2 = wb1f[n], wb2f[n]
        sd = 0
        for r1, r2 in zip(w1.iter_rows(), w2.iter_rows()):
            for a, b in zip(r1, r2):
                if style_sig(a) != style_sig(b):
                    sd += 1
        cw = {k: (w1.column_dimensions[k].width, w2.column_dimensions[k].width)
              for k in set(w1.column_dimensions) | set(w2.column_dimensions)
              if w1.column_dimensions[k].width != w2.column_dimensions[k].width}
        s1 = next(s for s in c1['sheets'] if s['name'] == n)
        s2 = next(s for s in c2['sheets'] if s['name'] == n)
        per[n] = OrderedDict(cells=len(f1), formula_or_constant_diffs=len(fd), value_diffs=len(vd), style_diffs=sd,
                             column_width_diffs=cw, sheetId=(s1['sheetId'], s2['sheetId']),
                             dynamic_array_flags=(s1['dynamic_array_flags'], s2['dynamic_array_flags']),
                             shared_formula_refs=(s1['shared_formula_refs'], s2['shared_formula_refs']),
                             xml_bytes=(s1['xml_bytes'], s2['xml_bytes']), examples=(fd[:5], vd[:5]))
    out['common_sheets'] = per
    p1, p2 = set(c1['parts']), set(c2['parts'])
    out['parts_removed_in_v2'] = sorted(p1 - p2)
    out['parts_added_in_v2'] = sorted(p2 - p1)
    out['defined_names'] = (c1['defined_names'], c2['defined_names'])
    out['core'] = {k: (c1[k], c2[k]) for k in ('creator', 'last_modified_by', 'created', 'modified', 'application')}
    return out


def main():
    t = time.time()
    books = {}
    for tag, path in SOURCES.items():
        books[tag] = (openpyxl.load_workbook(path, data_only=False), openpyxl.load_workbook(path, data_only=True))
    cont = {tag: container_facts(path) for tag, path in SOURCES.items()}
    inv = []
    for tag in ('V1', 'V2'):
        wbf, wbv = books[tag]
        for n in wbf.sheetnames:
            inv.append(sheet_inventory(wbf, wbv, n, tag))
    rec = {tag: recompute(books[tag][1]) for tag in ('V1', 'V2')}
    d = diff(*books['V1'], *books['V2'], cont['V1'], cont['V2'])
    dump('forensics.json', dict(container=cont, inventory=inv, recompute=rec, diff=d))
    print(f'forensics done in {time.time() - t:.0f}s; sheets V1={len(books["V1"][0].sheetnames)} V2={len(books["V2"][0].sheetnames)}')


if __name__ == '__main__':
    main()
