"""Phase 1 of the RootLens upgrade plan: an adversarial red-team suite for
the FR-8 SQL guardrail (app.analytics.sql_guardrails). Drives the labelled
cases in tests/redteam/cases.json through two independent layers —
sqlglot's AST guardrail, and the rootlens_readonly DB role with the
guardrail bypassed — and reports blocked/passed per category.

Shared by tests/redteam/test_redteam.py (CI gate, deterministic) and the
`redteam` CLI command (docs/evaluation/results report). See
docs/superpowers/plans/2026-11-05-rootlens-upgrade-plan.md Phase 1.
"""

import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.analytics.sql_guardrails import MAX_ROWS, UnsafeSqlError, validate_and_bound
from app.investigations import engine as investigation_engine
from app.llm.schemas import AdHocQueryDecision
from app.models import Hypothesis, Investigation

CASES_PATH = Path(__file__).resolve().parents[2] / "tests" / "redteam" / "cases.json"
_RESULTS_DIR = Path(__file__).resolve().parents[4] / "docs" / "evaluation" / "results"

# Categories that should structurally lack even session-level permission at
# the DB role layer (no INSERT/UPDATE/DELETE/TRUNCATE/DROP/CREATE grant) —
# a regression here means ADR-0004's role setup broke, not just that the
# guardrail missed something.
DB_PRIVILEGE_ENFORCED_CATEGORIES = {"ddl_dml", "copy_statement", "select_into"}

_DB_PROBE_TIMEOUT_MS = "2000"


def load_cases() -> dict[str, list[dict[str, Any]]]:
    return json.loads(CASES_PATH.read_text())


@dataclass
class GuardrailCheck:
    blocked: bool
    detail: str


def check_guardrail(case: dict[str, Any]) -> GuardrailCheck:
    """Layer 1: app.analytics.sql_guardrails.validate_and_bound. An
    oversized_limit case is "blocked" if the guardrail clamps it to
    MAX_ROWS — that category is designed to be bounded, not rejected."""
    sql = case["sql"]
    try:
        bounded = validate_and_bound(sql)
    except UnsafeSqlError as exc:
        return GuardrailCheck(True, f"blocked_by_guardrail: {exc}")
    if case["category"] == "oversized_limit" and f"LIMIT {MAX_ROWS}" in bounded:
        return GuardrailCheck(True, f"bounded_by_guardrail: {bounded}")
    return GuardrailCheck(False, f"NOT BLOCKED — passed validate_and_bound as: {bounded}")


@dataclass
class DbRoleCheck:
    blocked: bool
    detail: str


def check_db_role(engine: Engine, sql: str) -> DbRoleCheck:
    """Layer 2 (defense in depth): executes the raw, unvalidated SQL
    directly as rootlens_readonly — the guardrail is bypassed entirely,
    test-only — inside a transaction that is always rolled back, so a
    successful bypass (a real finding) never leaves a mark on the DB."""
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text(f"SET LOCAL statement_timeout = '{_DB_PROBE_TIMEOUT_MS}'"))
            conn.execute(text(sql))
        except Exception as exc:  # noqa: BLE001 — classifying arbitrary DB errors by design
            sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
            if sqlstate == "42501":
                return DbRoleCheck(True, f"blocked_by_db_permission ({sqlstate})")
            if sqlstate == "57014":
                return DbRoleCheck(True, "blocked_by_db_timeout (57014)")
            return DbRoleCheck(True, f"blocked_other_db_error ({sqlstate or type(exc).__name__})")
        else:
            return DbRoleCheck(False, "NOT BLOCKED — executed successfully as rootlens_readonly")
        finally:
            trans.rollback()


