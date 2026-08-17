"""Structure-first chunking for CleanDocument content."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Protocol

from .models import ChunkRecord, CleanDocument

MAX_CHUNK_TOKENS = 320
MIN_CHUNK_TOKENS = 60
FALLBACK_OVERLAP_TOKENS = 40
TOKENIZER_NAME = "intfloat/multilingual-e5-small"


class Tokenizer(Protocol):
    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]: ...
    def decode(self, tokens: list[int], skip_special_tokens: bool = True) -> str: ...


def load_tokenizer() -> Tokenizer:
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(TOKENIZER_NAME)


@dataclass
class _Unit:
    section_title: str
    text: str


def _heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    return (len(match.group(1)), match.group(2)) if match else None


def _parse_units(document: CleanDocument) -> list[_Unit]:
    lines: list[str] = []
    for raw_line in document.clean_content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parsed = _heading(line)
        if parsed and lines and lines[-1].strip() == parsed[1].strip():
            lines.pop()
        lines.append(line)
    units: list[_Unit] = []
    current_title = document.source_title
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            units.append(_Unit(current_title, "\n".join(current)))
            current = []

    for line in lines:
        parsed = _heading(line)
        if parsed:
            flush()
            current_title = parsed[1]
            current.append(line)
        else:
            current.append(line)
    flush()
    # Drop a heading-only duplicate when the same heading also has a substantive unit.
    substantive_titles = {unit.section_title for unit in units if len(unit.text.splitlines()) > 1}
    units = [unit for unit in units if len(unit.text.splitlines()) > 1 or unit.section_title not in substantive_titles]
    # A remaining heading-only unit is attached to the next substantive unit rather than
    # becoming an evidence-free Chunk; this also handles consecutive headings.
    merged: list[_Unit] = []
    pending: list[str] = []
    for unit in units:
        if all(_heading(line.strip()) for line in unit.text.splitlines() if line.strip()):
            pending.append(unit.text)
            continue
        if pending:
            unit = _Unit(unit.section_title, "\n".join(pending + [unit.text]))
            pending = []
        merged.append(unit)
    return merged


def _token_count(tokenizer: Tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))


def _fallback_split(text: str, tokenizer: Tokenizer) -> list[str]:
    tokens = tokenizer.encode(text, add_special_tokens=False)
    if not tokens:
        return []
    result: list[str] = []
    start = 0
    step = MAX_CHUNK_TOKENS - FALLBACK_OVERLAP_TOKENS
    while start < len(tokens):
        end = min(start + MAX_CHUNK_TOKENS, len(tokens))
        piece = tokenizer.decode(tokens[start:end], skip_special_tokens=True).strip()
        if piece:
            result.append(piece)
        if end >= len(tokens):
            break
        start += step
    return result


def _split_unit(unit: _Unit, tokenizer: Tokenizer) -> list[_Unit]:
    if _token_count(tokenizer, unit.text) <= MAX_CHUNK_TOKENS:
        return [unit]
    lines = unit.text.splitlines()
    groups: list[str] = []
    current: list[str] = []
    for line in lines:
        candidate = "\n".join(current + [line])
        if current and _token_count(tokenizer, candidate) > MAX_CHUNK_TOKENS:
            groups.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        groups.append("\n".join(current))

    if len(groups) > 1 and _heading(groups[0]):
        groups[1] = groups[0] + "\n" + groups[1]
        groups.pop(0)

    result: list[_Unit] = []
    for group in groups:
        if _token_count(tokenizer, group) <= MAX_CHUNK_TOKENS:
            result.append(_Unit(unit.section_title, group))
        else:
            result.extend(_Unit(unit.section_title, piece) for piece in _fallback_split(group, tokenizer))
    return result


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value or "section"


def chunk_document(document: CleanDocument, tokenizer: Tokenizer) -> list[ChunkRecord]:
    units: list[_Unit] = []
    for unit in _parse_units(document):
        units.extend(_split_unit(unit, tokenizer))
    records: list[ChunkRecord] = []
    seen_content: set[str] = set()
    for unit in units:
        content = unit.text.strip()
        if not content or content in seen_content:
            continue
        seen_content.add(content)
        order = len(records)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        chunk_id = f"{document.document_id}/{_slug(unit.section_title)}/{order:03d}"
        records.append(ChunkRecord(
            chunk_id=chunk_id, parent_doc_id=document.document_id,
            document_id=document.document_id, source_id=document.source_id,
            chunk_order=order, content=content, source_title=document.source_title,
            source_url=document.source_url, brand=document.brand,
            section_title=unit.section_title, content_hash=content_hash,
            kb_version="kb_v1",
        ))
    return records


def chunk_documents(documents: list[CleanDocument], tokenizer: Tokenizer) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for document in documents:
        chunks.extend(chunk_document(document, tokenizer))
    return chunks
