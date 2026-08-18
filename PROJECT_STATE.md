# FORAG Project State

## Project

FORAG 是一个基于品牌官方护理资料、面向户外功能服装的可追溯 RAG 问答系统。

## Source of Truth

事实优先级：

1. 当前 Git repository code
2. `PROJECT_STATE.md`
3. `docs/IMPLEMENTATION_PLAN.md`、`docs/DATA_DESIGN.md`、`docs/TECHNICAL_BASELINE.md`
4. 当前 Stage 执行结果
5. Chat history

旧对话不得覆盖当前仓库事实。

## Current Stage

Stage 13 — Integrated DEV Evaluation = DONE / PASS.

Stage 11A — Backend Runtime + RAGService + FastAPI = DONE / PASS.

- Lifespan runtime, RAGService, typed chat API, evidence/trace projection, CORS, health, and metrics: IMPLEMENTED / PASS
- Real Backend HTTP E2E: PASS; representative smoke latency approximately 13s
- The previous 180s executor termination was not reproduced during diagnosis
- No current Stage 11A blocker
- Stage 11B — Vue + Browser End-to-End: DONE / PASS
- Real Browser E2E: PASS; synthetic answered flow rendered answer, sources, evidence, trace, and browser request timing

Stage 13 — Integrated DEV Evaluation = DONE / PASS.

- Stage 11 overall remains DONE / PASS
- DEV records: 26 total; 24 retrieval-evaluable; 2 non-retrieval exclusions
- Success@5: 15/24 = 62.5%; Recall@5: 62.5%
- Category Recall@5: down_drying 80.0%, down_washing 0.0%, dwr 83.3%, fleece 100.0%, hardshell_drying 100.0%, hardshell_washing 50.0%, softshell 100.0%, stain_removal 100.0%, washing 0.0%
- Stage 8B integrated DEV baseline reproduced; Final TEST and RAGChecker NOT RUN

- Shared LLM transport: IMPLEMENTED / VERIFIED
- QueryAnalyzer shared transport migration: VERIFIED
- Real API regression smoke: 1 synthetic query PASS; not a Golden Dataset evaluation
- Frozen Retriever: UNCHANGED / FROZEN
- Golden Dataset / KB: UNCHANGED / FROZEN

Stage 5C standalone Frozen Hybrid Retriever formal TEST: 12/16, Success@5 75.0%, Recall@5 75.0%.

Stage 8A — Query Analysis Foundation = DONE / PASS.

- Provider: Qwen / 百炼
- Model: `qwen3.7-plus`
- Protocol: OpenAI-compatible Chat Completions
- Structured output: strict JSON Schema
- Local validation: Pydantic
- `enable_thinking=False`
- Deterministic Query Analysis → Frozen Retriever adapter verified
- Real Qwen API smoke: 3/3 PASS
- Frozen Hybrid Retriever unchanged

Stage 8B — Query Analysis → Frozen Hybrid Retriever = DONE / PASS.

- Standalone DEV: 12/24, Success@5 50.0%, Recall@5 50.0%
- Integrated DEV: 15/24, Success@5 62.5%, Recall@5 62.5%
- Delta: +3 hits, +12.5 percentage points
- Transitions: GAINED 3, LOST 0, UNCHANGED_HIT 12, UNCHANGED_MISS 9
- DEV only; TEST NOT RUN; no test-driven tuning; no prompt tuning after baseline
- Frozen Retriever unchanged; Golden Dataset / KB unchanged

Stage 9B — Evidence Judge + Query Rewrite + LangGraph Routing = DONE / PASS.

- Query Analysis, Frozen Hybrid Retriever, shared LLM transport, Agent State contract, Evidence Judge, Query Rewrite, and LangGraph routing: IMPLEMENTED / VERIFIED
- Max-one-rewrite retrieval loop: IMPLEMENTED / VERIFIED
- Answer Generation, Citation Generation, and deterministic source mapping: IMPLEMENTED / VERIFIED; FastAPI QA integration: IMPLEMENTED / VERIFIED; Vue QA integration: IMPLEMENTED / VERIFIED; final full-system evaluation: NOT IMPLEMENTED

## Stage Status

| Stage | Status |
|---|---|
| Stage 1 Engineering Skeleton | DONE |
| Stage 2 Elasticsearch | DONE |
| Stage 3 Knowledge Base | DONE |
| Stage 3 Final Hardening | DONE |
| Stage 4 Golden Dataset | DONE / FROZEN |
| Stage 5A Retrieval Foundation | DONE / PASS |
| Stage 5B Hybrid Retrieval | DONE / PASS |
| Stage 5C Retriever Evaluation & Freeze | DONE / PASS |
| Stage 6 Dense Retrieval | INCLUDED IN STAGE 5A / PASS |
| Stage 7 RRF + Cross-Encoder | INCLUDED IN STAGE 5B / PASS |
| Stage 8A Query Analysis Foundation | DONE / PASS |
| Stage 8B Integrated DEV Retrieval | DONE / PASS |
| Stage 9A Shared LLM Foundation + Agent Contract Freeze | DONE / PASS |
| Stage 9B Evidence Judge + Query Rewrite + LangGraph Routing | DONE / PASS |
| Stage 10 Answer Generation + Citation Generation | DONE / PASS |
| Stage 11 End-to-End Integration | DONE / PASS |
| Stage 11A Backend Runtime + RAGService + FastAPI | DONE / PASS |
| Stage 11B Vue + Browser End-to-End | DONE / PASS |
| Stage 13 Integrated DEV Evaluation | DONE / PASS |

