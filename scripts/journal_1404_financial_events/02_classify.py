"""Apply the provisional event model to every journal line; resolve document-level components; derive CC/contract/project/bank relations.
Output: data/work/fe_model/classified.pkl  (per-row records in journal order + relation table + document info)."""
import pickle, json, re, time, sys
from collections import Counter, defaultdict
sys.path.insert(0, 'H:/Freelancing_Project/KalaniProject/municipality_demo/scripts/journal_1404_financial_events')
import fe_rules as F
from fe_rules import g, s, num, norm, classify

W = 'H:/Freelancing_Project/KalaniProject/municipality_demo/data/work/fe_model/'
t0 = time.time()
ROWS = pickle.load(open(W + 'journal_v4.pkl', 'rb'))['rows']
AUX = pickle.load(open(W + 'aux_v4.pkl', 'rb'))
SRC = json.load(open(W + 'model_sources.json', encoding='utf-8'))
CCR = pickle.load(open(W + 'ccreview_v4.pkl', 'rb'))
SRCCC = pickle.load(open(W + 'source_cc_names.pkl', 'rb'))   # rows with CC names in the ORIGINAL source journal
CCM = {r[0]: r for r in SRC['cc_master'][1:] if r[0]}
for r in SRC['cc_new'][1:]:
    if r[0]: CCM.setdefault(r[0], (r[0], r[1], r[2]))

EV = {}
for r in SRC['dictionary'][1:]:
    if r[0]: EV[r[0]] = dict(title=r[1], family=r[4], nature=r[5], stage=r[6], canonical=True)
for k, v in F.GAPS.items():
    EV[k] = dict(title=v[0], family=v[1], nature=v[2], stage=v[3], canonical=False, why=v[4])

# budget reference (expense codes only; budget codes are not global across revenue/expense)
BTYPE = {}
for r in AUX['بودجه 1404 + مراکز هزینه'][2:]:
    if r[0] is not None: BTYPE[s(r[0])] = (s(r[2]), s(r[1]))
BT_FA = {'سرمایه‌ای غیرمستمر *': 'غیرمستمر (سرمایه‌ای) — مرجع منبع', 'سرمایه‌ای مستمر *': 'مستمر (سرمایه‌ای) — مرجع منبع', 'سرمایه ای': 'سرمایه‌ای — مستمر/غیرمستمر تفکیک نشده',
         'جاری': 'مستمر (جاری)', 'نیازمند تصمیم کارشناسی': 'نیازمند تصمیم کارشناسی (مرجع منبع)'}

# v4 row-level CC review (proposed CC-only etc.)
V4 = {}
for r in CCR[1:]:
    V4[r[0]] = dict(cc=s(r[18]), cc_title=s(r[19]), rel=s(r[20]), status=s(r[26]), action=s(r[27]))

N = len(ROWS)
CAT = [F.category(r) for r in ROWS]
SIDE = []
for r in ROWS:
    d, c = num(g(r, F.C_DR)), num(g(r, F.C_CR))
    SIDE.append('D' if d > c else ('C' if c > d else 'Z'))
AMT = [max(num(g(r, F.C_DR)), num(g(r, F.C_CR))) for r in ROWS]
DTYPE_RAW = [re.sub(r'\s+', ' ', s(g(r, F.C_DTYPE))) for r in ROWS]
DTYPE = [norm(x.split(',')[0]) for x in DTYPE_RAW]
DOCKEY = [f"1404-{s(g(r, F.C_REG))}-{s(g(r, F.C_DOCNO))}" for r in ROWS]
DOCS = defaultdict(list)
for i, k in enumerate(DOCKEY): DOCS[k].append(i)
print('docs', len(DOCS), round(time.time() - t0), flush=True)

DRV_OTHER = {'EXP', 'REV', 'PREPAY_PROJ', 'PREPAY_PURCH', 'PREPAY_CAPPURCH', 'PREPAY_OTHER', 'PREPAY_COMP', 'INVENTORY', 'IMPREST', 'STAFF_REC', 'TRANSFER_ADV', 'FIXED_ASSET'}
def native(r):
    v = [s(g(r, i)) for i in (F.C_AF, F.C_AG, F.C_AH, F.C_AI)]
    if not any(x and x != 'NULL' for x in v): return ''
    return f'{v[0]} {v[1]} / {v[2]} {v[3]}'.strip()

