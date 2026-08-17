"""Build the deterministic Stage 3B-1 chunks.jsonl artifact."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.knowledge.chunker import chunk_documents, load_tokenizer
from backend.app.knowledge.cleaner import clean_documents
from backend.app.knowledge.loader import load_sources
from backend.app.config import get_settings

OUTPUT = ROOT / "data/processed/chunks.jsonl"


def main() -> None:
    tokenizer = load_tokenizer()
    settings = get_settings()
    chunks = chunk_documents(
        clean_documents(load_sources()), tokenizer,
        max_tokens=settings.max_chunk_tokens,
        overlap_tokens=settings.fallback_overlap_tokens,
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("".join(json.dumps(chunk.model_dump(mode="json"), ensure_ascii=False) + "\n" for chunk in chunks), encoding="utf-8")
    print(json.dumps({"source_count": len({chunk.source_id for chunk in chunks}), "chunk_count": len(chunks), "path": str(OUTPUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
