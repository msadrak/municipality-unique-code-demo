"""Classify every journal row of the v3 workbook; emit per-row decisions for v4 writing."""
import pickle, json, re, openpyxl
from collections import Counter, defaultdict
from activity_rules import classify, norm

V3 = 'C:/Users/sadra/Desktop/دفتر_روزنامه_1404_مراکز_هزینه_فعالیت_محور_v3.xlsx'
d = pickle.load(open('zz_v3.pkl', 'rb')); ROWS = d['rows']
LIN = pickle.load(open('zz_lineage.pkl', 'rb'))
V3ADD = set(json.load(open('zz_v3add.json')))
REVIEW_V4 = {r[0]: r for r in json.load(open('cc_review_v4.json', encoding='utf-8'))}

def s(v): return '' if v is None else str(v).strip()
def blank(v): return v is None or s(v) in ('', 'NULL')

# ---- native hierarchy (authoritative reference sheet) ----
wb = openpyxl.load_workbook(V3, read_only=True, data_only=True)
ws = wb['بودجه 1404 + مراکز هزینه']
raw_forms = defaultdict(Counter); title_idx = defaultdict(set)
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[5] is None or s(r[5]) == 'کد سطح 1': continue
    l2 = s(str(r[7]).replace('\xa0', ' '))
    raw_forms[l2][(s(r[5]), str(r[6]), l2, str(r[8]))] += 1
    title_idx[norm(r[1])].add(l2)
wb.close()
NATIVE = {k: v.most_common(1)[0][0] for k, v in raw_forms.items()}   # L2 -> (AF, AG, AH, AI) raw reference form
NATIVE_L2 = set(NATIVE)

