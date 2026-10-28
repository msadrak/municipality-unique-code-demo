"""Step 2 — normalised chart of accounts (new municipal chart + old Taxi/Terminals chart) and integrity tests.

Inputs : V1 workbook (V2 common sheets are value-identical, verified in step 1), tt_v21.sqlite (Taxi/Terminals
         account master `hesab` and ledger `sanad`, prior project), municipality_chart.json (chart observed in the
         1404 municipality journal, prior project).
Output : data/work/taxi_gate_audit/coa.json
"""
import json
from collections import Counter, OrderedDict, defaultdict

import openpyxl

from common import (F_V1, MUN_CHART, TT_DB, JOURNAL_DB, S_FULL, S_DEDUP, S_KOL, S_MOEN, S_8, S_KOL1, dump, norm_fa, norm_key,
                    old_nature, new_nature, ro_sqlite, mask_title)

ORGS = ('Taxi', 'Terminals')


def is_arabic_variant(s):
    return any(ch in str(s) for ch in 'يك')


def main():
    wb = openpyxl.load_workbook(F_V1, data_only=True)
    anomalies = []

    def anomaly(cat, source, code, title, parent, conflict, consequence, treatment, decision, severity, sheet_rows):
        anomalies.append(OrderedDict(anomaly_id=f'COA-{len(anomalies) + 1:03d}', category=cat, source=source, code=code,
                                     title=title, parent=parent, conflicting_record=conflict, consequence=consequence,
                                     suggested_treatment=treatment, expert_decision_required=decision, severity=severity,
                                     source_rows=sheet_rows))

    # ---------------------------------------------------------------- new chart (Sheet2 = reference)
    s2 = wb[S_DEDUP]
    new_rows = []
    for r in range(6, 240):
        v = [s2.cell(r, c).value for c in range(1, 7)]
        new_rows.append(OrderedDict(src=f'Sheet2!A{r}:F{r}', row=r, cls=v[0], cls_title=v[1], kol=v[2], kol_title=v[3],
                                    code=v[4], title=v[5]))
    # Sheet1 frequencies per 6-field combination
    s1 = wb[S_FULL]
    freq = Counter()
    first_row = {}
    for r, row in enumerate(s1.iter_rows(min_row=4, max_row=s1.max_row, values_only=True), start=4):
        freq[row] += 1
        first_row.setdefault(row, r)
    for x in new_rows:
        key = (x['cls'], x['cls_title'], x['kol'], x['kol_title'], x['code'], x['title'])
        x['sheet1_rows'] = freq.get(key, 0)
        x['sheet1_first_row'] = first_row.get(key)
    sheet2_keys = {(x['cls'], x['cls_title'], x['kol'], x['kol_title'], x['code'], x['title']) for x in new_rows}
    sheet1_only = [k for k in freq if k not in sheet2_keys]

    by_code = defaultdict(list)
    for x in new_rows:
        by_code[x['code']].append(x)
    # nature + structure flags
    for x in new_rows:
        x['nature'] = new_nature(x['cls'], x['kol'])
        c = x['code']
        x['code_len'] = len(str(c)) if c is not None else 0
        x['prefix_ok'] = (c is not None and str(c)[:3] == str(x['kol']))
        x['class_prefix_ok'] = str(x['kol'])[:1] == str(x['cls'])
        x['normal_side'] = {'ASSET': 'بدهکار', 'EXPENSE': 'بدهکار', 'BUDGET_CAPEX': 'بدهکار', 'BUDGET_DEBT_SERVICE': 'بدهکار',
                            'LIABILITY': 'بستانکار', 'NET_WORTH': 'بستانکار', 'REVENUE': 'بستانکار', 'MEMO': 'بدهکار',
                            'MEMO_CONTRA': 'بستانکار', 'LIAISON': 'دوطرفه'}.get(x['nature'], '')
        x['dup_code'] = len(by_code[c]) > 1 if c is not None else False

    # observed 1404 municipality journal coding (prior project extract)
    mc = json.load(open(MUN_CHART, encoding='utf8'))
    jn = defaultdict(list)
    for e in mc['new_coding']:
        jn[e['moin']].append(e)
    for x in new_rows:
        js = jn.get(str(x['code'])) if x['code'] is not None else None
        if not js:
            x['journal_1404'] = 'NOT_OBSERVED'
            x['journal_1404_lines'] = 0
            continue
        x['journal_1404_lines'] = sum(j['n'] for j in js)
        kol_ok = any(j['kol'] == str(x['kol']) for j in js)
        tit_ok = any(norm_key(j['moin_title']) == norm_key(x['title']) for j in js)
        x['journal_1404'] = ('SAME_PARENT' if kol_ok else 'PARENT_DIFFERS') + '/' + ('SAME_TITLE' if tit_ok else 'TITLE_DIFFERS')
        x['journal_1404_parent'] = sorted({j['kol'] for j in js})
    journal_codes_missing = sorted({k for k in jn if k.isdigit() and int(k) not in by_code and k != '0'})

    # provenance test: is Sheet1 a slice (one region or any combination of regions) of the 1404 municipality journal?
    def nk(v):
        try:
            return int(str(v).strip())
        except (TypeError, ValueError):
            return None
    reg_rows, reg_moin = Counter(), defaultdict(Counter)
    for orig, in ro_sqlite(JOURNAL_DB).execute('SELECT original FROM journal'):
        d = json.loads(orig)
        reg_rows[d.get('C')] += 1
        reg_moin[d.get('C')][nk(d.get('AB'))] += 1
    s1_moin = Counter()
    for k_, n_ in freq.items():
        s1_moin[k_[4]] += n_
    import itertools
    regs = sorted(reg_rows.items())
    exact_sum = [c for r_ in range(1, 4) for c in itertools.combinations(regs, r_) if sum(v for _, v in c) == sum(freq.values())]
    all_moin = Counter()
    for c_ in reg_moin.values():
        all_moin.update(c_)
    provenance = OrderedDict(
        journal_rows=sum(reg_rows.values()), regions=len(regs),
        region_row_counts={k_: v for k_, v in regs},
        regions_with_identical_moin_counts=[k_ for k_, c_ in reg_moin.items() if all(c_.get(m_, 0) == n_ for m_, n_ in s1_moin.items())],
        region_combinations_with_same_row_total=len(exact_sum),
        sheet1_moin_codes=len([m_ for m_ in s1_moin if m_ is not None]),
        sheet1_moin_codes_absent_from_journal=len([m_ for m_ in s1_moin if m_ is not None and all_moin.get(m_, 0) == 0]))

    # ------------------------------------------------------------ integrity tests — new chart
    for c, lst in by_code.items():
        if c is None or len(lst) < 2:
            continue
        titles = {norm_key(x['title']) for x in lst}
        parents = {x['kol'] for x in lst}
        rows = [x['src'] for x in lst]
        if len(parents) > 1:
            anomaly('ONE_CODE_MULTIPLE_PARENTS', 'New chart (Sheet2)', c, lst[0]['title'], sorted(parents),
                    '; '.join(f"{x['src']} → kol {x['kol']} «{x['kol_title']}»" for x in lst),
                    'یک معین زیر دو حساب کل؛ تجمیع مانده در سطح کل دوبار یا در کل اشتباه شمرده می‌شود؛ XLOOKUP اولین ردیف را برمی‌گرداند.',
                    'یک والد معتبر انتخاب و ردیف دیگر غیرفعال شود (پیشوند کد با کل والد باید یکی باشد).', 'YES', 'HIGH', rows)
        if len(titles) > 1:
            same_after_ye = len({norm_key(x['title']).replace(' ', '') for x in lst}) == 1
            anomaly('ONE_CODE_MULTIPLE_TITLES' if not same_after_ye else 'SPELLING_VARIANT_DUPLICATE', 'New chart (Sheet2)', c,
                    ' | '.join(str(x['title']).strip() for x in lst), sorted(parents), '; '.join(rows),
                    'یک کد با دو مفهوم متفاوت؛ هر سند ثبت‌شده با این کد مبهم است.' if not same_after_ye else
                    'تکرار یک حساب با املای عربی/فارسی متفاوت؛ ردیف تکراری در جدول مرجع.',
                    'تفکیک کد یا حذف ردیف اضافی پس از تأیید کارشناس.', 'YES' if not same_after_ye else 'NO (data cleansing)',
                    'HIGH' if not same_after_ye else 'LOW', rows)
        elif len(parents) == 1:
            anomaly('DUPLICATE_ROW', 'New chart (Sheet2)', c, lst[0]['title'], sorted(parents), '; '.join(rows),
                    'ردیف تکراری در جدول مرجع.', 'حذف ردیف تکراری.', 'NO', 'LOW', rows)
    for x in new_rows:
        if x['code'] is None:
            anomaly('MISSING_CODE', 'New chart (Sheet2)', None, x['title'], x['kol'], x['src'],
                    'ردیف بدون کد معین؛ در moen به صفر تبدیل شده و در تطبیق V2 به‌عنوان گزینه با کد ۰ حاضر است.',
                    'کد معتبر تخصیص یابد یا ردیف حذف شود.', 'YES' if x['title'] else 'NO', 'MEDIUM', [x['src']])
        elif x['code_len'] != 5:
            anomaly('INVALID_CODE_LENGTH', 'New chart (Sheet2)', x['code'], x['title'], x['kol'], x['src'],
                    f"کد {x['code_len']} رقمی در ساختار ۵ رقمی (کل ۳ رقم + معین ۲ رقم).",
                    'اصلاح کد (احتمالاً ۱۱۵۱۴/۱۱۵۱۵) پس از بررسی ساختار رسمی.', 'YES', 'MEDIUM', [x['src']])
        if x['code'] is not None and not x['prefix_ok']:
            anomaly('CODE_PREFIX_PARENT_CONFLICT', 'New chart (Sheet2)', x['code'], x['title'], x['kol'], x['src'],
                    f"پیشوند کد ({str(x['code'])[:3]}) با کل والد ({x['kol']}) یکی نیست.",
                    'والد صحیح بر اساس پیشوند کد تعیین شود.', 'YES', 'HIGH', [x['src']])
        if not x['class_prefix_ok']:
            anomaly('CLASS_PREFIX_CONFLICT', 'New chart (Sheet2)', x['kol'], x['kol_title'], x['cls'], x['src'],
                    'رقم اول کل با طبقه یکی نیست.', 'اصلاح طبقه/کل.', 'YES', 'HIGH', [x['src']])
        if x.get('journal_1404', '').startswith('PARENT_DIFFERS'):
            anomaly('CROSS_SOURCE_PARENT_CONFLICT', 'New chart (Sheet2) vs 1404 municipality journal', x['code'], x['title'],
                    x['kol'], f"دفتر ۱۴۰۴ شهرداری: کل {x['journal_1404_parent']} ({x['journal_1404_lines']} ردیف)",
                    'همان کد معین در دو منبع رسمی زیر کل متفاوت است؛ هر نگاشت به این کد به نسخهٔ نمودار وابسته است.',
                    'نسخهٔ معتبر نمودار حساب (و تاریخ اعتبار) تعیین شود.', 'YES', 'HIGH', [x['src']])
    # semantic class conflicts: receivable-type titles under a liability kol, and cross-class twins
    for x in new_rows:
        t = norm_fa(x['title'])
        if x['nature'] == 'LIABILITY' and 'اسناد دریافتنی' in t:
            anomaly('SEMANTIC_CLASS_CONFLICT', 'New chart (Sheet2)', x['code'], x['title'], x['kol'],
                    f"«{x['title']}» (ماهیت دریافتنی/دارایی) زیر کل {x['kol']} «{x['kol_title']}» (بدهی)",
                    'تطبیق متنی «اسناد دریافتنی ...» به یک حساب بدهی می‌رود (نمونه: ۱۱۳-۶ ← ۲۳۰۰۴ با شباهت ۱۰۰٪).',
                    'محل صحیح این معین‌ها (۱۱۵/۱۸۰ یا ۲۳۰ با عنوان «پیش‌دریافت») توسط کارشناس تعیین شود.', 'YES', 'HIGH', [x['src']])
    by_title = defaultdict(list)
    for x in new_rows:
        if x['title']:
            by_title[norm_key(x['title']).replace('گ', 'ک')].append(x)
    for t, lst in by_title.items():
        codes = {x['code'] for x in lst}
        if len(codes) > 1:
            anomaly('ONE_TITLE_MULTIPLE_CODES', 'New chart (Sheet2)', sorted(c for c in codes if c is not None),
                    ' | '.join(str(x['title']).strip() for x in lst), sorted({x['kol'] for x in lst}),
                    '; '.join(f"{x['src']} ({x['code']} زیر {x['kol']})" for x in lst),
                    'یک عنوان برای چند کد در طبقات/کل‌های مختلف؛ تطبیق متنی صرف بین آن‌ها تصادفی انتخاب می‌کند.',
                    'عنوان‌ها متمایز شوند (افزودن کل/ماهیت به عنوان).', 'YES' if len({x['cls'] for x in lst}) > 1 else 'NO',
                    'MEDIUM' if len({x['cls'] for x in lst}) > 1 else 'LOW', [x['src'] for x in lst])
    kol_titles = defaultdict(set)
    for x in new_rows:
        kol_titles[x['kol']].add(norm_key(x['kol_title']))
    for k, ts in kol_titles.items():
        if len(ts) > 1:
            anomaly('KOL_MULTIPLE_TITLES', 'New chart (Sheet2)', k, ' | '.join(sorted({str(x['kol_title']).strip() for x in new_rows if x['kol'] == k})),
                    None, '', 'عنوان کل ناپایدار (غلط املایی یا دو مفهوم).', 'یکسان‌سازی عنوان کل.', 'NO', 'LOW',
                    [x['src'] for x in new_rows if x['kol'] == k][:3])
    kt_codes = defaultdict(set)
    for x in new_rows:
        kt_codes[norm_key(x['kol_title'])].add(x['kol'])
    for t, ks in kt_codes.items():
        if len(ks) > 1:
            anomaly('ONE_KOL_TITLE_MULTIPLE_KOL_CODES', 'New chart (Sheet2)', sorted(ks), t, None, '',
                    'یک عنوان کل برای دو کد کل؛ تمایز بین کل‌ها فقط با کد ممکن است.', 'عنوان‌های کل متمایز شوند.',
                    'YES', 'MEDIUM', [])

    # ------------------------------------------------------------ old chart (moen code-2 rows) + hesab
    wm = wb[S_MOEN]
    old_rows = []
    for r in range(2, 393):
        a, b, c = wm.cell(r, 1).value, wm.cell(r, 2).value, wm.cell(r, 3).value
        if c == 2:
            old_rows.append(OrderedDict(src=f'moen!A{r}:C{r}', row=r, code_raw=a, code=str(a).strip(), title=str(b).strip(),
                                        trailing_spaces=len(str(a)) - len(str(a).rstrip())))
    tc = ro_sqlite(TT_DB)
    hes = defaultdict(dict)
    for org, fy, hc, name, lvl, src_row in tc.execute('SELECT org,fy,hcode,name,level,src_row FROM hesab'):
        hes[hc.strip()][(org, fy)] = (name.strip(), lvl, src_row)
    lvl1 = {}
    for org, fy, hc, name in tc.execute('SELECT org,fy,hcode,name FROM hesab WHERE level=1'):
        lvl1.setdefault(hc.strip().split('-')[0], {})[org] = name.strip()
    # ledger usage aggregated to (kol, moeen, taf1)
    use = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    for org, fy, kol, mo, t1, bed, bes in tc.execute('SELECT org,fy,kol,moeen,taf1,bed,bes FROM sanad'):
        a = use[(int(kol), int(mo), int(t1))][f'{org}-{fy}']
        a[0] += 1
        a[1] += bed or 0
        a[2] += bes or 0
    l3_in_list = set()
    for x in old_rows:
        p = [int(t) for t in x['code'].split('-')]
        x['kol'], x['moeen'], x['taf1'] = p[0], p[1], p[2]
        x['level'] = 2 if p[2] == 0 else 3
        if x['level'] == 3:
            l3_in_list.add((p[0], p[1], p[2]))
    for x in old_rows:
        k, m, t1 = x['kol'], x['moeen'], x['taf1']
        agg = defaultdict(lambda: [0, 0, 0])
        for key, byof in use.items():
            if key[0] != k or key[1] != m:
                continue
            if x['level'] == 3 and key[2] != t1:
                continue
            if x['level'] == 2 and (k, m, key[2]) in l3_in_list:
                continue
            for of, a in byof.items():
                b = agg[of]
                b[0] += a[0]; b[1] += a[1]; b[2] += a[2]
        x['usage'] = {of: a for of, a in sorted(agg.items())}
        x['lines_total'] = sum(a[0] for a in agg.values())
        x['debit_total'] = sum(a[1] for a in agg.values())
        x['credit_total'] = sum(a[2] for a in agg.values())
        h = hes.get(x['code'], {})
        x['orgs'] = sorted({o for (o, f) in h})
        x['org_titles'] = {o: sorted({n for (oo, f), (n, l, sr) in h.items() if oo == o}) for o in ORGS if any(oo == o for (oo, f) in h)}
        x['hesab_rows'] = {f'{o}-{f}': sr for (o, f), (n, l, sr) in sorted(h.items())}
        x['kol_title_by_org'] = lvl1.get(str(k), {})
        x['parent_code'] = f'{k}-0-0-0' if x['level'] == 2 else f'{k}-{m}-0-0'
        x['parent_title_by_org'] = {o: sorted({n for (oo, f), (n, l, sr) in hes.get(x['parent_code'], {}).items() if oo == o}) for o in ORGS}
        x['nature'] = old_nature(k, m)
        x['normal_side'] = {'ASSET': 'بدهکار', 'EXPENSE': 'بدهکار', 'NONCASH_EXPENSE': 'بدهکار', 'COST_OF_SALES': 'بدهکار',
                            'CONTRA_ASSET': 'بستانکار', 'LIABILITY': 'بستانکار', 'PROVISION_LIABILITY': 'بستانکار',
                            'EQUITY': 'بستانکار', 'REVENUE': 'بستانکار', 'MEMO': 'بدهکار', 'MEMO_CONTRA': 'بستانکار',
                            'NONOP_MIXED': 'دوطرفه'}.get(x['nature'], '')
        nk = {o: {norm_key(t) for t in ts} for o, ts in x['org_titles'].items()}
        x['title_source_org'] = sorted(o for o, ts in nk.items() if norm_key(x['title']) in ts)
        x['org_title_variants'] = len({t for ts in nk.values() for t in ts})
        x['title_masked'] = mask_title(x['title'])

    # meaning collisions between Taxi and Terminals for the same code (manually reviewed list, see expert_crosswalk)
    from expert_crosswalk import MEANING_COLLISIONS
    for x in old_rows:
        if x['org_title_variants'] > 1:
            cat = 'OLD_CODE_MEANING_COLLISION_BETWEEN_ORGS' if x['code'] in MEANING_COLLISIONS else 'OLD_CODE_TITLE_VARIANT_BETWEEN_ORGS'
            anomaly(cat, 'Old chart (moen) vs Taxi/Terminals hesab', x['code'], x['title'], x['parent_code'],
                    ' | '.join(f"{o}: {mask_title(' / '.join(ts))}" for o, ts in x['org_titles'].items()),
                    ('یک کد در دو سازمان دو مفهوم حسابداری متفاوت دارد؛ فهرست همکار فقط یک عنوان نگه داشته '
                     f"(منبع عنوان: {','.join(x['title_source_org'])}) و گردش {x['lines_total']} ردیف/{x['debit_total']:,} بدهکار "
                     'متعلق به مفهوم دیگر می‌تواند باشد.') if cat.endswith('COLLISION_BETWEEN_ORGS') else
                    'تفاوت املایی/نگارشی عنوان بین دو سازمان.',
                    'نگاشت در سطح (سازمان، کد) انجام شود، نه کد مشترک.' if cat.endswith('COLLISION_BETWEEN_ORGS') else 'یکسان‌سازی عنوان.',
                    'YES' if cat.endswith('COLLISION_BETWEEN_ORGS') else 'NO', 'HIGH' if cat.endswith('COLLISION_BETWEEN_ORGS') else 'LOW',
                    [x['src']])
    for x in old_rows:
        if x['level'] == 3:
            anomaly('OLD_LIST_MIXES_LEVELS', 'Old chart (moen)', x['code'], x['title_masked'], x['parent_code'],
                    f"والد {x['parent_code']} نیز در فهرست هست", 'حساب تفصیلی در کنار معین والدش در یک فهرست تطبیق؛ خطر شمارش/نگاشت مضاعف.',
                    'حساب‌های سطح ۳ از فهرست معین جدا یا به‌عنوان بُعد (شخص/فعالیت) مدل شوند.', 'NO', 'MEDIUM', [x['src']])
    persons = [x for x in old_rows if x['title_masked'] != x['title']]
    for x in persons:
        anomaly('PERSONAL_DATA_IN_ACCOUNT_TITLE', 'Old chart (moen)', x['code'], x['title_masked'], x['parent_code'], '',
                'نام شخص حقیقی در عنوان حساب؛ «شخص» باید بُعد طرف حساب باشد نه حساب معین.',
                'انتقال به بُعد شخص/طرف حساب؛ ماسک در خروجی‌های غیرمحرمانه.', 'NO', 'MEDIUM', [x['src']])
    padded = sum(1 for x in old_rows if x['trailing_spaces'] > 0)
    anomaly('TEXT_CODE_PADDING', 'Old chart (moen, kol, 88888888)', f'{padded} کد', '', None,
            'کدهای قدیم به‌صورت متن با فاصلهٔ انتهایی (تا ۳۰ کاراکتر) ذخیره شده‌اند؛ کدهای جدید عدد هستند.',
            'ستون A شیت moen دو نوع داده دارد؛ XLOOKUP/مقایسه بدون TRIM شکننده است.', 'TRIM و نوع دادهٔ واحد (متن) برای کد.',
            'NO', 'LOW', ['moen!A4:A392'])

    # old list coverage vs hesab level-2
    lvl2 = defaultdict(dict)
    for org, fy, hc, name, kol, mo, t1 in tc.execute('SELECT org,fy,hcode,name,kol,moeen,taf1 FROM hesab WHERE level=2'):
        lvl2[hc.strip()][org] = name.strip()
    listed = {x['code'] for x in old_rows}
    missing_l2 = []
    for hc, by in sorted(lvl2.items()):
        if hc in listed:
            continue
        k, m = int(hc.split('-')[0]), int(hc.split('-')[1])
        agg = [0, 0, 0]
        for key, byof in use.items():
            if key[0] == k and key[1] == m:
                for a in byof.values():
                    agg[0] += a[0]; agg[1] += a[1]; agg[2] += a[2]
        missing_l2.append(OrderedDict(code=hc, titles={o: mask_title(t) for o, t in by.items()}, lines=agg[0], debit=agg[1], credit=agg[2]))
    # 88888888 A:B and kol E:G old lists
    e8 = wb[S_8]
    old88 = [(r, str(e8.cell(r, 1).value).strip(), str(e8.cell(r, 2).value).strip()) for r in range(1, 236) if e8.cell(r, 1).value]
    wk = wb[S_KOL]
    oldkol = [OrderedDict(src=f'kol!E{r}:G{r}', code=str(wk.cell(r, 5).value).strip(), flag=str(wk.cell(r, 6).value),
                          title=str(wk.cell(r, 7).value).strip()) for r in range(4, 43)]
    for x in oldkol:
        x['orgs'] = sorted({o for (o, f) in hes.get(x['code'], {})})
        x['flag_matches_inference'] = x['flag'] == {('Taxi', 'Terminals'): '1,2', ('Terminals',): '1', ('Taxi',): '2'}.get(tuple(x['orgs']))
    # interleaved kol list (colleague kol-level pairs)
    k1 = wb[S_KOL1]
    kol1 = [OrderedDict(src=f"'{S_KOL1}'!B{r}:C{r}", code=str(k1.cell(r, 2).value).strip(), title=str(k1.cell(r, 3).value).strip())
            for r in range(2, 75) if k1.cell(r, 2).value is not None]
    pairs = [x for x in kol1 if '/' in x['code']]

    # numeric kol collisions old vs new
    new_kols = {x['kol']: x['kol_title'] for x in new_rows}
    kol_collisions = []
    for x in oldkol:
        k = int(x['code'].split('-')[0])
        if k in new_kols:
            kol_collisions.append(OrderedDict(code=k, old_title=x['title'], new_title=new_kols[k],
                                              same_meaning=norm_key(x['title'])[:8] == norm_key(new_kols[k])[:8]))
    # Persian/Arabic character usage
    char_stats = OrderedDict(
        new_titles_arabic_ye_kaf=sum(1 for x in new_rows if x['title'] and is_arabic_variant(x['title'])),
        new_titles_total=sum(1 for x in new_rows if x['title']),
        new_titles_trailing_space=sum(1 for x in new_rows if x['title'] and str(x['title']) != str(x['title']).strip()),
        old_titles_arabic_ye_kaf=sum(1 for x in old_rows if is_arabic_variant(x['title'])),
        old_titles_total=len(old_rows),
        mixed_within_title=sum(1 for x in new_rows + old_rows if x['title'] and is_arabic_variant(x['title']) and any(ch in str(x['title']) for ch in 'یک')))
    anomaly('PERSIAN_ARABIC_CHARACTER_MIX', 'Both charts', '', '', None,
            f"عناوین جدید با ی/ک عربی: {char_stats['new_titles_arabic_ye_kaf']} از {char_stats['new_titles_total']}؛ "
            f"قدیم: {char_stats['old_titles_arabic_ye_kaf']} از {char_stats['old_titles_total']}؛ ترکیب هر دو در یک عنوان: {char_stats['mixed_within_title']}",
            'مقایسهٔ دقیق رشته‌ها بدون یکسان‌سازی شکست می‌خورد (مثلاً ۱۲۰۰۵ دوبار).', 'یکسان‌سازی حروف در جدول مرجع.', 'NO', 'LOW', [])

    dump('coa.json', OrderedDict(
        new_rows=new_rows, sheet1_combinations_not_in_sheet2=[list(k) for k in sheet1_only],
        sheet1_total_rows=sum(freq.values()), sheet1_distinct=len(freq), sheet1_provenance=provenance,
        journal_codes_not_in_sheet2=journal_codes_missing, old_rows=old_rows, old88=old88, old_kol=oldkol, kol1=kol1,
        kol1_pairs=pairs, kol_collisions=kol_collisions, missing_level2=missing_l2, char_stats=char_stats,
        anomalies=anomalies))
    print(f'new={len(new_rows)} old={len(old_rows)} anomalies={len(anomalies)} missing_l2={len(missing_l2)} '
          f'kol_pairs={len(pairs)} kol_collisions={len(kol_collisions)}')


if __name__ == '__main__':
    main()
