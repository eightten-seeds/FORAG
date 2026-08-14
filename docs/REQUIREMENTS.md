# 户外功能服装智能养护 RAG 问答系统
# Requirements Specification

## 1. 文档目的

本文档定义“户外功能服装智能养护 RAG 问答系统”的功能需求、非功能需求、数据需求、系统边界及验收条件。

本文档回答：

1. 系统面向谁；
2. 用户可以提出什么问题；
3. 系统必须提供什么能力；
4. 系统最终输出什么；
5. 哪些功能属于本项目范围；
6. 哪些功能明确不实现；
7. 项目最终如何判断完成。

本阶段只定义需求，不设计具体代码结构和算法实现细节。

---

# 2. 核心问题

户外功能服装涉及 GORE-TEX、DWR、羽绒、合成保温材料、Softshell、Fleece 等不同材料和技术。

其清洗、烘干、防泼水恢复、储存等养护知识通常分散在品牌官网、Product Care、FAQ 和护理指南中。

同时存在两类信息匹配问题：

### 2.1 知识分散

用户需要跨多个官方页面或文档自行查找护理要求。

### 2.2 表达差异

用户通常使用：

- “冲锋衣不挂水了”
- “水直接摊开了”
- “羽绒洗完一坨一坨”
- “能不能直接烘干”

等口语表达。

官方资料则可能使用：

- DWR
- durable water repellent
- wetting-out
- restore water repellency
- loft

等专业术语。

因此系统需要解决的核心问题是：

**将用户自然语言养护问题与适用的官方护理知识进行匹配，并基于检索证据生成具有来源依据的回答。**

---

# 3. 项目目标

构建一个可以在本机浏览器中使用的户外功能服装养护 RAG Web 问答系统。

系统应能够：

1. 建立官方护理资料知识库；
2. 接收用户自然语言问题；
3. 分析问题中的关键条件；
4. 从知识库召回相关护理知识；
5. 对多路检索结果进行融合和排序；
6. 判断当前证据是否足以回答问题；
7. 必要时重新组织查询并再次检索；
8. 基于最终证据生成回答；
9. 展示回答来源及相关证据；
10. 对最终系统进行量化评测。

---

# 4. 目标用户

主要目标用户为：

- 户外功能服装普通消费者；
- 需要查询服装清洗、烘干、储存和性能维护方法的用户；
- 对 DWR、GORE-TEX、羽绒等专业术语缺乏了解的用户。

本系统不面向专业服装检测机构，也不替代品牌售后服务。

---

# 5. 核心使用场景

## UC-01 功能服装清洗

用户：

“GORE-TEX 冲锋衣应该怎么洗？”

系统需要检索与 GORE-TEX、清洗相关的官方护理资料，并返回具体护理建议及来源。

---

## UC-02 防泼水性能下降

用户：

“我的冲锋衣以前水会形成水珠，现在直接摊开了怎么办？”

系统需要识别该表达可能对应防泼水性能下降或 wetting-out 相关问题，并检索对应护理资料。

系统不得直接将其判断为服装“漏水”或产品质量问题。

---

## UC-03 羽绒清洗后结团

用户：

“羽绒服洗完以后里面都结成一团了。”

系统需要检索羽绒干燥、恢复蓬松度等相关护理知识。

---

## UC-04 烘干条件查询

用户：

“这件功能服可以放烘干机吗？”

如果已有材料、品牌等信息，系统应检索适用护理条件。

如果缺少决定性信息且不同材料护理规则可能存在差异，应提示用户补充信息，而不是自行假设。

---

## UC-05 品牌或技术限定查询

用户：

“Arc'teryx 的 GORE-TEX 外套怎么恢复防泼水？”

系统需要保留品牌、技术类型和护理意图等实体，并优先检索适用资料。

---

## UC-06 口语与专业术语不一致

用户：

“我的外套现在完全不挂水珠了。”

即使问题没有出现“DWR”等专业术语，系统仍应具有语义检索能力。

---

## UC-07 证据不足

当知识库中没有足够依据时，系统不得生成没有来源支持的确定性结论。

系统应根据具体情况：

- 重写查询重新检索；
- 请求用户补充必要信息；
- 或明确说明当前资料不足。

---

# 6. 功能需求

系统划分为三个业务模块。

---

# 6.1 模块一：知识库构建

## FR-KB-01 文档输入

系统应能够读取整理后的官方户外功能服装护理资料。

数据来源原则上应来自：

- 品牌官网；
- 官方 Product Care；
- 官方 FAQ；
- 官方护理指南；
- 官方 Troubleshooting 文档。

不得将无法确认来源的普通论坛内容作为主要权威知识来源。

