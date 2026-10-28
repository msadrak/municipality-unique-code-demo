"""v2 — audit tables, v1->v2 reconciliation, row-level change log and the semantic / relational QA tests.
Run with TT_VARIANT=v2 after 04, 05, 07, 09 (v2).  The v1 database (tt.sqlite) is ATTACHED read-only for the comparison; it is never modified.
"""
import sqlite3, sys, os, json, collections, re
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from rules import TT_EVENTS, TT_EVENTS_V1, EVENT_REVIEW, EVENT_STATUS_V2, EXCEPTION_TYPES
assert VARIANT == 'v2'

con = sqlite3.connect(DB, timeout=300)
con.execute(f"ATTACH DATABASE '{WORK}/tt.sqlite' AS v1")   # v1 scratch DB: read-only use
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone()
    return r[0] if r and r[0] is not None else 0
for t in ('event_review', 'event_crosswalk', 'cc_proposal_recon', 'cc_resolution', 'cc_coverage', 'change_log', 'doc_transitions', 'kpi_verification', 'terminal_agency'):
    cur.execute(f'DROP TABLE IF EXISTS {t}')
cur.execute('CREATE INDEX IF NOT EXISTS i_le_own ON line_event(own_event)'); cur.execute('CREATE INDEX IF NOT EXISTS i_lc_st ON line_cc(cc_status)')

# ================================================================================================ 1. semantic review of the 28 TT-NE candidates
cur.execute('''CREATE TABLE event_review(v1_id, v1_title, family, v1_definition, gap_link, related_fe, review_outcome, v2_id, lifecycle_attribute, reason, orgs, v1_driver_lines INT, v1_docs INT,
  v1_debit INT, v1_credit INT, account_chains, v1_composite_docs INT, atomicity, counterparty_semantics, overlap_notes, v2_lines INT, v2_docs INT, v2_status, expert_approval_needed)''')
