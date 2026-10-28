"""Regression tests for the Taxi / Terminals FY1404-1405 mapping pipeline (scripts/taxi_terminals_1404_1405)."""
import os
import sqlite3
import sys

import pytest

PIPE = os.path.join(os.path.dirname(__file__), "..", "scripts", "taxi_terminals_1404_1405")
sys.path.insert(0, PIPE)

import common  # noqa: E402
import rules  # noqa: E402


def test_persian_normalization_never_rewrites_the_source_value() -> None:
    raw = "علي\u200cاكبر  كارمزد"
    assert common.norm(raw) == "علی اکبر کارمزد"
    assert raw == "علي\u200cاكبر  كارمزد"


def test_bank_service_fee_is_not_mapped_to_the_facility_interest_event() -> None:
    # FE-65 is interest/commission on bank FACILITIES; daily service fees must become their own candidate
    event, status, _conf, _rule = rules.EXP_MAP[("612", "5", "12")]
    assert event == "TT-NE-08" and status == "NEW_EVENT_CANDIDATE"


def test_spare_parts_stay_ambiguous_instead_of_forcing_purchase_or_repair() -> None:
    for taf1 in ("3", "4"):
        event, status, _c, _r = rules.EXP_MAP[("612", "7", taf1)]
        assert event is None and status == "AMBIGUOUS_EVENT"


def test_new_event_namespace_cannot_collide_with_canonical_ids() -> None:
    assert all(k.startswith("TT-NE-") for k in rules.TT_EVENTS)
    assert all(len(v[6]) > 20 for v in rules.TT_EVENTS.values()), "every candidate must justify why FE-01..FE-70 is insufficient"


def test_payroll_text_does_not_match_contractor_statement() -> None:
    assert rules.R_PAYROLL.search(common.norm("سند حقوق اردیبهشت ماه"))
    assert not rules.R_PAYROLL.search(common.norm("صورت وضعیت خدمات انتظامات"))


DB = os.path.join(os.path.dirname(__file__), "..", "data", "work", "taxi_terminals", "tt.sqlite")
DB2 = os.path.join(os.path.dirname(__file__), "..", "data", "work", "taxi_terminals", "tt_v2.sqlite")


@pytest.mark.skipif(not os.path.exists(DB), reason="pipeline work database not generated")
def test_pipeline_invariants_on_generated_database() -> None:
    con = sqlite3.connect(DB)
    q = lambda s: con.execute(s).fetchone()[0]
    assert q("SELECT count(*) FROM sanad") == q("SELECT count(*) FROM line_event") == q("SELECT count(*) FROM line_cc")
    assert q("SELECT sum(bed)-sum(bes) FROM sanad") == 0
    assert q("SELECT count(*) FROM (SELECT doc_key FROM sanad GROUP BY doc_key HAVING sum(bed)<>sum(bes))") == 0
    # nothing is approved and no cost-center match is claimed as exact/validated without an approved crosswalk
    assert q("SELECT count(*) FROM line_cc WHERE cc_status IN ('EXACT_EXISTING_CC','VALIDATED_EXISTING_CC')") == 0
    assert q("SELECT count(*) FROM line_event WHERE outcome LIKE '%APPROVED%'") == 0
    # pass-through school-service money must never be booked as revenue or expense
    assert q("SELECT count(*) FROM line_event WHERE own_event IN ('TT-NE-03','TT-NE-04','TT-NE-06','TT-NE-07') AND role='DRIVER' AND acat IN ('REV_OP','REV_NONOP','EXP')") == 0


# ----------------------------------------------------------------------------------------------- v2 (audited revision)



def test_v2_event_review_accounts_for_every_v1_candidate_and_retires_only_reviewed_ones() -> None:
    assert set(rules.EVENT_REVIEW) == set(rules.TT_EVENTS_V1)
    kept = {k for k, v in rules.EVENT_REVIEW.items() if v[0] in ("RETAIN_AS_NEW_EVENT", "SPLIT_INTO_DISTINCT_EVENTS", "INSUFFICIENT_EVIDENCE")}
    assert set(rules.TT_EVENTS_V2) == kept
    # a candidate merged into a lifecycle/posting concept must name its successor
    for k, (outcome, successor, _attr, reason) in rules.EVENT_REVIEW.items():
        assert reason
        if outcome.startswith(("MODEL_AS", "MERGE_WITH")):
            assert successor and successor != k


