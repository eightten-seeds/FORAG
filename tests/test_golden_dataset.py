from scripts.validate_golden_dataset import validate_records


CHUNKS = {
    "chunk-1": {"chunk_id": "chunk-1", "kb_version": "kb_v1", "brand": "Brand", "source_id": "source-1"},
    "chunk-2": {"chunk_id": "chunk-2", "kb_version": "kb_v1", "brand": "Brand", "source_id": "source-2"},
}


def record(**changes):
    value = {
        "question": "How should I wash it?", "gt_answer": "Use a gentle cycle.",
        "gold_chunk_ids": ["chunk-1"], "category": "washing", "kb_version": "kb_v1", "split": "dev",
    }
    value.update(changes)
    return value


def test_valid_record_and_deterministic_statistics_pass():
    first = validate_records([record()], CHUNKS)
    second = validate_records([record()], CHUNKS)
    assert first["valid"] and first["statistics"] == second["statistics"]


def test_invalid_split_and_kb_version_fail():
    result = validate_records([record(split="train", kb_version="kb_v2")], CHUNKS)
    assert not result["valid"]
    assert any("split" in error for error in result["errors"])
    assert any("kb_version" in error for error in result["errors"])


def test_missing_or_nonexistent_gold_fails_for_answerable_sample():
    empty = validate_records([record(gold_chunk_ids=[])], CHUNKS)
    missing = validate_records([record(gold_chunk_ids=["missing"])], CHUNKS)
    assert not empty["valid"] and not missing["valid"]


def test_insufficient_evidence_allows_empty_gold():
    result = validate_records([record(category="insufficient_evidence", gold_chunk_ids=[])], CHUNKS)
    assert result["valid"]
    assert result["statistics"]["non_retrieval_evaluable_count"] == 1


def test_duplicate_and_cross_split_exact_leakage_fail():
    result = validate_records([record(), record(split="test")], CHUNKS)
    assert not result["valid"]
    assert result["statistics"]["exact_duplicate_count"] == 1
    assert result["statistics"]["dev_test_exact_leakage_count"] == 1


def test_shared_gold_is_reported_and_intent_leakage_is_separate():
    shared = [record(question="General stain care?"), record(question="Sticky sap stain care?", split="test")]
    shared_result = validate_records(shared, CHUNKS)
    assert shared_result["valid"]
    assert shared_result["statistics"]["cross_split_shared_gold_count"] == 1
    assert shared_result["statistics"]["semantic_leakage_count"] == 0

    leakage = [
        record(question="Does wetting out mean leaking?"),
        record(question="My jacket wets out; is the membrane leaking?", split="test", gold_chunk_ids=["chunk-2"]),
    ]
    leakage_result = validate_records(leakage, CHUNKS)
    assert not leakage_result["valid"]
    assert leakage_result["statistics"]["semantic_leakage_count"] == 1
