"""v2.1 corrective pass (TT_VARIANT=v21).  Starts from a FRESH copy of tt_v2.sqlite (reproducible, v2 is never modified) and applies:
  S1  metadata: duplicate KPI definition row (TM-K15) removed + unique index
  S2  privacy: bank-account numbers / IBANs in account titles masked (originals kept in account_dictionary_restricted)
  S3  low-confidence cost-center audit (rule-level decisions, row-level audit table, change log, deterministic stratified sample)
  S4  FE-70 semantic correction (depreciation -> PEO-01, provision recognition -> PEO-02, utilisation of provisions -> TT-NE-11)
  S5  population bridge v2 -> v2.1 and coverage-by-confidence tables
Outputs are SQLite tables in tt_v21.sqlite; 08/16-series builders read them.
"""
import sqlite3, sys, os, json, shutil, random, re, collections, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from common import *
from audit_rules_v21 import decide, group_of, N
assert VARIANT == 'v21'
SRC_DB = f'{WORK}/tt_v2.sqlite'
if os.path.exists(DB): os.remove(DB)
shutil.copy(SRC_DB, DB)
con = sqlite3.connect(DB, timeout=300)
con.execute(f"ATTACH DATABASE '{WORK}/tt_v2.sqlite' AS v2")
con.execute(f"ATTACH DATABASE '{WORK}/tt.sqlite' AS v1")
cur = con.cursor()
q = lambda s, *a: cur.execute(s, a).fetchall()
def one(s, *a):
    r = cur.execute(s, a).fetchone(); return r[0] if r and r[0] is not None else 0

