"""Final simplified mapping v2: account → financial event → activity → cost center (Taxi & Terminals, 1404–1405).

Revision of account_event_cc_mapping_v1, rebuilt from the same validated sources (no new forensic analysis):
  ledger lines + v2.1 provisional classification       tt_v21.sqlite (sanad, line_event, line_cc, doc_class, hesab)
  financial events FE-xx (v7.1) + TT-NE/PEO/EXC ids     FE v7.1 workbook, v2.1 canonical_events.csv
  cost centers CC-xxx + TTCC proposals                 cc_master.json, v2.1 new_cost_center_candidates.json
  activities (CodeMarkaz → ACT-TX-xx, ACT-TM-01)        v2.1 workbook sheet Activity_Service_Map
  old→new account coding (reassessed crosswalk)         data/work/taxi_gate_audit/mapping_rows.json (m01)

Corrections relative to v1:
  A  relationship type per line — primary / secondary / unknown / non-event — from account nature × event nature × v2.1 role.
     A component line that drives its own event (v2.1 own_event) carries its amount on that event; the document event becomes
     an amount-free secondary row.
  B  a cost center is OBSERVED only when the line's activity supports it (source activity code or document narration, v2.1
     confidence ≥ MEDIUM, no conflict with the center mapped to the line's activity code); event/account defaults, keyword and
     location rules are PROPOSED.
  C  expense lines without a center: completed from the line's specific activity code or the single center of the same
     document (PROPOSED); several centers → amount-free suggestion rows; otherwise «نیازمند بررسی».
  D  revenue / balance-sheet / memo / opening-closing rows: «بدون مرکز هزینهٔ عملیاتی / موضوعیت ندارد».
Every ledger line is counted in exactly one amount row; the sid → row id lineage is written to data/work (internal).
Nothing is APPROVED.  No narration text and no personal names are exported.
"""
import csv
import json
import os
import re
from collections import Counter, OrderedDict, defaultdict

import openpyxl
import xlsxwriter
from xlsxwriter.utility import xl_col_to_name

from common import (SRC_DIR, WORK, TT_DB, FE_V71, CC_MASTER, V21_DIR, V21_EVENTS, NATURE_FA, ro_sqlite, mask_title, norm_key,
                    old_nature)
from expert_crosswalk import MEANING_COLLISIONS

OUT_DIR = os.path.join(SRC_DIR, 'account_event_cc_mapping_v2')
XLSX = os.path.join(OUT_DIR, 'Taxi_Terminals_Final_Mapping_v2.xlsx')
MAIN = 'جدول_نهایی_رویدادها_و_مراکز'
DETAIL = 'جزئیات_و_مستندات'
V1_ROWS = os.path.join(WORK, 'mapping_rows.json')
ROWS_JSON = os.path.join(WORK, 'final_v2_rows.json')
LINEAGE = os.path.join(WORK, 'final_v2_line_lineage.csv')

ORG_FA = {'Taxi': 'تاکسیرانی', 'Terminals': 'پایانه‌ها'}
PFX = {'Taxi': 'TX', 'Terminals': 'TM'}
EXP_NATS = {'EXPENSE', 'NONCASH_EXPENSE', 'COST_OF_SALES'}
BAL_NATS = {'ASSET', 'CONTRA_ASSET', 'LIABILITY', 'PROVISION_LIABILITY', 'EQUITY'}
CAPITAL_KOLS = {115, 116, 121, 123, 124, 125}       # inventories (incl. capital stock), capital prepayments, fixed assets, WIP
REL_FA = {'P': 'اصلی', 'S': 'ثانوی', 'U': 'نامشخص', 'N': 'غیررویدادی'}
ST_FA = {'OBSERVED': 'مشاهده‌شده', 'PROPOSED': 'پیشنهادی', 'UNRESOLVED': 'حل‌نشده', 'APPROVED': 'تأییدشده'}
CONF_FA = {3: 'بالا', 2: 'متوسط', 1: 'پایین'}
RANK = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
KIND_FA = {'AMOUNT': 'دارای مبلغ (هر سطر دفتر یک بار)', 'SECONDARY': 'بدون مبلغ — حضور حساب در سند رویداد دیگر',
           'ALT': 'بدون مبلغ — گزینهٔ پیشنهادی مرکز هزینه', 'PROPOSAL': 'پیشنهاد برای حساب بدون رویداد ثبت‌شده', 'NO_RELATION': 'بدون رابطه (بدون گردش)'}
KHODAPARAST = 'آقای خداپرست'

PSEUDO_EVENT = {
    'NON_EVENT_CLOSING': ('—', 'بستن/افتتاح حساب‌ها (رویداد عملیاتی نیست)', 'سند افتتاحیه، اختتامیه یا بستن حساب‌های موقت؛ در v2.1 رویداد عملیاتی شمرده نشده است.'),
    'NON_EVENT_MEMO': ('—', 'ثبت انتظامی بدون رویداد مشخص', 'ثبت حساب انتظامی که v2.1 آن را به رویداد ضمانت‌نامه (FE-15/FE-16) وصل نکرده است.'),
    'UNRESOLVED_AMBIGUOUS': ('—', 'رویداد تعیین نشده (سند مبهم)', 'در سند، سطر محرکی برای تعیین رویداد پیدا نشد.'),
    'NO_RELATION': ('—', 'رابطه‌ای احراز نشده', 'حساب در دفتر ۱۴۰۴–۱۴۰۵ این سازمان گردش ندارد.'),
}
NA_CC = 'بدون مرکز هزینهٔ عملیاتی / موضوعیت ندارد'
CC_LABEL = {
    'NA_REVENUE': NA_CC, 'NA_NONCOST': NA_CC, 'NA_MEMO': NA_CC, 'NA_CLOSING': NA_CC, 'NA_NONOP': NA_CC,
    'UNRESOLVED_MULTIPLE': 'نیازمند بررسی — چند مرکز محتمل',
    'UNRESOLVED_INSUFFICIENT': 'نیازمند بررسی — اطلاعات کافی نیست',
    'NEEDS_REVIEW': 'نیازمند بررسی — اطلاعات کافی نیست',
    'SEE_AMOUNT': 'مرکز هزینه روی ردیف مبلغ‌دار همین سطرها',
    'NONE': '—',
}
NOTE = {   # reason code → short analyst note (main sheet); order = priority
    'CD01': 'وابسته به تصمیم CD-01 (ماهیت عاملیتی یا اصیل پایانه‌ها) — بررسی ' + KHODAPARAST,
    'PEO': 'عملیات پایان دوره (استهلاک/ذخیره) — تصمیم CD-PEO، بررسی ' + KHODAPARAST,
    'EVENT_UNKNOWN': 'رویداد این سطرها تعیین نشده است',
    'EXC': 'صف استثنا: واریزی نامشخص تا شناسایی طرف حساب',
    'MISMATCH': 'ماهیت حساب با ماهیت رویداد هم‌خوان نیست — بررسی',
    'TTNE': 'رویداد پیشنهادی TT-NE (هنوز در فرهنگ FE تأیید نشده)',
    'TTCC': 'مرکز هزینهٔ پیشنهادی TTCC (خارج از فهرست مراکز موجود)',
    'CC_CONFLICT': 'مرکز با مرکزِ کد فعالیت سند متفاوت است — بررسی',
    'CC_EVENT_ACCOUNT': 'مرکز از نوع رویداد یا عنوان حساب آمده، نه از فعالیت ثبت‌شده',
    'CC_KEYWORD': 'مرکز فقط از یک واژهٔ کلیدی در شرح سند آمده — بررسی',
    'CC_LOCATION': 'مرکز فقط از محل (پایانه) آمده؛ فعالیت در سند نیست',
    'CC_LOWCONF': 'اطمینان طبقه‌بندی مرکز در v2.1 پایین است',
    'RES_ACT': 'مرکز در این نسخه از کد فعالیت سند تکمیل شد (پیشنهادی)',
    'RES_DOC': 'مرکز در این نسخه از سطر هزینهٔ دیگرِ همان سند تکمیل شد (پیشنهادی)',
    'RES_EVT': 'مرکز در این نسخه از مرکز پیش‌فرض همین رویداد در v2.1 تکمیل شد (پیشنهادی؛ نه از فعالیت)',
    'MULTI': 'چند مرکز محتمل؛ گزینه‌ها در ردیف‌های پیشنهادی جدا آمده‌اند',
    'DEPR': 'مرکز هزینهٔ استهلاک به محل استفادهٔ دارایی نیاز دارد که در سند نیست',
    'NEEDS_REVIEW': 'اطلاعات کافی برای تعیین مرکز هزینه نیست — بررسی',
    'CAPEX': 'خرید/مخارج سرمایه‌ای در حساب دارایی ثبت شده است',
    'BS_CC': 'حساب ترازنامه‌ای که هزینه روی آن ثبت شده؛ مرکز از فعالیت/شرح سند است',
    'COMPONENT': 'طرف حساب یا جزء سند؛ حساب اصلی رویداد حساب دیگری است',
    'CASH_LEG': 'طرف بانکی/نقدی سند؛ حساب اصلی رویداد حساب دیگری است',
    'BS_LEG': 'طرف ترازنامه‌ای (دریافتنی/پرداختنی/ذخیره)؛ حساب اصلی رویداد حساب دیگری است',
    'NA_REVENUE': 'درآمد؛ مرکز هزینه ندارد (منبع درآمد — CD-03)',
    'NA_NONCOST': 'حساب ترازنامه‌ای؛ مرکز هزینه روی سطر هزینهٔ همان سند است',
    'NA_MEMO': 'حساب انتظامی؛ اثر هزینه‌ای ندارد',
    'NA_CLOSING': 'سند افتتاحیه/اختتامیه',
    'NA_NONOP': 'درآمد/هزینهٔ غیرعملیاتی',
    'NON_EVENT_MEMO': 'v2.1 این ثبت انتظامی را رویداد عملیاتی ندانسته است',
}


