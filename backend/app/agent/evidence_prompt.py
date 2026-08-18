"""Versioned prompt for evidence sufficiency classification only."""

from __future__ import annotations

import json
from collections.abc import Sequence

from backend.app.retrieval.models import RetrievalCandidate


EVIDENCE_JUDGE_PROMPT_VERSION = "stage9b-evidence-v1"


def render_evidence(candidates: Sequence[RetrievalCandidate]) -> str:
    """Render only the Top-K provenance needed for a grounded evidence decision."""

    if not candidates:
        return "(No retrieved evidence.)"
    return "\n\n".join(
        "\n".join(
            (
                f"[E{index}]",
                f"chunk_id: {candidate.chunk_id}",
                f"source_title: {candidate.source_title}",
                f"section_title: {candidate.section_title}",
                f"source_url: {candidate.source_url}",
                f"content: {candidate.content}",
            )
        )
        for index, candidate in enumerate(candidates, start=1)
    )


def build_evidence_judge_system_prompt(schema: dict[str, object]) -> str:
    """Keep judgment semantics versioned and separate from provider transport."""

    schema_json = json.dumps(schema, ensure_ascii=False)
    return f"""You are FORAG Evidence Judge ({EVIDENCE_JUDGE_PROMPT_VERSION}).
Classify whether the supplied retrieval evidence alone can reliably support an answer to the original user question.

Return sufficient only when the current evidence contains the core facts needed to answer.
Return insufficient + retrieval_problem only when the user question has enough information but a different retrieval expression could reasonably find better evidence.
Return insufficient + missing_information only when essential user-specific information is absent and changing the retrieval expression cannot reliably resolve it.

Use only the supplied evidence. Do not use unstated world knowledge. Do not answer the question, create citations, rewrite the query, retrieve documents, invent user details, or return graph node names.
Return JSON only and obey this strict JSON Schema:
{schema_json}"""
