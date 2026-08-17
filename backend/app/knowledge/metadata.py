from __future__ import annotations

import json
import re
from pathlib import Path

from .models import ChunkRecord

CARE_STAGES = ("washing", "drying", "dwr", "stain_removal", "storage", "repair_maintenance")
def _load_terminology() -> dict[str, str]:
    path = Path(__file__).resolve().parents[3] / "data/dictionaries/terminology.json"
    if not path.is_file():
        raise FileNotFoundError(f"Terminology dictionary not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Terminology dictionary must be a JSON object")
    result: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("Terminology dictionary entries must map strings to strings")
        result[key] = value
    return result


def _garment_type(chunk: ChunkRecord) -> list[str]:
    source_map = {
        "goretex-outerwear-001": ["hardshell"],
        "mammut-hardshell-001": ["hardshell"],
        "mammut-down-001": ["down_jacket"],
        "mammut-softshell-001": ["softshell"],
        "mammut-fleece-001": ["fleece"],
        "arcteryx-goretex-dwr-001": ["hardshell"],
        "arcteryx-down-001": ["down_jacket"],
        "arcteryx-synthetic-001": ["synthetic_insulation"],
        "arcteryx-other-001": [],
        "rab-waterproof-001": ["hardshell"],
        "rab-down-001": ["down_jacket"],
    }
    if chunk.source_id in source_map:
        return source_map[chunk.source_id]
    key = f"{chunk.source_id} {chunk.section_title} {chunk.content}".lower()
    for term, value in (("hardshell", "hardshell"), ("waterproof", "hardshell"), ("down", "down_jacket"), ("softshell", "softshell"), ("fleece", "fleece"), ("synthetic", "synthetic_insulation")):
        if term in key:
            return [value]
    return []


def _technology(chunk: ChunkRecord) -> list[str]:
    text = f"{chunk.source_title} {chunk.section_title} {chunk.content}"
    values: list[str] = []
    if re.search(r"GORE[-‑ ]?TEX", text, re.I): values.append("GORE-TEX")
    if re.search(r"\bDWR\b|durable water repellent", text, re.I): values.append("DWR")
    if re.search(r"\bdown\b", text, re.I): values.append("down")
    if re.search(r"synthetic insulation", text, re.I): values.append("synthetic_insulation")
    return list(dict.fromkeys(values))


def _care_stage(chunk: ChunkRecord) -> list[str]:
    text = f"{chunk.section_title} {chunk.content}".lower()
    result = [stage for stage in CARE_STAGES if stage.replace("_", " ") in text or stage in text]
    if "wash" in text or "rinse" in text: result.append("washing")
    if "dry" in text: result.append("drying")
    return list(dict.fromkeys(result))


def normalized_terms(content: str) -> list[str]:
    text = content.lower()
    terms = _load_terminology()
    return [value for key, value in terms.items() if re.search(rf"\b{re.escape(key)}\b", text, re.I)]


def enrich_chunk(chunk: ChunkRecord) -> dict:
    data = chunk.model_dump(mode="json")
    data["garment_type"] = _garment_type(chunk)
    data["technology"] = _technology(chunk)
    data["care_stage"] = _care_stage(chunk)
    data["normalized_terms"] = normalized_terms(chunk.content)
    data["embedding_text"] = f"passage: {chunk.source_title}\n{chunk.section_title}\n{chunk.content}"
    data["embedding"] = []
    return data