SEM = {  # economic-substance / counterparty / overlap notes written from the document inspection (see corrective_audit_v2.md §4)
 'TT-NE-01': ('جریمه‌شونده: راننده/شرکت حمل‌ونقل؛ دریافت‌کننده: سازمان', 'FE-60 (بهای خدمات)، FE-61 (جرایم ساختمانی)'),
 'TT-NE-02': ('پرداخت‌کننده: شهرداری؛ دریافت‌کننده: سازمان', 'FE-69 (سمت پرداخت)'),
 'TT-NE-03': ('وجه‌دهنده: والدین/ثبت‌نام‌کنندگان از طریق سامانه؛ نگه‌دارنده: سازمان (عامل)', 'FE-68، FE-62 (استرداد عوارض)'),
 'TT-NE-04': ('دریافت‌کننده: شرکت‌های حمل‌ونقل مدارس / پیمانکاران ایاب‌وذهاب', 'FE-03 (پیمانکار)، FE-69'),
 'TT-NE-05': ('منبع: وجوه امانی سامانه؛ ذی‌نفع: سازمان', 'FE-60'),
 'TT-NE-06': ('بازگیرنده: ثبت‌نام‌کننده انصرافی', 'FE-62'), 'TT-NE-07': ('دریافت‌کننده: شرکت‌های حمل‌ونقل ویژه؛ منبع: شهرداری', 'FE-69، TT-NE-04'),
 'TT-NE-08': ('بانک', 'FE-65'), 'TT-NE-09': ('ذی‌نفع: رانندگان بخش خصوصی / شرکت بیمه', 'FE-51، FE-69'),
 'TT-NE-10': ('کارکنان', 'FE-44'), 'TT-NE-11': ('تأمین‌کننده/پیمانکار/سازمان وابسته (مبدأ بدهی نامعلوم در سند)', 'FE-03، FE-67'),
 'TT-NE-12': ('پیمانکار خدمات (انتظامات/نظافت/تأسیسات)، چاپخانه، تبلیغات', 'FE-03، FE-29، FE-45'),
 'TT-NE-13': ('بهره‌بردار غرفه/شرکت مسافربری (صادرکننده چک)', 'FE-60، FE-17'), 'TT-NE-14': ('همان چک‌ها', 'FE-60'),
 'TT-NE-15': ('بدهکار: بهره‌بردار/شرکت؛ بستانکار: شهرداری', 'FE-60'), 'TT-NE-17': ('بهره‌بردار غرفه', 'FE-17، FE-07'), 'TT-NE-18': ('بهره‌بردار غرفه', 'FE-18، FE-08'),
 'TT-NE-19': ('شهرداری', 'FE-68، FE-70'), 'TT-NE-21': ('انبار سازمان ← مصرف (به حساب شهرداری)', 'FE-22'), 'TT-NE-23': ('حسابداری (سیستمی)', 'FE-70'),
 'TT-NE-24': ('حسابداری/کارکنان/اداره دارایی', 'FE-50، FE-70'), 'TT-NE-26': ('تأمین‌کننده پذیرایی', 'FE-22، FE-51'), 'TT-NE-28': ('بانک/متفرقه', 'FE-65'),
 'TT-NE-29': ('تأمین‌کننده غیر پیمانکار', 'FE-01، FE-02'), 'TT-NE-30': ('تعاونی/صندوق قرض‌الحسنه', 'FE-48، FE-49'), 'TT-NE-32': ('خزانه شهرداری', 'FE-64'),
 'TT-NE-33': ('فروشنده ملک/زمین', 'FE-53، FE-23'), 'TT-NE-34': ('نامشخص (تا شناسایی)', 'FE-57..FE-62'),
}
rows = []
for vid, (outc, vid2, attr, reason) in EVENT_REVIEW.items():
    t = TT_EVENTS_V1[vid]
    n, nd, dr, cr, orgs = q("""SELECT count(*),count(DISTINCT doc_key),sum(amount_dr),sum(amount_cr),group_concat(DISTINCT org) FROM v1.line_event WHERE own_event=? AND role IN ('DRIVER','SETTLEMENT')""", vid)[0]
    docs = [r[0] for r in q("SELECT DISTINCT doc_key FROM v1.line_event WHERE own_event=? AND role IN ('DRIVER','SETTLEMENT')", vid)]
    ch = collections.Counter()
    for dk in docs:
        sig = tuple(sorted({f"{k}-{m}{'D' if b > 0 else 'C'}" for k, m, b in q('SELECT kol,moeen,bed FROM sanad WHERE doc_key=?', dk)}))
        ch[sig] += 1
    chains = ' | '.join(f"{c}× {' '.join(s)}" for s, c in ch.most_common(3))
    comp = one("SELECT count(*) FROM v1.doc_class WHERE outcome='COMPOSITE_TRANSACTION' AND doc_key IN (SELECT doc_key FROM v1.line_event WHERE own_event=?)", vid)
    succ = vid2.split(' ')[0] if vid2 and vid2.split(' ')[0] in (list(TT_EVENTS) + list(EXCEPTION_TYPES) + [f'FE-{i:02d}' for i in range(1, 71)]) else None
    if succ:
        v2n = one("SELECT count(*) FROM line_event WHERE own_event=? AND role IN ('DRIVER','SETTLEMENT')" + (" AND lifecycle_action=?" if attr and ' ' not in attr and '/' not in attr else ''), *( (succ, attr) if attr and ' ' not in attr and '/' not in attr else (succ,)))
        v2d = one("SELECT count(DISTINCT doc_key) FROM line_event WHERE own_event=? AND role IN ('DRIVER','SETTLEMENT')" + (" AND lifecycle_action=?" if attr and ' ' not in attr and '/' not in attr else ''), *( (succ, attr) if attr and ' ' not in attr and '/' not in attr else (succ,)))
    else: v2n = v2d = 0
    status = {'RETAIN_AS_NEW_EVENT': 'RETAINED_CANDIDATE', 'INSUFFICIENT_EVIDENCE': 'CANDIDATE_PENDING_EVIDENCE'}.get(outc, 'RETIRED_OR_NARROWED → ' + (vid2 or ''))
    need = 'نیاز به تصمیم کمیته رویداد' if outc in ('RETAIN_AS_NEW_EVENT', 'SPLIT_INTO_DISTINCT_EVENTS', 'INSUFFICIENT_EVIDENCE') else 'تأیید ادغام/چرخه‌عمر توسط کمیته رویداد'
    sem = SEM.get(vid, ('', ''))
    rows.append((vid, t[0], t[1], t[3], t[4], sem[1], outc, vid2, attr, reason, orgs, n, nd, dr or 0, cr or 0, chains, comp, 'ترکیبی (چندسطری، یک رویداد)' if comp > 0.3 * max(nd, 1) else 'اتمی در سطح سند', sem[0], t[6], v2n, v2d, status, need))
