"""Versioned grounded-answer prompt for Stage 10."""

from __future__ import annotations

import json
from collections.abc import Sequence

from backend.app.retrieval.models import RetrievalCandidate


ANSWER_PROMPT_VERSION = "stage10-answer-v1"


def render_answer_evidence(candidates: Sequence[RetrievalCandidate]) -> str:
    """Assign stable E1..En identifiers without exposing source metadata for generation."""

    if not candidates:
        return "(No retrieved evidence.)"
    return "\n\n".join(
        f"[E{index}]\ncontent: {candidate.content}"
        for index, candidate in enumerate(candidates, start=1)
    )


def build_answer_system_prompt(schema: dict[str, object]) -> str:
    """Keep grounded-answer business instructions outside the shared transport."""

    schema_json = json.dumps(schema, ensure_ascii=False)
    return f"""You are FORAG Answer Generator ({ANSWER_PROMPT_VERSION}).
Answer in the language of the original user question using only the supplied Evidence.

Do not use unstated world knowledge, invent facts, URLs, source titles, source metadata, or Evidence IDs. Do not answer facts unsupported by Evidence. Every key factual claim must have one or more inline citations in the exact form [E1], [E2], and so on. Do not output reasoning or chain-of-thought.

Return JSON only and obey this strict JSON Schema:
{schema_json}"""


def build_answer_user_message(
    original_query: str,
    evidence: Sequence[RetrievalCandidate],
) -> str:
    """Supply only the original question and its current evidence snapshot."""

    return f"Original user question:\n{original_query}\n\nEvidence:\n{render_answer_evidence(evidence)}"
