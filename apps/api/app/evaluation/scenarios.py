"""Milestone 5 incident-benchmark scenarios (FR-13), version-controlled in
code per the same pattern as app.metrics.catalog / app.prompts.catalog
(ADR-0005 / ADR-0006). app.evaluation.seed loads these into the hidden
`eval` schema (ADR-0007).

Grounded in the real ingested Olist dataset (verified locally: orders span
2016-09..2018-10, with 2017-02..2018-08 carrying thousands of orders/month
across every state/category referenced below — see the Milestone 5 plan's
"clean benchmark slice" note). 35 scenarios total:

- 10 cancellation_spike (by customer_state + product_category)
- 10 order_volume_decline (by customer_state)
- 10 seller_category_decline — 5 targeting a product_category directly, 5
  targeting a single seller *within* a product_category (resolved from real
  data at seed time, see SELLER_TO_RESOLVE)
- 5 unanswerable (natural variance only; question references data RootLens
  doesn't have, per PRD §8.3)

Split ~24 dev / ~11 held-out (PRD §18: never tune on held-out), each split
containing a mix of all three templates plus unanswerable cases.
"""

import calendar
from datetime import date

from app.evaluation.schemas import SELLER_TO_RESOLVE, ScenarioSpec


def _month(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _period(current: tuple[int, int], comparison: tuple[int, int]) -> dict[str, date]:
    current_start, current_end = _month(*current)
    comparison_start, comparison_end = _month(*comparison)
    return {
        "current_period_start": current_start,
        "current_period_end": current_end,
        "comparison_period_start": comparison_start,
        "comparison_period_end": comparison_end,
    }


_CANCELLATION_SPIKE: list[ScenarioSpec] = [
    ScenarioSpec(
        scenario_id="cs-01",
        template="cancellation_spike",
        split="dev",
        seed=101,
        severity="high",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "SP", "product_category": "cama_mesa_banho"},
        **_period((2017, 9), (2017, 8)),
    ),
    ScenarioSpec(
        scenario_id="cs-02",
        template="cancellation_spike",
        split="dev",
        seed=102,
        severity="medium",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "RJ", "product_category": "beleza_saude"},
        **_period((2017, 11), (2017, 10)),
    ),
    ScenarioSpec(
        scenario_id="cs-03",
        template="cancellation_spike",
        split="dev",
        seed=103,
        severity="high",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "MG", "product_category": "esporte_lazer"},
        **_period((2018, 2), (2018, 1)),
    ),
    ScenarioSpec(
        scenario_id="cs-04",
        template="cancellation_spike",
        split="dev",
        seed=104,
        severity="low",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "RS", "product_category": "moveis_decoracao"},
        **_period((2018, 4), (2018, 3)),
    ),
    ScenarioSpec(
        scenario_id="cs-05",
        template="cancellation_spike",
        split="dev",
        seed=105,
        severity="medium",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "PR", "product_category": "informatica_acessorios"},
        **_period((2017, 6), (2017, 5)),
    ),
    ScenarioSpec(
        scenario_id="cs-06",
        template="cancellation_spike",
        split="dev",
        seed=106,
        severity="high",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "SC", "product_category": "utilidades_domesticas"},
        **_period((2017, 8), (2017, 7)),
    ),
    ScenarioSpec(
        scenario_id="cs-07",
        template="cancellation_spike",
        split="dev",
        seed=107,
        severity="medium",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "BA", "product_category": "relogios_presentes"},
        **_period((2018, 6), (2018, 5)),
    ),
    ScenarioSpec(
        scenario_id="cs-08",
        template="cancellation_spike",
        split="held_out",
        seed=108,
        severity="low",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "DF", "product_category": "telefonia"},
        **_period((2017, 12), (2017, 11)),
    ),
    ScenarioSpec(
        scenario_id="cs-09",
        template="cancellation_spike",
        split="held_out",
        seed=109,
        severity="high",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "ES", "product_category": "ferramentas_jardim"},
        **_period((2018, 7), (2018, 6)),
    ),
    ScenarioSpec(
        scenario_id="cs-10",
        template="cancellation_spike",
        split="held_out",
        seed=110,
        severity="medium",
        direction="decrease",
        primary_driver="cancellation",
        dimensions={"customer_state": "GO", "product_category": "automotivo"},
        **_period((2017, 4), (2017, 3)),
    ),
]