cur.executemany('INSERT INTO event_review VALUES(' + ','.join('?' * 24) + ')', rows)

# ================================================================================================ 2. event crosswalk (line level v1 -> v2)
cur.execute('''CREATE TABLE event_crosswalk AS SELECT coalesce(a.own_event,'—') v1_event, coalesce(b.own_event,'—') v2_event, coalesce(b.lifecycle_action,'') lifecycle_action, a.role v1_role, b.role v2_role,
  count(*) lines, count(DISTINCT a.doc_key) docs FROM v1.line_event a JOIN line_event b ON a.sid=b.sid WHERE coalesce(a.own_event,'—')<>coalesce(b.own_event,'—') OR a.role<>b.role GROUP BY 1,2,3,4,5''')

# ================================================================================================ 3. new-cost-center proposal reconciliation
cur.execute('''CREATE TABLE cc_proposal_recon(version, cc_id, metric, value_lines INT, value_docs INT, value_debit INT, value_credit INT, value_net INT, definition)''')
def popul(db, cid, kind):
    pre = f'{db}.' if db else ''
    if kind == 'DIRECT': cond = f"c.cc_status IN ('NEW_CC_CANDIDATE','PROVISIONAL_EXISTING_CC') AND c.cc_id=?"; args = (cid,)
    elif kind == 'AMBIGUOUS': cond = f"c.cc_status='MULTIPLE_CC_CANDIDATES' AND (c.cc_id=? OR ';'||c.alt_ccs||';' LIKE ?)"; args = (cid, f'%;{cid};%')
    elif kind == 'REPORTED_V1': cond = "c.cc_id=?"; args = (cid,)
    elif kind == 'ALT_OF_SELECTED': cond = f"c.cc_status IN ('NEW_CC_CANDIDATE','PROVISIONAL_EXISTING_CC') AND ';'||c.alt_ccs||';' LIKE ? AND coalesce(c.cc_id,'')<>?"; args = (f'%;{cid};%', cid)
    return q(f"SELECT count(*),count(DISTINCT c.doc_key),coalesce(sum(s.bed),0),coalesce(sum(s.bes),0),coalesce(sum(s.bed-s.bes),0) FROM {pre}line_cc c JOIN sanad s ON s.sid=c.sid WHERE {cond}", *args)[0]
DEFS = {'DIRECT': 'Direct_Assignment: status ∈ {NEW_CC_CANDIDATE, PROVISIONAL_EXISTING_CC} and the proposal is the SELECTED center',
        'AMBIGUOUS': 'Ambiguous_Candidate: status = MULTIPLE_CC_CANDIDATES and the proposal is among the candidates (v1: also when it was listed first)',
        'EVIDENCE_SUPPORT': 'Evidence_Support = Direct_Assignment + Ambiguous_Candidate (records that support the concept; not all are assigned)',
        'REPORTED_V1': 'v1 sheet metric «ردیف‌های مستقیماً نگاشت‌شده» = every row whose cc_id column equals the proposal, regardless of status (mixed population — root cause)',
        'ALT_OF_SELECTED': 'Rows where another center was selected but the proposal is listed as alternative'}
