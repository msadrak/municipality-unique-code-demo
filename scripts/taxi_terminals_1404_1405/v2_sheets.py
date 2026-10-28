# exec'd inside 08_build_outputs.py (TT_VARIANT=v2) after the generic sheets, before QA_Reconciliation.  Uses: q, one, sheet, SHEETS, F, wb, ORGFA, CC, NEW_CC, QA, EVENT_REVIEW ...
from decisions_v2 import CC_AUDIT, build_decisions, COLS as DEC_COLS
import openpyxl as _ox
V2_SKIP.clear()
if VARIANT == 'v21': V2_SKIP.update({'V1_V2_Change_Log', 'CC_Coverage_v1_v2', 'CC_Resolution_Summary'})

# ------------------------------------------------------------------ New_CC_Proposals (v2): three separate counters, never one blended "supporting lines"
v1wb = _ox.load_workbook(f'{OUT.rsplit("/revisions", 1)[0]}/taxi_terminals_financial_mapping_1404_1405_v1.xlsx', read_only=True)
V1NP = {}
for r in v1wb['New_CC_Proposals'].iter_rows(values_only=True):
    if r and r[0] and str(r[0]).startswith('TTCC-P-'): V1NP[r[0]] = r
v1wb.close()
rec = {(r[0], r[1], r[2]): r[3:] for r in q('SELECT version,cc_id,metric,value_lines,value_docs,value_net FROM cc_proposal_recon')}
g = lambda ver, cid, m, i=0: (rec.get((ver, cid, m)) or (0, 0, 0))[i] or 0
NP2 = []
EXPL = {'TTCC-P-01': 'v1: ۶۴۴ = ۵۳۲ ردیف NEW_CC_CANDIDATE + ۱۱۲ ردیف MULTIPLE_CC_CANDIDATES (۱۸ سند، فعالیت منبع ۱۲۰ = حقوق واحد «بایگانی و کنترل اسناد ناوگان») که ستون cc_id نامزد اول (TTCC-P-01) را ذخیره کرده بود؛ شمارش بر اساس cc_id بود نه وضعیت. v2: ۵۳۲ مستقیم؛ ردیف‌های MULTIPLE مرکز انتخاب‌شده ندارند.',
        'TTCC-P-02': 'v1: ۱۵۷ ردیف مستقیم (همه NEW)، هیچ ناهمخوانی شمارش؛ مشکل مفهومی: ۱۴۸ ردیف با شرح خود ردیف و ۹ ردیف فقط با شرح کل سند تطبیق یافته بود. v2: پیشنهاد منحل و ردیف‌ها به CC-406 رفتند.',
        'TTCC-P-03': 'v1: ۰ ردیف مستقیم؛ ۱٬۶۴۳ ردیف MULTIPLE + ۱٬۲۵۹ ردیف PROVISIONAL آن را فقط به‌عنوان جایگزین ذکر کرده بودند. v2: دیگر نامزد مرکز نیست؛ هزینه پایانه → CC-403 و درآمد اجاره/عوارض بُعد منبع درآمد.'}
for cid in ('TTCC-P-01', 'TTCC-P-02', 'TTCC-P-03'):
    a = CC_AUDIT[cid]; v1r = V1NP.get(cid)
    moved = q("SELECT v2_status,v2_cc,sum(lines),sum(net) FROM cc_proposal_moves WHERE v1_cc=? GROUP BY 1,2", cid)
    NP2.append((cid, v1r[1] if v1r else '', a['recommendation'], a['title_v2'], a['reasoning'],
                g('v2', cid, 'DIRECT'), g('v2', cid, 'DIRECT', 1), g('v2', cid, 'DIRECT', 2), g('v2', cid, 'AMBIGUOUS'), g('v2', cid, 'AMBIGUOUS', 2), g('v2', cid, 'EVIDENCE_SUPPORT'), g('v2', cid, 'EVIDENCE_SUPPORT', 2),
                g('v1', cid, 'REPORTED_V1'), g('v1', cid, 'REPORTED_V1', 2), g('v1', cid, 'DIRECT'), g('v1', cid, 'AMBIGUOUS'), EXPL[cid],
                ' ؛ '.join(f'{s or "—"}→{c or "—"}: {n:,} ردیف' for s, c, n, _ in moved), a['alternatives'], a['overlap'], a['experts'], a['approval'], a['open_questions'], 'PROPOSED — نیازمند تصمیم؛ در master شهرداری وارد نشده است'))