CC_MASTER = json.load(open('cc_master.json', encoding='utf-8'))
# Re-evaluated crosswalk (activity-definition based). relation: EQUIVALENT / PARTIAL / MANY_TO_ONE / MISSING
XW = {
 'CC-101': ('07 -01', 'EQUIVALENT', ''), 'CC-102': ('07 -02', 'EQUIVALENT', ''),
 'CC-103': ('07 -03', 'MANY_TO_ONE', 'CC-103 و CC-104 هر دو به 07-03 می‌رسند'), 'CC-104': ('07 -03', 'MANY_TO_ONE', 'CC-103 و CC-104 هر دو به 07-03 می‌رسند'),
 'CC-105': ('07 -04', 'EQUIVALENT', 'فقط کنترل جانوران موذی/ناقل؛ نگهداری پرندگان باغ پرندگان مشمول نیست (06-06)'),
 'CC-106': (None, 'MISSING', 'نگاشت قبلی به 10-03 (رفع خطر) نادرست بود؛ سرویس بهداشتی عمومی سطح۲ بومی ندارد'),
 'CC-201': ('06 -01', 'BROADER', 'CC-201 علاوه بر 06-01، کاشت (06-03) و ساماندهی پارک (06-05) را نیز پوشش می‌دهد'),
 'CC-202': ('06 -02', 'EQUIVALENT', ''), 'CC-203': ('06 -04', 'EQUIVALENT', ''),
 'CC-204': ('06 -05', 'PARTIAL', 'تفرجگاه‌های ویژه؛ باغ پرندگان/باغ‌وحش در 06-06؛ احداث تأسیسات گردشگری مشمول نیست'),
 'CC-301': ('08 -01', 'BROADER', 'شبکه آبیاری 08-01 و تأمین/مخازن آب 08-02'),
 'CC-302': ('08 -03', 'EQUIVALENT', ''), 'CC-303': ('08 -04', 'MANY_TO_ONE', 'مادی‌ها و آب‌های سطحی هر دو 08-04'), 'CC-304': ('08 -04', 'MANY_TO_ONE', 'مادی‌ها و آب‌های سطحی هر دو 08-04'),
 'CC-401': ('12 -03', 'BROADER', 'سامانه‌های هوشمند 12-03 و دوربین ثبت تخلف 12-02'),
 'CC-402': ('12 -05', 'BROADER', 'علائم 12-05، ایمنی ترافیک 12-01، موانع 10-04'),
 'CC-403': ('13 -03', 'EQUIVALENT', ''), 'CC-404': ('11 -05', 'EQUIVALENT', ''), 'CC-405': ('13 -01', 'EQUIVALENT', ''),
 'CC-406': ('11 -08', 'EQUIVALENT', ''), 'CC-407': ('13 -02', 'EQUIVALENT', ''),
 'CC-408': ('12 -01', 'PARTIAL', 'حمل‌ونقل پاک؛ پایانه‌های دوچرخه در 13-01؛ سطح۲ دقیق بومی ندارد'),
 'CC-501': ('11 -02', 'BROADER', 'خیابان 11-02 و اصلاح هندسی/تقاطع 11-04'),
 'CC-502': ('11 -01', 'BROADER', 'آسفالت 11-01 و نگهداری معابر 11-06'),
 'CC-503': ('11 -03', 'EQUIVALENT', ''), 'CC-504': ('11 -07', 'EQUIVALENT', ''),
 'CC-505': ('11 -04', 'PARTIAL', 'پل سواره‌رو/تقاطع غیرهمسطح؛ بومی فقط اصلاح هندسی و تقاطع دارد'),
 'CC-506': ('11 -06', 'PARTIAL', ''),
 'CC-601': ('09 -01', 'BROADER', 'شبکه روشنایی 09-01 و نورپردازی 09-02'),
 'CC-602': ('09 -03', 'EQUIVALENT', ''), 'CC-603': ('09 -06', 'EQUIVALENT', ''), 'CC-604': ('09 -04', 'EQUIVALENT', ''), 'CC-605': ('09 -05', 'EQUIVALENT', ''),
 'CC-701': ('15 -01', 'EQUIVALENT', ''), 'CC-702': (None, 'MISSING', ''), 'CC-703': (None, 'MISSING', 'شکاف واقعی: تخلفات شهری در بومی به 02-03 (تدارکات) رفته است'),
 'CC-704': ('15 -03', 'EQUIVALENT', ''), 'CC-705': ('15 -02', 'EQUIVALENT', ''),
 'CC-801': (None, 'MISSING', 'نگاشت قبلی به 10-03 نادرست بود؛ عملیات اطفا سطح۲ بومی ندارد (10-02 فقط ایستگاه)'),
 'CC-802': ('10 -02', 'EQUIVALENT', ''), 'CC-803': ('10 -01', 'EQUIVALENT', ''),
 'CC-804': ('10 -03', 'EQUIVALENT', 'نگاشت قبلی به 10-04 (نرده) نادرست بود؛ معادل دقیق 10-03 است'),
 'CC-901': ('03 -05', 'BROADER', 'فرهنگسرا 03-05 و مرکز همایش 03-02'), 'CC-902': ('03 -02', 'BROADER', 'رویداد 03-02 و برنامه فرهنگی 03-01'),
 'CC-903': ('03 -04', 'EQUIVALENT', ''), 'CC-904': ('03 -03', 'PARTIAL', '03-03 و 03-06'),
 'CC-905': ('16 -01', 'BROADER', 'گردشگری 16-01 و میراث 16-02'), 'CC-906': ('03 -07', 'EQUIVALENT', ''),
 'CC-907': ('17 -02', 'BROADER', 'احداث آرامستان 17-01 و خدمات 17-02'),
 'CC-1001': ('15 -04', 'EQUIVALENT', ''), 'CC-1002': (None, 'MISSING', ''), 'CC-1003': ('02 -02', 'EQUIVALENT', ''),
 'CC-1101': ('05 -01', 'EQUIVALENT', ''), 'CC-1102': ('05 -03', 'BROADER', '05-02 و 05-03'), 'CC-1103': ('05 -05', 'EQUIVALENT', ''),
 'CC-1201': (None, 'MISSING', 'کارکرد درآمدی؛ در سطرهای هزینه انتظار نمی‌رود'), 'CC-1202': ('02 -01', 'EQUIVALENT', ''), 'CC-1203': ('02 -07', 'EQUIVALENT', ''),
 'CC-1204': (None, 'MISSING', 'تأمین مالی؛ بازپرداخت اصل تسهیلات هزینه فعالیت نیست'), 'CC-1205': (None, 'MISSING', 'تسویه دیون سنواتی زمان‌بندی پرداخت است نه فعالیت'),
 'CC-1301': ('01 -01', 'BROADER', '01-01 و مأموریت 01-04'), 'CC-1302': ('01 -02', 'EQUIVALENT', ''), 'CC-1303': ('01 -03', 'EQUIVALENT', ''),
 'CC-1305': (None, 'MISSING', ''),
 'CC-1401': ('14 -01', 'BROADER', 'تعریف CC-1401 «تعمیرات اساسی» را هم دارد؛ نگهداری جاری (14-02) معادل پیشنهادی ندارد'),
 'CC-1402': (None, 'MISSING', 'شکاف واقعی: نگهداری وسایط نقلیه در بومی به 14-02 (ساختمان) رفته است'),
 'CC-1403': ('02 -03', 'PARTIAL', '02-03 در بومی سبد عمومی ۴۵۵ ردیف است'), 'CC-1404': ('14 -02', 'PARTIAL', 'خدمات/نظافت ساختمان ≠ نگهداری ساختمان'),
 'CC-1405': (None, 'MISSING', 'شکاف واقعی: حفاظت فیزیکی و نیروی انتظامی'),
 'CC-1501': ('04 -02', 'EQUIVALENT', ''), 'CC-1502': ('04 -01', 'EQUIVALENT', ''), 'CC-1503': ('03 -02', 'PARTIAL', ''),
 'CC-1601': (None, 'MISSING', ''), 'CC-1602': (None, 'MISSING', ''), 'CC-109': (None, 'MISSING', 'سازمان وابسته؛ شاهد خدماتی دارد، شاهد سطر هزینه ندارد'),
}
for k, (nat, rel, note) in XW.items():
    assert nat is None or nat in NATIVE_L2, (k, nat)

