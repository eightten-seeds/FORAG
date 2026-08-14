# 户外功能服装智能养护 RAG 问答系统
# DATA_DESIGN.md
# 数据与知识库设计

## 1. 文档目标

本文档定义户外功能服装智能养护 RAG 系统的数据来源、数据模型、文档清洗、Chunking、Metadata、术语规范化、Embedding 数据构造、Elasticsearch 索引数据结构、数据质量控制、知识库版本管理以及评测数据关系。

本阶段解决的核心问题是：

> RAG 系统到底检索什么，以及如何把品牌官方护理资料加工成结构清晰、来源可追踪、适合 BM25 与 Dense Vector 检索的知识库。

知识库完整构建链路为：

Official Care Documents
        ↓
Source Manifest
        ↓
RawDocument
        ↓
Cleaner
        ↓
CleanDocument
        ↓
Structure-aware Recursive Chunking
        ↓
Core Metadata
        ↓
Terminology Normalization
        ↓
Embedding Text Construction
        ↓
Embedding
        ↓
Elasticsearch Index

最终 Elasticsearch 中的基本检索单位为：

Chunk

而不是整篇网页或单独一句话。

---

# 2. 数据范围

第一版知识库仅覆盖与“户外功能服装养护”直接相关的官方知识。

主要包括：

- 清洗 Washing
- 漂洗 Rinsing
- 烘干 / 干燥 Drying
- DWR / 防泼水性能恢复
- Water Repellency
- Wetting-out
- GORE-TEX 等功能材料护理
- 羽绒服护理
- 羽绒结团
- Loft 恢复
- 合成保温服装护理
- Softshell 护理
- Fleece 护理
- 储存 Storage
- 基础 Repair / Maintenance
- 基于官方资料的简单性能问题排查

第一版明确不纳入：

- 穿搭推荐
- 尺码推荐
- 商品推荐
- 价格信息
- 电商评论
- 论坛经验
- 普通博客经验
- 医学建议
- 未验证的第三方护理教程
- 专业服装物理损伤鉴定

这样保证知识库范围与项目核心问题一致。

---

# 3. 数据来源原则

知识库优先使用品牌和技术厂商公开的官方护理资料，例如：

- 官方 Product Care
- 官方 Care Guide
- 官方 FAQ
- 官方 Troubleshooting
- 官方 Material Care Guide
- 官方 Technology Care Guide
- 官方产品护理说明

每份资料必须能够关联：

- source_id
- source_title
- source_url
- source_type
- brand
- language
- accessed_at

最终系统展示的 Source URL 必须继承自这里，而不能由 LLM 自动生成。

---

# 4. 数据采集策略

第一版不构建全站自动爬虫。

采用：

人工确定官方资料页面
        ↓
登记 Source Manifest
        ↓
保存原始页面 / 正文快照
        ↓
进入统一数据处理流水线

原因：

1. 全站网页包含大量商品营销和导航噪声；
2. 不同品牌网站结构差异较大；
3. 自动爬虫维护成本高；
4. 容易使项目重点从 RAG 转移到 Web Crawler；
5. 官方页面可能发生变化；
6. 需要控制数据来源及版权风险。

第一版目标是构建：

> 小规模、来源明确、内容高质量的专业护理知识库。

---

# 5. 数据目录

推荐目录：

data/
├── raw/
│   ├── arcteryx/
│   ├── goretex/
│   ├── patagonia/
│   ├── thenorthface/
│   └── ...
│
├── interim/
│
├── processed/
│   └── chunks.jsonl
│
├── dictionaries/
│   └── terminology.json
│
├── manifests/
│   └── sources.jsonl
│
└── evaluation/

各目录职责：

raw/
保存原始官方资料或本地正文快照。

interim/
保存清洗后的中间 Document，便于调试文档处理流程。

processed/
保存最终进入 Elasticsearch 前的标准 Chunk。

dictionaries/
保存受控领域术语表。

manifests/
保存所有知识来源的登记信息。

evaluation/
保存后续 Golden Dataset，与知识库数据严格分离。

---

# 6. Source Manifest

所有资料在进入知识库之前必须登记来源。

文件：

data/manifests/sources.jsonl

逻辑 Schema：

