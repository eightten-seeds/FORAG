"""Versioned prompt for a single retrieval-oriented Query Rewrite."""

from __future__ import annotations

import json
from collections.abc import Sequence

from backend.app.agent.evidence_prompt import render_evidence
from backend.app.retrieval.models import RetrievalCandidate


QUERY_REWRITE_PROMPT_VERSION = "stage9b-rewrite-v1"


def build_query_rewrite_system_prompt(schema: dict[str, object]) -> str:
    """Keep rewrite business semantics outside the shared LLM transport."""

    schema_json = json.dumps(schema, ensure_ascii=False)
    return f"""You are FORAG Query Rewriter ({QUERY_REWRITE_PROMPT_VERSION}).
The current retrieval did not sufficiently cover a user question, but the question itself has enough information. Produce one concise reformulated query that preserves the original user intent and is better suited to retrieval.

Do not answer the question, create citations, invent facts or entities, use unavailable information, emit multiple candidates, run Query Analysis, or include commentary.
Return JSON only and obey this strict JSON Schema:
{schema_json}"""


def build_query_rewrite_user_message(
    original_query: str,
    evidence: Sequence[RetrievalCandidate],
) -> str:
    """Supply only the original question and current retrieval context."""

    return f"Original user question:\n{original_query}\n\nCurrent retrieval context:\n{render_evidence(evidence)}"
