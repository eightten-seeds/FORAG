import json
from pathlib import Path

import pytest

from backend.app.knowledge.cleaner import clean_document
from backend.app.knowledge.loader import ManifestError, load_sources, read_manifest
from backend.app.knowledge.models import RawDocument


def _record(path: str) -> dict[str, object]:
    return {
        "source_id": "src_test",
        "brand": "Test Brand",
        "source_type": "product_care",
        "source_title": "Test Care Guide",
        "source_url": "https://brand.example/care",
        "language": "en",
        "accessed_at": "2026-08-14",
        "local_path": path,
        "content_hash": "fixture-hash",
        "enabled": True,
    }


def _write_manifest(tmp_path: Path, record: dict[str, object]) -> Path:
    manifest = tmp_path / "sources.jsonl"
    manifest.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return manifest


def test_manifest_load_and_local_file(tmp_path: Path) -> None:
    source = tmp_path / "raw.txt"
    source.write_text("# Washing\nWash gently.\n", encoding="utf-8")
    docs = load_sources(_write_manifest(tmp_path, _record("raw.txt")), repository_root=tmp_path)
    assert len(docs) == 1
    assert docs[0].raw_content.startswith("# Washing")


def test_missing_source_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_sources(_write_manifest(tmp_path, _record("missing.txt")), repository_root=tmp_path)


def test_required_manifest_field_missing(tmp_path: Path) -> None:
    record = _record("raw.txt")
    del record["source_url"]
    with pytest.raises(ManifestError):
        read_manifest(_write_manifest(tmp_path, record))


def test_cleaner_removes_noise_and_preserves_content() -> None:
    raw = RawDocument(
        document_id="src_test",
        source_id="src_test",
        brand="Test Brand",
        source_type="product_care",
        source_title="Test Care Guide",
        source_url="https://brand.example/care",
        language="en",
        accessed_at="2026-08-14",
        raw_content="# Washing\n\nWash gently.\n- Do not bleach\nWARNING: Air dry.\nCookie Notice\nWash gently.\n",
        content_hash="fixture-hash",
    )
    clean = clean_document(raw)
    assert "Cookie Notice" not in clean.clean_content
    assert "Wash gently." in clean.clean_content
    assert "- Do not bleach" in clean.clean_content
    assert "WARNING: Air dry." in clean.clean_content
    assert clean.sections == ["# Washing", "WARNING: Air dry."]