WRITABLE = {'VERIFIED_NATIVE', 'PROPOSED_ACTIVITY'}
KIND_LABEL = {'op': 'عملیاتی مستقیم', 'cap': 'پروژه سرمایه‌ای/احداث', 'sup': 'پشتیبانی داخلی', 'per': 'پرسنلی/منابع مشترک (ماهیت حساب)',
              'CCONLY': 'فعالیت بدون معادل بومی', 'AMB': 'مبهم', 'AMBREF': 'مبهم', 'INS': 'نهاده عمومی', 'NA': 'تأمین مالی'}

def pick(r):
    cp = classify(r[11])
    if cp and cp['kind'] != 'GENERIC':
        cp['field'] = 'P'; return cp
    if cp is None and norm(r[11]):
        return None          # specific item title without activity signature: never borrow the program heading
    co = classify(r[10])
    if co and co['kind'] != 'GENERIC':
        co['field'] = 'O'; return co
    return None

def decide(r):
    w = s(r[16])
    if w.startswith('32') and len(w) == 11:
        return dict(status='NOT_APPLICABLE', kind='NA', act='بازپرداخت اصل و سود تسهیلات/اوراق (کد بودجه 32)', cc='CC-1204', native=None,
                    method='قاعده ماهیت تأمین مالی', evidence=f'کد بودجه {w}؛ معین {s(r[9])}', note='تأمین مالی؛ انتساب مرکز هزینه فعالیت در سطح سطر کاربرد ندارد (CC-1204 فقط ساختاری)')
    c = pick(r)
    if not c:
        note = 'شرح تفضیلی/جزء فعالیت مشخصی ندارد'
        if s(r[2]) == '31':
            note += '؛ واحد سازمانی «مدیریت طرح ساماندهی ناژوان» فقط شاهد مسئولیت سازمانی است (کاندید CC-204)، نه شاهد فعالیت'
        return dict(status='INSUFFICIENT_EVIDENCE', kind='INS', act='', cc=None, native=None, method='بدون امضای فعالیت', evidence=f'P={s(r[11])} | O={s(r[10])}', note=note)
    ev = f"{'جزء' if c['field'] == 'P' else 'تفضیلی'}: «{c['text']}»"
    base = dict(kind=c['kind'], act=c['act'], cc=c['cc'], rule=c['rule'])
    ref = title_idx.get(c['text'], set())
    refs = '|'.join(sorted(ref))
    if c['kind'] == 'NA':
        return dict(base, status='NOT_APPLICABLE', native=None, method=f"قاعده {c['rule']}", evidence=ev, note='تأمین مالی/سرمایه‌گذاری')
    if c['kind'] == 'INS':
        return dict(base, status='INSUFFICIENT_EVIDENCE', native=None, method=f"قاعده {c['rule']}", evidence=ev, note='فقط ماهیت نهاده/حساب؛ فعالیت شهری قابل استناد نیست')
    if c['kind'] == 'AMB':
        return dict(base, status='AMBIGUOUS', native=None, method=f"قاعده {c['rule']}", evidence=ev, note=c['act'])
    if c['kind'] == 'AMBREF':
        if len(ref) == 1 and next(iter(ref)) in c['compat']:
            nat = next(iter(ref))
            return dict(base, status='VERIFIED_NATIVE', native=nat, method=f"امضای فعالیت {c['rule']} + تطابق عنوان ردیف بودجه مرجع", evidence=ev + f'؛ ردیف مرجع بودجه → {nat}', note='ابهام با سطح۲ مرجع رفع شد')
        return dict(base, status='AMBIGUOUS', native=None, method=f"قاعده {c['rule']}", evidence=ev + (f'؛ مرجع بودجه: {refs}' if refs else ''), note=c['act'])
    if c['kind'] == 'CCONLY':
        return dict(base, status='PROPOSED_CC_ONLY', native=None, method=f"امضای فعالیت {c['rule']}", evidence=ev + (f'؛ مرجع بودجه بومی: {refs}' if refs else ''),
                    note=f"{c['cc']} معادل بومی ندارد؛ کد بومی جعل نشد" + (f'؛ مرجع بودجه آن را به {refs} برده که با فعالیت سازگار نیست' if refs else ''))
    if len(ref) == 1 and next(iter(ref)) in c['compat']:
        nat = next(iter(ref))
        return dict(base, status='VERIFIED_NATIVE', native=nat, method=f"امضای فعالیت {c['rule']} + تطابق مستقل عنوان ردیف بودجه مرجع", evidence=ev + f'؛ ردیف مرجع بودجه با همین عنوان → {nat}', note='دو شاهد مستقل (فعالیت و مرجع بومی) هم‌جهت‌اند')
    note = 'انتساب پیشنهادی بر پایه تعریف فعالیت؛ نیازمند تأیید کارشناس'
    if refs:
        note += f'؛ مرجع بودجه بومی برای این عنوان {refs} را می‌دهد که با فعالیت سازگار نیست'
    if c['cc'] is None:
        note += '؛ taxonomy پیشنهادی مرکز معادل «نگهداری جاری ساختمان» ندارد (CC-1401 فقط احداث/تعمیرات اساسی)'
    return dict(base, status='PROPOSED_ACTIVITY', native=c['native'], method=f"امضای فعالیت {c['rule']}", evidence=ev, note=note)