sheet('New_CC_Proposals', [('provisional_id', 'شناسه موقت', 't'), ('v1_title', 'عنوان پیشنهادی در v1', 't'), ('v2_recommendation', 'توصیه v2', 't'), ('v2_title', 'عنوان/جایگاه v2', 't'), ('reasoning', 'استدلال و مقایسه با مراکز موجود', 't'),
      ('Direct_Assignment_Count', 'Direct_Assignment_Count (ردیف‌های با مرکز انتخاب‌شده)', 'n'), ('Direct_docs', 'اسناد مستقیم', 'n'), ('Direct_net', 'خالص بدهکار مستقیم', 'n'),
      ('Ambiguous_Candidate_Count', 'Ambiguous_Candidate_Count (ردیف‌های MULTIPLE با این پیشنهاد در نامزدها)', 'n'), ('Ambiguous_net', 'خالص بدهکار ابهام‌دار', 'n'),
      ('Evidence_Support_Count', 'Evidence_Support_Count (= مستقیم + ابهام‌دار؛ ردیف یکتا)', 'n'), ('Evidence_Support_net', 'خالص بدهکار شاهدی', 'n'),
      ('v1_reported_lines', 'ردیف گزارش‌شده در v1', 'n'), ('v1_reported_net', 'خالص گزارش‌شده در v1', 'n'), ('v1_direct_recomputed', 'مستقیم بازمحاسبه‌شده v1', 'n'), ('v1_ambiguous_recomputed', 'ابهام‌دار بازمحاسبه‌شده v1', 'n'),
      ('reconciliation', 'تطبیق اختلاف v1 و مبنای شمارش', 't'), ('lines_moved', 'جابه‌جایی ردیف‌ها v1→v2', 't'), ('alternatives', 'گزینه‌های بررسی‌شده', 't'), ('overlap', 'هم‌پوشانی', 't'),
      ('expert', 'مرجع کارشناسی', 't'), ('approval', 'تأییدکننده لازم', 't'), ('open_questions', 'سؤال‌های باز', 't'), ('governance_status', 'وضعیت حاکمیتی', 't')], NP2,
      title='پیشنهادهای مرکز هزینه جدید — بازبینی v2 (سه شمارنده جدا، بدون جمعیت مختلط)',
      note='MULTIPLE_CC_CANDIDATES مرکز انتخاب‌شده ندارد و در Direct شمرده نمی‌شود. هیچ مرکزی به master شهرداری اضافه نشده است؛ هیچ پیشنهادی APPROVED نیست.', widths={'reasoning': 70, 'reconciliation': 60, 'v2_title': 44, 'v1_title': 36, 'lines_moved': 40})

# ------------------------------------------------------------------ QA_CC_Consistency
qcc = q('SELECT version,cc_id,metric,value_lines,value_docs,value_net,definition FROM cc_proposal_recon ORDER BY cc_id,version,metric')
sheet('QA_CC_Consistency', [('version', 'نسخه', 't'), ('cc_id', 'پیشنهاد', 't'), ('metric', 'شاخص', 't'), ('lines', 'ردیف', 'n'), ('docs', 'سند', 'n'), ('net', 'خالص بدهکار', 'n'), ('definition', 'تعریف شاخص', 't')], qcc,
      title='سازگاری شمارش پیشنهادهای مرکز هزینه (v1 در برابر v2)', note='DIRECT + AMBIGUOUS = EVIDENCE_SUPPORT؛ REPORTED_V1 = شمارش بر اساس cc_id (روش معیوب v1). ردیف‌های ALT_OF_SELECTED مرکز دیگری انتخاب‌شده دارند و فقط پیشنهاد را به‌عنوان جایگزین ذکر کرده‌اند.', widths={'definition': 70})