for ver, db in (('v1', 'v1'), ('v2', '')):
    for cid in ('TTCC-P-01', 'TTCC-P-02', 'TTCC-P-03'):
        d, a = popul(db, cid, 'DIRECT'), popul(db, cid, 'AMBIGUOUS')
        for kind, vals in (('DIRECT', d), ('AMBIGUOUS', a), ('REPORTED_V1', popul(db, cid, 'REPORTED_V1')), ('ALT_OF_SELECTED', popul(db, cid, 'ALT_OF_SELECTED'))):
            cur.execute('INSERT INTO cc_proposal_recon VALUES(?,?,?,?,?,?,?,?,?)', (ver, cid, kind, *vals, DEFS[kind]))
        # evidence support (distinct sids)
        pre = f'{db}.' if db else ''
        ev = q(f"""SELECT count(*),count(DISTINCT c.doc_key),coalesce(sum(s.bed),0),coalesce(sum(s.bes),0),coalesce(sum(s.bed-s.bes),0) FROM {pre}line_cc c JOIN sanad s ON s.sid=c.sid
                   WHERE (c.cc_status IN ('NEW_CC_CANDIDATE','PROVISIONAL_EXISTING_CC') AND c.cc_id=?) OR (c.cc_status='MULTIPLE_CC_CANDIDATES' AND (c.cc_id=? OR ';'||c.alt_ccs||';' LIKE ?))""", cid, cid, f'%;{cid};%')[0]
        cur.execute('INSERT INTO cc_proposal_recon VALUES(?,?,?,?,?,?,?,?,?)', (ver, cid, 'EVIDENCE_SUPPORT', *ev, DEFS['EVIDENCE_SUPPORT']))
# lines previously directly assigned to a retired/changed proposal and where they went
cur.execute('''CREATE TABLE IF NOT EXISTS cc_proposal_moves AS SELECT a.cc_id v1_cc, a.cc_status v1_status, b.cc_status v2_status, coalesce(b.cc_id,'') v2_cc, b.alt_ccs v2_candidates, count(*) lines,
  sum(s.bed-s.bes) net FROM v1.line_cc a JOIN line_cc b ON a.sid=b.sid JOIN sanad s ON s.sid=a.sid WHERE a.cc_id LIKE 'TTCC-P-%' AND (coalesce(a.cc_id,'')<>coalesce(b.cc_id,'') OR a.cc_status<>b.cc_status) GROUP BY 1,2,3,4,5''')

# ================================================================================================ 4. resolution of the 5,409 unresolved v1 rows + coverage
cur.execute('''CREATE TABLE cc_resolution AS
 SELECT a.sid, a.org, a.fy, a.doc_key, ea.own_event v1_event, eb.own_event v2_event, a.cc_status prev_status, trim(coalesce(a.cc_id,'')||';'||coalesce(a.alt_ccs,''),';') prev_candidates,
        b.cc_status new_status, coalesce(b.cc_id,'') new_selected_cc, coalesce(b.alt_ccs,'') new_candidates, b.basis evidence, b.rule_id rule, b.conf confidence,
        CASE WHEN b.cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') THEN 'RESOLVED_PROVISIONALLY' WHEN b.cc_status='CC_NOT_APPLICABLE' THEN 'NO_LONGER_ELIGIBLE' ELSE 'STILL_UNRESOLVED' END resolution,
        CASE WHEN b.cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') AND b.conf='LOW' THEN 'نیازمند بازبینی کارشناس' WHEN b.cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') THEN 'بازبینی نمونه‌ای' ELSE 'نیازمند تصمیم/داده' END expert_review,
        s.bed - s.bes net_value
 FROM v1.line_cc a JOIN line_cc b ON a.sid=b.sid JOIN v1.line_event ea ON ea.sid=a.sid JOIN line_event eb ON eb.sid=a.sid JOIN sanad s ON s.sid=a.sid
 WHERE a.cc_status IN ('MULTIPLE_CC_CANDIDATES','INSUFFICIENT_INFORMATION')''')
cur.execute('''CREATE TABLE cc_coverage(version, org, fy, eligible_lines INT, selected_lines INT, multiple_lines INT, insufficient_lines INT, eligible_value INT, selected_value INT, multiple_value INT, insufficient_value INT)''')
for ver, pre in (('v1', 'v1.'), ('v2', '')):
    for org in ORGS:
        for fy in YEARS + ('ALL',):
            f = '' if fy == 'ALL' else f" AND c.fy='{fy}'"
            def agg(statuses):
                st = ','.join(f"'{x}'" for x in statuses)
                return q(f"SELECT count(*),coalesce(sum(s.bed-s.bes),0) FROM {pre}line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.org=? AND c.eligible=1 AND c.cc_status IN ({st}){f}", org)[0]
            e, sel, mu, ins = agg(('PROVISIONAL_EXISTING_CC', 'NEW_CC_CANDIDATE', 'MULTIPLE_CC_CANDIDATES', 'INSUFFICIENT_INFORMATION', 'EXACT_EXISTING_CC')), agg(('PROVISIONAL_EXISTING_CC', 'NEW_CC_CANDIDATE')), agg(('MULTIPLE_CC_CANDIDATES',)), agg(('INSUFFICIENT_INFORMATION',))
            cur.execute('INSERT INTO cc_coverage VALUES(?,?,?,?,?,?,?,?,?,?,?)', (ver, org, fy, e[0], sel[0], mu[0], ins[0], e[1], sel[1], mu[1], ins[1]))