{
  "source_id": "src_xxx",
  "brand": "arcteryx",
  "source_type": "product_care",
  "source_title": "Product Care Guide",
  "source_url": "https://...",
  "language": "en",
  "accessed_at": "YYYY-MM-DD",
  "local_path": "data/raw/...",
  "content_hash": "...",
  "enabled": true
}

其中：

source_id
是知识来源的稳定 ID。

source_url
是原始官方来源。

accessed_at
表示本项目获取该内容的时间。

content_hash
用于检测原始资料内容是否发生变化。

enabled
用于决定当前知识库版本是否使用该来源。

---

# 7. 知识库版本管理

官方网页可能后续发生更新，因此知识库必须增加：

kb_version

例如：

kb_v1
kb_v2

知识库每次发生以下变化时，应考虑创建新版本：

- 修改主要数据源；
- 大规模更新官方资料；
- 修改 Chunking 策略导致 Chunk 结构发生明显变化；
- 修改关键 Metadata 生成逻辑。

评测数据同样需要记录：

kb_version

这样才能保证：

Golden Dataset
与
当前被评测的 Knowledge Base

属于同一版本。

---

# 8. RawDocument 模型

Loader 将不同来源资料统一转换为：

RawDocument

逻辑 Schema：

RawDocument:
    document_id
    source_id
    brand
    source_type
    source_title
    source_url
    language
    accessed_at
    raw_content
    content_hash

document_id 应保持稳定。

它表示：

> 一份逻辑上的官方文档。

document_id 不应依赖正文每一个字符，否则文档修改一个标点就会完全变成另一份文档。

---

# 9. 原始资料处理原则

后续 Cleaner、Splitter 和 RAG Pipeline 均尽量基于本地保存的资料运行，而不是用户每次提问时实时访问官方网页。

流程：

Official Website / Document
        ↓
Raw Snapshot
        ↓
RawDocument
        ↓
Knowledge Pipeline

这样可以保证：

- 开发结果可复现；
- 官方网页临时无法访问时系统仍然可以运行；
- 数据版本明确；
- Golden Dataset 可以绑定稳定知识库；
- 后续 ES 重建无需重复抓取网页。

---

# 10. Cleaner

Cleaner 负责去除与护理知识无关的内容。

需要处理：

- Header
- Footer
- Cookie Notice
- 网站导航
- 重复菜单
- 无意义空白
- HTML 残留
- 重复段落
- 与养护无关的营销内容

必须尽量保留：

- 文档标题
- Section Heading
- Paragraph
- Numbered List
- Bullet List
- Table 信息
- 护理操作
- 条件说明
- Warning
- Note
- 技术名称
- 材料名称
- 温度 / 操作限制
- 来源信息

Cleaner 的目标不是总结文档。

禁止：

原始资料
→ LLM总结
→ 只保存总结

因为这样会提前引入信息损失和潜在幻觉。

---

# 11. CleanDocument

Cleaner 输出：

CleanDocument:
    document_id
    source_id
    source_title
    source_url
    brand
    language
    sections
    clean_content
    content_hash

其中 `sections` 尽量保留文档的显式结构。

例如：

Product Care
├── Washing
├── Drying
└── Restoring DWR

后续 Splitter 应优先利用这些显式结构。

---

# 12. Chunking总体原则

本项目不采用：

固定 500 字符
→ 机械切割

作为主要 Chunking 方法。

因为护理资料经常包含：

Condition
+
Action
+
Warning

如果被切断，会降低 Retrieval 与 Generation 的可靠性。

因此采用：

> 面向护理条件和操作流程的结构感知递归切分策略。

但“结构感知”不意味着系统能够理解所有文档语义结构。

P0 实际实现采用：

显式文档结构
        ↓
简单完整性规则
        ↓
长度约束兜底

---

# 13. 第一层：显式结构切分

优先识别真实可观察的文档结构：

- Heading
- Subheading
- Paragraph
- Numbered List
- Bullet List
- Table Block
- Warning / Note Block

例如：

Washing
├── paragraph
├── steps list
└── warning

如果完整结构块长度满足限制，则尽量作为一个语义单元保留。

---

# 14. 第二层：简单完整性规则

在显式结构基础上，仅用简单规则尽量保持以下内容完整：

- 连续护理步骤；
- Warning / Note 与所属操作；
- Condition + Action。