OWN = [None] * N
DOCINFO = {}
CORR = {}
for dk, ix in DOCS.items():
    cs = Counter((CAT[i], SIDE[i]) for i in ix)
    has = lambda c, sd=None: any((c2 == c and (sd is None or s2 == sd)) for (c2, s2) in cs)
    ctx = dict(has_rev_c=has('REV', 'C'), has_rev_d=has('REV', 'D'), has_bank_d=has('BANK', 'D'), has_bank_c=has('BANK', 'C'),
               has_610=any(CAT[i] == 'EXP' and s(g(ROWS[i], F.C_KOL)) == '610' for i in ix),
               drivers_other=any(CAT[i] in DRV_OTHER and (SIDE[i] == 'D' or CAT[i] == 'REV') for i in ix),
               has_inv_c=has('INVENTORY', 'C'), has_pay_c=has('PAY_OTHER', 'C') or has('PAY_AFFIL', 'C') or has('PAY_CONTRACTOR', 'C'),
               has_rev415_c=any(CAT[i] == 'REV' and SIDE[i] == 'C' and s(g(ROWS[i], F.C_MOIN)) == '41501' for i in ix),
               has_notes_c=has('NOTES_REC', 'C'),
               cash_only=all(c in ('BANK', 'INTER_REGION', 'CLEARING', 'CASHBOX', 'INTRANSIT', 'BANK_BLOCKED') for (c, _) in cs))
    dsum, csum = sum(num(g(ROWS[i], F.C_DR)) for i in ix), sum(num(g(ROWS[i], F.C_CR)) for i in ix)
    DOCINFO[dk] = dict(n=len(ix), balanced=abs(dsum - csum) < 0.5, diff=dsum - csum, dtype=DTYPE_RAW[ix[0]], docid=s(g(ROWS[ix[0]], F.C_DOCID)))
    for i in ix:
        OWN[i] = F.line_rule(ROWS[i], CAT[i], SIDE[i], DTYPE[i], ctx)
        if 'اصلاحی' in DTYPE[i] and OWN[i][0] != 'FE-70':
            e0, k0, role0, m0, b0 = OWN[i]
            CORR[i] = e0 if isinstance(e0, list) else ([e0] if e0 else [])
            OWN[i] = ('FE-70', 'DRIVER', f'سند اصلاحی — {role0}', 'قاعده نوع سند اصلاحی', f'نوع سند «{DTYPE_RAW[i]}»؛ ' + (f"رویداد اصلاح‌شده (کاندید): {'/'.join(CORR[i])}؛ " if CORR[i] else '') + b0)
print('line rules', round(time.time() - t0), flush=True)

