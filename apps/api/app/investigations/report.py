import re

from app.analytics.schemas import ToolResult
from app.investigations.report_schemas import (
    InvestigationReport,
    ObservedChange,
    ReportFinding,
    ReportNarrative,
)
from app.llm.provider import LLMProvider
from app.models import Hypothesis, Investigation
from app.prompts.catalog import get_prompt_definition

_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_NUMERIC_RELATIVE_TOLERANCE = 0.05
_NUMERIC_ABSOLUTE_TOLERANCE = 0.5


def build_observed_change(metric: str, revenue_result: ToolResult) -> ObservedChange:
    row = revenue_result.rows[0]
    return ObservedChange(
        metric=metric,
        current_value=row["current_value"],
        comparison_value=row["comparison_value"],
        percent_change=row["percent_change"],
        evidence_ids=[revenue_result.evidence_id],
    )


def determine_status(hypothesis: Hypothesis, contribution_result: ToolResult) -> str:
    if not contribution_result.rows:
        return "insufficient_evidence"
    if hypothesis.status == "supported":
        return "answered"
    return "partial"


def generate_report(
    llm: LLMProvider,
    investigation: Investigation,
    hypothesis: Hypothesis,
    revenue_result: ToolResult,
    orders_result: ToolResult,
    cancellation_result: ToolResult,
    contribution_result: ToolResult,
) -> InvestigationReport:
    observed_change = build_observed_change(investigation.metric, revenue_result)
    status = determine_status(hypothesis, contribution_result)

    allowed_evidence_ids = {
        revenue_result.evidence_id,
        orders_result.evidence_id,
        cancellation_result.evidence_id,
        contribution_result.evidence_id,
    }
    evidence_by_id = {
        revenue_result.evidence_id: revenue_result,
        orders_result.evidence_id: orders_result,
        cancellation_result.evidence_id: cancellation_result,
        contribution_result.evidence_id: contribution_result,
    }

    narrative = _generate_narrative(
        llm, investigation, hypothesis, contribution_result, allowed_evidence_ids
    )
    problems = _check_narrative(narrative, allowed_evidence_ids, evidence_by_id)

    if problems:
        # PRD §20 failure mode "Report has unknown citation" / "Numerical
        # claim not found in evidence": regenerate once with feedback.
        narrative = _generate_narrative(
            llm,
            investigation,
            hypothesis,
            contribution_result,
            allowed_evidence_ids,
            retry_feedback=problems,
        )
        problems = _check_narrative(narrative, allowed_evidence_ids, evidence_by_id)

    if problems:
        # Still bad after one retry: deterministically repair rather than
        # fail the whole investigation — strip unknown citations, and
        # downgrade any remaining unsupported claim to "interpretation"
        # instead of removing it outright.
        narrative = _repair_narrative(narrative, allowed_evidence_ids, evidence_by_id)

    return InvestigationReport(
        status=status,
        headline=narrative.headline,
        observed_change=observed_change,
        findings=narrative.findings,
        limitations=narrative.limitations,
        recommended_next_checks=narrative.recommended_next_checks,
    )


def _generate_narrative(
    llm: LLMProvider,
    investigation: Investigation,
    hypothesis: Hypothesis,
    contribution_result: ToolResult,
    allowed_evidence_ids: set[str],
    retry_feedback: list[str] | None = None,
) -> ReportNarrative:
    top_row = contribution_result.rows[0] if contribution_result.rows else None
    top_share = top_row["share_of_total_change"] if top_row else None

    prompt = get_prompt_definition("report_generator").template.format(
        metric=investigation.metric,
        hypothesis_statement=hypothesis.statement,
        hypothesis_status=hypothesis.status,
        dimension=top_row["segment_value"] if top_row else "none",
        top_share=f"{abs(top_share) * 100:.1f}" if top_share is not None else "undefined",
        evidence_ids=", ".join(sorted(allowed_evidence_ids)),
    )
    if retry_feedback:
        prompt += "\n\nYour previous report had these problems, fix them:\n- " + "\n- ".join(
            retry_feedback
        )

    return llm.generate_structured(prompt, ReportNarrative)


def _check_narrative(
    narrative: ReportNarrative,
    allowed_evidence_ids: set[str],
    evidence_by_id: dict[str, ToolResult],
) -> list[str]:
    problems = []
    for i, finding in enumerate(narrative.findings):
        unknown = set(finding.evidence_ids) - allowed_evidence_ids
        if unknown:
            problems.append(f"finding {i}: cites unknown evidence_id(s) {sorted(unknown)}")
            continue
        if finding.claim_type == "observed_fact" and not _numbers_supported(
            finding, evidence_by_id
        ):
            problems.append(f"finding {i}: claim contains a number not found in its cited evidence")
    return problems


def _numbers_supported(finding: ReportFinding, evidence_by_id: dict[str, ToolResult]) -> bool:
    claimed_numbers = [float(n) for n in _NUMBER_PATTERN.findall(finding.claim)]
    if not claimed_numbers:
        return True

    evidence_numbers: list[float] = []
    for evidence_id in finding.evidence_ids:
        result = evidence_by_id.get(evidence_id)
        if result is None:
            continue
        for row in result.rows:
            for value in row.values():
                if not isinstance(value, int | float):
                    continue
                signed = float(value)
                # Claims are often phrased as a magnitude ("decreased by
                # 40%") against a signed evidence value (-0.4), so match
                # on both signed and absolute form.
                evidence_numbers.extend([signed, abs(signed)])
                # Tolerate percentage-form numbers (e.g. claim says
                # "40.0%" while the evidence row stores -0.4) — only for
                # fraction-scale values, otherwise a large dollar figure
                # times 100 creates a tolerance window wide enough to
                # match almost any nearby claimed number.
                if abs(signed) <= 1:
                    evidence_numbers.extend([signed * 100, abs(signed) * 100])

    def _within_tolerance(claimed: float, ev: float) -> bool:
        tolerance = max(_NUMERIC_RELATIVE_TOLERANCE * abs(ev), _NUMERIC_ABSOLUTE_TOLERANCE)
        return abs(claimed - ev) <= tolerance

    return all(
        any(_within_tolerance(claimed, ev) for ev in evidence_numbers)
        for claimed in claimed_numbers
    )


def _repair_narrative(
    narrative: ReportNarrative,
    allowed_evidence_ids: set[str],
    evidence_by_id: dict[str, ToolResult],
) -> ReportNarrative:
    repaired_findings = []
    for finding in narrative.findings:
        valid_ids = [eid for eid in finding.evidence_ids if eid in allowed_evidence_ids]
        claim_type = finding.claim_type
        narrowed = finding.model_copy(update={"evidence_ids": valid_ids})
        if not valid_ids or not _numbers_supported(narrowed, evidence_by_id):
            claim_type = "interpretation"
        repaired_findings.append(
            finding.model_copy(update={"evidence_ids": valid_ids, "claim_type": claim_type})
        )
    return narrative.model_copy(update={"findings": repaired_findings})
