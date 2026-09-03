from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_write_session
from app.main import app
from app.models import EvalGroundTruth, EvalScenario, EvaluationCaseResult, EvaluationRun


def _seed_run(session: Session) -> None:
    session.add(
        EvalScenario(
            scenario_id="ov-01",
            template="order_volume_decline",
            metric="product_revenue",
            current_period_start=date(2018, 1, 1),
            current_period_end=date(2018, 1, 31),
            comparison_period_start=date(2017, 12, 1),
            comparison_period_end=date(2017, 12, 31),
            split="dev",
            seed=1,
            is_unanswerable=False,
            question=None,
        )
    )
    session.flush()
    session.add(
        EvalGroundTruth(
            scenario_id="ov-01",
            direction="decrease",
            primary_driver="order_volume",
            dimensions={"customer_state": "SP"},
            severity="medium",
        )
    )
    session.add(
        EvaluationRun(
            id="run-1",
            model_name="qwen3:8b",
            prompt_versions={"decomposition_planner": "v2"},
            config={"split": "dev"},
            split="dev",
            status="completed",
            aggregate_metrics={"scenario_count": 1, "root_cause_accuracy": 1.0},
        )
    )
    session.flush()
    session.add(
        EvaluationCaseResult(
            run_id="run-1",
            scenario_id="ov-01",
            investigation_id=None,
            predicted_direction="decrease",
            predicted_primary_driver="order_volume",
            predicted_dimensions={"customer_state": "SP"},
            correct_driver=True,
            correct_dimension=True,
            abstained=False,
            expected_abstain=False,
            evidence_citation_valid=True,
            tool_execution_success=True,
            unsupported_claim_count=0,
            total_claim_count=2,
            tool_call_count=4,
            latency_ms=1234.5,
            status="pass",
            notes=None,
        )
    )
    session.commit()


def test_list_evaluations_returns_seeded_run(db_session: Session) -> None:
    _seed_run(db_session)
    app.dependency_overrides[get_write_session] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.get("/api/evaluations")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["run_id"] == "run-1"
    assert body[0]["aggregate_metrics"]["root_cause_accuracy"] == 1.0


def test_get_evaluation_returns_run_detail_with_scenario_metadata(db_session: Session) -> None:
    _seed_run(db_session)
    app.dependency_overrides[get_write_session] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.get("/api/evaluations/run-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run-1"
    assert len(body["cases"]) == 1
    case = body["cases"][0]
    assert case["scenario_id"] == "ov-01"
    assert case["template"] == "order_volume_decline"
    assert case["is_unanswerable"] is False
    assert case["status"] == "pass"


def test_get_evaluation_returns_404_for_unknown_run(db_session: Session) -> None:
    app.dependency_overrides[get_write_session] = lambda: db_session
    try:
        client = TestClient(app)
        response = client.get("/api/evaluations/does-not-exist")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
