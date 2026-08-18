# 户外功能服装智能养护 RAG 问答系统
# IMPLEMENTATION_PLAN.md
# 第6步：实施计划与阶段验收

## 1. 本阶段目标

前五步已经确定：

1. PROJECT_DEFINITION.md —— 项目解决什么问题
2. REQUIREMENTS.md —— 系统必须做到什么
3. ARCHITECTURE.md —— 系统如何协作
4. DATA_DESIGN.md —— 知识如何构建
5. TECHNICAL_BASELINE.md —— 使用什么技术和第一版参数

第6步只解决：

> 按什么顺序把整个系统真正实现出来，并保证每个阶段都有可验证结果。

从本阶段之后停止继续扩展架构，正式进入编码。

---

# 2. 实施原则

开发过程中遵守以下规则：

1. 一次只完成一个阶段；
2. 当前阶段未通过验收，不进入下一阶段；
3. 核心 RAG 功能不得使用 Mock；
4. BM25、Dense、RRF、Cross-Encoder 必须真实运行；
5. 不提前填写任何 Recall、Faithfulness、延迟等结果；
6. 不额外引入 Redis、Kafka、Milvus、Celery、Kubernetes、多 Agent 等组件；
7. 修改代码前先阅读现有设计文档；
8. 每个阶段完成后必须实际运行验证；
9. 配置统一从 `.env → config.py` 读取；
10. 每个阶段完成后再提交 Git。

---

# 3. 最终实施主线

整个项目只按照下面这条主线开发：

```text
阶段1  工程初始化
        ↓
阶段2  Elasticsearch环境
        ↓
阶段3  知识库构建
        ↓
阶段4  知识库验收 + Golden Dataset
        ↓
阶段5A Retrieval Foundation（BM25 + Dense Retriever）
        ↓
阶段5B Hybrid Retrieval（RRF + Cross-Encoder + Hybrid Retriever）
        ↓
阶段5C Retriever Evaluation & Freeze
        ↓
阶段8  Qwen API + Query Analysis
        ↓
阶段9  LangGraph RAG Workflow
        ↓
阶段10 Answer Generation + Citation
        ↓
阶段11 FastAPI
        ↓
阶段12 Vue Web
        ↓
阶段13 Integrated / Final Evaluation
        ↓
阶段14 RAGChecker
        ↓
阶段15 全链路验收
        ↓
阶段16 README + 简历结果
```

核心原则：

> 先把知识库和 Retriever 做通，再做 LangGraph、Web 和评测。

------

# 4. 阶段1：工程初始化

## 目标

建立最小可运行工程。

目录：

```text
fashion-care-rag/
│
├── backend/
│   └── app/
│       ├── knowledge/
│       ├── retrieval/
│       ├── agent/
│       ├── llm/
│       ├── generation/
│       ├── services/
│       ├── api/
│       ├── schemas/
│       ├── runtime.py
│       ├── config.py
│       └── main.py
│
├── frontend/
├── evaluation/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── dictionaries/
│   ├── manifests/
│   └── evaluation/
│
├── scripts/
├── tests/
├── results/
├── docs/
│
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

## 实现

后端：

```text
Python 3.12
uv
FastAPI
统一Config
Python logging
```

前端：

```text
Vue 3
Vite
Vue Router
```

此阶段不实现 RAG。

## 验收

后端：

```bash
uv sync
uv run uvicorn backend.app.main:app --reload
```

能够打开：

```text
http://127.0.0.1:8000/docs
```

前端：

```bash
npm install
npm run dev
```

能够打开：

```text
http://localhost:5173
```

------

# 5. 阶段2：Elasticsearch环境

## 目标

让 Elasticsearch 在本机真实运行。

采用：

```text
Elasticsearch 9.5.1
官方 Windows x86_64 ZIP
Windows 本机单节点运行
```

地址：

```text
https://localhost:9200
```

配置：

```ini
ES_URL=https://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=
ES_CA_CERT=
ES_INDEX_NAME=fashion_care_kb_v1
```

安装与启动步骤：

1. 下载 `elasticsearch-9.5.1-windows-x86_64.zip`；
2. 解压到本机固定目录；
3. 进入 Elasticsearch 根目录并运行：

```powershell
.\bin\elasticsearch.bat
```

4. 保存首次初始化输出的 `elastic` 用户密码；
5. 使用 `config\certs\http_ca.crt` 作为本机 HTTPS 连接的 CA 证书；
6. 通过 Elasticsearch Python Client 使用 URL、用户名、密码和 CA 证书连接；
7. 实际验证 Elasticsearch 可以访问。

Windows ZIP 包自带 OpenJDK，不单独安装 Java / JDK。保持 Elasticsearch 默认安全机制，不主动关闭 security。不使用 Docker Desktop、Docker、docker compose 或 WSL。

创建统一 ES Client。

不要在 BM25、Dense、Indexer 中分别初始化 Client。

## 验收

Elasticsearch 必须通过 `.\bin\elasticsearch.bat` 启动成功，并能使用 HTTPS、`elastic` 账号和 `config\certs\http_ca.crt` 成功连接 `https://localhost:9200`。

