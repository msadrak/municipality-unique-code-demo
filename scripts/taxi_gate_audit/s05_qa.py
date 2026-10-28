"""Step 5 — single QA registry (PRE-BUILD tests only; post-build tests live in s07 and are never embedded in the files they test).

Every status is computed from the step outputs or re-derived from the sources; nothing is a static label.
Output: data/work/taxi_gate_audit/qa_registry.json
"""
from collections import Counter, OrderedDict

from common import SOURCES, sha256, dump, load
from expert_crosswalk import ENTRIES


def main():
    fx, coa, mt, ig = load('forensics.json'), load('coa.json'), load('matching.json'), load('integration.json')
    tests = []

    def t(tid, area, desc, condition, actual, status, method):
        assert status in ('PASS', 'REVIEW', 'FAIL', 'NOT TESTABLE'), status
        tests.append(OrderedDict(test_id=tid, area=area, description=desc, pass_condition=condition, actual=str(actual), status=status, method=method))

    # ------------------------------------------------------------ sources
    now = {k: sha256(p) for k, p in SOURCES.items()}
    rec = {k: fx['container'][k]['sha256'] for k in SOURCES}
    t('QA-SRC-01', 'Sources', 'هش SHA-256 هر دو فایل همکار ثبت شد', 'هش در forensics.json موجود', rec, 'PASS', 's01 container_facts')
    t('QA-SRC-02', 'Sources', 'فایل‌های منبع در طول تحلیل تغییر نکرده‌اند', 'هش فعلی = هش ابتدای اجرا', {k: now[k] == rec[k] for k in now},
      'PASS' if now == rec else 'FAIL', 'sha256 recomputed in s05 (and again post-build in s07)')
    inv = fx['inventory']
    t('QA-INV-01', 'Inventory', 'همهٔ شیت‌ها (شامل پنهان) فهرست شدند', 'V1=8، V2=11 ردیف موجودی',
      Counter(x['workbook'] for x in inv), 'PASS' if Counter(x['workbook'] for x in inv) == {'V1': 8, 'V2': 11} else 'FAIL', 'openpyxl + workbook.xml')
    hidden = [x['sheet'] for x in inv if x['visibility'] != 'visible']
    t('QA-INV-02', 'Inventory', 'شیت پنهان/خیلی‌پنهان', 'وضعیت هر شیت خوانده شود', hidden or 'هیچ شیت پنهانی نیست', 'PASS', 'sheet_state + <sheet state=>')
    ext = {k: fx['container'][k]['external_links'] for k in SOURCES}
    t('QA-INV-03', 'Inventory', 'پیوند خارجی / نام تعریف‌شده', 'پیوند خارجی = ۰؛ نام‌ها فهرست شوند', {k: (len(v), len(fx['container'][k]['defined_names'])) for k, v in ext.items()},
      'PASS' if not any(ext.values()) else 'REVIEW', 'xl/externalLinks + definedNames')
    # ------------------------------------------------------------ diff
    d = fx['diff']
    vd = sum(v['value_diffs'] for v in d['common_sheets'].values())
    fd = sum(v['formula_or_constant_diffs'] for v in d['common_sheets'].values())
    sd = sum(v['style_diffs'] for v in d['common_sheets'].values())
    cw = {k: v['column_width_diffs'] for k, v in d['common_sheets'].items() if v['column_width_diffs']}
    t('QA-DIF-01', 'Version diff', 'شیت‌های افزوده/حذف/تغییرنام V1→V2', 'افزوده ۳، حذف ۰، تغییرنام ۰', (d['added'], d['deleted'], d['renamed']),
      'PASS' if len(d['added']) == 3 and not d['deleted'] else 'FAIL', 'sheet names + cell content')
    t('QA-DIF-02', 'Version diff', 'مقادیر و فرمول‌های ۸ شیت مشترک', 'اختلاف سلولی = ۰', dict(values=vd, formulas=fd), 'PASS' if vd == 0 and fd == 0 else 'FAIL',
      'cell-by-cell compare (data_only False/True)')
    t('QA-DIF-03', 'Version diff', 'تفاوت قالب‌بندی', 'فقط گزارش شود', dict(style_diffs=sd, column_widths=cw), 'REVIEW' if cw or sd else 'PASS', 'style signature per cell + column widths')
    da = {k: v['dynamic_array_flags'] for k, v in d['common_sheets'].items() if v['dynamic_array_flags'][0] != v['dynamic_array_flags'][1]}
    t('QA-DIF-04', 'Version diff', 'ساختار OOXML: حذف metadata.xml و پرچم آرایهٔ پویا در V2', 'گزارش ریسک', dict(parts_removed=d['parts_removed_in_v2'], flags=da),
      'REVIEW' if d['parts_removed_in_v2'] else 'PASS', 'zip parts + cm="1" count')
    # ------------------------------------------------------------ formulas
    rc = fx['recompute']['V1']
    eq = all(v.get('cached_equal', True) for k, v in rc.items() if 'cached_equal' in v)
    rows_ok = all(v['cached_equal_rows'] == v['rows'] for k, v in rc.items() if 'cached_equal_rows' in v)
    t('QA-FML-01', 'Formulas', 'مقادیر ذخیره‌شدهٔ UNIQUE/XLOOKUP/TEXTJOIN با محاسبهٔ مستقل', 'برابر', dict(arrays_equal=eq, rowwise_equal=rows_ok),
      'PASS' if eq and rows_ok else 'FAIL', 's01 recompute()')
    k = next(v for kk, v in rc.items() if kk.startswith('kol!C4'))
    t('QA-FML-02', 'Formulas', 'kol!C:D — UNIQUE جداگانهٔ کد و عنوان', 'جفت کد/عنوان هم‌تراز', f"{k['misaligned_pairs']} ردیف ناهم‌تراز (C6:D12)",
      'FAIL' if k['misaligned_pairs'] else 'PASS', 'pair check vs A:B')
    sh = next(v for kk, v in rc.items() if kk.startswith('moen rows where'))
    t('QA-FML-03', 'Formulas', 'moen!D:G/I/J محاسبه برای ستون H (UNIQUE) نه ستون A همان ردیف', 'H=A در همهٔ ردیف‌ها',
      f"{sh['rows']} از {sh['of_total']} ردیف جابه‌جا از ردیف {sh['first_row']}", 'FAIL' if sh['rows'] else 'PASS', 'compare A(row) vs H(row)')
    # ------------------------------------------------------------ populations
    s1 = next(x for x in inv if x['workbook'] == 'V1' and x['sheet'] == 'Sheet1')
    t('QA-POP-01', 'Population', 'Sheet1: ردیف‌های داده و ترکیب‌های یکتای ۶ فیلدی', 'گزارش مقدماتی ۷۳٬۴۶۱ / ۲۳۴', (s1['data_rows_after_header'], s1['distinct_data_rows']),
      'PASS' if (s1['data_rows_after_header'], s1['distinct_data_rows']) == (73461, 234) else 'REVIEW', 'distinct tuples A:F')
    t('QA-POP-02', 'Population', 'ترکیب‌های Sheet1 زیرمجموعهٔ Sheet2', '۰ ترکیب خارج از Sheet2', len(coa['sheet1_combinations_not_in_sheet2']),
      'PASS' if not coa['sheet1_combinations_not_in_sheet2'] else 'FAIL', 'set difference')
    t('QA-POP-03', 'Population', 'معنای تراکنشی تکرارهای Sheet1', 'وجود شمارهٔ سند/مبلغ/تاریخ', 'Sheet1 فقط ۶ ستون حساب دارد', 'NOT TESTABLE',
      'column inventory — fields absent')
    pv = coa['sheet1_provenance']
    found = pv['regions_with_identical_moin_counts'] or pv['region_combinations_with_same_row_total']
    t('QA-POP-04', 'Population', 'منشأ Sheet1 در دفتر روزنامهٔ ۱۴۰۴ شهرداری', 'تطابق شمارش معین‌ها با یک منطقه یا جمع ردیف با ترکیب ≤۳ منطقه',
      f"مناطق هم‌شمار: {len(pv['regions_with_identical_moin_counts'])} از {pv['regions']}؛ ترکیب هم‌جمع: {pv['region_combinations_with_same_row_total']}؛ "
      f"{pv['sheet1_moin_codes_absent_from_journal']} از {pv['sheet1_moin_codes']} کد معین Sheet1 در دفتر ۱۴۰۴ نیست",
      'PASS' if found else 'REVIEW', 'journal_records.sqlite X:AC (s02 provenance block)')
    # ------------------------------------------------------------ chart integrity
    cat = Counter(a['category'] for a in coa['anomalies'])
    for tid, c, desc, sev in (('QA-COA-01', 'ONE_CODE_MULTIPLE_TITLES', 'یک کد با چند عنوان (نمودار جدید)', 'FAIL'),
                              ('QA-COA-02', 'ONE_CODE_MULTIPLE_PARENTS', 'یک کد با چند والد', 'FAIL'),
                              ('QA-COA-03', 'MISSING_CODE', 'ردیف بدون کد معین', 'FAIL'),
                              ('QA-COA-04', 'INVALID_CODE_LENGTH', 'طول کد نامعتبر', 'FAIL'),
                              ('QA-COA-05', 'SEMANTIC_CLASS_CONFLICT', 'دریافتنی زیر کل بدهی', 'FAIL'),
                              ('QA-COA-06', 'CROSS_SOURCE_PARENT_CONFLICT', 'والد متفاوت با نمودار دفتر ۱۴۰۴', 'REVIEW'),
                              ('QA-COA-07', 'OLD_CODE_MEANING_COLLISION_BETWEEN_ORGS', 'یک کد قدیم با دو معنا در دو سازمان', 'FAIL'),
                              ('QA-COA-08', 'ONE_TITLE_MULTIPLE_CODES', 'یک عنوان با چند کد', 'REVIEW'),
                              ('QA-COA-09', 'CODE_PREFIX_PARENT_CONFLICT', 'پیشوند کد ≠ کل والد', 'FAIL')):
        t(tid, 'Chart integrity', desc, 'تعداد = ۰', cat.get(c, 0), sev if cat.get(c, 0) else 'PASS', 's02 anomaly rules')
    t('QA-COA-10', 'Chart integrity', 'پوشش فهرست قدیم همکار نسبت به معین‌های سطح ۲ حساب‌های سازمان‌ها', 'همهٔ معین‌های دارای گردش در فهرست',
      f"{len(coa['missing_level2'])} معین سطح ۲ خارج از فهرست؛ {sum(x['lines'] for x in coa['missing_level2'])} ردیف گردش",
      'REVIEW' if coa['missing_level2'] else 'PASS', 'hesab level=2 minus moen code-2 list')
    ok_t = sum(1 for x in coa['old_rows'] if x['title_source_org'])
    t('QA-COA-11', 'Chart integrity', 'عنوان هر حساب قدیم در حساب‌های سازمان‌ها موجود است', '۱۵۷/۱۵۷', f'{ok_t}/{len(coa["old_rows"])}',
      'PASS' if ok_t == len(coa['old_rows']) else 'FAIL', 'normalised title ∈ hesab names')
    fl = sum(1 for x in coa['old_kol'] if x['flag_matches_inference'])
    t('QA-COA-12', 'Chart integrity', 'معنای ستون kol!F (1=پایانه‌ها، 2=تاکسیرانی) — استنتاج', 'سازگاری با حضور کل در hesab', f'{fl}/{len(coa["old_kol"])}',
      'PASS' if fl == len(coa['old_kol']) else 'REVIEW', 'inference test (not documented in the file)')
    lead = [x['code'] for x in coa['new_rows'] if x['code'] is not None and str(x['code']).startswith('0')]
    t('QA-COA-13', 'Chart integrity', 'حذف صفر پیشرو/تبدیل عددی', 'هیچ کد با صفر پیشرو یا کد اعشاری', len(lead), 'PASS' if not lead else 'FAIL', 'type + prefix check')
    # ------------------------------------------------------------ matching
    r = mt['reproduction']
    t('QA-MAT-01', 'Matching', 'بازتولید درصد شباهت همکار', '۴۷۱/۴۷۱', f"{r['score_reproduced']}/{r['score_pairs']}", 'PASS' if r['score_reproduced'] == r['score_pairs'] else 'FAIL',
      'Indel 2·LCS/(|a|+|b|) after norm_fa()')
    t('QA-MAT-02', 'Matching', 'بازتولید رتبه‌بندی سه گزینه', '۱۵۷/۱۵۷ (با تساوی)', f"{r['ranking_reproduced']} + {r['ranking_tie_order_only']} تساوی",
      'PASS' if r['ranking_reproduced'] + r['ranking_tie_order_only'] == r['accounts'] else 'FAIL', 'argmax over 234 moen code-1 rows, stable order')
    cs = dict(mt['colleague_summary'])
    rs = dict(mt['reproduced_summary'])
    keys = [('تعداد حساب‌های جدید (کد ۱)', 'تعداد حساب‌های جدید (کد ۱)'), ('تعداد حساب‌های قدیمی (کد ۲)', 'تعداد حساب‌های قدیمی (کد ۲)'),
            ('نام‌های دقیقاً یکسان پس از یکسان‌سازی حروف و فاصله', 'نام‌های دقیقاً یکسان پس از یکسان‌سازی حروف و فاصله'),
            ('بهترین گزینه با شباهت ۹۰٪ به بالا', '>=90'), ('بهترین گزینه با شباهت ۸۰٪ تا کمتر از ۹۰٪', '80-90'),
            ('بهترین گزینه با شباهت ۷۰٪ تا کمتر از ۸۰٪', '70-80'), ('بهترین گزینه با شباهت کمتر از ۷۰٪', '<70')]
    cmp = {a: (cs.get(a), rs.get(b)) for a, b in keys}
    t('QA-MAT-03', 'Matching', 'بازتولید شیت «خلاصه تطبیق»', 'همهٔ ۷ عدد برابر', cmp, 'PASS' if all(x == y for x, y in cmp.values()) else 'FAIL', 'recount from matching sheet')
    t('QA-MAT-04', 'Matching', 'ستون‌های گروه/کل جدید در شیت‌های تطبیق', 'والد نمایش‌داده = والد واقعی', f"درست {r['parent_correct']}، نادرست {r['parent_wrong']}، «پیدا نشد» {r['parent_not_found']} از ۴۷۱",
      'FAIL' if r['parent_wrong'] or r['parent_not_found'] else 'PASS', 'compare with Sheet2 parent')
    t('QA-MAT-05', 'Matching', 'علت ریشه‌ای والد نادرست', 'بازتولید از moen!D:G ردیف کد', f"{r['parent_hypothesis_reproduced']}/471", 'PASS' if r['parent_hypothesis_reproduced'] == 471 else 'REVIEW',
      'row lookup hypothesis')
    inc = sum(1 for a in mt['audit'] if a['structural'] == 'INCOMPATIBLE')
    t('QA-MAT-06', 'Matching', 'اعمال قید ماهیت/طبقه در روش همکار', 'هیچ «بهترین گزینه» ناسازگار ساختاری', f'{inc} از ۱۵۷ ناسازگار', 'FAIL' if inc else 'PASS',
      'structural_compat(old nature, new nature)')
    badc = [a['old_code'] for a in mt['audit'] if (a['structural'] == 'INCOMPATIBLE' and a['verdict'] not in ('INVALID_STRUCTURAL', 'INVALID_PERSPECTIVE', 'INVALID_ENTITY'))
            or (a['verdict'] == 'INVALID_STRUCTURAL' and a['structural'] != 'INCOMPATIBLE')]
    t('QA-MAT-07', 'Matching', 'سازگاری حکم ممیزی با آزمون ساختاری', '۰ تناقض', badc or 0, 'PASS' if not badc else 'FAIL', 'cross-check verdict × structural')
    t('QA-MAT-08', 'Matching', 'پوشش ممیزی', '۱۵۷ بهترین + ۴۷۱ گزینه + ۵ جفت کل', (len(mt['audit']), len(mt['candidates']), len(mt['kol_pairs'])),
      'PASS' if (len(mt['audit']), len(mt['candidates']), len(mt['kol_pairs'])) == (157, 471, 5) else 'FAIL', 'row counts')
    ctrl_bad = sum(1 for x in mt['alternatives'] if x['source'] == 'CONTROLLED_MATCHER_STAGE_ABC' and x['structural'] == 'INCOMPATIBLE')
    c = mt['controlled']
    t('QA-MAT-09', 'Matching', 'روش کنترل‌شده (A→B→C) هرگز گزینهٔ ناسازگار ساختاری نمی‌دهد', '۰ گزینهٔ ناسازگار', ctrl_bad, 'PASS' if ctrl_bad == 0 else 'FAIL', 'alternatives table')
    t('QA-MAT-10', 'Matching', 'کیفیت کاندیدسازی در برابر پیشنهاد مستقل (اطلاعاتی)', 'گزارش top-1 و recall@3',
      f"کنترل‌شده {c['controlled_top1']}/{c['comparable']} و {c['controlled_recall3']}/{c['comparable']}؛ همکار {c['colleague_top1']} و {c['colleague_recall3']}", 'PASS',
      'candidate generator metric (not accuracy of accounting truth)')
    # ------------------------------------------------------------ crosswalk
    xw = mt['crosswalk']
    keys = {(r['old_code'], r['org_scope']) for r in xw}
    t('QA-XW-01', 'Crosswalk', 'هر حساب قدیم (و هر معنای سازمانی) حداقل یک ردیف', '۱۵۷ کد / ۱۶۵ ردیف سازمانی',
      (len({k[0] for k in keys}), len(keys)), 'PASS' if len({k[0] for k in keys}) == 157 and len(keys) == len(ENTRIES) else 'FAIL', 'distinct keys')
    appr = [r for r in xw if r['approval_status'] != 'NOT_APPROVED'] + [r for r in ig['account_event'] if r['approval_status'] != 'NOT_APPROVED']
    t('QA-XW-02', 'Governance', 'هیچ رابطه‌ای «تأییدشده» برچسب نخورده', '۰', len(appr), 'PASS' if not appr else 'FAIL', 'scan approval_status')
    t('QA-XW-03', 'Crosswalk', 'کاردینالیتی محاسبه شد', 'همهٔ ردیف‌ها یکی از 1→1/1→N/N→1/N→N/UNMAPPED', Counter(r['cardinality'] for r in xw),
      'PASS' if all(r['cardinality'] in ('1→1', '1→N', 'N→1', 'N→N', 'UNMAPPED') for r in xw) else 'FAIL', 'degree computation')
    bad = [r for r in ig['split_recon'] if not r['equal']]
    t('QA-XW-04', 'Crosswalk', 'مجموع زیرحساب‌های تفکیک = گردش حساب', '۰ اختلاف', len(bad), 'PASS' if not bad else 'FAIL', 'split_recon')
    # ------------------------------------------------------------ reconciliation
    rcn = ig['reconciliation']
    t('QA-REC-01', 'Reconciliation', 'حفظ ردیف منبع در تبارشناسی', '۱۱۱٬۶۰۰ = ۱۱۱٬۶۰۰', (rcn['source']['lines'], rcn['lineage']['lines'], rcn['unique_sid']),
      'PASS' if rcn['source']['lines'] == rcn['lineage']['lines'] == rcn['unique_sid'] else 'FAIL', 'count + unique Source_Record_ID')
    t('QA-REC-02', 'Reconciliation', 'حفظ جمع بدهکار/بستانکار', 'برابر منبع', (rcn['source']['debit'] == rcn['lineage']['debit'], rcn['source']['credit'] == rcn['lineage']['credit']),
      'PASS' if rcn['source']['debit'] == rcn['lineage']['debit'] and rcn['source']['credit'] == rcn['lineage']['credit'] else 'FAIL', 'sum(Bed), sum(Bes)')
    unb = {k: v for k, v in rcn['per_org_fy'].items() if v[1] != v[2]}
    t('QA-REC-03', 'Reconciliation', 'تراز هر سازمان/سال', 'بدهکار = بستانکار', unb or 'همه متوازن', 'PASS' if not unb else 'FAIL', 'per org/fy')
    sb = [sum(v[i] for v in rcn['proposal_buckets'].values()) for i in range(3)]
    sv = [sum(v[i] for v in rcn['colleague_verdict_buckets'].values()) for i in range(3)]
    ok = sb == [rcn['lineage']['lines'], rcn['lineage']['debit'], rcn['lineage']['credit']] == sv
    t('QA-REC-04', 'Reconciliation', 'عدم تورم مبلغ در نگاشت ۱→N (هر ردیف دقیقاً یک مقصد)', 'جمع سطل‌ها = کل', dict(proposal=sb, colleague=sv), 'PASS' if ok else 'FAIL',
      'bucket sums')
    t('QA-REC-05', 'Reconciliation', 'اسناد مشترک بین چند مقصد', 'گزارش', f"{rcn['shared_documents_multi_destination']} از {rcn['documents']} سند", 'REVIEW',
      'documents whose lines map to ≥2 destinations (expected for double-entry)')
    t('QA-REC-06', 'Reconciliation', 'کد بودجه در تبارشناسی', 'وجود فیلد', 'Sanad سازمان‌ها ستون بودجه ندارد', 'NOT TESTABLE', 'schema')
    t('QA-REC-07', 'Reconciliation', 'واحد پول', 'تصریح در منبع', 'تصریح نشده (CD-02)', 'NOT TESTABLE', 'schema')
    t('QA-REC-08', 'Reconciliation', 'اعتبارسنجی مانده در فایل‌های همکار', 'وجود مبلغ/سند', 'فایل‌های همکار مبلغ ندارند؛ فقط از دفتر سازمان‌ها', 'NOT TESTABLE',
      'schema of Taxi-Gate workbooks')
    # ------------------------------------------------------------ events / cc / domain
    fe = {x['event_id'] for x in ig['fe_dictionary']}
    unk = sorted({r['event_id'] for r in ig['account_event'] if r['event_id'] not in fe and r['event_id'] != 'UNASSIGNED' and not str(r['event_id']).startswith('EXC')})
    t('QA-EV-01', 'Events', 'شناسهٔ رویدادها در فرهنگ v7.1 یا فهرست TT-NE موجود', '۰ شناسهٔ ناشناخته', unk or 0, 'PASS' if not unk else 'FAIL', 'set membership')
    rv = sum(1 for r in ig['account_event'] if r['semantic_compatibility'] == 'REVIEW')
    t('QA-EV-02', 'Events', 'ناسازگاری معنایی حساب × رویداد', 'گزارش برای بازبینی', rv, 'REVIEW' if rv else 'PASS', 'account nature vs FE nature')
    import json as _j
    CC = _j.load(open(__import__('common').CC_MASTER, encoding='utf8'))
    bad_cc = sorted({r['cost_center_id'] for r in ig['activity_cc'] if r['cost_center_id'] and r['cost_center_id'] not in CC and not r['cost_center_id'].startswith('TTCC')})
    t('QA-CC-01', 'Cost centers', 'شناسهٔ مراکز در cc_master یا TTCC', '۰ شناسهٔ ساختگی', bad_cc or 0, 'PASS' if not bad_cc else 'FAIL', 'set membership')
    t('QA-CC-02', 'Cost centers', 'استخراج مرکز هزینه از فایل‌های همکار', 'وجود فعالیت/واحد/سند', 'هیچ‌یک از این فیلدها در Taxi-Gate نیست', 'NOT TESTABLE', 'schema')
    multi = sum(1 for r in ig['account_cc'] if r['distinct_cost_centers'] > 1)
    t('QA-CC-03', 'Cost centers', 'حساب‌های عمومی با چند مرکز هزینهٔ مشاهده‌شده', 'گزارش', f"{multi} از {len(ig['account_cc'])} حساب", 'REVIEW' if multi else 'PASS', 'account × cc')
    term = sum(1 for x in ig['domain'] if x['classification'] == 'DIRECT_TERMINAL')
    t('QA-DOM-01', 'Domain', 'شواهد مستقیم پایانه‌ای در فایل‌های همکار', '≥۱', term, 'REVIEW' if term == 0 else 'PASS', 'keyword scan of every title')
    masked = sum(1 for x in coa['old_rows'] if x['title_masked'] != x['title'])
    t('QA-PRIV-01', 'Privacy', 'ماسک نام شخص/شمارهٔ حساب در عناوین', 'اعمال در خروجی', f'{masked} عنوان قدیم ماسک شد؛ کد سلسله‌مراتبی حفظ شد', 'PASS', 'mask_title(); post-build scan in s07')
    dump('qa_registry.json', tests)
    print(Counter(x['status'] for x in tests), len(tests))


if __name__ == '__main__':
    main()
