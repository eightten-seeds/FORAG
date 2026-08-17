# Fashion Care RAG

户外功能服装智能养护 RAG 问答系统。

当前仅完成 `IMPLEMENTATION_PLAN.md` 的阶段 1：工程初始化。Elasticsearch、知识库、Retriever、Qwen、LangGraph、问答 API 与评测均尚未实现。

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