## Frozen Components

KB v1 已冻结。未经确定性测试失败、确认的数据错误、正式评估错误分析或可复现性失败证据，不得主动修改：

- approved source set、Collector、Loader、Cleaner、Chunker
- Metadata、Terminology、E5 Embedding
- Elasticsearch mapping、Indexer 及 KB build semantics
- KB v1 的 source、chunk、embedding、索引数据与 chunk ID

## Knowledge Base v1

- Official sources：14
- Chunks：234
- Embeddings：234
- Embedding model：`intfloat/multilingual-e5-small`
- Embedding dimension：384
- Elasticsearch：9.5.1
- Index：`fashion_care_kb_v1`
- ES documents：234
- Source coverage：14/14
- Chunk token limit：320；统计口径为 `add_special_tokens=False`
- 当前质量指标：pure-heading 0、FAQ split error 0、Step split error 0、empty 0、duplicate chunk_id 0、same-source duplicate 0、orphan 0

## Golden Dataset

文件：

- `data/evaluation/golden_dataset.jsonl`
- `data/evaluation/golden_review.csv`

当前真实统计：

- total：42
- dev/test：26/16
- retrieval-evaluable：40
- negative：2
- Chinese/English：33/9
- `kb_version`：`kb_v1`
- Human Review：42 / 42 approved
- Golden Dataset v1：FROZEN against `kb_v1`
- invalid gold：0
- semantic leakage：0

## Current Task

Stage 13 — Integrated DEV Evaluation = DONE / PASS. The frozen system reproduced the Stage 8B integrated DEV baseline: 26 DEV records, 24 retrieval-evaluable, 2 exclusions, Success@5 15/24 = 62.5%, and Recall@5 62.5%. Stage 5C standalone formal TEST remains 12/16 = 75.0%; Stage 8B integrated DEV remains 15/24 = 62.5%; integrated TEST NOT RUN. Stage 13 Final TEST and RAGChecker remain NOT RUN.

## Current Blockers

None.

## Next Gate

Stage 14 — Final TEST + RAGChecker.

## Next Stage

Stage 14 — Final TEST + RAGChecker.

## Retrieval / Agent Status

Query Analysis/Qwen: IMPLEMENTED / REAL API VERIFIED (3/3 smoke); deterministic adapter verified; Frozen Hybrid Retriever unchanged.

BM25：IMPLEMENTED / REAL INTEGRATION VERIFIED。
Dense Retrieval：IMPLEMENTED / REAL INTEGRATION VERIFIED。
Python RRF：IMPLEMENTED。Cross-Encoder：IMPLEMENTED。Unified Hybrid Retriever：IMPLEMENTED / REAL E2E VERIFIED / FROZEN。Retriever architecture / parameters：FROZEN。
LangGraph、Evidence Judge、Query Rewrite、Answer Generation、Citation Generation、FastAPI backend integration、Vue QA integration：IMPLEMENTED / VERIFIED；final full-system evaluation 尚未实现。

Stage 9A shared transport and Agent contracts are DONE / PASS. Stage 9B routing, Stage 10 final-response generation, Stage 11A/11B end-to-end web integration, and Stage 13 integrated DEV evaluation are IMPLEMENTED / VERIFIED. Final TEST and RAGChecker remain unimplemented.

## Git Checkpoints

- `e25f6ea feat: complete vue browser integration` (Stage 11B Vue + Browser End-to-End)
- `227e543 feat: integrate rag backend api`（Stage 11A Backend Runtime + RAGService + FastAPI）
- `584a7d7 feat: implement grounded answer and citation generation`（Stage 10 Answer Generation + Citation Generation）
- `5855999 feat: implement evidence rewrite agent routing`（Stage 9B Evidence Judge + Query Rewrite + LangGraph Routing）
- `ca9382d refactor: establish shared llm and agent contracts`（Stage 9A Shared LLM Foundation + Agent Contract Freeze）
- `cf33d5f feat: evaluate query analysis integrated retrieval`（Stage 8B Integrated DEV Retrieval）
- `ad88cfa feat: implement qwen query analysis foundation`（Stage 8A Query Analysis Foundation）
- `a091688 feat(retrieval): complete Stage 5C evaluation and freeze hybrid retriever`（Retriever Evaluation & Freeze）
- `7f712c5 feat: complete hybrid retrieval`（Hybrid Retrieval）
- `b1bc052 feat: complete retrieval foundation`（Retrieval Foundation）
- `41efd9f feat: finalize golden dataset evaluation set`（Golden Dataset）
- `b3e73ca fix: harden knowledge base build pipeline`（KB Final Hardening）
- `0bfa53e feat: build outdoor care knowledge base pipeline`

当前 HEAD 必须以 `git log --oneline` 为准。

## Repository Hygiene

本地运行环境、`.env`、raw/processed 生成数据、模型缓存、浏览器运行时、Elasticsearch 运行数据及用户私人 DOCX/PDF 不应作为项目源代码修改对象。不要修改 `.gitignore`。

## New Conversation Handoff

这是 FORAG 的当前阶段状态。请先读取 `PROJECT_STATE.md`、`docs/IMPLEMENTATION_PLAN.md` 及当前 Stage 相关代码，以仓库事实确认 Current Stage、Current Task、Frozen Components 和 Next Gate；不要依赖旧聊天推测 Retriever 是否已实现。
