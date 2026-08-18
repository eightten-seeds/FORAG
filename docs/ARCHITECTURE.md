# 第3步：系统架构设计

## 1. 架构目标

本项目最终实现一个面向户外功能服装养护场景的 RAG Web 智能问答系统。

用户通过浏览器输入自然语言问题，系统从品牌官方护理资料构建的知识库中检索相关证据，对候选知识进行融合与重排序，在证据充分的情况下由大语言模型生成带来源的回答；如果当前检索表达不足，则通过 Query Rewrite 重新检索；如果用户本身缺少回答所必需的信息，则返回补充信息提示。

整个系统划分为三个业务模块：

1. **知识库构建模块**
2. **RAG检索与智能体模块**
3. **Web应用与量化评测模块**

------

# 2. 总体架构

```text
                     【离线知识库构建】

                 品牌官方护理资料
                         │
                         ▼
                       Loader
                         │
                         ▼
                       Cleaner
                         │
                         ▼
               Structure-aware Chunking
                         │
                         ▼
                 Metadata Enrichment
                         │
                         ▼
                      Embedding
                         │
                         ▼
                  Elasticsearch
                         ▲
                         │
══════════════════════════════════════════════════════
                         │
                     【在线问答】
                         │
                       用户
                         │
                         ▼
                   Vue3 + Vite
                         │
                    HTTP / JSON
                         │
                         ▼
                     FastAPI
                         │
                         ▼
                   RAG Service
                         │
                         ▼
                    LangGraph
                         │
                         ▼
                   Query Analysis
                         │
       一次 LLM 调用输出 structured_query
                  + lexical_terms_en
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
        Lexical Query         Semantic Query
              │                     │
              ▼                     ▼
             BM25                  Dense
              │                     │
              └──────────┬──────────┘
                         ▼
                        RRF
                         │
                         ▼
                   Cross-Encoder
                         │
                         ▼
                   Top-K Evidence
                         │
                         ▼
                   Evidence Grade
                  /                 \
               充分                 不充分
                │                     │
                ▼                     ▼
            Generation       判断不足原因
                │              /          \
                │      查询表达问题       信息缺失
                │           │               │
                │           ▼               ▼
                │     Query Rewrite    返回补充信息提示
                │           │               │
                │           ▼               ▼
                │       Retrieve            END
                │
                ▼
          Answer + Sources
                │
                ▼
             FastAPI
                │
                ▼
               Vue
```

同时存在独立的离线评测链路：

```text
Golden Dataset
      │
      ▼
完整 RAG Pipeline
      │
      ├── Recall@5
      │
      └── RAGChecker
              │
              ▼
      final_metrics.json
```

------

# 3. 模块一：知识库构建

知识库构建是**离线流程**，不是每次用户提问时重新执行。

完整数据流：

```text
Official Documents
        ↓
      Loader
        ↓
      Cleaner
        ↓
Structure-aware Splitter
        ↓
Metadata Enrichment
        ↓
     Embedding
        ↓
 Elasticsearch Index
```

## 3.1 Loader

负责读取整理后的官方护理资料，并转换为统一 Document 对象。

输入：

```text
data/raw/
```

逻辑输出：

```text
document_id
source_title
source_url
brand
raw_content
```

Loader 只负责“读取”，不负责 Chunk、Embedding 或检索。

------

## 3.2 Cleaner

负责去除与护理知识无关的内容，例如：

```text
网页导航
重复内容
Footer/Header
多余空白
无关营销文本
```

同时尽量保留：

```text
标题层级
护理步骤
适用条件
Warning
注意事项
来源信息
```

输出：

```text
CleanDocument
```

------

# 4. 结构感知递归切分

本项目不采用单纯固定字符数机械切分。

P0 优先按照真实可观察的显式结构：

```text
文档
 ↓
Heading / Section
 ↓
Paragraph / List / Warning
 ↓
multilingual-e5-small tokenizer 长度兜底
```

核心目标是尽量避免把：

