from app.prompts.schemas import PromptDefinition

REPORT_GENERATOR_V1 = PromptDefinition(
    name="report_generator",
    version="v1",
    template=(
        "You are writing a business investigation report for the metric "
        "'{metric}'. The working hypothesis is: \"{hypothesis_statement}\" "
        "(status: {hypothesis_status}). The largest contributing segment "
        "found was '{dimension}', responsible for {top_share}% of the "
        "total change.\n\n"
        "Write a concise headline, a short list of findings, limitations, "
        "and recommended next checks. Every quantitative finding MUST cite "
        "one or more of these evidence IDs (do not invent others): "
        "{evidence_ids}.\n\n"
        "Only state numbers that are directly supported by the cited "
        "evidence. If a claim is an interpretation rather than a directly "
        "observed fact, set its claim_type to 'interpretation' instead of "
        "'observed_fact'. Do not claim external causality (e.g. "
        "competitor activity) that this data cannot support."
    ),
    description=(
        "Milestone 4 report-narrative prompt: given a resolved hypothesis "
        "and its evidence, produces a ReportNarrative "
        "(app.investigations.report_schemas.ReportNarrative) — headline, "
        "findings, limitations, recommended_next_checks. observed_change "
        "and status are computed deterministically in Python, never by "
        "the model (PRD §6 principle 4: deterministic business logic "
        "belongs in tested code, not prompts)."
    ),
)
