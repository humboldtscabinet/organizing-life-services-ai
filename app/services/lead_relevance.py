"""Lead relevance scoring for SEO/content opportunities."""

from __future__ import annotations

from dataclasses import dataclass

HIGH_INTENT_TERMS = (
    "estate sale company",
    "estate sale companies",
    "estate sale service",
    "estate sale services",
    "estate sale organizer",
    "estate sale organizers",
    "estate sale liquidator",
    "estate liquidator",
    "estate liquidation",
    "estate cleanout",
    "estate clean out",
    "home cleanout",
    "house cleanout",
    "downsizing help",
    "senior downsizing",
    "probate estate sale",
    "organizing service",
)

MEDIUM_INTENT_TERMS = (
    "estate sale",
    "estate sales",
    "downsizing",
    "liquidation",
    "cleanout",
    "clean out",
    "organizing",
    "declutter",
    "appraisal",
    "probate",
    "moving sale",
)

SHOPPER_OR_RESEARCH_TERMS = (
    "near me",
    "today",
    "this weekend",
    "tomorrow",
    "pictures",
    "photos",
    "hours",
    "address",
    "what is",
    "meaning",
    "definition",
    "vs",
    "difference between",
    "buyers",
    "buy",
)

SERVICE_AREA_TERMS = (
    "tampa",
    "tampa bay",
    "clearwater",
    "largo",
    "dunedin",
    "palm harbor",
    "tarpon springs",
    "new port richey",
    "holiday",
    "hudson",
    "brooksville",
    "st petersburg",
    "saint petersburg",
    "pinellas",
    "pasco",
    "hillsborough",
    "hernando",
    "citrus",
    "manatee",
    "florida",
    "fl",
)


@dataclass(frozen=True)
class LeadRelevance:
    score: int
    tier: str
    reasons: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "lead_score": self.score,
            "lead_tier": self.tier,
            "lead_relevance_reasons": list(self.reasons),
        }


def score_lead_relevance(query: str, *, page: str | None = None) -> LeadRelevance:
    """
    Score how likely an SEO/content opportunity is to create real OLS leads.

    The score intentionally favors seller/client intent over raw traffic. A
    shopper query can still be useful, but it should not outrank a lower-volume
    query from someone looking for estate sale help.
    """
    text = " ".join(part for part in [query or "", page or ""] if part).lower()
    score = 25
    reasons: list[str] = []

    if any(term in text for term in HIGH_INTENT_TERMS):
        score += 45
        reasons.append("contains high-intent service language")
    elif any(term in text for term in MEDIUM_INTENT_TERMS):
        score += 25
        reasons.append("contains relevant estate sale/downsizing language")

    if any(term in text for term in SERVICE_AREA_TERMS):
        score += 20
        reasons.append("matches OLS service-area geography")

    if any(term in text for term in SHOPPER_OR_RESEARCH_TERMS):
        score -= 15
        reasons.append("appears partly shopper/research oriented")

    if not reasons:
        reasons.append("weak direct service intent")

    score = max(0, min(100, score))
    if score >= 70:
        tier = "HIGH"
    elif score >= 45:
        tier = "MEDIUM"
    else:
        tier = "LOW"

    return LeadRelevance(score=score, tier=tier, reasons=tuple(reasons))
