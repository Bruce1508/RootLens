"""Exercises app.evaluation.runner.run_evaluation end to end against a
small, committed synthetic dataset (not the real Olist dataset, and not
the real 35 app.evaluation.scenarios.SCENARIOS — those reference real
months/states this synthetic setup doesn't have).

Requires DATABASE_URL and DATABASE_URL_READONLY to both point at
rootlens_test for this process (see test_investigations_api.py's
docstring for why) — app.db.session's WriteSessionLocal/ReadOnlySessionLocal
and app.evaluation.scenario_schema.scenario_sessions all create their own
engines from app.core.config.Settings(), so they only touch the test
database when the test runner is invoked that way. Milestone 6 actually
uses the readonly role now (the engine's analytics reads run through it),
so DATABASE_URL_READONLY must be real rootlens_readonly credentials
against rootlens_test, not just a copy of TEST_DATABASE_URL:
    export DATABASE_URL="$TEST_DATABASE_URL"
    export DATABASE_URL_READONLY="postgresql+psycopg://rootlens_readonly:\
${ROOTLENS_READONLY_PASSWORD}@localhost:5432/rootlens_test"
    uv run pytest tests/integration/test_runner.py

Everything this test writes is committed (multiple real connections are
involved, so the usual rolled-back db_session fixture can't be used) and
is explicitly cleaned up in a `finally` block.
"""

import json
import os
from datetime import date, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.evaluation.runner import _RESULTS_DIR, run_evaluation
from app.investigations.report_schemas import ReportFinding, ReportNarrative
from app.llm.schemas import DecompositionPlan
from app.models import (
    Customer,
    EvalGroundTruth,
    EvalScenario,
    EvaluationCaseResult,
    EvaluationRun,
    Order,
    OrderItem,
    Product,
    Seller,
)

_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://rootlens_app:changeme_app@localhost:5432/rootlens_test",
)
_SPLIT = "integration_test_split"
_SCENARIO_ID = "it-01"


def _settings_point_at_test_database() -> bool:
    # app.evaluation.runner creates its own engines from
    # app.core.config.Settings().database_url (not from TEST_DATABASE_URL
    # directly) — this test's synthetic data and cleanup only land where
    # the runner itself will actually look if that resolves to the test
    # database too, e.g. `DATABASE_URL="$TEST_DATABASE_URL" pytest ...`.
    return "rootlens_test" in Settings().database_url


class _FakeLLM:
    def generate_structured(self, prompt: str, schema: type, model: str | None = None) -> object:
        if schema is DecompositionPlan:
            return DecompositionPlan(
                metric="product_revenue",
                primary_driver_hypothesis="order_volume",
                rationale="Order count fell while AOV stayed flat.",
                recommended_next_dimension="customer_state",
            )
        if schema is ReportNarrative:
            return ReportNarrative(
                headline="Order volume decline concentrated in SP",
                findings=[
                    ReportFinding(
                        claim="Order volume fell, concentrated in one state.",
                        claim_type="interpretation",
                        evidence_ids=[],
                        confidence="medium",
                    )
                ],
                limitations=["Synthetic integration-test data only."],
                recommended_next_checks=[],
            )
        raise AssertionError(f"unexpected schema {schema}")

    def health_check(self) -> bool:
        return True


def _make_engine() -> "sessionmaker":
    engine = create_engine(_TEST_DATABASE_URL)
    return sessionmaker(bind=engine)


def _seed_business_data(session_local: "sessionmaker") -> None:
    """Inserts 6 SP orders in Dec 2017 (comparison) and 3 in Jan 2018
    (current) — a real 50% order-volume decline for the engine to find,
    matching the order_volume_decline scenario seeded below."""
    session = session_local()
    try:
        session.add_all(
            [
                Product(product_id="it-prod-1", product_category_name="it_category"),
                Seller(
                    seller_id="it-seller-1",
                    seller_zip_code_prefix="0",
                    seller_city="c",
                    seller_state="SP",
                ),
                Customer(
                    customer_id="it-cust-sp",
                    customer_unique_id="it-cust-sp-u",
                    customer_zip_code_prefix="0",
                    customer_city="c",
                    customer_state="SP",
                ),
            ]
        )
        session.flush()

        order_ids = [f"it-order-2017-12-{day:02d}" for day in range(1, 7)] + [
            f"it-order-2018-01-{day:02d}" for day in range(1, 4)
        ]
        for order_id in order_ids:
            year, month, day = (int(part) for part in order_id.removeprefix("it-order-").split("-"))
            session.add(
                Order(
                    order_id=order_id,
                    customer_id="it-cust-sp",
                    order_status="delivered",
                    order_purchase_timestamp=datetime(year, month, day),
                    order_estimated_delivery_date=datetime(year, month, day),
                )
            )
        session.flush()

        for order_id in order_ids:
            session.add(
                OrderItem(
                    order_id=order_id,
                    order_item_id=1,
                    product_id="it-prod-1",
                    seller_id="it-seller-1",
                    shipping_limit_date=datetime(2018, 1, 20),
                    price=100.0,
                    freight_value=1.0,
                )
            )
        session.commit()
    finally:
        session.close()


