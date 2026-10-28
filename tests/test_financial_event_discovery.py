from scripts.build_financial_event_discovery_workbook import (
    candidate_id_for_key,
    classify_baseline_matches,
    make_event_key,
    normalize_analysis_text,
)


def test_persian_normalization_is_limited_to_analysis_key() -> None:
    raw = "  علي\u200cاكبر يزدي ك  "

    assert normalize_analysis_text(raw) == "علی اکبر یزدی ک"
    assert raw == "  علي\u200cاكبر يزدي ك  "


def test_candidate_identifier_is_opaque_and_deterministic() -> None:
    key = "211|001|00001|00009|هزینه خدمات"

    assert candidate_id_for_key(key) == candidate_id_for_key(key)
    assert candidate_id_for_key(key).startswith("CFE-")
    assert "211" not in candidate_id_for_key(key)


def test_cost_center_evidence_match_never_selects_an_ambiguous_center() -> None:
    observed = [{"cost_center_id": "CC-502", "baseline_row": "12"}]
    duplicate_observed = observed + [{"cost_center_id": "CC-502", "baseline_row": "31"}]
    ambiguous = observed + [{"cost_center_id": "CC-503", "baseline_row": "32"}]

    status, match = classify_baseline_matches([])
    assert (status, match) == ("UNMAPPED", None)

    status, match = classify_baseline_matches(duplicate_observed)
    assert status == "OBSERVED"
    assert match is not None and match["cost_center_id"] == "CC-502"

    status, match = classify_baseline_matches(ambiguous)
    assert (status, match) == ("AMBIGUOUS", None)


def test_missing_account_detail_stays_unclassified_instead_of_creating_candidate() -> None:
    indexes = {
        "TitkNo": 0,
        "TitMNo": 1,
        "TitTNo": 2,
        "titjno": 3,
        "شرح سرفصل حساب جزء": 4,
    }

    assert make_event_key(("611", "001", "00001", "00009", "NULL"), indexes) is None
