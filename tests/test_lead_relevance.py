from app.services.lead_relevance import score_lead_relevance


def test_high_intent_local_query_scores_high():
    score = score_lead_relevance("estate sale company clearwater fl")

    assert score.tier == "HIGH"
    assert score.score >= 70
    assert "contains high-intent service language" in score.reasons
    assert "matches OLS service-area geography" in score.reasons


def test_shopper_research_query_is_deprioritized():
    score = score_lead_relevance("estate sales near me this weekend")

    assert score.score < 70
    assert score.tier in {"LOW", "MEDIUM"}
    assert "appears partly shopper/research oriented" in score.reasons