def _seed_scenario(session_local: "sessionmaker") -> None:
    # Built directly as ORM rows rather than via ScenarioSpec — that
    # Pydantic model's `split` field is deliberately restricted to
    # "dev"/"held_out" (the real 35-scenario catalog's only valid splits),
    # which this test's throwaway split value isn't.
    session = session_local()
    try:
        session.add(
            EvalScenario(
                scenario_id=_SCENARIO_ID,
                template="order_volume_decline",
                metric="product_revenue",
                current_period_start=date(2018, 1, 1),
                current_period_end=date(2018, 1, 31),
                comparison_period_start=date(2017, 12, 1),
                comparison_period_end=date(2017, 12, 31),
                split=_SPLIT,
                seed=1,
                is_unanswerable=False,
                question=None,
            )
        )
        session.flush()
        session.add(
            EvalGroundTruth(
                scenario_id=_SCENARIO_ID,
                direction="decrease",
                primary_driver="order_volume",
                dimensions={"customer_state": "SP"},
                severity="medium",
                notes=None,
            )
        )
        session.commit()
    finally:
        session.close()


def _cleanup(session_local: "sessionmaker", run_id: str | None) -> None:
    session = session_local()
    try:
        if run_id is not None:
            session.execute(
                delete(EvaluationCaseResult).where(EvaluationCaseResult.run_id == run_id)
            )
            session.execute(delete(EvaluationRun).where(EvaluationRun.id == run_id))
            exported_path = _RESULTS_DIR / f"{run_id}.json"
            if exported_path.exists():
                exported_path.unlink()
        session.execute(delete(EvalGroundTruth).where(EvalGroundTruth.scenario_id == _SCENARIO_ID))
        session.execute(delete(EvalScenario).where(EvalScenario.scenario_id == _SCENARIO_ID))
        session.execute(text("DELETE FROM order_items WHERE order_id LIKE 'it-order-%'"))
        session.execute(text("DELETE FROM orders WHERE order_id LIKE 'it-order-%'"))
        session.execute(delete(Customer).where(Customer.customer_id == "it-cust-sp"))
        session.execute(delete(Seller).where(Seller.seller_id == "it-seller-1"))
        session.execute(delete(Product).where(Product.product_id == "it-prod-1"))
        session.commit()
    finally:
        session.close()


@pytest.mark.skipif(
    not _settings_point_at_test_database(),
    reason=(
        "requires DATABASE_URL pointed at rootlens_test for this process "
        "(app.evaluation.runner's engines read Settings().database_url) — see module docstring"
    ),
)
def test_run_evaluation_end_to_end_against_synthetic_data() -> None:
    session_local = _make_engine()
    run_id: str | None = None
    try:
        _seed_business_data(session_local)
        _seed_scenario(session_local)

        with patch("app.evaluation.runner.OllamaProvider", return_value=_FakeLLM()):
            run_id = run_evaluation(_SPLIT, model_name="fake-model")

        session = session_local()
        try:
            run = session.get(EvaluationRun, run_id)
            assert run is not None
            assert run.status == "completed"
            assert run.split == _SPLIT
            assert run.aggregate_metrics is not None
            assert run.aggregate_metrics["scenario_count"] == 1

            case = (
                session.query(EvaluationCaseResult)
                .filter(EvaluationCaseResult.run_id == run_id)
                .one()
            )
            assert case.scenario_id == _SCENARIO_ID
            assert case.investigation_id is not None
            assert case.status in ("pass", "fail")
            assert case.tool_call_count >= 3
        finally:
            session.close()

        exported = json.loads((_RESULTS_DIR / f"{run_id}.json").read_text())
        assert exported["run_id"] == run_id
        assert exported["split"] == _SPLIT
        assert len(exported["cases"]) == 1
    finally:
        _cleanup(session_local, run_id)
