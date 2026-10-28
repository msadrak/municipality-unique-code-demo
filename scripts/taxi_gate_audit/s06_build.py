"""Step 6 — build the deliverables from the step outputs (no new analysis happens here).

  Taxi_Gate_Deep_Audit_and_Integration_v1.xlsx
  تصمیمات_کارشناسی_تاکسیرانی_و_پایانه‌ها_v1.xlsx
  گزارش_ممیزی_عمیق_تاکسیرانی_و_پایانه‌ها_کد_یکتا_v1.md
"""
import csv
import datetime as dt
import json
import os
from collections import Counter, OrderedDict, defaultdict

import xlsxwriter

from common import OUT, WORK, SOURCES, SOURCE_UNIT, NATURE_FA, load, sha256
from decisions import DECISIONS
from expert_crosswalk import ENTRIES, REL_FA

AUDIT_XLSX = os.path.join(OUT, 'Taxi_Gate_Deep_Audit_and_Integration_v1.xlsx')
DEC_XLSX = os.path.join(OUT, 'تصمیمات_کارشناسی_تاکسیرانی_و_پایانه‌ها_v1.xlsx')
REPORT_MD = os.path.join(OUT, 'گزارش_ممیزی_عمیق_تاکسیرانی_و_پایانه‌ها_کد_یکتا_v1.md')
TODAY = dt.date.today().isoformat()
MEMO_MD = os.path.join(OUT, 'یادداشت_کارشناسی_CD-01_پایانه‌ها_v1.md')

VERDICT_FA = {'VALID': 'معتبر', 'PARTIALLY_VALID': 'معتبر برای یک جزء', 'PLAUSIBLE_REVIEW': 'قابل‌دفاع — بازبینی', 'RELATED_NOT_EQUIVALENT': 'مرتبط ولی غیرهم‌ارز',
              'INVALID_STRUCTURAL': 'نامعتبر — ناسازگاری ماهیت/طبقه', 'INVALID_SEMANTIC': 'نامعتبر — معنای متفاوت', 'INVALID_ENTITY': 'نامعتبر — نهاد/عدد متفاوت',
              'INVALID_PERSPECTIVE': 'نامعتبر — حساب آینهٔ طرف مقابل'}
STATUS_FA = {'EXACT_EQUIVALENCE_PROPOSED': 'هم‌ارزی دقیق (پیشنهادی)', 'RENAMED_EQUIVALENT': 'هم‌ارز با تغییر نام', 'POSSIBLE_EQUIVALENT_INCOMPLETE_EVIDENCE': 'هم‌ارز احتمالی — شواهد ناقص',
             'SPLIT_1_TO_N': 'تفکیک ۱←N', 'RECLASSIFIED': 'طبقه‌بندی مجدد', 'RELATED_ONLY': 'فقط مرتبط', 'NO_SUITABLE_CANDIDATE': 'بدون معادل مناسب',
             'EXPERT_REVIEW_REQUIRED': 'نیازمند تصمیم کارشناس', 'MODEL_AS_DIMENSION': 'مدل‌سازی به‌صورت بُعد (نه معین)'}


def fmt_num(x):
    try:
        return f'{int(x):,}'
    except (TypeError, ValueError):
        return str(x)


def e12(x):
    return f'{x / 1e12:.2f}e12' if abs(x) >= 1e11 else f'{x:,}'


class Book:
    def __init__(self, path, rtl=True):
        self.wb = xlsxwriter.Workbook(path, {'constant_memory': True, 'strings_to_numbers': False, 'strings_to_formulas': False,
                                             'strings_to_urls': False})
        self.rtl = rtl
        self.f_title = self.wb.add_format({'bold': True, 'font_size': 13, 'font_color': '#1F3864'})
        self.f_note = self.wb.add_format({'italic': True, 'font_color': '#595959', 'text_wrap': False})
        self.f_head = self.wb.add_format({'bold': True, 'bg_color': '#1F4E78', 'font_color': 'white', 'text_wrap': True, 'valign': 'top', 'border': 1})
        self.f_key = self.wb.add_format({'font_color': '#7F7F7F', 'font_size': 8, 'bg_color': '#F2F2F2'})
        self.f_txt = self.wb.add_format({'valign': 'top'})
        self.f_wrap = self.wb.add_format({'text_wrap': True, 'valign': 'top'})
        self.f_num = self.wb.add_format({'num_format': '#,##0', 'valign': 'top'})
        self.f_pct = self.wb.add_format({'num_format': '0.0%', 'valign': 'top'})
        self.sheets = OrderedDict()

    def table(self, name, title, note, cols, rows, wrap_cols=()):
        ws = self.wb.add_worksheet(name)
        if self.rtl:
            ws.right_to_left()
        for i, c in enumerate(cols):
            ws.set_column(i, i, c[2])
        ws.write(0, 0, title, self.f_title)
        ws.write(1, 0, note, self.f_note)
        for i, c in enumerate(cols):
            ws.write(2, i, c[1], self.f_head)
        for i, c in enumerate(cols):
            ws.write(3, i, c[0], self.f_key)
        r = 4
        n = 0
        for row in rows:
            for i, c in enumerate(cols):
                v = row.get(c[0]) if isinstance(row, dict) else row[i]
                if isinstance(v, (list, tuple, set)):
                    v = '; '.join(str(x) for x in v)
                elif isinstance(v, dict):
                    v = json.dumps(v, ensure_ascii=False)
                if v is None:
                    v = ''
                if isinstance(v, bool):
                    ws.write_string(r, i, 'YES' if v else 'NO', self.f_txt)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    ws.write_number(r, i, v, self.f_pct if len(c) > 3 and c[3] == 'pct' else self.f_num)
                else:
                    ws.write_string(r, i, str(v), self.f_wrap if c[0] in wrap_cols else self.f_txt)
            r += 1
            n += 1
        ws.freeze_panes(4, 0)
        if cols:
            ws.autofilter(3, 0, max(r - 1, 3), len(cols) - 1)
        self.sheets[name] = n
        return ws

    def close(self):
        self.wb.close()


