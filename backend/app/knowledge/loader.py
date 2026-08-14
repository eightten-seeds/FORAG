import hashlib
import json
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from .models import RawDocument, SourceRecord


class ManifestError(ValueError):
    """Raised when a source manifest record is invalid."""


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_path(local_path: str, root: Path) -> Path:
    path = Path(local_path)
    return path if path.is_absolute() else root / path


def read_manifest(path: str | Path | None = None) -> list[SourceRecord]:
    manifest_path = Path(path) if path else _repository_root() / "data/manifests/sources.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Source manifest not found: {manifest_path}")

    records: list[SourceRecord] = []
    for line_number, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(SourceRecord.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ManifestError(f"Invalid manifest record at line {line_number}") from exc
    return records


def load_sources(
    manifest_path: str | Path | None = None,
    *,
    repository_root: str | Path | None = None,
) -> list[RawDocument]:
    root = Path(repository_root) if repository_root else _repository_root()
    documents: list[RawDocument] = []
    for source in read_manifest(manifest_path):
        if not source.enabled:
            continue
        local_file = _resolve_path(source.local_path, root)
        if not local_file.is_file():
            raise FileNotFoundError(f"Source file not found: {local_file}")
        content = local_file.read_text(encoding="utf-8")
        document_id = source.source_id
        documents.append(
            RawDocument(
                document_id=document_id,
                source_id=source.source_id,
                brand=source.brand,
                source_type=source.source_type,
                source_title=source.source_title,
                source_url=source.source_url,
                language=source.language,
                accessed_at=source.accessed_at,
                raw_content=content,
                content_hash=source.content_hash or hashlib.sha256(content.encode()).hexdigest(),
            )
        )
    return documents
