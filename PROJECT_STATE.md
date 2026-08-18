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

## Historical Pre-Stage 8A State

Stage 5C — Retriever Evaluation & Freeze：DONE / PASS。

当前任务：Standalone Hybrid Retriever 已完成 Frozen Golden Dataset dev/test evaluation，架构与参数均已冻结；下一 Gate 为 Query Analysis 正式设计。

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
| Stage 8 Qwen Query Analysis | DONE / PASS |
| Stage 9 LangGraph | NOT STARTED |
| Stage 10+ | NOT STARTED |

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

Stage 5A Retrieval Foundation 与 Stage 5B Hybrid Retrieval 已完成并通过真实本地集成验收。Stage 5C 已使用 Frozen Golden Dataset 完成 standalone Hybrid Retriever dev/test evaluation：Retriever architecture / parameters 已 FROZEN；test 在冻结后首次有效运行，未发生 test-driven tuning。DEV：evaluable 24，Success@5 12/24 = 50.0%，Recall@5 50.0%。TEST：evaluable 16，Success@5 12/16 = 75.0%，Recall@5 75.0%。

## Current Blockers

None。Stage 5A、5B、5C 均已通过本地验收。

## Next Gate

Stage 8B — Query Analysis → Frozen Hybrid Retriever DEV-only integrated retrieval evaluation.

## Historical Next Gate

正式设计 Query Analysis。Frozen standalone Hybrid Retriever 的参数不得因 Stage 5C test misses 重新打开。

## Next Stage

Stage 8B — Query Analysis → Frozen Hybrid Retriever DEV-only integrated retrieval evaluation.

## Historical Next Stage

Stage 8 — Qwen API + Query Analysis 正式设计。当前状态：NOT STARTED。

## Retrieval / Agent Status (through Stage 5C)

Query Analysis/Qwen: IMPLEMENTED / REAL API VERIFIED (3/3 smoke); deterministic adapter verified; Frozen Hybrid Retriever unchanged.

BM25：IMPLEMENTED / REAL INTEGRATION VERIFIED。
Dense Retrieval：IMPLEMENTED / REAL INTEGRATION VERIFIED。
Python RRF：IMPLEMENTED。Cross-Encoder：IMPLEMENTED。Unified Hybrid Retriever：IMPLEMENTED / REAL E2E VERIFIED / FROZEN。Retriever architecture / parameters：FROZEN。
Query Analysis/Qwen、LangGraph、FastAPI 问答和 Vue 问答尚未实现。

## Git Checkpoints

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