cur.execute('DROP TABLE IF EXISTS change_log_v21')
cur.execute('''CREATE TABLE change_log_v21(change_id, change_class, source_record_id, organization, fiscal_year, source_document, affected_component, v2_value, v21_value, reason, evidence, rule_change, confidence_change, qa_reference, governance_impact)''')
_n = [0]
def log(cls, sid, org, fy, doc, comp, old, new, reason, evidence='', rule='', conf='', qa='', gov='PROPOSED → PROPOSED (not approved)'):
    _n[0] += 1
    cur.execute('INSERT INTO change_log_v21 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (f'CHG21-{_n[0]:06d}', cls, sid, org, fy, doc, comp, old, new, reason, evidence, rule, conf, qa, gov))

# ------------------------------------------------------------------------------------------------ S1 KPI metadata
dups = q('SELECT kpi_id,count(*) FROM kpi_catalogue GROUP BY 1 HAVING count(*)>1')
cur.execute('DELETE FROM kpi_catalogue WHERE rowid NOT IN (SELECT min(rowid) FROM kpi_catalogue GROUP BY kpi_id)')
cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS u_kpi_catalogue ON kpi_catalogue(kpi_id)')
for k, n in dups:
    log('METADATA', '', '', '', '', f'KPI_Catalogue:{k}', f'{n} rows', '1 row', 'ردیف تکراری تعریف KPI (INSERT OR REPLACE روی جدول بدون کلید یکتا در اجرای مکرر 15_kpi_qa_v2.py) باعث شمارش ۴ KPI تأییدشده برای پایانه‌ها و ۳۲ تعریف به‌جای ۳۱ شده بود',
        'kpi_catalogue: 32 rows, 31 distinct kpi_id', 'unique index u_kpi_catalogue', '', 'QA_KPI_UNIQUE_IDENTITY', 'none')

# ------------------------------------------------------------------------------------------------ S2 privacy masking of titles
def mask_text(t):
    if not t: return t
    t2 = re.sub(r'IR\s?\d{2}[\d\s]{8,}', 'IR••••••••', t, flags=re.I)
    return re.sub(r'\d{6,}', lambda m: '•' * (len(m.group()) - 3) + m.group()[-3:], t2)
cur.execute('DROP TABLE IF EXISTS account_dictionary_restricted')
cur.execute('CREATE TABLE account_dictionary_restricted AS SELECT org,fy,hcode,title FROM account_dictionary')
masked = 0
for hid, t in q('SELECT hid,title FROM account_dictionary'):
    m = mask_text(t)
    if m != t: cur.execute('UPDATE account_dictionary SET title=?,title_norm=? WHERE hid=?', (m, m, hid)); masked += 1
for tab, cols in (('account_crosswalk', ('org_title',)), ('account_divergence', ('title_a', 'title_b'))):
    for c in cols:
        for rid, t in q(f'SELECT rowid,{c} FROM {tab}'):
            m = mask_text(t)
            if m != t: cur.execute(f'UPDATE {tab} SET {c}=? WHERE rowid=?', (m, rid))
log('PRIVACY', '', '', '', '', 'account_dictionary.title / account_crosswalk.org_title / account_divergence.title_*', 'full digit strings (bank account numbers, IBAN)', 'masked (••• + last 3 digits)', f'{masked} عنوان حساب دارای شماره حساب بانکی/شبا ماسک شد؛ کد حسابداری سلسله‌مراتبی (مثل ۱۱۳-۱-۱) ماسک نشد', 'regex \\d{6,} / IR\\d{2}…', 'mask_text()', '', 'QA_PRIVACY_CLIENT_PACKAGE', 'none')

# ------------------------------------------------------------------------------------------------ S3 low-confidence audit
for col in ('v21_decision TEXT', 'v21_note TEXT'):
    try: cur.execute(f'ALTER TABLE line_cc ADD COLUMN {col}')
    except sqlite3.OperationalError: pass
pop = q("""SELECT r.sid,r.org,r.fy,r.doc_key,r.prev_status,r.prev_candidates,c.cc_status,c.cc_id,c.alt_ccs,c.conf,c.rule_id,c.basis,c.source_markaz,c.source_unit,c.activity_id,
                  s.src_row,s.sanad_num,s.hcode,s.bed,s.bes,s.sharh,coalesce(a.title,''),coalesce(e.own_event,''),coalesce(e.rule_id,''),s.date,r.evidence
           FROM cc_resolution r JOIN line_cc c ON c.sid=r.sid JOIN sanad s ON s.sid=r.sid JOIN line_event e ON e.sid=r.sid
           LEFT JOIN account_dictionary_restricted a ON a.org=s.org AND a.fy=s.fy AND a.hcode=s.hcode
           WHERE r.resolution='RESOLVED_PROVISIONALLY' AND r.confidence='LOW' AND c.conf='LOW' AND c.cc_status='PROVISIONAL_EXISTING_CC' ORDER BY s.src_row, r.org, r.fy""")
assert len(pop) == 1016, len(pop)
cur.execute('DROP TABLE IF EXISTS low_audit')
cur.execute('''CREATE TABLE low_audit(source_record_id, organization, fiscal_year, document_key, sanad_num, account_code, source_activity_code, source_unit, existing_activity_id, previous_v1_status, previous_v1_candidates,
    v2_status, v2_cc, v2_confidence, v2_rule_id, v2_reason, v2_candidates, event_v2, event_rule, amount_net, rule_group, audit_layer, audit_decision, v21_status, v21_cc, v21_confidence, v21_candidates, audit_reason, audit_evidence, sample_flag)''')
GROUPNAME = {'S': 'S انبار (حواله خروج کالا)', 'E': 'E پیش‌فرض رویداد FE-22', 'K': 'K واژهٔ کلیدی قاعده فعالیت‌محور شهرداری', 'F': 'F شاهد محلی (پایانه)', 'O': 'O سایر'}
rows_out = []
for p in pop:
    (sid, org, fy, dk, pst, pcand, st, cc, alts, conf, rule, basis, mz, unit, act, srow, num, hc, bed, bes, sharh, atitle, own, erule, date, ev) = p
    rec = dict(org=org, cc=cc, T=N(sharh), A=N(atitle), event=own, basis=basis, rule_id=rule)
    dec, nst, ncc, nconf, nalts, reason, evid = decide(rec)
    g = group_of(rec)
    if nst == 'MULTIPLE_CC_CANDIDATES' and len(set(nalts)) < 2:     # a MULTIPLE status needs >=2 candidates (QA_CC_CANDIDATE_VS_SELECTED)
        if nalts and nalts[0] == cc: dec, nst, ncc, nconf, nalts = 'RETAIN_LOW_CONFIDENCE', 'PROVISIONAL_EXISTING_CC', cc, 'LOW', []
        else: dec, nst, ncc, nconf = 'RECLASSIFY_TO_INSUFFICIENT_INFORMATION', 'INSUFFICIENT_INFORMATION', None, 'LOW'
    nal = ';'.join(nalts)
    rows_out.append((sid, org, fy, dk, num, hc, mz, unit, act, pst, pcand, st, cc, conf, rule, basis, alts, own, erule, (bed or 0) - (bes or 0), g, 'LAYER1_RULE_LEVEL', dec, nst, ncc, nconf, nal, reason, evid, 0))
    changed = (nst != st) or (ncc != cc) or (nconf != conf) or (nal != (alts or ''))
    cur.execute('UPDATE line_cc SET v21_decision=?, v21_note=? WHERE sid=?', (dec, reason, sid))
    if changed:
        code = {'UPGRADE_TO_MEDIUM_WITH_EVIDENCE': 'UPG', 'RECLASSIFY_TO_MULTIPLE_CANDIDATES': 'MULT', 'RECLASSIFY_TO_INSUFFICIENT_INFORMATION': 'INSUF'}.get(dec, 'OTH')
        cur.execute('UPDATE line_cc SET cc_status=?, cc_id=?, alt_ccs=?, conf=?, rule_id=?, basis=?, review=1 WHERE sid=?',
                    (nst, ncc, nal, nconf, f'V21-{g}-{code}', f'[v2.1 audit] {reason}', sid))
        if nst != st: log('CLASSIFICATION', sid, org, fy, dk, 'line_cc.cc_status', st, nst, reason, evid, f'{rule} → V21-{g}-{code}', f'{conf}→{nconf}', 'QA_LOW_CONFIDENCE_AUDIT_COMPLETENESS')
        if ncc != cc: log('CLASSIFICATION', sid, org, fy, dk, 'line_cc.cc_id_selected', cc or '', ncc or '', reason, evid, f'{rule} → V21-{g}-{code}', f'{conf}→{nconf}', 'QA_CC_ASSIGNMENT_UNIQUENESS')
        if nal != (alts or ''): log('CLASSIFICATION', sid, org, fy, dk, 'line_cc.candidates', alts or '', nal, reason, evid, f'{rule} → V21-{g}-{code}', f'{conf}→{nconf}', 'QA_CC_CANDIDATE_VS_SELECTED')
        if nconf != conf: log('CLASSIFICATION', sid, org, fy, dk, 'line_cc.confidence', conf, nconf, reason, evid, f'{rule} → V21-{g}-{code}', f'{conf}→{nconf}', 'QA_CC_UPGRADE_EVIDENCE')
cur.executemany('INSERT INTO low_audit VALUES(' + ','.join('?' * 30) + ')', rows_out)

# deterministic stratified sample (seed fixed); manual verdicts merged from audit_samples_v21.json when present
random.seed(20260301)
strata = collections.defaultdict(list)
for r in rows_out: strata[(r[1], r[2], r[22], r[20])].append(r)
sample = []
for k in sorted(strata):
    rs = sorted(strata[k], key=lambda r: (-abs(r[19]), r[0]))
    pick = [rs[0]]                                  # materiality: largest absolute value in the stratum
    rest = rs[1:]
    nrand = 1 + (1 if len(strata[k]) >= 40 else 0) + (1 if len(strata[k]) >= 150 else 0)
    pick += random.sample(rest, min(nrand, len(rest)))
    for r in pick: sample.append((k, r))
cur.execute('DROP TABLE IF EXISTS low_sample')
cur.execute('CREATE TABLE low_sample(source_record_id, organization, fiscal_year, stratum, rule_group, audit_decision, v21_status, v21_cc, amount_net, sample_reason, reviewer_verdict, reviewer_note)')
_r2p = f'{WORK}/audit_samples_v21_round2.json'
VER = {}
if os.path.exists(_r2p):      # the round-2 sample (54 records, deterministic from seed 20260301 on the round-2 rule set) is frozen; verdicts were assigned by manual review
    R2 = json.load(open(_r2p, encoding='utf8'))
    VER = {k: v[:2] for k, v in R2.items()}
    sample = [(('R2',), r) for r in rows_out if r[0] in R2]
for k, r in sample:
    v = VER.get(r[0], ['NOT_YET_REVIEWED', ''])
    cur.execute('INSERT INTO low_sample VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (r[0], r[1], r[2], f'{r[1]}|{r[2]}|{r[22]}|{GROUPNAME[r[20]][:1]}', r[20], r[22], r[23], r[24], r[19], 'round-2 frozen stratified sample (seed 20260301; largest value + seeded random per stratum)', v[0], v[1]))
    cur.execute('UPDATE low_audit SET sample_flag=1 WHERE source_record_id=?', (r[0],))
cur.execute('DROP TABLE IF EXISTS low_sample_round1')
cur.execute('CREATE TABLE low_sample_round1(source_record_id, decision_at_round1, reviewer_verdict, reviewer_note, current_decision, current_cc_or_candidates)')
_r1p = f'{WORK}/audit_samples_v21_round1.json'
if os.path.exists(_r1p):
    for sid_, (vd, nt, d0) in json.load(open(_r1p, encoding='utf8')).items():
        cu = q('SELECT audit_decision,coalesce(v21_cc,\'\')||CASE WHEN v21_candidates<>\'\' THEN \' [\'||v21_candidates||\']\' ELSE \'\' END FROM low_audit WHERE source_record_id=?', sid_)
        cur.execute('INSERT INTO low_sample_round1 VALUES(?,?,?,?,?,?)', (sid_, d0, vd, nt, cu[0][0] if cu else '', cu[0][1] if cu else ''))
cur.execute('DROP TABLE IF EXISTS low_postfix_changes')
cur.execute('CREATE TABLE low_postfix_changes(source_record_id, organization, prev_decision, prev_cc, prev_candidates, new_decision, new_cc, new_candidates, amount_net, reviewer_verdict, reviewer_note)')
_pp = f'{WORK}/low_audit_prev_round2.json'
if os.path.exists(_pp):
    PREV = json.load(open(_pp, encoding='utf8'))
    PFV = json.load(open(f'{WORK}/audit_postfix_v21.json', encoding='utf8')) if os.path.exists(f'{WORK}/audit_postfix_v21.json') else {}
    with open(f'{WORK}/low_postfix_review_v21.txt', 'w', encoding='utf8') as fpf:
        for r in rows_out:
            pv = PREV.get(r[0])
            if pv and (pv[0], pv[1], pv[2]) != (r[22], r[24] or '', r[26]):
                v = PFV.get(r[0], ['NOT_YET_REVIEWED', ''])
                cur.execute('INSERT INTO low_postfix_changes VALUES(?,?,?,?,?,?,?,?,?,?,?)', (r[0], r[1], pv[0], pv[1], pv[2], r[22], r[24] or '', r[26], r[19], v[0], v[1]))
                sh = q('SELECT sharh FROM sanad WHERE sid=?', r[0])[0][0] or ''
                fpf.write(f'{r[0]}|{r[22]}|{r[24] or r[26]}|{r[19]}|{sh[:100]}\n')
cur.execute('DROP TABLE IF EXISTS low_sample_round1_dummy')
# sample dump for the reviewer (narration kept in the work dir only, never in deliverables)
with open(f'{WORK}/low_sample_review_v21.txt', 'w', encoding='utf8') as f:
    for k, r in sample:
        s = q('SELECT sharh,des FROM sanad WHERE sid=?', r[0])[0]
        f.write(f"{r[0]}|{r[1]}|G{r[20]}|{r[22]}|{r[12]}→{r[24] or r[26]}|{r[19]}|{(q('SELECT title FROM account_dictionary_restricted a JOIN sanad x ON x.org=a.org AND x.fy=a.fy AND x.hcode=a.hcode WHERE x.sid=?', r[0]) or [('',)])[0][0][:28]}|{(s[0] or '')[:110]}\n")

# rule-level analysis
cur.execute('DROP TABLE IF EXISTS low_rule_analysis')
cur.execute('''CREATE TABLE low_rule_analysis(organization, rule_group, v2_cc, v2_rule_id, lines, abs_value, share_of_org_low_value, retained_low, upgraded_medium, to_multiple, to_insufficient, other, finding)''')
FINDINGS = {'S': 'انبار: عنوان حساب تفصیلی تفکیک‌کنندهٔ مصرفی/سرمایه‌ای است؛ مصرف‌کنندهٔ نهایی در سند نیست',
            'E': 'پیش‌فرض FE-22→CC-1403 («ملزومات») برای پذیرایی/مراسم/هدایا از نظر معنایی پشتیبانی نمی‌شود',
            'K': 'واژهٔ کلیدی تنها؛ برخورد واژگانی (رول‌پلاک/پلاک، لکه‌گیری، سامانه هوشمند، حراست، تبلیغات، پارکینگ، زباله) مشاهده شد',
            'F': 'شاهد محلی؛ ماهیت تعیین‌کننده نیست مگر تأسیسات', 'O': '—'}
tot = {o: sum(abs(r[19]) for r in rows_out if r[1] == o) for o in ORGS}
agg = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])
for r in rows_out:
    a = agg[(r[1], r[20], r[12], r[14])]; a[0] += 1; a[1] += abs(r[19])
    a[{'RETAIN_LOW_CONFIDENCE': 2, 'UPGRADE_TO_MEDIUM_WITH_EVIDENCE': 3, 'RECLASSIFY_TO_MULTIPLE_CANDIDATES': 4, 'RECLASSIFY_TO_INSUFFICIENT_INFORMATION': 5}.get(r[22], 6)] += 1