def lineage_cat(r):
    o = LIN[r[0]]
    src = not blank(o[1]) or not blank(o[3])
    v1 = not any(blank(x) for x in o[4:8])
    if src: return 'SOURCE_NAMES'
    if v1: return 'V1_NATIVE_REF'
    return 'V3_ADDED'

DEC = {}
stats = Counter()
CLOSE = re.compile(r'پایان دوره|افتتاحیه|افتتاحيه|بستن حساب|اختتامیه|اختتاميه')
for r in ROWS:
    rn = r[0]; cls = s(r[17]); v3 = tuple(s(x) for x in r[23:27]); has = any(v3)
    if cls == '6':
        dec = decide(r)
        if not has:
            dec['population'] = 'EXPENSE_BLANK_IN_V3'
            dec['action'] = 'WRITE' if dec['status'] in WRITABLE else 'REVIEW_ONLY'
        else:
            cat = lineage_cat(r)
            dec['population'] = {'SOURCE_NAMES': 'EXPENSE_SOURCE_ORIGINAL_NAMES', 'V1_NATIVE_REF': 'EXPENSE_V1_NATIVE_REFERENCE', 'V3_ADDED': 'EXPENSE_V3_ADDED'}[cat]
            old_l2 = v3[2]
            if cat == 'V3_ADDED':
                if dec['status'] in WRITABLE and dec['native'] == old_l2:
                    dec['action'] = 'UNCHANGED_CONFIRMED'
                elif dec['status'] in WRITABLE:
                    dec['action'] = 'CORRECT'
                elif dec['status'] == 'INSUFFICIENT_EVIDENCE' and old_l2 in ('02 -03', '02 -01'):
                    dec['action'] = 'RETAIN_FLAG'; dec['note'] += '؛ مقدار v3 (سبد پشتیبانی عمومی) حفظ شد ولی شاهد فعالیت نیست'
                else:
                    dec['action'] = 'CLEAR'
            else:
                conflict = False
                if dec['status'] in WRITABLE and old_l2 not in dec.get('compat_set', ()) and dec['native'] != old_l2:
                    rule_compat = next((x[5] for x in __import__('activity_rules').R if x[0] == dec.get('rule')), ())
                    conflict = old_l2 not in rule_compat
                elif dec['status'] == 'PROPOSED_CC_ONLY':
                    conflict = True
                dec['action'] = 'FLAG_EXISTING' if conflict else 'UNCHANGED'
            dec['old'] = v3
    elif cls == '4' and has:
        dec = dict(status='EXISTING_ASSIGNMENT_REVIEW', kind='', act='', cc=None, native=None, population='REVENUE_WITH_SOURCE_EXPENSE_CC',
                   action='FLAG_EXISTING', method='قاعده ماهیت حساب درآمدی', evidence=f'طبقه 4 (درآمد)؛ کل {s(r[18])}',
                   note='سطر درآمدی نام مرکز هزینه‌ای منبع دارد؛ مقدار منبع حفظ و فقط علامت‌گذاری شد', old=v3)
    else:
        dec = dict(status='NOT_APPLICABLE', population=f'NON_EXPENSE_CLASS_{cls}', action='NONE', native=None, cc=None, kind='')
    DEC[rn] = dec