cov = q('SELECT version,org,fy,eligible_lines,selected_lines,multiple_lines,insufficient_lines,eligible_value,selected_value,multiple_value,insufficient_value FROM cc_coverage ORDER BY version,org,fy')
sheet('CC_Coverage_v1_v2', [('version', 'نسخه', 't'), ('organization', 'سازمان', 't'), ('fy', 'سال', 't'), ('eligible_lines', 'ردیف‌های واجد شرایط', 'n'), ('selected_lines', 'با مرکز انتخاب‌شده (PROVISIONAL+NEW)', 'n'), ('multiple_lines', 'MULTIPLE', 'n'),
      ('insufficient_lines', 'INSUFFICIENT', 'n'), ('eligible_value', 'ارزش خالص واجد شرایط', 'n'), ('selected_value', 'ارزش انتخاب‌شده', 'n'), ('multiple_value', 'ارزش MULTIPLE', 'n'), ('insufficient_value', 'ارزش INSUFFICIENT', 'n')], cov,
      title='پوشش مرکز هزینه v1 در برابر v2', note='ارزش = Σ(بدهکار−بستانکار) ردیف‌های هزینه‌ای/سرمایه‌ای واجد شرایط (نه گردش ترازنامه‌ای). مقایسه v1/v2 روی جمعیت واجد شرایط متفاوت است زیرا نقش ردیف‌ها (COMPONENT/VAT) در v2 اصلاح شد.')
res = q('SELECT org,resolution,new_status,rule,confidence,expert_review,count(*),sum(net_value) FROM cc_resolution GROUP BY 1,2,3,4,5,6 ORDER BY 1,2,7 DESC')
sheet('CC_Resolution_Summary', [('organization', 'سازمان', 't'), ('resolution', 'نتیجه', 't'), ('new_status', 'وضعیت v2', 't'), ('rule', 'قاعده', 't'), ('confidence', 'اطمینان', 't'), ('expert_review', 'بازبینی کارشناس', 't'), ('lines', 'ردیف', 'n'), ('net_value', 'ارزش خالص', 'n')], res,
      title='سرنوشت ۵٬۴۰۹ ردیف حل‌نشده v1 (MULTIPLE/INSUFFICIENT) در v2', note='فهرست ردیف‌به‌ردیف با شواهد: machine_readable/cc_unresolved_resolution.csv', widths={'rule': 34})