_ORDER_VOLUME_DECLINE: list[ScenarioSpec] = [
    ScenarioSpec(
        scenario_id="ov-01",
        template="order_volume_decline",
        split="dev",
        seed=201,
        severity="medium",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "SP"},
        **_period((2018, 3), (2018, 2)),
    ),
    ScenarioSpec(
        scenario_id="ov-02",
        template="order_volume_decline",
        split="dev",
        seed=202,
        severity="high",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "RJ"},
        **_period((2017, 10), (2017, 9)),
    ),
    ScenarioSpec(
        scenario_id="ov-03",
        template="order_volume_decline",
        split="dev",
        seed=203,
        severity="low",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "MG"},
        **_period((2018, 5), (2018, 4)),
    ),
    ScenarioSpec(
        scenario_id="ov-04",
        template="order_volume_decline",
        split="dev",
        seed=204,
        severity="medium",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "RS"},
        **_period((2017, 7), (2017, 6)),
    ),
    ScenarioSpec(
        scenario_id="ov-05",
        template="order_volume_decline",
        split="dev",
        seed=205,
        severity="high",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "PR"},
        **_period((2018, 8), (2018, 7)),
    ),
    ScenarioSpec(
        scenario_id="ov-06",
        template="order_volume_decline",
        split="dev",
        seed=206,
        severity="low",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "SC"},
        **_period((2018, 1), (2017, 12)),
    ),
    ScenarioSpec(
        scenario_id="ov-07",
        template="order_volume_decline",
        split="dev",
        seed=207,
        severity="medium",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "BA"},
        **_period((2018, 2), (2018, 1)),
    ),
    ScenarioSpec(
        scenario_id="ov-08",
        template="order_volume_decline",
        split="held_out",
        seed=208,
        severity="high",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "DF"},
        **_period((2017, 5), (2017, 4)),
    ),
    ScenarioSpec(
        scenario_id="ov-09",
        template="order_volume_decline",
        split="held_out",
        seed=209,
        severity="low",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "ES"},
        **_period((2017, 9), (2017, 8)),
    ),
    ScenarioSpec(
        scenario_id="ov-10",
        template="order_volume_decline",
        split="held_out",
        seed=210,
        severity="medium",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"customer_state": "GO"},
        **_period((2018, 6), (2018, 5)),
    ),
]