# ---- document-level (event) relations ----
doc_rows = defaultdict(list)
for r in ROWS:
    doc_rows[(s(r[2]), s(r[4]))].append(r)
evt = 0
for key, rs in doc_rows.items():
    if len(rs) > 300 or any(CLOSE.search(s(x[14]) + ' ' + s(x[15])) for x in rs):
        continue
    acts = set()
    for x in rs:
        dx = DEC[x[0]]
        if s(x[17]) != '6': continue
        if dx['status'] in WRITABLE and dx.get('action') in ('WRITE', 'CORRECT', 'UNCHANGED_CONFIRMED'):
            acts.add(('N', dx['native'], dx.get('cc')))
        elif dx['status'] == 'PROPOSED_CC_ONLY':
            acts.add(('C', None, dx['cc']))
        elif dx.get('action') in ('UNCHANGED', 'FLAG_EXISTING') and any(dx.get('old', ())):
            acts.add(('N', dx['old'][2], None))
    keys = set((a[1] or a[2]) for a in acts)
    if len(keys) != 1:
        continue
    a = next(iter(acts)); k = next(iter(keys))
    for x in rs:
        dx = DEC[x[0]]; cls = s(x[17])
        if (cls in ('1', '2') and dx['status'] == 'NOT_APPLICABLE') or (cls == '6' and dx['status'] == 'INSUFFICIENT_EVIDENCE' and dx.get('action') == 'REVIEW_ONLY'):
            dx.update(status='EVENT_LEVEL_ONLY', action='REVIEW_ONLY', native=a[1] if a[0] == 'N' else None, cc=a[2],
                      method='رابطه سند (منطقه+شماره سند) با یک فعالیت یکتا', evidence=f'سند {key[1]} منطقه {key[0]}؛ تنها فعالیت سطرهای هزینه سند: {k}',
                      note='مرکز هزینه برای رویداد/سند پشتیبانی می‌شود نه لزوماً برای این سطر؛ در AF:AI نوشته نشد', kind='EVENT', act='', population=dx['population'])
            evt += 1

for rn, dx in DEC.items():
    stats[(dx['population'], dx['status'], dx.get('action'))] += 1
pickle.dump({'DEC': DEC, 'NATIVE': NATIVE, 'XW': XW, 'title_idx': dict(title_idx)}, open('zz_decisions.pkl', 'wb'))
for k, v in sorted(stats.items()): print(v, k)
print('event-level', evt)
# cc_review_v4 reconciliation
rv = Counter()
for rn, x in REVIEW_V4.items():
    dx = DEC[rn]; rv[(x[5], dx['population'], dx['status'], dx.get('action'))] += 1
print('cc_review_v4 1036 →'); [print('  ', v, k) for k, v in rv.most_common()]
