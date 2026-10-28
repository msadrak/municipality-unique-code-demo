"""Phase 2 — account dictionary, organization→municipality account crosswalk, taxonomy-divergence report.

Municipality chart = the 1404 municipality journal taxonomy (new coding, data/work/taxi_terminals/municipality_chart.json, built from
data/work/fe_model/journal_v4.pkl).  It is OBSERVED, not an authoritative chart.  The two organizations use a different (affiliated-
organization) chart: the same numeric code frequently means something else (e.g. 411/412/413/611/612), so numeric equality is never
used as evidence.  Matching levels (mandate §5.2): L1 exact code+definition, L2 hierarchy/component, L3 authoritative reference — none is
available — L4 normalized-title + compatible nature (PROVISIONAL), L5 expert-review candidate / no equivalent.
"""
import sqlite3, sys, os, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from common import *

con = sqlite3.connect(DB)
cur = con.cursor()
MUN = json.load(open(f'{WORK}/municipality_chart.json', encoding='utf8'))
mun_titles = {}
for r in MUN['new_coding']:
    mun_titles[(r['kol'], r['moin'])] = r['moin_title']; mun_titles[(r['kol'], None)] = r['kol_title']

# org chart (kol, moeen) -> (mun kol, mun moin, method, nature_compat, note)
# method L4 = title+nature compatible (PROVISIONAL), L5 = expert-review candidate, NONE = no equivalent in the observed municipality chart
X = {
 ('111', '1'): ('110', '11007', 'L4', 'صندوق ↔ صندوق'), ('111', '2'): ('110', '11001/11002/11005', 'L4', 'بانک‌ها ↔ بانک پرداخت هزینه/دریافت درآمد/دریافت وجوه سپرده؛ تفکیک با تفصیلی ۱/۲/۳ سازمان (درآمد/هزینه/سپرده)'),
 ('111', '3'): ('110', '11009', 'L4', 'تنخواه گردان‌ها ↔ تنخواه گردانها'), ('111', '4'): ('110', '11008', 'L4', 'وجوه بین‌راه ↔ وجوه بین راهی'),
 ('112', '1'): ('125', None, 'L5', 'سرمایه‌گذاری کوتاه‌مدت؛ زیرحساب‌های شهرداری با نام شرکت‌اند'), ('112', '2'): ('125', None, 'L5', ''), ('112', '3'): ('125', None, 'L5', ''),
 ('112', '8'): ('125', None, 'L5', ''), ('112', '9'): ('', None, 'NONE', 'ذخیره کاهش ارزش — مبنای نقدی شهرداری ندارد'),
 ('113', '1'): ('115', '11503', 'L5', 'حساب‌های دریافتنی مختلط (بهره‌بردار، شهرداری، شرکت‌ها) ↔ مطالبات از سازمان‌ها/شرکت‌های وابسته — فقط بخشی هم‌ارز'),
 ('113', '5'): ('115', '11513', 'L4', 'اسناد دریافتنی ↔ اسناد دریافتنی عملیاتی سال جاری'), ('113', '6'): ('115', '11513', 'L5', 'اسناد در جریان وصول؛ زیرحساب جدا در شهرداری نیست'),
 ('113', '7'): ('150', '115014', 'L5', 'اسناد برگشتی ↔ اسناد واخواستی (کد شهرداری ۱۱۵۰۱۴ زیر کل ۱۵۰ ثبت شده است)'), ('113', '9'): ('', None, 'NONE', 'ذخیره مطالبات مشکوک‌الوصول'),
 ('114', '1'): ('120', '12001', 'L5', 'بدهکاران کارکنان (وام/مساعده) ↔ مطالبات از کارکنان غیرپرسنلی؛ هم‌پوشانی جزئی'), ('114', '2'): ('710', '71006', 'L5', 'خزانه معین شهرداری ↔ حساب رابط/تمرکز وجوه'),
 ('114', '3'): ('', None, 'NONE', ''), ('114', '4'): ('120', '12003', 'L4', 'سپرده ما نزد دیگران ↔ سپرده‌ها و ودایع دریافتنی'), ('114', '5'): ('', None, 'NONE', ''),
 ('114', '7'): ('120', '12005', 'L5', 'بازپرداخت وام به خزانه ↔ تسهیلات مالی پرداختی'), ('114', '8'): ('120', None, 'L5', ''),
 ('114', '9'): ('', None, 'NONE', 'تاکسیرانی: مالیات ارزش افزوده پرداختی؛ پایانه‌ها: حساب خزانه معین بانک شهر — یک کد، دو معنا'), ('114', '10'): ('710', None, 'L5', 'صندوق ذخیره خزانه‌داری ↔ حساب رابط'),
 ('115', '1'): ('130', '13002', 'L5', ''), ('115', '4'): ('130', '13002', 'L4', 'موجودی کالای اموالی ↔ موجودی مواد'), ('115', '5'): ('130', '13002', 'L4', 'موجودی کالای مصرفی ↔ موجودی مواد'),
 ('115', '6'): ('130', '13005', 'L5', ''), ('115', '8'): ('130', '13005', 'L4', 'سایر موجودی‌ها'), ('115', '2'): ('130', None, 'L5', ''), ('115', '3'): ('130', None, 'L5', ''),
 ('115', '9'): ('', None, 'NONE', 'ذخیره کاهش ارزش موجودی'),
 ('116', '1'): ('140', '14003', 'L4', 'پیش‌پرداخت سرمایه‌ای ↔ پیش پرداخت خریدهای سرمایه‌ای'), ('116', '2'): ('140', '14002', 'L4', 'پیش‌پرداخت هزینه‌ای ↔ پیش پرداخت خرید کالا و خدمات'),
 ('116', '3'): ('140', '14003', 'L4', 'علی‌الحساب سرمایه‌ای'), ('116', '4'): ('140', '14002', 'L4', 'علی‌الحساب هزینه‌ای'), ('116', '5'): ('140', '14005', 'L5', ''),
 ('116', '6'): ('140', '14005', 'L5', ''), ('116', '7'): ('140', '14005', 'L5', ''), ('116', '8'): ('140', '14005', 'L5', ''),
 ('120', '1'): ('150', None, 'L5', 'زمین'), ('120', '2'): ('150', None, 'L5', 'زمین'),
 ('121', '1'): ('150', None, 'L5', 'زمین؛ در دفتر شهرداری زیرحساب زمین مشاهده نشد'), ('121', '2'): ('150', '15005', 'L4', 'ساختمان ↔ ساختمان و مستحدثات'),
 ('121', '3'): ('150', '15002', 'L5', 'ماشین‌آلات و تجهیزات ↔ اثاثه و منصوبات؛ هم‌پوشانی جزئی'), ('121', '4'): ('150', '15005', 'L5', 'تأسیسات'), ('121', '5'): ('150', None, 'L5', 'وسایط نقلیه'),
 ('121', '6'): ('150', '15002', 'L5', ''), ('121', '7'): ('150', '15002', 'L4', 'اثاثیه اداری ↔ اثاثه و منصوبات'), ('121', '8'): ('150', None, 'L5', ''),
 ('121', '9'): ('150', '15001', 'L4', 'دارایی در جریان ساخت ↔ دارایی در جریان تکمیل'), ('121', '10'): ('160', None, 'L5', 'نرم‌افزار'), ('121', '11'): ('150', None, 'L5', ''),
 ('122', None): ('', None, 'NONE', 'استهلاک انباشته: مبنای نقدی/بودجه‌ای شهرداری در دفتر ۱۴۰۴ حساب معادل ندارد'),
 ('123', '1'): ('150', '16002', 'L4', 'سرقفلی'), ('123', '2'): ('160', '16005', 'L4', 'حق‌الامتیاز ↔ حق امتیاز و فرانشیز'), ('123', '3'): ('160', None, 'L5', ''), ('123', '8'): ('160', None, 'L5', ''),
 ('124', '1'): ('170', '17001', 'L4', 'سرمایه‌گذاری در سهام'), ('124', None): ('170', None, 'L5', ''), ('125', None): ('', None, 'NONE', 'سایر دارایی‌های بلندمدت — معادل مشاهده نشد'),
 ('211', '1'): ('210', '21003', 'L5', 'حساب‌های پرداختنی مختلط؛ هم‌ارز با بدهی به سازمان‌های وابسته/پیمانکاران به‌تناسب تفصیلی'), ('211', '2'): ('210', '21003', 'L5', ''),
 ('211', '5'): ('210', '21017', 'L4', 'اسناد پرداختنی'),
 ('212', '1'): ('220', '22001', 'L4', 'بستانکاران کارکنان ↔ بدهی به کارکنان'), ('212', '2'): ('', None, 'NONE', 'ذخیره هزینه‌های پرداختنی'),
 ('212', '3'): ('', None, 'NONE', 'مالیات‌های تکلیفی/پرداختنی (غیر ارزش افزوده)'), ('212', '4'): ('', None, 'NONE', 'حق بیمه پرداختنی'),
 ('212', '6'): ('225', '22501-22507', 'L4', 'سپرده دیگران نزد ما ↔ سپرده‌های پرداختنی؛ تفکیک با تفصیلی'), ('212', '7'): ('', None, 'NONE', 'کسورات حقوق'),
 ('212', '8'): ('220', None, 'L5', 'سایر بستانکاران'), ('212', '9'): ('220', '22011', 'L4', 'مالیات بر ارزش افزوده دریافتی ↔ مالیات و عوارض ارزش افزوده پرداختنی'),
 ('212', '10'): ('220', '22011', 'L5', ''), ('212', '11'): ('220', '22009', 'L5', 'بستانکاران/تعهدات مصرف‌معین ↔ تعهدات مرتبط با کمک بلاعوض'),
 ('212', '12'): ('220', '22009', 'L5', ''), ('212', '13'): ('220', '22009', 'L5', ''), ('212', '14'): ('220', '22009', 'L5', ''),
 ('213', '1'): ('230', '23001', 'L4', 'پیش‌دریافت فروش'), ('213', '2'): ('230', '23001', 'L5', 'پیش‌دریافت خدمات؛ در تاکسیرانی شامل وجوه امانی سفیر مهر'),
 ('214', None): ('', None, 'NONE', 'ذخیره مالیات'), ('215', None): ('', None, 'NONE', 'سود سهام پرداختنی'),
 ('216', '1'): ('235', '23501', 'L4', 'تسهیلات از بانک‌ها'), ('216', '3'): ('220', '22008', 'L5', 'تسهیلات از خزانه شهرداری ↔ تسهیلات مالی دریافتی'), ('216', '8'): ('235', '23502', 'L5', ''),
 ('217', None): ('', None, 'NONE', 'ذخیره حسابرسی'),
 ('221', None): ('250', None, 'L5', 'حساب‌های پرداختنی بلندمدت'), ('222', None): ('235', None, 'L5', 'تسهیلات بلندمدت'),
 ('223', None): ('', None, 'NONE', 'ذخیره مزایای پایان خدمت'), ('224', None): ('', None, 'NONE', 'ذخیره مطالبات مشکوک‌الوصول'),
 ('311', None): ('310', None, 'L5', 'سرمایه'), ('313', None): ('310', None, 'L5', ''), ('314', None): ('310', None, 'L5', ''), ('315', None): ('310', None, 'L5', ''),
 ('316', None): ('310', '31001/31002', 'L5', 'سود و زیان انباشته ↔ مازاد انباشته'),
 ('411', None): ('', None, 'NONE', 'فروش محصولات: تفاوت ماهیت — کد ۴۱۱ شهرداری «عوارض اختصاصی» است'), ('412', None): ('', None, 'NONE', 'بهای تمام‌شده: در شهرداری کد ۴۱۲ درآمد است'),
 ('413', '1'): ('412', '41201/41204', 'L5', 'درآمد خدمات عملیاتی ↔ بهای خدمات و درآمد مؤسسات انتفاعی؛ کد ۴۱۳ در شهرداری «درآمد وجوه و اموال» است (برخورد کد)'),
 ('413', '8'): ('413', '41301', 'L5', 'سایر درآمدها (کمک بودجه، اجاره، کارمزد) ↔ درآمد وجوه و اموال/کمک دولت — مختلط'),
 ('414', None): ('', None, 'NONE', 'بهای تمام‌شده فعالیت؛ مشاهده‌ای در دفتر ندارد'),
 ('611', '1'): ('610', '61001', 'L4', 'حقوق و دستمزد ↔ جبران خدمات کارکنان (حقوق ثابت)؛ کد ۶۱۱ شهرداری «کالا و خدمات» است (برخورد کد)'),
 ('611', '2'): ('610', '61002', 'L4', 'مزایا و فوق‌العاده‌ها ↔ فوق‌العاده‌ها و مزایای شغل'),
 ('612', '3'): ('611', '61101/61103', 'L5', 'مأموریت/تلفن ↔ مأموریت داخلی/حمل‌ونقل و ارتباطات'), ('612', '4'): ('611', '61111', 'L4', 'اجاره بها و کرایه ↔ اجاره و کرایه'),
 ('612', '5'): ('611', '61102', 'L5', 'خدمات قراردادی عام (شامل کارمزد بانکی، چاپ، پذیرایی) ↔ حق‌الزحمه خدمات قراردادی؛ زیرحساب‌های سازمان وسیع‌ترند'),
 ('612', '6'): ('611', '61108', 'L4', 'سوخت، آب، برق، تلفن ↔ آب و برق و سوخت'), ('612', '7'): ('611', '61109', 'L4', 'مواد و لوازم مصرف‌شدنی'),
 ('613', '16'): ('630', '63002', 'L5', 'کمک به بخش عمومی'), ('613', '17'): ('613', '61305', 'L5', 'کمک به بخش خصوصی ↔ هدایا و پرداخت‌های تشویقی؛ ماهیت متفاوت'),
 ('613', '18'): ('620', '62001', 'L5', 'بازپرداخت وام و کارمزد'), ('613', '19'): ('614', '61404', 'L5', 'پرداخت‌های انتقالی به کارکنان ↔ رفاه اجتماعی'),
 ('613', '20'): ('', None, 'NONE', 'هزینه استهلاک/مطالبات مشکوک‌الوصول: در دفتر شهرداری حساب معادل ندارد'), ('613', '21'): ('650', '65001', 'L5', 'هزینه سنوات قبل ↔ دیون با محل'),
 ('812', '1'): ('416', '41601', 'L5', ''), ('812', '2'): ('413', '41304', 'L4', 'درآمد سپرده بانکی ↔ درآمد حاصل از وجوه سپرده'), ('812', '3'): ('', None, 'NONE', ''),
 ('812', '4'): ('415', '41501', 'L4', 'درآمد ضبط سپرده ↔ ضبط سپرده معاملات'), ('812', '5'): ('', None, 'NONE', 'اصلاح حساب‌های سنواتی'), ('812', '8'): ('', None, 'NONE', 'متفرقه غیرعملیاتی'),
 ('917', None): ('810', None, 'L5', ''), ('918', None): ('810', '81002', 'L4', 'حساب انتظامی'), ('919', None): ('810', None, 'L4', 'طرف حساب انتظامی'), ('920', None): ('', None, 'NONE', 'حساب «تست» — احتمالاً باقی‌مانده آزمایشی'),
}