```text
适用条件
+
护理操作
+
注意事项
```

拆散。

第一版仅通过显式结构和简单规则尽量保持护理步骤、Warning、Condition + Action 完整；不实现复杂 NLP 条件句识别器或语义 Chunking 模型。

最终每个 Chunk 应具有稳定 `chunk_id`，并能够回溯原始文档。

------

# 5. Metadata设计

每个知识 Chunk 至少保存：

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
content
```

根据实际官方资料增加：

```text
brand
garment_type
technology
care_stage
```

例如：

```json
{
  "brand": "Arc'teryx",
  "garment_type": "hardshell",
  "technology": "GORE-TEX",
  "care_stage": "restore_dwr"
}
```

原则：

> 文档中有依据才能写，没有依据允许为空，不进行人为补全。

------

# 6. Embedding

Chunk 内容经过 Embedding Model 转换为向量：

```text
Chunk Content
     ↓
Embedding Model
     ↓
Dense Vector
```

在线检索时 Query 也必须使用与文档兼容的 Embedding Model。

具体：

```text
Embedding模型名称
向量维度
是否采用多语言模型
```

暂时不在架构阶段写死，在后续技术选型阶段确定。

由于本项目存在：

```text
中文用户问题
↕
英文官方护理文档
```

因此后续 Embedding 选型必须考虑中英文跨语言语义匹配能力。

------

# 7. Elasticsearch职责

Elasticsearch 中一个 Document 对应一个 Chunk。

主要保存：

```text
Content
Metadata
Embedding
```

Elasticsearch 在整个架构中负责：

```text
知识存储
BM25检索
Dense Vector检索
Metadata Boost
```

Elasticsearch 不负责：

```text
RRF
Cross-Encoder
LangGraph工作流
Answer Generation
```

这些属于上层应用逻辑。

------

# 8. Query Analysis

用户 Query 首先进入 Query Analysis。

例如：

```text
Arc'teryx 的 GORE-TEX 冲锋衣现在不挂水珠了怎么办？
```

可能分析为：

```json
{
  "brand": "Arc'teryx",
  "garment_type": "hardshell",
  "technology": "GORE-TEX",
  "issue_type": "water_repellency_loss",
  "intent": "care_troubleshooting"
}
```

P0 只进行一次 Qwen structured-output 调用，同时得到：

```text
structured_query
+
lexical_terms_en
```

Query Analysis 主要负责：

```text
识别用户明确提供的信息
+
识别问题类型
+
保存关键实体
+
辅助后续查询构造
+
辅助Metadata检索
```

它不负责最终回答。

用户没有提供的信息不能随意补充。

------

# 9. Query Analysis的检索产物

P0 不设置独立的 Retrieval Query Formulation Node，也不为查询构造再次调用 LLM。

原因是本项目可能出现：

```text
用户：
“冲锋衣现在不挂水珠了”

官方文档：
DWR / water repellency / wetting-out
```

如果直接把用户中文原句交给 BM25，专业英文术语可能无法匹配。

Query Analysis 的同一次结构化输出根据：

```text
original_query
+
structured_query
```

生成不同检索路径需要的 Query。

逻辑形式：

```text
original_query
      ↓
Query Analysis（一次 LLM 调用）
      ↓
┌───────────────────────────┐
│                           │
Lexical Query          Semantic Query
│                           │
BM25                      Dense
```

例如：

```text
Original Query：

“我的GORE-TEX冲锋衣现在不挂水珠了怎么办？”
```

结构化信息：

```text
technology = GORE-TEX
issue_type = water_repellency_loss
```

Lexical Query 可以包含：

```text
GORE-TEX
DWR
water repellency
wetting-out
```

Semantic Query 则保留原始自然语言语义：

```text
我的GORE-TEX冲锋衣现在不挂水珠了怎么办？
```

这样形成：

> **BM25负责专业术语和精确实体匹配，Dense负责原始语义匹配。**

专业词映射只使用少量核心术语表与受约束的结构化输出，不建设大型领域 Ontology。

------

# 10. BM25检索

BM25 在 Elasticsearch 中执行。

擅长处理：

```text
GORE-TEX
DWR
ePE
Arc'teryx
材料名称
技术名称
产品型号
```

流程：

```text
Lexical Query
      ↓