def is_gap(e): return isinstance(e, str) and e.startswith('GAP')
REC = [None] * N
REL = []   # supplementary line↔event associations
for dk, ix in DOCS.items():
    prim = defaultdict(list); wh = defaultdict(list); amb = set()
    for i in ix:
        e, kind = OWN[i][0], OWN[i][1]
        if isinstance(e, list): amb.update(e)
        elif e and kind == 'DRIVER': prim[e].append(i)
        elif e and kind == 'WITHHOLD': wh[e].append(i)
    pool = prim if prim else wh
    tot = {e: sum(AMT[j] for j in v) for e, v in pool.items()}
    for i in ix:
        e, kind, role, method, basis = OWN[i]
        rec = dict(role=role, method=method, basis=basis, cands=[], kind=kind)
        if isinstance(e, list):
            rec.update(ev='', status='AMBIGUOUS', cands=e)
            for c in e: REL.append((i, dk, f'EI-{dk}-AMB', c, 'کاندید (مبهم)', basis))
        elif e:
            st = 'REQUIRES_NEW_EVENT_REVIEW' if is_gap(e) else 'MAPPED_DIRECT'
            rec.update(ev=e, status=st)
            if i in CORR and CORR[i]:
                rec.update(status='MULTI_EVENT', cands=CORR[i])
                REL.append((i, dk, f'EI-{dk}-FE-70', 'FE-70', 'رویداد اصلی (سند اصلاحی)', 'نوع سند اصلاحی'))
                for c in CORR[i]: REL.append((i, dk, f'EI-{dk}-FE-70', c, 'رویداد اصلاح‌شده (کاندید)', 'قاعده حساب سطر'))
            elif e == 'FE-67' and 'صورت وضعیت' in DTYPE[i]:
                rec.update(status='MULTI_EVENT', cands=['GAP-01'])
                REL.append((i, dk, f'EI-{dk}-{e}', e, 'رویداد اصلی (تعهد سنوات قبل)', basis))
                REL.append((i, dk, f'EI-{dk}-GAP-01', 'GAP-01', 'رویداد همزمان (ثبت صورت‌وضعیت)', 'نوع سند محاسبه صورت‌وضعیت'))
            elif e == 'GAP-01' and CAT[i] == 'EXP':
                r_ = ROWS[i]
                tn = norm(s(g(r_, F.C_MOINT)) + ' ' + norm(' '.join(s(g(r_, j)) for j in (F.C_TAFT, F.C_JOZT))))
                nat_ev = F.expense_event(r_, tn, False)[0]
                nat_ev = nat_ev if isinstance(nat_ev, list) else ([nat_ev] if nat_ev and nat_ev != 'GAP-01' else [])
                rec['cands'] = nat_ev
                REL.append((i, dk, f'EI-{dk}-GAP-01', 'GAP-01', 'رویداد اصلی (ثبت صورت‌وضعیت — شکاف فرهنگ)', basis))
                for c in nat_ev: REL.append((i, dk, f'EI-{dk}-GAP-01', c, 'ماهیت هزینه/خرید مرتبط (کاندید)', 'قاعده معین + متن حساب'))
        else:
            if len(pool) == 1:
                e1 = next(iter(pool))
                rec.update(ev=e1, status='REQUIRES_NEW_EVENT_REVIEW' if is_gap(e1) else 'MAPPED_EVENT_COMPONENT', method='وراثت از تنها رویداد محرک سند')
            elif len(pool) > 1:
                a = AMT[i]
                hit = [ev for ev, v in pool.items() if abs(tot[ev] - a) < 0.5 or any(abs(AMT[j] - a) < 0.5 for j in v)]
                if len(hit) == 1:
                    e1 = hit[0]
                    rec.update(ev=e1, status='REQUIRES_NEW_EVENT_REVIEW' if is_gap(e1) else 'MAPPED_EVENT_COMPONENT', method='تطبیق مبلغ با ردیف محرک همان سند')
                else:
                    e1 = max(pool, key=lambda k: tot[k])
                    others = sorted(set(pool) - {e1})
                    rec.update(ev=e1, status='MULTI_EVENT', cands=others, method='سند چندرویدادی؛ رویداد با بیشترین مبلغ نمایش داده شد')
                    for c in [e1] + others:
                        REL.append((i, dk, f'EI-{dk}-{c}', c, 'رویداد اصلی نمایش‌داده‌شده' if c == e1 else 'رویداد همزمان در همان سند', f'طرف تسویه مشترک؛ مبلغ کل رویداد {int(tot[c]):,}'))
            elif amb:
                rec.update(ev='', status='AMBIGUOUS', cands=sorted(amb), method='وراثت از ردیف محرک مبهم')
                for c in sorted(amb): REL.append((i, dk, f'EI-{dk}-AMB', c, 'کاندید (مبهم، وراثتی)', basis))
            else:
                rec.update(ev='', status='INSUFFICIENT_EVIDENCE', method='سند فاقد ردیف محرک قابل استناد')
        ev = rec['ev']
        rec['inst'] = f'EI-{dk}-{ev}' if ev else (f'EI-{dk}-AMB' if rec['status'] == 'AMBIGUOUS' else '')
        REC[i] = rec
print('doc resolution', round(time.time() - t0), flush=True)