def lookup(k, m):
    return X.get((k, m)) or X.get((k, None))

def nature(kol):
    d = kol[0]
    if kol == '122' or kol in ('224', '223'): return 'CONTRA_ASSET_OR_PROVISION'
    return {'1': 'ASSET', '2': 'LIABILITY', '3': 'EQUITY', '4': 'REVENUE', '6': 'EXPENSE', '8': 'NON_OPERATING_REV_EXP', '9': 'MEMO'}.get(d, 'UNKNOWN')

for t in ('account_dictionary', 'account_crosswalk', 'account_divergence'):
    cur.execute(f'DROP TABLE IF EXISTS {t}')
cur.execute('''CREATE TABLE account_dictionary(hid, org, fy, hcode, title, title_norm, parent_hcode, kol, moeen, taf1, taf2, level INT, is_leaf INT,
  src_kind, src_type, src_p, proposed_nature, nature_basis, confidence, n_lines INT, bed_total INT, bes_total INT, src_row INT)''')
use = {(r[0], r[1], r[2]): r[3:] for r in cur.execute('SELECT org,fy,hcode,count(*),sum(bed),sum(bes) FROM sanad GROUP BY 1,2,3')}
rows = cur.execute('SELECT hid,org,fy,hcode,name,name_norm,parent_hcode,kol,moeen,taf1,taf2,level,is_leaf,kind,type,p,src_row FROM hesab ORDER BY org,fy,src_row').fetchall()
out = []
for (hid, org, fy, hcode, name, nn, parent, kol, moe, t1, t2, lvl, leaf, kind, typ, p, srow) in rows:
    u = use.get((org, fy, hcode), (0, 0, 0))
    out.append((hid, org, fy, hcode, name, nn, parent, kol, moe, t1, t2, lvl, leaf, kind, typ, p, nature(kol), 'ارقام اول کد (۱ دارایی، ۲ بدهی، ۳ حقوق صاحبان سرمایه، ۴ درآمد، ۶ هزینه، ۸ غیرعملیاتی، ۹ انتظامی) + عنوان؛ ستون Type منبع تفسیر نشد', 'MEDIUM', u[0], u[1] or 0, u[2] or 0, srow))