P0 不实现复杂 NLP 条件句识别器，也不引入语义 Chunking 模型。

---

# 15. 第三层：递归长度兜底

当一个结构单元仍然超过模型允许长度时：

Section
→ Paragraph
→ Sentence
→ Token Length Fallback

逐层递归。

因此整体优先级可以表示为：

Document
   ↓
Heading / Section
   ↓
Paragraph / List / Table Block
   ↓
Sentence
   ↓
Length Fallback

核心原则：

> 结构优先，长度限制兜底。

---

# 16. Chunk语义完整性要求

Splitter 尽量保持以下关系：

条件 + 操作

问题现象 + 处理方法

步骤序列

操作 + Warning

材料适用范围 + 护理方式

例如：

If water no longer beads on the surface,
restore the water repellent treatment...

应尽量放在同一个 Chunk。

避免：

Chunk A:
If water no longer beads...

Chunk B:
restore the treatment...

---

# 17. 列表处理

护理文档常见：

1. Close all zippers.
2. Wash the garment.
3. Rinse thoroughly.
4. Dry according to instructions.

如果整体长度允许：

> 一组连续步骤应作为一个语义块保存。

不能默认：

一个 list item = 一个 Chunk

否则可能只召回步骤 3，而失去前置步骤。

---

# 18. Warning与Note

Warning / Note 必须保留其所属 Section。

例如：

Washing
...
Warning: Do not use fabric softener.

至少需要通过：

section_title

明确：

该 Warning 属于 Washing。

避免 Warning 在检索中脱离原本护理情境。

---

# 19. Chunk长度配置

架构阶段不硬编码：

chunk_size = 500

而是提供配置：

MAX_CHUNK_TOKENS
MIN_CHUNK_TOKENS
FALLBACK_OVERLAP_TOKENS

具体参数后续根据：

- 文档长度统计
- Embedding 模型限制
- Retrieval Recall
- Context Precision
- 本机资源

共同确定。

Overlap 只主要用于长度兜底切分。

不应为了“多召回”在所有 Chunk 间加入大量重复文本。

---

# 20. Chunk ID与Content Hash

`chunk_id` 和 `content_hash` 必须分离。

chunk_id 表示：

> Chunk 的逻辑身份。

content_hash 表示：

> Chunk 内容当前版本。

推荐逻辑：

chunk_id
=
document_id
+
section_title
+
chunk_order

例如：

arcteryx-care-001/drying/003

另外：

content_hash = hash(content)

这样：

正文轻微发生变化
→ content_hash 变化

但逻辑位置没有变化时：
→ chunk_id 可以保持相对稳定

避免因为一个标点变化导致 Golden Dataset 所有 Chunk ID 全部失效。

---

# 21. Chunk Schema

最终 Chunk 的逻辑结构：

{
  "chunk_id": "...",
  "parent_doc_id": "...",
  "source_id": "...",

  "chunk_order": 0,
  "section_title": "Drying",

  "content": "...",

  "brand": "arcteryx",
  "garment_type": [],
  "technology": [],
  "care_stage": [],

  "normalized_terms": [],

  "source_title": "...",
  "source_url": "...",
  "language": "en",

  "content_hash": "...",
  "kb_version": "kb_v1",

  "embedding_text": "...",
  "embedding": []
}

P0 重点保证准确的 Metadata：

- brand
- technology
- garment_type
- care_stage

其余字段仅保留 Chunk 身份、来源、版本、检索正文和向量所必需的内容，不扩展领域 Metadata 集合。

---

# 22. Content是唯一主要Evidence正文

`content` 保存：

> 清洗后的官方护理正文。

它用于：

- Evidence 展示；
- LLM Context；
- Source Citation；
- 人工检查。

不得将系统自己构造的检索增强词直接混入 `content`。

否则无法区分：

> 哪些信息来自官方资料，哪些信息来自系统。

---

# 23. 不使用统一search_text作为核心字段

第一版不把：

Brand
+
Title
+
Section
+
Terms
+
Content

全部拼成一个巨大的：

search_text

作为 BM25 唯一字段。

原因：

- 不利于字段权重设计；
- 不利于解释命中来源；
- 字段长度会影响 BM25；
- 品牌与正文语义职责不同；
- 后续难以独立调整各字段。

