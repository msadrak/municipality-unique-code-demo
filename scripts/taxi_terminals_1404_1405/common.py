"""Shared paths and helpers for the Taxi / Terminals 1404-1405 integration pipeline.

All values read from the source workbooks are kept verbatim (strings with source padding) in the *_raw columns;
normalized fields are separate.  Nothing here approves a rule: every derived assignment is PROPOSED/OBSERVED.
"""
import re, os

ROOT = 'H:/Freelancing_Project/KalaniProject/municipality_demo'
SRC = 'H:/Freelancing_Project/KalaniProject/Taxi_Gate'
WORK = f'{ROOT}/data/work/taxi_terminals'
OUT = f'{ROOT}/data/deliverables/taxi_terminals_1404_1405'
MR = f'{OUT}/machine_readable'
VARIANT = os.environ.get('TT_VARIANT', 'v1')      # 'v1' (original, reproducible) or 'v2' (audited revision; separate DB/output dir)
if VARIANT == 'v2':
    OUT = f'{OUT}/revisions/v2'
    MR = f'{OUT}/machine_readable'
    DB = f'{WORK}/tt_v2.sqlite'
    QA_JSON = f'{WORK}/qa_results_v2.json'
elif VARIANT == 'v21':      # v2.1 final corrective pass: starts from a copy of tt_v2.sqlite, rules of v2 + 17_v21_corrections.py
    OUT = f'{OUT}/revisions/v2.1'
    MR = f'{OUT}/machine_readable'
    DB = f'{WORK}/tt_v21.sqlite'
    QA_JSON = f'{WORK}/qa_results_v21.json'
else:
    DB = f'{WORK}/tt.sqlite'
    QA_JSON = f'{WORK}/qa_results.json'

VSUF = {'v2': 'v2', 'v21': 'v2.1'}.get(VARIANT, 'v1')
V2FAMILY = VARIANT in ('v2', 'v21')
ORGS = {'Taxi': ('TAXI', 'تاکسیرانی', 'سازمان تاکسیرانی'), 'Terminals': ('TERM', 'پایانه ها', 'سازمان پایانه‌ها')}
YEARS = ('1404', '1405')


def src_path(org, fy, kind):
    return f'{SRC}/{ORGS[org][1]}/{fy}/{kind}.xlsx'


_AR = str.maketrans({'ي': 'ی', 'ك': 'ک', 'ى': 'ی', 'ة': 'ه', 'ۀ': 'ه', 'أ': 'ا', 'إ': 'ا', 'ؤ': 'و', '\u200c': ' ',
                     '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
                     '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'})


def norm(s):
    """Persian/Arabic normalisation for MATCHING fields only (never overwrites source text)."""
    if s is None:
        return ''
    s = str(s).translate(_AR)
    s = re.sub(r'[\u064b-\u065f\u0640]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def strip(s):
    return None if s is None else str(s).strip()