cur.executemany('INSERT INTO account_dictionary VALUES(' + ','.join('?' * 23) + ')', out)

# ---- crosswalk at (kol, moeen) level per org/year (rows = distinct general/subsidiary accounts of each org-year chart)
cur.execute('''CREATE TABLE account_crosswalk(org, fy, org_kol, org_moeen, org_title, org_hcode, mun_kol, mun_moin, mun_kol_title, mun_moin_title, match_level, match_status, note, n_lines INT, bed_total INT, bes_total INT, code_collision INT, review INT)''')
lv2 = cur.execute("SELECT org,fy,kol,moeen,hcode,title FROM (SELECT org,fy,kol,moeen,hcode,name AS title FROM hesab WHERE taf1='0' AND taf2='0' AND moeen<>'0')").fetchall()
mun_kols = {k[0] for k in mun_titles if k[1] is None}
mun_kol_title = {k[0]: v for k, v in mun_titles.items() if k[1] is None}
cw = []
for org, fy, k, m, hc, title in lv2:
    n, b, c = use.get((org, fy, hc), (0, 0, 0))
    # usage over all tafsili beneath this moeen
    n, b, c = cur.execute('SELECT count(*),coalesce(sum(bed),0),coalesce(sum(bes),0) FROM sanad WHERE org=? AND fy=? AND kol=? AND moeen=?', (org, fy, k, m)).fetchone()
    mk = lookup(k, m)
    if mk is None:
        mk = ('', None, 'NONE', 'حساب در جدول نگاشت نیست')
    mkol, mmoin, lvl, note = mk
    status = {'L4': 'PROVISIONAL_TITLE_NATURE_MATCH', 'L5': 'EXPERT_REVIEW_CANDIDATE', 'NONE': 'NO_MUNICIPALITY_EQUIVALENT'}[lvl]
    # code collision: the SAME numeric kol/moin exists in the municipality chart but with a different meaning
    collision = 1 if (k in mun_kols and mkol != k) else 0
    mm_t = ''
    if mmoin and '/' not in mmoin and '-' not in mmoin: mm_t = mun_titles.get((mkol, mmoin), '')
    cw.append((org, fy, k, m, title, hc, mkol, mmoin, mun_kol_title.get(mkol, ''), mm_t, lvl, status, note, n, b, c, collision, 0 if lvl == 'L4' and False else 1))
