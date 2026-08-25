from hunter_piggy_signal_router import HunterPiggySignalRouter, RiskLevel
from kai_operator import KaiOperator


def signal_names(result):
    return {signal.name for signal in result.signals}


def test_benign_text_is_low_without_review():
    router = HunterPiggySignalRouter(enable_optional_modules=False)

    result = router.analyze("Dzień dobry, jak się masz?")

    assert result.risk_level == RiskLevel.LOW
    assert result.risk_score == 0
    assert result.human_review_recommended is False


def test_phishing_style_message_is_prioritized_for_review():
    router = HunterPiggySignalRouter(enable_optional_modules=False)

    result = router.analyze(
        "Pilne!!! Twoje konto zostało zablokowane. "
        "Potwierdź tożsamość: http://bit.ly/confirm123"
    )

    assert result.risk_level in {RiskLevel.HIGH, RiskLevel.URGENT_REVIEW}
    assert result.human_review_recommended is True
    assert {"url_shortener", "credential_or_verification_url_pattern", "manipulative_or_scam_language"}.issubset(signal_names(result))
    assert result.correlation_boosts


def test_osint_and_sensitive_context_correlation_is_explainable():
    router = HunterPiggySignalRouter(enable_optional_modules=False)

    result = router.analyze(
        "Co zrobić gdy dziecko jest narażone na niebezpieczne treści? "
        "http://phishing-site.com/verify"
    )

    assert "osint_domain_flagged" in signal_names(result)
    assert "sensitive_priority_context" in signal_names(result)
    assert result.human_review_recommended is True
    assert result.explainability.data_audit
    assert result.explainability.limitations


def test_validation_error_returns_safe_result():
    router = HunterPiggySignalRouter(enable_optional_modules=False)

    result = router.analyze("")

    assert result.risk_level == RiskLevel.LOW
    assert result.confidence == 1.0
    assert result.intuition_signal == "not_run"
    assert result.human_review_recommended is False


def test_kai_operator_exposes_hunter_piggy_integration():
    kai = KaiOperator()

    result = kai.analyze_public_signal("urgent click here http://fake-login.xyz/verify")

    assert result.human_review_recommended is True
    assert kai.diagnostics()["HunterPiggy"] == "active"