健康检查能够返回：

```json
{
  "api": "ok",
  "elasticsearch": "ok"
}
```

------

# 6. 阶段3：知识库构建

这是第一个核心阶段。

完整流程：

```text
Official Documents
        ↓
Source Manifest
        ↓
Loader
        ↓
Cleaner
        ↓
Structure-aware Chunking
        ↓
基础 Metadata
        ↓
Embedding
        ↓
chunks.jsonl
        ↓
Elasticsearch
```

------

## 6.1 Source Manifest

创建：

```text
data/manifests/sources.jsonl
```

第一版只收集少量真实官方护理资料。

优先覆盖：

```text
GORE-TEX 清洗
DWR恢复
羽绒护理
干燥
储存
基础护理问题
```

每个来源至少：

```json
{
  "source_id": "...",
  "brand": "...",
  "source_title": "...",
  "source_url": "...",
  "language": "en",
  "local_path": "...",
  "content_hash": "..."
}
```

不做全站爬虫。

------

## 6.2 Loader

实现：

```text
Manifest
+
Local Raw File
↓
RawDocument
```

职责只是统一读取资料。

------

## 6.3 Cleaner

删除：

```text
导航
Footer
Cookie文本
营销噪声
无意义HTML
```

保留：

```text
Heading
Paragraph
List
Warning
护理步骤
来源
```

禁止：

```text
原文 → LLM总结 → Knowledge Base
```

------

## 6.4 Chunking

只实现三个核心规则：

### 规则1：显式结构优先

优先：

```text
Heading
Paragraph
List
```

进行组织。

### 规则2：护理操作保持完整

尽量不拆开：

```text
Condition + Action
Action + Warning
连续护理步骤
```

### 规则3：长度兜底

结构块过长时：

```text
multilingual-e5-small tokenizer
↓
递归切分
```

Baseline：

```ini
MAX_CHUNK_TOKENS=320
MIN_CHUNK_TOKENS=60
FALLBACK_OVERLAP_TOKENS=40
```

不开发复杂语义 Chunking 模型。

------

## 6.5 Metadata

P0 只保留：

```text
brand
garment_type
technology
care_stage
```

以及必要溯源：

```text
chunk_id
parent_doc_id
source_id
section_title
source_title
source_url
language
content_hash
kb_version
```

不维护复杂 Metadata Provenance。

------

## 6.6 术语表

创建：

```text
data/dictionaries/terminology.json
```

只维护高频护理概念。

例如：

```json
{
  "concept": "water_repellency_loss",
  "query_aliases_zh": [
    "不挂水",
    "不挂水珠"
  ],
  "retrieval_terms_en": [
    "DWR",
    "water repellency",
    "water beading",
    "wetting-out"
  ]
}
```

不建设大型服装 Ontology。

------

## 6.7 Embedding

模型：

```text
intfloat/multilingual-e5-small
```

Document：

```text
passage:
source_title
+
section_title
+
content
```

输出：

```text
384维Embedding
```

保存：

```text
data/processed/chunks.jsonl
```

然后写入 Elasticsearch。

------