cur.executemany('INSERT INTO account_crosswalk VALUES(' + ','.join('?' * 18) + ')', cw)

# ---- divergence: org vs org (same fy) and 1404 vs 1405 (same org), at hcode level
cur.execute('''CREATE TABLE account_divergence(kind, org_a, org_b, fy_a, fy_b, hcode, title_a, title_b, n_lines_a INT, n_lines_b INT, note)''')
chart = collections.defaultdict(dict)
for org, fy, hc, nn, name in cur.execute('SELECT org,fy,hcode,name_norm,name FROM hesab'):
    chart[(org, fy)][hc] = (nn, name)
def nlines(org, fy, hc): return use.get((org, fy, hc), (0, 0, 0))[0]
div = []
for fy in YEARS:
    a, b = chart[('Taxi', fy)], chart[('Terminals', fy)]
    for hc in sorted(set(a) | set(b)):
        if hc in a and hc not in b: div.append(('ONLY_TAXI', 'Taxi', 'Terminals', fy, fy, hc, a[hc][1], None, nlines('Taxi', fy, hc), 0, ''))
        elif hc in b and hc not in a: div.append(('ONLY_TERMINALS', 'Taxi', 'Terminals', fy, fy, hc, None, b[hc][1], 0, nlines('Terminals', fy, hc), ''))
        elif a[hc][0] == b[hc][0]: div.append(('SHARED_SAME_MEANING', 'Taxi', 'Terminals', fy, fy, hc, a[hc][1], b[hc][1], nlines('Taxi', fy, hc), nlines('Terminals', fy, hc), 'کد و عنوان نرمال‌شده یکسان؛ هم‌معنایی هنوز مستند تأیید نشده'))
        else: div.append(('SAME_CODE_DIFFERENT_TITLE', 'Taxi', 'Terminals', fy, fy, hc, a[hc][1], b[hc][1], nlines('Taxi', fy, hc), nlines('Terminals', fy, hc), 'کد یکسان با عنوان متفاوت — باید معنایی بررسی شود'))
