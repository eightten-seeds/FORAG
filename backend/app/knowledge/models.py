from datetime import date

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: HttpUrl
    language: str = Field(min_length=1)
    accessed_at: date
    local_path: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    enabled: bool = True


class RawDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    source_id: str
    brand: str
    source_type: str
    source_title: str
    source_url: HttpUrl
    language: str
    accessed_at: date
    raw_content: str
    content_hash: str


class CleanDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    source_id: str
    source_title: str
    source_url: HttpUrl
    brand: str
    language: str
    sections: list[str]
    clean_content: str
    content_hash: str


class ChunkRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    parent_doc_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    chunk_order: int = Field(ge=0)
    content: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: HttpUrl
    brand: str = Field(min_length=1)
    language: str = Field(min_length=1)
    garment_type: list[str] = Field(default_factory=list)
    technology: list[str] = Field(default_factory=list)
    care_stage: list[str] = Field(default_factory=list)
    section_title: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    kb_version: str = Field(min_length=1)
    normalized_terms: list[str] = Field(default_factory=list)
    embedding_text: str = ""
    embedding: list[float] = Field(default_factory=list)
