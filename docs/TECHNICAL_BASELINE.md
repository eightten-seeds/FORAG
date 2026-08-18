# 第5步：技术选型与参数基线

## 1. 本阶段目标

前四步已经确定：

```text
项目定义
↓
需求分析
↓
系统架构
↓
数据与知识库设计
```

第 5 步解决：

> **这个架构具体用什么技术实现，第一版从什么参数开始。**

本阶段需要区分两类内容：

```text
技术选型
→ 可以正式固定

参数Baseline
→ 只是第一版工程起点，不代表最优
```

------

# 2. 技术选型原则

本项目第一版遵循：

1. 完整系统可在个人电脑运行；
2. 核心 RAG 检索链路必须真实执行；
3. 不要求本地部署大型 LLM；
4. 用户以中文提问，知识库以英文官方护理资料为主；
5. 支持中文 Query → 英文 Document 的跨语言检索；
6. 技术链必须能够自己解释；
7. 不引入 Redis、Kafka、Milvus、Celery、Kubernetes 等非必要组件；
8. LLM Provider 与核心 Retrieval 解耦；
9. 所有最终指标必须可以复现。

------

# 3. 第一版最终技术栈

| 层             | 技术                                       |
| -------------- | ------------------------------------------ |
| 后端语言       | Python 3.12                                |
| Python依赖管理 | uv + pyproject.toml + uv.lock              |
| Web后端        | FastAPI 0.141.1                            |
| 工作流         | LangGraph 1.2.11                           |
| 检索引擎       | Elasticsearch 9.5.1                        |
| Embedding框架  | sentence-transformers 5.7.0                |
| Embedding      | intfloat/multilingual-e5-small             |
| Embedding维度  | 384                                        |
| Reranker       | cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 |
| LLM Provider   | 阿里云百炼                                 |
| 开发LLM        | qwen3.7-plus                               |
| 最终评测LLM    | qwen3.7-plus-2026-05-26                    |
| LLM接口        | OpenAI-compatible Chat Completions         |
| 结构化输出     | JSON Schema strict                         |
| 前端           | Vue 3 + Vite                               |
| Node           | Node.js 24 LTS                             |
| RAG评测        | Recall@5 + RAGChecker                      |
| ES运行         | Windows ZIP 本地单节点运行                 |