for org in ('Taxi', 'Terminals'):
    a, b = chart[(org, '1404')], chart[(org, '1405')]
    for hc in sorted(set(a) | set(b)):
        if hc in a and hc not in b: div.append(('REMOVED_IN_1405', org, org, '1404', '1405', hc, a[hc][1], None, nlines(org, '1404', hc), 0, ''))
        elif hc in b and hc not in a: div.append(('ADDED_IN_1405', org, org, '1404', '1405', hc, None, b[hc][1], 0, nlines(org, '1405', hc), ''))
        elif a[hc][0] != b[hc][0]: div.append(('RENAMED_IN_1405', org, org, '1404', '1405', hc, a[hc][1], b[hc][1], nlines(org, '1404', hc), nlines(org, '1405', hc), 'تغییر عنوان حساب'))
cur.executemany('INSERT INTO account_divergence VALUES(?,?,?,?,?,?,?,?,?,?,?)', div)
con.commit()
print('dictionary', len(out), 'crosswalk', len(cw))
for r in cur.execute('SELECT kind,count(*) FROM account_divergence GROUP BY 1'): print(r)
for r in cur.execute('SELECT match_status,count(*),sum(n_lines) FROM account_crosswalk GROUP BY 1'): print(r)
print(cur.execute("SELECT count(*) FROM account_crosswalk WHERE note='حساب در جدول نگاشت نیست'").fetchone())
print(cur.execute("SELECT org,fy,org_kol,org_moeen,org_title,n_lines FROM account_crosswalk WHERE note='حساب در جدول نگاشت نیست' ORDER BY n_lines DESC LIMIT 12").fetchall())
print('collisions', cur.execute('SELECT count(*), sum(n_lines) FROM account_crosswalk WHERE code_collision=1').fetchone())