因此使用：

> Elasticsearch Multi-field Retrieval。

---

# 24. BM25多字段检索设计

BM25 可以同时检索：

- content
- source_title
- section_title
- brand
- technology
- normalized_terms

逻辑上：

Query
 ↓
Elasticsearch Multi-field BM25
 ↓
Weighted Matching
 ↓
Top-N

不同字段后续可以设置不同 Boost。

例如：

technology
可能比普通正文中的一次偶然词命中更重要。

但具体权重：

content^?
title^?
technology^?

不在数据设计阶段写死。

通过后续检索实验确定。

---

# 25. normalized_terms

`normalized_terms` 是：

> 本项目维护的受控检索增强术语。

它不属于官方正文。

例如：

{
  "water_repellency_loss": {
    "zh": [
      "不挂水",
      "不挂水珠",
      "防泼水下降"
    ],
    "en": [
      "DWR",
      "water repellency",
      "water beading",
      "wetting-out"
    ]
  }
}

这些词可以用于：

- Query Analysis；
- Query Analysis 同次输出的 `lexical_terms_en`；
- BM25 检索增强；
- Metadata Normalization。

但是：

Generation Context
主要使用 `content`。

不能把 normalized_terms 当成官方 Evidence。

---

# 26. 术语表

文件：

data/dictionaries/terminology.json

术语表主要解决：

> 中文用户表达与英文专业护理术语之间的词汇差异。

例如：

“不挂水珠”
→ water repellency
→ DWR

“湿透表布”
→ wetting-out

“羽绒一坨一坨”
→ down clumping
→ restore loft

这是领域受控词典。

第一版只维护少量高频核心护理概念，不建设大型服装领域 Ontology。

第一版不允许让 LLM 每次动态随机生成大量同义词然后永久写入知识库。

---

# 27. Embedding Text

Dense Retrieval 使用的向量来自：

embedding_text

建议组合：

Document / Section Context
+
Content

例如：

Title: GORE-TEX Product Care
Section: Restoring Water Repellency

[Official Content]

也就是说：

embedding_text
≈
title + section_title + content

而不是：

content
+
大量人工关键词
+
大量中英文同义词

跨语言匹配主要交给后续选择的：

> 多语言 Embedding Model。

人工术语主要增强 Lexical Retrieval。

---

# 28. 为什么content和embedding_text分开

例如一个 Chunk 正文可能是：

Wash on a warm permanent press cycle...

如果直接只 Embedding 裸正文，模型可能不知道：

> 这是 GORE-TEX 产品的 Washing Instructions。

因此把：

Title
Section Context

一起加入 embedding_text。

但最终 Evidence 展示仍然使用：

content

保证回答引用的是官方正文，而不是人为拼接后的检索文本。

---

# 29. 中英文跨语言检索设计

系统存在：

中文用户 Query
↕
英文官方护理文档

因此采用双路径：

Lexical：
Query Analysis
+
Terminology Mapping
+
lexical_terms_en
+
BM25

Semantic：
Original / Semantic Query
+
Multilingual Embedding
+
Dense Retrieval

例如：

用户：

“冲锋衣现在不挂水珠了”

Lexical Query 可以扩展：

DWR
water repellency
water beading
wetting-out

Dense Query 则尽量保留原始自然语言语义。

因此准确表述是：

> BM25 负责专业术语与实体的精确匹配，Dense Retrieval 负责口语表达、语义近似以及跨语言语义召回。

不是：

> BM25 本身能够理解中英文同义语义。

---

# 30. Metadata设计

第一版主要 Metadata：

brand
garment_type
technology
care_stage

P0 不增加其他领域 Metadata。

例如：

brand:
arcteryx

garment_type:
hardshell

technology:
GORE-TEX

care_stage:
restore_dwr

Metadata 不是越多越好。

核心原则：

> 只有后续检索真正需要、且能够可靠获得的字段才值得维护。

---

# 31. Metadata赋值原则

Metadata 仅从 Source Manifest、文档显式内容或简单确定性规则获得；缺失时保持为空，不伪造。

P0 不记录 `source_explicit`、`rule_derived`、`manual_verified` 等字段级 Metadata Provenance，也不建设完整追踪体系。

---

# 32. Metadata Boost原则

例如：

用户明确提供：