截至当前，Elasticsearch 9.5.1、FastAPI 0.141.1、LangGraph 1.2.11 和 Sentence Transformers 5.7.0 都是已发布版本；LangGraph定位为低层有状态工作流编排框架。([Elastic](https://www.elastic.co/docs/release-notes/elasticsearch?utm_source=chatgpt.com))

------

# 4. P0知识库语言范围

第一版明确：

```text
用户Query：
中文为主
兼容英文

知识库：
优先使用英文官方护理资料
```

例如：

```text
用户：
“冲锋衣现在不挂水珠了”

Document：
“Restore durable water repellency when water no longer beads...”
```

这样第一版不额外引入复杂中文 Elasticsearch Analyzer。

跨语言问题分别交给：

```text
Lexical Path
→ 中文概念识别
→ 英文专业检索词
→ BM25

Semantic Path
→ multilingual E5
→ 中文Query ↔ 英文Document
```

如果以后扩大中文官方资料比例，再单独设计中文 Analyzer。

------

# 5. Embedding选型

固定：

```text
intfloat/multilingual-e5-small
```

原因：

- 多语言；
- 适合 Query → Passage Retrieval；
- 模型规模适合个人电脑；
- 向量维度只有 384；
- 能满足中文 Query 与英文 Document 的跨语言语义检索。

模型卡明确给出 384 维 Embedding。([Hugging Face](https://huggingface.co/intfloat/multilingual-e5-small?utm_source=chatgpt.com))

ES：

```json
"embedding": {
  "type": "dense_vector",
  "dims": 384,
  "index": true,
  "similarity": "cosine"
}
```

------

# 6. E5编码规范

必须统一：

```text
Query:
query: {semantic_query}

Document:
passage: {embedding_text}
```

不能一部分代码使用前缀、一部分不使用。

Document：

```text
passage:
Title
+
Section Path
+
Official Content
```

Semantic Query：

```text
query:
用户原始问题
```

Dense Path 原则上保留用户原始语义，而不是塞大量人工关键词。

首次检索使用 `original_query`；唯一一次 Rewrite 后使用 `reformulated_query`。Query Analysis 不会因此重复调用。

------

# 7. Chunk Token计数

第一版：

```ini
MAX_CHUNK_TOKENS=320
MIN_CHUNK_TOKENS=60
FALLBACK_OVERLAP_TOKENS=40
```

这里最重要的规则是：

> **Token 数必须使用 multilingual-e5-small 对应 tokenizer 计算。**

禁止用：

```text
字符数
空格split
tiktoken
其他LLM tokenizer
```

来定义这 320 tokens。

参数 320 只是第一版 Baseline，不是最优实验结果。

真实 Chunking 仍是：

```text
结构块
↓
简单完整性规则
↓
如果仍过长
↓
Token长度兜底
```

而不是每 320 tokens 强制切一刀。

------

# 8. Query Analysis实现方式

P0 不实现独立 Query Formulation Node，也不为查询构造再次调用 Qwen。

一次 Qwen structured-output 请求直接输出：

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
    "water beading",
    "wetting-out"
  ]
}
```

得到两类产物：

```text
structured_query
+
lexical_terms_en
```

然后：

```text
BM25
→ lexical_terms_en + 明确实体

Dense
→ original_query
```

这样少一次 LLM API 调用。

------

# 9. 术语映射

术语表区分 Query 侧和 Document 侧。

例如：

```json
{
  "concept": "water_repellency_loss",

  "query_aliases_zh": [
    "不挂水",
    "不挂水珠",
    "防泼水下降"
  ],

  "retrieval_terms_en": [
    "DWR",
    "water repellency",
    "water beading",
    "wetting-out"
  ]
}
```

因此：

```text
中文Query
↓
识别领域概念
↓
得到英文retrieval terms
↓
BM25查询英文Document
```

不要把大量中文 Query Alias 写进英文知识 Chunk。

------

# 10. BM25字段设计

BM25 不使用一个巨大的：

```text
search_text
```

而采用 Elasticsearch 多字段检索。

全文相关字段：

```text
content
source_title
section_title
normalized_terms
```

结构化字段：

```text
brand
technology
garment_type.keyword
care_stage.keyword
```

逻辑关系：

```text
             Elasticsearch Query
                    │
        ┌───────────┴───────────┐
        ↓                       ↓
全文相关性                  结构化匹配
BM25                       term / should
        ↓                       ↓
content                   brand
title                     technology
section                   garment_type
normalized_terms          care_stage
```

第一版 Field Boost：

```ini
CONTENT_BOOST=1.0
TITLE_BOOST=1.5
SECTION_BOOST=1.5
NORMALIZED_TERMS_BOOST=1.5

BRAND_BOOST=1.5
TECHNOLOGY_BOOST=2.0
```

都是 Baseline。

------

# 11. Metadata原则

第一版：

> **只使用简单 Metadata Boost。**

原因：

```text
Metadata错误
+
Hard Filter
↓
正确Chunk直接被排除
```

因此用户明确出现的品牌、技术等可以先：

```text
term should / boost
```

P0 不实现 Hard Filter / Boost 切换体系；仅允许在 dev 集上有限调整上述简单 Boost 权重。

------

# 12. 第一阶段召回

Baseline：

```ini
BM25_TOP_K=20

DENSE_TOP_K=20
DENSE_NUM_CANDIDATES=100
```

形成：

```text
                Query
                 │
        ┌────────┴────────┐
        ↓                 ↓
      BM25              Dense
     Top-20             Top-20
        │                 │
        └────────┬────────┘
                 ↓
                RRF
```

Top-20 只是候选池初始值。

------

# 13. RRF

RRF 在 Python 应用层自己实现。

虽然 Elasticsearch 本身原生支持 Hybrid Search 与 RRF，而且 Elastic 官方也推荐使用 RRF 组合全文与向量检索，但本项目仍选择应用层实现。([Elastic](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/rrf-retriever?utm_source=chatgpt.com))

原因：

```text
可以看到BM25排名
可以看到Dense排名
可以看到每个Chunk的RRF贡献
便于调试
便于答辩
算法不依赖ES内部融合
```

公式：

```text
RRF(d)
=
Σ 1 / (k + rank_i(d))
```

Baseline：

```ini
RRF_K=60
RRF_TOP_N=30

BM25_RRF_WEIGHT=1.0
DENSE_RRF_WEIGHT=1.0
```

流程：

```text
BM25 Top20 ─────┐
                ├→ 去重 → RRF → Top30
Dense Top20 ────┘
```

必须明确：

> RRF不是唯一融合方法。

也可以做归一化后 Weighted Fusion。本项目选择 RRF 是为了避免直接处理两个 Retriever 原始 Score 的尺度差异。Elastic 对 RRF 的定义同样强调其用于融合不同 relevance indicator 的结果。([Elastic](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion?utm_source=chatgpt.com))

------

# 14. Cross-Encoder

固定：

```text
cross-encoder/mmarco-mMiniLMv2-L12-H384-v1
```

该模型基于 multilingual MiniLMv2，并在 MMARCO 多语言数据上训练，模型卡明确用于信息检索后的 passage reranking，规模约 0.1B。([Hugging Face](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1))

Baseline：

```ini
RERANK_CANDIDATE_TOP_N=30
RERANK_TOP_K=5
RERANK_BATCH_SIZE=8
RERANKER_DEVICE=cpu
```

流程：

```text
RRF Top30
↓
(Query, Chunk)
↓
Cross-Encoder
↓
rerank_score
↓
Top-5 Evidence
```

不能使用：

```python
docs[:5]
```

冒充 Rerank。

------

# 15. Embedding与Reranker加载方式

两个模型必须在应用启动阶段**只加载一次**。

禁止：

```python
def search():
    model = SentenceTransformer(...)
```

或者：

```python
def rerank():
    model = CrossEncoder(...)
```

正确：

```text
FastAPI Startup / Lifespan
           ↓
初始化ES Client
加载Embedding Model
加载Cross-Encoder
           ↓
Application Resources
           ↓
所有HTTP请求复用
```

否则每次请求都会重新加载模型，CPU、内存和延迟都会严重恶化。

------

# 16. Elasticsearch运行

固定：

```text
Elasticsearch 9.5.1
官方 Windows x86_64 ZIP
Windows 本机单节点运行
```

安装与启动：

```text
下载 elasticsearch-9.5.1-windows-x86_64.zip
解压到本机固定目录
进入 Elasticsearch 根目录
.\bin\elasticsearch.bat
```

Windows ZIP 包自带 OpenJDK，不单独安装 Java / JDK。P0 不使用 Docker Desktop、Docker、docker compose 或 WSL 运行 Elasticsearch。

保持 Elasticsearch 首次启动时默认启用的安全机制，不为了简化项目关闭 security。首次启动后保存 `elastic` 用户密码，并使用自动生成的：

```text
config\certs\http_ca.crt
```

作为本机 HTTPS 客户端连接的 CA 证书。不要为本机开发主动绑定所有公网接口。

配置：

```ini
ES_URL=https://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=
ES_CA_CERT=

ES_INDEX_NAME=fashion_care_kb_v1

ES_NUMBER_OF_SHARDS=1
ES_NUMBER_OF_REPLICAS=0
```

ES负责：

```text
Chunk存储
Metadata存储
BM25
Dense Vector kNN
```

不负责：

```text
RRF
Cross-Encoder
LangGraph
LLM
```

Python Elasticsearch Client 统一通过 `ES_URL`、用户名、密码和 `ES_CA_CERT` 建立经过 CA 校验的 HTTPS 连接。

Elasticsearch 原生支持 `dense_vector` 与 kNN/vector search。([Elastic](https://www.elastic.co/docs/solutions/search/vector/knn?utm_source=chatgpt.com))

------

# 17. LLM最终选型

第一版 Provider：

```text
阿里云百炼
```

开发模型：

```text
qwen3.7-plus
```

正式评测：

```text
qwen3.7-plus-2026-05-26
```

阿里云官方说明 `qwen3.7-plus` 当前与 `qwen3.7-plus-2026-05-26` 功能等价，并提供该固定 Snapshot。([阿里云帮助中心](https://help.aliyun.com/en/model-studio/qwen3-7-plus))

这样：

```text
开发
→ alias方便

最终Evaluation
→ snapshot保证模型版本可追踪
```

------

# 18. 为什么使用Qwen3.7-Plus

主要不是因为“它一定比其他模型强”，而是它适合本项目的工程需求。

LLM主要负责：

```text
Query Analysis
Evidence Grade
Query Rewrite
Answer Generation
```

其中 Query Analysis 和 Evidence Grade 需要可靠结构化输出。

Qwen3.7-Plus 当前支持 JSON Schema 模式，并支持 `strict: true` 强制指定结构和字段类型。([阿里云帮助中心](https://help.aliyun.com/en/model-studio/qwen-structured-output))

因此可以直接得到：

```json
{
  "evidence_sufficient": false,
  "insufficient_reason": "retrieval_problem"
}
```

供 LangGraph Conditional Edge 使用。

------

# 19. LLM接口

采用：

```text
OpenAI-compatible
Chat Completions API
```

阿里云官方提供对应的 OpenAI-compatible 调用方式。([阿里云帮助中心](https://help.aliyun.com/en/model-studio/qwen-structured-output))

配置：

```ini
LLM_PROVIDER=qwen

DASHSCOPE_API_KEY=
QWEN_BASE_URL=

QWEN_DEV_MODEL=qwen3.7-plus
QWEN_EVAL_MODEL=qwen3.7-plus-2026-05-26
```

`BASE_URL` 通过 `.env` 配置，避免写死地域 Endpoint。

------

# 20. Thinking模式

Qwen3.7 Plus属于 Hybrid Thinking 系列，官方当前说明 thinking 默认开启。([阿里云帮助中心](https://help.aliyun.com/en/model-studio/deep-thinking?utm_source=chatgpt.com))

P0统一：

```ini
LLM_ENABLE_THINKING=false
```

适用于：

```text
Query Analysis
Evidence Grade
Query Rewrite
Generation
```

原因：

这些任务主要是：

```text
抽取
分类
改写
基于Evidence回答
```

没有必要为了第一版增加大量推理 Token 和延迟。

如果后续真实评测证明某个节点开启 Thinking 有明显改善，再针对该节点修改。

------

# 21. Query Analysis

使用：

```text
qwen3.7-plus
+
JSON Schema strict
```

一次调用同时完成：

```text
实体抽取
领域概念识别
Lexical Terms生成
```

输出：

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

不能凭空添加用户没有提供的品牌、型号或材料事实。

------

# 22. Evidence Grade

输入：

```text
Original Query
+
Structured Query
+
Top-5 Evidence
```

使用：

```text
Qwen3.7-Plus
+
JSON Schema
```

输出只允许：

```json
{
  "evidence_sufficient": true,
  "insufficient_reason": null
}
```

或者：

```json
{
  "evidence_sufficient": false,
  "insufficient_reason": "retrieval_problem"
}
```

或者：

```json
{
  "evidence_sufficient": false,
  "insufficient_reason": "missing_information"
}
```

不提前设计：

```text
CrossEncoder Score > 0.7
```

这种没有实验依据的阈值。

------

# 23. Query Rewrite

只有：

```text
insufficient_reason
=
retrieval_problem
```

才 Rewrite。

如果：

```text
missing_information
```

则：

```text
返回需要补充的信息
→ END
```

第一版：

```ini
MAX_REWRITE_COUNT=1
```

Rewrite必须：

```text
保留original_query
保留品牌
保留型号
保留technology
保留用户明确条件
```

只产生：

```text
reformulated_query
```

不能覆盖 Original Query。

------

# 24. LLM失败处理

配置：

```ini
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

第一版统一处理：

```text
任一LLM调用失败
↓
简单Retry
↓
仍失败
↓
返回明确的LLM服务错误
```

不实现绕过 Query Analysis、Evidence Grade 或 Generation 的自动降级链路。

绝不能：

```text
LLM异常
→ 无限重试
```

------

# 25. LLM Provider解耦

禁止代码：

```python
qwen_query_analysis()
qwen_grade()
qwen_generate()
```

推荐：

```text
backend/app/llm/
├── client.py
├── schemas.py
└── prompts.py
```

统一：

```text
LLMClient

analyze_query()
grade_evidence()
rewrite_query()
generate_answer()
```

当前底层：

```text
Qwen Provider
```

以后换：

```text
DeepSeek
Gemini
OpenAI
```

不会影响：

```text
BM25
Dense
RRF
Cross-Encoder
```

------

# 26. Evidence引用机制

这一点正式锁定：

> **不让 Qwen 自己生成 Source URL。**

首先给 Evidence 编号：

```text
[E1]
chunk_id=xxx
content=...

[E2]
chunk_id=yyy
content=...
```

要求 Qwen 只允许引用：

```text
[E1]
[E2]
```

例如：

```text
建议重新进行防泼水处理。[E1]
```

后端再执行：

```text
E1
↓
chunk_id
↓
Elasticsearch Metadata
↓
source_title
source_url
```

最终 API：

```json
{
  "answer": "...[E1]",
  "sources": [
    {
      "evidence_id": "E1",
      "chunk_id": "...",
      "title": "...",
      "url": "..."
    }
  ]
}
```

这样来源不会被 LLM 编造。

------

# 27. LangGraph

固定：

```text
LangGraph 1.2.11
```

LangGraph负责：

```text
State
Nodes
Conditional Edges
Rewrite Loop
```

其 Graph API 的核心概念就是 State、Nodes 和 Edges，Edge 可以是固定转移或条件分支。([Docs by LangChain](https://docs.langchain.com/oss/python/langgraph/graph-api?utm_source=chatgpt.com))

不负责：

```text
BM25实现
Dense实现
RRF计算
Cross-Encoder算法
```

因此代码关系：

```text
RetrieveNode
↓
HybridRetriever
↓
BM25 + Dense + RRF + Rerank
```

------

# 28. FastAPI

固定：

```text
FastAPI 0.141.1
```

负责：

```text
POST /api/chat
GET /api/health
GET /api/metrics
```

结构：

```text
FastAPI Route
↓
RAG Service
↓
LangGraph
```

Route不写核心 Retrieval 算法。

------

# 29. 前端

第一版采用：

```text
Node.js 24 LTS
Vue 3
Vite
Vue Router
原生fetch
```

Node 24 当前处于 LTS 支持线。([Node.js](https://nodejs.org/en/blog/migrations/v22-to-v24?utm_source=chatgpt.com))

第一版不需要：

```text
Pinia
Axios
Nuxt
大型UI组件库
```

核心页面：

```text
ChatView
MetricsView
```

ChatView：

```text
问题
回答
Sources
Evidence
简化RAG Trace
```

Trace 只包含 Query Analysis 结果、BM25 / Dense / RRF 候选数量、Top-K Evidence、是否 Rewrite 和基础耗时，不直接暴露完整 LangGraph State。

MetricsView：

```text
Recall@5
Claim Recall
Context Precision
Faithfulness
```

------

# 30. RAGChecker

RAGChecker不能简单理解成“输入答案自动算几个数学公式”。

其核心包含：

```text
Claim Extraction
+
Claim Checking
```

而这两个过程依赖 LLM。官方教程明确说明 RAGChecker 使用一个 LLM 抽取 Claim，再由 Checker LLM 对 Claim 与 GT/Evidence 进行验证，并支持 `custom_llm_api_func` 接入自定义模型。([GitHub](https://github.com/amazon-science/RAGChecker/blob/main/tutorial/ragchecker_tutorial_en.md))

因此必须增加配置：

```ini
RAGCHECKER_EXTRACTOR_MODEL=qwen3.7-plus-2026-05-26
RAGCHECKER_CHECKER_MODEL=qwen3.7-plus-2026-05-26
```

通过自定义 LLM 调用函数接入百炼。

------

# 31. RAGChecker Evaluator范围

P0 的 RAGChecker extractor 与 checker 均固定使用同一 Qwen Snapshot，并在结果中记录模型名。只产出 Claim Recall、Context Precision、Faithfulness，不开展多个 Evaluator 模型的对比实验。

------

# 32. 最终评测必须保存实验元数据

`results/final_metrics.json` 不能只有：

```json
{
  "recall_at_5": 0.9
}
```

建议保存：

```json
{
  "kb_version": "kb_v1",

  "embedding_model": "intfloat/multilingual-e5-small",
  "reranker_model": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",

  "generator_model": "qwen3.7-plus-2026-05-26",

  "ragchecker_extractor_model": "qwen3.7-plus-2026-05-26",
  "ragchecker_checker_model": "qwen3.7-plus-2026-05-26",

  "retrieval_config": {},

  "evaluation_samples": 0,

  "recall_at_5": null,
  "claim_recall": null,
  "context_precision": null,
  "faithfulness": null
}
```

这样以后简历结果能够追溯到实际系统版本。

------

# 33. 第一版完整配置Baseline

最终 `.env.example`：

```ini
# =====================================
# Elasticsearch
# =====================================

ES_URL=https://localhost:9200
ES_USERNAME=elastic
ES_PASSWORD=
ES_CA_CERT=

ES_INDEX_NAME=fashion_care_kb_v1

ES_NUMBER_OF_SHARDS=1
ES_NUMBER_OF_REPLICAS=0


# =====================================
# Chunking
# =====================================

MAX_CHUNK_TOKENS=320
MIN_CHUNK_TOKENS=60
FALLBACK_OVERLAP_TOKENS=40


# =====================================
# Embedding
# =====================================

EMBEDDING_MODEL=intfloat/multilingual-e5-small
EMBEDDING_DIM=384
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=16


# =====================================
# Retrieval
# =====================================

BM25_TOP_K=20

DENSE_TOP_K=20
DENSE_NUM_CANDIDATES=100

RRF_K=60
RRF_TOP_N=30

BM25_RRF_WEIGHT=1.0
DENSE_RRF_WEIGHT=1.0


# =====================================
# Reranker
# =====================================

RERANKER_MODEL=cross-encoder/mmarco-mMiniLMv2-L12-H384-v1

RERANKER_DEVICE=cpu
RERANKER_BATCH_SIZE=8

RERANK_TOP_K=5


# =====================================
# LangGraph
# =====================================

MAX_REWRITE_COUNT=1


# =====================================
# Qwen
# =====================================

LLM_PROVIDER=qwen

DASHSCOPE_API_KEY=
QWEN_BASE_URL=

QWEN_DEV_MODEL=qwen3.7-plus
QWEN_EVAL_MODEL=qwen3.7-plus-2026-05-26

LLM_ENABLE_THINKING=false

LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2


# =====================================
# RAGChecker
# =====================================

RAGCHECKER_EXTRACTOR_MODEL=qwen3.7-plus-2026-05-26
RAGCHECKER_CHECKER_MODEL=qwen3.7-plus-2026-05-26


# =====================================
# Web
# =====================================

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

FRONTEND_URL=http://localhost:5173

RAG_TRACE_ENABLED=true
```

所有 Key 只进入 `.env`。

`.env` 不进入 Git。

------

# 34. 最终运行链

现在第一版已经可以精确描述为：

```text
中文用户Query
       ↓
Vue3
       ↓
FastAPI
       ↓
RAG Service
       ↓
LangGraph
       ↓
Qwen3.7-Plus
Query Analysis
一次Structured Output
       │
       ├── structured_query
       └── lexical_terms_en
               ↓
      ┌────────┴─────────┐
      ↓                  ↓
    BM25           multilingual E5
英文术语检索           原始中文语义
   Top20              Top20
      └────────┬─────────┘
               ↓
            Python RRF
               ↓
             Top30
               ↓
      multilingual Cross-Encoder
               ↓
             Top-5
               ↓
        Evidence Grade
               ↓
       ┌───────┴────────┐
       ↓                ↓
   sufficient      insufficient
       ↓                ↓
   Generation      判断不足原因
       ↓          /           \
Qwen3.7-Plus   retrieval     missing
       ↓         problem    information
Answer+[E1]        ↓           ↓
       │         Rewrite     返回提示
       ↓           ↓
后端Evidence映射   Retrieve
       ↓
Source URL
       ↓
Vue
```

------

# 35. 在线与离线模型加载

在线系统启动：

```text
FastAPI Startup
       ↓
ES Client
Embedding Model
Cross-Encoder
       ↓
只初始化一次
       ↓
请求复用
```

Qwen：

```text
按请求调用API
```

离线评测：

```text
Golden Dataset
↓
Final RAG Pipeline
↓
Recall@5
+
RAGChecker
↓
final_metrics.json
```

两条链独立。

------

# 36. 已经正式确定的内容

这些现在可以锁死：

```text
Python 3.12

FastAPI
LangGraph

Elasticsearch

multilingual-e5-small
384 dims

mMARCO multilingual Cross-Encoder

BM25 + Dense
Python RRF
Cross-Encoder Rerank

Qwen3.7-Plus
百炼OpenAI-compatible API

Vue3 + Vite

Recall@5
RAGChecker
```

Qwen3.7-Plus 当前支持 Structured Output，且官方提供固定 `qwen3.7-plus-2026-05-26` Snapshot。([阿里云帮助中心](https://help.aliyun.com/en/model-studio/qwen-structured-output))

------

# 37. 只是Baseline的内容

下面不能说成“经过实验得到的最佳值”：

```text
Chunk 320

Overlap 40

BM25 Top20

Dense Top20

Dense candidates 100

RRF k=60

RRF Top30

Cross-Encoder Top5

Rewrite最多1次

BM25字段权重
```

后面可根据真实：

```text
Recall@5
Context Precision
Latency
```

调整。

------

# 38. 当前绝对不能写的结果

不能提前写：

```text
Recall@5 = 92%

Claim Recall = 89%

Faithfulness = 94%

平均响应时间 = 1.4s

RRF提升Recall 12%

Cross-Encoder提升15%
```

只有最终代码真实运行后才能产生。

------

