# Fashion Care RAG

户外功能服装智能养护 RAG 问答系统。

已完成：Engineering Skeleton、Elasticsearch、Controlled Official Source Collection、Loader / Cleaner、Structure-aware Chunking、Metadata / Terminology、multilingual E5 Embedding、Elasticsearch Knowledge Base、KB Final Hardening、Golden Dataset v1。

Golden Dataset v1：42 samples，dev/test = 26/16，Human Review complete，已冻结并绑定 `kb_v1`。

已实现：BM25、Dense → RRF → Cross-Encoder → Top5 的 Hybrid Retriever；Stage 5C 已 DONE / PASS。
Hybrid Retriever：IMPLEMENTED / VERIFIED / FROZEN。
Stage 5C standalone Retriever formal TEST：12/16 = 75.0%。
Query Analysis/Qwen：IMPLEMENTED / REAL API VERIFIED；Stage 8A = DONE。
Stage 8B DEV integration：VERIFIED；standalone Success@5 50.0%，integrated Success@5 62.5%，提升 +3 hits / +12.5 pp。
Stage 8B integrated TEST NOT RUN。Stage 9A：Shared LLM Foundation + Agent Contract Freeze = DONE / PASS。Stage 9B：Evidence Judge + Query Rewrite + LangGraph routing = DONE / PASS。Stage 10：Answer Generation + Citation Generation = DONE / PASS。Stage 11A：Backend FastAPI integration = IMPLEMENTED / PASS。Real Backend HTTP E2E = PASS。Stage 11 overall = IN PROGRESS。Next Gate：Stage 11B — Vue + Browser End-to-End。
Answer Generation、Citation Generation、Citation Validation、FastAPI backend integration：IMPLEMENTED；Real Backend HTTP E2E：PASS；Vue QA：NOT IMPLEMENTED。

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
Terminology, multilingual E5 embeddings, the Elasticsearch knowledge base,
and the frozen Stage 5A/5B retrieval pipeline. Stage 5C formal standalone
TEST is 12/16 = 75.0%; Stage 8A Query Analysis/Qwen and Stage 8B DEV
integration are complete, while the integrated TEST was not run. Stage 9A
shared LLM transport and Agent contract freeze are DONE / PASS; Stage 9B
LangGraph execution, Evidence Judge, and Query Rewrite are DONE / PASS.
Stage 10 Answer Generation and Citation Validation are DONE / PASS;
Stage 11A Backend FastAPI integration is IMPLEMENTED / PASS; Real Backend
HTTP E2E is PASS; Stage 11 overall is IN PROGRESS; the next gate is Stage
11B Vue + Browser End-to-End. Vue QA is NOT IMPLEMENTED.