Elasticsearch BM25
      ↓
BM25 Top-N
```

返回：

```text
chunk_id
content
metadata
bm25_rank
bm25_score
```

BM25 主要解决：

> **关键词和专业实体的精确匹配问题。**

------

# 11. Dense Vector检索

Dense Retrieval 流程：

```text
Semantic Query
      ↓
Query Embedding
      ↓
Elasticsearch Vector Search
      ↓
Dense Top-N
```

主要解决：

> 用户表达与文档表述不同但语义相近的问题。

例如：

```text
“不挂水珠”
```

可能与：

```text
water repellency loss
DWR
wetting-out
```

具有较高语义相关性。

因此 BM25 和 Dense 不是替代关系，而是互补关系。

------

# 12. Metadata Boost

Query Analysis 得到的可靠实体可以辅助 ES 检索。

例如用户明确说：

```text
technology = GORE-TEX
brand = Arc'teryx
```

P0 仅作为简单 Boost 使用，不设计 Hard Filter / Boost 切换和复杂调参体系，以避免不完整 Metadata 直接排除正确 Chunk。

------

# 13. RRF排名融合

BM25 与 Dense 分别产生自己的候选排序。

两者原始 Score 来源于不同评分机制，数值尺度和分布不同。

并不是说“两种分数绝对不能融合”。

理论上可以使用：

```text
Score Normalization
+
Weighted Fusion
```

但是会额外引入：

```text
归一化策略
融合权重
参数调优
```

因此本项目选择：

**Reciprocal Rank Fusion（RRF）**

基于两路结果中的排名进行融合。

流程：

```text
BM25 Ranking ──────┐
                   ├── RRF
Dense Ranking ─────┘
                       ↓
                Unified Candidates
```

因此选择 RRF 的理由是：

> **降低 BM25 与 Dense 原始分数尺度差异带来的融合复杂度，并避免额外设计大量融合权重。**

RRF 是本项目的工程选择，不是唯一可行的融合算法。

RRF 在：

```text
retrieval/
```

中实现。

不是 LangGraph Node 内部重新实现。

------

# 14. Cross-Encoder重排序

RRF 主要完成候选融合，但最终排序仍可以进一步优化。

Cross-Encoder 对：

```text
Query + Candidate Chunk
```

进行联合编码和相关性评分。

流程：

```text
RRF Candidates
      ↓
(Query, Chunk)
      ↓
Cross-Encoder
      ↓
rerank_score
      ↓
重新排序
      ↓
Top-K Evidence
```

Cross-Encoder 不对整个知识库逐条计算。

因此整个检索系统采用：

```text
第一阶段：
BM25 + Dense
→ 快速召回候选

第二阶段：
RRF
→ 合并候选排序