## 6.8 Knowledge Base Build

统一脚本：

```bash
python scripts/build_knowledge_base.py
```

默认不能无限追加重复文档。

ES：

```text
_id = chunk_id
```

如果需要重新构建：

```bash
python scripts/build_knowledge_base.py --rebuild
```

执行：

```text
删除旧 kb_v1 Index
↓
重新创建Mapping
↓
重新Index
```

------

## 验收

必须确认：

```text
Source是真实官方来源
Chunk不是空文本
chunk_id唯一
Embedding全部384维
ES文档数量与chunks.jsonl一致
Source URL可追踪
```

并人工抽查 10～20 个 Chunk。

通过后：

> 冻结 `kb_v1`。

------

# 7. 阶段4：Golden Dataset

知识库冻结后立即建立评测集，不等 Web 做完。

创建：

```text
data/evaluation/golden_dataset.jsonl
```

结构：

```json
{
  "question": "...",
  "gt_answer": "...",
  "gold_chunk_ids": ["..."],
  "category": "...",
  "kb_version": "kb_v1",
  "split": "dev"
}
```

------

## 问题覆盖

至少覆盖：

```text
GORE-TEX清洗
DWR恢复
中文口语“不挂水珠”
羽绒结团
干燥
储存
品牌限定
技术限定
信息不足
```

问题和 GT 由官方知识人工核对。

不得：

```text
让当前RAG生成答案
↓
直接作为GT
```

------

## Dev / Test

简单分成：

```text
dev
→ 开发和调参数

test
→ 最终评测
```

不需要 train / validation 等复杂划分。

重要规则：

> 最终参数确定以后再运行 test，不再根据 test 结果继续调参。

------

# 8. 阶段5：BM25 Retriever

文件：

```text
backend/app/retrieval/bm25.py
```

输入：

```text
lexical_terms_en
+
structured_query
```

例如：

```text
GORE-TEX
DWR
water repellency
wetting-out
```

全文字段：

```text
content
source_title
section_title
normalized_terms
```

Metadata：

```text
brand
technology
```

只做简单 Boost，不做 Hard Filter。

Baseline：

```ini
BM25_TOP_K=20
```

输出统一为：

```text
RetrievalCandidate
```

例如：

```python
RetrievalCandidate(
    chunk_id,
    content,
    source_title,
    source_url,
    bm25_score
)
```

## 验收

输入：

```text
GORE-TEX DWR water repellency
```

必须能够返回相关官方 Chunk。

------

# 9. 阶段6：Dense Retriever

文件：

```text
backend/app/retrieval/dense.py
```

输入：

```text
original_query
```

例如：

```text
我的冲锋衣现在不挂水珠了
```

流程：

```text
query: 中文Query
↓
multilingual-e5-small
↓
384维Query Embedding
↓
Elasticsearch kNN
```

Baseline：

```ini
DENSE_TOP_K=20
DENSE_NUM_CANDIDATES=100
```

## 核心验收

中文 Query：

```text
我的冲锋衣现在不挂水珠了
```

应能够召回英文：

```text
DWR
water repellency
water beading
```

相关知识。

这是 Dense Retrieval 的主要价值。

------

# 10. 阶段7：RRF + Cross-Encoder + Hybrid Retriever

这一阶段完成整个核心 Retriever。

------

## 10.1 RRF

文件：

```text
retrieval/rrf.py
```

输入：

```text
BM25 Top20
Dense Top20
```

公式：

```text
RRF(d) = Σ 1 / (k + rank_i(d))
```

Baseline：

```ini
RRF_K=60
RRF_TOP_N=30
```

需要保留：

```text
bm25_rank
dense_rank
rrf_score
```

用于调试。

------

## 10.2 Cross-Encoder

文件：

```text
retrieval/reranker.py
```

模型：

```text
cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
```

流程：

```text
RRF Top30
↓
Cross-Encoder
↓
Top5
```

Baseline：

```ini
RERANK_TOP_K=5
```

禁止：

```python
docs[:5]
```

冒充 Reranking。

------

## 10.3 Hybrid Retriever

文件：

```text
retrieval/hybrid.py
```

