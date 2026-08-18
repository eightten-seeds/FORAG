"""Application-lifespan composition of heavy Stage 11A runtime resources."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from elasticsearch import Elasticsearch

from backend.app.config import Settings
from backend.app.services.rag_service import RAGService


logger = logging.getLogger(__name__)


@dataclass
class AppRuntime:
    """Resources built once at startup and safely reused across requests."""

    es_client: Elasticsearch
    hybrid_retriever: Any
    llm_transport: Any
    query_analyzer: Any
    evidence_judge: Any
    query_rewriter: Any
    answer_generator: Any
    agent_graph: Any
    rag_service: RAGService

    def close(self) -> None:
        close_transport = getattr(self.llm_transport, "close", None)
        if not callable(close_transport):
            close_transport = getattr(getattr(self.llm_transport, "client", None), "close", None)
        if callable(close_transport):
            close_transport()
        self.es_client.close()

    def check_elasticsearch(self) -> dict[str, str]:
        info = self.es_client.info()
        return {
            "status": "ok",
            "cluster_name": str(info.get("cluster_name", "")),
            "version": str(info.get("version", {}).get("number", "")),
        }


def create_elasticsearch_client(settings: Settings) -> Elasticsearch:
    client_options: dict[str, object] = {
        "hosts": [settings.es_url],
        "basic_auth": (settings.es_username, settings.es_password),
        "request_timeout": 10,
    }
    if settings.es_ca_cert:
        client_options["ca_certs"] = settings.es_ca_cert
    return Elasticsearch(**client_options)


def create_runtime(settings: Settings) -> AppRuntime:
    """Compose the frozen retrieval stack and Agent consumers exactly once."""

    started_at = perf_counter()
    startup_timings: list[dict[str, int | str]] = []

    def build_stage(name: str, factory: Any) -> Any:
        stage_started_at = perf_counter()
        value = factory()
        startup_timings.append(
            {
                "stage": name,
                "duration_ms": round((perf_counter() - stage_started_at) * 1000),
            }
        )
        return value

    def load_runtime_dependencies() -> tuple[Any, ...]:
        from backend.app.agent.answer_generator import AnswerGenerator
        from backend.app.agent.evidence_judge import EvidenceJudge
        from backend.app.agent.graph import build_agent_graph
        from backend.app.agent.query_rewriter import QueryRewriter
        from backend.app.knowledge.embedding import E5Embedder
        from backend.app.llm.client import QwenOpenAICompatibleClient
        from backend.app.query_analysis.analyzer import QueryAnalyzer
        from backend.app.retrieval.bm25 import BM25Retriever
        from backend.app.retrieval.dense import DenseRetriever
        from backend.app.retrieval.hybrid import HybridRetriever
        from backend.app.retrieval.reranker import CrossEncoderReranker

        return (
            AnswerGenerator,
            EvidenceJudge,
            build_agent_graph,
            QueryRewriter,
            E5Embedder,
            QwenOpenAICompatibleClient,
            QueryAnalyzer,
            BM25Retriever,
            DenseRetriever,
            HybridRetriever,
            CrossEncoderReranker,
        )

    (
        AnswerGenerator,
        EvidenceJudge,
        build_agent_graph,
        QueryRewriter,
        E5Embedder,
        QwenOpenAICompatibleClient,
        QueryAnalyzer,
        BM25Retriever,
        DenseRetriever,
        HybridRetriever,
        CrossEncoderReranker,
    ) = build_stage("runtime_dependency_imports", load_runtime_dependencies)
    es_client = build_stage("elasticsearch_client", lambda: create_elasticsearch_client(settings))
    try:
        embedder = build_stage(
            "e5_embedder",
            lambda: E5Embedder(settings.embedding_model, device=settings.embedding_device),
        )
        bm25_retriever, dense_retriever = build_stage(
            "retriever_adapters",
            lambda: (
                BM25Retriever(es_client, settings.es_index_name, top_k=settings.bm25_top_k),
                DenseRetriever(
                    es_client,
                    embedder,
                    settings.es_index_name,
                    top_k=settings.dense_top_k,
                    num_candidates=settings.dense_num_candidates,
                    embedding_dim=settings.embedding_dim,
                ),
            ),
        )
        reranker = build_stage(
            "cross_encoder",
            lambda: CrossEncoderReranker.load(
                settings.reranker_model,
                device=settings.reranker_device,
                batch_size=settings.reranker_batch_size,
                top_k=settings.rerank_top_k,
            ),
        )
        hybrid_retriever = build_stage(
            "hybrid_retriever",
            lambda: HybridRetriever(
                bm25_retriever,
                dense_retriever,
                reranker,
                rrf_k=settings.rrf_k,
                rrf_top_n=settings.rrf_top_n,
                bm25_weight=settings.bm25_rrf_weight,
                dense_weight=settings.dense_rrf_weight,
            ),
        )
        llm_transport, query_analyzer, evidence_judge, query_rewriter, answer_generator = build_stage(
            "llm_and_agent_components",
            lambda: (
                (transport := QwenOpenAICompatibleClient.from_settings(settings)),
                QueryAnalyzer(
                    transport,
                    model=settings.qwen_dev_model,
                    enable_thinking=settings.llm_enable_thinking,
                ),
                EvidenceJudge(
                    transport,
                    model=settings.qwen_dev_model,
                    enable_thinking=settings.llm_enable_thinking,
                ),
                QueryRewriter(
                    transport,
                    model=settings.qwen_dev_model,
                    enable_thinking=settings.llm_enable_thinking,
                ),
                AnswerGenerator(
                    transport,
                    model=settings.qwen_dev_model,
                    enable_thinking=settings.llm_enable_thinking,
                ),
            ),
        )
        agent_graph = build_stage(
            "compiled_graph",
            lambda: build_agent_graph(
                analyzer=query_analyzer,
                retriever=hybrid_retriever,
                evidence_judge=evidence_judge,
                query_rewriter=query_rewriter,
                answer_generator=answer_generator,
            ),
        )
        rag_service = build_stage("rag_service", lambda: RAGService(agent_graph))
        logger.info(
            "Runtime startup timing: %s",
            {
                "total_ms": round((perf_counter() - started_at) * 1000),
                "stages": startup_timings,
            },
        )
        return AppRuntime(
            es_client=es_client,
            hybrid_retriever=hybrid_retriever,
            llm_transport=llm_transport,
            query_analyzer=query_analyzer,
            evidence_judge=evidence_judge,
            query_rewriter=query_rewriter,
            answer_generator=answer_generator,
            agent_graph=agent_graph,
            rag_service=rag_service,
        )
    except Exception:
        es_client.close()
        raise