第三阶段：
Cross-Encoder
→ 精排候选
```

最终得到：

```text
Top-K Evidence
```

具体：

```text
BM25 Top-N
Dense Top-N
RRF Candidate Size
最终Top-K
```

不在架构阶段硬编码，由后续实验确定。

------

# 15. Hybrid Retriever

Retrieval Layer 对 LangGraph 提供统一能力。

例如：

```python
HybridRetriever.retrieve(
    original_query,
    bm25_query_text=None,
    brand=None,
    technologies=(),
)
```

首次检索由 Query Analysis upstream adapter 将 `lexical_terms_en` 清洗并以单个空格连接为 `bm25_query_text`；`structured_query.brand` 映射为 `brand`，`structured_query.technology` 映射为 `technologies`。语义检索与 Cross-Encoder 使用 `original_query`。`structured_query` 不整体传入 Retriever；`garment_type`、`issue_type`、`intent`、`care_stage` 保留在 Agent State。

唯一一次 Rewrite 后，Agent State 的 `original_query` 仍表示用户最初输入；`reformulated_query` 是当前检索语义。第二次调用等价于：

```python
HybridRetriever.retrieve(
    original_query=reformulated_query,
    bm25_query_text=reformulated_query,
    brand=stored_brand,
    technologies=stored_technologies,
)
```

Rewrite 后不得再次运行 Query Analysis，必须复用首次分析得到的 `brand` 与 `technologies`。最多一次 Rewrite；第二次 Evidence 判断后无论充分与否均不再 Rewrite。Stage 9 负责该 State、节点与条件路由；Stage 10 才负责 Answer/Citation Generation。

Stage 10 extends only the downstream terminal paths: `ready_for_generation` runs grounded Answer Generation and deterministic citation validation; `insufficient_evidence` creates a deterministic terminal response. Evidence Judge receives only `original_query + current Top-K Evidence`; it does not receive the whole structured query. Citation source metadata is mapped directly from the current `RetrievalCandidate` snapshot, never by a second Elasticsearch lookup.

内部执行：

```text
BM25 ──┐
       ├→ RRF → Cross-Encoder → Top-K Evidence
Dense ─┘
```

因此架构职责明确：

```text
Retrieval Layer
负责：
检索算法怎么执行

LangGraph
负责：
什么时候调用Retrieval
```

LangGraph 不需要知道 RRF 的内部计算逻辑。

------

# 16. LangGraph职责

LangGraph 是整个 RAG 的**流程编排层**。

它不负责实现：

```text
BM25
Dense
RRF
Cross-Encoder
```

它负责：

```text
保存State
执行Node
控制条件分支
控制Query Rewrite回路
决定何时生成回答
```

第一版工作流：

```text
START
  ↓
Query Analysis
  ↓
Retrieve
  ↓
Evidence Grade
  ↓