_SELLER_CATEGORY_DECLINE: list[ScenarioSpec] = [
    # Category-flavored: dimensions target product_category directly.
    ScenarioSpec(
        scenario_id="sc-01",
        template="seller_category_decline",
        split="dev",
        seed=301,
        severity="medium",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"product_category": "cama_mesa_banho"},
        **_period((2017, 10), (2017, 9)),
    ),
    ScenarioSpec(
        scenario_id="sc-02",
        template="seller_category_decline",
        split="dev",
        seed=302,
        severity="high",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"product_category": "beleza_saude"},
        **_period((2018, 3), (2018, 2)),
    ),
    ScenarioSpec(
        scenario_id="sc-03",
        template="seller_category_decline",
        split="dev",
        seed=303,
        severity="low",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"product_category": "esporte_lazer"},
        **_period((2017, 6), (2017, 5)),
    ),
    ScenarioSpec(
        scenario_id="sc-04",
        template="seller_category_decline",
        split="dev",
        seed=304,
        severity="medium",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"product_category": "moveis_decoracao"},
        **_period((2018, 7), (2018, 6)),
    ),
    ScenarioSpec(
        scenario_id="sc-05",
        template="seller_category_decline",
        split="dev",
        seed=305,
        severity="high",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"product_category": "informatica_acessorios"},
        **_period((2017, 12), (2017, 11)),
    ),
    # Seller-flavored: target seller resolved at seed time within the given
    # category during the incident month (see SELLER_TO_RESOLVE).
    ScenarioSpec(
        scenario_id="sc-06",
        template="seller_category_decline",
        split="dev",
        seed=306,
        severity="medium",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"seller": SELLER_TO_RESOLVE, "product_category": "utilidades_domesticas"},
        **_period((2018, 4), (2018, 3)),
    ),
    ScenarioSpec(
        scenario_id="sc-07",
        template="seller_category_decline",
        split="dev",
        seed=307,
        severity="high",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"seller": SELLER_TO_RESOLVE, "product_category": "relogios_presentes"},
        **_period((2017, 8), (2017, 7)),
    ),
    ScenarioSpec(
        scenario_id="sc-08",
        template="seller_category_decline",
        split="held_out",
        seed=308,
        severity="low",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"seller": SELLER_TO_RESOLVE, "product_category": "telefonia"},
        **_period((2018, 5), (2018, 4)),
    ),
    ScenarioSpec(
        scenario_id="sc-09",
        template="seller_category_decline",
        split="held_out",
        seed=309,
        severity="medium",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"seller": SELLER_TO_RESOLVE, "product_category": "ferramentas_jardim"},
        **_period((2017, 11), (2017, 10)),
    ),
    ScenarioSpec(
        scenario_id="sc-10",
        template="seller_category_decline",
        split="held_out",
        seed=310,
        severity="high",
        direction="decrease",
        primary_driver="order_volume",
        dimensions={"seller": SELLER_TO_RESOLVE, "product_category": "automotivo"},
        **_period((2018, 2), (2018, 1)),
    ),
]

_UNANSWERABLE: list[ScenarioSpec] = [
    ScenarioSpec(
        scenario_id="ua-01",
        template="order_volume_decline",  # nominal — no incident is applied
        split="dev",
        seed=401,
        is_unanswerable=True,
        question=(
            "Why did revenue decline? Our competitor cut prices sharply this "
            "period — did we lose sales to them?"
        ),
        notes="Requires competitor pricing data RootLens does not have.",
        **_period((2017, 5), (2017, 4)),
    ),
    ScenarioSpec(
        scenario_id="ua-02",
        template="order_volume_decline",
        split="dev",
        seed=402,
        is_unanswerable=True,
        question="Did our reduced advertising spend this period cause the revenue change?",
        notes="Requires marketing/ad-spend data RootLens does not have.",
        **_period((2017, 10), (2017, 9)),
    ),
    ScenarioSpec(
        scenario_id="ua-03",
        template="order_volume_decline",
        split="dev",
        seed=403,
        is_unanswerable=True,
        question="Did customer sentiment about our brand shift this period?",
        notes="Requires customer survey/interview data RootLens does not have.",
        **_period((2018, 4), (2018, 3)),
    ),
    ScenarioSpec(
        scenario_id="ua-04",
        template="order_volume_decline",
        split="held_out",
        seed=404,
        is_unanswerable=True,
        question="Did a drop in website traffic explain the change in orders?",
        notes="Requires web-analytics/marketing-funnel data RootLens does not have.",
        **_period((2018, 6), (2018, 5)),
    ),
    ScenarioSpec(
        scenario_id="ua-05",
        template="order_volume_decline",
        split="held_out",
        seed=405,
        is_unanswerable=True,
        question="Was the change caused by macroeconomic conditions in Brazil that period?",
        notes="Requires macroeconomic data RootLens does not have.",
        **_period((2018, 1), (2017, 12)),
    ),
]

SCENARIOS: list[ScenarioSpec] = [
    *_CANCELLATION_SPIKE,
    *_ORDER_VOLUME_DECLINE,
    *_SELLER_CATEGORY_DECLINE,
    *_UNANSWERABLE,
]


def scenarios_for_split(split: str) -> list[ScenarioSpec]:
    return [s for s in SCENARIOS if s.split == split]
