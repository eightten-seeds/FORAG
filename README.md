# Fashion Care RAG

户外功能服装智能养护 RAG 问答系统。

已完成：Engineering Skeleton、Elasticsearch、Controlled Official Source Collection、Loader / Cleaner、Structure-aware Chunking、Metadata / Terminology、multilingual E5 Embedding、Elasticsearch Knowledge Base、KB Final Hardening、Golden Dataset v1。

Golden Dataset v1：42 samples，dev/test = 26/16，Human Review complete，已冻结并绑定 `kb_v1`。

尚未实现：BM25、Dense Retrieval、RRF、Cross-Encoder、Hybrid Retriever、Qwen / LangGraph、Web QA、Final Evaluation。

## 环境要求

- Python 3.12
- uv
- Node.js 24 LTS
- npm

## 后端

```powershell
Copy-Item .env.example .env
uv sync
uv run uvicorn backend.app.main:app --reload
```

访问：<http://127.0.0.1:8000/docs>

## 前端

```powershell
Set-Location frontend
npm install
npm run dev
```

访问：<http://localhost:5173>

## 测试

```powershell
uv run pytest
```

## Local Elasticsearch on Windows

If Elasticsearch fails during startup because automatic heap sizing exceeds
available memory, start the existing installation with a process-local heap
setting such as `ES_JAVA_OPTS=-Xms1g -Xmx1g`. Keep the existing security,
certificate, and password configuration unchanged.

Implemented pipeline stages include controlled official-source collection,
Loader/Cleaner, structure-aware Chunking, deterministic Metadata and
Terminology, multilingual E5 embeddings, and the Elasticsearch knowledge
base. Golden Dataset, retrieval, reranking, Qwen/LangGraph, and Web QA remain
out of scope.
