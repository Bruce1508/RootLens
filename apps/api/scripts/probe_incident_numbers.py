"""Debug tool for Phase 2 error analysis (docs/evaluation/error-analysis-*.md):
provisions a scenario's schema clone, applies its incident, and prints the raw
orders/cancellation_rate compare_periods numbers the decomposition prompt is
built from — bypassing the LLM and the full investigation engine entirely, so
it's cheap to re-run against any scenario id.

Usage (from apps/api, with the real dev DB running):
    PYTHONPATH=. uv run python scripts/probe_incident_numbers.py cs-01 ov-05 ...
"""

import sys

from sqlalchemy import select

from app.analytics.compare_periods import compare_periods
from app.analytics.schemas import DateRange
from app.db.session import WriteSessionLocal
from app.evaluation.incidents import apply_incident
from app.evaluation.scenario_schema import (
    provision_scenario_schema,
    scenario_schema_name,
    scenario_sessions,
    teardown_scenario_schema,
)
from app.models import EvalGroundTruth, EvalScenario


def probe(scenario_id: str) -> None:
    admin = WriteSessionLocal()
    scenario = admin.execute(
        select(EvalScenario).where(EvalScenario.scenario_id == scenario_id)
    ).scalar_one()
    ground_truth = admin.execute(
        select(EvalGroundTruth).where(EvalGroundTruth.scenario_id == scenario_id)
    ).scalar_one()
    admin.close()

    schema_name = scenario_schema_name(scenario_id)
    provisioning_session = WriteSessionLocal()
    provision_scenario_schema(provisioning_session, schema_name)
    provisioning_session.close()

    period = DateRange(start=scenario.current_period_start, end=scenario.current_period_end)
    comparison_period = DateRange(
        start=scenario.comparison_period_start, end=scenario.comparison_period_end
    )

    with scenario_sessions(schema_name) as (write_session, readonly_session):
        if not scenario.is_unanswerable:
            apply_incident(
                write_session,
                scenario.template,  # type: ignore[arg-type]
                period,
                ground_truth.dimensions,
                ground_truth.severity,
                scenario.seed,
            )
        orders = compare_periods(readonly_session, "orders", period, comparison_period)
        cancellation = compare_periods(
            readonly_session, "cancellation_rate", period, comparison_period
        )
        print(scenario_id, scenario.template, ground_truth.primary_driver, ground_truth.severity)
        print("  orders:", orders.rows[0])
        print("  cancellation:", cancellation.rows[0])

    teardown_session = WriteSessionLocal()
    teardown_scenario_schema(teardown_session, schema_name)
    teardown_session.close()


if __name__ == "__main__":
    for scenario_id in sys.argv[1:]:
        probe(scenario_id)
