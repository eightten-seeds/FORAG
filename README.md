# Fashion Care RAG

户外功能服装智能养护 RAG 问答系统。

已完成：Engineering Skeleton、Elasticsearch、Controlled Official Source Collection、Loader / Cleaner、Structure-aware Chunking、Metadata / Terminology、multilingual E5 Embedding、Elasticsearch Knowledge Base、KB Final Hardening、Golden Dataset v1。

Golden Dataset v1：42 samples，dev/test = 26/16，Human Review complete，已冻结并绑定 `kb_v1`。

已实现：BM25、Dense → RRF → Cross-Encoder → Top5 的 Hybrid Retriever；Stage 5C 已 DONE / PASS。
Hybrid Retriever：IMPLEMENTED / VERIFIED / FROZEN。
Stage 5C standalone Retriever formal TEST：12/16 = 75.0%。
Query Analysis/Qwen：IMPLEMENTED / REAL API VERIFIED；Stage 8A = DONE。
Stage 8B DEV integration：VERIFIED；standalone Success@5 50.0%，integrated Success@5 62.5%，提升 +3 hits / +12.5 pp。
Stage 9A：Shared LLM Foundation + Agent Contract Freeze = DONE / PASS。Stage 9B：Evidence Judge + Query Rewrite + LangGraph routing = DONE / PASS。Stage 10：Answer Generation + Citation Generation = DONE / PASS。Stage 11A：Backend FastAPI integration = IMPLEMENTED / PASS。Stage 11B：Vue + Browser End-to-End = IMPLEMENTED / PASS。Real Backend HTTP E2E 与 Browser E2E 均为 PASS。Stage 11 overall = DONE / PASS。Stage 13 Integrated DEV Evaluation = DONE / PASS：26 DEV records / 24 retrieval-evaluable，Success@5 = 15/24 = 62.5%，Recall@5 = 62.5%。
Stage 14 Final TEST + RAGChecker = DONE / PASS（Official Attempt #2 完整执行）。Next Gate：Stage 15 — Full-chain Final Acceptance。

## 最终系统评测结果 (Stage 14 Official TEST)

- **评测数据集**：Golden TEST（16 samples，16 retrieval-evaluable，0 excluded）
- **评测模型快照**：
  - Generation Pipeline LLM: `qwen3.7-plus-2026-05-26`
  - RAGChecker Extractor: `qwen3.7-plus-2026-05-26`
  - RAGChecker Checker: `qwen3.7-plus-2026-05-26`
  - Embedding: `intfloat/multilingual-e5-small`
  - Reranker: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- **核心质量指标**：
  - **Success@5 / Recall@5**: 14/16 = **87.5%**（14/16 TEST queries 的 Final Top-5 命中 Gold evidence；完整全链路相较 Stage 5C standalone baseline 12/16 = 75.0% 观察到 +12.5 percentage points 系统级差异）
  - **Claim Recall**: **77.9%**（检索上下文覆盖了多数 ground-truth claims，仍存在 claim coverage gap）
  - **Context Precision**: **41.2%**（当前 Top-5 中仍存在较多与目标 claim 无直接关系的上下文，context filtering / ranking precision 是当前系统主要限制之一）
  - **Faithfulness**: **81.4%**（多数生成 claims 能由检索上下文支持，但仍存在一定 unsupported / weakly-supported claims）
- **路由与重写分布**：
  - FinalResponse status: `answered` = 13, `needs_more_information` = 2, `insufficient_evidence` = 1（系统在部分 answerable cases 上仍存在保守的 terminal routing 行为）
  - Rewrite count: 0 rewrite = 14, 1 rewrite = 2；Retrieval passes: 1 pass = 14, 2 passes = 2；Final Top-5 misses = 2

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
