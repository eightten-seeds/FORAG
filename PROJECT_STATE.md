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

Stage 14 — Final TEST + RAGChecker = DONE / PASS.

- Official Attempt #1: commit `bdc256317f055d9b6385cb3973b3fda54c1ce264`, INTERRUPTED (citation consistency runtime validation exception; quality metrics: NONE)
- Official Attempt #2: commit `52e9a1f676dca923a474124862978eac936d79cf`, run id `stage14_official_attempt2_52e9a1f`, COMPLETE
- TEST samples: 16 total, 16 retrieval-evaluable, 0 excluded
- Final integrated Recall@5: 14/16 = 87.5%, Success@5 = 87.5% (observed system-level comparison to Stage 5C standalone TEST baseline 12/16 = 75.0%: +2 hits, +12.5 percentage points)
- RAGChecker metrics: Claim Recall = 77.9%, Context Precision = 41.2%, Faithfulness = 81.4% (metric unit: percent)
- FinalResponse status distribution: answered = 13, needs_more_information = 2, insufficient_evidence = 1
- Rewrite distribution: 0 rewrites = 14, 1 rewrite = 2. Retrieval passes: 1 pass = 14, 2 passes = 2. Final Top-5 misses = 2
- Model snapshots: Generator `qwen3.7-plus-2026-05-26`, RAGChecker Extractor/Checker `qwen3.7-plus-2026-05-26`, Embedding `intfloat/multilingual-e5-small`, Reranker `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- Historical baselines preserved: Stage 5C standalone formal TEST 12/16 = 75.0%, Stage 8B integrated DEV 15/24 = 62.5%, Stage 13 integrated DEV 15/24 = 62.5%

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
- Stage 8B integrated DEV baseline reproduced; Stage 14 Final TEST + RAGChecker completed on Attempt #2

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
- Answer Generation, Citation Generation, and deterministic source mapping: IMPLEMENTED / VERIFIED; FastAPI QA integration: IMPLEMENTED / VERIFIED; Vue QA integration: IMPLEMENTED / VERIFIED; Stage 14 final evaluation: DONE / PASS.

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
| Stage 14 Final TEST + RAGChecker | DONE / PASS |
| Stage 15 Full-chain Verification | IMPLEMENTATION / EVALUATION PASS (CHECKPOINT PENDING REVIEW) |

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

Stage 15 — Full-chain Final Acceptance (Stage 15A Real Browser E2E, Stage 15B High-Aesthetic Regression, Stage 15C Final Regression + DEV Retriever Ablation + Local Latency Smoke).
- Stage 15C implementation/evaluation: PASS
- Stage 15 checkpoint: PENDING REVIEW

## Current Blockers

None.

## Next Gate

Stage 16 — User Documentation & Project Packaging.

### Stage 16 User Guide Mandatory Requirements

Stage 16 User Guide (`docs/USER_GUIDE.md` / `README.md`) MUST explicitly include the following 15 sections:

1. **系统用途**：面向户外功能服装智能养护的垂直领域可追溯 RAG 问答系统。
2. **支持的知识范围**：防水外壳 (GORE-TEX / 冲锋衣)、DWR 防泼水涂层恢复、羽绒服装护理、软壳与抓绒透气保暖护理。
3. **当前 KB 概况**：14 个官方来源，234 个知识切片（包含 Arc'teryx、GORE-TEX、Patagonia、Nikwax 等权威指南）。
4. **推荐提问方式**：提问应包含完整且具体的服装类型、面料材质/技术（如 GORE-TEX、DWR、白鹅绒）以及具体的护理环节（水温、洗涤剂类型、烘干温度等）。
5. **示例问题**：提供一键填入并可复现的高质量示例（如冲锋衣机洗水温、不挂水珠恢复方法、羽绒服结团处理等）。
6. **单轮问答 / 无记忆说明**：**FORAG 当前采用单轮问答模式。每次提交的问题独立处理，系统不会自动使用上一轮对话作为下一轮问题的上下文。因此后续提问应再次说明服装类型、材质/技术、品牌和具体问题。**
7. **answered 状态说明**：证据充分，基于官方资料生成可靠养护建议并严格标注行内引用 `[E#]`。
8. **needs_more_information 状态说明**：输入缺少必要上下文（如面料类型、洗标信息），系统拒绝凭空推断并引导补充信息。
9. **insufficient_evidence 状态说明**：超出知识库范围或证据不足，系统明确告知并安全终止。
10. **Sources 的含义**：代表最终回答实际引用 / 投射的官方来源清单（包含文档标题、章节标题、官方出处链接）。
11. **Evidence / 候选检索结果的含义**：代表多路混合检索与 Cross-Encoder 重排筛选出的 Top-5 核心候选切片（在 `answered` 状态下为回答依据，在 `needs_more_information` / `insufficient_evidence` 状态下明确标注为候选参考，不作为最终回答依据）。
12. **Retrieval Process 如何查看**：说明右侧面板中 Query Analysis → BM25+Dense 并行召回 → RRF (k=60) 融合 → Cross-Encoder 重排 → Evidence Judge 证据判定 → 最终路由决策各步骤的含义。
13. **Metrics 页面如何理解**：说明 6 项评测指标含义（Recall@5 87.5%、Claim Recall 77.9%、Context Precision 41.2%、Faithfulness 81.4% 等），以及 Context Precision 41.2% 作为当前系统主要限制的客观原因。
14. **系统当前能力边界**：明确系统不提供跨领域医疗、穿搭导购推荐或无依据推测。
15. **常见使用问题**：涵盖连续追问处理、专业洗涤剂选择、低温烘干激活注意点等常见问答。

## Retrieval / Agent Status

Query Analysis/Qwen: IMPLEMENTED / REAL API VERIFIED (3/3 smoke); deterministic adapter verified; Frozen Hybrid Retriever unchanged.

BM25：IMPLEMENTED / REAL INTEGRATION VERIFIED。
Dense Retrieval：IMPLEMENTED / REAL INTEGRATION VERIFIED。
Python RRF：IMPLEMENTED。Cross-Encoder：IMPLEMENTED。Unified Hybrid Retriever：IMPLEMENTED / REAL E2E VERIFIED / FROZEN。Retriever architecture / parameters：FROZEN。
LangGraph、Evidence Judge、Query Rewrite、Answer Generation、Citation Generation、Citation Validation (deterministic reconciliation)、FastAPI backend integration、Vue QA integration：IMPLEMENTED / VERIFIED；Stage 14 final evaluation：DONE / PASS (Recall@5 87.5%, Faithfulness 81.4%, Claim Recall 77.9%, Context Precision 41.2%)。

Stage 9A shared transport and Agent contracts are DONE / PASS. Stage 9B routing, Stage 10 final-response generation, Stage 11A/11B end-to-end web integration, Stage 13 integrated DEV evaluation, and Stage 14 final TEST + RAGChecker evaluation are DONE / PASS. Next gate: Stage 15 Full-chain Final Acceptance.

## Git Checkpoints

- `ce8c82e docs: freeze official final evaluation results` (Stage 14 Official Result Freeze)
- `52e9a1f fix: reconcile answer citations deterministically` (Stage 14 Citation Runtime Bug Fix)
- `bdc2563 fix: harden final evaluation preflight` (Stage 14 Final Evaluation Preflight Hardening)
- `4590815 feat: freeze final evaluation contract` (Stage 14 Final Evaluation Contract Freeze)
- `d386f07 feat: complete integrated dev evaluation` (Stage 13 Integrated DEV Evaluation)

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