# ------------------------------------------------------------------ dimensions
ACT_CATS = {'PREPAY_PROJ', 'PREPAY_PURCH', 'PREPAY_CAPPURCH', 'PREPAY_OTHER', 'PREPAY_COMP', 'PAY_CONTRACTOR', 'DEP_PERF', 'DEP_INS', 'IMPREST', 'EXP', 'PAY_COMP', 'INVENTORY', 'FIXED_ASSET'}
def act_pick(r):
    for i, f in ((F.C_JOZT, 'جزء'), (F.C_TAFT, 'تفضیلی')):
        c = classify(g(r, i))
        if c and c['kind'] != 'GENERIC': return c, f
        if c is None and norm(g(r, i)) and i == F.C_JOZT and s(g(r, F.C_KOL)) == '652': return None, ''
    return None, ''

def proj_of(i):
    r = ROWS[i]
    if CAT[i] != 'EXP': return None
    b = s(g(r, F.C_BUD))
    if not b or b == 'NULL': return ('NOT_INDICATED', '', '')
    if len(b) == 11 and b.startswith('31'): return ('PROJECT_CANDIDATE_PRIOR_YEAR_NO_ID', f'تعهد سنواتی؛ عنوان: {s(g(r, F.C_JOZT))}', 'تعهدات سنواتی (کد بودجه 31)')
    if len(b) == 11 and b.startswith('32'): return ('NOT_APPLICABLE_CANDIDATE', '', 'بازپرداخت تسهیلات (کد بودجه 32)')
    bt = BTYPE.get(b)
    if not bt: return ('NOT_INDICATED', '', 'کد بودجه خارج از مرجع')
    typ, title = bt
    lab = BT_FA.get(typ, typ)
    if typ == 'سرمایه‌ای غیرمستمر *': return ('PROJECT_IDENTIFIED_BUDGET_ROW', f'{b} — {title}', lab)
    if typ == 'سرمایه ای': return ('PROJECT_CANDIDATE_BUDGET_TYPE_UNDECIDED', f'{b} — {title}', lab)
    if typ == 'سرمایه‌ای مستمر *': return ('NOT_PROJECT_RECURRING_CAPITAL', f'ردیف مستمر {b} — {title}', lab)
    if typ == 'جاری': return ('NOT_APPLICABLE_CANDIDATE', '', lab)
    return ('UNKNOWN_BUDGET_TYPE', f'{b} — {title}', lab)

BANKLAB = {}
for i, r in enumerate(ROWS):
    if CAT[i] == 'BANK': BANKLAB[i] = F.bank_account(r)
CONTRACT = {}
for i, r in enumerate(ROWS):
    c = F.contract_in(' '.join(s(g(r, j)) for j in (F.C_TAFT, F.C_JOZT, F.C_DESC)))
    if c: CONTRACT[i] = c
print('contracts found', len(CONTRACT), round(time.time() - t0), flush=True)