统一接口：

```python
retrieve(
    active_query,
    lexical_terms_en,
    structured_query
)
```

首次检索时：

```text
active_query = original_query
```

唯一一次 Rewrite 后：

```text
active_query = reformulated_query
```

BM25 使用 `lexical_terms_en`、明确实体和 active query；Dense 使用 active query。

内部：

```text
BM25 Top20
+
Dense Top20
↓
RRF Top30
↓
Cross-Encoder
↓
Top5 Evidence
```

------

## Retriever核心验收

暂时不用 Qwen。

手动输入：

```text
original_query:
我的GORE-TEX冲锋衣现在不挂水珠了怎么办？

lexical_terms_en:
GORE-TEX
DWR
water repellency
wetting-out
```

然后得到：

```text
真实Top-5 Evidence
```

如果这里效果明显错误：

> 不进入 LangGraph 开发。

------

# 11. 阶段8：Qwen API 与 Query Analysis

实现：

```text
backend/app/llm/
├── client.py
├── schemas.py
└── prompts.py
```

统一：

```text
LLMClient
```

第一版模型：

```text
qwen3.7-plus
```

------

## Query Analysis

用户：

```text
我的GORE-TEX冲锋衣现在不挂水珠了
```

一次结构化调用返回：

```json
{
  "structured_query": {
    "brand": null,
    "garment_type": "hardshell",
    "technology": ["GORE-TEX"],
    "issue_type": "water_repellency_loss",
    "intent": "care_troubleshooting"
  },
  "lexical_terms_en": [
    "GORE-TEX",
    "DWR",
    "water repellency",
    "wetting-out"
  ]
}
```

因此：

```text
lexical_terms_en
→ BM25

original_query
→ Dense
```

不再单独增加一个 Query Formulation LLM Node。

------

## LLM异常

保持简单：

```text
API失败
↓
Retry
↓
仍失败
↓
返回明确服务错误
```

不实现复杂降级系统。

------

# 12. 阶段9：LangGraph Workflow

文件：

```text
backend/app/agent/
├── state.py
├── nodes.py
├── routes.py
└── workflow.py
```

State 简化为：

```text
original_query
reformulated_query
structured_query
lexical_terms_en
retrieved_docs
evidence_sufficient
insufficient_reason
rewrite_count
answer
sources
trace
```

------

## Workflow

```text
START
 ↓
Query Analysis
 ↓
Hybrid Retrieval
 ↓
Evidence Grade
 ↓
 ┌───────────────┬────────────────────┐
 ↓               ↓                    ↓
sufficient   retrieval_problem   missing_information
 ↓               ↓                    ↓
Generate       Rewrite              返回提示
                 ↓
              Retrieve
                 ↓
           Evidence Grade
                 ↓
             仍然不足
                 ↓
                END
```

只允许：

```ini
MAX_REWRITE_COUNT=1
```

一次 Rewrite 足够体现 LangGraph Feedback Loop。

------

## Evidence Grade

输入：

```text
Original Query
+
Top5 Evidence
```

输出：

```text
sufficient

retrieval_problem

missing_information
```

直接使用 Qwen structured output。

不增加复杂阈值评分系统。

------

# 13. 阶段10：Generation 与 Citation

输入：

```text
Original Query
+
Top5 Evidence
```

Evidence 编号：

```text
[E1]
[E2]
[E3]
[E4]
[E5]
```

Qwen 只能输出：

```text
建议……。[E1]
```

禁止生成 Source URL。

后端：

```text
[E1]
↓
chunk_id
↓
source_title
source_url
```

------

## Citation Validator

只做简单检查：

```text
模型引用 E1～E5
↓
提取citation
↓
验证是否属于当前Evidence
↓
映射Source
```

例如本次只有：

```text
E1~E5
```

模型却产生：

```text
[E9]
```

则不能把它作为有效来源。

------

# 14. 阶段11：FastAPI

实现：

```text
POST /api/chat
GET /api/health
GET /api/metrics
```

结构：

```text
FastAPI
↓
RAGService
↓
LangGraph
```

`RAGService` 保持很薄。

例如：

