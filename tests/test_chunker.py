import hashlib

from backend.app.knowledge.chunker import (
    FALLBACK_OVERLAP_TOKENS,
    MAX_CHUNK_TOKENS,
    chunk_document,
)
from backend.app.knowledge.models import CleanDocument
from backend.app.knowledge.metadata import enrich_chunk
from backend.app.knowledge.indexer import build_mapping


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return text.split()

    def decode(self, tokens, skip_special_tokens=True):
        return " ".join(tokens)


def document(text):
    return CleanDocument(
        document_id="doc-1", source_id="src-1", source_title="Care", source_url="https://example.test/care",
        brand="Brand", language="en", sections=[], clean_content=text, content_hash="raw-hash",
    )


def test_heading_paragraph_list_and_metadata():
    chunks = chunk_document(document("# Washing\nWash gently.\n- Close zippers\n- Rinse thoroughly"), FakeTokenizer())
    assert len(chunks) == 1
    assert chunks[0].content.startswith("# Washing")
    assert "- Close zippers" in chunks[0].content
    assert chunks[0].section_title == "Washing"
    assert chunks[0].chunk_id == "doc-1/washing/000"
    assert chunks[0].content_hash == hashlib.sha256(chunks[0].content.encode()).hexdigest()


def test_faq_warning_and_steps_stay_together_when_short():
    text = "## Washing\nQuestion: Can I machine wash?\nAnswer: Yes, use a gentle cycle.\nWARNING: Do not use bleach.\nStep 1: Close zippers.\nStep 2: Wash gently."
    chunks = chunk_document(document(text), FakeTokenizer())
    assert len(chunks) == 1
    assert "Question:" in chunks[0].content and "Answer:" in chunks[0].content
    assert "WARNING:" in chunks[0].content and "Step 2" in chunks[0].content


def test_long_structure_uses_bounded_fallback_and_overlap():
    text = "## Long\n" + " ".join(f"word{i}" for i in range(MAX_CHUNK_TOKENS + 100))
    chunks = chunk_document(document(text), FakeTokenizer())
    assert len(chunks) > 1
    assert all(0 < len(FakeTokenizer().encode(c.content)) <= MAX_CHUNK_TOKENS for c in chunks)
    first = FakeTokenizer().encode(chunks[0].content)
    second = FakeTokenizer().encode(chunks[1].content)
    assert len(set(first[-FALLBACK_OVERLAP_TOKENS:]) & set(second[:FALLBACK_OVERLAP_TOKENS])) > 0


def test_empty_content_produces_no_empty_chunks():
    assert chunk_document(document(""), FakeTokenizer()) == []


def test_same_source_exact_duplicate_is_removed_and_metadata_is_deterministic():
    chunks = chunk_document(document("## Washing\nWash gently.\n## Washing\nWash gently."), FakeTokenizer())
    assert len(chunks) == 1
    data = enrich_chunk(chunks[0])
    assert data["care_stage"] == ["washing"]
    assert data["embedding_text"].startswith("passage: Care")


def test_mapping_has_dense_vector_and_source_fields():
    mapping = build_mapping()["mappings"]["properties"]
    assert mapping["embedding"] == {"type": "dense_vector", "dims": 384, "index": True, "similarity": "cosine"}
    assert mapping["source_id"]["type"] == "keyword"


def test_heading_only_duplicate_is_not_emitted():
    chunks = chunk_document(document("## FAQ\n## FAQ\nAnswer: use a gentle cycle."), FakeTokenizer())
    assert all(len(c.content.splitlines()) > 1 for c in chunks)