for dk, ix in DOCS.items():
    # per-event natives, projects, banks, contracts within the document
    nat_by_ev = defaultdict(set); proj_by_ev = defaultdict(set); bank_by_ev = defaultdict(set); con_by_key = defaultdict(set)
    prim_nat = set()
    for i in ix:
        rec = REC[i]; evs = [rec['ev']] + rec['cands'] if rec['ev'] else rec['cands']
        nv = native(ROWS[i])
        if nv and CAT[i] == 'EXP' and SIDE[i] == 'D':
            for e in evs: nat_by_ev[e].add(nv)
            prim_nat.add(nv)
        p = proj_of(i)
        if p and p[0].startswith('PROJECT_'):
            for e in evs: proj_by_ev[e].add((p[0], p[1]))
        if i in BANKLAB:
            for e in evs: bank_by_ev[e].add(BANKLAB[i][0])
        if i in CONTRACT:
            for e in evs: con_by_key[('ev', e)].add(CONTRACT[i])
            per = s(g(ROWS[i], F.C_PER))
            if per and per != 'NULL': con_by_key[('per', per)].add(CONTRACT[i])
    bal = DOCINFO[dk]['balanced']
    n_prim = len({REC[i]['ev'] for i in ix if REC[i]['kind'] == 'DRIVER' and REC[i]['ev'] and REC[i]['status'] != 'AMBIGUOUS'})
    for i in ix:
        r = ROWS[i]; rec = REC[i]; ev = rec['ev']; cat = CAT[i]
        dm = F.dims(ev) if ev else (F.U_,) * 6
        closing = ev == 'FE-70'   # closing/opening/adjustment: dimensions stay with the original transactions
        # ---- cost center
        nv = native(r); v4 = V4.get(r[0], {})
        cc_direct, cc_event, cc_prop, cc_status = nv, '', '', ''
        if v4.get('status') == 'PROPOSED_CC_ONLY' and v4.get('cc'):
            cc_prop = f"{v4['cc']} {v4['cc_title']}"
        rec['cc_prov'] = ''
        if nv:
            cc_status = 'DIRECT_LINE_NATIVE_REVENUE_FLAG' if cat == 'REV' else 'DIRECT_LINE_NATIVE'
            rec['cc_prov'] = ('نام مرکز (AG/AI) در منبع اصلی موجود بود؛ کد AF/AH در غنی‌سازی پیشین افزوده شد' if r[0] in SRCCC
                              else 'نوشته‌شده در v4 — فعالیت پیشنهادی تأییدنشده' if v4.get('status') == 'PROPOSED_ACTIVITY' and 'نوشته' in v4.get('action', '')
                              else 'نوشته‌شده در v4 — تطابق مرجع بومی' if 'نوشته' in v4.get('action', '') or 'اصلاح' in v4.get('action', '')
                              else 'غنی‌سازی پیشین (v1–v3)؛ در منبع اصلی خالی')
        else:
            src = nat_by_ev.get(ev, set()) if ev and not closing and rec['status'] != 'MULTI_EVENT' else set()
            if not src and not closing and n_prim == 1 and rec['status'] != 'MULTI_EVENT' and (rec['kind'] in ('WITHHOLD', 'COMPONENT') or ev == 'GAP-01'): src = prim_nat
            if src and dm[0] != F.N_:
                cc_event = ' || '.join(sorted(src))
                cc_status = 'EVENT_LEVEL_FROM_DOCUMENT' if len(src) == 1 else 'EVENT_LEVEL_MULTI_CC'
            elif cat in ACT_CATS and dm[0] != F.N_ and not closing:
                c, fld = act_pick(r)
                if c and c['kind'] in ('op', 'cap', 'sup', 'per', 'CCONLY') and c['cc']:
                    t = CCM.get(c['cc'], (c['cc'], ''))[1]
                    cc_event = f"{c['cc']} {t}" + (f" (سطح۲ بومی پیشنهادی {c['native']})" if c['native'] else ' (بدون معادل بومی)')
                    cc_status = 'EVENT_LEVEL_ACTIVITY_PROPOSED'
                    rec['cc_basis'] = f"قاعده فعالیت {c['rule']} روی عنوان {fld}: «{c['text']}»"
                elif c and c['kind'] in ('AMB', 'AMBREF'):
                    cc_status = 'AMBIGUOUS_ACTIVITY'; rec['cc_basis'] = f"{c['act']} ({fld})"
            if not cc_status:
                if cc_prop: cc_status = 'PROPOSED_CC_ONLY'
                elif dm[0] == F.N_ or closing: cc_status = 'NOT_APPLICABLE_CANDIDATE'
                elif not ev: cc_status = 'UNKNOWN'
                elif dm[0] == F.R_: cc_status = 'MISSING_EVIDENCE'
                else: cc_status = 'CONDITIONAL_NOT_ESTABLISHED'
        rec.update(cc_direct=cc_direct, cc_event=cc_event, cc_prop=cc_prop, cc_status=cc_status,
                   cc_related=cc_direct or cc_event or cc_prop)
        # ---- contract
        con = CONTRACT.get(i)
        if con: cst, cv = 'CONTRACT_IDENTIFIED', con
        else:
            per = s(g(r, F.C_PER))
            cand = con_by_key.get(('per', per), set()) if per and per != 'NULL' and not closing else set()
            if len(cand) > 1: cst, cv = 'CONTRACT_MULTIPLE_FOR_COUNTERPARTY', ' | '.join(sorted(cand))[:200]
            else:
                if not cand and ev and not closing:
                    cand = con_by_key.get(('ev', ev), set())
                    cand = cand if len(cand) == 1 else set()
                cst, cv = ('CONTRACT_IDENTIFIED_EVENT_LEVEL', next(iter(cand))) if cand else ('', '')
            if cst: pass
            elif dm[1] == F.N_ or closing: cst, cv = 'NOT_APPLICABLE_CANDIDATE', ''
            elif F.RX_CONTRACT_WORD.search(norm(' '.join(s(g(r, j)) for j in (F.C_TAFT, F.C_JOZT, F.C_DESC)))) or cat in ('PAY_CONTRACTOR', 'DEP_PERF', 'DEP_INS', 'PREPAY_PROJ') or ev in ('GAP-01', 'FE-01', 'FE-02', 'FE-03', 'FE-07', 'FE-08', 'FE-09', 'FE-10'):
                cst, cv = 'CONTRACT_INDICATED_NO_NUMBER', ''
            elif dm[1] in (F.R_, F.C_): cst, cv = 'CONTRACT_POTENTIAL', ''
            else: cst, cv = 'NOT_INDICATED', ''
        rec.update(con_status=cst, con_value=cv)
        # ---- project & budget type
        p = proj_of(i)
        if p:
            pst, pv, btype = p
            if pst == 'NOT_INDICATED' and (dm[3] == F.N_ or closing): pst = 'NOT_APPLICABLE_CANDIDATE'
        else:
            btype = ''
            cand = proj_by_ev.get(ev, set()) if ev and not closing else set()
            if len(cand) == 1:
                c0 = next(iter(cand)); pst, pv = c0[0] + '_EVENT_LEVEL', c0[1]
            elif len(cand) > 1:
                pst, pv = 'PROJECT_MULTIPLE_IN_EVENT', ' | '.join(sorted(x[1] for x in cand))[:250]
            elif cat == 'PREPAY_PROJ':
                pst, pv = 'PROJECT_INDICATED_NO_ID', f"فقط عنوان حساب «پیش‌پرداخت پروژه‌ها»؛ شناسه پروژه/ردیف بودجه در سطر نیست (ممکن است قرارداد خدماتی باشد). موضوع: {s(g(r, F.C_JOZT))}"
            elif dm[3] == F.N_ or closing: pst, pv = 'NOT_APPLICABLE_CANDIDATE', ''
            elif not ev: pst, pv = 'UNKNOWN', ''
            else: pst, pv = 'NOT_INDICATED', ''
            if cat == 'REV': btype = 'کد بودجه درآمدی' if s(g(r, F.C_BUD)) not in ('', 'NULL') else ''
        rec.update(proj_status=pst, proj_value=pv, btype=btype)
        # ---- bank
        if i in BANKLAB:
            bst, bv = 'BANK_DIRECT_LINE', BANKLAB[i][0]
        elif cat in ('IMPREST', 'CASHBOX'):
            bst, bv = 'NOT_BANK_CASH_OR_IMPREST', ''
        else:
            cand = bank_by_ev.get(ev, set()) if ev and not closing else set()
            if len(cand) == 1: bst, bv = 'BANK_EVENT_LEVEL', next(iter(cand))
            elif len(cand) > 1: bst, bv = 'BANK_EVENT_LEVEL_MULTIPLE', ' || '.join(sorted(cand))[:250]
            elif ev and dm[2] == F.R_ and not closing: bst, bv = 'BANK_NOT_IN_DOCUMENT', ''
            elif not ev: bst, bv = 'UNKNOWN', ''
            elif dm[2] == F.C_ and not closing: bst, bv = 'CONDITIONAL_NOT_ESTABLISHED', ''
            else: bst, bv = 'NOT_APPLICABLE_CANDIDATE', ''
        rec.update(bank_status=bst, bank_value=bv)
        rec['_bal'] = bal; rec['_v4'] = v4.get('status', '')
        rec['cat'] = cat; rec['side'] = SIDE[i]; rec['doc'] = dk