def hkey(k, m, t):
    return f'{k}-{m}-{t}-0'


def natural(e):
    m = re.match(r'([A-Z\-]+?)-?(\d+)$', str(e))
    return (m.group(1), int(m.group(2))) if m else (str(e), 0)


TECH = re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b|\b[A-Z]{5,}\b')     # v2.1 lifecycle tokens (REFUND, PAYOUT_EARMARKED …)


def clean_fa(s):
    """Drop English lifecycle tokens from Persian event titles/definitions for the analyst view."""
    s = TECH.sub('', str(s))
    s = re.sub(r'\(\s*[/،,؛\s]*\)', '', s)
    s = re.sub(r'\s*/\s*(?:/\s*)+', ' / ', s)
    s = re.sub(r'\s*/\s*(?=\))', '', s)
    s = re.sub(r'(?<=\()\s*/\s*', '', s)
    return re.sub(r'\s{2,}', ' ', s).strip(' /؛')


def text_lines(text, width):
    """Estimated wrapped lines of a Tahoma-9 cell (≈1.15 Persian characters per width unit)."""
    cpl = max(1.0, width * 1.15)
    return sum(max(1, -(-len(part) // int(cpl))) for part in str(text).split('\n'))


def main():
    tc = ro_sqlite(TT_DB)

    # ------------------------------------------------------------------ account master: latest-FY titles, masked
    acct = defaultdict(dict)
    for org, fy, hc, name, lvl, kol, mo, t1 in tc.execute('SELECT org,fy,hcode,name,level,kol,moeen,taf1 FROM hesab ORDER BY fy'):
        d = acct[org].setdefault(hc.strip(), dict(level=lvl, kol=int(kol), moeen=int(mo), taf1=int(t1), name=''))
        d['name'] = mask_title(name.strip())

    def aname(org, hc):
        return acct[org].get(hc, {}).get('name', '')

    # ------------------------------------------------------------------ events
    wbe = openpyxl.load_workbook(FE_V71, read_only=True, data_only=True)
    EV = OrderedDict()
    for r in wbe['فرهنگ_رویداد_مالی_کاندید'].iter_rows(min_row=2, values_only=True):
        if r[0]:
            EV[r[0]] = dict(title=r[1], desc=r[3], nature=str(r[5] or ''), kind='FE')
    for r in csv.DictReader(open(V21_EVENTS, encoding='utf-8-sig')):
        if r['event_id'] not in EV:
            EV[r['event_id']] = dict(title=r['title_fa'], desc=r['definition'] or r['title_fa'], nature=r['nature'],
                                     kind=r['event_id'].split('-')[0].replace('TT', 'TTNE'))

    def evclass(e):
        if e.startswith('PEO'):
            return 'PEO'
        if e.startswith('EXC'):
            return 'EXC'
        n = EV[e]['nature']
        for pre, c in (('هزینه', 'EXPENSE'), ('سرمایه', 'CAPITAL'), ('درآمد', 'REVENUE'), ('ترازنامه', 'BALANCE'), ('انتظامی', 'MEMO'),
                       ('واسط', 'TRANSFER')):
            if n.startswith(pre):
                return c
        return 'UNKNOWN'

    # expense events whose dictionary nature includes capitalisation (e.g. FE-03, FE-24): a capital-asset account is primary
    CAPITALISABLE = {e for e in EV if not e.startswith(('PEO', 'EXC')) and evclass(e) == 'EXPENSE' and 'دارایی' in EV[e]['nature']}
    # balance-sheet events whose title explicitly includes the employer share (FE-48): the employer-share expense account is primary
    EXPENSE_IN_BALANCE_EVENT = {e for e in EV if not e.startswith(('PEO', 'EXC')) and evclass(e) == 'BALANCE' and 'کارفرما' in str(EV[e]['title'])}

    def compat(e, nat, k):
        """Relationship of a line that records event e itself (v2.1 DRIVER / own event): P, S or U, plus reason."""
        c = evclass(e)
        if k == 111 and c != 'TRANSFER':
            return 'S', 'CASH_LEG'      # cash/bank is the settlement leg of every event except cash transfers
        if c == 'EXPENSE':
            if nat in EXP_NATS:
                return 'P', ''
            if nat == 'ASSET' and k in CAPITAL_KOLS and e in CAPITALISABLE:
                return 'P', 'CAPEX'
            return ('S', 'BS_LEG') if nat in BAL_NATS else ('U', 'MISMATCH')
        if c == 'CAPITAL':
            if nat in EXP_NATS:
                return 'P', ''
            if nat == 'ASSET' and k in CAPITAL_KOLS:
                return 'P', 'CAPEX'
            return ('S', 'BS_LEG') if nat in BAL_NATS else ('U', 'MISMATCH')
        if c == 'REVENUE':
            if nat in ('REVENUE', 'NONOP_MIXED'):
                return 'P', ''
            return ('S', 'BS_LEG') if nat in BAL_NATS else ('U', 'MISMATCH')
        if c == 'BALANCE':
            if nat in BAL_NATS or (e in EXPENSE_IN_BALANCE_EVENT and nat in EXP_NATS):
                return 'P', ''
            return 'U', 'MISMATCH'
        if c == 'MEMO':
            return ('P', '') if nat in ('MEMO', 'MEMO_CONTRA') else ('S', 'BS_LEG')
        if c == 'TRANSFER':
            return ('P', '') if nat in BAL_NATS | {'NONOP_MIXED'} else ('U', 'MISMATCH')
        if c == 'PEO':
            return ('P', 'PEO') if nat in EXP_NATS | {'CONTRA_ASSET', 'PROVISION_LIABILITY', 'LIABILITY'} else ('U', 'MISMATCH')
        return 'U', 'EXC'

    # ------------------------------------------------------------------ cost centers and activities
    CC = json.load(open(CC_MASTER, encoding='utf8'))
    NCC = json.load(open(os.path.join(V21_DIR, 'machine_readable', 'new_cost_center_candidates.json'), encoding='utf8'))
    w21 = openpyxl.load_workbook(os.path.join(V21_DIR, 'taxi_terminals_financial_mapping_1404_1405_v2.1.xlsx'), read_only=True, data_only=True)
    act_by_code, act_title, ASMC, unit_name = {}, {}, {}, {}
    for r in w21['Activity_Service_Map'].iter_rows(min_row=5, values_only=True):
        if not r[0]:
            continue
        rid = str(r[0])
        if rid.startswith('ACT-'):
            if rid.startswith('ACT-TX') and r[2] == 'Taxi':
                act_by_code[str(r[3])] = rid
            act_title.setdefault(rid, r[1])
            cc_id = str(r[8] or '')
            alts = [x.strip() for x in re.split(r'[،,;]', str(r[10] or '')) if x.strip()]
            if rid != 'ACT-TX-CATCHALL':
                ASMC.setdefault(rid, dict(cc=cc_id if cc_id.startswith(('CC-', 'TTCC-')) else '', alts=alts))
        elif rid.startswith('ORGUNIT-TM-'):
            unit_name[rid[-3:]] = r[1]
    wcd = openpyxl.load_workbook(os.path.join(V21_DIR, 'committee_decisions_v2.1.xlsx'), read_only=True, data_only=True)
    prior_dec = {str(r[0]) for r in wcd['Decisions'].iter_rows(min_row=4, values_only=True) if r[0]}

    def cc_title(c):
        if c in CC:
            return CC[c]['title']
        if c in NCC:
            n = NCC[c]
            return (n.get('title_v2') or n.get('title', '')) + ' (پیشنهادی)'
        return CC_LABEL.get(c, c)

    def cc_basis(rule, basis):
        r, b = rule or '', basis or ''
        if r.startswith('MZ-') or (r == 'TERM' and b.startswith('کد فعالیت منبع')):
            return 'ACTIVITY'
        if r in ('EV-DEF', 'AST-DEF', 'V21-S-UPG') or 'PER_PAY مرکز' in b or b.startswith('حواله خروج'):
            return 'EVENT_ACCOUNT'
        if r in ('TXT-OVR', 'V21-K-OTH', 'V21-K-UPG') or b.startswith(('خدمات انتظامات', 'قبوض ساختمان')):
            return 'NARRATION'
        if r.startswith('V4-') or 'روی شرح سطر' in b:
            return 'KEYWORD'
        if 'در پایانه' in b and 'معنایی' in b:
            return 'LOCATION'
        return 'EVENT_ACCOUNT'

    BASIS_FA = {'ACTIVITY': 'کد فعالیت ثبت‌شده در سند', 'NARRATION': 'شرح سند (فعالیت در متن سند)', 'EVENT_ACCOUNT': 'نوع رویداد/عنوان حساب (پیش‌فرض)',
                'KEYWORD': 'واژهٔ کلیدی در شرح سند', 'LOCATION': 'محل (پایانه) بدون فعالیت', 'RES_ACT': 'تکمیل v2 از کد فعالیت سند',
                'RES_DOC': 'تکمیل v2 از سطر هزینهٔ همان سند', 'RES_EVT': 'تکمیل v2 از مرکز پیش‌فرض رویداد در v2.1'}

    # ------------------------------------------------------------------ head-level coding info from v1 (reassessed crosswalk)
    v1 = json.load(open(V1_ROWS, encoding='utf8'))
    newcode = {}
    for r in v1['rows']:
        o, _, k, m, t = r['_key'][:5]
        newcode.setdefault((o, k, m, t), (r['c12'], r['c13'], r['c14']))

    # ------------------------------------------------------------------ document-level selected centers (for C)
    doc_cc = defaultdict(set)
    evt_cc = defaultdict(set)       # v2.1 event-default centers (rule EV-DEF), used only when unique for the event
    for doc, c, rule, ev in tc.execute("""SELECT c.doc_key, c.cc_id, c.rule_id, e.event_id FROM line_cc c JOIN line_event e ON e.sid=c.sid
                                         WHERE c.eligible=1 AND c.cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE')"""):
        doc_cc[doc].add(c)
        if rule == 'EV-DEF' and ev:
            evt_cc[ev].add(c)
    evt_cc = {e: next(iter(s)) for e, s in evt_cc.items() if len(s) == 1}

    # ------------------------------------------------------------------ line pass
    q = """SELECT s.sid,s.org,s.fy,s.doc_key,s.kol,s.moeen,s.taf1,s.bed,s.bes,s.markaz,s.vahed,
                  e.event_id,e.own_event,e.role,e.outcome,e.conf,e.rule_id,
                  c.eligible,c.cc_status,c.cc_id,c.alt_ccs,c.activity_id,c.source_markaz,c.source_unit,c.conf,c.rule_id,c.basis,
                  d.composite,d.driver_events
           FROM sanad s JOIN line_event e ON e.sid=s.sid JOIN line_cc c ON c.sid=s.sid JOIN doc_class d ON d.doc_key=s.doc_key"""
    G = OrderedDict()           # amount rows
    F = OrderedDict()           # amount-free rows (secondary links / alternative centers)
    S = OrderedDict()           # secondary links collected per account–event pair
    lineage = []
    n_lines = 0

    def is_cd01(org, k, m, t):
        return org == 'Terminals' and ((k, m, t) in ((113, 1, 1), (211, 1, 1)) or (k, m) == (413, 8))

    def status_of(org, k, m, t, ekey, rel, ckey, res, cc_ok_flag, cc_reason):
        reasons = []
        if is_cd01(org, k, m, t):
            reasons.append('CD01')
        if ekey == 'UNRESOLVED_AMBIGUOUS':
            reasons.append('EVENT_UNKNOWN')
        if ekey.startswith('EXC'):
            reasons.append('EXC')
        if ckey in ('UNRESOLVED_MULTIPLE', 'UNRESOLVED_INSUFFICIENT', 'NEEDS_REVIEW'):
            reasons.append(res if res in ('DEPR', 'MULTI') else ('MULTI' if ckey == 'UNRESOLVED_MULTIPLE' else 'NEEDS_REVIEW'))
        if reasons:
            return 'UNRESOLVED', reasons
        if ekey.startswith('NON_EVENT'):
            return 'OBSERVED', reasons
        st = 'OBSERVED'
        if rel == 'U':
            st = 'PROPOSED'
        if EV.get(ekey, {}).get('kind') in ('TTNE', 'PEO'):
            st = 'PROPOSED'
        if ckey in NCC:
            st = 'PROPOSED'
            reasons.append('TTCC')
        if res in ('ACT', 'DOC', 'EVT'):
            st = 'PROPOSED'
            reasons.append('RES_' + res)
        if ckey in CC and not cc_ok_flag:
            st = 'PROPOSED'
            reasons.append(cc_reason)
        return st, reasons

    def new_group(store, key, kind):
        org, k, m, t, ekey, akey, ckey, rel, st = key
        return store.setdefault(key, dict(org=org, k=k, m=m, t=t, ekey=ekey, akey=akey, ckey=ckey, rel=rel, status=st, kind=kind,
                                          lines=0, docs=set(), debit=0, credit=0, fy=Counter(), roles=Counter(), units=Counter(),
                                          econf=Counter(), cconf=Counter(), erule=Counter(), basis=Counter(), crule=Counter(),
                                          reasons=Counter(), check=Counter(), res=Counter(), big=(0, ''), refs=set(), own=0, src=Counter(),
                                          companions=Counter(), alts=Counter()))

    for (sid, org, fy, doc, kol, mo, t1, bed, bes, markaz, vahed, ev, own, role, outcome, econf, erule, elig, ccst, ccid, alt, act, smz,
         sunit, cconf, crule, cbas, composite, drivers) in tc.execute(q):
        n_lines += 1
        k, m, t = int(kol), int(mo), int(t1)
        bed, bes = bed or 0, bes or 0
        nat = old_nature(k, m)
        cd01 = is_cd01(org, k, m, t)
        # ---- event (own event of a component line carries the amount; document event becomes a secondary row)
        doc_ev = None
        if role == 'CLOSING' or outcome == 'NOT_AN_OPERATIONAL_EVENT':
            ekey = 'NON_EVENT_MEMO' if role == 'MEMO' else 'NON_EVENT_CLOSING'
        elif own and own != ev and role == 'COMPONENT':
            ekey, doc_ev = own, ev
        else:
            ekey = ev or 'UNRESOLVED_AMBIGUOUS'
        role_eff = 'DRIVER' if (role in ('DRIVER', 'SETTLEMENT') or (own and own == ekey)) else role
        # ---- relationship type
        if ekey.startswith('NON_EVENT'):
            rel, why = 'N', ''
        elif ekey == 'UNRESOLVED_AMBIGUOUS' or ekey.startswith('EXC'):
            rel, why = 'U', ''
        elif cd01:
            rel, why = 'U', ''
        elif role_eff == 'COMPONENT' and evclass(ekey) != 'TRANSFER':     # in a transfer every balance-sheet leg is the event itself
            rel, why = 'S', 'COMPONENT'
        else:
            rel, why = compat(ekey, nat, k)
            if role_eff == 'MEMO' and rel != 'P':
                rel, why = 'S', 'BS_LEG'
        # ---- activity
        akey = ''
        if not ekey.startswith('NON_EVENT') and (elig == 1 or nat in EXP_NATS):
            mz = str(smz or markaz or '').strip()
            if org == 'Taxi':
                akey = act or ('NO_ACTIVITY_CODE' if mz in ('', 'NULL', 'None') else act_by_code.get(mz) or f'MARKAZ:{mz}')
            else:
                akey = 'ACT-TM-01' if mz == '008' else 'NO_ACTIVITY_CODE'
        # ---- cost center
        res, sugg = '', []
        if ekey.startswith('NON_EVENT'):
            ckey = 'NA_MEMO' if ekey == 'NON_EVENT_MEMO' else 'NA_CLOSING'
        elif elig == 1:
            ckey = {'PROVISIONAL_EXISTING_CC': ccid, 'NEW_CC_CANDIDATE': ccid, 'MULTIPLE_CC_CANDIDATES': 'UNRESOLVED_MULTIPLE',
                    'INSUFFICIENT_INFORMATION': 'UNRESOLVED_INSUFFICIENT'}[ccst]
        elif nat == 'REVENUE':
            ckey = 'NA_REVENUE'
        elif nat == 'NONOP_MIXED':
            ckey = 'NA_NONOP'
        elif nat in ('MEMO', 'MEMO_CONTRA'):
            ckey = 'NA_MEMO'
        elif nat in EXP_NATS:
            ckey = 'UNRESOLVED_NO_CC'
        else:
            ckey = 'NA_NONCOST'
        # C — expense line without a center
        if ckey in ('UNRESOLVED_NO_CC', 'UNRESOLVED_INSUFFICIENT') and nat in EXP_NATS:
            a = ASMC.get(akey)
            dcc = doc_cc.get(doc, set())
            if nat == 'NONCASH_EXPENSE' or ekey == 'PEO-01':
                ckey, res = 'NEEDS_REVIEW', 'DEPR'
            elif a and a['cc']:
                ckey, res = a['cc'], 'ACT'
            elif a and a['alts']:
                ckey, res, sugg = 'UNRESOLVED_MULTIPLE', 'MULTI', a['alts']
            elif ekey in evt_cc:
                ckey, res = evt_cc[ekey], 'EVT'
            elif ckey == 'UNRESOLVED_NO_CC' and len(dcc) == 1:
                ckey, res = next(iter(dcc)), 'DOC'
            elif ckey == 'UNRESOLVED_NO_CC' and len(dcc) > 1:
                ckey, res, sugg = 'UNRESOLVED_MULTIPLE', 'MULTI', sorted(dcc)
            else:
                ckey, res = 'NEEDS_REVIEW', 'NEEDS_REVIEW'
        # B — is the center grounded in the line's activity?
        basis, cc_ok, cc_reason, check = '', False, '', ''
        if ckey in CC or ckey in NCC:
            if res:
                basis = 'RES_' + res
            else:
                basis = cc_basis(crule, cbas)
            a = ASMC.get(akey)
            allowed = ({a['cc']} | set(a['alts'])) - {''} if a else set()
            if not a:
                check = 'NO_SPECIFIC_ACTIVITY'
            elif ckey == a['cc']:
                check = 'MATCH'
            elif ckey in allowed:
                check = 'ALT_OF_ACTIVITY'
            else:
                check = 'CONFLICT'
            cc_ok = basis in ('ACTIVITY', 'NARRATION') and (RANK.get(cconf, 1) >= 2) and check != 'CONFLICT'
            if not cc_ok and not res:
                cc_reason = ('CC_CONFLICT' if check == 'CONFLICT' else 'CC_EVENT_ACCOUNT' if basis == 'EVENT_ACCOUNT' else
                             'CC_KEYWORD' if basis == 'KEYWORD' else 'CC_LOCATION' if basis == 'LOCATION' else 'CC_LOWCONF')
        st, reasons = status_of(org, k, m, t, ekey, rel, ckey, res, cc_ok, cc_reason)
        key = (org, k, m, t, ekey, akey, ckey, rel, st)
        g = new_group(G, key, 'AMOUNT')
        g['lines'] += 1
        g['docs'].add(doc)
        g['debit'] += bed
        g['credit'] += bes
        g['fy'][fy] += 1
        g['roles'][role] += 1
        if org == 'Terminals' and vahed:
            g['units'][str(vahed)[:3]] += 1
        g['econf'][econf or ''] += 1
        if ckey in CC or ckey in NCC:
            g['cconf'][cconf or ''] += 1
            g['basis'][basis] += 1
            g['check'][check] += 1
            if crule and not res:
                g['crule'][crule] += 1
        if erule:
            g['erule'][erule] += 1
        if why:
            g['reasons'][why] += 1
        for r_ in reasons:
            g['reasons'][r_] += 1
        if res:
            g['res'][res] += 1
        if doc_ev:
            g['own'] += 1
        if bed + bes > g['big'][0]:
            g['big'] = (bed + bes, doc)
        lineage.append((sid, key))
        # ---- amount-free secondary link to the document's own event (one per account–event pair; center stays on the amount row)
        if doc_ev:
            s = S.setdefault((org, k, m, t, doc_ev), dict(lines=0, docs=set(), refs=set(), src=Counter(), ckeys=Counter()))
            s['lines'] += 1
            s['docs'].add(doc)
            s['refs'].add(key)
            s['src']['DOC_EVENT'] += 1
            s['ckeys'][ckey if ckey.startswith('NA_') else 'SEE_AMOUNT'] += 1
        # other driver events of a composite document: documented on the amount row, not a relationship of its own
        if composite and outcome == 'COMPONENT_OF_COMPOSITE_TRANSACTION' and drivers:
            for de in json.loads(drivers):
                if de and de not in (ekey, doc_ev):
                    g['companions'][de] += 1
        alts = [x.strip() for x in (alt or '').split(';') if x.strip()] if (elig == 1 and not ekey.startswith('NON_EVENT')) else []
        if ckey not in ('UNRESOLVED_MULTIPLE', 'UNRESOLVED_INSUFFICIENT', 'NEEDS_REVIEW'):
            g['alts'].update(a for a in alts if a != ckey)      # alternatives of an assigned center: documented, not separate rows
            alts = []
        for a in dict.fromkeys(alts + sugg):
            if a != ckey and (a in CC or a in NCC):
                st4 = 'UNRESOLVED' if (cd01 or ekey == 'UNRESOLVED_AMBIGUOUS' or ekey.startswith('EXC')) else 'PROPOSED'
                f = new_group(F, (org, k, m, t, ekey, akey, a, rel, st4), 'ALT')
                f['lines'] += 1
                f['docs'].add(doc)
                f['refs'].add(key)
                f['src']['ALT_V21' if a in alts else 'ALT_V2'] += 1
                if cd01:
                    f['reasons']['CD01'] += 1
                if a in NCC:
                    f['reasons']['TTCC'] += 1

    # secondary links: drop pairs already shown by an amount row, then finalise center label and status
    pairs = {(g['org'], g['k'], g['m'], g['t'], g['ekey']): key for key, g in G.items()}
    for (org, k, m, t, se), s in S.items():
        if (org, k, m, t, se) in pairs:
            g = G[pairs[(org, k, m, t, se)]]
            g['also_lines'] = g.get('also_lines', 0) + s['lines']
            continue
        ckey = 'SEE_AMOUNT' if s['ckeys'].get('SEE_AMOUNT') else s['ckeys'].most_common(1)[0][0]
        if is_cd01(org, k, m, t) or se.startswith('EXC'):
            st = 'UNRESOLVED'
        elif EV[se]['kind'] == 'FE':
            st = 'OBSERVED'
        else:
            st = 'PROPOSED'
        f = new_group(F, (org, k, m, t, se, '', ckey, 'S', st), 'SECONDARY')
        for x in ('lines', 'docs', 'refs', 'src'):
            f[x] = s[x]
        f['reasons']['COMPONENT'] += 1
        if is_cd01(org, k, m, t):
            f['reasons']['CD01'] += 1
    # alternative-center rows that coincide with an amount row are folded into it
    for fk in [x for x in F if x in G]:
        G[fk]['also_lines'] = G[fk].get('also_lines', 0) + F.pop(fk)['lines']

    # ------------------------------------------------------------------ accounts without an established event: proposals / no relation
    established, heads_with_rows, ev_by_head = defaultdict(set), defaultdict(set), defaultdict(Counter)
    for g in G.values():
        hc = hkey(g['k'], g['m'], g['t'])
        heads_with_rows[g['org']].add(hc)
        if g['ekey'] in EV and EV[g['ekey']]['kind'] != 'EXC':
            established[g['org']].add(hc)
            ev_by_head[(g['org'], hc)][g['ekey']] += g['lines']
    P = OrderedDict()
    universe = defaultdict(set)
    for org, accs in acct.items():
        for hc, d in accs.items():
            if d['level'] in (2, 3):
                universe[org].add(hc)
    for org in heads_with_rows:
        universe[org] |= heads_with_rows[org]

    def add_prop(org, k, m, t, ekey, ckey, kind, method, why):
        st = 'UNRESOLVED' if (kind == 'NO_RELATION' or is_cd01(org, k, m, t)) else 'PROPOSED'
        key = (org, k, m, t, ekey, '', ckey, 'U', st)
        if key not in G and key not in F and key not in P:
            P[key] = dict(org=org, k=k, m=m, t=t, ekey=ekey, akey='', ckey=ckey, rel='U', status=st, kind=kind, method=method, why=why)

    for org in ('Taxi', 'Terminals'):
        other = 'Terminals' if org == 'Taxi' else 'Taxi'
        for hc in sorted(universe[org]):
            if hc in established[org]:
                continue
            k, m, t = [int(x) for x in hc.split('-')[:3]]
            if t == 0 and hc not in heads_with_rows[org] and any(
                    x.startswith(f'{k}-{m}-') and x != hc and acct[org][x]['level'] == 3 for x in acct[org]):
                continue        # an L2 with children is covered through its children
            nat = old_nature(k, m)
            exp = nat in EXP_NATS
            na = ('NA_REVENUE' if nat == 'REVENUE' else 'NA_MEMO' if nat in ('MEMO', 'MEMO_CONTRA') else 'NA_NONOP' if nat == 'NONOP_MIXED'
                  else 'NA_NONCOST')
            peo = None
            if k == 122 or (k == 613 and m == 20 and t != 9):
                peo = 'PEO-01'
            elif (k, m) in ((112, 9), (124, 4), (115, 9), (113, 9), (212, 2)) or k in (214, 217, 223, 224) or (k == 613 and m == 20 and t == 9):
                peo = 'PEO-02'
            if peo:
                add_prop(org, k, m, t, peo, 'NEEDS_REVIEW' if exp else na, 'PROPOSAL',
                         'پیشنهاد از ماهیت حساب و تعریف عملیات پایان دوره (CD-PEO)', 'حساب در این سازمان گردش ندارد')
            same = (hc in acct[other] and norm_key(aname(other, hc)) == norm_key(aname(org, hc)) and hkey(k, m, 0) not in MEANING_COLLISIONS)
            if same and ev_by_head.get((other, hc)):
                tot = sum(ev_by_head[(other, hc)].values())
                for e2, n2 in ev_by_head[(other, hc)].most_common(3):
                    if n2 >= 3 and n2 / tot >= 0.10:
                        add_prop(org, k, m, t, e2, 'NEEDS_REVIEW' if exp else na, 'PROPOSAL',
                                 f'پیشنهاد از همان حساب (همان کد و عنوان) در {ORG_FA[other]}',
                                 f'در {ORG_FA[other]} {n2:,} از {tot:,} ردیف این حساب به این رویداد طبقه‌بندی شده است')
            if hc not in heads_with_rows[org] and not any(p['org'] == org and hkey(p['k'], p['m'], p['t']) == hc for p in P.values()):
                add_prop(org, k, m, t, 'NO_RELATION', 'NONE', 'NO_RELATION', '—', '')

    # ------------------------------------------------------------------ assemble, order, assign ids
    rows = list(G.values()) + list(F.values()) + list(P.values())
    kind_o = {'AMOUNT': 0, 'SECONDARY': 1, 'ALT': 2, 'PROPOSAL': 3, 'NO_RELATION': 4}
    rel_o = {'P': 0, 'S': 1, 'U': 2, 'N': 3}

    def sk(r):
        return (0 if r['org'] == 'Taxi' else 1, str(r['k'])[0], r['k'], r['m'], r['t'], rel_o[r['rel']], kind_o[r['kind']],
                r['ekey'] not in EV, natural(r['ekey']), str(r['akey']), not (r['ckey'] in CC or r['ckey'] in NCC), natural(r['ckey']), r['status'])
    rows.sort(key=sk)
    seq = Counter()
    id_of = {}
    for r in rows:
        seq[r['org']] += 1
        r['id'] = f"{PFX[r['org']]}-{seq[r['org']]:04d}"
        id_of[(r['org'], r['k'], r['m'], r['t'], r['ekey'], r['akey'], r['ckey'], r['rel'], r['status'], r['kind'])] = r['id']
    amount_id = {key: id_of[key + ('AMOUNT',)] for key in G}

    # ------------------------------------------------------------------ cell texts
    def head_cell(org, hc):
        nm = aname(org, hc)
        return f'{hc} — {nm}' if nm else hc

    def act_text(akey):
        if akey == '':
            return '—'
        if akey == 'ACT-TX-CATCHALL':
            return 'کد فعالیت عمومی ۱۰۰ — فعالیت مشخص نیست'
        if akey.startswith('ACT-'):
            return f"{akey} — {act_title.get(akey, '')}"
        if akey.startswith('MARKAZ:'):
            return f'کد فعالیت منبع {akey[7:]} — در نقشهٔ فعالیت نیست'
        return 'کد فعالیت در سند ثبت نشده'

    def short_desc(ekey):
        if ekey in PSEUDO_EVENT:
            return PSEUDO_EVENT[ekey][2]
        e = EV[ekey]
        s = re.sub(r'\s*\[[^\]]*\]\s*', ' ', clean_fa(e['desc'] or e['title'])).strip()
        s = re.split(r'؛|\.\s', s)[0].strip().rstrip('.')
        nat = e['nature'] if e['nature'] and e['nature'] != 'در انتظار شناسایی' else ''
        return s + (f' (ماهیت: {nat})' if nat else '')

    def refs_owner(r, nat):
        org, k, m, t, ekey, ckey = r['org'], r['k'], r['m'], r['t'], r['ekey'], r['ckey']
        refs, owners = [], []
        if is_cd01(org, k, m, t):
            refs.append('CD-01 / TG-D-01')
            owners.append('کارشناسان حسابداری شهرداری + ' + KHODAPARAST + ' + حقوقی')
        if ekey.startswith('PEO') or k in (122, 214, 217, 223, 224) or (k, m) in ((613, 20), (212, 2)):
            refs.append('CD-PEO / TG-D-03')
            owners.append('کارشناسان حسابداری شهرداری + ' + KHODAPARAST)
        if ckey == 'NA_REVENUE':
            refs.append('CD-03 / TG-D-14')
            owners.append('درآمد شهرداری + سازمان')
        if ckey in NCC:
            refs.append({'TTCC-P-01': 'CD-04', 'TTCC-P-02': 'CD-05', 'TTCC-P-03': 'CD-06'}[ckey])
            owners.append('کمیتهٔ مراکز هزینه')
        if ckey == 'CC-1301':
            refs.append('CD-08')
            owners.append('کمیتهٔ مراکز هزینه')
        if ckey in ('UNRESOLVED_MULTIPLE', 'UNRESOLVED_INSUFFICIENT', 'NEEDS_REVIEW') or r['kind'] == 'ALT' or r.get('res'):
            refs.append('CD-07 / TG-D-21')
            owners.append('کمیتهٔ مراکز هزینه')
        if ekey.startswith('TT-NE-') and 'CD-EV-' + ekey[-2:] in prior_dec:
            refs.append('CD-EV-' + ekey[-2:])
            owners.append('کمیتهٔ رویداد مالی')
        if ekey == 'FE-60':
            refs.append('CD-FE60')
        if ekey == 'EXC-01':
            refs.append('CD-EXC01')
            owners.append('حسابداری سازمان')
        if ckey == 'NA_MEMO':
            refs.append('CD-GUAR / TG-D-15')
            owners.append('حسابداری')
        if ekey in EV:
            refs.append('CD-CARD / TG-D-20')
            owners.append('کمیتهٔ رویداد مالی')
        return ' ; '.join(dict.fromkeys(refs)), ' ; '.join(dict.fromkeys(owners))

    order = list(NOTE)
    out = []
    for r in rows:
        org, k, m, t, ekey, akey, ckey = r['org'], r['k'], r['m'], r['t'], r['ekey'], r['akey'], r['ckey']
        nat = old_nature(k, m)
        l1, l2, l3 = hkey(k, 0, 0), hkey(k, m, 0), hkey(k, m, t)
        kind = r['kind']
        reasons = Counter(r.get('reasons', {}))
        if kind in ('AMOUNT', 'SECONDARY', 'ALT') and ekey in EV and EV[ekey]['kind'] == 'TTNE':
            reasons['TTNE'] += 1
        if ekey.startswith('PEO'):
            reasons['PEO'] += 1
        if ckey.startswith('NA_') and kind != 'NO_RELATION' and not (r['rel'] == 'S' and ckey == 'NA_NONCOST'):
            reasons[ckey] += 1
        if ekey == 'NON_EVENT_MEMO':
            reasons['NON_EVENT_MEMO'] += 1
        if (ckey in CC or ckey in NCC) and nat in BAL_NATS and kind == 'AMOUNT':
            reasons['BS_CC' if not reasons.get('CAPEX') else 'CAPEX'] += 1
        if ckey in NCC:
            reasons['TTCC'] += 1
        notes = [NOTE[c] for c in order if reasons.get(c)]
        if kind == 'SECONDARY':
            notes.insert(0, 'بدون مبلغ؛ مبلغ این سطرها در ردیف ' + '، '.join(sorted({amount_id[x] for x in r['refs']})[:4]) +
                         (' …' if len({amount_id[x] for x in r['refs']}) > 4 else ''))
        elif kind == 'ALT':
            notes.insert(0, 'گزینهٔ پیشنهادی مرکز؛ بدون مبلغ (مبلغ در ردیف ' + '، '.join(sorted({amount_id[x] for x in r['refs']})[:4]) +
                         (' …' if len({amount_id[x] for x in r['refs']}) > 4 else '') + ')')
        elif kind == 'PROPOSAL':
            notes.insert(0, r['method'])
        elif kind == 'NO_RELATION':
            notes = ['حساب در ۱۴۰۴–۱۴۰۵ گردش ندارد؛ رابطه‌ای قابل احراز نیست'] + (['کل ۹۲۰ «تست» — احتمالاً آزمایشی'] if k == 920 else [])
        if is_cd01(org, k, m, t) and NOTE['CD01'] not in notes:
            notes.insert(0, NOTE['CD01'])
        notes = list(dict.fromkeys(notes))[:4]
        # confidence
        if kind == 'AMOUNT':
            if ekey.startswith('NON_EVENT'):
                lvl = 3 if ekey == 'NON_EVENT_CLOSING' else 2
            else:
                lvl = RANK.get(r['econf'].most_common(1)[0][0], 1) if r['econf'] else 1
                if r['cconf']:
                    lvl = min(lvl, RANK.get(r['cconf'].most_common(1)[0][0], 1))
                if r['status'] == 'PROPOSED':
                    lvl = min(lvl, 2)
                if r['basis'] and r['basis'].most_common(1)[0][0] in ('KEYWORD', 'LOCATION'):
                    lvl = 1
                if r['status'] == 'UNRESOLVED' or r['rel'] == 'U':
                    lvl = 1
        elif kind == 'SECONDARY':
            lvl = 2 if r['status'] != 'UNRESOLVED' else 1
        elif kind == 'PROPOSAL':
            lvl = 2 if ekey.startswith('PEO') else 1
        else:
            lvl = 1
        if r['status'] == 'UNRESOLVED':
            lvl = 1
        refs, owners = refs_owner(r, nat)
        e_code, e_title = (PSEUDO_EVENT[ekey][0], PSEUDO_EVENT[ekey][1]) if ekey in PSEUDO_EVENT else (ekey, clean_fa(EV[ekey]['title']))
        c_code = ckey if (ckey in CC or ckey in NCC) else '—'
        nc = newcode.get((org, k, m, t), ('', '', ''))
        has_amt = kind == 'AMOUNT'
        o = OrderedDict()
        o['id'] = r['id']
        o['org'] = ORG_FA[org]
        o['gl'] = head_cell(org, l1)
        o['sub'] = head_cell(org, l2)
        o['det'] = head_cell(org, l3) if t else '—'
        o['ev_code'] = e_code
        o['ev_title'] = e_title
        o['ev_desc'] = short_desc(ekey)
        o['activity'] = act_text(akey)
        o['cc_code'] = c_code
        o['cc_title'] = cc_title(ckey)
        o['rel'] = REL_FA[r['rel']]
        o['status'] = ST_FA[r['status']]
        o['conf'] = CONF_FA[lvl]
        o['docs'] = len(r['docs']) if 'docs' in r else 0
        o['notes'] = '؛ '.join(notes)
        # details
        d = OrderedDict()
        d['kind'] = KIND_FA[kind]
        d['l1'], d['l2'], d['l3'] = l1, l2, (l3 if t else '')
        d['nature'] = NATURE_FA.get(nat, nat)
        d['lines'] = r['lines'] if has_amt else (r.get('lines') or 0)
        d['l1404'] = r['fy'].get('1404', 0) if has_amt else ''
        d['l1405'] = r['fy'].get('1405', 0) if has_amt else ''
        d['debit'] = r['debit'] if has_amt else ''
        d['credit'] = r['credit'] if has_amt else ''
        if has_amt:
            d['count_rule'] = 'در جمع کل شمرده شده (هر سطر دفتر فقط در این ردیف)'
        elif kind in ('SECONDARY', 'ALT'):
            ids = sorted({amount_id[x] for x in r['refs']})
            d['count_rule'] = 'بدون مبلغ — مبلغ همین سطرها در ردیف‌های: ' + '، '.join(ids)
        else:
            d['count_rule'] = 'بدون سطر دفتر در این سازمان'
        role_fa = {'DRIVER': 'محرک', 'COMPONENT': 'مؤلفه', 'SETTLEMENT': 'تسویه', 'MEMO': 'انتظامی', 'CLOSING': 'افتتاحیه/اختتامیه'}
        d['roles'] = '؛ '.join(f'{role_fa.get(x, x)} {n:,}' for x, n in r['roles'].most_common()) if has_amt else ''
        if has_amt and r['own']:
            d['roles'] += f"؛ از این تعداد {r['own']:,} سطر جزء سند رویداد دیگری است و رویداد خود سطر (own_event در v2.1) ثبت شد"
        d['units'] = '؛ '.join(f"{unit_name.get(u, 'واحد ' + u)} {n:,}" for u, n in r['units'].most_common(6)) if has_amt and r['units'] else ''
        if has_amt:
            docs_s = sorted(r['docs'])
            pick = list(dict.fromkeys([r['big'][1]] + docs_s[:1] + docs_s[-1:]))
            d['sample_docs'] = '؛ '.join(x for x in pick if x)
        elif kind in ('SECONDARY', 'ALT'):
            d['sample_docs'] = '؛ '.join(sorted(r['docs'])[:3])
        else:
            d['sample_docs'] = ''
        d['ev_basis'] = ('؛ '.join(f'{x} {n:,}' for x, n in r['erule'].most_common(3)) if has_amt and r['erule'] else
                         'رویداد سند (doc_class / line_event)؛ سطر رویداد خود را دارد (own_event)' if kind == 'SECONDARY' else
                         r.get('why', '') if kind == 'PROPOSAL' else '')
        if has_amt and r['basis']:
            d['cc_basis'] = '؛ '.join(f'{BASIS_FA[x]} {n:,}' for x, n in r['basis'].most_common()) + (
                ' | قاعده‌ها: ' + '، '.join(x for x, _ in r['crule'].most_common(3)) if r['crule'] else '')
        elif kind == 'ALT':
            d['cc_basis'] = '؛ '.join({'ALT_V21': 'گزینهٔ جایگزین v2.1 (alt_ccs)', 'ALT_V2': 'گزینهٔ v2 از نقشهٔ فعالیت/مراکز همان سند'}[x]
                                     for x in r['src'])
        else:
            d['cc_basis'] = ''
        chk_fa = {'MATCH': 'هم‌خوان با مرکز فعالیت', 'ALT_OF_ACTIVITY': 'گزینهٔ مجاز همان فعالیت', 'CONFLICT': 'ناسازگار با مرکز کد فعالیت',
                  'NO_SPECIFIC_ACTIVITY': 'فعالیت مشخص در سند نیست'}
        d['cc_check'] = '؛ '.join(f'{chk_fa[x]} {n:,}' for x, n in r['check'].most_common()) if has_amt and r['check'] else ''
        res_fa = {'ACT': 'تکمیل از کد فعالیت', 'DOC': 'تکمیل از مرکز همان سند', 'EVT': 'تکمیل از مرکز پیش‌فرض رویداد v2.1',
                  'MULTI': 'چند گزینه (پیشنهادها جدا)', 'DEPR': 'استهلاک — نیازمند محل استفادهٔ دارایی', 'NEEDS_REVIEW': 'نیازمند بررسی'}
        d['resolution'] = '؛ '.join(f'{res_fa[x]} {n:,}' for x, n in r['res'].most_common()) if has_amt and r['res'] else ''
        d['new_code'], d['new_title'], d['new_status'] = nc
        d['refs'] = refs
        d['owners'] = owners
        d['also'] = (f"این حساب در {r['also_lines']:,} سطر دیگر هم به‌عنوان جزء سند یا گزینهٔ مرکز به همین رویداد مربوط است (بدون مبلغ اضافه)"
                     if r.get('also_lines') else '')
        d['companions'] = ('؛ '.join(f'{x} {n:,}' for x, n in sorted(r['companions'].items(), key=lambda z: (-z[1], natural(z[0]))))
                           if has_amt and r['companions'] else '')
        d['alts'] = '؛ '.join(f'{x} {n:,}' for x, n in r['alts'].most_common()) if has_amt and r['alts'] else ''
        d['source'] = ('tt_v21.sqlite: sanad + line_event + line_cc + doc_class' if kind in ('AMOUNT', 'SECONDARY', 'ALT') else
                       'tt_v21.sqlite: hesab' + ('' if kind == 'NO_RELATION' else ' + ' + str(r.get('method', ''))))
        o['_d'] = d
        o['_k'] = dict(org=org, k=k, m=m, t=t, ekey=ekey, akey=akey, ckey=ckey, rel=r['rel'], status=r['status'], kind=kind)
        out.append(o)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(LINEAGE, 'w', newline='', encoding='utf8') as fh:
        w = csv.writer(fh)
        w.writerow(['sid', 'row_id'])
        for sid, key in lineage:
            w.writerow([sid, amount_id[key]])
    json.dump(dict(rows=out, n_lines=n_lines, universe={o: sorted(v) for o, v in universe.items()}), open(ROWS_JSON, 'w', encoding='utf8'),
              ensure_ascii=False, default=list)
    write_xlsx(out)
    print('rows', len(out), Counter(r['_k']['kind'] for r in out), Counter(r['_k']['status'] for r in out),
          Counter(r['_k']['rel'] for r in out), 'lines', n_lines)


MAIN_COLS = [('id', 'شناسه ردیف', 10), ('org', 'حوزه', 10), ('gl', 'حساب کل', 24), ('sub', 'حساب معین', 30), ('det', 'حساب تفصیلی', 30),
             ('ev_code', 'کد رویداد مالی', 11), ('ev_title', 'عنوان رویداد مالی', 34), ('ev_desc', 'شرح ساده رویداد', 46),
             ('activity', 'فعالیت مرتبط', 30), ('cc_code', 'کد مرکز هزینه', 11), ('cc_title', 'عنوان مرکز هزینه', 34),
             ('rel', 'نوع رابطه حساب و رویداد', 12), ('status', 'وضعیت رابطه', 12), ('conf', 'درجه اطمینان', 10),
             ('docs', 'تعداد اسناد مرتبط', 10), ('notes', 'توضیحات و موارد نیازمند بررسی', 55)]
DETAIL_COLS = [('id', 'شناسه ردیف', 10), ('org', 'حوزه', 10), ('kind', 'نوع ردیف', 26), ('l1', 'کد حساب کل', 11), ('l2', 'کد حساب معین', 11),
               ('l3', 'کد حساب تفصیلی', 12), ('nature', 'ماهیت حساب', 18), ('ev_code', 'کد رویداد مالی', 11), ('cc_code', 'کد مرکز هزینه', 11),
               ('rel', 'نوع رابطه', 10), ('status', 'وضعیت رابطه', 11), ('lines', 'تعداد سطرهای دفتر', 11), ('l1404', 'سطرهای ۱۴۰۴', 10),
               ('l1405', 'سطرهای ۱۴۰۵ (ناقص)', 10), ('docs', 'تعداد اسناد', 10), ('debit', 'جمع بدهکار', 19), ('credit', 'جمع بستانکار', 19),
               ('count_rule', 'وضعیت شمارش مبلغ', 34), ('roles', 'نقش سطرها در طبقه‌بندی v2.1', 34), ('units', 'واحدهای سازمانی (پایانه‌ها)', 30),
               ('sample_docs', 'نمونه شماره سند', 30), ('ev_basis', 'مبنای تعیین رویداد (قاعده‌ها)', 30), ('cc_basis', 'مبنای تعیین مرکز هزینه', 36),
               ('cc_check', 'بازبینی مرکز با فعالیت', 30), ('resolution', 'تکمیل مرکز برای سطر هزینهٔ بدون مرکز', 30),
               ('new_code', 'کد در کدینگ جدید', 11), ('new_title', 'عنوان در کدینگ جدید', 26), ('new_status', 'وضعیت تطبیق با کدینگ جدید', 40),
               ('refs', 'ارجاع تصمیم', 26), ('owners', 'مرجع بررسی', 30), ('also', 'یادداشت ادغام', 24),
               ('companions', 'رویدادهای دیگرِ همان اسناد ترکیبی (سطر)', 30), ('alts', 'مراکز جایگزین ثبت‌شده در v2.1 (سطر)', 26),
               ('source', 'منبع داده', 32)]
DETAIL_NUM = {'lines', 'l1404', 'l1405', 'docs', 'debit', 'credit'}
DETAIL_CODE = {'id', 'l1', 'l2', 'l3', 'ev_code', 'cc_code', 'new_code'}
MAIN_CODE = {'id', 'ev_code', 'cc_code'}
HEADER_NOTES = {
    'id': 'شناسهٔ ثابت ردیف؛ همین شناسه در شیت «جزئیات_و_مستندات» جزئیات، مبالغ و شماره اسناد را می‌دهد.',
    'rel': 'اصلی: حساب ماهیت رویداد را مستقیم ثبت می‌کند.\nثانوی: طرف حساب یا جزء سند (بانک، دریافتنی، پرداختنی، کسور).\nنامشخص: شواهد کافی نیست یا به تصمیم باز (CD-01) وابسته است.\nغیررویدادی: سند افتتاحیه/اختتامیه یا ثبت انتظامی بدون رویداد.',
    'status': 'مشاهده‌شده: در دفتر ۱۴۰۴–۱۴۰۵ دیده شده و مرکز هزینه (در صورت وجود) با فعالیت سند پشتیبانی می‌شود.\nپیشنهادی: رویداد یا مرکز کاندید است یا مرکز از فعالیت تأیید نشده.\nحل‌نشده: رویداد یا مرکز تعیین نشده یا به CD-01 وابسته است.\nتأییدشده: هیچ ردیفی تأیید رسمی ندارد.',
    'cc_title': '«بدون مرکز هزینهٔ عملیاتی / موضوعیت ندارد» برای درآمد، حساب‌های ترازنامه‌ای، انتظامی و افتتاحیه/اختتامیه.',
    'docs': 'ردیف‌های بدون مبلغ (ثانوی/گزینهٔ مرکز) را جمع نزنید؛ مبلغ هر سطر دفتر فقط یک بار در جزئیات آمده است.',
}


def write_xlsx(rows):
    wb = xlsxwriter.Workbook(XLSX, {'strings_to_numbers': False, 'strings_to_formulas': False, 'strings_to_urls': False})
    base = dict(font_name='Tahoma', font_size=9, valign='top', reading_order=2, border=1, border_color='#D9D9D9')
    head = wb.add_format(dict(base, bold=True, bg_color='#DDEBF7', font_color='#1F3864', text_wrap=True, valign='vcenter', align='center',
                              border_color='#9BC2E6'))
    f_txt = wb.add_format(dict(base, text_wrap=True))
    f_code = wb.add_format(dict(base, num_format='@', align='center'))
    f_num = wb.add_format(dict(base, num_format='#,##0'))
    tint = {'تاکسیرانی': wb.add_format({'bg_color': '#FFFBEF'}), 'پایانه‌ها': wb.add_format({'bg_color': '#F1F7FC'})}
    warn = wb.add_format({'bg_color': '#FCE4D6', 'font_color': '#9C0006', 'bold': True})
    soft = wb.add_format({'font_color': '#7F6000', 'bold': True})
    low = wb.add_format({'font_color': '#9C0006'})

    def sheet(name, cols, getter, num, code):
        ws = wb.add_worksheet(name)
        ws.right_to_left()
        for i, (k, h, w) in enumerate(cols):
            ws.set_column(i, i, w)
            ws.write_string(0, i, h, head)
            if name == MAIN and k in HEADER_NOTES:
                ws.write_comment(0, i, HEADER_NOTES[k], {'x_scale': 2.2, 'y_scale': 2.2})
        ws.set_row(0, 36)
        wrap_w = {k: w for k, h, w in cols}
        for r, row in enumerate(rows, start=1):
            lines = max(text_lines(getter(row, k), wrap_w[k]) for k, _, _ in cols if k not in num and k not in code)
            ws.set_row(r, 12.6 * lines + 3)
            for i, (k, h, w) in enumerate(cols):
                v = getter(row, k)
                if k in num:
                    ws.write_number(r, i, v, f_num) if isinstance(v, int) else ws.write_blank(r, i, None, f_num)
                elif v in ('', None):
                    ws.write_blank(r, i, None, f_code if k in code else f_txt)
                else:
                    ws.write_string(r, i, str(v), f_code if k in code else f_txt)
        n = len(rows)
        ws.autofilter(0, 0, n, len(cols) - 1)
        last = xl_col_to_name(len(cols) - 1)
        names = [c[0] for c in cols]
        for k, crit, fmt in (('status', 'حل‌نشده', warn), ('rel', 'نامشخص', warn), ('status', 'پیشنهادی', soft), ('conf', 'پایین', low)):
            if k in names:
                ci = names.index(k)
                ws.conditional_format(1, ci, n, ci, {'type': 'cell', 'criteria': '==', 'value': f'"{crit}"', 'format': fmt})
        if 'cc_title' in names:
            ci = names.index('cc_title')
            ws.conditional_format(1, ci, n, ci, {'type': 'text', 'criteria': 'begins with', 'value': 'نیازمند بررسی', 'format': warn})
        for org, fmt in tint.items():
            ws.conditional_format(f'A2:{last}{n + 1}', {'type': 'formula', 'criteria': f'=$B2="{org}"', 'format': fmt})
        return ws

    m = sheet(MAIN, MAIN_COLS, lambda row, k: row[k], {'docs'}, MAIN_CODE)
    m.freeze_panes(1, 2)
    m.set_zoom(90)
    m.activate()

    def dget(row, k):
        if k in ('id', 'org', 'ev_code', 'cc_code', 'rel', 'status', 'docs'):
            return row[k]
        return row['_d'][k]
    d = sheet(DETAIL, DETAIL_COLS, dget, DETAIL_NUM, DETAIL_CODE)
    d.freeze_panes(1, 2)
    d.set_zoom(90)
    wb.close()


if __name__ == '__main__':
    main()
