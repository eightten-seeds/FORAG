"""Deterministic Stage 10 citation validation and source mapping."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from backend.app.agent.answer_models import AnswerDraft, FinalResponse, SourceCitation
from backend.app.retrieval.models import RetrievalCandidate

_INLINE_CITATION_PATTERN = re.compile(r"\[E(\d+)\]")
_RAW_URL_PATTERN = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)


class AnswerValidationError(ValueError):
    """Raised when a generated grounded answer has invalid citations."""


@dataclass(frozen=True)
class CitationValidationResult:
    """Validated citations in first-inline-appearance order."""

    cited_evidence_ids: tuple[str, ...]


def evidence_id_map(evidence: Sequence[RetrievalCandidate]) -> dict[str, RetrievalCandidate]:
    """Assign E1..En directly from the current retrieval snapshot order."""

    return {f"E{index}": candidate for index, candidate in enumerate(evidence, start=1)}


def _deduplicate_in_order(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def validate_citations(
    draft: AnswerDraft,
    evidence: Sequence[RetrievalCandidate],
) -> CitationValidationResult:
    """Reject malformed, unknown, or missing citations, reconciling inline citations as authoritative."""

    if _RAW_URL_PATTERN.search(draft.answer):
        raise AnswerValidationError("Answer must not contain raw URLs; sources come from evidence provenance.")

    available = evidence_id_map(evidence)
    inline_ids = tuple(f"E{number}" for number in _INLINE_CITATION_PATTERN.findall(draft.answer))
    if not inline_ids:
        raise AnswerValidationError("Answered output must contain at least one inline [E#] citation.")

    inline_set = set(inline_ids)
    unknown_inline = inline_set.difference(available)
    if unknown_inline:
        unknown = sorted(unknown_inline)
        raise AnswerValidationError(f"Citation IDs are not present in the current evidence: {unknown}.")

    # Deterministic Citation Reconciliation:
    # Valid inline [E#] citations in the answer body are the authoritative source of truth.
    # We reconcile the final citation list to the inline citations in order of first appearance.
    canonical_citation_ids = _deduplicate_in_order(inline_ids)
    return CitationValidationResult(cited_evidence_ids=canonical_citation_ids)


def map_sources(
    citation_ids: Sequence[str],
    evidence: Sequence[RetrievalCandidate],
) -> list[SourceCitation]:
    """Map valid IDs to current candidate provenance without any Elasticsearch lookup."""

    available = evidence_id_map(evidence)
    sources: list[SourceCitation] = []
    for evidence_id in _deduplicate_in_order(citation_ids):
        candidate = available.get(evidence_id)
        if candidate is None:
            raise AnswerValidationError(f"Citation ID is not present in the current evidence: {evidence_id}.")
        sources.append(
            SourceCitation(
                evidence_id=evidence_id,
                chunk_id=candidate.chunk_id,
                source_title=candidate.source_title,
                section_title=candidate.section_title,
                source_url=candidate.source_url,
            )
        )
    return sources


def build_answered_final_response(
    draft: AnswerDraft,
    evidence: Sequence[RetrievalCandidate],
) -> FinalResponse:
    """Validate a draft before projecting deterministic candidate provenance into FinalResponse."""

    validation = validate_citations(draft, evidence)
    return FinalResponse(
        status="answered",
        answer=draft.answer,
        sources=map_sources(validation.cited_evidence_ids, evidence),
    )
