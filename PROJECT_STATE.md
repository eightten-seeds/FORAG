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

Stage 4 — Golden Dataset。

当前任务：完成 Candidate Golden Dataset 的 split leakage audit，并准备 Human Review；Stage 5 Retriever 尚未开始。

## Stage Status

| Stage | Status |
|---|---|
| Stage 1 Engineering Skeleton | DONE |
| Stage 2 Elasticsearch | DONE |
| Stage 3 Knowledge Base | DONE |
| Stage 3 Final Hardening | DONE |
| Stage 4 Golden Dataset | IN PROGRESS |
| Stage 5 BM25 | NOT STARTED |
| Stage 6 Dense Retrieval | NOT STARTED |
| Stage 7 RRF + Cross-Encoder | NOT STARTED |
| Stage 8 Qwen Query Analysis | NOT STARTED |
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
- retrieval-evaluable：38
- negative：4
- Chinese/English：33/9
- `kb_version`：`kb_v1`
- Human Review：42 条均为 `pending`
- Candidate Golden Dataset：尚未冻结
- 当前阶段：split leakage audit + human review

## Current Task

完成 Stage 4：最终 split leakage audit、Human Review、必要修正、validator/test 通过，并冻结 Golden Dataset。

## Current Blockers

None。未完成 Human Review 和 Golden Dataset 冻结不是阻塞项，而是当前任务内容。

## Next Gate

Golden Dataset FROZEN。必须满足：Candidate review complete、required corrections complete、validator pass、tests pass、dev/test leakage accepted、Human Review complete，并建立 Git checkpoint；之后才可进入 Stage 5。

## Next Stage

Stage 5 — Hybrid Retrieval，目标为 BM25 Top20、Dense Top20、Python RRF Top30、Cross-Encoder 后取 Top5。这里只记录目标，不表示相关功能已实现。

## Retrieval / Agent Status

Retriever、BM25、Dense Retrieval、RRF、Cross-Encoder、Qwen、LangGraph、FastAPI 问答和 Vue 问答均未作为本阶段任务实现。

## Git Checkpoints

- `b3e73ca fix: harden knowledge base build pipeline`（KB Final Hardening）
- `0bfa53e feat: build outdoor care knowledge base pipeline`

当前 HEAD 必须以 `git log --oneline` 为准。

## Repository Hygiene

本地运行环境、`.env`、raw/processed 生成数据、模型缓存、浏览器运行时、Elasticsearch 运行数据及用户私人 DOCX/PDF 不应作为项目源代码修改对象。不要修改 `.gitignore`。

## New Conversation Handoff

这是 FORAG 的当前阶段状态。请先读取 `PROJECT_STATE.md`、`docs/IMPLEMENTATION_PLAN.md` 及当前 Stage 相关代码，以仓库事实确认 Current Stage、Current Task、Frozen Components 和 Next Gate；不要依赖旧聊天推测 Retriever 是否已实现。