所有来源在进入知识库前必须登记到 Source Manifest，并保留真实 `source_url`、内容哈希和本地快照位置，以支持复现和来源追踪。

---

## FR-KB-02 文档清洗

系统应能够：

- 去除无关网页导航内容；
- 去除重复文本；
- 保留标题层级；
- 保留护理步骤；
- 保留条件说明；
- 保留警告和注意事项；
- 保留来源信息。

---

## FR-KB-03 文档切分

系统必须将长文档切分为可独立检索的知识 Chunk。

切分过程应尽可能保持：

“适用条件 → 操作方式 → 注意事项”

之间的完整关系。

不能仅依赖固定字符长度进行机械切割。

---

## FR-KB-04 Metadata

每个 Chunk 至少应保存：

- chunk_id
- parent_doc_id
- source_id
- source_title
- source_url
- content
- brand
- garment_type
- technology
- care_stage
- section_title
- language
- content_hash
- kb_version

Metadata 缺失时允许为空，但不得伪造。

`chunk_id` 表示逻辑身份，必须与反映正文变化的 `content_hash` 分离。最终 Chunk 必须落盘到 `data/processed/chunks.jsonl`，Elasticsearch 不得作为唯一副本。

---

## FR-KB-05 Embedding

系统应能够为知识 Chunk 生成向量表示，用于语义检索。

Embedding 必须真实执行。

---

## FR-KB-06 Elasticsearch 索引

系统应能够将：

- 原始文本；
- Metadata；
- Embedding

写入 Elasticsearch。

每个 Chunk 应具有稳定、可追踪的唯一 ID。

---

# 6.2 模块二：RAG 检索与智能体

该模块是系统核心。

## FR-RAG-01 Query Analysis

系统应能够从用户查询中识别可能影响检索的关键信息，例如：

- brand
- garment_type
- technology
- issue_type
- intent

P0 的 Query Analysis 只进行一次 LLM 调用，并同时输出：

- `structured_query`；
- `lexical_terms_en`。

不得再为 Query Formulation 单独增加一次 LLM 调用或独立 LangGraph Node。

不得强制要求所有字段都存在。

不能从用户没有提供的信息中随意推断具体品牌或型号。

---

## FR-RAG-02 BM25 检索

系统必须支持关键词检索。

该检索主要用于处理：

- 品牌名；
- 专业技术名称；
- 材料名称；
- 型号；
- 专业术语。

例如：

- GORE-TEX
- DWR
- ePE

BM25 必须从 Elasticsearch 实际执行。

---

## FR-RAG-03 Dense Vector 检索

系统必须支持基于 Query Embedding 的语义检索。

该能力主要用于解决用户口语表达与官方专业术语不一致的问题。

例如：

“水现在不挂珠了”

应有机会召回与：

“water repellency / DWR”

相关的资料。

---

## FR-RAG-04 混合召回

对于同一个 Query，系统应同时获得：

- BM25 候选文档；
- Dense Vector 候选文档。

两路结果必须保留原始排名信息。

---

## FR-RAG-05 RRF 排名融合

系统必须能够将两路候选结果进行排名融合。

RRF 应根据排名进行计算，而不能直接将 BM25 Score 与 Dense Similarity Score 简单相加。

RRF 必须真实实现，不得使用固定排序结果模拟。

---

## FR-RAG-06 Cross-Encoder Rerank

融合后的候选结果必须经过 Cross-Encoder 进行相关性重排序。

Cross-Encoder 必须实际执行 Query-Document 成对评分。

不得使用：

docs[:5]

等截断方式冒充重排序。

---

## FR-RAG-07 Top-K Evidence

系统应从重排序结果中选择最终证据集合提供给后续生成模块。

Top-K 应作为配置参数，而不是散落在代码中的固定常量。

---

## FR-RAG-08 Evidence Grade

系统必须具有证据充分性判断能力。

需要区分：

- 当前检索证据足以支持回答；
- 当前证据不足，需要进一步处理。

具体判断方法在架构设计阶段确定。

---

## FR-RAG-09 Query Rewrite

当检索证据不足时，系统应允许重新组织查询并再次检索。

Query Rewrite 必须满足：

1. 始终保留 original_query；
2. 不得无依据删除品牌；
3. 不得无依据删除材料；
4. 不得无依据删除技术名称；
5. 不得覆盖原始查询；
6. 必须限制最大 Rewrite 次数。

P0 固定 `MAX_REWRITE_COUNT=1`，即最多执行一次 Query Rewrite。

---

## FR-RAG-10 信息不足处理

Query Rewrite 与用户补充信息是两种不同机制。

如果只是表达方式不利于检索，可进行 Query Rewrite。