# ================================================================================================ 5. row-level change log
cur.execute('''CREATE TABLE change_log(source_record_id, organization, fiscal_year, original_document_ref, field_changed, old_value, new_value, reason, supporting_evidence, rule_or_code_path, confidence, governance_effect)''')
EVR = {k: v for k, v in EVENT_REVIEW.items()}
doc_kind_changed = {r[0]: (r[1], r[2]) for r in q("SELECT a.doc_key,a.kind,b.kind FROM v1.doc_class a JOIN doc_class b ON a.doc_key=b.doc_key WHERE a.kind<>b.kind")}
rows = q("""SELECT a.sid,a.org,a.fy,a.doc_key,ea.role,eb.role,ea.own_event,eb.own_event,ea.outcome,eb.outcome,eb.lifecycle_action,eb.rule_id,eb.conf,eb.basis,
            ca.cc_status,cb.cc_status,coalesce(ca.cc_id,''),coalesce(cb.cc_id,''),coalesce(ca.alt_ccs,''),coalesce(cb.alt_ccs,''),cb.rule_id,cb.basis,cb.conf,ca.eligible,cb.eligible
            FROM v1.line_cc ca JOIN line_cc cb ON ca.sid=cb.sid JOIN v1.line_event ea ON ea.sid=ca.sid JOIN line_event eb ON eb.sid=ca.sid JOIN v1.line_cc a ON a.sid=ca.sid""")
out = []
def log(sid, org, fy, dk, field, old, new, reason, ev, rule, conf, gov): out.append((sid, org, fy, dk, field, old, new, reason, ev, rule, conf, gov))
for (sid, org, fy, dk, rA, rB, eA, eB, oA, oB, act, ruleE, confE, basisE, sA, sB, cA, cB, altA, altB, ruleC, basisC, confC, elA, elB) in rows:
    ref = f"{ORGS[org][1]}/{fy}/Sanad.xlsx#{sid.split('-S-')[1].lstrip('0')}|{dk}"
    if dk in doc_kind_changed and (eA != eB or oA != oB or rA != rB):
        log(sid, org, fy, ref, 'doc_kind', *doc_kind_changed[dk], 'v1 treated every «بستن حساب» text as inter-entity settlement; v2 separates bonus / school pre-receipt recognition / P&L-to-retained-earnings', f'doc {dk}', '04_classify_events.doc_kind (R_BONUS_CLOSE, R_PREREC_CLOSE, R_PL_TO_RE)', 'HIGH', 'PROPOSED → PROPOSED (reclassified)')
    if (eA or '') != (eB or ''):
        rv = EVR.get(eA)
        reason = (f"{rv[0]}: {rv[3]}" if rv else 'قاعده متنی/زیرحساب بازنگری‌شده (مثلاً اجزای حقوق، حواله انبار، چک)') if eA else 'رویداد پیشتر مبهم بود و با شاهد بیشتر تعیین شد'
        log(sid, org, fy, ref, 'own_event', eA or '', eB or '', reason, (basisE or '')[:200], f"{ruleE or ''} / v2_adjust" + (f" [{act}]" if act else ''), confE, 'PROPOSED → PROPOSED; no approval implied')
    if rA != rB: log(sid, org, fy, ref, 'line_role', rA, rB, 'نقش سطر در سند پس از بازنگری رویداد/نوع سند', '', 'driver-class selection (04)', confE, 'PROPOSED → PROPOSED')
    if oA != oB and (eA or '') == (eB or ''): log(sid, org, fy, ref, 'event_outcome', oA, oB, 'تغییر وضعیت طبقه‌بندی همان رویداد', '', ruleE, confE, 'PROPOSED → PROPOSED')
    if act: log(sid, org, fy, ref, 'lifecycle_action', '', act, 'افزوده شدن ویژگی چرخه‌عمر (به‌جای رویداد جداگانه)', '', 'rules.EVENT_REVIEW', confE, 'PROPOSED')
    if sA != sB: log(sid, org, fy, ref, 'cc_status', sA, sB, 'نتیجه دور دوم تفکیک مرکز هزینه / اصلاح تعریف مراکز پیشنهادی', (basisC or '')[:200], ruleC, confC, 'PROPOSED → PROPOSED' + ('; ابهام کاهش یافت' if sA in ('MULTIPLE_CC_CANDIDATES', 'INSUFFICIENT_INFORMATION') and sB in ('PROVISIONAL_EXISTING_CC', 'NEW_CC_CANDIDATE') else ''))
    if cA != cB: log(sid, org, fy, ref, 'cc_id_selected', cA, cB, 'در v1 ستون cc_id برای ردیف‌های MULTIPLE نامزد اول را نگه می‌داشت؛ در v2 فقط مرکز انتخاب‌شده' if sA == 'MULTIPLE_CC_CANDIDATES' else 'تغییر مرکز انتخاب‌شده', (basisC or '')[:200], ruleC, confC, 'PROPOSED → PROPOSED')
    if altA != altB and sA == sB: log(sid, org, fy, ref, 'cc_candidates', altA, altB, 'حذف TTCC-P-02/03 از نامزدها یا تغییر نامزدها', (basisC or '')[:200], ruleC, confC, 'PROPOSED → PROPOSED')