def main():
    fx, coa, mt, ig, qa = load('forensics.json'), load('coa.json'), load('matching.json'), load('integration.json'), load('qa_registry.json')
    old = {x['code']: x for x in coa['old_rows']}
    audit = {a['old_code']: a for a in mt['audit']}
    new_rows = coa['new_rows']
    src_hash = {k: fx['container'][k]['sha256'] for k in SOURCES}

    # ------------------------------------------------------------------ KPI computation (single place)
    vc = Counter(a['verdict'] for a in mt['audit'])
    invalid = sum(v for k, v in vc.items() if k.startswith('INVALID'))
    org_rows = OrderedDict()
    for r in mt['crosswalk']:
        org_rows.setdefault((r['old_code'], r['org_scope']), r)
    st = Counter(e['status'] for e in ENTRIES)
    one_to_many = sum(1 for r in org_rows.values() if r['old_to_new_degree'] > 1)
    in_deg = defaultdict(set)
    for r in mt['crosswalk']:
        if r['relation'] in ('EQUIVALENT', 'RENAMED', 'SPLIT_COMPONENT', 'RECLASSIFIED', 'CANDIDATE_REVIEW') and r['new_code'] is not None:
            in_deg[r['new_code']].add((r['old_code'], r['org_scope']))
    many_to_one = sum(1 for v in in_deg.values() if len(v) > 1)
    unmapped = sum(1 for r in org_rows.values() if r['old_to_new_degree'] == 0)
    new_codes = {x['code'] for x in new_rows if x['code'] is not None}
    dup_codes = sorted(c for c, n in Counter(x['code'] for x in new_rows if x['code'] is not None).items() if n > 1)
    cat = Counter(a['category'] for a in coa['anomalies'])
    aev = ig['account_event']
    aev_sup = sum(1 for r in aev if r['analytical_status'] == 'ANALYTICALLY_SUPPORTED')
    cc_rows = [r for r in ig['activity_cc'] if r['cost_center_id']]
    cc_none = [r for r in ig['activity_cc'] if not r['cost_center_id']]
    dom = Counter(d['classification'] for d in ig['domain'] if d['source'].startswith('colleague'))
    dom_codes_taxi = sorted({d['code'] for d in ig['domain'] if d['classification'] == 'DIRECT_TAXI' and d['source'].startswith('colleague')})
    dom_codes_term = sorted({d['code'] for d in ig['domain'] if d['classification'] == 'DIRECT_TERMINAL' and d['source'].startswith('colleague')})
    led = Counter(d['classification'] for d in ig['domain_ledger'])
    rcn = ig['reconciliation']
    rec_b = rcn['proposal_buckets']
    tot_d = rcn['lineage']['debit']
    not_observed = sum(1 for x in new_rows if x.get('journal_1404') == 'NOT_OBSERVED' and x['code'] is not None)
    qa_c = Counter(t['status'] for t in qa)
    r = mt['reproduction']
    ctrl = mt['controlled']

    def usage(spec):
        if spec == 'MISSING_LEVEL2':
            return (sum(x['lines'] for x in coa['missing_level2']), sum(x['debit'] for x in coa['missing_level2']), sum(x['credit'] for x in coa['missing_level2']))
        org, code = (spec.split(':') + [None])[:2] if ':' in spec else (None, spec)
        x = old.get(code)
        if not x:
            return (0, 0, 0)
        u = [v for k, v in x['usage'].items() if org is None or k.startswith(org)]
        return (sum(v[0] for v in u), sum(v[1] for v in u), sum(v[2] for v in u))

    for d in DECISIONS:
        t = [usage(s) for s in d['impact']]
        d['impact_lines'] = sum(x[0] for x in t)
        d['impact_debit'] = sum(x[1] for x in t)
        d['impact_credit'] = sum(x[2] for x in t)
        d['impact_text'] = (f"{len(d['impact'])} حساب؛ {d['impact_lines']:,} ردیف؛ گردش بدهکار {d['impact_debit']:,} و بستانکار {d['impact_credit']:,} ({SOURCE_UNIT}) در ۱۴۰۴–۱۴۰۵"
                            if d['impact'] else 'غیرمبلغی (کیفیت داده/روش/حاکمیت)')

    KPIS = [
        ('K01', 'کل ردیف‌های منبع Sheet1 (داده)', 73461 if fx['inventory'][0]['data_rows_after_header'] == 73461 else fx['inventory'][0]['data_rows_after_header'], 'ردیف‌های A4:F73464؛ فیزیکی ۷۳٬۴۶۴ با ۳ ردیف سرآیند', 'Source_Inventory'),
        ('K02', 'ترکیب‌های یکتای ۶ فیلدی Sheet1', coa['sheet1_distinct'], 'هر ۲۳۴ ترکیب = ۲۳۴ ردیف Sheet2', 'Source_Inventory'),
        ('K03', 'ردیف‌های نمودار جدید (Sheet2)', len(new_rows), 'شامل ۳ ردیف بدون کد', 'CoA_Normalized'),
        ('K04', 'کدهای یکتای معین جدید', len(new_codes), 'کد غیرتهی', 'CoA_Normalized'),
        ('K05', 'حساب‌های قدیم (فهرست همکار)', len(old), f"{sum(1 for x in old.values() if x['level'] == 2)} معین + {sum(1 for x in old.values() if x['level'] == 3)} تفصیلی", 'CoA_Normalized'),
        ('K06', 'کدهای تکراری در نمودار جدید', len(dup_codes), ', '.join(map(str, dup_codes)), 'CoA_Integrity_QA'),
        ('K07', 'تخصیص متعارض کد-عنوان', cat['ONE_CODE_MULTIPLE_TITLES'], '۴۱۰۱۰ و ۱۴۰۰۴ (+۱ تکرار املایی ۱۲۰۰۵)', 'CoA_Integrity_QA'),
        ('K08', 'تعارض والد (یک کد دو والد)', cat['ONE_CODE_MULTIPLE_PARENTS'], '۱۱۵۱۱ و ۸۱۰۱۰', 'CoA_Integrity_QA'),
        ('K09', 'تعارض والد با نمودار دفتر ۱۴۰۴', cat['CROSS_SOURCE_PARENT_CONFLICT'], 'همان کد زیر کل متفاوت', 'CoA_Integrity_QA'),
        ('K10', 'کد قدیم با دو معنا بین دو سازمان', cat['OLD_CODE_MEANING_COLLISION_BETWEEN_ORGS'], 'فهرست همکار عنوان پایانه‌ها را برداشته (۲۷/۲۷)', 'CoA_Integrity_QA'),
        ('K11', 'تطبیق‌های پیشنهادی همکار (بهترین)', len(mt['audit']), f"+ {len(mt['candidates']) - len(mt['audit'])} گزینهٔ دوم/سوم + {len(mt['kol_pairs'])} جفت کل", 'Original_Mapping_Audit'),
        ('K12', 'تطبیق‌های معتبر به‌طور مستقل', vc['VALID'], f"+ {vc['PARTIALLY_VALID']} معتبر فقط برای یک جزء", 'Original_Mapping_Audit'),
        ('K13', 'تطبیق‌های آشکارا نامعتبر', invalid, f"ساختاری {vc['INVALID_STRUCTURAL']}، معنایی {vc['INVALID_SEMANTIC']}، نهاد/عدد {vc['INVALID_ENTITY']}، آینه {vc['INVALID_PERSPECTIVE']}", 'Original_Mapping_Audit'),
        ('K14', 'تطبیق‌های مبهم', vc['RELATED_NOT_EQUIVALENT'] + vc['PLAUSIBLE_REVIEW'], f"مرتبط غیرهم‌ارز {vc['RELATED_NOT_EQUIVALENT']} + قابل‌دفاع {vc['PLAUSIBLE_REVIEW']}", 'Original_Mapping_Audit'),
        ('K15', 'والد نادرست/پیدانشده در ستون‌های V2', r['parent_wrong'] + r['parent_not_found'], f"{r['parent_wrong']} نادرست + {r['parent_not_found']} «پیدا نشد» از ۴۷۱", 'Candidate_Audit'),
        ('K16', 'ردیف‌های حساب قدیم (سازمان‌محور) در crosswalk', len(org_rows), f'{len(old)} کد؛ ۸ کد با دو معنای سازمانی', 'Account_Crosswalk_Proposed'),
        ('K17', 'حساب‌های قدیم بدون مقصد مهاجرت', unmapped, f"NO_SUITABLE_CANDIDATE={st['NO_SUITABLE_CANDIDATE']}؛ بقیه فقط رابطهٔ مرتبط/تصمیم", 'Account_Crosswalk_Proposed'),
        ('K18', 'نگاشت یک به چند (۱←N)', one_to_many, 'ردیف‌های سازمان‌محور با بیش از یک مقصد', 'Account_Crosswalk_Proposed'),
        ('K19', 'نگاشت چند به یک (N→۱)', many_to_one, 'کدهای جدید با بیش از یک مبدأ', 'Account_Crosswalk_Proposed'),
        ('K20', 'پیشنهادهای حساب↔رویداد', len(aev), 'هم‌رخدادی در طبقه‌بندی موقت v2.1', 'Account_Event_Crosswalk'),
        ('K21', 'روابط حساب↔رویداد با پشتوانهٔ تحلیلی', aev_sup, 'پشتیبانی قوی/متوسط + سازگاری معنایی + crosswalk قوی؛ تأییدنشده', 'Account_Event_Crosswalk'),
        ('K22', 'روابط حساب↔رویداد نیازمند بازبینی', len(aev) - aev_sup, 'هیچ رابطه‌ای تأیید نشده (۰ APPROVED)', 'Account_Event_Crosswalk'),
        ('K23', 'روابط فعالیت↔مرکز هزینه با شاهد', len(cc_rows), f"{sum(x['lines'] for x in cc_rows):,} ردیف (از دفتر v2.1، نه از فایل‌های همکار)", 'Activity_CC_Crosswalk'),
        ('K24', 'روابط مرکز هزینه غیرقابل‌اشتقاق', len(cc_none), f"{sum(x['lines'] for x in cc_none):,} ردیف واجد شرایط بدون مرکز؛ از فایل‌های همکار: ۱۰۰٪ غیرقابل‌اشتقاق", 'Activity_CC_Crosswalk'),
        ('K25', 'سوابق اختصاصی تاکسیرانی در فایل‌های همکار', len(dom_codes_taxi), f"{dom['DIRECT_TAXI']} سابقه (با تکرار در ۸۸۸۸۸۸۸۸)؛ در دفتر سازمان: {led['DIRECT_TAXI']} زیرحساب", 'Taxi_Terminal_Evidence'),
        ('K26', 'سوابق اختصاصی پایانه در فایل‌های همکار', len(dom_codes_term), f"در دفتر سازمان: {led['DIRECT_TERMINAL']} زیرحساب", 'Taxi_Terminal_Evidence'),
        ('K27', 'تصمیمات نیازمند تأیید کمیته', len(DECISIONS), 'TG-D-01 … TG-D-22 (پیوند با CD-xx قبلی)', 'Governance_Decisions'),
        ('K28', 'ردیف‌های دفتر سازمان‌ها در تبارشناسی', rcn['lineage']['lines'], f"بدهکار=بستانکار={tot_d:,} ({SOURCE_UNIT})", 'Historical_Lineage_Recon'),
        ('K29', 'سهم مبلغ قابل‌نگاشت قوی (۱←۱ هم‌ارز)', rec_b.get('SINGLE_TARGET_STRONG', [0, 0, 0])[1] / tot_d, 'بدهکار سطل SINGLE_TARGET_STRONG ÷ کل', 'Historical_Lineage_Recon'),
        ('K30', 'آزمون‌های QA', len(qa), f"PASS {qa_c['PASS']}، REVIEW {qa_c['REVIEW']}، FAIL {qa_c['FAIL']}، NOT TESTABLE {qa_c['NOT TESTABLE']}", 'QA_Reproducibility'),
    ]

    # ------------------------------------------------------------------ workbook
    b = Book(AUDIT_XLSX)
    readme = [
        ('عنوان', 'ممیزی عمیق و یکپارچه‌سازی Taxi-Gate با معماری کد یکتا — نسخهٔ ۱'),
        ('تاریخ', TODAY),
        ('وضعیت', 'PROPOSED / OBSERVED — هیچ نگاشت، رابطه یا کاردینالیتی «تأییدشده» نیست. فایل‌های منبع تغییر نکرده‌اند (QA-SRC-02).'),
        ('منبع ۱', f"Taxi-Gate_Version1.xlsx — SHA-256 {src_hash['V1']}"),
        ('منبع ۲', f"Taxi-Gate_version2.xlsx — SHA-256 {src_hash['V2']}"),
        ('منبع ۳ (پروژهٔ قبلی)', 'tt_v21.sqlite: دفتر Sanad (۱۱۱٬۶۰۰ ردیف) و حساب‌ها (Hesab، ۲٬۱۷۸) تاکسیرانی و پایانه‌ها ۱۴۰۴–۱۴۰۵؛ line_event/line_cc طبقه‌بندی موقت v2.1'),
        ('منبع ۴', 'فرهنگ رویداد v7.1 (FE-01…FE-70، کاندید)، cc_master.json (۷۵ مرکز، پیشنهادی)، committee_decisions_v2.1.xlsx، account_crosswalk.csv v2.1، journal_records.sqlite (دفتر ۱۴۰۴ شهرداری)'),
        ('دامنه', 'هر ۱۹ شیت دو نسخه؛ نمودار جدید (۲۳۴ ردیف) و فهرست قدیم (۱۵۷ حساب)؛ همهٔ ۴۷۱ جفت تطبیق V2؛ اتصال به رویداد، مرکز هزینه و دفتر تاریخی.'),
        ('تفسیر کد ۱/۲', 'در شیت moen: ۱ = نمودار جدید شهرداری، ۲ = نمودار قدیم سازمان‌ها. در kol!F: «1» = فقط پایانه‌ها، «2» = فقط تاکسیرانی، «1,2» = هر دو [استنتاج، ۳۹/۳۹ سازگار با Hesab].'),
        ('فرض', f'مبالغ «{SOURCE_UNIT}» هستند؛ ماهیت حساب از کل/طبقه استخراج شده نه از منبع؛ عنوان‌های دارای نام شخص و شمارهٔ حساب بانکی ماسک شده‌اند؛ شرح اسناد (Sharh/Des) صادر نشده است.'),
        ('محدودیت ۱', 'فایل‌های همکار سند، مبلغ، تاریخ، واحد، فعالیت یا کد بودجه ندارند؛ اعتبارسنجی مانده/رویداد/مرکز هزینه فقط از طریق دفتر سازمان‌ها (پروژهٔ قبلی) ممکن شد.'),
        ('محدودیت ۲', 'منشأ Sheet1 (۷۳٬۴۶۱ ردیف) شناسایی نشد؛ فراوانی تکرار معنای تراکنشی ندارد (QA-POP-03/04).'),
        ('محدودیت ۳', 'نمودار رسمی و نسخه‌دار حساب شهرداری، Master_Data_ERP و Doc_No_Mapping مستقل در مخزن یافت نشد (Prior_Artifacts).'),
        ('محدودیت ۴', 'روابط حساب↔رویداد و فعالیت↔مرکز از طبقه‌بندی موقت v2.1 مشاهده شده‌اند و قاعده نیستند.'),
        ('برچسب‌ها', 'PASS فقط با شاهد محاسبه‌شده؛ NOT TESTABLE وقتی فیلد در منبع نیست؛ REVIEW برای یافته‌های نیازمند قضاوت؛ FAIL برای نقص اثبات‌شده.'),
        ('بازتولید', 'python scripts/taxi_gate_audit/run_all.py  (s01 → s07)؛ خروجی‌های میانی در data/work/taxi_gate_audit/'),
        ('کلید ردیف', 'هر ردیف یک شناسهٔ پایدار دارد: COA-xxx، OMA-xxx، XW-xxxx، AEX-xxxx، LN-xxxxxx، TG-D-xx؛ ارجاع منبع به‌صورت Sheet!Range یا Source_Record_ID.'),
    ]
    b.table('README', 'README — دامنه، منابع، فرض‌ها، محدودیت‌ها', 'Taxi-Gate deep audit v1', [('item', 'مورد', 24), ('value', 'توضیح', 150)],
            [dict(item=a, value=v) for a, v in readme] + [dict(item=f'شیت: {n}', value=d) for n, d in (
                ('Source_Inventory', 'موجودی کامل شیت‌ها'), ('Version_Diff', 'تفاوت V1/V2'), ('CoA_Normalized', 'سلسله‌مراتب نرمال‌شده'),
                ('CoA_Integrity_QA', 'ناهنجاری‌ها'), ('Original_Mapping_Audit', 'ممیزی ۱۵۷ بهترین تطبیق'), ('Candidate_Audit', 'ممیزی ۴۷۱ گزینه'),
                ('Kol_Pair_Audit', 'جفت‌های سطح کل همکار'), ('Account_Crosswalk_Proposed', 'crosswalk پیشنهادی با کاردینالیتی'),
                ('Account_Split_Evidence', 'مبنای تفکیک زیرحساب‌ها با مبلغ'), ('Alternative_Candidates', 'گزینه‌های رتبه‌بندی‌شده از ۴ منبع'),
                ('Taxi_Terminal_Evidence', 'شواهد دامنه'), ('Terminal_CD01_Evidence', 'بازمحاسبهٔ CD-01'), ('Account_Event_Crosswalk', 'حساب↔رویداد'),
                ('Event_Dimension_Cardinality', 'کاردینالیتی مشاهده/پیشنهاد/تأیید'), ('Activity_CC_Crosswalk', 'فعالیت↔مرکز هزینه'),
                ('Account_CC_Observed', 'حساب↔مرکز مشاهده‌شده'), ('Historical_Lineage_Recon', 'آشتی مبالغ'), ('Lineage_Lines', 'تبارشناسی ۱۱۱٬۶۰۰ ردیف'),
                ('Prior_Artifacts', 'موجودی مصنوعات قبلی'), ('Prior_Project_Comparison', 'مقایسه و پاسخ Q1–Q12'), ('Governance_Decisions', 'تصمیمات باز'),
                ('Audited_Examples', 'نمونه‌های ممیزی‌شده'), ('QA_Reproducibility', 'آزمون‌های بازتولیدپذیر'), ('Executive_KPIs', 'شاخص‌ها'))])

    inv_rows = []
    for x in fx['inventory']:
        inv_rows.append(dict(workbook=x['workbook'], sheet=x['sheet'], visibility=x['visibility'], used_range=x['used_range'], physical_rows=x['physical_rows'],
                             nonempty_rows=x['nonempty_rows'], columns=x['columns'], data_rows=x['data_rows_after_header'], distinct=x['distinct_data_rows'],
                             duplicates=x['duplicate_data_rows'], formulas=x['formula_cells'], merged=', '.join(x['merged']), autofilter=x['autofilter'] or '',
                             freeze=x['freeze'] or '', tables=len(x['tables']), dv=x['data_validations'], cf=x['conditional_formats'],
                             headings=' | '.join(' ؛ '.join(f'{c}={v}' for c, v in h) for h in x['headings'])[:900],
                             types=json.dumps(x['column_types'], ensure_ascii=False)[:900], formula_patterns=json.dumps(x['formula_patterns'], ensure_ascii=False)[:900],
                             key_columns=json.dumps(x.get('column_distinct_missing', {}), ensure_ascii=False)[:900], role=x['role']))
    for tag in ('V1', 'V2'):
        c = fx['container'][tag]
        inv_rows.append(dict(workbook=tag, sheet='(workbook)', visibility='', used_range='', physical_rows='', nonempty_rows='', columns='', data_rows='', distinct='',
                             duplicates='', formulas='', merged='', autofilter='', freeze='', tables='', dv='', cf='',
                             headings=f"defined names: {len(c['defined_names'])} (_xlnm._FilterDatabase only); external links: {len(c['external_links'])}",
                             types=f"SHA-256 {c['sha256']}; bytes {c['bytes']:,}; creator {c['creator']}; lastModifiedBy {c['last_modified_by']}; modified {c['modified']}",
                             formula_patterns=', '.join(c['parts']), role='OOXML container'))
    b.table('Source_Inventory', 'موجودی کامل شیت‌ها و ساختار فایل', 'همهٔ شیت‌ها قابل‌مشاهده‌اند؛ جدول اکسل، اعتبارسنجی داده و پیوند خارجی وجود ندارد',
            [('workbook', 'نسخه', 7), ('sheet', 'شیت', 22), ('visibility', 'نمایش', 9), ('used_range', 'محدوده', 12), ('physical_rows', 'ردیف فیزیکی', 10),
             ('nonempty_rows', 'ردیف غیرتهی', 10), ('columns', 'ستون', 7), ('data_rows', 'ردیف داده', 10), ('distinct', 'ردیف یکتا', 9), ('duplicates', 'تکراری', 9),
             ('formulas', 'فرمول', 8), ('merged', 'ادغام', 18), ('autofilter', 'فیلتر', 12), ('freeze', 'ثابت', 6), ('tables', 'جدول', 6), ('dv', 'DV', 5),
             ('cf', 'CF', 5), ('headings', 'سرآیندها', 60), ('types', 'نوع داده/هش', 50), ('formula_patterns', 'الگوی فرمول/اجزا', 50),
             ('key_columns', 'یکتا/خالی هر ستون', 50), ('role', 'نقش', 45)], inv_rows)

    d = fx['diff']
    diff_rows = [dict(item='شیت‌های افزوده در V2', v1='—', v2=', '.join(d['added']), finding='مشتق ایستا (بدون فرمول)؛ داده پایه تغییر نکرده')]
    diff_rows.append(dict(item='شیت‌های حذف/تغییرنام', v1='', v2='', finding='هیچ (همهٔ ۸ شیت V1 با همان نام و محتوا در V2)'))
    for n, (a, bb) in d['position_change'].items():
        diff_rows.append(dict(item=f'جایگاه شیت {n}', v1=a, v2=bb, finding='جابه‌جایی به‌دلیل درج «خلاصه تطبیق» در ابتدا؛ sheetId بازشماری شده'))
    for n, v in d['common_sheets'].items():
        diff_rows.append(dict(item=f'{n}: سلول/مقدار/فرمول/سبک', v1=v['cells'], v2=f"{v['value_diffs']}/{v['formula_or_constant_diffs']}/{v['style_diffs']}",
                              finding='یکسان' if not (v['value_diffs'] or v['formula_or_constant_diffs'] or v['style_diffs']) else 'متفاوت'))
        if v['column_width_diffs']:
            diff_rows.append(dict(item=f'{n}: عرض ستون', v1=json.dumps(v['column_width_diffs']), v2='', finding='فقط قالب‌بندی'))
        if v['dynamic_array_flags'][0] != v['dynamic_array_flags'][1]:
            diff_rows.append(dict(item=f'{n}: پرچم آرایهٔ پویا (cm=1)', v1=v['dynamic_array_flags'][0], v2=v['dynamic_array_flags'][1],
                                  finding='در V2 حذف شده؛ فرمول‌های UNIQUE/FILTER به آرایهٔ ثابت قدیمی تبدیل می‌شوند (ریسک عدم گسترش پویا)'))
        diff_rows.append(dict(item=f'{n}: اندازهٔ XML', v1=v['xml_bytes'][0], v2=v['xml_bytes'][1], finding='بازنویسی فایل (شاخص سبک)، بدون تغییر محتوا'))
    diff_rows.append(dict(item='اجزای حذف‌شده در V2', v1=', '.join(d['parts_removed_in_v2']), v2='', finding='metadata.xml (آرایهٔ پویا) و تنظیمات چاپ'))
    diff_rows.append(dict(item='اجزای افزوده در V2', v1='', v2=', '.join(d['parts_added_in_v2']), finding='سه شیت جدید'))
    for k, (a, bb) in d['core'].items():
        diff_rows.append(dict(item=f'docProps: {k}', v1=a, v2=bb, finding=''))
    diff_rows.append(dict(item='آیا V2 دادهٔ پایه را بهبود داده؟', v1='', v2='', finding='خیر — فقط تحلیل شباهت متنی اضافه شده'))
    diff_rows.append(dict(item='آیا V2 خطای جدید وارد کرده؟', v1='', v2='', finding=f"بله — ستون‌های گروه/کل: {r['parent_wrong']} نادرست و {r['parent_not_found']} «پیدا نشد» از ۴۷۱ (QA-MAT-04)؛ "
                                                                                f"{sum(1 for a in mt['audit'] if a['structural'] == 'INCOMPATIBLE')} بهترین گزینهٔ ناسازگار ساختاری"))
    b.table('Version_Diff', 'تفاوت‌های اثبات‌شدهٔ V1 و V2 (سطح سلول، فرمول، قالب و ظرف OOXML)', 'مقایسهٔ کامل سلول‌به‌سلول ۸ شیت مشترک',
            [('item', 'مورد', 40), ('v1', 'V1', 40), ('v2', 'V2', 40), ('finding', 'یافته', 80)], diff_rows, wrap_cols=('v1', 'finding'))

    coa_rows = []
    for x in new_rows:
        coa_rows.append(dict(system='NEW — نمودار جدید شهرداری (Sheet2)', level='معین', code=x['code'], title=x['title'], parent_code=x['kol'], parent_title=x['kol_title'],
                             cls=x['cls'], cls_title=x['cls_title'], depth=3, nature=NATURE_FA.get(x['nature']), normal_side=x['normal_side'], ref=x['src'],
                             sheet1_rows=x['sheet1_rows'], journal_1404=x.get('journal_1404', ''), scope='شهرداری اصفهان (نمونه با حساب‌های رابط منطقه ۶)',
                             validity='در فایل نیست', flags=('کد تکراری؛ ' if x['dup_code'] else '') + ('' if x['prefix_ok'] else 'پیشوند≠والد؛ ')))
    for x in coa['old_rows']:
        coa_rows.append(dict(system='OLD — نمودار سازمان‌های وابسته (moen کد ۲)', level='معین' if x['level'] == 2 else 'تفصیلی', code=x['code'], title=x['title_masked'],
                             parent_code=x['parent_code'], parent_title=' / '.join(f"{o}: {'، '.join(t)}" for o, t in x['parent_title_by_org'].items() if t),
                             cls=x['kol'] // 100, cls_title='', depth=x['level'] + 1, nature=NATURE_FA.get(x['nature']), normal_side=x['normal_side'], ref=x['src'],
                             sheet1_rows='', journal_1404='', scope=', '.join(x['orgs']),
                             validity=', '.join(sorted(x['hesab_rows'])), flags=(f"عنوان از: {','.join(x['title_source_org'])}؛ " if x['org_title_variants'] > 1 else '') +
                             f"گردش {x['lines_total']:,} ردیف",
                             ledger_net=x['debit_total'] - x['credit_total'],
                             ledger_side=('بدهکار' if x['debit_total'] > x['credit_total'] else 'بستانکار' if x['credit_total'] > x['debit_total'] else
                                          ('صفر' if x['lines_total'] else 'بدون گردش'))))
    for x in coa['old_kol']:
        coa_rows.append(dict(system='OLD — کل (kol!E:G)', level='کل', code=x['code'], title=x['title'], parent_code='', parent_title='', cls=int(x['code'][0]), cls_title='',
                             depth=1, nature='', normal_side='', ref=x['src'], sheet1_rows='', journal_1404='', scope=', '.join(x['orgs']), validity='',
                             flags=f"kol!F={x['flag']}"))
    b.table('CoA_Normalized', 'سلسله‌مراتب نرمال‌شدهٔ حساب‌ها (طبقه → کل → معین → تفصیلی)', 'ماهیت و سمت عادی از طبقه/کل مشتق شده‌اند (نه از منبع)',
            [('system', 'نسخهٔ کدگذاری', 34), ('level', 'سطح', 8), ('code', 'کد', 12), ('title', 'عنوان', 40), ('parent_code', 'کد والد', 11), ('parent_title', 'عنوان والد', 32),
             ('cls', 'طبقه', 6), ('cls_title', 'عنوان طبقه', 12), ('depth', 'عمق', 5), ('nature', 'ماهیت (مشتق)', 22), ('normal_side', 'سمت عادی', 9), ('ref', 'ارجاع منبع', 18),
             ('sheet1_rows', 'ردیف در Sheet1', 9), ('journal_1404', 'در دفتر ۱۴۰۴', 22), ('scope', 'دامنهٔ سازمانی', 18), ('validity', 'اعتبار سالانه (Hesab)', 30),
             ('flags', 'نشانه‌ها', 40), ('ledger_net', 'خالص گردش ۱۴۰۴–۱۴۰۵ (بد−بس)', 18), ('ledger_side', 'سمت مشاهده‌شده', 12)], coa_rows)

    b.table('CoA_Integrity_QA', 'ناهنجاری‌های نمودار حساب (بدون حل خودکار)', f"{len(coa['anomalies'])} ناهنجاری؛ دستهٔ هر مورد و تصمیم کارشناسی",
            [('anomaly_id', 'شناسه', 9), ('category', 'دسته', 30), ('source', 'منبع', 24), ('code', 'کد', 14), ('title', 'عنوان', 36), ('parent', 'والد', 12),
             ('conflicting_record', 'سابقهٔ متعارض', 50), ('consequence', 'پیامد حسابداری', 50), ('suggested_treatment', 'پیشنهاد', 36),
             ('expert_decision_required', 'تصمیم کارشناس', 10), ('severity', 'شدت', 8), ('source_rows', 'ردیف‌ها', 30)], coa['anomalies'],
            wrap_cols=('conflicting_record', 'consequence'))

    oma = []
    for a in mt['audit']:
        oma.append(dict(a, verdict_fa=VERDICT_FA[a['verdict']], old_nature_fa=NATURE_FA.get(a['old_nature']), proposal_status_fa=STATUS_FA.get(a['proposal_status'])))
    b.table('Original_Mapping_Audit', 'ممیزی همهٔ ۱۵۷ «بهترین گزینه» همکار', 'شباهت متنی ≠ هم‌ارزی حسابداری؛ والد واقعی از Sheet2',
            [('audit_id', 'شناسه', 8), ('src', 'ارجاع V2', 22), ('moen_row', 'ردیف moen', 7), ('old_code', 'کد قدیم', 11), ('old_title', 'عنوان قدیم', 32),
             ('old_nature_fa', 'ماهیت قدیم', 16), ('orgs', 'سازمان‌ها', 14), ('title_source_org', 'منبع عنوان', 10), ('meaning_collision', 'برخورد معنا', 7),
             ('lines', 'ردیف دفتر', 8), ('debit', 'بدهکار', 16), ('credit', 'بستانکار', 16), ('best_code', 'بهترین کد', 9), ('best_title', 'عنوان پیشنهادی', 32),
             ('best_score', 'شباهت٪', 7), ('colleague_status', 'وضعیت همکار', 18), ('parent_shown', 'والد نمایش‌داده', 12), ('parent_true', 'والد واقعی', 12),
             ('new_nature', 'ماهیت جدید', 14), ('structural', 'آزمون ساختاری', 13), ('verdict', 'حکم', 18), ('verdict_fa', 'حکم (فارسی)', 22),
             ('agrees_with_proposal', 'هم‌سو با پیشنهاد', 7), ('proposal_status_fa', 'وضعیت پیشنهاد مستقل', 22), ('proposal_targets', 'مقصد(های) پیشنهادی', 34),
             ('reason', 'استدلال/شاهد', 70), ('other_org_rows', 'معنای سازمان دیگر', 30), ('decision', 'تصمیم', 9)], oma, wrap_cols=('reason',))
    b.table('Candidate_Audit', 'ممیزی همهٔ ۴۷۱ جفت (بهترین + دو گزینهٔ بعدی)', 'شباهت بازتولید شده؛ والد نمایش‌داده با والد واقعی مقایسه شده',
            [('src', 'ارجاع', 24), ('old_code', 'کد قدیم', 11), ('rank', 'رتبه', 5), ('new_code', 'کد جدید', 9), ('new_title', 'عنوان جدید', 36), ('score', 'شباهت٪', 7),
             ('reproduced_score', 'شباهت بازتولید', 8), ('parent_shown', 'والد نمایش', 12), ('parent_true', 'والد واقعی', 12), ('parent_status', 'وضعیت والد', 14),
             ('structural', 'ساختاری', 12), ('new_nature', 'ماهیت جدید', 14), ('verdict', 'حکم', 30), ('entity_number_conflict', 'تعارض عدد نهاد', 8)], mt['candidates'])
    b.table('Kol_Pair_Audit', 'جفت‌های صریح سطح کل در «حساب کل کد 1»', 'تنها نگاشت صریح دست‌ساز همکار',
            [('src', 'ارجاع', 24), ('pair', 'جفت', 10), ('title', 'عنوان', 32), ('new_kol', 'کل جدید', 8), ('old_kol', 'کل قدیم', 8), ('verdict', 'حکم', 16), ('reason', 'استدلال', 70)],
            mt['kol_pairs'])

    xw = [dict(r, account_status_fa=STATUS_FA.get(r['account_status']), old_nature_fa=NATURE_FA.get(r['old_nature'])) for r in mt['crosswalk']]
    b.table('Account_Crosswalk_Proposed', 'crosswalk بازارزیابی‌شده (قدیم → جدید) با کاردینالیتی صریح', 'PROPOSED — EXPERT_REVIEW_REQUIRED؛ هیچ ردیفی تأیید نشده؛ کلید = (کد، دامنهٔ سازمان)',
            [('row_id', 'شناسه', 8), ('old_code', 'کد قدیم', 11), ('org_scope', 'دامنه', 9), ('old_title', 'عنوان قدیم', 30), ('old_nature_fa', 'ماهیت', 16),
             ('account_status', 'وضعیت', 22), ('account_status_fa', 'وضعیت (فارسی)', 22), ('new_code', 'کد جدید', 9), ('new_title', 'عنوان جدید', 32), ('new_parent', 'والد جدید', 12),
             ('relation', 'نوع رابطه', 20), ('relation_note', 'مبنا/یادداشت', 34), ('structural', 'ساختاری', 12), ('cardinality', 'کاردینالیتی', 9),
             ('old_to_new_degree', 'تعداد مقصد', 7), ('new_from_old_degree', 'تعداد مبدأ', 7), ('lines', 'ردیف دفتر', 8), ('debit', 'بدهکار', 16), ('credit', 'بستانکار', 16),
             ('reason', 'استدلال', 60), ('domain', 'دامنه', 16), ('decision', 'تصمیم', 9), ('review_status', 'بازبینی', 18), ('approval_status', 'تأیید', 14)], xw, wrap_cols=('reason',))
    b.table('Account_Split_Evidence', 'مبنای تفکیک ۱←N در سطح زیرحساب (گردش ۱۴۰۴–۱۴۰۵)', 'جمع زیرحساب‌ها = گردش حساب (QA-XW-04)؛ مبالغ ' + SOURCE_UNIT,
            [('old_code', 'کد قدیم', 11), ('org', 'سازمان', 9), ('sub_account', 'زیرحساب', 11), ('sub_title', 'عنوان زیرحساب (ماسک)', 36), ('proposed_new', 'مقصد پیشنهادی', 10),
             ('new_title', 'عنوان مقصد', 30), ('relation', 'رابطه', 18), ('lines', 'ردیف', 8), ('debit', 'بدهکار', 17), ('credit', 'بستانکار', 17),
             ('share_of_account_debit', 'سهم از بدهکار حساب', 9, 'pct')], ig['split_rows'])
    b.table('Alternative_Candidates', 'گزینه‌های جایگزین رتبه‌بندی‌شده از چهار منبع شاهد', 'پیشنهاد مستقل؛ تطبیق متنی همکار؛ crosswalk v2.1؛ روش کنترل‌شده A(کل مجاز)→B(ماهیت)→C(شباهت با هم‌معنا)',
            [('old_code', 'کد قدیم', 11), ('old_title', 'عنوان قدیم', 30), ('rank', 'رتبه', 5), ('new_code', 'کد جدید', 9), ('new_title', 'عنوان جدید', 32), ('new_parent', 'والد', 12),
             ('source', 'منبع شاهد', 30), ('relation', 'نوع', 22), ('structural', 'ساختاری', 12), ('similarity', 'شباهت', 7), ('evidence', 'شاهد', 60)], mt['alternatives'])

    dom_rows = [dict(x, curated_domain=x.get('curated_domain', '')) for x in ig['domain'] if x['classification'] != 'GENERAL' or x['source'].endswith('(moen)')]
    dom_rows += ig['domain_ledger']
    dom_rows += [dict(source='Sanad.CodeVahed — واحد/پایانه (فقط در دفتر)', ref=f['unit_segment'], code=f['unit_segment'], title=f['name'], classification='DIRECT_TERMINAL (unit)',
                      matched_term='', usage=f"{f['lines']:,} ردیف؛ بدهکار {f['debit']:,}", curated_domain='', note=f['source']) for f in ig['facilities']]
    b.table('Taxi_Terminal_Evidence', 'شواهد اختصاصی تاکسیرانی و پایانه‌ها', 'فایل‌های همکار فقط عنوان حساب دارند؛ شواهد زیرحساب/واحد از دفتر سازمان‌ها (پروژهٔ قبلی) است',
            [('source', 'منبع', 36), ('ref', 'ارجاع', 18), ('code', 'کد', 16), ('title', 'عنوان', 40), ('classification', 'طبقه‌بندی (از عنوان)', 22),
             ('matched_term', 'واژهٔ شاهد', 14), ('curated_domain', 'دامنهٔ کارشناسی', 18), ('usage', 'گردش', 34), ('note', 'یادداشت', 30)], dom_rows)
    cd = [dict(x, table='FLOW') for x in ig['cd01']] + [dict(fy=x['fy'], account=x['account'], doc_kind='OPENING / ALL', lines='', debit='', credit='',
                                                             net=f"افتتاحیه {x['opening_net']:,} ؛ کل اسناد {x['all_documents_net']:,}", table='BALANCE') for x in ig['cd01_balances']]
    b.table('Terminal_CD01_Evidence', 'بازمحاسبهٔ مستقل شواهد CD-01 از دفتر پایانه‌ها', 'بدون نتیجه‌گیری حقوقی؛ الگو با عاملیت سازگار است ولی آن را اثبات نمی‌کند',
            [('table', 'جدول', 8), ('fy', 'سال', 6), ('account', 'حساب', 10), ('doc_kind', 'نوع سند', 20), ('lines', 'ردیف', 8), ('debit', 'بدهکار', 17), ('credit', 'بستانکار', 17),
             ('net', 'خالص', 30)], cd)
    b.table('Account_Event_Crosswalk', 'رابطهٔ پیشنهادی حساب ↔ رویداد مالی کانونی (چند به چند)', 'مشاهده‌شده در طبقه‌بندی موقت v2.1؛ اسناد افتتاحیه/اختتامیه حذف؛ هیچ رابطه‌ای تأیید نشده',
            [('rel_id', 'شناسه', 9), ('old_code', 'کد حساب', 11), ('org', 'سازمان', 9), ('old_title', 'عنوان حساب', 30), ('account_nature', 'ماهیت', 14),
             ('account_coding_version', 'نسخهٔ کدگذاری', 22), ('proposed_new_accounts', 'حساب(های) جدید پیشنهادی', 26), ('crosswalk_status', 'وضعیت crosswalk', 20),
             ('event_id', 'رویداد', 9), ('event_title', 'عنوان رویداد', 36), ('event_origin', 'منشأ رویداد', 22), ('relation_type', 'نوع رابطه', 16),
             ('lines', 'ردیف', 7), ('share_of_account_operational_lines', 'سهم از ردیف‌های عملیاتی حساب', 9, 'pct'), ('debit', 'بدهکار', 16), ('credit', 'بستانکار', 16),
             ('evidence_source', 'منبع شاهد', 30), ('observed_or_inferred', 'مشاهده/استنتاج', 22), ('matching_method', 'روش', 20), ('support', 'اطمینان (پشتوانه)', 9),
             ('semantic_compatibility', 'سازگاری معنایی', 18), ('analytical_status', 'وضعیت تحلیلی', 20), ('expert_review_status', 'بازبینی', 9),
             ('approval_status', 'تأیید', 12)], aev)
    b.table('Event_Dimension_Cardinality', 'کاردینالیتی ابعاد هر رویداد: مشاهده‌شده / پیشنهادی / تأییدشده', 'ستون «تأییدشده» همیشه Needs Decision است',
            [('event_id', 'رویداد', 9), ('event_title', 'عنوان', 34), ('lines', 'ردیف', 8), ('documents', 'سند', 7), ('accounts_per_doc_observed', 'حساب در سند (مشاهده)', 10),
             ('account_observed', 'حساب مشاهده', 9), ('account_proposed', 'حساب پیشنهاد', 9), ('account_approved', 'حساب تأیید', 12),
             ('cc_observed', 'مرکز مشاهده', 20), ('cc_proposed', 'مرکز پیشنهاد', 26), ('cc_approved', 'مرکز تأیید', 12),
             ('contract_observed', 'قرارداد مشاهده', 18), ('contract_proposed', 'قرارداد پیشنهاد', 12), ('contract_approved', 'قرارداد تأیید', 12),
             ('project_observed', 'پروژه مشاهده', 22), ('project_proposed', 'پروژه پیشنهاد', 12), ('project_approved', 'پروژه تأیید', 12),
             ('person_observed', 'شخص مشاهده', 18), ('person_proposed', 'شخص پیشنهاد', 9), ('person_approved', 'شخص تأیید', 12),
             ('org_unit_observed', 'واحد مشاهده', 18), ('org_unit_proposed', 'واحد پیشنهاد', 9), ('org_unit_approved', 'واحد تأیید', 12),
             ('source_activity_observed', 'کد فعالیت منبع', 22)], ig['dims'])
    b.table('Activity_CC_Crosswalk', 'فعالیت ↔ مرکز هزینه (فقط جایی که شاهد وجود دارد)', 'از طبقه‌بندی موقت v2.1؛ فایل‌های همکار هیچ فعالیتی ندارند → INSUFFICIENT SOURCE EVIDENCE',
            [('activity_id', 'شناسهٔ فعالیت', 22), ('activity_title', 'عنوان فعالیت', 34), ('organization', 'سازمان', 9), ('source_code', 'کد منبع', 8),
             ('cost_center_id', 'مرکز هزینه', 10), ('cost_center_title', 'عنوان مرکز', 34), ('cc_domain', 'حوزهٔ خدمت', 24), ('cc_master_status', 'وضعیت در master', 24), ('prior_cc_status', 'وضعیت قبلی', 22),
             ('mapping_method', 'روش', 30), ('lines', 'ردیف', 7), ('net_debit', 'خالص بدهکار', 16), ('confidence', 'اطمینان', 20), ('historical_source', 'منبع', 16),
             ('status', 'وضعیت', 18), ('evidence_in_taxi_gate_files', 'شاهد در Taxi-Gate', 30)], ig['activity_cc'])
    b.table('Account_CC_Observed', 'حساب قدیم ↔ مراکز هزینهٔ مشاهده‌شده', 'حساب‌های عمومی به چند مرکز می‌روند؛ مرکز از عنوان حساب قابل استخراج نیست',
            [('old_code', 'کد', 11), ('org', 'سازمان', 9), ('old_title', 'عنوان', 32), ('eligible_lines', 'ردیف واجد شرایط', 9), ('distinct_cost_centers', 'تعداد مرکز', 8),
             ('cc_distribution', 'توزیع', 60), ('derivable_from_account_alone', 'قابل‌اشتقاق از حساب؟', 30)], ig['account_cc'])
    recon_rows = []
    for k, v in rcn['proposal_buckets'].items():
        recon_rows.append(dict(view='پیشنهاد مستقل', bucket=k, lines=v[0], debit=v[1], credit=v[2], share=v[1] / tot_d if tot_d else 0))
    for k, v in rcn['colleague_verdict_buckets'].items():
        recon_rows.append(dict(view='حکم بهترین تطبیق همکار', bucket=k, lines=v[0], debit=v[1], credit=v[2], share=v[1] / tot_d if tot_d else 0))
    for k, v in rcn['per_org_fy'].items():
        recon_rows.append(dict(view='منبع به تفکیک سازمان/سال', bucket=k, lines=v[0], debit=v[1], credit=v[2], share=v[1] / tot_d if tot_d else 0))
    recon_rows.append(dict(view='کنترل', bucket='منبع (Sanad)', lines=rcn['source']['lines'], debit=rcn['source']['debit'], credit=rcn['source']['credit'], share=1))
    recon_rows.append(dict(view='کنترل', bucket='تبارشناسی', lines=rcn['lineage']['lines'], debit=rcn['lineage']['debit'], credit=rcn['lineage']['credit'], share=1))
    recon_rows.append(dict(view='کنترل', bucket='اسناد / اسناد با چند مقصد', lines=rcn['documents'], debit=rcn['shared_documents_multi_destination'], credit='', share=''))
    b.table('Historical_Lineage_Recon', 'آشتی مبالغ: ردیف اصلی → سند → کد قدیم → crosswalk → رویداد → مرکز', f'هر ردیف دقیقاً یک سطل؛ بدون تورم در ۱←N؛ {SOURCE_UNIT}',
            [('view', 'دیدگاه', 24), ('bucket', 'سطل', 34), ('lines', 'ردیف', 9), ('debit', 'بدهکار', 18), ('credit', 'بستانکار', 18), ('share', 'سهم بدهکار', 9, 'pct')], recon_rows)

    # line lineage (streamed)
    ws = b.wb.add_worksheet('Lineage_Lines')
    ws.right_to_left()
    ws.write(0, 0, 'تبارشناسی سطر به سطر (۱۱۱٬۶۰۰ ردیف دفتر تاکسیرانی و پایانه‌ها ۱۴۰۴–۱۴۰۵)', b.f_title)
    ws.write(1, 0, 'شرح اسناد صادر نشده (RESTRICTED)؛ رقم چهارم کد حساب‌های بانکی ماسک شده؛ کد بودجه در منبع نیست', b.f_note)
    with open(ig['lineage_file'], encoding='utf-8-sig') as fh:
        rd = csv.reader(fh)
        hdr = next(rd)
        for i, h in enumerate(hdr):
            ws.write(2, i, h, b.f_head)
            ws.write(3, i, h, b.f_key)
            ws.set_column(i, i, 14)
        rr = 4
        num_cols = {hdr.index('Debit'), hdr.index('Credit'), hdr.index('Source_Row'), hdr.index('Line_Ref')}
        for row in rd:
            for i, v in enumerate(row):
                if i in num_cols and v.lstrip('-').isdigit():
                    ws.write_number(rr, i, int(v))
                else:
                    ws.write_string(rr, i, v)
            rr += 1
    ws.freeze_panes(4, 0)
    ws.autofilter(3, 0, rr - 1, len(hdr) - 1)
    b.sheets['Lineage_Lines'] = rr - 4

    b.table('Prior_Artifacts', 'موجودی مصنوعات پروژهٔ قبلی (نام، کارکرد، وضعیت، فیلد اتصال، نوع بازرسی)', 'نام‌های ذکرشده در شرح کار که در مخزن نیستند صریحاً NOT FOUND شده‌اند',
            [('candidate', 'مصنوع', 34), ('path', 'مسیر', 60), ('found', 'یافت شد', 9), ('function', 'کارکرد', 36), ('status', 'وضعیت', 30), ('link_fields', 'فیلد اتصال', 30),
             ('inspected', 'نوع بازرسی', 30), ('sha256', 'SHA-256', 20)], ig['artefacts'])

    # Prior comparison (models + Q1–Q12 + per-account)
    pc = Counter(x['relation'] for x in mt['prior_cmp'])
    contra = [x for x in mt['prior_cmp'] if x['relation'] in ('PRIOR_CONTRADICTS', 'PRIOR_OVERLAPS', 'PRIOR_MAPPED_NOW_NONE')]
    supported = [x for x in aev if x['analytical_status'] == 'ANALYTICALLY_SUPPORTED']
    ev_sup = Counter(x['event_id'] for x in supported)
    QA_TEXT = [
        ('Q1', 'هر مدل چه مسئله‌ای را حل می‌کند؟',
         f"V1: کارگاه مهاجرت نمودار حساب — نمودار جدید شهرداری ({len(new_rows)} ردیف) و فهرست قدیم سازمان‌ها ({len(old)} حساب) کنار هم با فرمول‌های کمکی. V2: همان + پیشنهاد خودکار سه گزینهٔ متنی برای هر حساب قدیم. "
         f"مدل رویداد کد یکتا (v7.1): فرهنگ کاندید FE-01…FE-70 از شرح اسناد دفتر شهرداری. مدل مرکز هزینه: ۷۵ مرکز فعالیت‌محور (پیشنهادی). Taxi/Terminals v2.1: طبقه‌بندی سطر به سطر ۱۱۱٬۶۰۰ ردیف دفتر دو سازمان به رویداد و مرکز هزینه + crosswalk حساب L4/L5 + KPI + ماتریس تصمیم."),
        ('Q2', 'آیا دو فایل یک مسئلهٔ مهاجرت حساب را که قبلاً نبود حل می‌کنند؟',
         f"تا حدی. سهم واقعی: یک فهرست مرجع کامل‌تر از نمودار جدید ({len(new_codes)} کد یکتا؛ {not_observed} کد آن در دفتر ۱۴۰۴ شهرداری مشاهده نشده و در crosswalk v2.1 که بر ۱۵۶ ترکیب مشاهده‌شده بنا بود در دسترس نبود) و فهرست یکپارچهٔ ۱۵۷ حساب قدیم (۱۵۷/۱۵۷ در Hesab تأیید شد). "
         f"اما خود مهاجرت حل نشده: فقط {vc['VALID']} بهترین تطبیق معتبر است، {invalid} نامعتبر، و ستون‌های والد {r['parent_wrong'] + r['parent_not_found']} از ۴۷۱ نادرست‌اند."),
        ('Q3', 'تعریف رویداد مالی دارند یا فقط عنوان حساب؟', 'فقط عنوان حساب و سلسله‌مراتب. صفر شناسهٔ رویداد، صفر نوع تراکنش، صفر سند/مبلغ/تاریخ.'),
        ('Q4', 'آیا پشتیبان اشتقاق مرکز هزینهٔ فعالیت‌محورند؟', 'خیر. هیچ فیلد فعالیت، واحد، بودجه، پروژه یا سند ندارند (QA-CC-02 = NOT TESTABLE). در دفتر سازمان‌ها هم ' +
         f"{sum(1 for x in ig['account_cc'] if x['distinct_cost_centers'] > 1)} از {len(ig['account_cc'])} حساب هزینه‌ای به بیش از یک مرکز رفته‌اند؛ مرکز از فعالیت می‌آید نه از حساب."),
        ('Q5', 'کدام رویدادهای کانونی به حساب‌های معتبر پیوند می‌خورند؟',
         f"{len(supported)} رابطه با پشتوانهٔ تحلیلی (crosswalk قوی + پشتیبانی + سازگاری معنایی) روی {len(ev_sup)} رویداد: " + '، '.join(f'{k} ({v})' for k, v in ev_sup.most_common(15)) + '. همه تأییدنشده.'),
        ('Q6', 'کدام روابط با طبقه‌بندی‌های قبلی تناقض دارند؟',
         f"در برابر crosswalk v2.1: موافق {pc['PRIOR_AGREES']}، هم‌پوشان {pc['PRIOR_OVERLAPS']}، متناقض {pc['PRIOR_CONTRADICTS']}، قبلاً بی‌معادل/اکنون پیشنهاد {pc['PRIOR_NONE_NOW_PROPOSED']}، قبلاً نگاشت/اکنون بی‌معادل {pc['PRIOR_MAPPED_NOW_NONE']}، هر دو بی‌معادل {pc['BOTH_NO_EQUIVALENT']}. "
         'تطبیق‌های همکار با v2.1 بیشتر در جاهایی تناقض دارند که همکار طبقه را عوض کرده (مثلاً ۲۱۱-۱ → دارایی ۱۲۰۰۸؛ ۲۱۲-۹ → ۱۲۰۰۹).'),
        ('Q7', 'آیا رویداد یا مرکز هزینهٔ اختصاصی گمشده‌ای هست؟',
         'فایل‌ها شاهد جدیدی برای رویداد تازه نمی‌دهند؛ مفاهیم تاکسیرانی (کمک بودجه، سرویس مدارس، جریمه، بهای خدمات) قبلاً در TT-NE-01…34 آمده‌اند. '
         'مفهوم «بهره‌برداری جایگاه گاز» (۴۱۳-۱-۱۰، ۴۱۳-۸-۱۰، ۱۱۳-۱-۱ تاکسیرانی) در ۱۴۰۴–۱۴۰۵ گردش ندارد → فقط پیشنهاد مفهومی، نه رویداد. مرکز جدیدی فراتر از TTCC-P-01…03 توجیه نمی‌شود.'),
        ('Q8', 'کدام نگاشت‌های قبلی باید بازنگری شوند؟', '؛ '.join(f"{x['old_code']}: v2.1={x['prior_mun_moin']} → پیشنهاد {x['proposal']}" for x in contra[:25])),
        ('Q9', 'کدام نتایج قبلی معتبر می‌مانند؟',
         f"تعاریف FE-01…FE-70 (بدون بازتعریف)، شناسه‌های cc_master، CD-01…CD-08 و CD-EV-xx (باز)، اصل «L1–L3 قابل اثبات نیست»، شواهد عاملیت پایانه‌ها (بازمحاسبه شد)، {pc['PRIOR_AGREES']} ردیف crosswalk v2.1 که با پیشنهاد مستقل هم‌سو است."),
        ('Q10', 'چه داده‌ای برای تکمیل لازم است؟',
         'نمودار رسمی نسخه‌دار شهرداری با تعریف هر معین و تاریخ اعتبار؛ منشأ Sheet1؛ فرهنگ تفصیلی دو سازمان؛ دیکشنری کد فعالیت (CodeMarkaz) و نقشهٔ واحدهای پایانه؛ مبنای حقوقی/قراردادی پایانه‌ها (CD-01)؛ کد بودجهٔ تراکنش‌های سازمان؛ واحد پول (CD-02)؛ سیاست تلفیق درون‌گروهی؛ سیاست استهلاک/ذخایر در مهاجرت.'),
        ('Q11', 'کدام تصمیم‌ها با کارشناسان/آقای خداپرست/کمیته است؟', '؛ '.join(f"{x['id']} ({x['expert']})" for x in DECISIONS)),
        ('Q12', 'ارزش عینی این فایل‌ها برای معماری چیست؟',
         f"(۱) مرجع ۲۳۴ ردیفی نمودار جدید با طبقه/کل/معین؛ (۲) فهرست ۱۵۷ حساب قدیم با پرچم سازمان؛ (۳) ۵ جفت صریح سطح کل؛ (۴) آشکارسازی نقص‌های نمودار جدید (کد تکراری، دریافتنی زیر بدهی، کد ۶ رقمی)؛ "
         f"(۵) مولد کاندید برای تطبیق (recall@3 همکار {ctrl['colleague_recall3']}/{ctrl['comparable']} در برابر روش کنترل‌شده {ctrl['controlled_recall3']}/{ctrl['comparable']}). فاقد: نگاشت معتبر، رویداد، مرکز هزینه، مبلغ."),
    ]
    models = [
        dict(model='Taxi-Gate V1', purpose='کارگاه مهاجرت نمودار حساب', grain='کل/معین', keys='کد معین (عدد/متن)', events='ندارد', cc='ندارد', amounts='ندارد',
             status='کاری، بدون تأیید', reuse='مرجع نمودار جدید + فهرست قدیم'),
        dict(model='Taxi-Gate V2', purpose='پیشنهاد تطبیق متنی', grain='معین', keys='کد قدیم ↔ کد جدید', events='ندارد', cc='ندارد', amounts='ندارد',
             status='پیشنهاد متنی؛ ستون والد نادرست', reuse='فقط مولد کاندید'),
        dict(model='فرهنگ رویداد کد یکتا v7.1', purpose='رویداد مالی کانونی', grain='الگوی شرح سند', keys='FE-01…FE-70', events='۷۰ کاندید', cc='ماتریس شواهد',
             status='CANDIDATE', reuse='شناسه‌های رویداد در Account_Event_Crosswalk'),
        dict(model='مرکز هزینه (cc_master)', purpose='تجمیع هزینه فعالیت‌محور', grain='مرکز', keys='CC-xxx', events='—', cc='۷۵', amounts='—', status='PROPOSED',
             reuse='شناسه‌ها در Activity_CC_Crosswalk'),
        dict(model='Taxi/Terminals v2.1', purpose='طبقه‌بندی سطر به سطر دفتر دو سازمان', grain='سطر سند', keys='Source_Record_ID, HCode', events='FE + TT-NE', cc='CC + TTCC-P',
             amounts='۱۱۱٬۶۰۰ ردیف', status='PROPOSED/OBSERVED', reuse='تبارشناسی، رویداد، مرکز، CD-01'),
    ]
    ws = b.table('Prior_Project_Comparison', 'مقایسهٔ نظام‌مند با پروژهٔ قبلی و پاسخ پرسش‌های Q1–Q12', 'هر پاسخ به شیت/شناسهٔ مشخص ارجاع دارد',
                 [('k', 'کلید', 10), ('q', 'پرسش/مدل', 40), ('a', 'پاسخ/شرح', 150)],
                 [dict(k=m['model'], q=m['purpose'], a=f"دانه: {m['grain']}؛ کلید: {m['keys']}؛ رویداد: {m['events']}؛ مرکز: {m['cc']}؛ مبلغ: {m.get('amounts', '')}؛ وضعیت: {m['status']}؛ قابل استفاده برای: {m['reuse']}") for m in models]
                 + [dict(k=a, q=q, a=t) for a, q, t in QA_TEXT], wrap_cols=('a',))
    b.table('Prior_Crosswalk_Compare', 'مقایسهٔ حساب‌به‌حساب: crosswalk v2.1 / تطبیق همکار / پیشنهاد مستقل', 'رابطه با v2.1 در ستون relation',
            [('old_code', 'کد قدیم', 11), ('old_title', 'عنوان', 30), ('prior_mun_moin', 'v2.1 معین شهرداری', 20), ('prior_level', 'سطح v2.1', 9), ('colleague_best', 'همکار', 9),
             ('colleague_verdict', 'حکم همکار', 20), ('proposal', 'پیشنهاد مستقل', 24), ('relation', 'رابطه', 26)], mt['prior_cmp'])
    gov = [dict(id=x['id'], topic=x['topic'], prior=x['prior'], evidence=x['evidence'], existing=x['existing'], problem=x['problem'], alternatives=x['alternatives'],
                recommendation=x['recommendation'], impact=x['impact_text'], priority=x['priority'], expert=x['expert'], status='OPEN — منتظر تصمیم') for x in DECISIONS]
    b.table('Governance_Decisions', 'تصمیمات کارشناسی حل‌نشده', 'ستون‌های تصمیم کمیته در فایل تصمیمات خالی‌اند',
            [('id', 'شناسه', 9), ('topic', 'موضوع', 40), ('prior', 'پیوند قبلی', 14), ('evidence', 'شاهد', 60), ('existing', 'طبقه‌بندی موجود', 40), ('problem', 'مسئله', 50),
             ('alternatives', 'گزینه‌ها', 50), ('recommendation', 'توصیهٔ تحلیلی', 40), ('impact', 'اثر مالی بالقوه', 40), ('priority', 'اولویت', 12), ('expert', 'مسئول', 28),
             ('status', 'وضعیت', 16)], gov, wrap_cols=('evidence', 'problem', 'alternatives'))

    EXAMPLES = [
        ('شباهت بالا، نهاد متفاوت', '113-1-20-0'), ('شباهت ۱۰۰٪، طبقهٔ مخالف (دارایی→بدهی)', '113-6-0-0'), ('شباهت بالا، مشهود/نامشهود', '123-8-0-0'),
        ('شباهت بالا، آینهٔ طرف مقابل', '114-10-0-0'), ('شباهت بالا، دارایی↔بدهی', '211-1-0-0'), ('شباهت بالا، بدهی↔دارایی', '221-8-0-0'),
        ('شباهت بالا، هزینه↔دارایی', '613-19-0-0'), ('شباهت متوسط، ارزش افزوده فروش↔خرید', '212-9-0-0'), ('شباهت ۷۵٪، استهلاک↔کارمزد بانکی', '613-20-0-0'),
        ('درآمد↔هزینه', '413-1-20-0'), ('دارایی↔درآمد', '125-5-0-0'), ('درآمد↔دارایی', '413-1-10-0'), ('دارایی↔درآمد (۴۳٪)', '121-6-0-0'),
        ('استهلاک انباشته↔دارایی ثابت', '122-2-0-0'), ('استهلاک انباشته نرم‌افزار↔هزینهٔ تملک نرم‌افزار', '122-10-0-0'), ('سرمایهٔ سازمان↔سرمایه‌گذاری شهرداری', '311-4-0-0'),
        ('حقوق↔حقوق و امتیازات (همنامی)', '611-1-0-0'), ('شباهت پایین ولی هم‌ارز', '121-5-0-0'), ('گزینهٔ سوم صحیح', '121-7-0-0'), ('گزینهٔ سوم صحیح', '212-1-0-0'),
        ('گزینهٔ دوم صحیح', '121-2-0-0'), ('گزینهٔ دوم صحیح', '123-2-0-0'), ('گزینهٔ دوم صحیح', '315-1-0-0'), ('تفکیک: همکار فقط یک جزء', '113-5-0-0'),
        ('تفکیک: همکار فقط یک جزء', '212-6-0-0'), ('تفکیک چندماهیتی', '612-5-0-0'), ('برخورد معنایی بین سازمان‌ها', '114-2-0-0'), ('برخورد معنایی بین سازمان‌ها', '114-9-0-0'),
        ('تاکسیرانی: تجهیز GPS', '121-11-0-0'), ('تاکسیرانی: تعهدات بیمه تکمیلی رانندگان', '212-14-0-0'), ('تاکسیرانی: ایاب‌وذهاب دانش‌آموزان استثنایی', '212-11-0-0'),
        ('حساب انتظامی ضمانت↔یورو', '918-1-0-0'), ('معتبر', '612-4-0-0'), ('معتبر', '121-4-0-0'), ('معتبر', '216-1-0-0'), ('معتبر', '812-4-0-0'), ('معتبر', '111-3-0-0'),
        ('شخص در عنوان حساب', '212-1-20-0'), ('ملک مشخص در عنوان حساب', '120-2-0-0'), ('بانک‌ها↔بانک ارزی', '111-2-0-0')]
    ex_rows = []
    for i, (catg, code) in enumerate(EXAMPLES, 1):
        a = audit[code]
        ex_rows.append(dict(example_id=f'EX-{i:02d}', category=catg, old_code=code, old_title=a['old_title'], orgs=a['orgs'], usage=f"{a['lines']:,} ردیف؛ بدهکار {a['debit']:,}",
                            colleague=f"{a['best_code']} «{a['best_title']}» ({a['best_score']}٪)", parent=f"نمایش {a['parent_shown']} / واقعی {a['parent_true']}",
                            structural=a['structural'], verdict=VERDICT_FA[a['verdict']], proposal=a['proposal_targets'], why=a['reason']))
    b.table('Audited_Examples', f'{len(ex_rows)} نمونهٔ ممیزی‌شده (شامل موارد موفق و ناموفق)', 'موارد نام‌برده در شرح کار + نمونه‌های هدفمند از هر دستهٔ خطا',
            [('example_id', 'شناسه', 7), ('category', 'دسته', 30), ('old_code', 'کد', 11), ('old_title', 'عنوان قدیم', 30), ('orgs', 'سازمان', 14), ('usage', 'گردش', 30),
             ('colleague', 'پیشنهاد همکار', 40), ('parent', 'والد', 22), ('structural', 'ساختاری', 12), ('verdict', 'حکم', 24), ('proposal', 'پیشنهاد مستقل', 30),
             ('why', 'استدلال', 70)], ex_rows, wrap_cols=('why',))
    b.table('QA_Reproducibility', 'آزمون‌های بازتولیدپذیر (پیش از ساخت)', 'وضعیت‌ها محاسبه‌شده‌اند؛ آزمون‌های پس از ساخت در POSTBUILD_QA.md (خارج از این فایل)',
            [('test_id', 'شناسه', 11), ('area', 'حوزه', 14), ('description', 'شرح', 46), ('pass_condition', 'شرط', 34), ('actual', 'نتیجهٔ واقعی', 60), ('status', 'وضعیت', 12),
             ('method', 'روش', 40)], qa, wrap_cols=('actual',))
    prelim = [('۸ شیت در V1', len(fx['diff']['sheets_v1']), 'تأیید'), ('۱۱ شیت در V2', len(fx['diff']['sheets_v2']), 'تأیید'), ('۳ شیت تطبیق افزوده', len(d['added']), 'تأیید'),
              ('حدود ۷۳٬۴۶۱ ردیف داده', coa['sheet1_total_rows'], 'تأیید'), ('۲۳۴ ترکیب ۶ فیلدی', coa['sheet1_distinct'], 'تأیید'),
              ('۱۵۷ حساب قدیم', len(old), 'تأیید (۱۴۶ معین + ۱۱ تفصیلی)'), ('۲۳۴ حساب جدید', len(new_rows), f'تأیید؛ ولی {len(new_codes)} کد یکتا'),
              ('تعداد کمی نزدیک به یکسان', mt['reproduction']['exact_after_norm'], 'تأیید: ۷ یکسان + ۳ ≥۹۰٪ — از این ۱۰ مورد، ۸ معتبرند')]
    b.table('Executive_KPIs', 'شاخص‌های ممیزی‌شده', 'هر عدد از خروجی‌های s01–s05 محاسبه شده؛ ستون «شیت» منبع جزئیات است',
            [('kpi', 'شناسه', 6), ('name', 'شاخص', 44), ('value', 'مقدار', 14), ('basis', 'مبنا/تعریف', 70), ('sheet', 'شیت', 26)],
            [dict(kpi=k, name=n, value=v, basis=bb, sheet=s) for k, n, v, bb, s in KPIS] +
            [dict(kpi='P', name=f'یافتهٔ مقدماتی: {a}', value=v, basis=c, sheet='Source_Inventory') for a, v, c in prelim])
    b.close()
    sheets_written = dict(b.sheets)

    # ------------------------------------------------------------------ decision workbook
    db = Book(DEC_XLSX)
    db.table('راهنما', 'بستهٔ تصمیم کارشناسی تاکسیرانی و پایانه‌ها — نسخهٔ ۱', 'برای بازبینی کارشناسان مالی شهرداری و آقای خداپرست',
             [('k', 'مورد', 26), ('v', 'توضیح', 140)],
             [dict(k='وضعیت', v='هیچ تصمیمی اتخاذ نشده؛ ستون‌های «تصمیم کمیته»، «تاریخ تصمیم» و «مرجع تأیید» عمداً خالی‌اند.'),
              dict(k='منبع شواهد', v='Taxi_Gate_Deep_Audit_and_Integration_v1.xlsx (شیت‌های ذکرشده در ستون شاهد) و دفتر ۱۴۰۴–۱۴۰۵ سازمان‌ها (tt_v21.sqlite).'),
              dict(k='اثر مالی', v=f'گردش ۱۴۰۴–۱۴۰۵ حساب‌های درگیر ({SOURCE_UNIT})؛ نشانهٔ ابعاد ریسک است نه مبلغ تعدیل.'),
              dict(k='پیوند با تصمیمات قبلی', v='ستون «پیوند قبلی» به CD-xx در committee_decisions_v2.1.xlsx اشاره دارد؛ این بسته آن‌ها را جایگزین نمی‌کند.'),
              dict(k='اولویت', v='P1 مسدودکنندهٔ مهاجرت/ERP؛ P2 لازم پیش از فعال‌سازی؛ P3 پاک‌سازی.')])
    dec_rows = []
    for x in DECISIONS:
        dec_rows.append(OrderedDict([('Decision ID', x['id']), ('Topic', x['topic']), ('Source evidence', x['evidence']), ('Existing classification', x['existing']),
                                     ('Identified problem', x['problem']), ('Proposed alternatives', x['alternatives']), ('Analytical recommendation', x['recommendation']),
                                     ('Potential financial impact', x['impact_text']), ('Priority', x['priority']), ('Responsible expert', x['expert']),
                                     ('Committee decision', ''), ('Decision date', ''), ('Approval reference', ''), ('Final status', 'OPEN — منتظر تصمیم کمیته'),
                                     ('Prior decision link', x['prior'])]))
    fa = {'Decision ID': 'شناسهٔ تصمیم', 'Topic': 'موضوع', 'Source evidence': 'شاهد منبع', 'Existing classification': 'طبقه‌بندی موجود', 'Identified problem': 'مسئلهٔ شناسایی‌شده',
          'Proposed alternatives': 'گزینه‌های پیشنهادی', 'Analytical recommendation': 'توصیهٔ تحلیلی', 'Potential financial impact': 'اثر مالی بالقوه', 'Priority': 'اولویت',
          'Responsible expert': 'کارشناس مسئول', 'Committee decision': 'تصمیم کمیته', 'Decision date': 'تاریخ تصمیم', 'Approval reference': 'مرجع تأیید', 'Final status': 'وضعیت نهایی',
          'Prior decision link': 'پیوند قبلی'}
    widths = {'Topic': 40, 'Source evidence': 60, 'Existing classification': 40, 'Identified problem': 50, 'Proposed alternatives': 50, 'Analytical recommendation': 40,
              'Potential financial impact': 40, 'Responsible expert': 28, 'Committee decision': 30, 'Approval reference': 20}
    db.table('تصمیمات', 'فهرست تصمیمات', 'ستون‌های کمیته خالی', [(k, fa[k], widths.get(k, 14)) for k in dec_rows[0]], dec_rows,
             wrap_cols=('Source evidence', 'Identified problem', 'Proposed alternatives', 'Analytical recommendation', 'Existing classification'))
    ev_rows = []
    for x in DECISIONS:
        for spec in x['impact']:
            if spec == 'MISSING_LEVEL2':
                for m in coa['missing_level2']:
                    ev_rows.append(dict(decision=x['id'], org='', code=m['code'], title=' / '.join(m['titles'].values()), lines=m['lines'], debit=m['debit'], credit=m['credit'],
                                        colleague='خارج از فهرست همکار', proposal='—'))
                continue
            org, code = spec.split(':') if ':' in spec else ('', spec)
            a = audit.get(code)
            o = old.get(code)
            if not a:
                continue
            u = usage(spec)
            props = '؛ '.join(f"{e['org']}: {STATUS_FA[e['status']]} → {', '.join(str(t[0]) for t in e['targets'] if t[0]) or '—'}" for e in ENTRIES if e['code'] == code)
            ev_rows.append(dict(decision=x['id'], org=org or ', '.join(o['orgs']), code=code, title=a['old_title'], lines=u[0], debit=u[1], credit=u[2],
                                colleague=f"{a['best_code']} «{a['best_title']}» ({a['best_score']}٪) — {VERDICT_FA[a['verdict']]}", proposal=props))
    db.table('شواهد_حساب‌ها', 'حساب‌های درگیر در هر تصمیم با گردش ۱۴۰۴–۱۴۰۵', SOURCE_UNIT,
             [('decision', 'تصمیم', 9), ('org', 'سازمان', 14), ('code', 'کد', 11), ('title', 'عنوان', 34), ('lines', 'ردیف', 8), ('debit', 'بدهکار', 17), ('credit', 'بستانکار', 17),
              ('colleague', 'پیشنهاد همکار و حکم', 50), ('proposal', 'پیشنهاد مستقل', 50)], ev_rows)
    db.table('تصمیمات_قبلی_v2.1', 'تصمیمات باز پروژهٔ قبلی (برای پیوند)', 'committee_decisions_v2.1.xlsx — هیچ‌کدام اتخاذ نشده',
             [('id', 'شناسه', 12), ('org', 'سازمان', 12), ('subject', 'موضوع', 70), ('status', 'وضعیت', 30)], ig['prior_decisions'])
    db.close()

    # ------------------------------------------------------------------ Persian report
    write_report(fx, coa, mt, ig, qa, KPIS, DECISIONS, vc, invalid, org_rows, st, one_to_many, many_to_one, unmapped, new_codes, dup_codes, cat, aev, aev_sup, cc_rows, cc_none,
                 dom_codes_taxi, dom_codes_term, led, rcn, tot_d, not_observed, r, ctrl, QA_TEXT, EXAMPLES, audit, contra, src_hash)
    write_memo(ig, old)
    manifest = OrderedDict(generated=TODAY, sources={k: dict(path=p, sha256=src_hash[k]) for k, p in SOURCES.items()},
                           outputs={os.path.basename(p): sha256(p) for p in (AUDIT_XLSX, DEC_XLSX, REPORT_MD, MEMO_MD)},
                           audit_sheets=sheets_written, decision_rows=len(dec_rows), qa=dict(Counter(t['status'] for t in qa)))
    json.dump(manifest, open(os.path.join(OUT, 'MANIFEST.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print('built', sheets_written)


def write_memo(ig, old):
    """Expert decision memorandum on the accounting nature of the Terminals organisation (CD-01 / TG-D-01)."""
    flows = ig['cd01']
    bal = ig['cd01_balances']
    L = ['# یادداشت کارشناسی تصمیم — ماهیت حسابداری سازمان پایانه‌ها (CD-01 / TG-D-01) — نسخهٔ ۱', '',
         f'تاریخ: {TODAY} — وضعیت: **REQUIRES_AUTHORITY_DECISION**. این یادداشت هیچ رویکردی را تحمیل نمی‌کند و جایگزین یادداشت CD-01 نسخهٔ v2.1 نیست؛ آن را با بازمحاسبهٔ مستقل تکمیل می‌کند.', '',
         '## پرسش', '',
         'آیا سازمان پایانه‌ها در درآمد (اجاره غرفات، عوارض ۵٪ فروش بلیط، حق شارژ، تابلو تبلیغاتی) و هزینه‌های عملیاتی پایانه‌ها «عامل» شهرداری است یا «اصیل»؟', '',
         '## شواهد بازمحاسبه‌شده از دفتر ۱۴۰۴–۱۴۰۵ پایانه‌ها (tt_v21.sqlite)', '',
         md_table(['سال', 'حساب', 'نوع سند', 'ردیف', 'بدهکار', 'بستانکار', 'خالص'],
                  [(x['fy'], x['account'], x['doc_kind'], f"{x['lines']:,}", f"{x['debit']:,}", f"{x['credit']:,}", f"{x['net']:,}") for x in flows]), '',
         md_table(['سال', 'حساب', 'خالص افتتاحیه', 'خالص کل اسناد سال'], [(x['fy'], x['account'], f"{x['opening_net']:,}", f"{x['all_documents_net']:,}") for x in bal]), '',
         f"- زیرحساب‌های درآمدی ۴۱۳-۸ پایانه‌ها (اجاره غرفات، اجاره شرکت‌ها، حق شارژ، ۵٪ بلیط) در ۱۴۰۴–۱۴۰۵ فقط {sum(v[0] for k, v in old['413-8-0-0']['usage'].items() if k.startswith('Terminals'))} ردیف دارند.",
         '- در فایل‌های Taxi-Gate هیچ‌یک از این شواهد دیده نمی‌شود (فقط عنوان معین‌ها).', '',
         '## تفسیرهای جایگزین و پیامدها', '',
         md_table(['موضوع', 'الف) عامل شهرداری', 'ب) اصیل (واحد مستقل)', 'ج) ترکیبی'], [
             ('شناسایی درآمد', 'درآمد متعلق به شهرداری؛ در سازمان فقط بدهی به شهرداری (۲۱۰۰۱)', 'درآمد ناخالص در سازمان (۴۱۳۰۱ اجاره، ۴۱۲۰۴ خدمات)', 'اجاره غرفات اصیل؛ عوارض ۵٪ عاملیتی'),
             ('مسئولیت هزینه', 'هزینه به حساب شهرداری (طلب ۱۱۵۰۱)', 'هزینه در ۶۱۱xx سازمان', 'به تفکیک قرارداد/فعالیت'),
             ('دریافتنی/پرداختنی', 'مانده‌ها با شهرداری تهاتر؛ صفر در پایان دوره (سازگار با شواهد)', 'مطالبه از بهره‌برداران و بدهی به تأمین‌کنندگان', 'هر دو'),
             ('ناخالص/خالص', 'خالص (فقط کارمزد احتمالی سازمان)', 'ناخالص', 'ترکیبی'),
             ('KPI (TM-K01/K05/K14)', 'POLICY_PENDING می‌ماند؛ «مطالبه صادرشده» نه درآمد', 'قابل محاسبه به‌عنوان درآمد/هزینه', 'جزئی'),
             ('مرکز هزینه', 'CC-403 فقط برای هزینهٔ تحمیل‌شده؛ درآمد در بُعد منبع درآمد', 'CC-403 + مرکز درآمد', 'CC-403 + بُعد منبع درآمد'),
             ('نگاشت به نمودار جدید', '۱۱۳-۱-۱ → ۱۱۵۰۱ و ۲۱۱-۱-۱ → ۲۱۰۰۱ (پیشنهادی فعلی)', 'باز تعریف کامل نگاشت درآمد/هزینه', 'ترکیبی')]), '',
         '## آنچه برای تصمیم لازم است', '',
         '1. مبنای حقوقی/اساسنامه و قراردادهای واگذاری پایانه‌ها (مالکیت درآمد اجاره و عوارض ۵٪).',
         '2. رویهٔ تسویه با خزانهٔ شهرداری (اسناد اختتامیهٔ ۱۱۳-۱-۱/۲۱۱-۱-۱).',
         '3. تأیید آقای خداپرست و کارشناسان حسابداری شهرداری؛ ثبت تصمیم در Committee decision بستهٔ تصمیم.', '',
         '## وضعیت', '', 'تصمیم: ________  تاریخ: ________  مرجع تأیید: ________ (خالی — فقط کمیته)']
    open(MEMO_MD, 'w', encoding='utf8').write('\n'.join(L))


def md_table(header, rows):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    for r in rows:
        out.append('| ' + ' | '.join(str(x).replace('|', '／').replace('\n', ' ') for x in r) + ' |')
    return '\n'.join(out)


def write_report(fx, coa, mt, ig, qa, KPIS, DEC, vc, invalid, org_rows, st, one_to_many, many_to_one, unmapped, new_codes, dup_codes, cat, aev, aev_sup, cc_rows, cc_none,
                 dom_taxi, dom_term, led, rcn, tot_d, not_observed, r, ctrl, QA_TEXT, EXAMPLES, audit, contra, src_hash):
    old = {x['code']: x for x in coa['old_rows']}
    d = fx['diff']
    qa_c = Counter(t['status'] for t in qa)
    xt = defaultdict(Counter)
    for band, v, n in mt['xtab']:
        xt[band][v] += n
    buckets = rcn['proposal_buckets']
    strong = buckets.get('SINGLE_TARGET_STRONG', [0, 0, 0])
    split = [buckets.get('SPLIT_ALLOCATED', [0, 0, 0])[i] + buckets.get('SPLIT_ALLOCATED_REVIEW', [0, 0, 0])[i] for i in range(3)]
    nocand = [sum(buckets.get(k, [0, 0, 0])[i] for k in ('NO_SUITABLE_CANDIDATE', 'SPLIT_NO_EQUIVALENT', 'EXPERT_REVIEW_NO_TARGET', 'SPLIT_BASIS_NOT_IN_ACCOUNT_CODE',
                                                          'SPLIT_SUBACCOUNT_UNRESOLVED')) for i in range(3)]
    colb = rcn['colleague_verdict_buckets']
    col_valid = colb.get('VALID', [0, 0, 0])
    col_invalid = [sum(v[i] for k, v in colb.items() if k.startswith('INVALID')) for i in range(3)]
    sup_ev = Counter(x['event_id'] for x in aev if x['analytical_status'] == 'ANALYTICALLY_SUPPORTED')
    L = []
    A = L.append
    A('# گزارش ممیزی عمیق Taxi-Gate: مهاجرت نمودار حساب تاکسیرانی و پایانه‌ها و یکپارچه‌سازی با معماری کد یکتا (نسخهٔ ۱)')
    A('')
    A(f'تاریخ: {TODAY} — وضعیت همهٔ نگاشت‌ها و روابط: **پیشنهادی/مشاهده‌شده، تأییدنشده**. فایل‌های منبع تغییر نکرده‌اند (SHA-256 پیش و پس از اجرا برابر؛ QA-SRC-02).')
    A('')
    A(f"- V1: `Taxi-Gate_Version1.xlsx` — `{src_hash['V1']}`")
    A(f"- V2: `Taxi-Gate_version2.xlsx` — `{src_hash['V2']}`")
    A('- کارنامهٔ کامل شواهد: `Taxi_Gate_Deep_Audit_and_Integration_v1.xlsx`؛ بستهٔ تصمیم: `تصمیمات_کارشناسی_تاکسیرانی_و_پایانه‌ها_v1.xlsx`؛ اسکریپت‌ها: `scripts/taxi_gate_audit/`.')
    A('')
    A('## ۱. خلاصهٔ مدیریتی')
    A('')
    A(f"این دو فایل **کارگاه مهاجرت نمودار حساب** هستند، نه مدل رویداد مالی یا مرکز هزینه. V1 نمودار جدید شهرداری ({len(coa['new_rows'])} ردیف، {len(new_codes)} کد یکتا) و فهرست ۱۵۷ حساب قدیم سازمان‌های تاکسیرانی و پایانه‌ها را کنار هم می‌گذارد؛ "
      f"V2 فقط سه شیت ایستای «تطبیق متنی» افزوده و هیچ سلولی از ۸ شیت V1 را تغییر نداده است. روش تطبیق V2 به‌طور کامل بازتولید شد (۴۷۱/۴۷۱ امتیاز، ۱۵۶ رتبه + ۱ تساوی): شباهت Indel روی عنوان، بدون هیچ قید کد، طبقه، ماهیت یا سلسله‌مراتب.")
    A('')
    A(f"نتیجهٔ ممیزی مستقل ۱۵۷ «بهترین گزینه»: **{vc['VALID']} معتبر**، {vc['PARTIALLY_VALID']} معتبر فقط برای یک جزء، {vc['PLAUSIBLE_REVIEW'] + vc['RELATED_NOT_EQUIVALENT']} مبهم/مرتبط، و **{invalid} نامعتبر** "
      f"({vc['INVALID_STRUCTURAL']} ناسازگاری ماهیت/طبقه، {vc['INVALID_SEMANTIC']} معنای متفاوت، {vc['INVALID_ENTITY']} نهاد متفاوت، {vc['INVALID_PERSPECTIVE']} حساب آینهٔ طرف مقابل). "
      f"ستون‌های «گروه/کل جدید» در V2 برای {r['parent_wrong']} جفت نادرست و برای {r['parent_not_found']} جفت «پیدا نشد» است؛ علت ریشه‌ای در شیت moen اثبات شد (۴۷۱/۴۷۱).")
    A('')
    A(f"با اتصال به دفتر واقعی ۱۴۰۴–۱۴۰۵ دو سازمان (۱۱۱٬۶۰۰ ردیف، پروژهٔ قبلی) معلوم شد که تطبیق‌های معتبر همکار فقط {col_valid[1] / tot_d:.1%} گردش بدهکار را پوشش می‌دهند و تطبیق‌های نامعتبر {col_invalid[1] / tot_d:.1%} را. "
      f"crosswalk بازارزیابی‌شده {len(org_rows)} ردیف سازمان‌محور دارد: {one_to_many} ردیف ۱←N، {many_to_one} کد جدید N→۱، و {unmapped} حساب قدیم بدون مقصد مهاجرت (عمدتاً استهلاک انباشته، ذخایر، حقوق مالکانه و بهای تمام‌شده که نمودار جدید معادلی برایشان ندارد).")
    A('')
    A(f"شواهد اختصاصی تاکسیرانی در فایل‌های همکار فقط {len(dom_taxi)} حساب است ({', '.join(dom_taxi)}) و شاهد مستقیم پایانه‌ای **صفر**؛ شواهد پایانه‌ای (اجاره غرفات، ۵٪ بلیط، حق شارژ، واحدهای پایانه) فقط در زیرحساب‌ها و ابعاد دفتر سازمان‌ها وجود دارد ({led['DIRECT_TERMINAL']} زیرحساب).")
    A('')
    A('**پاسخ مستقیم:** این دو فایل بنیان قابل‌دفاعی برای استخراج رویداد مالی و مرکز هزینهٔ فعالیت‌محور نیستند؛ اساساً یک **crosswalk ناقص مهاجرت نمودار حساب** هستند که ارزششان در «مرجع نمودار جدید» و «فهرست یکپارچهٔ حساب‌های قدیم» است، نه در تطبیق‌ها.')
    A('')
    A('## ۲. هدف و دامنهٔ ظاهری کار همکار')
    A('')
    A('- هدف ظاهری: تطبیق معین‌های نمودار «سازمان‌های وابسته» (کدهای ۱۱۱-۰-۰-۰ … که تاکسیرانی و پایانه‌ها به کار می‌برند) با معین‌های نمودار جدید شهرداری (کدهای ۵ رقمی ۶۱۱۰۱ …).')
    pres = Counter(tuple(x['orgs']) for x in coa['old_rows'])
    varied = [x for x in coa['old_rows'] if x['org_title_variants'] > 1]
    from_term = sum(1 for x in varied if x['title_source_org'] == ['Terminals'])
    kf = sum(1 for x in coa['old_kol'] if x['flag_matches_inference'])
    A(f"- شاهد: هر {len(coa['old_rows'])} کد قدیم در Hesab تاکسیرانی/پایانه‌ها ۱۴۰۴–۱۴۰۵ وجود دارند ({pres[('Taxi', 'Terminals')]} در هر دو، {pres[('Taxi',)]} فقط تاکسیرانی، "
      f"{pres[('Terminals',)]} فقط پایانه‌ها) و عنوان هر کد با Hesab یکی است (QA-COA-11). ستون kol!F با «1=پایانه‌ها، 2=تاکسیرانی» در {kf}/{len(coa['old_kol'])} کل سازگار است [استنتاج].")
    A(f"- در {from_term} از {len(varied)} کدی که عنوان دو سازمان فرق دارد، فهرست همکار **عنوان پایانه‌ها** را برداشته است؛ در {cat['OLD_CODE_MEANING_COLLISION_BETWEEN_ORGS']} کد این تفاوت معنایی است (CoA_Integrity_QA).")
    A('- فراداده: Creator = «Amir khodaparast» (قالب ۲۰۱۵)، LastModifiedBy = «ACER»؛ این فقط فرادادهٔ فایل است و انتساب نویسندگی نیست.')
    A('')
    A('## ۳. ساختار و محتوای دقیق دو فایل')
    A('')
    rows = []
    for x in fx['inventory']:
        rows.append((x['workbook'], x['sheet'], x['used_range'], f"{x['physical_rows']:,}", f"{x['nonempty_rows']:,}", x['columns'], x['formula_cells'], x['role'][:70]))
    A(md_table(['نسخه', 'شیت', 'محدوده', 'ردیف فیزیکی', 'غیرتهی', 'ستون', 'فرمول', 'نقش'], rows))
    A('')
    A(f"- همهٔ شیت‌ها قابل‌مشاهده‌اند؛ پیوند خارجی، جدول اکسل، اعتبارسنجی داده و قالب شرطی وجود ندارد؛ نام‌های تعریف‌شده فقط `_xlnm._FilterDatabase` هستند.")
    A(f"- Sheet1: {coa['sheet1_total_rows']:,} ردیف داده با فقط ۶ ستون (طبقه، کل، معین) و **{coa['sheet1_distinct']} ترکیب یکتا** — همان ۲۳۴ ردیف Sheet2. هیچ شمارهٔ سند، مبلغ، تاریخ یا منطقه ندارد؛ پس تکرارها معنای تراکنشی ندارند (QA-POP-03). "
      f"منشأ آن در دفتر ۱۴۰۴ شهرداری یافت نشد: هیچ منطقه یا ترکیب ≤۳ منطقه هم‌شمار نیست و {coa['sheet1_provenance']['sheet1_moin_codes_absent_from_journal']} از {coa['sheet1_provenance']['sheet1_moin_codes']} کد معین آن در دفتر ۱۴۰۴ دیده نمی‌شود (QA-POP-04).")
    A('- شیت‌های فرمول‌دار: Sheet3 (`UNIQUE`)، kol (سه `UNIQUE` + یک `VLOOKUP`)، moen (۲٬۳۰۵ سلول فرمول: `UNIQUE`، `XLOOKUP`، `TEXTJOIN(FILTER)`). مقادیر ذخیره‌شدهٔ همهٔ آن‌ها با محاسبهٔ مستقل برابرند (QA-FML-01) — یعنی خطاها در **طراحی** فرمول‌اند نه در محاسبه.')
    A('')
    A('## ۴. تفاوت دو نسخه')
    A('')
    A(md_table(['مورد', 'نتیجه'], [
        ('شیت افزوده', '، '.join(d['added'])), ('شیت حذف/تغییرنام', 'هیچ'),
        ('تفاوت مقدار/فرمول/سبک در ۸ شیت مشترک', f"{sum(v['value_diffs'] for v in d['common_sheets'].values())} / {sum(v['formula_or_constant_diffs'] for v in d['common_sheets'].values())} / {sum(v['style_diffs'] for v in d['common_sheets'].values())}"),
        ('تفاوت قالب‌بندی', 'فقط عرض ستون K شیت moen (۳۲٫۱ → ۱۲٫۳)'),
        ('ظرف OOXML', f"حذف `xl/metadata.xml` و {sum(v['dynamic_array_flags'][0] - v['dynamic_array_flags'][1] for v in d['common_sheets'].values())} پرچم آرایهٔ پویا (`cm=\"1\"`)؛ "
                      'فرمول‌های UNIQUE/FILTER در V2 آرایهٔ ثابت قدیمی شده‌اند؛ حذف تنظیمات چاپ؛ بازشماری sheetId'),
        ('بهبود دادهٔ پایه؟', 'خیر'), ('خطای جدید؟', f"بله: ستون‌های والد نادرست ({r['parent_wrong']}+{r['parent_not_found']} از ۴۷۱) و پیشنهادهای ناسازگار ساختاری")]))
    A('')
    A('## ۵. یافته‌های کیفیت داده')
    A('')
    A(md_table(['دسته', 'تعداد'], sorted(Counter(a['category'] for a in coa['anomalies']).items(), key=lambda kv: -kv[1])))
    A('')
    A(f"- عناوین جدید با «ي/ك» عربی: {coa['char_stats']['new_titles_arabic_ye_kaf']} از {coa['char_stats']['new_titles_total']}؛ فاصلهٔ انتهایی: {coa['char_stats']['new_titles_trailing_space']}؛ کدهای قدیم همه متن با ۲۰+ فاصلهٔ انتهایی و کدهای جدید عدد — ستون A شیت moen دو نوع داده دارد.")
    A(f"- فهرست قدیم همکار {len(coa['missing_level2'])} معین سطح ۲ دارای حساب را ندارد، از جمله ۱۱۵-۴ «موجودی کالاهای اموالی» (۱۲۱ ردیف) و ۱۱۱-۱ «صندوق» (QA-COA-10).")
    A('')
    A('## ۶. مشکلات سلسله‌مراتب کد حساب')
    A('')
    keyan = [a for a in coa['anomalies'] if a['category'] in ('ONE_CODE_MULTIPLE_TITLES', 'ONE_CODE_MULTIPLE_PARENTS', 'DUPLICATE_ROW', 'MISSING_CODE', 'INVALID_CODE_LENGTH',
                                                             'CODE_PREFIX_PARENT_CONFLICT', 'SEMANTIC_CLASS_CONFLICT', 'OLD_CODE_MEANING_COLLISION_BETWEEN_ORGS')]
    A(md_table(['شناسه', 'دسته', 'کد', 'عنوان', 'سابقهٔ متعارض', 'پیامد', 'شدت', 'تصمیم کارشناس'],
               [(a['anomaly_id'], a['category'], a['code'], str(a['title'])[:60], str(a['conflicting_record'])[:110], a['consequence'][:110], a['severity'], a['expert_decision_required']) for a in keyan]))
    A('')
    A('- طراحی فرمول kol!C:D: `UNIQUE` جداگانه روی کد و عنوان؛ چون ۱۱۲ و ۱۱۵ عنوان یکسان و ۱۶۰ دو عنوان دارند، ۷ جفت (C6:D12) ناهم‌ترازند (مثلاً ۱۲۵ کنار «موجودی ها») — QA-FML-02.')
    shv = next(v for k, v in fx['recompute']['V1'].items() if k.startswith('moen rows where'))
    A(f"- طراحی شیت moen: ستون‌های D:G/I/J برای مقدار ستون H (=UNIQUE(A)) محاسبه می‌شوند ولی کنار A/B همان ردیف نمایش داده می‌شوند؛ از ردیف {shv['first_row']} (پس از نخستین کد تکراری) "
      f"{shv['rows']} از {shv['of_total']} ردیف به حساب دیگری اشاره می‌کنند — QA-FML-03. این همان منشأ ستون‌های والد غلط V2 است.")
    xs = [a for a in coa['anomalies'] if a['category'] == 'CROSS_SOURCE_PARENT_CONFLICT']
    A(f"- {len(xs)} کد معین در Sheet2 والدی متفاوت با کدگذاری مشاهده‌شده در دفتر ۱۴۰۴ شهرداری دارند (" + '، '.join(f"{a['code']} ({a['parent']}↔{a['conflicting_record'].split('کل ')[1].split(' (')[0]})" for a in xs)
      + ') — نسخهٔ نمودار باید تعیین شود (TG-D-19).')
    A('- کدهای عددی کل قدیم و جدید با معنای متفاوت هم‌پوشانی دارند: ' + '، '.join(f"{x['code']} (قدیم «{x['old_title']}» / جدید «{str(x['new_title']).strip()}»)" for x in coa['kol_collisions'][:10]) + '.')
    A('')
    A('## ۷. ارزیابی روش تطبیق اصلی')
    A('')
    A('- ورودی: عنوان ۱۵۷ حساب قدیم و عنوان ۲۳۴ ردیف کد ۱ شیت moen (شامل دو ردیف ۰ و ردیف بدون کد).')
    A('- یکسان‌سازی: ي→ی، ك→ک، ة→ه، أ/إ→ا، ئ→ی، ؤ→و، نیم‌فاصله→فاصله، ارقام فارسی→لاتین، حذف علائم، فشرده‌سازی فاصله.')
    A('- امتیاز: شباهت Indel = ۲×LCS/(|a|+|b|)×۱۰۰ (معادل rapidfuzz `fuzz.ratio`) — ۴۷۱/۴۷۱ بازتولید شد.')
    A('- رتبه‌بندی: بیشینهٔ امتیاز روی همهٔ ۲۳۴ ردیف؛ تساوی به ترتیب شیت — ۱۵۶ بازتولید دقیق + ۱ تفاوت فقط در ترتیب تساوی.')
    A('- برچسب‌ها: ۱۰۰ = «تطبیق دقیق نام»، ۹۰–۱۰۰ «بسیار مشابه»، ۸۰–۹۰ «مشابه»، ۷۰–۸۰ «شباهت متوسط»، <۷۰ «تطبیق نامشخص». شیت «خلاصه تطبیق» (۷/۳/۱۸/۲۲/۱۰۷) کاملاً بازتولید شد.')
    A('- **هیچ** قید کد، طبقه، کل، ماهیت، سلسله‌مراتب یا سازمان اعمال نشده است؛ ' + f"{sum(1 for a in mt['audit'] if a['structural'] == 'INCOMPATIBLE')} بهترین گزینه از نظر ساختاری ناسازگارند (QA-MAT-06).")
    A('')
    A('جدول شباهت متنی در برابر اعتبار حسابداری (بهترین گزینه):')
    A('')
    verds = ['VALID', 'PARTIALLY_VALID', 'PLAUSIBLE_REVIEW', 'RELATED_NOT_EQUIVALENT', 'INVALID_STRUCTURAL', 'INVALID_SEMANTIC', 'INVALID_ENTITY', 'INVALID_PERSPECTIVE']
    A(md_table(['باند شباهت'] + [VERDICT_FA[v] for v in verds], [(bnd,) + tuple(xt[bnd][v] for v in verds) for bnd in ('100', '90–99.9', '80–89.9', '70–79.9', '<70')]))
    A('')
    A(f"روش کنترل‌شدهٔ پیشنهادی (A: کل‌های مجاز بر اساس ماهیت → B: آزمون سازگاری ساختاری → C: شباهت با فرهنگ هم‌معنا و جریمهٔ تفاوت عدد نهاد) هرگز گزینهٔ ناسازگار نمی‌دهد (QA-MAT-09) و در {ctrl['comparable']} حساب قابل‌مقایسه "
      f"top-1 = {ctrl['controlled_top1']} و recall@3 = {ctrl['controlled_recall3']} دارد، در برابر {ctrl['colleague_top1']} و {ctrl['colleague_recall3']} روش همکار. این هم فقط **مولد کاندید** است و جایگزین قضاوت کارشناسی نیست.")
    A('')
    A('## ۸. نگاشت‌های معتبر و نامعتبر اثبات‌شده')
    A('')
    exrows = []
    for catg, code in EXAMPLES:
        a = audit[code]
        exrows.append((code, a['old_title'][:40], f"{a['best_code']} «{a['best_title'][:35]}» ({a['best_score']}٪)", VERDICT_FA[a['verdict']], catg, a['proposal_targets'][:50]))
    A(md_table(['کد قدیم', 'عنوان قدیم', 'پیشنهاد همکار', 'حکم', 'دسته', 'پیشنهاد مستقل'], exrows))
    A('')
    A('موارد نام‌برده در شرح کار همه تأیید شدند: ابزارآلات→عوارض آلایندگی (دارایی→درآمد)؛ استهلاک انباشته نرم‌افزار→۶۱۷۰۱ (کاهندهٔ دارایی→هزینهٔ تملک)؛ حق بهره‌برداری خطوط→حق بیمه سهم شهرداری (درآمد→هزینه)؛ '
      'حق عضویت اتحادیه تاکسیرانی→مال‌الاجاره (دارایی→درآمد)؛ شهرداری منطقه ۱→شهرداری منطقه ۶ (نهاد دیگر؛ ۹۳٫۳٪)؛ هزینه‌های استهلاک→هزینه‌های بانکی (۷۵٪).')
    A('')
    cv = Counter(c['verdict'] for c in mt['candidates'])
    A(f"ممیزی همهٔ ۴۷۱ گزینه (بهترین + دوم + سوم): هم‌سو با پیشنهاد مستقل {cv['AGREES_WITH_PROPOSAL']}، مرتبط غیرهم‌ارز {cv['RELATED_NOT_EQUIVALENT']}، "
      f"هم‌طبقه ولی غیرهم‌ارز {cv['COMPATIBLE_CLASS_NOT_EQUIVALENT']}، ناسازگار ساختاری {cv['INVALID_STRUCTURAL']} (Candidate_Audit). در چند حساب (۱۲۱-۲، ۱۲۱-۷، ۱۲۳-۲، ۲۱۲-۱، ۳۱۵-۱، ۶۱۱-۱) "
      'گزینهٔ صحیح در رتبهٔ دوم یا سوم بوده ولی روش، بدون قید ماهیت، گزینهٔ نادرست را اول گذاشته است.')
    A('')
    A('## ۹. یافته‌های اختصاصی تاکسیرانی')
    A('')
    taxi_list = '، '.join(f"{c} «{old[c]['title_masked']}»" for c in dom_taxi if c in old)
    A(f'- در فایل‌های همکار فقط این حساب‌ها مستقیماً تاکسیرانی‌اند: {taxi_list}.')
    A('- در دفتر تاکسیرانی ۴۱۳-۱ «درآمد حاصل از فعالیت عملیاتی» ۲۳ زیرحساب تاکسیرانی دارد (صدور/تمدید پروانه، حق عضویت، نقل‌وانتقال ۴٪، سهم ۱٪ سرویس مدارس، تاکسی‌های اینترنتی …) که در فایل همکار دیده نمی‌شوند؛ نمودار جدید معین معادل ندارد و نزدیک‌ترین ۴۱۲۰۴ «درآمد سایر تأسیسات شهرداری - سازمان‌ها» است (TG-D-14).')
    A('- ۴۱۳-۸-۱ «کمک از محل اعتبارات شهرداری» (۱٫۰۸e12) درون‌گروهی است و به هیچ درآمد شهرداری نباید برود (TT-NE-02).')
    A('- ۲۱۳-۲-۵ «سامانه سفیر مهر» (۲٫۷۴e12) وجوه عبوری سرویس مدارس است؛ فقط سهم سازمان درآمد است — عنوان زیرحساب ۴۱۳-۱-۱۶ «۱٪ سهم سرویس مدارس» است در حالی که v2.1 (CD-EV-05) از ۲٪ سخن می‌گوید؛ نرخ باید تأیید شود.')
    A('- جایگاه گاز (۴۱۳-۱-۱۰، ۴۱۳-۸-۱۰) در ۱۴۰۴–۱۴۰۵ گردش ندارد → شاهدی برای رویداد/مرکز جدید نیست.')
    A('')
    A('## ۱۰. یافته‌های اختصاصی پایانه‌ها')
    A('')
    A('- شاهد مستقیم پایانه‌ای در فایل‌های همکار: **صفر**. حساب‌های پایانه‌ها در فهرست همکار عناوین عمومی دارند.')
    A(f"- در دفتر پایانه‌ها {led['DIRECT_TERMINAL']} زیرحساب پایانه‌ای (اجاره غرفات، ۵٪ فروش بلیط، حق شارژ، تابلو تبلیغاتی، درآمد پایانه‌های مشخص) و ۸ واحد سازمانی (کاوه، صفه، زاینده‌رود، جی، صمدیه …) وجود دارد.")
    A('- بازمحاسبهٔ CD-01:')
    A('')
    A(md_table(['سال', 'حساب', 'خالص افتتاحیه', 'خالص کل اسناد'], [(x['fy'], x['account'], f"{x['opening_net']:,}", f"{x['all_documents_net']:,}") for x in ig['cd01_balances']]))
    A('')
    A('الگو (مانده صفر در ابتدا و انتهای هر دوره؛ هزینه در بدهکار ۱۱۳-۱-۱؛ درآمد در بستانکار ۲۱۱-۱-۱؛ زیرحساب‌های درآمدی ۴۱۳-۸ پایانه‌ها تقریباً بی‌گردش) با **عاملیت** سازگار است ولی آن را اثبات نمی‌کند. '
      'تفسیرهای جایگزین و پیامدها در یادداشت کارشناسی `یادداشت_کارشناسی_CD-01_پایانه‌ها_v1.md` و TG-D-01؛ هیچ رویکردی تحمیل نشده است.')
    A('')
    A('تفکیک نهاد از فعالیت — آنچه فایل‌های همکار اجازهٔ شناسایی آن را می‌دهند:')
    A('')
    A(md_table(['مفهوم', 'در فایل‌های همکار', 'در دفتر سازمان‌ها (پروژهٔ قبلی)'], [
        ('شهرداری به‌عنوان نهاد گزارشگر', 'بله — نمودار جدید از دید شهرداری (حساب‌های رابط ۷xx، «منطقه ۶»، «مطالبات از سازمان‌های وابسته»)', '—'),
        ('سازمان تاکسیرانی/پایانه‌ها به‌عنوان نهاد وابسته', 'ضمنی — فقط از کدهای ۱۱۱-۰-۰-۰… و پرچم kol!F؛ هیچ ستون «سازمان»', 'بله (org)'),
        ('بهره‌بردار پایانه / پیمانکار / شرکت حمل‌ونقل', 'خیر — فقط نوع حساب (۲۱۰۱۴ بدهی به پیمانکاران، ۲۲۵۰x سپرده‌ها)', 'جزئی (تفصیلی‌ها، CodePerson)'),
        ('واحد عملیاتی / پایانهٔ مشخص', 'خیر', 'بله برای پایانه‌ها (CodeVahed: کاوه، صفه، زاینده‌رود، جی، صمدیه)'),
        ('تسویهٔ درون‌سازمانی', 'فقط حساب‌های رابط ۷xx شهرداری؛ بدون شناسهٔ طرف', 'بله (۱۱۳-۱-x، ۲۱۱-۱-x، ۱۱۳-۱-۱۲ تاکسیرانی = طلب از پایانه‌ها)')]))
    A('')
    A('نقل‌وانتقال‌های میان‌سازمانی (کمک بودجه، تسهیلات از شهرداری، مطالبهٔ درآمد برای شهرداری) هزینهٔ مستقیم خدمت نیستند و در crosswalk به‌صورت «درون‌گروهی/بدون معادل» نگه داشته شده‌اند (TG-D-13، TG-D-14).')
    A('')
    A('## ۱۱. رابطه با کار قبلی رویداد مالی شهرداری')
    A('')
    A(f"- {len(aev)} رابطهٔ حساب↔رویداد از طبقه‌بندی موقت v2.1 مشاهده شد؛ {aev_sup} رابطه پشتوانهٔ تحلیلی دارند (crosswalk قوی + پشتیبانی + سازگاری معنایی) و {len(aev) - aev_sup} نیازمند بازبینی‌اند؛ **هیچ‌کدام تأیید نشده**.")
    A('- رویدادهای دارای پشتوانه: ' + '، '.join(f'{k} ({v})' for k, v in sup_ev.most_common(20)) + '.')
    A('- تمایز حفظ شد: حساب (مثلاً ۶۱۲-۴ «اجاره‌بها و کرایه» → ۶۱۱۱۱) ≠ رویداد (FE-35 «پرداخت اجاره املاک») ≠ نمونهٔ رویداد (سند مشخص در Lineage_Lines).')
    A('- نمونه‌های دارای پشتوانه (تأییدنشده): ۶۱۲-۶ «سوخت، آب، برق» ↔ FE-33؛ ۶۱۲-۷ «مواد و لوازم مصرف‌شدنی» ↔ FE-22؛ ۲۱۲-۱ «بستانکاران کارکنان» ↔ FE-44؛ ۶۱۱-۲ «مزایا و فوق‌العاده‌ها» ↔ FE-45/46/51؛ '
      '۱۲۱-۷ «اثاثیه اداری» ↔ FE-23؛ ۱۱۳-۶ «اسناد در جریان وصول» (پایانه‌ها) ↔ TT-NE-13. رابطهٔ ۶۱۲-۴ «اجاره‌بها و کرایه» در طبقه‌بندی موقت عمدتاً FE-32 (کرایهٔ ماشین‌آلات/حمل) است نه FE-35 — شاهدی بر اینکه عنوان حساب رویداد را تعیین نمی‌کند.')
    A('- رویداد جدیدی پیشنهاد نشد؛ معیارهای پنج‌گانهٔ شرح کار برای هیچ مفهوم تازه‌ای برآورده نشد.')
    A('')
    A('## ۱۲. رابطه با مراکز هزینهٔ فعالیت‌محور')
    A('')
    A('- فایل‌های همکار هیچ فیلد فعالیت، واحد، بودجه، پروژه یا سند ندارند → اشتقاق مرکز هزینه از آن‌ها **INSUFFICIENT SOURCE EVIDENCE** است (QA-CC-02).')
    A(f"- از دفتر سازمان‌ها: {len(cc_rows)} رابطهٔ فعالیت↔مرکز با شاهد ({sum(x['lines'] for x in cc_rows):,} ردیف) و {len(cc_none)} ترکیب بدون مرکز ({sum(x['lines'] for x in cc_none):,} ردیف). "
      f"{sum(1 for x in ig['account_cc'] if x['distinct_cost_centers'] > 1)} حساب هزینه‌ای به چند مرکز رفته‌اند — مرکز از حساب قابل استخراج نیست.")
    A('- مراکز مرتبط موجود: CC-406 (ناوگان تاکسیرانی)، CC-403 (پایانه‌ها)، CC-405 (پارکینگ)؛ پیشنهادهای قبلی TTCC-P-01…03 بدون تغییر حفظ شدند. درآمدها مرکز هزینه نمی‌گیرند؛ بُعد «منبع درآمد» (CD-03) توصیه می‌شود.')
    A('')
    A('## ۱۳. معماری یکپارچه‌سازی پیشنهادی')
    A('')
    A('```')
    A('کد حساب منبع (سازمان، کد قدیم، تفصیلی)')
    A('  → Crosswalk مهاجرت تأییدشده (۱→۱ / ۱→N با مبنای زیرحساب / N→۱ / بدون مقصد)')
    A('  → نمودار جدید نسخه‌دار (کد + تاریخ اعتبار)')
    A('  ↔ رویداد مالی کانونی (FE / TT-NE) — رابطهٔ چند به چند، مجاز فقط پس از تأیید')
    A('  ↔ فعالیت/خدمت (CodeMarkaz، واحد پایانه) → مرکز هزینه (CC-xxx) | منبع درآمد (برای درآمد)')
    A('ابعاد: قرارداد، پروژه، شخص/طرف حساب (ADR-0024)، واحد سازمانی، سند حسابداری، مستند پشتیبان')
    A('```')
    A('')
    A('اثر crosswalk تأییدشده بر گردش‌کار پیش‌حسابداری (فقط پس از تصمیم مرجع؛ ADR-0001، ADR-0014، ADR-0019):')
    A('')
    A('- **پیشنهاد رویداد:** رابطهٔ حساب↔رویداد فقط فهرست رویدادهای محتمل را رتبه‌بندی می‌کند (مثلاً ۶۱۲-۶ → FE-33)؛ انتخاب با کاربر است.')
    A('- **فیلتر حساب:** پس از انتخاب رویداد فقط معین‌های جدیدِ مرتبط با آن رویداد نمایش داده می‌شوند؛ حساب‌های بدون مقصد مهاجرت هرگز پیشنهاد نمی‌شوند.')
    A('- **انتخاب مرکز هزینه:** از فعالیت/واحد (CodeMarkaz، CodeVahed) پیشنهاد می‌شود، نه از حساب؛ برای درآمد بُعد «منبع درآمد».')
    A('- **تبدیل حساب قدیم:** فقط از ردیف‌های تأییدشدهٔ Account_Crosswalk_Proposed با کلید (سازمان، کد، تفصیلی)؛ ردیف‌های ۱←N بدون مبنای زیرحساب به صف استثنا می‌روند.')
    A('- **فیلدهای لازم:** فقط وقتی کاردینالیتی «Approved» تعیین شد (اکنون همه Needs Decision) الزامی می‌شوند؛ تا آن زمان ابعاد «شناخته/ارائه‌شده» نمایش داده می‌شوند.')
    A('- **استثنا:** برخورد معنایی کد بین دو سازمان، کد نمودار با دو والد، و حساب‌های درون‌گروهی به صف بازبینی هدایت می‌شوند.')
    A('- **اعتبارسنجی:** آشتی دقیق ریالی (ADR-0026) بین سطر منبع و سطر پیش‌حسابداری؛ هر سطر منبع دقیقاً یک مقصد.')
    A('')
    A('## ۱۴. داده‌های موجود در برابر داده‌های لازم')
    A('')
    A(md_table(['داده', 'وضعیت'], [
        ('نمودار جدید (۲۳۴ ردیف)', 'موجود در فایل همکار — با نقص'), ('حساب‌های قدیم دو سازمان', 'موجود (فایل همکار + Hesab)'), ('مبالغ، سند، تاریخ', 'فقط در دفتر سازمان‌ها (پروژهٔ قبلی)'),
        ('کد بودجه', 'موجود نیست'), ('واحد پول', 'تصریح نشده (CD-02)'), ('نمودار رسمی نسخه‌دار + تعریف معین‌ها', 'موجود نیست'), ('Master_Data_ERP / Doc_No_Mapping مستقل', 'یافت نشد'),
        ('منشأ Sheet1', 'نامعلوم'), ('دیکشنری فعالیت/واحد', 'جزئی (v2.1)'), ('مبنای حقوقی پایانه‌ها', 'موجود نیست')]))
    A('')
    A('## ۱۵. ریسک‌های پیاده‌سازی ERP')
    A('')
    A(f"- مهاجرت با V2: {col_invalid[1] / tot_d:.1%} گردش بدهکار ۱۴۰۴–۱۴۰۵ در حساب نادرست (اغلب با طبقهٔ مخالف) می‌نشست.")
    A('- کلید مشترک کد بین دو سازمان: ۶ کد دو معنا دارند؛ ۱۱۴-۲ تاکسیرانی با ۱٫۰e12 بدهکار به بدهی نگاشت می‌شد.')
    A('- نبود حساب‌های تعهدی در نمودار جدید: استهلاک انباشته، ذخایر و حقوق مالکانه بدون سیاست، یا حذف یا جابه‌جا می‌شوند.')
    A('- کد تکراری/دو والد (۴۱۰۱۰، ۱۱۵۱۱، ۸۱۰۱۰، ۱۴۰۰۴): XLOOKUP و هر بارگذاری خودکار اولین ردیف را برمی‌دارد.')
    A('- تبدیل فرمول‌های پویا به آرایهٔ ثابت در V2: افزودن ردیف به نمودار باعث از قلم افتادن آن در فهرست‌های UNIQUE می‌شود.')
    A('')
    A('## ۱۶. موارد نیازمند تأیید کارشناسی')
    A('')
    A(md_table(['شناسه', 'موضوع', 'اولویت', 'مسئول', 'پیوند قبلی', 'اثر مالی'], [(x['id'], x['topic'][:70], x['priority'], x['expert'], x['prior'], x['impact_text'][:90]) for x in DEC]))
    A('')
    A('## ۱۷. اقدامات اصلاحی اولویت‌بندی‌شده')
    A('')
    A('1. **اصلاح فوری داده:** کنار گذاشتن ستون‌های والد V2 و «خلاصه تطبیق» به‌عنوان مرجع (TG-D-16)؛ پاک‌سازی ۴۱۰۱۰/۱۴۰۰۴/۱۲۰۰۵/۱۱۵۱۱/۸۱۰۱۰، ۳ ردیف بدون کد و ۱۱۵۰۱۴ (TG-D-18)؛ رفع طراحی kol!C:D و moen.')
    A('2. **اعتبارسنجی مهاجرت حساب:** کلید (سازمان، کد)؛ تصمیم ۲۳۰۰۴–۶؛ سیاست استهلاک/ذخایر/حقوق مالکانه؛ تأیید مبنای تفکیک زیرحساب‌ها؛ افزودن ۲۰ معین جاافتاده (TG-D-02…13، TG-D-22).')
    A('3. **یکپارچه‌سازی رویداد:** بررسی ' + f'{aev_sup} رابطهٔ دارای پشتوانه' + '؛ کاردینالیتی‌ها Needs Decision بمانند تا تصمیم (TG-D-20).')
    A('4. **یکپارچه‌سازی مرکز هزینه:** crosswalk کد فعالیت (CD-07)، سیاست حقوق (CD-08)، بُعد منبع درآمد (CD-03) (TG-D-21).')
    A('5. **تصمیمات کمیته:** CD-01/TG-D-01 (پایانه‌ها)، TG-D-13 (تلفیق)، TG-D-14 (درآمد).')
    A('6. **آمادگی ERP:** نمودار نسخه‌دار با تاریخ اعتبار؛ هیچ قاعدهٔ الزامی پیش از تصمیم؛ بارگذاری فقط از Account_Crosswalk_Proposed پس از تأیید ردیف‌به‌ردیف.')
    A('')
    A('## ۱۸. ارزیابی نهایی تناسب برای استفادهٔ عملیاتی')
    A('')
    A(f"فایل‌ها برای استفادهٔ عملیاتی **مناسب نیستند**. V1 به‌عنوان مرجع نمودار جدید (پس از پاک‌سازی) و فهرست حساب‌های قدیم ارزشمند است؛ V2 فقط سند تاریخی و مولد کاندید است. "
      f"هیچ رویداد مالی، فعالیت یا مرکز هزینه‌ای از این فایل‌ها قابل استخراج نیست؛ پیوند به رویداد و مرکز فقط از طریق دفتر سازمان‌ها و طبقه‌بندی موقت v2.1 برقرار شد و همچنان نیازمند تصمیم است.")
    A('')
    A('## پیوست الف — ثبت یافته‌های اصلی')
    A('')
    F = [
        ('F-01', 'V2 فقط سه شیت ایستا افزوده؛ ۸ شیت مشترک بدون تغییر', 'Version_Diff؛ QA-DIF-01/02', 'دادهٔ پایه بهبود نیافته', 'اطلاعاتی', 'V2 را به‌عنوان مرجع داده استفاده نکنید', 'خیر'),
        ('F-02', f"ستون‌های والد V2 برای {r['parent_wrong'] + r['parent_not_found']} از ۴۷۱ جفت غلط/پیدانشده", 'Candidate_Audit؛ QA-MAT-04/05', 'قضاوت کاربر از طبقهٔ پیشنهاد را گمراه می‌کند', 'بالا', 'حذف ستون‌ها', 'خیر'),
        ('F-03', f'{invalid} از ۱۵۷ بهترین تطبیق نامعتبر', 'Original_Mapping_Audit', f'{col_invalid[1] / tot_d:.1%} گردش بدهکار', 'بحرانی', 'جایگزینی با crosswalk پیشنهادی', 'بله'),
        ('F-04', 'روش فقط شباهت Indel بدون قید', 'QA-MAT-01/02/06', 'شباهت ≠ هم‌ارزی', 'بالا', 'روش کنترل‌شده A→B→C', 'خیر'),
        ('F-05', '۶ کد قدیم با دو معنای سازمانی؛ عنوان پایانه‌ها برداشته شده', 'CoA_Integrity_QA (COA-0xx)', '۱۱۴-۲ تاکسیرانی ۱٫۰e12', 'بالا', 'کلید (سازمان، کد)', 'بله (TG-D-04)'),
        ('F-06', 'نمودار جدید: دریافتنی‌ها زیر کل بدهی ۲۳۰', 'COA SEMANTIC_CLASS_CONFLICT', 'تطبیق ۱۰۰٪ به طبقهٔ مخالف', 'بالا', 'اصلاح نمودار', 'بله (TG-D-02)'),
        ('F-07', 'کد تکراری/دو والد/بدون کد در نمودار جدید', 'COA-001…022', 'نگاشت مبهم', 'بالا', 'پاک‌سازی', 'بله (TG-D-18)'),
        ('F-08', 'طراحی معیوب فرمول kol!C:D و moen', 'QA-FML-02/03', 'منشأ خطای V2', 'متوسط', 'بازطراحی', 'خیر'),
        ('F-09', 'نبود حساب‌های تعهدی (استهلاک انباشته، ذخایر، سرمایه) در نمودار جدید', 'Account_Crosswalk_Proposed (NO_SUITABLE_CANDIDATE)', f'{unmapped} حساب بدون مقصد', 'بالا', 'تصمیم سیاستی', 'بله (TG-D-03/13)'),
        ('F-10', 'حساب‌های مختلط نیازمند تفکیک زیرحساب', 'Account_Split_Evidence', f'{split[1] / tot_d:.1%} گردش بدهکار', 'بالا', 'تأیید مبنای تفکیک', 'بله (TG-D-06)'),
        ('F-11', 'شاهد پایانه‌ای در فایل‌های همکار صفر', 'Taxi_Terminal_Evidence؛ QA-DOM-01', 'مدل پایانه از این فایل‌ها ممکن نیست', 'بالا', 'استفاده از دفتر/واحد', 'بله (TG-D-01)'),
        ('F-12', 'مرکز هزینه از فایل‌ها قابل اشتقاق نیست', 'QA-CC-02؛ Account_CC_Observed', 'ABC نیازمند فعالیت', 'بالا', 'crosswalk فعالیت', 'بله (TG-D-21)'),
        ('F-13', 'منشأ Sheet1 نامعلوم', 'QA-POP-03/04', 'فراوانی بی‌معنا', 'متوسط', 'معرفی منشأ', 'خیر (TG-D-17)'),
        ('F-14', 'آشتی کامل مبالغ بدون تورم', 'Historical_Lineage_Recon؛ QA-REC-01…04', 'پایهٔ قابل‌حسابرسی', 'اطلاعاتی', '—', 'خیر'),
    ]
    A(md_table(['شناسه', 'یافته', 'شاهد/ارجاع', 'اهمیت', 'شدت', 'اقدام', 'تأیید کارشناس'], F))
    A('')
    A('## پیوست ب — شاخص‌ها')
    A('')
    A(md_table(['شناسه', 'شاخص', 'مقدار', 'مبنا'], [(k, n, (f'{v:.1%}' if isinstance(v, float) else fmt_num(v)), bb) for k, n, v, bb, s in KPIS]))
    A('')
    A(f"QA: {len(qa)} آزمون — PASS {qa_c['PASS']}، REVIEW {qa_c['REVIEW']}، FAIL {qa_c['FAIL']}، NOT TESTABLE {qa_c['NOT TESTABLE']} (شیت QA_Reproducibility؛ آزمون‌های پس از ساخت در POSTBUILD_QA.md).")
    A('')
    A('## پیوست ج — پاسخ پرسش‌های Q1–Q12')
    A('')
    for k, q, t in QA_TEXT:
        A(f'**{k}. {q}** {t}')
        A('')
    open(REPORT_MD, 'w', encoding='utf8').write('\n'.join(L))


if __name__ == '__main__':
    main()