如果缺少决定答案所必需的信息，例如材料类型完全未知且不同材料护理方式存在冲突，系统应允许要求用户补充信息。

Query Rewrite 不得自行编造缺失条件。

---

## FR-RAG-11 Answer Generation

系统必须通过 Qwen API 基于最终检索证据生成回答。

生成模块应接收：

- 用户原始问题；
- 最终 Evidence；
- 必要的结构化查询信息。

回答应优先基于提供的证据，而不是依靠模型自由补充事实。

---

## FR-RAG-12 来源溯源

最终回答必须能够关联到检索证据。

至少需要返回：

- source_title；
- source_url；
- chunk_id；
- 对应 evidence 内容。

---

## FR-RAG-13 LangGraph 工作流

系统应通过 LangGraph 对以下流程进行状态化编排：

Query Analysis
→ Retrieval
→ RRF
→ Rerank
→ Evidence Grade

若证据充分：

Evidence Grade
→ Generation
→ END

若证据不足：

Evidence Grade
→ Query Rewrite
→ Retrieval

必须具有终止条件，禁止无限循环。

---

# 6.3 模块三：系统应用与量化评测

## FR-APP-01 Web 应用

最终系统必须能够通过浏览器使用，而不是仅提供命令行脚本。

---

## FR-APP-02 用户提问

Web 页面应提供自然语言问题输入框。

用户提交问题后，应能够查看生成状态和最终结果。

---

## FR-APP-03 回答展示

页面至少展示：

- 用户问题；
- 最终回答；
- 信息来源。

---

## FR-APP-04 Evidence 展示

系统应允许用户查看支持回答的相关 Chunk。

Evidence 可采用折叠形式展示，避免影响正常问答体验。

---

## FR-APP-05 RAG Trace

系统应支持返回基本流程信息用于开发调试，例如：

- Query Analysis 结果；
- BM25、Dense、RRF 候选数量；
- 最终 Top-K Evidence；
- 是否发生 Rewrite；
- 基础耗时。

该内容主要用于调试和项目展示，不要求普通用户必须查看。

Trace 不得直接暴露完整 LangGraph State。

---

## FR-APP-06 后端接口

系统至少需要提供：

POST /api/chat

用于完成完整问答流程。

GET /api/health

用于检查后端基本状态。

GET /api/metrics

用于读取最终量化评测结果。

---

# 7. 评测需求

## FR-EVAL-01 Golden Dataset

系统必须建立独立测试数据集。

每条测试数据至少应包括：

- question
- gt_answer

用于 Recall@5 的测试数据还应具有：

- gold_chunk_ids

---

## FR-EVAL-02 Recall@5

系统必须能够真实计算检索 Recall@5。

不得手工填写结果。

---

## FR-EVAL-03 RAGChecker

系统应使用 RAGChecker 对最终 RAG 系统进行评估。

重点记录：

- Claim Recall
- Context Precision
- Faithfulness

P0 不开展多个 Evaluator 模型的对比实验。

---

## FR-EVAL-04 评测数据真实性

以下行为禁止：

- 手工填写最终指标；
- 在代码中写死评测结果；
- 使用 Mock Response 冒充模型结果；
- 将开发案例直接当作整个系统评测结果。

---

## FR-EVAL-05 测试问题覆盖

Golden Dataset 应覆盖不同难度的问题，包括：

- 专业术语查询；
- 用户口语查询；
- 品牌限定查询；
- 材料限定查询；
- 多条件问题；
- 相似护理规则；
- 信息不足问题。

最终样本量和分布在评测设计阶段确定。

---

# 8. 输入输出需求

## 8.1 输入

核心输入：

```json
{
  "query": "我的GORE-TEX冲锋衣现在不挂水珠了怎么办？"
}
```

未来如实现多轮会话，可增加：

```
{
  "query": "...",
  "session_id": "..."
}
```

但 session_id 不是第一版系统的强制需求。

------

## 8.2 输出

核心问答接口应至少能够表达：

```json
{
  "answer": "...",
  "sources": [],
  "retrieved_chunks": [],
  "trace": {}
}
```

其中：

answer：
最终生成回答。

sources：
回答涉及的官方资料来源。

retrieved_chunks：
最终用于回答的证据 Chunk。

trace：
RAG 工作流调试信息。

------

# 9. 非功能需求

## NFR-01 本机运行

系统完整开发版本必须能够在个人电脑中启动。

最终用户应能够通过浏览器访问系统。

------

## NFR-02 核心检索真实性

以下核心链路不得使用 Mock 代替：

- Elasticsearch 检索；
- BM25；
- Dense Vector；
- RRF；
- Cross-Encoder。