for (o, g, cc, rl), a in sorted(agg.items(), key=lambda x: -x[1][1]):
    cur.execute('INSERT INTO low_rule_analysis VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (o, GROUPNAME[g], cc, rl, a[0], a[1], a[1] / tot[o] if tot[o] else 0, a[2], a[3], a[4], a[5], a[6], FINDINGS[g]))

# ------------------------------------------------------------------------------------------------ S4 FE-70 semantic correction
for col in ('v2_event TEXT', 'v2_lifecycle TEXT'):
    try: cur.execute(f'ALTER TABLE line_event ADD COLUMN {col}')
    except sqlite3.OperationalError: pass
cur.execute('UPDATE line_event SET v2_event=own_event, v2_lifecycle=lifecycle_action')
fl = q("""SELECT e.sid,e.doc_key,e.org,e.fy,e.acat,e.role,e.lifecycle_action,s.bed,s.bes FROM line_event e JOIN sanad s ON s.sid=e.sid
          WHERE e.own_event='FE-70' AND e.lifecycle_action IN ('DEPRECIATION','PROVISION_OR_ACCRUAL')""")
fe70 = []
for sid, dk, org, fy, acat, role, la, bed, bes in fl:
    if la == 'DEPRECIATION': ne, nl = 'PEO-01', 'DEPRECIATION_RECOGNITION'
    elif (bes or 0) > (bed or 0): ne, nl = 'PEO-02', 'PROVISION_ACCRUAL_RECOGNITION'
    else: ne, nl = 'TT-NE-11', 'SETTLE_ACCRUED_LIABILITY'
    cur.execute('UPDATE line_event SET own_event=?, event_id=?, lifecycle_action=?, review=1 WHERE sid=?', (ne, ne, nl, sid))
    why = {'PEO-01': 'استهلاک دوره‌ای = ثبت تعدیلی پایان دوره (بدهکار هزینه استهلاک / بستانکار استهلاک انباشته)؛ نه اصلاح سند، نه بستن حساب، نه انتقال مانده؛ تعریف FE-70 آن را پوشش نمی‌دهد',
           'PEO-02': 'شناسایی ذخیره/هزینه تعهدی (بستانکار حساب ذخیره): عملیات تعدیلی پایان دوره، خارج از تعریف FE-70',
           'TT-NE-11': 'بدهکار حساب ذخیره در مقابل بانک = تسویه/پرداخت بدهی تعهدی (مصرف ذخیره)، نه شناسایی ذخیره'}[ne]
    log('ACCOUNTING_INTERPRETATION', sid, org, fy, dk, 'line_event.assigned_event', f'FE-70 [{la}]', f'{ne} [{nl}]', why, f'acat={acat}, Dr={bed}, Cr={bes}', 'v2: TT-NE-23/24→FE-70  ⇒  v2.1: ' + ne, '', 'QA_FE70_SEMANTICS', 'event reclassified; still PROPOSED')
    fe70.append((sid, dk, org, fy, acat, role, la, ne, nl, bed or 0, bes or 0))
cur.execute('DROP TABLE IF EXISTS fe70_review')
cur.execute('CREATE TABLE fe70_review(sid, doc_key, org, fy, acat, role, v2_lifecycle, v21_event, v21_lifecycle, debit, credit)')
cur.executemany('INSERT INTO fe70_review VALUES(?,?,?,?,?,?,?,?,?,?,?)', fe70)
# document level: recompute driver_events for affected docs and fix primary event
aff = sorted({r[1] for r in fe70})
for dk in aff:
    evs = [r[0] for r in q("SELECT DISTINCT own_event FROM line_event WHERE doc_key=? AND role='DRIVER' AND own_event IS NOT NULL ORDER BY own_event", dk)]
    old = q('SELECT primary_event,driver_events FROM doc_class WHERE doc_key=?', dk)[0]
    newde = json.dumps(sorted(set(evs)), ensure_ascii=False)
    prim = old[0]
    if prim == 'FE-70':
        c = q("SELECT own_event,sum(amount_dr+amount_cr) a FROM line_event WHERE doc_key=? AND role='DRIVER' AND own_event IS NOT NULL GROUP BY 1 ORDER BY a DESC", dk)
        prim = c[0][0] if c else prim
    cur.execute('UPDATE doc_class SET primary_event=?, driver_events=? WHERE doc_key=?', (prim, newde, dk))
    cur.execute('UPDATE line_event SET doc_primary_event=? WHERE doc_key=?', (prim, dk))
    if (prim, newde) != tuple(old):
        org, fy = q('SELECT org,fy FROM doc_class WHERE doc_key=?', dk)[0]
        log('CLASSIFICATION', '', org, fy, dk, 'doc_class.primary_event / driver_events', f'{old[0]} {old[1]}', f'{prim} {newde}', 'پیامد بازتخصیص خطوط FE-70 روی رویداد سند', '', '', '', 'QA_FE70_SEMANTICS')
# event review rows for TT-NE-23 / TT-NE-24 (v2 outcome preserved in v2_* columns)
for col in ('v2_review_outcome TEXT', 'v2_target TEXT'):
    try: cur.execute(f'ALTER TABLE event_review ADD COLUMN {col}')
    except sqlite3.OperationalError: pass
cur.execute('UPDATE event_review SET v2_review_outcome=review_outcome, v2_target=v2_id')
cur.execute("UPDATE event_review SET review_outcome='MODEL_AS_PERIOD_END_ACCOUNTING_OPERATION', v2_id='PEO-01', lifecycle_attribute='DEPRECIATION_RECOGNITION', reason='v2.1: استهلاک دوره‌ای ثبت تعدیلی پایان دوره است و در تعریف FE-70 (اصلاح سند/بستن حساب/جابه‌جایی) نمی‌گنجد؛ عملیات حسابداری پایان دوره غیرقانونی‌کانونی (PEO-01)', v2_status='PEO-01 (عملیات پایان دوره؛ نه رویداد canonical)' WHERE v1_id='TT-NE-23'")
cur.execute("UPDATE event_review SET review_outcome='SPLIT_RECOGNITION_VS_UTILISATION', v2_id='PEO-02 + TT-NE-11', lifecycle_attribute='PROVISION_ACCRUAL_RECOGNITION / SETTLE_ACCRUED_LIABILITY', reason='v2.1: بستانکار حساب ذخیره = شناسایی (PEO-02)؛ بدهکار حساب ذخیره در مقابل بانک = تسویهٔ بدهی تعهدی (TT-NE-11)', v2_status='PEO-02 + TT-NE-11' WHERE v1_id='TT-NE-24'")
cur.execute('DROP TABLE IF EXISTS event_crosswalk_v2_v21')
cur.execute('CREATE TABLE event_crosswalk_v2_v21 AS SELECT v2_event, own_event AS v21_event, v2_lifecycle, lifecycle_action AS v21_lifecycle, count(*) AS lines, count(DISTINCT doc_key) AS docs FROM line_event WHERE coalesce(v2_event,\'\')<>coalesce(own_event,\'\') OR coalesce(v2_lifecycle,\'\')<>coalesce(lifecycle_action,\'\') GROUP BY 1,2,3,4')

# ------------------------------------------------------------------------------------------------ S5 bridge and coverage by confidence
cur.execute('DROP TABLE IF EXISTS cc_bridge_v2_v21')
cur.execute('''CREATE TABLE cc_bridge_v2_v21 AS SELECT a.org AS org, a.eligible AS v2_eligible, a.cc_status AS v2_status, a.conf AS v2_conf, b.eligible AS v21_eligible, b.cc_status AS v21_status, b.conf AS v21_conf, count(*) AS lines, sum(s.bed-s.bes) AS net_value
    FROM v2.line_cc a JOIN line_cc b ON a.sid=b.sid JOIN sanad s ON s.sid=a.sid GROUP BY 1,2,3,4,5,6,7''')
cur.execute('DROP TABLE IF EXISTS cc_confidence_coverage')
cur.execute('''CREATE TABLE cc_confidence_coverage(version, organization, eligible_lines, eligible_value, selected_high_lines, selected_high_value, selected_medium_lines, selected_medium_value, selected_low_lines, selected_low_value,
    analytical_selected_lines, analytical_selected_value, evidence_supported_lines, evidence_supported_value, multiple_lines, multiple_value, insufficient_lines, insufficient_value)''')
for ver, dbp in (('v2', 'v2.'), ('v2.1', '')):
    for o in ORGS:
        def agg2(cond):
            r = q(f"SELECT count(*),sum(s.bed-s.bes) FROM {dbp}line_cc c JOIN sanad s ON s.sid=c.sid WHERE c.eligible=1 AND c.org=? AND {cond}", o)[0]; return (r[0] or 0, r[1] or 0)
        SEL = "c.cc_status IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE')"
        el, h, m, l, mu, ins = agg2('1=1'), agg2(SEL + " AND c.conf='HIGH'"), agg2(SEL + " AND c.conf='MEDIUM'"), agg2(SEL + " AND c.conf='LOW'"), agg2("c.cc_status='MULTIPLE_CC_CANDIDATES'"), agg2("c.cc_status='INSUFFICIENT_INFORMATION'")
        cur.execute('INSERT INTO cc_confidence_coverage VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (ver, o, el[0], el[1], h[0], h[1], m[0], m[1], l[0], l[1], h[0] + m[0] + l[0], h[1] + m[1] + l[1], h[0] + m[0], h[1] + m[1], mu[0], mu[1], ins[0], ins[1]))
con.commit()
print('low population', len(pop), collections.Counter(r[22] for r in rows_out))
print('by org/decision', collections.Counter((r[1], r[22]) for r in rows_out))
print('sample size', len(sample), 'fe70 lines', len(fe70), collections.Counter((r[7]) for r in fe70), 'docs', len(aff))
print('change_log_v21', one('SELECT count(*) FROM change_log_v21'))
for r in q('SELECT * FROM cc_confidence_coverage'): print(r)
