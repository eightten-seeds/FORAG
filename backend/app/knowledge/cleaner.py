import re

from .models import CleanDocument, RawDocument


_NOISE_LINE = re.compile(
    r"^(?:cookie(?: policy| notice)?|accept cookies|privacy policy|terms of use|"
    r"subscribe|sign up|newsletter|all rights reserved|home\s*[|>]\s*navigation)\s*$",
    re.IGNORECASE,
)
_HTML_TAG = re.compile(r"<[^>]+>")


def clean_document(document: RawDocument) -> CleanDocument:
    lines: list[str] = []
    for raw_line in document.raw_content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = _HTML_TAG.sub("", raw_line).strip()
        if not line or _NOISE_LINE.match(line):
            continue
        lines.append(re.sub(r"[ \t]+", " ", line))

    # Collapse only directly repeated lines; preserve headings, lists, warnings and order.
    kept: list[str] = []
    for line in lines:
        if not kept or line != kept[-1]:
            kept.append(line)

    sections = [line for line in kept if _is_heading(line)]
    return CleanDocument(
        document_id=document.document_id,
        source_id=document.source_id,
        source_title=document.source_title,
        source_url=document.source_url,
        brand=document.brand,
        language=document.language,
        sections=sections,
        clean_content="\n".join(kept),
        content_hash=document.content_hash,
    )


def _is_heading(line: str) -> bool:
    return bool(
        re.match(r"^#{1,6}\s+\S", line)
        or re.match(r"^(?:warning|caution|note)\s*[:：]", line, re.IGNORECASE)
    )


def clean_documents(documents: list[RawDocument]) -> list[CleanDocument]:
    return [clean_document(document) for document in documents]