brand = Arc'teryx

P0 只作为简单 Boost 使用，不设计 Hard Filter / Boost 切换体系。Boost 的 Baseline 在技术基线中统一给出，后续只允许基于 dev 集做有限调整。

---

# 33. Elasticsearch数据字段

ES Document 逻辑分为四类字段。

### A. 全文检索字段

content
source_title
section_title

用于：

BM25

---

### B. Metadata / Term字段

brand
garment_type
technology
care_stage
normalized_terms
language

用于：

BM25 Field Matching
Boost

---

### C. 溯源字段

chunk_id
parent_doc_id
source_id
source_title
source_url
section_title
content_hash
kb_version

用于：

Source Citation
Debug
Evaluation
Version Tracking

---

### D. 向量字段

embedding

用于：

Dense Vector Retrieval

具体 Elasticsearch Mapping、Analyzer、Dense Vector dims 等：

在技术选型阶段确定。

不得提前假设：

dims = 768

除非后续 Embedding 模型已经确定。

---

# 34. Embedding模型数据要求

后续选择的 Embedding 模型至少需要满足：

- 支持英文官方文档；
- 支持中文用户 Query；
- 具有较好的跨语言检索能力；
- 适用于短 Query → Chunk Retrieval；
- 模型规模适合本机运行；
- 文档 Embedding 与 Query Embedding 使用兼容空间。

具体模型不属于本 DATA_DESIGN 阶段。

---

# 35. Chunk落盘

即使所有 Chunk 最终写入 Elasticsearch，也必须保存：

data/processed/chunks.jsonl

原因：

- 人工查看 Chunk；
- 调试 Splitter；
- 检查 Metadata；
- 重建 ES Index；
- 更换 Embedding Model；
- Golden Chunk 标注；
- 复现实验。

不能让 Elasticsearch 成为唯一的数据副本。

---

# 36. 数据去重

第一版至少实现：

### 来源级去重

相同 canonical source URL
不得重复导入。

### 内容级去重

通过：

content_hash

识别完全重复内容。

第一版暂时不引入：

MinHash
SimHash
复杂近重复算法

除非实际数据表明近重复已经成为明显问题。

---

# 37. 数据质量检查

写入 Elasticsearch 之前至少检查：

- chunk_id 非空；
- chunk_id 唯一；
- parent_doc_id 存在；
- content 非空；
- source_title 非空；
- source_url 非空；
- content_hash 存在；
- kb_version 存在；
- Embedding 维度一致；
- 无完全重复 Chunk。

同时必须进行随机人工抽样检查。

---

# 38. Chunk质量重点检查

重点检测：

1. 条件与操作被拆散；
2. Warning 与对应操作被拆散；
3. 标题语境完全丢失；
4. Chunk 只有几个无意义单词；
5. 一个 Chunk 混入两个完全不同护理主题；
6. Metadata 与正文明显不一致；
7. 来源 URL 与 Parent Document 不一致。

这些问题会直接影响后续 Retrieval。

---

# 39. Source可靠性

Source URL 的完整传递链必须是：

Source Manifest
        ↓
RawDocument
        ↓
CleanDocument
        ↓
Chunk
        ↓
Elasticsearch
        ↓
Retrieved Evidence
        ↓
API Response
        ↓
Vue

LLM 不参与 Source URL 的生成。

因此系统可以保证：

> 返回的 Source URL 与 Evidence 的原始知识来源一致。

---

# 40. Knowledge Base Build Report

每次完整构建知识库后生成：

results/kb_build_report.json

至少记录：

{
  "kb_version": "...",
  "source_count": 0,
  "document_count": 0,
  "chunk_count": 0,
  "duplicate_count": 0,
  "failed_document_count": 0,
  "metadata_statistics": {},
  "chunk_length_statistics": {},
  "build_time": 0
}

所有统计必须来自实际运行。

不得手工填写。

---

# 41. Golden Dataset与Knowledge Base分离

知识库：

data/processed/

评测数据：

data/evaluation/

必须分离。

Golden Dataset 不属于 Knowledge Base。

否则会造成训练 / 检索数据与评测数据概念混乱。

---

# 42. Golden Dataset分阶段建立

Golden Dataset 不应该等所有 Retriever 写完以后才开始设计。

正确过程：

