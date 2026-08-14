from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Fashion Care RAG"
    app_env: str = "development"
    log_level: str = "INFO"

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    rag_trace_enabled: bool = True

    es_url: str = "https://localhost:9200"
    es_username: str = "elastic"
    es_password: str = ""
    es_ca_cert: str = ""
    es_index_name: str = "fashion_care_kb_v1"
    es_number_of_shards: int = 1
    es_number_of_replicas: int = 0

    max_chunk_tokens: int = 320
    min_chunk_tokens: int = 60
    fallback_overlap_tokens: int = 40

    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    embedding_device: str = "cpu"
    embedding_batch_size: int = 16

    bm25_top_k: int = 20
    dense_top_k: int = 20
    dense_num_candidates: int = 100
    rrf_k: int = 60
    rrf_top_n: int = 30
    bm25_rrf_weight: float = 1.0
    dense_rrf_weight: float = 1.0

    reranker_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
    reranker_device: str = "cpu"
    reranker_batch_size: int = 8
    rerank_top_k: int = 5

    max_rewrite_count: int = 1

    llm_provider: str = "qwen"
    dashscope_api_key: str = ""
    qwen_base_url: str = ""
    qwen_dev_model: str = "qwen3.7-plus"
    qwen_eval_model: str = "qwen3.7-plus-2026-05-26"
    llm_enable_thinking: bool = False
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 2

    ragchecker_extractor_model: str = "qwen3.7-plus-2026-05-26"
    ragchecker_checker_model: str = "qwen3.7-plus-2026-05-26"


@lru_cache
def get_settings() -> Settings:
    return Settings()