┌──────────────────────────────────┐
│                                  │
证据充分                         证据不足
│                                  │
▼                                  ▼
Generate                     判断不足原因
│                            /          \
│                    查询表达问题       关键信息缺失
│                         │                │
│                         ▼                ▼
│                    Query Rewrite    返回信息不足
│                         │                │
│                         ▼                ▼
│                      Retrieve           END
│
▼
END
```

------

# 17. Evidence Grade

Evidence Grade 判断：

> 当前 Top-K Evidence 是否足够支持回答用户原始问题。

输入：

```text
original_query
structured_query
Top-K Evidence
```

输出至少包含：

```text
evidence_sufficient
```

如果证据不足，还需要区分：

```text
retrieval_problem
```

还是：

```text
missing_information
```

P0 直接使用 Qwen structured output 完成该判断，不增加 Cross-Encoder 阈值、规则与 LLM 的组合评分系统。

不能在还没有数据的情况下凭空写：

```text
score > 0.7 就充分
```

------

# 18. Query Rewrite

Query Rewrite 解决的是：

> **用户原问题信息基本足够，但是当前表达方式不利于检索。**

例如：

```text
冲锋衣现在完全不挂水了
```

可以调整为更适合检索的表达：

```text
DWR water repellency wetting-out restoration
```

但必须保存：

```text
original_query
```

Rewrite 产生：

```text
reformulated_query
```

不能覆盖原始 Query。

同时必须保留用户明确提供的：

```text
品牌
材料
技术名称
型号
关键现象
```

------

# 19. Query Rewrite不能创造信息

例如用户问：

```text
这件衣服能不能烘干？
```

如果系统不知道：

```text
材料
品牌
护理标签
```

Query Rewrite 不能擅自把它改成：

```text
GORE-TEX衣服如何烘干？
```

因为用户没有说它是 GORE-TEX。

因此：

```text
缺少必要事实
≠
查询表达不好
```

前者：

```text
返回信息不足提示
```

后者：

```text
Query Rewrite
```

------

# 20. 第一版不做真正跨轮Clarification

第一版如果遇到必要信息缺失，例如：

```text
“这件衣服能烘干吗？”
```

返回：

```text
当前信息不足，请补充服装品牌、材料或护理标签信息。
```

随后：

```text
END
```

第一版不实现：

```text
系统提问
↓
等待用户下一轮回答
↓
恢复之前LangGraph State
↓
继续执行
```

因为这需要额外实现：

```text
session_id
thread_id
checkpointer
conversation persistence
```

这些不是本项目第一版的核心价值。

后续如有需要，再扩展真正多轮会话。

------

# 21. Rewrite循环终止

State 中必须存在：

```text
rewrite_count
```

以及：

```text
MAX_REWRITE_COUNT
```

P0 固定：

```text
MAX_REWRITE_COUNT=1
```

流程：

```text
Rewrite
↓
Retrieve
↓
Evidence Grade
↓
仍不足
```

一次 Rewrite 后若证据仍不足则终止：

```text
基于现有证据谨慎回答
```

或：

```text
返回证据不足
```

禁止无限循环。

------

# 22. LangGraph State

第一版建议 State 包含：

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

API Trace 只投影必要信息，不直接暴露该完整 State。

实际 Query 选择需要避免空字符串问题。

例如：

```python
query = reformulated_query or original_query
```

`original_query` 始终保留。

------

# 23. Generation Layer

Generation 输入：

```text
Original Query
+
Top-K Evidence
```

然后：

```text
Prompt
↓
LLM
↓
Answer
```

生成模型只负责：

> **根据已经检索出的 Evidence 组织自然语言答案。**

它不负责重新搜索 Elasticsearch。

Prompt 应要求：

```text
尽量依据Evidence
区分品牌和材料条件
证据不足时明确说明
不进行专业损伤诊断
```

P0 通过 Qwen API 调用 LLM。

第一版不要求本地部署大型 LLM。

------

# 24. Evidence与Source溯源

Evidence 必须来自 Elasticsearch 中真实存在的 Chunk。

完整来源链：

```text
Official Document
      ↓
Chunk
      ↓
Metadata
      ↓
Elasticsearch
      ↓
Retrieval
      ↓
Top-K Evidence
```

每个 Evidence 至少保存：

```text
chunk_id
parent_doc_id
source_title
source_url
content
```

因此最终 Source URL 来自：

> 原始官方文档 Metadata。

不是由 LLM 临时生成。

------

# 25. RAG Service

在 FastAPI 与 LangGraph 之间增加：

```text
RAG Service
```

调用关系：

```text
FastAPI Route
      ↓
RAG Service
      ↓
LangGraph Workflow
```

RAG Service 负责：

```text
调用Workflow
组织输入
转换输出
处理业务异常
```

这样 FastAPI 不直接依赖 LangGraph 内部 Node。

------

# 26. FastAPI

FastAPI 属于 Web 服务层。

负责：

```text
HTTP请求
参数验证
RAG Service调用
Response格式化
异常处理
```

不负责：

```text
BM25
Dense
RRF
Cross-Encoder
```

第一版至少提供：

```text
POST /api/chat

GET /api/health

GET /api/metrics
```

------

# 27. /api/chat

输入：

```json
{
  "question": "GORE-TEX冲锋衣现在不挂水珠了怎么办？"
}
```

正常输出：

```json
{
  "answer": "...",
  "sources": [],
  "retrieved_chunks": [],
  "trace": {}
}
```

信息不足时：

```json
{
  "answer": null,
  "needs_more_information": true,
  "message": "请补充服装品牌、材料或护理标签信息。",
  "sources": [],
  "retrieved_chunks": []
}
```

------

# 28. Vue3 + Vite前端

第一版主要包含两个页面。

### ChatView

负责：

```text
用户问题输入
回答展示
来源展示
Evidence展示
Loading
错误提示
```

可选展示：

```text
Query Analysis
BM25 / Dense / RRF候选数量
Top-K Evidence
是否Rewrite
基础耗时
```

这些 Trace 信息主要用于项目演示与调试。

### MetricsView

展示：

```text
Recall@5
Claim Recall
Context Precision
Faithfulness
```

通过：

```text
GET /api/metrics
```

读取后端结果。

不得写死。

------

# 29. 离线评测架构

评测与在线 Chat 完全分离。

```text
Golden Dataset
      ↓
