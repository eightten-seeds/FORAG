import json
import hashlib
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
        "content_hash": hashlib.sha256(b"# Washing\nWash gently.\n").hexdigest(),
        "enabled": True,
    }


def _write_manifest(tmp_path: Path, record: dict[str, object]) -> Path:
    manifest = tmp_path / "sources.jsonl"
    manifest.write_text(json.dumps(record) + "\n", encoding="utf-8")
    return manifest


def test_manifest_load_and_local_file(tmp_path: Path) -> None:
    source = tmp_path / "raw.txt"
    source.write_text("# Washing\nWash gently.\n", encoding="utf-8")
    record = _record("raw.txt")
    record["content_hash"] = hashlib.sha256(source.read_bytes()).hexdigest()
    docs = load_sources(_write_manifest(tmp_path, record), repository_root=tmp_path)
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


def test_html_cleaner_removes_page_noise_and_preserves_structure() -> None:
    raw = RawDocument(
        document_id="src_html",
        source_id="src_html",
        brand="Test Brand",
        source_type="product_care",
        source_title="Care",
        source_url="https://brand.example/care",
        language="en",
        accessed_at="2026-08-14",
        raw_content="""<html><head><style>.x{}</style><script>track()</script></head>
        <body><header>Menu Search</header><nav>Home Products</nav>
        <main><h1>Care Guide</h1><p>Wash gently.</p><h2>Steps</h2>
        <ol><li>Step 1: Wash.</li><li>Step 2: Dry.</li></ol>
        <div class='warning'>WARNING: Do not bleach.</div>
        <div class='faq'><h2>Can I tumble dry?</h2><div aria-hidden='true'>Yes, use low heat.</div></div>
        </main><footer>Privacy Cookie</footer></body></html>""",
        content_hash="fixture-hash",
    )
    clean = clean_document(raw)
    assert clean.clean_content.startswith("# Care Guide")
    assert "Menu Search" not in clean.clean_content
    assert "Home Products" not in clean.clean_content
    assert "Privacy Cookie" not in clean.clean_content
    assert "Step 1: Wash." in clean.clean_content and "Step 2: Dry." in clean.clean_content
    assert "WARNING: Do not bleach." in clean.clean_content
    assert "Can I tumble dry?" in clean.clean_content and "Yes, use low heat." in clean.clean_content
    assert "track()" not in clean.clean_content and ".x{}" not in clean.clean_content
    assert clean.clean_content