```python
answer(query)
```

即可。

------

## Runtime Resources

统一：

```text
runtime.py
```

初始化一次：

```text
ES Client
Embedding Model
Cross-Encoder
```

FastAPI 和评测脚本都复用这套初始化逻辑。

不要每个请求重新加载模型。

------

## CORS

本地只允许前端开发地址，例如：

```text
http://localhost:5173
```

保证：

```text
Vue
→ FastAPI
```

浏览器访问正常。

------

## Metrics

如果尚未运行评测：

```json
{
  "available": false,
  "metrics": null
}
```

不能报 500，也不能返回假指标。

------

# 15. 阶段12：Vue Web

只实现两个页面。

## ChatView

包含：

```text
问题输入
发送按钮
Loading
答案
Source
Evidence
简化Trace
错误信息
```

Trace 只展示：

```text
Query Analysis
BM25候选数量
Dense候选数量
RRF候选数量
最终Top5
是否Rewrite
总耗时
```

不要展示整个 LangGraph 内部 State。

------

## MetricsView

显示：

```text
Recall@5
Claim Recall
Context Precision
Faithfulness
```

评测前显示：

```text
尚未评测
```

------

# 16. 阶段13：Integrated / Final Evaluation

Stage 5C 已完成 standalone Hybrid Retriever 的 Frozen Golden Dataset dev/test evaluation 与参数冻结。本阶段仅在 Query Analysis、Agent、Answer 等完整系统实现后，评估集成链路；不得使用 Stage 5C test misses 重新调整已冻结的 Retriever 参数。

先使用：

```text
Golden Dataset dev
```

评估：

```text
Recall@5
```

流程：

```text
Question
↓
Query Analysis
↓
Hybrid Retriever
↓
Top5
↓
gold_chunk_ids
↓
Recall@5
```

输出：

```text
overall Recall@5
category Recall@5
per-query result
```

这里的 dev 仅用于集成链路验证；Stage 5C 已冻结的 Retriever configuration 不在后续 test 结果驱动下重新调整。

------

# 17. 冻结参数

Stage 5C 已完成 dev/test evaluation，并已冻结 Retrieval Configuration。

后续 dev 阶段允许调整 Agent、Query Analysis、Evidence、Rewrite 和 Generation 层；不得调整 Frozen Retriever Configuration，也不得使用 Stage 5C test misses 重新打开 Retriever tuning。

之后不再因为 Test 结果修改参数。

------

# 18. 阶段14：最终Evaluation

## Recall@5

在：

```text
test split
```

上运行最终 Recall@5。

------

## RAGChecker

输入：

```text
question
gt_answer
retrieved_context
generated_response
```

最终只关注：

```text
Claim Recall
Context Precision
Faithfulness
```

Evaluator 使用固定模型 Snapshot，并在结果中记录模型名。

不额外开展复杂 Evaluator 模型比较。

------

## 输出

生成：

```text
results/
├── kb_build_report.json
├── retrieval_evaluation.json
├── ragchecker_results.json
└── final_metrics.json
```

`final_metrics.json` 至少：

```json
{
  "kb_version": "kb_v1",

  "embedding_model": "intfloat/multilingual-e5-small",
  "reranker_model": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
  "generator_model": "qwen3.7-plus-2026-05-26",

  "evaluation_samples": 0,

  "recall_at_5": null,
  "claim_recall": null,
  "context_precision": null,
  "faithfulness": null
}
```

全部由程序真实生成。

------

# 19. 阶段15：全链路验收

最终必须真正完成：

```text
Browser
↓
Vue
↓
FastAPI
↓
LangGraph
↓
Query Analysis
↓
BM25 + Dense
↓
RRF
↓
Cross-Encoder
↓
Evidence Grade
↓
Generate / Rewrite / Missing Info
↓
Citation
↓
Answer + Sources
↓
Vue
```

------

## 必测场景

至少测试：

### 正常问题

```text
GORE-TEX冲锋衣怎么洗？
```

### 中文口语

```text
冲锋衣现在不挂水珠了怎么办？
```

### 羽绒

```text
羽绒服洗完以后羽绒结成一团怎么办？
```

