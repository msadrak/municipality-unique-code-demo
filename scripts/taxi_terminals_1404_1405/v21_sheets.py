# exec'd inside 08_build_outputs.py (TT_VARIANT=v21) right after v2_sheets.py, before QA_Reconciliation.
from decisions_v21 import build_decisions_v21
import re as _re

# ---------------------------------------------------------------- QA_Low_Confidence_CC : the full audit population (1,016 rows), no narration
la = q("""SELECT source_record_id,organization,fiscal_year,document_key,sanad_num,account_code,source_activity_code,existing_activity_id,previous_v1_status,previous_v1_candidates,v2_status,v2_cc,v2_confidence,v2_rule_id,v2_reason,v2_candidates,
              event_v2,amount_net,rule_group,audit_layer,audit_decision,v21_status,v21_cc,v21_confidence,v21_candidates,audit_reason,audit_evidence,sample_flag FROM low_audit ORDER BY organization,fiscal_year,source_record_id""")
la = [tuple(mcode(x) if i == 5 else x for i, x in enumerate(r)) for r in la]
sheet('QA_Low_Confidence_CC', [('source_record_id', 'Source_Record_ID', 't'), ('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('document_key', 'سند', 't'), ('sanad_num', 'Sanad_Num', 't'), ('account_code', 'حساب اصلی', 't'),
      ('source_activity_code', 'کد فعالیت منبع', 't'), ('existing_activity_id', 'شناسه فعالیت موجود', 't'), ('previous_v1_status', 'وضعیت v1', 't'), ('previous_v1_candidates', 'نامزدهای v1', 't'), ('v2_status', 'وضعیت v2', 't'),
      ('v2_cc', 'مرکز v2', 't'), ('v2_confidence', 'اطمینان v2', 't'), ('v2_rule_id', 'قاعده v2', 't'), ('v2_reason', 'دلیل v2', 't'), ('v2_candidates', 'جایگزین‌های v2', 't'), ('event_v2', 'رویداد', 't'), ('amount_net', 'خالص بدهکار', 'n'),
      ('rule_group', 'گروه قاعده', 't'), ('audit_layer', 'لایه ممیزی', 't'), ('audit_decision', 'تصمیم ممیزی', 't'), ('v21_status', 'وضعیت v2.1', 't'), ('v21_cc', 'مرکز v2.1', 't'), ('v21_confidence', 'اطمینان v2.1', 't'),
      ('v21_candidates', 'نامزدهای v2.1', 't'), ('audit_reason', 'دلیل ممیزی', 't'), ('audit_evidence', 'شاهد', 't'), ('in_sample', 'در نمونه دستی (۱=بله)', 'n')], la,
      title='ممیزی ۱٬۰۱۶ تخصیص مرکز هزینه با اطمینان LOW (تخصیص‌های جدید v2 از ردیف‌های حل‌نشده v1)',
      note='لایه ۱: بازبینی قاعده‌محور همهٔ ردیف‌ها؛ لایه ۲: نمونه‌گیری طبقه‌ای دستی (جدول QA_Low_Rule_Analysis و فایل low_confidence_cc_audit_v2.1.xlsx). شرح متنی اسناد عمداً نیامده است؛ ردیف‌های نمونه‌نشده «تأییدشده فردی» نیستند.', widths={'v2_reason': 50, 'audit_reason': 60, 'audit_evidence': 30})
ra = q('SELECT organization,rule_group,v2_cc,v2_rule_id,lines,abs_value,share_of_org_low_value,retained_low,upgraded_medium,to_multiple,to_insufficient,other,finding FROM low_rule_analysis ORDER BY organization,abs_value DESC')
sheet('QA_Low_Rule_Analysis', [('organization', 'سازمان', 't'), ('rule_group', 'گروه قاعده', 't'), ('v2_cc', 'مرکز v2', 't'), ('v2_rule_id', 'قاعده v2', 't'), ('lines', 'ردیف', 'n'), ('abs_value', 'ارزش مطلق', 'n'),
      ('share', 'سهم از ارزش LOW سازمان', 'p'), ('retained_low', 'LOW حفظ‌شده', 'n'), ('upgraded_medium', 'ارتقا به MEDIUM', 'n'), ('to_multiple', 'به چندنامزد', 'n'), ('to_insufficient', 'به ناکافی', 'n'), ('other', 'سایر', 'n'), ('finding', 'یافته', 't')], ra,
      title='تحلیل در سطح قاعده: تمرکز ریسک و نتیجهٔ ممیزی', widths={'finding': 70, 'rule_group': 30})

# ---------------------------------------------------------------- QA_CC_Confidence_Coverage + population bridge
cv = q('SELECT version,organization,eligible_lines,eligible_value,selected_high_lines,selected_high_value,selected_medium_lines,selected_medium_value,selected_low_lines,selected_low_value,analytical_selected_lines,analytical_selected_value,evidence_supported_lines,evidence_supported_value,multiple_lines,multiple_value,insufficient_lines,insufficient_value FROM cc_confidence_coverage ORDER BY organization,version')
cvr = [r + (r[10] / r[2] if r[2] else 0, r[12] / r[2] if r[2] else 0, r[11] / r[3] if r[3] else 0, r[13] / r[3] if r[3] else 0) for r in cv]
sheet('QA_CC_Confidence_Coverage', [('version', 'نسخه', 't'), ('organization', 'سازمان', 't'), ('eligible_lines', 'ردیف واجد شرایط', 'n'), ('eligible_value', 'ارزش واجد شرایط', 'n'), ('high_lines', 'HIGH ردیف', 'n'), ('high_value', 'HIGH ارزش', 'n'),
      ('medium_lines', 'MEDIUM ردیف', 'n'), ('medium_value', 'MEDIUM ارزش', 'n'), ('low_lines', 'LOW ردیف', 'n'), ('low_value', 'LOW ارزش', 'n'), ('analytical_lines', 'پوشش تحلیلی موقت: ردیف (همه انتخاب‌شده)', 'n'), ('analytical_value', 'پوشش تحلیلی: ارزش', 'n'),
      ('evidence_lines', 'پوشش پشتیبانی‌شده با شاهد (MEDIUM+HIGH): ردیف', 'n'), ('evidence_value', 'پوشش شاهدی: ارزش', 'n'), ('multiple_lines', 'چندنامزد: ردیف', 'n'), ('multiple_value', 'چندنامزد: ارزش', 'n'),
      ('insufficient_lines', 'ناکافی: ردیف', 'n'), ('insufficient_value', 'ناکافی: ارزش', 'n'), ('analytical_pct_lines', 'پوشش تحلیلی ٪ ردیف', 'p'), ('evidence_pct_lines', 'پوشش شاهدی ٪ ردیف', 'p'), ('analytical_pct_value', 'پوشش تحلیلی ٪ ارزش', 'p'), ('evidence_pct_value', 'پوشش شاهدی ٪ ارزش', 'p')], cvr,
      title='پوشش مرکز هزینه به تفکیک سطح اطمینان (v2 در برابر v2.1)',
      note='«پوشش تحلیلی موقت» شامل همهٔ ردیف‌های دارای مرکز انتخاب‌شده (از جمله LOW)؛ «پوشش شاهدی» فقط MEDIUM و HIGH. هیچ‌یک «تأییدشده/اعتبارسنجی‌شده» نیست. ارزش = Σ(بدهکار−بستانکار) ردیف‌های واجد شرایط.')
br = q('SELECT org,v2_eligible,v2_status,v2_conf,v21_eligible,v21_status,v21_conf,lines,net_value FROM cc_bridge_v2_v21 ORDER BY org,v2_status,v21_status,v2_conf')
sheet('QA_CC_Population_Bridge', [('org', 'سازمان', 't'), ('v2_eligible', 'واجد شرایط v2', 'n'), ('v2_status', 'وضعیت v2', 't'), ('v2_conf', 'اطمینان v2', 't'), ('v21_eligible', 'واجد شرایط v2.1', 'n'), ('v21_status', 'وضعیت v2.1', 't'), ('v21_conf', 'اطمینان v2.1', 't'), ('lines', 'ردیف', 'n'), ('net', 'ارزش خالص', 'n')], br,
      title='پل جمعیت v2 → v2.1 (هر ردیف منبع دقیقاً یک بار)', note='مجموع ردیف‌ها = ۱۱۱٬۶۰۰. جمعیت واجد شرایط تغییر نکرده است؛ فقط وضعیت/اطمینان ردیف‌های ممیزی‌شده تغییر کرده است.')

# ---------------------------------------------------------------- KPI status consistency + counts
ks = q('SELECT kpi_id,org,catalogue_status,distinct_result_statuses,result_rows,rows_with_value,rows_independently_verified,definition_status,calculation_status,verification_status,governance_status,consistent FROM kpi_status_consistency ORDER BY org,kpi_id')
sheet('QA_KPI_Status_Consistency', [('kpi_id', 'KPI', 't'), ('org', 'سازمان', 't'), ('catalogue_status', 'وضعیت کاتالوگ', 't'), ('result_statuses', 'وضعیت‌های ردیف نتایج', 't'), ('result_rows', 'ردیف نتیجه', 'n'), ('rows_with_value', 'دارای مقدار', 'n'),
      ('rows_verified', 'مشاهدات تأییدشده مستقل', 'n'), ('definition_status', 'Definition_Status', 't'), ('calculation_status', 'Calculation_Status', 't'), ('verification_status', 'Verification_Status', 't'), ('governance_status', 'Governance_Status', 't'), ('consistent', 'سازگار', 't')], ks,
      title='سازگاری وضعیت KPI و مدل پنج‌گانه (تعریف / محاسبه / راستی‌آزمایی / حاکمیت / برچسب ترکیبی)',
      note='تعریف یکتا ≠ نتیجهٔ محاسبه‌شده ≠ مشاهدهٔ KPI×دوره. TX-K01 در v2 در نتایج وضعیت قدیمی داشت؛ TM-K02 ردیف نتیجه نداشت؛ TM-K15 دو بار در کاتالوگ بود.', widths={'result_statuses': 36})
kcnt = q('SELECT organization,metric,value,definition FROM kpi_counts ORDER BY metric,organization')
sheet('QA_KPI_Counts', [('organization', 'سازمان', 't'), ('metric', 'شمارش', 't'), ('value', 'مقدار', 'n'), ('definition', 'تعریف', 't')], kcnt, title='شمارش‌های KPI (تنها منبع اعداد گزارش‌ها)', widths={'metric': 44, 'definition': 70})

# ---------------------------------------------------------------- FE-70 semantics
fe70def = FE['FE-70']
rows70 = q("""SELECT v2.v2_event||' ['||coalesce(v2.v2_lifecycle,'')||']', e.own_event||' ['||coalesce(e.lifecycle_action,'')||']', e.org, count(*), count(DISTINCT e.doc_key), sum(s.bed), sum(s.bes)
              FROM line_event e JOIN line_event v2 ON v2.sid=e.sid JOIN sanad s ON s.sid=e.sid WHERE e.sid IN (SELECT sid FROM fe70_review) GROUP BY 1,2,3 ORDER BY 4 DESC""")
rows70 = [(a, b, o, n, d, x, y, 'FE-70 «' + fe70def['title'] + '»: ' + fe70def['definition'][:140]) for a, b, o, n, d, x, y in rows70]
sheet('QA_FE70_Semantics', [('v2', 'تخصیص v2', 't'), ('v21', 'تخصیص v2.1', 't'), ('org', 'سازمان', 't'), ('lines', 'ردیف', 'n'), ('docs', 'سند', 'n'), ('debit', 'بدهکار', 'n'), ('credit', 'بستانکار', 'n'), ('fe70_definition', 'تعریف FE-70 (v7.1)', 't')], rows70,
      title='بازبینی معنایی FE-70: استهلاک و ذخایر', note='FE-70 فقط ثبت اصلاحی، انتقال مانده، بستن حساب موقت و اسناد اختتامیه را پوشش می‌دهد. استهلاک دوره‌ای = PEO-01؛ شناسایی ذخیره = PEO-02؛ مصرف ذخیره (بدهکار ذخیره در مقابل بانک) = تسویه بدهی TT-NE-11. تعریف FE-70 تغییر نکرد.', widths={'fe70_definition': 80, 'v2': 34, 'v21': 38})

# ---------------------------------------------------------------- change log v2 -> v2.1
cl21 = q('SELECT change_id,change_class,source_record_id,organization,fiscal_year,source_document,affected_component,v2_value,v21_value,reason,evidence,rule_change,confidence_change,qa_reference,governance_impact FROM change_log_v21 ORDER BY rowid')
sheet('V2_V21_Change_Log', [('change_id', 'Change ID', 't'), ('change_class', 'نوع تغییر', 't'), ('source_record_id', 'Source_Record_ID', 't'), ('organization', 'سازمان', 't'), ('fiscal_year', 'سال', 't'), ('source_document', 'سند', 't'),
      ('affected_component', 'مؤلفه', 't'), ('v2_value', 'مقدار v2', 't'), ('v21_value', 'مقدار v2.1', 't'), ('reason', 'دلیل', 't'), ('evidence', 'شاهد', 't'), ('rule_change', 'تغییر قاعده', 't'), ('confidence_change', 'تغییر اطمینان', 't'),
      ('qa_reference', 'مرجع QA', 't'), ('governance_impact', 'اثر حاکمیتی', 't')], cl21, title='گزارش تغییرات v2 → v2.1',
      note='هیچ مبلغ حسابداری تغییر نکرده است. دسته‌ها: METADATA، PRIVACY، CLASSIFICATION (مرکز هزینه و رویداد)، ACCOUNTING_INTERPRETATION (FE-70). تغییرات فقط QA/گزارش (مثل برچسب KPI) در audit مستند و در این جدول ردیف ندارند.', widths={'reason': 50, 'evidence': 30, 'v2_value': 28, 'v21_value': 28})

# ---------------------------------------------------------------- Decision matrix (v2.1) + Handover readiness
cvm = {(r[0], r[1]): r for r in q('SELECT version,organization,eligible_lines,analytical_selected_lines,evidence_supported_lines,selected_low_lines,multiple_lines,insufficient_lines FROM cc_confidence_coverage')}
kcm = {(r[0], r[1]): r[2] for r in q('SELECT organization,metric,value FROM kpi_counts')}
HR = []
for o, fa in ORGFA.items():
    c = cvm[('v2.1', o)]
    HR += [(fa, 'استفاده فنی (تحلیل و ردیابی داخلی)', 'READY', f'همه ۱۱۱٬۶۰۰ ردیف منبع ردیابی‌پذیر؛ ردیف‌های چندنامزد/ناکافی {c[6] + c[7]:,} از {c[2]:,} عمداً بدون مرکز'),
           (fa, 'بازبینی کارشناسی', 'READY_FOR_EXPERT_REVIEW', f'پوشش تحلیلی {c[3]:,} ({c[3] / c[2]:.1%})؛ پوشش شاهدی {c[4]:,} ({c[4] / c[2]:.1%})؛ LOW {c[5]:,}؛ ماتریس تصمیم و نمونه‌های ممیزی آماده'),
           (fa, 'ارائه موقت به کارفرما', 'READY_WITH_LABELS', 'همه نتایج با برچسب PROPOSED/PROVISIONAL؛ سال ۱۴۰۵ ناقص؛ مقایسه فقط پنجره مشترک و شاخص'),
           (fa, 'تأیید رسمی', 'NOT_STARTED', 'هیچ مورد APPROVED نیست؛ approved_items = 0'),
           (fa, 'یکپارچه‌سازی آتی ERP', 'NOT_READY', 'activate_in_production = NO؛ وابسته به CD-01 (پایانه‌ها)، CD-02 واحد پول، CD-04..08 مراکز هزینه و تأیید رویدادها')]
sheet('Handover_Readiness', [('organization', 'سازمان', 't'), ('audience', 'مخاطب/کاربرد', 't'), ('status', 'وضعیت', 't'), ('basis', 'مبنا', 't')], HR, title='آمادگی تحویل (برای هر کاربرد)',
      note='READY_FOR_EXPERT_REVIEW به معنای تأیید سیاست حسابداری نیست. APPROVED_FOR_PRODUCTION برای هیچ بخشی صادق نیست.', widths={'basis': 90, 'audience': 36})