# ------------------------------------------------------------------ semantic events
er = q('SELECT v1_id,v1_title,family,v1_definition,gap_link,related_fe,review_outcome,v2_id,lifecycle_attribute,reason,orgs,v1_driver_lines,v1_docs,v1_debit,v1_credit,account_chains,v1_composite_docs,atomicity,counterparty_semantics,overlap_notes,v2_lines,v2_docs,v2_status,expert_approval_needed FROM event_review ORDER BY v1_id')
sheet('QA_Semantic_Events', [('v1_id', 'کاندید v1', 't'), ('v1_title', 'عنوان v1', 't'), ('family', 'خانواده', 't'), ('v1_definition', 'تعریف v1', 't'), ('gap_link', 'شکاف v7.1', 't'), ('related_fe', 'FE مرتبط', 't'),
      ('review_outcome', 'نتیجه بازبینی', 't'), ('v2_id', 'شناسه v2 / مقصد', 't'), ('lifecycle_attribute', 'ویژگی چرخه‌عمر', 't'), ('reason', 'دلیل', 't'), ('orgs', 'سازمان‌ها', 't'), ('v1_driver_lines', 'ردیف محرک v1', 'n'),
      ('v1_docs', 'اسناد v1', 'n'), ('v1_debit', 'بدهکار v1', 'n'), ('v1_credit', 'بستانکار v1', 'n'), ('account_chains', 'زنجیره حساب‌ها (نمونه غالب)', 't'), ('v1_composite_docs', 'اسناد ترکیبی v1', 'n'),
      ('atomicity', 'اتمیک بودن', 't'), ('counterparty_semantics', 'طرف‌حساب/معنا', 't'), ('overlap_notes', 'هم‌پوشانی', 't'), ('v2_lines', 'ردیف محرک v2 (شناسه v2)', 'n'), ('v2_docs', 'اسناد v2', 'n'),
      ('v2_status', 'وضعیت v2', 't'), ('expert_approval_needed', 'تأیید کارشناس لازم', 't')], er,
      title='بازبینی مفهومی همه ۲۸ کاندید رویداد v1', note='نتیجه‌ها: RETAIN / MERGE / SPLIT / LIFECYCLE / POSTING_COMPONENT / INSUFFICIENT_EVIDENCE / EXCEPTION. هیچ کاندیدی APPROVED نیست.', widths={'v1_definition': 50, 'reason': 60, 'account_chains': 50, 'overlap_notes': 40, 'counterparty_semantics': 40})
xw = q('SELECT v1_event,v2_event,lifecycle_action,v1_role,v2_role,lines,docs FROM event_crosswalk ORDER BY v1_event,lines DESC')
sheet('Event_Crosswalk_v1_v2', [('v1_event', 'رویداد v1', 't'), ('v2_event', 'رویداد v2', 't'), ('lifecycle_action', 'اقدام چرخه‌عمر', 't'), ('v1_role', 'نقش v1', 't'), ('v2_role', 'نقش v2', 't'), ('lines', 'ردیف', 'n'), ('docs', 'سند', 'n')], xw,
      title='crosswalk رویداد v1→v2 (ردیف‌به‌ردیف در change_log)')
dt = q('SELECT v1_outcome,v2_outcome,docs,bed_total FROM doc_transitions ORDER BY docs DESC')
sheet('Doc_Outcome_Transitions', [('v1_outcome', 'نتیجه سند v1', 't'), ('v2_outcome', 'نتیجه سند v2', 't'), ('docs', 'اسناد', 'n'), ('debit_total', 'جمع بدهکار اسناد', 'n')], dt, title='تغییر نتیجه طبقه‌بندی اسناد (فقط اسناد تغییرکرده)')

# ------------------------------------------------------------------ KPI verification
kv = q('SELECT metric_id,org,fy,window,v1_value,v2_pipeline_value,independent_value,abs_diff,verdict,note FROM kpi_verification ORDER BY org,metric_id,fy,window')
sheet('QA_KPI_Verification', [('metric_id', 'شاخص پایه', 't'), ('org', 'سازمان', 't'), ('fy', 'سال', 't'), ('window', 'پنجره', 't'), ('v1_value', 'مقدار v1', 'n'), ('v2_pipeline', 'مقدار پایپ‌لاین v2', 'n'),
      ('independent', 'بازمحاسبه مستقل از فایل منبع', 'n'), ('abs_diff', 'اختلاف مطلق (v2−مستقل)', 'n'), ('verdict', 'نتیجه', 't'), ('note', 'یادداشت', 't')], kv,
      title='بازمحاسبه مستقل شاخص‌های پایه KPI (13_kpi_independent.py: خواندن مستقیم xlsx منبع بدون SQLite و بدون موتور طبقه‌بندی)',
      note='مقادیر v1 فقط برای مقایسه‌اند؛ اختلاف v1 با مقدار مستقل توضیح داده شده است (تعریف یا نوع سند).', widths={'note': 60})
