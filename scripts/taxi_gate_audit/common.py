"""Shared paths, loaders and normalisation for the Taxi-Gate deep audit.

All sources are opened read-only.  The two colleague workbooks are hashed before and after every run
(QA test QA-SRC-02) so that any accidental write is detected.
"""
import hashlib
import json
import os
import re
import sqlite3
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC_DIR = os.path.join(ROOT, 'data', 'deliverables', 'taxi_terminals_1404_1405')
F_V1 = os.path.join(SRC_DIR, 'Taxi-Gate_Version1.xlsx')
F_V2 = os.path.join(SRC_DIR, 'Taxi-Gate_version2.xlsx')
SOURCES = {'V1': F_V1, 'V2': F_V2}

WORK = os.path.join(ROOT, 'data', 'work', 'taxi_gate_audit')
OUT = os.path.join(SRC_DIR, 'taxi_gate_audit_v1')
os.makedirs(WORK, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

# prior-project artifacts (read-only)
TT_DB = os.path.join(ROOT, 'data', 'work', 'taxi_terminals', 'tt_v21.sqlite')
MUN_CHART = os.path.join(ROOT, 'data', 'work', 'taxi_terminals', 'municipality_chart.json')
JOURNAL_DB = os.path.join(ROOT, 'data', 'deliverables', 'journal_1404_enrichment_v1_independent_audit', 'journal_records.sqlite')
FE_V71 = os.path.join(ROOT, 'data', 'deliverables', 'financial_event_discovery', 'revisions',
                      '1404-r20260922-canonical-events-v7.1', 'financial_event_discovery_1404-r20260922_canonical-events_v7.1.xlsx')
CC_MASTER = os.path.join(ROOT, 'cc_master.json')
V21_DIR = os.path.join(SRC_DIR, 'revisions', 'v2.1')
V21_CROSSWALK = os.path.join(V21_DIR, 'machine_readable', 'account_crosswalk.csv')
V21_EVENTS = os.path.join(V21_DIR, 'machine_readable', 'canonical_events.csv')
V21_DECISIONS = os.path.join(V21_DIR, 'committee_decisions_v2.1.xlsx')
V21_CD01 = os.path.join(V21_DIR, 'CD-01_terminal_agency_expert_memo_REDACTED.md')
V21_AGENCY = os.path.join(V21_DIR, 'machine_readable', 'terminal_agency_evidence.csv')

# names of the sheets as they exist in the colleague workbooks
S_FULL = 'Sheet1'            # 73,461-row repeated account extract (new chart)
S_DEDUP = 'Sheet2'           # de-duplicated new chart (234 rows, A6:F239)
S_KOL_UNIQ = 'Sheet3'        # =UNIQUE(Sheet1!C:D)
S_KOL = 'kol'
S_EMPTY = 'Sheet4'
S_MOEN = 'moen'              # combined old (flag 2) + new (flag 1) moein list with lookup formulas
S_8 = '88888888'             # A:B old moein list (77) ; I:N copy of the new chart
S_KOL1 = 'حساب کل کد 1'       # interleaved kol list incl. explicit 'new/old' pairs
S_SUMMARY = 'خلاصه تطبیق'      # V2 only
S_MATCH = 'تطبیق معین ۱ با ۲'  # V2 only : best + 2 alternates per old account
S_ALLM = 'بررسی همه تطبیق‌ها'  # V2 only : long form of S_MATCH

SOURCE_UNIT = 'واحد منبع (واحد پول در منبع تصریح نشده — CD-02)'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dump(name, obj):
    with open(os.path.join(WORK, name), 'w', encoding='utf8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, default=str)


def load(name):
    with open(os.path.join(WORK, name), encoding='utf8') as fh:
        return json.load(fh)


def ro_sqlite(path):
    return sqlite3.connect(f'file:{path}?mode=ro', uri=True)


# ------------------------------------------------------------------ Persian normalisation
_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
_CHARS = {'ي': 'ی', 'ى': 'ی', 'ك': 'ک', 'ة': 'ه', 'أ': 'ا', 'إ': 'ا', 'ئ': 'ی', 'ؤ': 'و'}


def norm_fa(s):
    """Normalisation that exactly reproduces the colleague's scoring input (verified 471/471)."""
    s = '' if s is None else str(s)
    for k, v in _CHARS.items():
        s = s.replace(k, v)
    s = s.replace('\u200c', ' ').translate(_DIGITS)
    s = re.sub(r'[^\w\s]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def norm_key(s):
    """Stricter key used for duplicate/variant detection (also removes all spaces)."""
    return norm_fa(s).replace(' ', '')


def _lcs(a, b):
    prev = [0] * (len(b) + 1)
    for ch in a:
        cur = [0]
        for j, bj in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if ch == bj else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def indel_similarity(a, b):
    """2·LCS/(|a|+|b|)·100 — the normalised Indel similarity (rapidfuzz fuzz.ratio)."""
    if not a and not b:
        return 100.0
    return 100.0 * 2 * _lcs(a, b) / (len(a) + len(b))


def colleague_score(a, b):
    return round(indel_similarity(norm_fa(a), norm_fa(b)), 1)


# ------------------------------------------------------------------ privacy masking
_RETIREE = re.compile(r'^(.*?)([-=]\s*)(باز?نشسته سازمان)')


def mask_title(s):
    """Mask bank-account-like digit runs and personal names in sub-ledger titles."""
    if s is None:
        return s
    s = str(s).strip()
    s = re.sub(r'\d{5,}', lambda m: '•' * (len(m.group()) - 3) + m.group()[-3:], s)
    m = _RETIREE.match(s)
    if m:
        s = '‹نام شخص حذف شد›' + m.group(2) + m.group(3) + s[m.end():]
    return s


# ------------------------------------------------------------------ chart helpers
def old_parts(code):
    p = str(code).strip().split('-')
    return tuple(int(x) for x in p)


def old_nature(kol, moeen=None):
    """Accounting nature of an account of the affiliated-organisation chart (Taxi/Terminals)."""
    kol = int(kol)
    if kol == 122 or (kol, moeen) in ((112, 9), (124, 4), (115, 9), (113, 9)):
        return 'CONTRA_ASSET'
    if kol == 224:
        return 'CONTRA_ASSET'          # ذخیره مطالبات مشکوک‌الوصول (allowance), booked in class 2
    if kol in (214, 223):
        return 'PROVISION_LIABILITY'
    if kol in (412, 414):
        return 'COST_OF_SALES'
    if kol == 812:
        return 'NONOP_MIXED'
    if kol == 917:
        return 'CLOSING'
    if kol in (918,):
        return 'MEMO'
    if kol == 919:
        return 'MEMO_CONTRA'
    if kol == 920:
        return 'TEST'
    if kol == 613 and moeen == 20:
        return 'NONCASH_EXPENSE'       # depreciation / bad-debt expense
    return {1: 'ASSET', 2: 'LIABILITY', 3: 'EQUITY', 4: 'REVENUE', 6: 'EXPENSE'}.get(kol // 100, 'UNKNOWN')


def new_nature(cls, kol):
    cls = int(cls) if cls not in (None, '') else None
    kol = int(kol) if kol not in (None, '') else None
    if cls == 7:
        return 'LIAISON'
    if cls == 8:
        return 'MEMO_CONTRA' if kol == 820 else 'MEMO'
    if cls == 6 and kol in (615, 616, 617, 618, 619):
        return 'BUDGET_CAPEX'
    if cls == 6 and kol in (620, 650, 652):
        return 'BUDGET_DEBT_SERVICE'
    return {1: 'ASSET', 2: 'LIABILITY', 3: 'NET_WORTH', 4: 'REVENUE', 6: 'EXPENSE'}.get(cls, 'UNKNOWN')


# old nature -> {new nature: compatibility}
COMPAT = {
    # an asset BALANCE cannot migrate into a budget-basis capital-expenditure (flow) account; that link is an event, not a migration
    'ASSET': {'ASSET': 'COMPATIBLE', 'LIAISON': 'CONDITIONAL'},
    'CONTRA_ASSET': {},
    'LIABILITY': {'LIABILITY': 'COMPATIBLE', 'LIAISON': 'CONDITIONAL'},
    'PROVISION_LIABILITY': {'LIABILITY': 'CONDITIONAL'},
    'EQUITY': {'NET_WORTH': 'COMPATIBLE'},
    'REVENUE': {'REVENUE': 'COMPATIBLE'},
    'EXPENSE': {'EXPENSE': 'COMPATIBLE', 'BUDGET_DEBT_SERVICE': 'CONDITIONAL'},
    'NONCASH_EXPENSE': {'EXPENSE': 'CONDITIONAL'},
    'COST_OF_SALES': {'EXPENSE': 'CONDITIONAL'},
    'NONOP_MIXED': {'REVENUE': 'CONDITIONAL', 'EXPENSE': 'CONDITIONAL', 'NET_WORTH': 'CONDITIONAL'},
    'MEMO': {'MEMO': 'COMPATIBLE'},
    'MEMO_CONTRA': {'MEMO_CONTRA': 'COMPATIBLE', 'MEMO': 'CONDITIONAL'},
    'CLOSING': {},
    'TEST': {},
}


def structural_compat(old_nat, new_nat):
    if new_nat in (None, 'UNKNOWN'):
        return 'NOT_TESTABLE'
    return COMPAT.get(old_nat, {}).get(new_nat, 'INCOMPATIBLE')


NATURE_FA = {
    'ASSET': 'دارایی', 'CONTRA_ASSET': 'کاهندهٔ دارایی (استهلاک انباشته/ذخیره)', 'LIABILITY': 'بدهی',
    'PROVISION_LIABILITY': 'ذخیرهٔ بدهی', 'EQUITY': 'حقوق صاحبان سرمایه', 'NET_WORTH': 'ارزش خالص', 'REVENUE': 'درآمد',
    'EXPENSE': 'هزینه', 'NONCASH_EXPENSE': 'هزینهٔ غیرنقدی (استهلاک/مطالبات مشکوک)', 'COST_OF_SALES': 'بهای تمام‌شده',
    'NONOP_MIXED': 'درآمد/هزینهٔ غیرعملیاتی (مختلط)', 'MEMO': 'انتظامی', 'MEMO_CONTRA': 'طرف انتظامی',
    'CLOSING': 'تراز افتتاحیه/اختتامیه', 'TEST': 'آزمایشی', 'LIAISON': 'حساب رابط درون‌شهرداری',
    'BUDGET_CAPEX': 'هزینهٔ تملک دارایی سرمایه‌ای (مبنای بودجه)', 'BUDGET_DEBT_SERVICE': 'بازپرداخت/دیون (مبنای بودجه)',
    'UNKNOWN': 'نامعلوم',
}