print('dimensions', round(time.time() - t0), flush=True)

# ---- cross-document linkage through the SAME contract number within the same region (e.g. statement → payment)
CON_CC = defaultdict(set); CON_PRJ = defaultdict(set)
for i, rec in enumerate(REC):
    if not rec['con_status'].startswith('CONTRACT_IDENTIFIED') or rec['ev'] == 'FE-70': continue
    key = (s(g(ROWS[i], F.C_REG)), rec['con_value'])
    if rec['cc_direct'] and CAT[i] == 'EXP' and SIDE[i] == 'D': CON_CC[key].add(rec['cc_direct'])
    if rec['proj_status'] in ('PROJECT_IDENTIFIED_BUDGET_ROW', 'PROJECT_CANDIDATE_BUDGET_TYPE_UNDECIDED'): CON_PRJ[key].add((rec['proj_status'], rec['proj_value']))
for i, rec in enumerate(REC):
    if not rec['con_status'].startswith('CONTRACT_IDENTIFIED') or rec['ev'] == 'FE-70': continue
    key = (s(g(ROWS[i], F.C_REG)), rec['con_value'])
    if rec['cc_status'] in ('MISSING_EVIDENCE', 'CONDITIONAL_NOT_ESTABLISHED', 'AMBIGUOUS_ACTIVITY') and CON_CC.get(key):
        src = CON_CC[key]
        rec['cc_event'] = ' || '.join(sorted(src)); rec['cc_related'] = rec['cc_event']
        rec['cc_status'] = 'EVENT_LEVEL_VIA_CONTRACT' if len(src) == 1 else 'EVENT_LEVEL_VIA_CONTRACT_MULTI'
        rec['cc_basis'] = f'از ردیف هزینه همان قرارداد {rec["con_value"]} در منطقه {key[0]} (سند دیگر)'
    if rec['proj_status'] in ('NOT_INDICATED', 'PROJECT_INDICATED_NO_ID') and len(CON_PRJ.get(key, ())) == 1:
        st0, pv0 = next(iter(CON_PRJ[key]))
        rec['proj_status'] = st0 + '_VIA_CONTRACT'; rec['proj_value'] = pv0
