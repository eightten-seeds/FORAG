"""Validate Candidate Golden Dataset records against frozen chunks."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data/evaluation/golden_dataset.jsonl"
DEFAULT_CHUNKS = ROOT / "data/processed/chunks.jsonl"
REQUIRED_FIELDS = {"question", "gt_answer", "gold_chunk_ids", "category", "kb_version", "split"}
NON_RETRIEVAL_CATEGORIES = {"insufficient_evidence", "missing_information"}


def _read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"Record at line {line_number} is not an object")
        records.append(value)
    return records


def normalize_question(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value.casefold())


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", value.casefold()))


def _near_duplicate_warnings(records: list[dict]) -> list[dict]:
    warnings: list[dict] = []
    for left, record in enumerate(records):
        left_tokens = _tokens(record["question"])
        for right in range(left + 1, len(records)):
            other = records[right]
            if record["split"] == other["split"]:
                continue
            right_tokens = _tokens(other["question"])
            union = left_tokens | right_tokens
            score = len(left_tokens & right_tokens) / len(union) if union else 0.0
            if score >= 0.72:
                warnings.append({"left_line": left + 1, "right_line": right + 1, "jaccard": round(score, 3)})
    return warnings


def _intent_markers(question: str) -> set[str]:
    text = question.casefold()
    markers: set[str] = set()
    if re.search(r"wets?\s*out", text): markers.add("wetting_out")
    if re.search(r"wet\s*out|wetting\s*out|wetting[- ]out|湿透|不挂水珠", text): markers.add("wetting_out")
    if re.search(r"leak|漏水|waterproof membrane", text): markers.add("leakage")
    if re.search(r"dryer balls?|tennis balls?|redistribute|clump|loft|蓬松|结团|烘干时.*拍", text): markers.add("down_loft")
    return markers


def _semantic_leakage(records: list[dict]) -> list[dict]:
    pairs: list[dict] = []
    for left, record in enumerate(records):
        if not record.get("gold_chunk_ids"):
            continue
        for right in range(left + 1, len(records)):
            other = records[right]
            if record.get("split") == other.get("split") or not other.get("gold_chunk_ids"):
                continue
            shared_intent = _intent_markers(record["question"]) & _intent_markers(other["question"])
            if {"wetting_out", "leakage"}.issubset(shared_intent) or "down_loft" in shared_intent:
                pairs.append({"left_line": left + 1, "right_line": right + 1, "intent": sorted(shared_intent)})
    return pairs


def _cross_split_shared_gold(records: list[dict]) -> list[dict]:
    by_chunk: dict[str, list[tuple[int, str]]] = {}
    for line_number, record in enumerate(records, 1):
        for chunk_id in record.get("gold_chunk_ids", []):
            by_chunk.setdefault(chunk_id, []).append((line_number, record["split"]))
    return [{"gold_chunk_id": chunk_id, "records": [{"line": line, "split": split} for line, split in values]}
            for chunk_id, values in sorted(by_chunk.items()) if {split for _, split in values} == {"dev", "test"}]


def validate_records(records: list[dict], chunks: dict[str, dict]) -> dict:
    errors: list[str] = []
    versions = {chunk["kb_version"] for chunk in chunks.values()}
    if len(versions) != 1:
        errors.append("Frozen chunks must contain exactly one kb_version")
    expected_version = next(iter(versions), None)
    normalized: dict[str, list[tuple[int, str]]] = {}
    retrieval_evaluable = 0
    non_retrieval_evaluable = 0
    invalid_gold = 0

    for line_number, record in enumerate(records, 1):
        if set(record) != REQUIRED_FIELDS:
            errors.append(f"line {line_number}: schema fields must exactly match the formal schema")
            continue
        for field in ("question", "gt_answer", "category", "kb_version", "split"):
            if not isinstance(record[field], str) or not record[field].strip():
                errors.append(f"line {line_number}: {field} must be a non-empty string")
        if record["split"] not in {"dev", "test"}:
            errors.append(f"line {line_number}: split must be dev or test")
        if record["kb_version"] != expected_version:
            errors.append(f"line {line_number}: kb_version does not match frozen chunks")
        if not isinstance(record["gold_chunk_ids"], list) or not all(isinstance(value, str) for value in record["gold_chunk_ids"]):
            errors.append(f"line {line_number}: gold_chunk_ids must be a list of strings")
            continue
        missing = [value for value in record["gold_chunk_ids"] if value not in chunks]
        invalid_gold += len(missing)
        if missing:
            errors.append(f"line {line_number}: nonexistent gold chunk ids: {missing}")
        if record["category"] in NON_RETRIEVAL_CATEGORIES:
            non_retrieval_evaluable += 1
            if record["gold_chunk_ids"]:
                errors.append(f"line {line_number}: non-retrieval sample must have empty gold_chunk_ids")
        else:
            retrieval_evaluable += 1
            if not record["gold_chunk_ids"]:
                errors.append(f"line {line_number}: answerable sample must have gold_chunk_ids")
        normalized.setdefault(normalize_question(record["question"]), []).append((line_number, record["split"]))

    duplicate_questions = sum(len(items) - 1 for items in normalized.values() if len(items) > 1)
    leakage = sum(1 for items in normalized.values() if {split for _, split in items} == {"dev", "test"})
    if duplicate_questions:
        errors.append(f"exact duplicate question count: {duplicate_questions}")
    if leakage:
        errors.append(f"exact dev/test leakage count: {leakage}")

    semantic_leakage = _semantic_leakage(records)
    shared_gold = _cross_split_shared_gold(records)
    if semantic_leakage:
        errors.append(f"semantic leakage count: {len(semantic_leakage)}")
    answerable = [record for record in records if record.get("category") not in NON_RETRIEVAL_CATEGORIES]
    evidence = [chunks[chunk_id] for record in answerable for chunk_id in record.get("gold_chunk_ids", []) if chunk_id in chunks]
    chinese = sum(bool(re.search(r"[\u4e00-\u9fff]", record.get("question", ""))) for record in records)
    statistics = {
        "total": len(records), "dev": sum(record.get("split") == "dev" for record in records), "test": sum(record.get("split") == "test" for record in records),
        "retrieval_evaluable_count": retrieval_evaluable, "non_retrieval_evaluable_count": non_retrieval_evaluable,
        "chinese": chinese, "english": len(records) - chinese,
        "average_gold_chunks_per_answerable": round(sum(len(record.get("gold_chunk_ids", [])) for record in answerable) / len(answerable), 3) if answerable else 0,
        "category_distribution": dict(sorted(Counter(record.get("category") for record in records).items())),
        "brand_distribution": dict(sorted(Counter(chunk["brand"] for chunk in evidence).items())),
        "source_distribution": dict(sorted(Counter(chunk["source_id"] for chunk in evidence).items())),
        "invalid_gold_chunk_count": invalid_gold,
        "exact_duplicate_count": duplicate_questions, "dev_test_exact_leakage_count": leakage,
        "near_duplicate_warnings": _near_duplicate_warnings(records),
        "semantic_leakage": semantic_leakage,
        "semantic_leakage_count": len(semantic_leakage),
        "cross_split_shared_gold_chunk_ids": shared_gold,
        "cross_split_shared_gold_count": len(shared_gold),
    }
    return {"valid": not errors, "errors": errors, "statistics": statistics, "kb_version": expected_version}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    args = parser.parse_args()
    chunks = {record["chunk_id"]: record for record in _read_jsonl(args.chunks)}
    result = validate_records(_read_jsonl(args.dataset), chunks)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