@pytest.mark.skipif(not os.path.exists(DB2), reason="v2 work database not generated")
def test_v2_unresolved_cost_center_rows_never_carry_a_selected_center() -> None:
    # root cause of the v1 TTCC-P-01 644-vs-532 discrepancy: MULTIPLE rows stored their first candidate in cc_id
    con = sqlite3.connect(DB2)
    q = lambda s: con.execute(s).fetchone()[0]
    assert q("SELECT count(*) FROM line_cc WHERE cc_status NOT IN ('PROVISIONAL_EXISTING_CC','NEW_CC_CANDIDATE') AND coalesce(cc_id,'')<>''") == 0
    assert q("SELECT count(*) FROM line_cc WHERE cc_status='MULTIPLE_CC_CANDIDATES' AND instr(alt_ccs,';')=0") == 0
    assert q("SELECT count(*) FROM line_cc WHERE cc_id IN ('TTCC-P-02','TTCC-P-03')") == 0
    d, a, s = (q(f"SELECT value_lines FROM cc_proposal_recon WHERE version='v2' AND cc_id='TTCC-P-01' AND metric='{m}'") for m in ("DIRECT", "AMBIGUOUS", "EVIDENCE_SUPPORT"))
    assert d + a == s


@pytest.mark.skipif(not os.path.exists(DB2), reason="v2 work database not generated")
def test_v2_every_terminals_expense_driver_line_stays_in_the_cost_center_population() -> None:
    # regression: renaming a rule id once silently removed 456 outsourced-service lines (1.76e12) from the eligible population
    con = sqlite3.connect(DB2)
    n = con.execute("SELECT count(*) FROM line_event e JOIN line_cc c ON c.sid=e.sid WHERE e.org='Terminals' AND e.acat='EXP' AND e.role='DRIVER' AND c.eligible=0 AND e.doc_outcome<>'NOT_AN_OPERATIONAL_EVENT'").fetchone()[0]
    assert n == 0


@pytest.mark.skipif(not os.path.exists(DB2), reason="v2 work database not generated")
def test_v2_unidentified_receipts_are_an_exception_never_revenue_and_kpis_match_independent_recompute() -> None:
    con = sqlite3.connect(DB2)
    assert con.execute("SELECT count(*) FROM line_event WHERE own_event='EXC-01' AND acat IN ('REV_OP','REV_NONOP')").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM kpi_verification WHERE verdict<>'EXACT_MATCH'").fetchone()[0] == 0


# ----------------------------------------------------------------------------------------------- v2.1 (final corrective pass)
DB21 = os.path.join(os.path.dirname(__file__), "..", "data", "work", "taxi_terminals", "tt_v21.sqlite")


def test_v21_low_confidence_rules_do_not_trust_bare_keywords_or_default_event_centers() -> None:
    from audit_rules_v21 import decide

    def rec(**k):
        base = dict(org="Terminals", cc="CC-1403", T="", A="", event="", basis="", rule_id="TERM")
        base.update(k)
        return base

    # warehouse issue on the «office consumables» account keeps CC-1403 (two independent facts: account nature + item), capital equipment does not
    d = decide(rec(basis="حواله خروج کالای مصرفی (۱۱۵-۵)", A="لوازم مصرفی اداری", T="کالا:چای ایرانی"))
    assert d[0] == "UPGRADE_TO_MEDIUM_WITH_EVIDENCE" and d[3] == "MEDIUM"
    d = decide(rec(basis="حواله خروج کالای مصرفی (۱۱۵-۵)", A="اثاثیه و منصوبات(سرمایه ای)", T="کالا:مانیتور"))
    assert d[1] == "MULTIPLE_CC_CANDIDATES" and d[2] is None and len(d[4]) >= 2
    # event-default FE-22 -> CC-1403 («supplies») must not stand for hospitality / ceremonies
    d = decide(rec(org="Taxi", rule_id="EV-DEF", basis="مرکز از رویداد FE-22: ملزومات", A="هزینه جشن و پذیرایی، سوگواری", T="خرید میوه"))
    assert d[1] == "MULTIPLE_CC_CANDIDATES" and "CC-1403" in d[4] and "CC-1503" in d[4]
    # «رول پلاک» (wall plug) must not be read as a licence-plate activity (CC-602)
    d = decide(rec(cc="CC-602", basis="قاعده فعالیت‌محور شهرداری OP_PLATE روی شرح سطر؛ اطمینان پایین", A="لوازم مصرفی اداری", T="بابت مهر ژلاتینی/مهر و پلاک سازی"))
    assert d[1] != "PROVISIONAL_EXISTING_CC"
    # a MULTIPLE status never carries fewer than two candidates
    for T_ in ("لایحه خدمات قضایی", "سامانه عدل", "ماموریت"):
        d = decide(rec(cc="CC-1003", basis="قاعده فعالیت‌محور شهرداری SUP_LEGAL روی شرح سطر", A="", T=T_))
        assert d[1] != "MULTIPLE_CC_CANDIDATES" or len(set(d[4])) >= 2