print('contract linkage', round(time.time() - t0), flush=True)

for rec in REC:
    why = []
    if rec['status'] in ('AMBIGUOUS', 'INSUFFICIENT_EVIDENCE', 'REQUIRES_NEW_EVENT_REVIEW', 'MULTI_EVENT'): why.append(rec['status'])
    if rec['cc_status'] in ('DIRECT_LINE_NATIVE_REVENUE_FLAG', 'AMBIGUOUS_ACTIVITY', 'EVENT_LEVEL_MULTI_CC', 'EVENT_LEVEL_ACTIVITY_PROPOSED', 'PROPOSED_CC_ONLY',
                            'EVENT_LEVEL_VIA_CONTRACT', 'EVENT_LEVEL_VIA_CONTRACT_MULTI'): why.append('CC:' + rec['cc_status'])
    if rec.pop('_v4') == 'PROPOSED_ACTIVITY': why.append('CC:v4_PROPOSED_ACTIVITY')
    if rec['proj_status'].startswith(('PROJECT_CANDIDATE', 'UNKNOWN_BUDGET', 'PROJECT_INDICATED', 'PROJECT_MULTIPLE')) or rec['proj_status'].endswith('_VIA_CONTRACT'): why.append('PROJECT:' + rec['proj_status'])
    if rec['con_status'] == 'CONTRACT_MULTIPLE_FOR_COUNTERPARTY': why.append('CONTRACT:' + rec['con_status'])
    if not rec.pop('_bal'): why.append('سند نامتوازن')
    rec['review'] = 'بله' if why else 'خیر'
    rec['review_why'] = '؛ '.join(why)

pickle.dump(dict(REC=REC, REL=REL, DOCINFO=DOCINFO, EV=EV, CAT=CAT, SIDE=SIDE, DOCKEY=DOCKEY, CONTRACT=CONTRACT, BTYPE=BTYPE), open(W + 'classified.pkl', 'wb'))
st = Counter(r['status'] for r in REC)
print('status', st.most_common())
print('rel rows', len(REL))
print('cc', Counter(r['cc_status'] for r in REC).most_common())
print('contract', Counter(r['con_status'] for r in REC).most_common())
print('project', Counter(r['proj_status'] for r in REC).most_common())
print('bank', Counter(r['bank_status'] for r in REC).most_common())
print('secs', round(time.time() - t0))