Evaluation Runner
      ↓
完整RAG
      ↓
┌──────────────────┐
│                  │
Recall@5       RAGChecker
│                  │
└────────┬─────────┘
         ↓
results/final_metrics.json
```

其中：

```text
Recall@5
```

主要评价 Retrieval。

RAGChecker 重点记录：

```text
Claim Recall
Context Precision
Faithfulness
```

最终项目中的量化数据只能来自实际评测文件。

------

# 30. 系统三条独立执行链

整个工程必须明确区分：

```text
A. 知识库构建

Official Documents
→ Clean
→ Chunk
→ Metadata
→ Embedding
→ Elasticsearch
B. 在线问答

Vue
→ FastAPI
→ RAG Service
→ LangGraph
→ Retrieval
→ Generation
→ Answer
C. 离线评测

Golden Dataset
→ RAG Pipeline
→ Evaluation
→ final_metrics.json
```

三条链不能混在一起。

------

# 31. 工程职责映射

最终代码结构建议为：

```text
fashion-care-rag/
│
├── backend/
│   └── app/
│       │
│       ├── knowledge/
│       │   ├── loader.py
│       │   ├── cleaner.py
│       │   ├── splitter.py
│       │   ├── metadata.py
│       │   ├── embedding.py
│       │   └── indexer.py
│       │
│       ├── retrieval/
│       │   ├── query_formulation.py
│       │   ├── bm25.py
│       │   ├── dense.py
│       │   ├── rrf.py
│       │   ├── reranker.py
│       │   └── hybrid.py
│       │
│       ├── agent/
│       │   ├── state.py
│       │   ├── nodes.py
│       │   ├── routes.py
│       │   └── workflow.py
│       │
│       ├── generation/
│       │   ├── prompt.py
│       │   └── generator.py
│       │
│       ├── services/
│       │   └── rag_service.py
│       │
│       ├── api/
│       │   ├── chat.py
│       │   ├── health.py
│       │   └── metrics.py
│       │
│       ├── schemas/
│       │
│       ├── config.py
│       └── main.py
│
├── frontend/
│
├── evaluation/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── evaluation/
│
├── scripts/
│
├── results/
│
├── tests/
│
└── docs/
```

------

# 32. 各层最终职责

这一部分你必须记住：

```text
Knowledge
→ 把官方文档加工成可检索知识

Elasticsearch
→ 存储Chunk并执行BM25 / Dense基础检索

Query Analysis
→ 一次调用同时产生structured_query与lexical_terms_en

Retrieval
→ BM25 + Dense → RRF → Cross-Encoder

LangGraph
→ 控制Query Analysis、Retrieve、Evidence Grade、
  Rewrite和Generate之间的执行流程

Generation
→ 根据Evidence生成回答

FastAPI
→ 对外提供Web接口

Vue
→ 用户交互与展示

Evaluation
→ 独立量化最终系统效果
```

------

# 33. 本阶段故意不确定的内容

第三步只确定架构，不提前拍脑袋决定以下参数：

```text
Embedding具体模型
Cross-Encoder具体模型
ES中文/英文Analyzer
Embedding维度
BM25 Top-N
Dense Top-N
RRF k
Rerank Top-K
Metadata Boost权重
Evidence Grade具体算法
Evidence Grade具体阈值
Golden Dataset规模
```

这些将在：

> 数据设计 → 技术选型 → 检索设计 → 实验评测

阶段逐步确定。

这样可以避免出现“架构文档写了一个参数，实际代码根本不适合”的问题。

------