kk = q('SELECT kpi_id,org,fy,window,v1_value,v2_value,independent_value,v1_status,v2_status,verdict,note FROM kpi_v1_v2 ORDER BY kpi_id,fy,window')
sheet('KPI_V1_V2', [('kpi_id', 'KPI', 't'), ('org', 'سازمان', 't'), ('fy', 'سال', 't'), ('window', 'پنجره', 't'), ('v1_value', 'مقدار v1', 'd'), ('v2_value', 'مقدار v2', 'd'), ('independent', 'مقدار مستقل', 'd'),
      ('v1_status', 'وضعیت v1', 't'), ('v2_status', 'وضعیت v2', 't'), ('verdict', 'قضاوت', 't'), ('note', 'یادداشت', 't')], kk, title='KPIهای قابل‌محاسبه: v1، v2 و مقدار مستقل',
      note='مقادیر اولیه TX-K01 و TM-K02/K11 مبلغ‌اند؛ سایر مقادیر نسبت. مقدار صفر برای TX-K03 ۱۴۰۴ پنجره مشترک یعنی در آن پنجره کمک بودجه ثبت نشده است.', widths={'note': 60, 'verdict': 36})

# ------------------------------------------------------------------ Terminal agency evidence
ta = q('SELECT section,fy,doc_kind,account_group,account_title,debit,credit,lines,example_docs FROM terminal_agency ORDER BY section,fy,doc_kind,debit DESC')
sheet('Terminal_Agency_Evidence', [('section', 'بخش', 't'), ('fy', 'سال', 't'), ('doc_kind', 'نوع سند', 't'), ('account_group', 'گروه حساب', 't'), ('account_title', 'عنوان حساب', 't'), ('debit', 'بدهکار', 'n'), ('credit', 'بستانکار', 'n'), ('lines', 'ردیف', 'n'), ('example_docs', 'اسناد نمونه', 't')], ta,
      title='شواهد حسابداری پایانه‌ها برای تصمیم CD-01 (فقط مشاهده؛ بدون نتیجه‌گیری حقوقی)', note='مانده افتتاحیه و اختتامیه ۱۱۳-۱-۱ و ۲۱۱-۱-۱ صفر است؛ این الگو با عامل‌بودن سازگار است اما وضعیت حقوقی را اثبات نمی‌کند.', widths={'account_title': 40, 'example_docs': 40})