def test_v21_registry_keeps_historical_regressions_out_of_the_acceptance_summary() -> None:
    from qa_registry_v21 import build_registry, summarize

    qa = {"tests": [dict(test_id="QA_NEW_CC_PROPOSAL_RECONCILIATION-V1", area="V1_ARTIFACT", status="FAIL"), dict(test_id="QA_X", area="KPI", status="PASS"), dict(test_id="P13-Taxi-1404", area="Deliverable", status="PASS")]}
    s = summarize(build_registry(qa))
    assert s["HISTORICAL_REGRESSION"]["FAIL"] == 1 and s["V21_ACCEPTANCE"]["FAIL"] == 0 and s["V21_ACCEPTANCE"]["PASS"] == 1 and s["WORKBOOK_FORMULA_CONTROL"]["PASS"] == 1


@pytest.mark.skipif(not os.path.exists(DB21), reason="v2.1 work database not generated")
def test_v21_kpi_definitions_are_unique_and_results_follow_the_catalogue_status() -> None:
    con = sqlite3.connect(DB21)
    q = lambda s: con.execute(s).fetchall()
    assert q("SELECT count(*),count(DISTINCT kpi_id) FROM kpi_catalogue") == [(31, 31)]
    assert q("SELECT count(*) FROM kpi_results r JOIN kpi_catalogue c ON c.kpi_id=r.kpi_id WHERE r.status<>c.calc_status") == [(0,)]
    # every calculable KPI has result rows (TM-K02 had none in v2)
    assert q("SELECT count(*) FROM kpi_catalogue c WHERE c.calc_status IN ('CALCULATED_AND_VERIFIED','CALCULATED_BUT_ACCOUNTING_POLICY_PENDING') AND NOT EXISTS (SELECT 1 FROM kpi_results r WHERE r.kpi_id=c.kpi_id)") == [(0,)]


@pytest.mark.skipif(not os.path.exists(DB21), reason="v2.1 work database not generated")
def test_v21_depreciation_and_provisions_are_not_fe70_and_amounts_are_conserved() -> None:
    con = sqlite3.connect(DB21)
    con.execute(f"ATTACH DATABASE '{DB2}' AS v2")
    q = lambda s: con.execute(s).fetchone()
    assert q("SELECT count(*) FROM line_event WHERE own_event='FE-70' AND lifecycle_action IN ('DEPRECIATION','PROVISION_OR_ACCRUAL')")[0] == 0
    assert q("SELECT sum(s.bed),sum(s.bes) FROM line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event IN ('PEO-01','PEO-02') OR e.lifecycle_action='SETTLE_ACCRUED_LIABILITY'") == \
        q("SELECT sum(s.bed),sum(s.bes) FROM v2.line_event e JOIN sanad s ON s.sid=e.sid WHERE e.own_event='FE-70' AND e.lifecycle_action IN ('DEPRECIATION','PROVISION_OR_ACCRUAL')")
    assert q("SELECT sum(bed),sum(bes) FROM sanad") == q("SELECT sum(bed),sum(bes) FROM v2.sanad")


@pytest.mark.skipif(not os.path.exists(DB21), reason="v2.1 work database not generated")
def test_v21_confidence_is_never_raised_without_evidence_and_bank_accounts_are_masked() -> None:
    con = sqlite3.connect(DB21)
    q = lambda s: con.execute(s).fetchone()[0]
    assert q("SELECT count(*) FROM low_audit") == 1016
    assert q("SELECT count(*) FROM low_audit WHERE v21_confidence<>v2_confidence AND (coalesce(audit_evidence,'')='' OR v21_confidence='HIGH')") == 0
    assert q("SELECT count(*) FROM account_dictionary WHERE title GLOB '*[0-9][0-9][0-9][0-9][0-9][0-9]*'") == 0