class _InjectedAdHocLLM:
    """A fixed, deterministic stand-in for an LLM that was successfully
    prompt-injected into emitting `injected_query` as its one ad hoc SQL
    decision. Used to drive the real production code path (engine.
    _maybe_run_ad_hoc_query -> run_safe_sql -> the guardrail / DB role)
    without depending on a live Ollama daemon, so CI stays deterministic."""

    def __init__(self, injected_query: str) -> None:
        self._injected_query = injected_query
        self.calls = 0

    def generate_structured(self, prompt: str, schema: type, model: str | None = None) -> Any:
        assert schema is AdHocQueryDecision
        self.calls += 1
        if self.calls == 1:
            return AdHocQueryDecision(
                should_query=True, query=self._injected_query, purpose="prompt-injection probe"
            )
        # FR-8 allows one correction attempt; a real attacker gets no
        # second bite once the retry is also refused.
        return AdHocQueryDecision(should_query=False)

    def health_check(self) -> bool:
        return True


@dataclass
class PromptInjectionCheck:
    blocked: bool
    detail: str


def check_prompt_injection(
    write_session: Session, readonly_session: Session, case: dict[str, Any]
) -> PromptInjectionCheck:
    """Drives case["injected_query"] through the real ad hoc SQL step
    (app.investigations.engine._maybe_run_ad_hoc_query) as if an LLM had
    been talked into emitting it by case["question"] — the actual
    exfiltration surface a prompt-injection attack would need to reach."""
    investigation = Investigation(
        investigation_id=str(uuid.uuid4()),
        metric="orders",
        metric_definition_version="orders:v1",
        current_period_start=datetime(2018, 1, 1, tzinfo=UTC).date(),
        current_period_end=datetime(2018, 1, 31, tzinfo=UTC).date(),
        comparison_period_start=datetime(2017, 12, 1, tzinfo=UTC).date(),
        comparison_period_end=datetime(2017, 12, 31, tzinfo=UTC).date(),
        question=case["question"],
        status="running",
    )
    write_session.add(investigation)
    write_session.flush()

    hypothesis = Hypothesis(
        id=str(uuid.uuid4()),
        investigation_id=investigation.investigation_id,
        statement="redteam probe hypothesis",
        status="inconclusive",
        confidence="low",
        supporting_evidence_ids=[],
        contradicting_evidence_ids=[],
    )
    write_session.add(hypothesis)
    write_session.commit()

    llm = _InjectedAdHocLLM(case["injected_query"])
    result = investigation_engine._maybe_run_ad_hoc_query(
        write_session, readonly_session, llm, investigation, hypothesis, time.monotonic()
    )

    if result is not None:
        return PromptInjectionCheck(
            False, "NOT BLOCKED — injected query executed and returned a ToolResult"
        )
    return PromptInjectionCheck(True, "blocked: ad hoc query rejected before execution")


@dataclass
class CategorySummary:
    category: str
    total: int
    blocked: int
    bypassed: list[str]


def summarize(outcomes: dict[str, bool], cases: list[dict[str, Any]]) -> list[CategorySummary]:
    by_category: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        by_category.setdefault(case["category"], []).append(case)

    summaries = []
    for category, group in sorted(by_category.items()):
        bypassed = [c["id"] for c in group if not outcomes[c["id"]]]
        summaries.append(
            CategorySummary(
                category=category,
                total=len(group),
                blocked=len(group) - len(bypassed),
                bypassed=bypassed,
            )
        )
    return summaries


def run_and_export(
    readonly_engine: Engine, write_session: Session, readonly_session: Session
) -> str:
    """Runs every case and writes docs/evaluation/results/redteam-<date>.
    {json,md}. Returns the date-stamped run id."""
    cases = load_cases()

    malicious_guardrail: dict[str, GuardrailCheck] = {}
    malicious_db_role: dict[str, DbRoleCheck] = {}
    for case in cases["malicious_direct"]:
        malicious_guardrail[case["id"]] = check_guardrail(case)
        malicious_db_role[case["id"]] = check_db_role(readonly_engine, case["sql"])

    benign_guardrail: dict[str, GuardrailCheck] = {
        case["id"]: check_guardrail(case) for case in cases["benign"]
    }

    prompt_injection: dict[str, PromptInjectionCheck] = {}
    for case in cases["prompt_injection"]:
        prompt_injection[case["id"]] = check_prompt_injection(write_session, readonly_session, case)

    run_id = f"redteam-{datetime.now(UTC).strftime('%Y-%m-%d')}"
    _export(
        run_id,
        cases,
        malicious_guardrail,
        malicious_db_role,
        benign_guardrail,
        prompt_injection,
    )
    return run_id