### 阶段A：知识范围确定后

设计：

question
gt_answer
category

测试问题应独立于当前 Retriever 的实际输出。

避免：

看系统会答什么
→ 再专门设计它容易答的问题。

### 阶段B：Chunk结构稳定后

人工增加：

gold_chunk_ids
kb_version

因此最终结构：

{
  "question": "...",
  "gt_answer": "...",
  "gold_chunk_ids": [],
  "category": "...",
  "kb_version": "kb_v1"
}

---

# 43. Gold Chunk版本绑定

如果修改：

Chunking Algorithm

或者：

Knowledge Base

导致：

kb_v1
→
kb_v2

必须重新检查：

gold_chunk_ids

是否仍然有效。

不能：

用 kb_v1 的 gold_chunk_ids
评价 kb_v2

然后继续报告 Recall@5。

---

# 44. Golden Dataset防止评测泄漏

禁止简单：

读取一个 Chunk
↓
让 LLM 把它改成一个问题
↓
把这个问题直接作为主要测试集

因为这样会使 Query 与 Gold Chunk 过于接近。

Golden Dataset 应覆盖：

- 专业术语表达；
- 中文口语表达；
- 品牌限制；
- 技术限制；
- 材料限制；
- 多条件组合；
- 易混淆护理规则；
- Evidence 不充分；
- 用户缺少关键信息。

这样评测才更接近真实检索难度。

---

# 45. GitHub公开数据策略

如果项目后续上传 GitHub：

建议公开：

- Source Manifest
- Source URLs
- 数据处理代码
- Schema
- 少量示例数据
- 数据获取说明

是否公开完整第三方官方网页正文，需要根据具体网页使用条款与版权情况决定。

项目代码与本机知识库可以分离。

---

# 46. Knowledge Module接口边界

知识库模块逻辑上提供：

load_sources()
      ↓
clean_documents()
      ↓
split_documents()
      ↓
enrich_metadata()
      ↓
build_embedding_text()
      ↓
encode_chunks()
      ↓
build_index()

这些表示职责边界。

具体 Python 函数签名在实施阶段由 Codex 根据工程结构设计。

---

# 47. 最终工程目录映射

fashion-care-rag/
│
├── backend/
│   └── app/
│       └── knowledge/
│           ├── models.py
│           ├── loader.py
│           ├── cleaner.py
│           ├── splitter.py
│           ├── metadata.py
│           ├── terminology.py
│           ├── embedding.py
│           └── indexer.py
│
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   │   └── chunks.jsonl
│   ├── dictionaries/
│   │   └── terminology.json
│   ├── manifests/
│   │   └── sources.jsonl
│   └── evaluation/
│
├── scripts/
│   └── build_knowledge_base.py
│
├── results/
│   └── kb_build_report.json
│
└── docs/
    └── DATA_DESIGN.md

---

# 48. 本阶段明确不决定的内容

数据设计阶段不提前固定：

- Elasticsearch 具体版本；
- Elasticsearch Analyzer；
- Embedding 具体模型；
- Embedding Vector Dimensions；
- Cross-Encoder 模型；
- MAX_CHUNK_TOKENS；
- MIN_CHUNK_TOKENS；
- Overlap；
- BM25 Field Boost；
- Metadata Boost权重；
- Retrieval Top-N；
- RRF参数；
- Rerank Top-K；
- Evidence Grade算法。

这些属于后续：

技术选型
+
Retrieval Design
+
实际实验

阶段。

---

# 49. 最终数据主线

整个数据层可以压缩为：

Official Care Source
        ↓
Source Manifest
        ↓
RawDocument
        ↓
CleanDocument
        ↓
Structure-aware Chunk
        │
        ├── content
        │     └── 官方Evidence
        │
        ├── Metadata
        │
        ├── normalized_terms
        │     └── 检索辅助
        │
        ├── embedding_text
        │     └── Dense编码输入
        │
        └── source information
                ↓
             Embedding
                ↓
          Elasticsearch

检索阶段：

```
BM25
↓
content
+ title
+ section
+ technology
+ normalized_terms
（Multi-field Search）
Dense
↓
embedding
```

生成阶段：

```
Top-K Evidence
↓
content
↓
LLM
```

来源展示：

```
Evidence
↓
source_title + source_url
```
