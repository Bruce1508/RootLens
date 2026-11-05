"""Phase 1 red-team suite (docs/superpowers/plans/2026-11-05-rootlens-upgrade-plan.md).

Deterministic by design: the prompt-injection cases drive a fixed,
in-memory stand-in LLM (app.evaluation.redteam._InjectedAdHocLLM) through
the real ad hoc SQL path, never a live Ollama daemon — this suite needs no
skip-if and runs in every CI invocation of `pytest tests`.
"""

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.evaluation.redteam import (
    DB_PRIVILEGE_ENFORCED_CATEGORIES,
    check_db_role,
    check_guardrail,
    check_prompt_injection,
    load_cases,
)

_CASES = load_cases()
_MALICIOUS = _CASES["malicious_direct"]
_BENIGN = _CASES["benign"]
_PROMPT_INJECTION = _CASES["prompt_injection"]


def test_case_files_meet_the_plans_minimum_counts() -> None:
    assert len(_MALICIOUS) >= 60
    assert len(_PROMPT_INJECTION) >= 20
    assert len(_BENIGN) >= 40


@pytest.mark.parametrize("case", _MALICIOUS, ids=[c["id"] for c in _MALICIOUS])
def test_malicious_direct_case_is_blocked_by_the_guardrail(case: dict) -> None:
    result = check_guardrail(case)
    assert result.blocked, f"{case['id']} ({case['category']}) was NOT blocked: {result.detail}"


@pytest.mark.parametrize(
    "case",
    [c for c in _MALICIOUS if c["category"] in DB_PRIVILEGE_ENFORCED_CATEGORIES],
    ids=lambda c: c["id"],
)
def test_malicious_write_case_is_also_blocked_by_the_db_role(
    case: dict, readonly_engine: Engine
) -> None:
    """Defense in depth for the categories that should structurally lack
    write/DDL privilege at the DB layer (ADR-0004) — a regression here
    means the role grant itself broke, independent of the guardrail."""
    result = check_db_role(readonly_engine, case["sql"])
    assert result.blocked, f"{case['id']} was NOT blocked by rootlens_readonly: {result.detail}"


@pytest.mark.parametrize("case", _MALICIOUS, ids=[c["id"] for c in _MALICIOUS])
def test_malicious_direct_case_db_role_probe_runs_without_leaving_a_mark(
    case: dict, readonly_engine: Engine
) -> None:
    """Runs the defense-in-depth probe for every malicious case (not just
    the write-shaped ones) so docs/evaluation/results/redteam-*.md can
    report the DB role's real coverage honestly — including categories
    (e.g. system catalog reads) where Postgres's own default grants mean
    the DB role is NOT expected to be the layer that stops it, because the
    guardrail (asserted separately above) already is."""
    check_db_role(readonly_engine, case["sql"])


@pytest.mark.parametrize("case", _BENIGN, ids=[c["id"] for c in _BENIGN])
def test_benign_case_is_not_a_false_positive(case: dict) -> None:
    result = check_guardrail(case)
    assert not result.blocked, f"{case['id']} ({case['category']}) false positive: {result.detail}"


@pytest.mark.parametrize("case", _PROMPT_INJECTION, ids=[c["id"] for c in _PROMPT_INJECTION])
def test_prompt_injection_case_never_reaches_the_database(
    case: dict, db_session: Session, readonly_db_session: Session
) -> None:
    result = check_prompt_injection(db_session, readonly_db_session, case)
    assert result.blocked, f"{case['id']} was NOT blocked: {result.detail}"