### 品牌/技术限制

```text
GORE-TEX衣服应该怎么烘干？
```

### 信息不足

```text
我的衣服能放烘干机吗？
```

### Rewrite路径

初次 Query 表达较差，但知识库存在相关证据。

### 无法找到证据

系统应明确说明证据不足，而不是编造答案。

------

# 20. 最终代码检查

项目结案前扫描：

```text
TODO
FIXME
NotImplemented
mock
placeholder
fake
dummy
hardcoded metrics
docs[:5]
```

重点确认：

```text
BM25真实
Dense真实
RRF真实
Cross-Encoder真实
Qwen真实
LangGraph条件分支真实
Recall@5真实
RAGChecker真实
```

------

# 21. 日志

不使用复杂监控系统。

Python logging 足够。

至少记录：

```text
Query
BM25 latency
Dense latency
RRF latency
Rerank latency
LLM latency
Total latency
Error
```

最终真实运行以后才能统计响应时间。

------

# 22. Git策略

每个阶段通过后：

```bash
git status
git diff
git add .
git commit -m "..."
```

建议关键提交：

```text
chore: initialize project
feat: build knowledge base
feat: implement bm25 retrieval
feat: implement dense retrieval
feat: implement hybrid retrieval
feat: integrate qwen
feat: build langgraph workflow
feat: add evidence citation
feat: add fastapi service
feat: add vue frontend
feat: add rag evaluation
docs: finalize project results
```

不要求每个小函数都 Commit。

------

# 23. Codex统一执行规则

每次给 Codex 一个阶段。

统一 Prompt：

请先阅读：

- docs/PROJECT_DEFINITION.md
- docs/REQUIREMENTS.md
- docs/ARCHITECTURE.md
- docs/DATA_DESIGN.md
- docs/TECHNICAL_BASELINE.md
- docs/IMPLEMENTATION_PLAN.md

当前只实施 IMPLEMENTATION_PLAN.md 中的【阶段X】。

要求：

1. 先检查现有仓库；
2. 不提前实现下一阶段；
3. 遵守现有架构和技术Baseline；
4. 核心功能不得使用Mock；
5. 不增加未设计的新框架或基础设施；
6. 增加本阶段必要测试；
7. 实际运行验证；
8. 失败则先定位并修复；
9. 完成后停止，不继续下一阶段。

最后报告：

- 修改文件；
- 输入；
- 核心实现；
- 输出；
- 实际运行命令；
- 实际运行结果；
- 测试结果；
- 当前尚未实现内容。

------

# 24. 最关键的阶段停止点

整个实施过程中有三个必须停下来验收的位置。

## 停止点A：Knowledge Base

必须证明：

```text
Official Source
→ Chunk
→ Embedding
→ Elasticsearch
```

真实完成。

------

## 停止点B：Hybrid Retriever

必须证明：

```text
BM25
+
Dense
↓
RRF
↓
Cross-Encoder
↓
真实Top5
```

能够工作。

如果 Retriever 本身不对：

> 不允许靠 Qwen 弥补检索错误。

------

## 停止点C：Final Evaluation

只有：

```text
Golden Test Set
↓
真实Final Pipeline
↓
Recall@5
+
RAGChecker
```

运行以后，才允许填写项目最终结果。

------

# 25. 实施结束条件

满足以下条件才能认为项目完成：

```text
[ ] 官方知识库真实构建
[ ] Elasticsearch真实存储
[ ] BM25真实执行
[ ] Dense真实执行
[ ] RRF真实执行
[ ] Cross-Encoder真实执行
[ ] Qwen Query Analysis真实执行
[ ] LangGraph有真实条件分支
[ ] Rewrite最多执行一次
[ ] Evidence不足可以停止
[ ] Answer基于真实Evidence
[ ] Source URL来自Knowledge Base
[ ] FastAPI可访问
[ ] Vue浏览器可使用
[ ] Golden Dataset存在
[ ] Recall@5真实计算
[ ] RAGChecker真实运行
[ ] final_metrics.json真实生成
```

全部满足：

**第6步实施计划完成，项目可以结案。**
