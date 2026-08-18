"""Versioned, centralized prompt construction for Query Analysis."""

from __future__ import annotations

import json
from typing import Any


QUERY_ANALYSIS_PROMPT_VERSION = "stage8a-v1"

_SYSTEM_PROMPT_TEMPLATE = """You are the Query Analysis component for an outdoor functional garment-care retrieval system.

Return JSON only. Do not answer the user's question, give advice, cite sources, generate evidence, or add commentary.

Extract concise English lexical terms suitable for searching an English official-care knowledge base. Preserve explicitly stated brand names, technology names, material names, care actions, and problem terminology when relevant. Do not invent brands, technologies, facts, or evidence. Every structured field must be supported by the user question; use null or an empty array when the user did not explicitly provide the corresponding entity.

The JSON must conform to this schema. No additional fields are allowed:
{schema}
"""


def build_query_analysis_system_prompt(schema: dict[str, Any]) -> str:
    """Render the single versioned prompt with the local typed-schema contract."""

    return _SYSTEM_PROMPT_TEMPLATE.format(
        schema=json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
    )