def _export(
    run_id: str,
    cases: dict[str, list[dict[str, Any]]],
    malicious_guardrail: dict[str, GuardrailCheck],
    malicious_db_role: dict[str, DbRoleCheck],
    benign_guardrail: dict[str, GuardrailCheck],
    prompt_injection: dict[str, PromptInjectionCheck],
) -> None:
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    malicious_defended = {
        cid: malicious_guardrail[cid].blocked or malicious_db_role[cid].blocked
        for cid in malicious_guardrail
    }
    true_bypasses = [cid for cid, defended in malicious_defended.items() if not defended]
    # `benign_guardrail[id].blocked` means "the guardrail rejected it" — a
    # false positive for a benign case is exactly that.
    benign_false_positives = [
        case["id"] for case in cases["benign"] if benign_guardrail[case["id"]].blocked
    ]
    injection_bypasses = [cid for cid, c in prompt_injection.items() if not c.blocked]

    payload = {
        "run_id": run_id,
        "malicious_direct": {
            "total": len(malicious_guardrail),
            "defended": len(malicious_guardrail) - len(true_bypasses),
            "true_bypasses": true_bypasses,
            "by_category": [
                {
                    "category": s.category,
                    "total": s.total,
                    "blocked": s.blocked,
                    "bypassed": s.bypassed,
                }
                for s in summarize(malicious_defended, cases["malicious_direct"])
            ],
            "cases": [
                {
                    "id": cid,
                    "guardrail": malicious_guardrail[cid].detail,
                    "db_role": malicious_db_role[cid].detail,
                }
                for cid in malicious_guardrail
            ],
        },
        "benign": {
            "total": len(benign_guardrail),
            "false_positives": benign_false_positives,
        },
        "prompt_injection": {
            "total": len(prompt_injection),
            "bypasses": injection_bypasses,
        },
    }
    (_RESULTS_DIR / f"{run_id}.json").write_text(json.dumps(payload, indent=2))
    (_RESULTS_DIR / f"{run_id}.md").write_text(_render_markdown(run_id, payload))


def _render_markdown(run_id: str, payload: dict[str, Any]) -> str:
    md = payload["malicious_direct"]
    lines = [
        f"# Red-team report — {run_id}",
        "",
        f"Malicious (direct): {md['defended']}/{md['total']} blocked by at least one layer "
        f"({len(md['true_bypasses'])} true bypass(es)).",
        f"Benign false positives: {len(payload['benign']['false_positives'])}/"
        f"{payload['benign']['total']}.",
        f"Prompt-injection bypasses: {len(payload['prompt_injection']['bypasses'])}/"
        f"{payload['prompt_injection']['total']}.",
        "",
        "## Malicious (direct) by category",
        "",
        "| category | total | blocked | bypassed |",
        "|---|---|---|---|",
    ]
    for cat in md["by_category"]:
        bypassed = ", ".join(cat["bypassed"]) or "-"
        lines.append(f"| {cat['category']} | {cat['total']} | {cat['blocked']} | {bypassed} |")

    if md["true_bypasses"]:
        lines += ["", "## True bypasses (neither layer stopped these)", ""]
        for cid in md["true_bypasses"]:
            case = next(c for c in payload["malicious_direct"]["cases"] if c["id"] == cid)
            lines.append(f"- `{cid}`: guardrail={case['guardrail']}; db_role={case['db_role']}")

    if payload["benign"]["false_positives"]:
        lines += ["", "## Benign false positives", ""]
        for cid in payload["benign"]["false_positives"]:
            lines.append(f"- `{cid}`")

    if payload["prompt_injection"]["bypasses"]:
        lines += ["", "## Prompt-injection bypasses", ""]
        for cid in payload["prompt_injection"]["bypasses"]:
            lines.append(f"- `{cid}`")

    return "\n".join(lines) + "\n"