------

## NFR-03 模块化

知识库构建、检索、智能体、生成、API 和评测逻辑应保持清晰职责边界。

不得把所有业务逻辑全部写进一个 FastAPI Route 或 LangGraph Node。

------

## NFR-04 可配置性

以下参数应优先通过统一配置管理：

- Elasticsearch 地址；
- Index Name；
- Embedding Model；
- Reranker Model；
- Retrieval Top-K；
- RRF 参数；
- Rerank Top-K；
- 最大 Query Rewrite 次数；
- LLM 配置。

敏感 API Key 不得写入源码。

------

## NFR-05 可追踪性

系统运行过程中应保留必要日志，至少能够定位：

- ES 连接失败；
- Embedding 失败；
- 检索失败；
- Reranker 失败；
- LLM API 失败；
- LangGraph 节点异常。

------

## NFR-06 错误处理

系统发生外部组件异常时不得直接导致前端无响应。

应返回明确错误信息。

------

## NFR-07 性能

当前阶段不人为规定具体响应时间阈值。

系统应记录实际运行时间，并在完成后根据本机真实测试结果决定是否需要进一步优化。

不得提前虚构“响应时间 < X ms”等指标。

------

## NFR-08 可复现性

项目应提供明确环境配置、依赖和启动说明，使系统可以按照 README 在相同环境重新运行。

------

# 10. 系统边界

系统明确不提供以下功能：

- 穿搭推荐；
- 商品推荐；
- 尺码推荐；
- 价格预测；
- 电商搜索；
- 医疗建议；
- 皮肤问题诊断；
- 专业服装质量鉴定；
- 专业物理损坏诊断；
- 自动售后判责；
- 自动维修决策。

对于疑似严重损坏、产品缺陷或超出官方护理资料范围的问题，应建议用户参考品牌官方售后或专业维修渠道，而不是生成确定性诊断。

------

# 11. 第一版本必须完成的功能

第一版本 P0 功能：

1. 官方护理文档知识库；
2. 文档切分；
3. Metadata；
4. Embedding；
5. Elasticsearch 索引；
6. BM25；
7. Dense Vector；
8. RRF；
9. Cross-Encoder；
10. Query Analysis；
11. Evidence Grade；
12. Query Rewrite；
13. Answer Generation；
14. 来源展示；
15. FastAPI；
16. Vue Web 页面；
17. Recall@5；
18. RAGChecker。

以下属于 P1，可在 P0 完成以后考虑：

- 更完善的多轮会话；
- 用户账户；
- 后台知识库管理页面；
- 自动文档同步；
- 复杂统计 Dashboard。

P1 功能不得阻塞第一版本完成。

------

# 12. 最终验收标准

只有满足以下条件，项目才能被认为完成。

### 知识库

-  真实官方护理资料可以读取；
-  文档可以完成清洗；
-  文档可以完成 Chunking；
-  Chunk 具有稳定 ID；
-  Metadata 正确写入；
-  Embedding 真实生成；
-  Chunk 真实写入 Elasticsearch。

### 检索

-  BM25 可以返回真实 ES 文档；
-  Dense Vector 可以返回真实 ES 文档；
-  两路检索结果可以独立查看；
-  RRF 可以真实计算融合排名；
-  Cross-Encoder 可以真实计算相关性分数；
-  最终可以产生 Top-K Evidence。

### 智能体

-  Query Analysis 可以真实执行；
-  Evidence Grade 可以真实执行；
-  证据充足时进入 Generation；
-  证据不足时可以进入 Query Rewrite；
-  Rewrite 后能够再次检索；
-  Rewrite 存在最大循环次数；
-  original_query 始终得到保留。

### 生成

-  LLM 使用检索 Evidence 生成回答；
-  回答具有来源信息；
-  证据不足时不会伪造确定性答案。

### Web 系统

-  FastAPI 可以启动；
-  Vue 可以启动；
-  浏览器可以访问系统；
-  用户可以提交问题；
-  用户能够获得真实 RAG 回答；
-  用户能够看到来源；
-  用户能够查看 Evidence。

### 评测

-  Golden Dataset 真实存在；
-  Recall@5 通过代码真实计算；
-  RAGChecker 真实运行；
-  评测结果由程序输出；
-  最终简历数据来自真实评测结果。

------

# 13. 需求完成定义

本需求阶段完成后，项目已经明确：

- 为什么做；
- 面向谁；
- 用户输入什么；
- 系统输出什么；
- 三个核心模块分别需要完成什么；
- 核心 RAG 系统需要具备什么能力；
- 哪些事情不属于本项目；
- 最终通过什么标准判断项目完成。