cur.executemany('INSERT INTO change_log VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', out)
cur.execute('''CREATE TABLE doc_transitions AS SELECT a.outcome v1_outcome, b.outcome v2_outcome, count(*) docs, sum(b.bed_total) bed_total FROM v1.doc_class a JOIN doc_class b ON a.doc_key=b.doc_key GROUP BY 1,2''')

# ================================================================================================ 6. Terminals agency evidence (flows and balances by account group)
cur.execute('''CREATE TABLE terminal_agency(section, fy, doc_kind, account_group, account_title, debit INT, credit INT, lines INT, example_docs)''')
names = {(k, m, t): n for k, m, t, n in q("SELECT kol,moeen,taf1,name FROM hesab WHERE org='Terminals' AND fy='1404' AND level=3")}
for fy in YEARS:
    for k, m, t, kind, dr, cr, n in q("""SELECT s.kol,s.moeen,s.taf1,d.kind,sum(s.bed),sum(s.bes),count(*) FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Terminals' AND s.fy=? AND
        ((s.kol='113' AND s.moeen='1') OR (s.kol='211' AND s.moeen='1') OR (s.kol='212' AND s.moeen='6')) GROUP BY 1,2,3,4 ORDER BY 1,2,3,4""", fy):
        ex = ','.join(r[0] for r in q("SELECT DISTINCT s.doc_key FROM sanad s JOIN doc_class d ON d.doc_key=s.doc_key WHERE s.org='Terminals' AND s.fy=? AND s.kol=? AND s.moeen=? AND s.taf1=? AND d.kind=? LIMIT 2", fy, k, m, t, kind))
        cur.execute('INSERT INTO terminal_agency VALUES(?,?,?,?,?,?,?,?,?)', ('FLOW_BY_ACCOUNT_GROUP', fy, kind, f'{k}-{m}-{t}', names.get((k, m, t), ''), dr, cr, n, ex))
con.commit()
print('event_review', one('SELECT count(*) FROM event_review'), 'change_log', one('SELECT count(*) FROM change_log'), 'cc_resolution', one('SELECT count(*) FROM cc_resolution'))
for r in q('SELECT version,cc_id,metric,value_lines,value_net FROM cc_proposal_recon ORDER BY version,cc_id,metric'): print(r)
for r in q("SELECT version,org,fy,eligible_lines,selected_lines,multiple_lines,insufficient_lines,eligible_value,selected_value FROM cc_coverage WHERE fy='ALL'"): print(r)
for r in q('SELECT resolution,count(*) FROM cc_resolution GROUP BY 1'): print(r)
for r in q('SELECT v1_outcome,v2_outcome,docs FROM doc_transitions WHERE v1_outcome<>v2_outcome ORDER BY docs DESC LIMIT 12'): print(r)