# ------------------------------------------------------------------ change log (row-level) — full CSV also exported
cl = q('SELECT source_record_id,organization,fiscal_year,original_document_ref,field_changed,old_value,new_value,reason,supporting_evidence,rule_or_code_path,confidence,governance_effect FROM change_log ORDER BY organization,fiscal_year,source_record_id,field_changed')
sheet('V1_V2_Change_Log', [('source_record_id', 'Source_Record_ID', 't'), ('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('original_document_ref', 'ارجاع سند اصلی', 't'), ('field_changed', 'فیلد تغییرکرده', 't'),
      ('old_value', 'مقدار v1', 't'), ('new_value', 'مقدار v2', 't'), ('reason', 'دلیل', 't'), ('supporting_evidence', 'شاهد پشتیبان', 't'), ('rule_or_code_path', 'قاعده/مسیر کد', 't'), ('confidence', 'اطمینان', 't'), ('governance_effect', 'اثر حاکمیتی', 't')], cl,
      title='گزارش تغییرات v1→v2 (ردیف‌به‌ردیف)', note='هر تغییر پیامدی ثبت شده است: رویداد، نقش ردیف، وضعیت مرکز هزینه، مرکز انتخاب‌شده، نامزدها، نوع سند و اقدام چرخه‌عمر. فهرست مشابه: machine_readable/v1_to_v2_change_log.csv', widths={'old_value': 30, 'new_value': 30, 'reason': 34, 'original_document_ref': 30})

# ------------------------------------------------------------------ Decision_Readiness (13-column matrix) + per-organization assessment
if VARIANT == 'v21':
    from decisions_v21 import build_decisions_v21 as _bd
else: _bd = build_decisions
DEC = _bd(q, one)
HDR13 = ['Decision ID', 'Organization', 'Subject', 'Current evidence', 'Model recommendation', 'Alternative options', 'Financial / operational impact', 'Relevant source examples', 'Expert responsible', 'Required approval', 'Blocking / non-blocking', 'Decision status', 'Recommended next action']
dr_ws = sheet('Decision_Readiness', [(k, h, 't') for k, h in zip(DEC_COLS, HDR13)], DEC, title='ماتریس آمادگی تصمیم (Decision Readiness)',
              note='وضعیت‌ها: TECHNICALLY_VERIFIED / PROVISIONALLY_MODELED / REQUIRES_AUTHORITY_DECISION. هیچ تصمیمی APPROVED نیست؛ activate_in_production = NO.', widths={'subject': 40, 'current_evidence': 60, 'model_recommendation': 50, 'alternative_options': 30, 'impact': 30, 'source_examples': 34, 'next_action': 40})
cvg = {(r[0], r[1]): r for r in q("SELECT version,org,sum(eligible_lines),sum(selected_lines),sum(multiple_lines),sum(insufficient_lines),sum(eligible_value),sum(selected_value) FROM cc_coverage WHERE fy='ALL' GROUP BY 1,2")}
if VARIANT == 'v21': cvg = {('v2', r[1]): (r[0], r[1], r[2], r[10], r[14], r[16], r[3], r[11]) for r in q("SELECT * FROM cc_confidence_coverage WHERE version='v2.1'")}
r0 = SHEETS['Decision_Readiness']['first'] + SHEETS['Decision_Readiness']['n'] + 2
dr_ws.write(r0, 0, 'ارزیابی آمادگی به تفکیک سازمان', F['title']); r0 += 1
for j, h in enumerate(['سازمان', 'بُعد', 'ارزیابی', 'شواهد عددی']): dr_ws.write(r0, j, h, F['h'])
r0 += 1
READY = []
for org, fa in ORGFA.items():
    c2 = cvg[('v2', org)]; docs = one('SELECT count(*) FROM doc_class WHERE org=?', org)
    ev_un = one("SELECT count(*) FROM doc_class WHERE org=? AND outcome IN ('AMBIGUOUS_EVENT','COMPOSITE_TRANSACTION','PENDING_IDENTIFICATION')", org)
    kst = collections.Counter(r[0] for r in q('SELECT calc_status FROM kpi_catalogue WHERE org=?', org))
    READY += [(fa, 'یکپارچگی داده منبع', 'TECHNICALLY_VERIFIED', f'اسناد {docs:,}؛ هش RAR و تراز تأیید شد'),
              (fa, 'رویدادهای مالی', 'PROVISIONALLY_MODELED', f'اسناد مبهم/ترکیبی/در انتظار شناسایی: {ev_un:,} از {docs:,}'),
              (fa, 'مراکز هزینه', 'PROVISIONALLY_MODELED', f'ردیف واجد شرایط {c2[2]:,}؛ دارای مرکز {c2[3]:,} ({c2[3] / c2[2]:.1%})؛ چندمرکزی {c2[4]:,}؛ ناکافی {c2[5]:,}'),
              (fa, 'KPI', 'PROVISIONALLY_MODELED', ' ؛ '.join(f'{k}: {v}' for k, v in sorted(kst.items()))),
              (fa, 'تصمیم‌های بیرونی', 'REQUIRES_AUTHORITY_DECISION', 'ر.ک. ماتریس بالا (وضعیت REQUIRES_AUTHORITY_DECISION)')]
for row in READY:
    for j, v in enumerate(row): dr_ws.write(r0, j, v, F['t'])
    r0 += 1
DEC_ROWS_FOR_EXPORT = DEC; READY_ROWS = READY
