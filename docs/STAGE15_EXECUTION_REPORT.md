# Stage 15 Comprehensive Execution Report & Evidence Pack

## 1. Executive Summary & Verification Context

FORAG（Fashion-Care Outdoor RAG）在 Stage 15 阶段完成了全栈交付与端到端闭环验证，涵盖真实浏览器端到端交互（Stage 15A）、前端高质感视觉设计与无死角回归（Stage 15B）、以及全量代码回归、DEV 检索模块消融与本地端到端延迟测试（Stage 15C）。

本阶段严格遵循**算法与知识库绝对冻结**原则：
- 知识库（14 个官方来源，234 个知识切片，234 个 384 维向量）自 Stage 3/4 起严格冻结。
- 检索器（Elasticsearch 9.5.1 BM25 + Dense + RRF + Cross-Encoder）自 Stage 5C 起严格冻结。
- Agent 状态机、Prompt 与生成逻辑自 Stage 10/11 起严格冻结。
- 官方评测基准（Stage 14 盲测结果）严格保持，禁止重新运行 TEST 集或 RAGChecker 评测框架。

---

## 2. Stage-by-Stage Verification Summary

### Stage 15A — Real Browser E2E Verification (CLOSED)
- **目标**：验证前后端分离架构在真实 Chromium 浏览器中的端到端可用性。
- **完成项**：
  - 启动 FastAPI 8000 与 Vite 5173 前后端服务，验证跨域通信。
  - 完成核心问答交互链路验证（输入、加载、回答、引用标注 `[E#]`、证据文献抽屉）。
  - 完成无多轮记忆单轮契约验证（第二轮提问仅发送当前单句，无历史会话注入）。
  - 完成 8 张全景真实渲染快照归档（涵盖正常回答、信息缺失引导、越界安全拒绝、评测指标展示与移动端响应式布局）。

### Stage 15B — Frontend Product Finish & High-Aesthetic Regression (CLOSED)
- **目标**：完成前端界面高质感视觉定型（High-Aesthetic Final Art Direction）与 67 项全量无死角回归。
- **完成项**：
  - 视觉冻结为 02:08 高质感版式，修正 Cross-Encoder 冗余文案。
  - 完成 67 项全覆盖验证矩阵：业务状态机（`answered`, `needs_more_information`, `insufficient_evidence`）、交互安全（XSS 转义、`v-html` 0 出现、外链安全性）、防重复提交门禁、异常捕获与降级（Chat 500、Network Failure、Health 离线告警、Metrics 异常提示）。
  - 验证多分辨率适配（1366×768 首屏无遮挡、1920×1080 居中双栏、800×1024 平板单栏流）。
  - 前端单元测试 7/7 全部通过，Vite 生产构建 0 错误。

### Stage 15C — Final Regression, DEV Retriever Ablation & Latency Smoke (IMPLEMENTATION / EVALUATION PASS)
- **目标**：执行全栈最终代码回归、DEV 检索模块消融实验、本机端到端延迟测试与证据链固化。
- **完成项**：
  - Python `compileall backend` 0 语法错误。
  - Pytest 146/146 测试全部通过（耗时 25.05s）。
  - CORS 验证（`localhost:5173` 与 `127.0.0.1:5173` 对 OPTIONS / GET / POST 均正常放行）。
  - DEV 检索模块消融实验（4 种变体横向对比，Variant D 严格复现 12/24 = 50.0% 硬门）。
  - 本机端到端延迟测试（3 个非 Golden 样本，真实记录各阶段耗时）。

---

## 3. DEV Retriever Ablation Study (DEV-Only)

### 3.1 实验契约与数据说明
- **数据集**：Golden Dataset DEV 子集（26 条总样本，24 条 retrieval-evaluable 可评估样本，2 条非检索样本排除；全量 Golden Dataset 共有 42 条，其中 DEV 26 条、TEST 16 条）。
- **输入契约**：严格复用 Stage 5C standalone retriever 输入契约（原始提问输入，无 Query Analysis 改写、无 Agent 决策、无 LLM 生成介入）。
- **评估标准**：Recall@5 与 Success@5（命中 Top 5 任意黄金切片）。

### 3.2 消融变体对比结果

| 变体名称 (Variant) | 检索与重排配置 | Top-K 评估窗口 | 命中数 (Hits / 24) | Recall@5 |
| :--- | :--- | :---: | :---: | :---: |
| **Variant A: BM25 Only** | 关键词多字段加权 BM25 检索 | Top 5 | 4 / 24 | 16.7% |
| **Variant B: Dense Only** | E5 向量语义检索 (384-dim) | Top 5 | 9 / 24 | 37.5% |
| **Variant C: BM25 + Dense + RRF** | BM25 Top20 + Dense Top20 $\rightarrow$ RRF ($k=60$) | Top 5 (RRF) | 9 / 24 | 37.5% |
| **Variant D: Full Frozen Retriever** | BM25 + Dense $\rightarrow$ RRF Top30 $\rightarrow$ Cross-Encoder | Top 5 (CE) | **12 / 24** | **50.0%** |

> [!IMPORTANT]
> **Reproduction Gate 验证**：Variant D 在 DEV 数据集上取得 **12/24 = 50.0%**，与 Stage 5C standalone DEV 历史基线完全一致，硬门严格通过。

### 3.3 BM25 与 Dense 互补性分析 (Complementarity)
在 24 个 DEV 样本的单路 Top 5 命中表现中：
- **Both Hit**（BM25 与 Dense 均命中）：**2** 条样本
- **BM25-only Hit**（仅 BM25 命中，Dense 未命中）：**2** 条样本
- **Dense-only Hit**（仅 Dense 命中，BM25 未命中）：**7** 条样本
- **Neither Hit**（单路 Top 5 均未命中）：**13** 条样本
- **样本总计**：$2 + 2 + 7 + 13 = 24$

**客观事实与结论**：
- BM25-only 命中 2 条，Dense-only 命中 7 条，两路检索存在互补；在当前 DEV 样本中 Dense 独占命中更多。
- 在当前 24 条 DEV 可评测样本上，Dense-only Recall@5 为 37.5%，数值高于 BM25-only 的 16.7%。该结果仅反映当前 DEV 样本上的观测差异，不代表统计显著性或普遍泛化结论。

### 3.4 阶段转换分析 (Transition Dynamics)
- **RRF 融合阶段 (相比单路 Top 5 并集)**：
  - Rescued（通过融合新进入 Top 5）：**1** 条样本
  - Dropped（单路进入 Top 5 但被 RRF 挤出 Top 5）：**3** 条样本
  - Unchanged：**20** 条样本
  - **客观说明**：RRF 完成 BM25 与 Dense 异构排名融合，但在当前 DEV Top5 口径下，1 条样本被 rescue、3 条样本被 drop，最终 RRF Recall@5 为 37.5%。RRF 主要提供统一候选融合与 Top30 候选池，供后续 Cross-Encoder 进一步重排。
- **Cross-Encoder 重排阶段 (相比 RRF Top 5)**：
  - Rescued（从 RRF Top 6~30 候选池被重排精选拉入 Top 5）：**7** 条样本
  - Dropped（在 RRF Top 5 但被 CE 重排挤出 Top 5）：**4** 条样本
  - Unchanged：**13** 条样本
  - **客观说明**：相较 RRF Top5，Cross-Encoder 使 7 条样本由 miss 转为 hit，同时使 4 条样本由 hit 转为 miss，净增加 3 条命中，Recall@5 由 37.5% 变为 50.0%。在当前 DEV 实验中，CE 重排的净结果为 +3 个 Top5 命中。

### 3.5 最终 Miss 样本归因分析 (12 Misses Breakdown)
在 Variant D 最终未命中的 12 个样本中：
1. **Candidate Generation Loss**（BM25 Top 20 与 Dense Top 20 均未召回目标黄金切片）：**5** 条样本（占比 41.7%，DEV-007, DEV-011, DEV-015, DEV-021, DEV-024）
2. **Fusion / Ranking Loss**（初筛召回但在 RRF Top 30 截断前丢失）：**0** 条样本（占比 0.0%）
3. **Rerank Loss**（已进入 RRF Top 30 候选池，但在 Cross-Encoder 重排时未能排入前 5）：**7** 条样本（占比 58.3%，DEV-003, DEV-004, DEV-005, DEV-006, DEV-009, DEV-013, DEV-018）

---

## 4. Local Latency Smoke Benchmark

### 4.1 测试环境说明
- **操作系统**：Windows 10 / Windows Server
- **处理器**：Intel Core i7-8750H CPU @ 2.20GHz (6 核 12 线程)
- **内存**：16 GB RAM
- **运行时**：Python 3.12.13
- **搜索引擎**：Elasticsearch 9.5.1 本地单节点
- **检索推理**：CPU 纯本地计算（E5 Embedding 批处理 + mMiniLMv2-L12 Cross-Encoder 批处理）
- **大语言模型**：远端 Qwen 3.7-Plus API（网络环境受公网延迟波动影响）

### 4.2 样本测试耗时记录 (毫秒 ms)

| 样本编号 | 问题类型与具体问题 | 业务状态 | 改写轮数 | 检索轮数 | 意图解析 (QA) | 混合检索 | 重排 | 证据判定 | 回答生成 | 端到端 (E2E) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Warmup** | 冲锋衣日常保养注意事项 | `answered` | 0 | 1 | 2980 | 1710 | *N/A* | 1450 | 11524 | 17664 (不计入统计) |
| **Query A** | `GORE-TEX冲锋衣怎么洗？` (常规回答) | `answered` | 0 | 1 | 3091 | 1692 | *N/A* | 1472 | 6574 | 12833 |
| **Query B** | `冲锋衣洗完以后不挂水了怎么恢复？` (口语回答) | `answered` | 0 | 1 | 3064 | 1703 | *N/A* | 1429 | 4309 | 10507 |
| **Query C** | `这件衣服能直接放烘干机吗？` (缺失信息) | `needs_more_information` | 0 | 1 | 2638 | 1649 | *N/A* | 1508 | **NOT APPLICABLE** | 5798 |

*注：*
- *Cross-Encoder 重排耗时包含在「混合检索」总体耗时中（约 1.6~1.7s），单项标记为 `NOT SEPARATELY AVAILABLE`。*
- *Query C 为 `needs_more_information` 终止状态，未调用大模型生成回答，因此 Answer Generation 标记为 `NOT APPLICABLE`。*

### 4.3 汇总统计

| 阶段 / 耗时指标 | 统计样本量 | 最小值 (Min) | 平均值 (Mean) | 最大值 (Max) | 属性说明 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **意图解析 (Query Analysis)** | $n=3$ | 2638 ms | 2931.0 ms | 3091 ms | 远端 LLM 结构化解析 |
| **混合检索与重排 (Retrieval Total)** | $n=3$ | 1649 ms | 1681.3 ms | 1703 ms | 本地 CPU (BM25 + Dense + RRF + CE) |
| **证据充分性判定 (Evidence Judge)** | $n=3$ | 1429 ms | 1469.7 ms | 1508 ms | 远端 LLM 规则决策 |
| **回答生成 (Answer Generation)** | **$n=2$ (Answered only)** | **4309 ms** | **5441.5 ms** | **6574 ms** | 远端 LLM 答案生成（仅计入实际生成样本） |
| **终止响应处理 (Terminal Response)** | **$n=1$ (Query C)** | **NOT APPLICABLE** | **NOT APPLICABLE** | **NOT APPLICABLE** | 确定性模板响应，不纳入生成模型延迟统计 |
| **端到端总延迟 (E2E Latency)** | **$n=3$** | **5798 ms** | **9712.7 ms** | **12833 ms** | 本机小样本单并发真实测量 |

> [!NOTE]
> 本测试为**本机开发环境、小样本（3 样本）、单并发快速冒烟测试（Local Latency Smoke）**，非生产高并发压力测试，受远端 API 网络抖动影响。

---

## 5. Frozen Official Metrics Reference (Stage 14 Baseline)

系统已冻结并发布的官方盲测指标（基于 16 个真实 TEST 盲测样本与 RAGChecker 0.1.9 自动化评估标准；全量 Golden Dataset 共 42 条样本）：

| 官方指标 (Official Metric) | 官方公布数值 | 历史 Standalone TEST 对比 | 观测差异与客观结论说明 |
| :--- | :---: | :---: | :--- |
| **Success@5** (检索命中率) | **87.5%** (14/16) | 75.0% (12/16) | 最终集成系统相对 standalone 检索的观测差异为 **+12.5 pp**。 |
| **Recall@5** (切片召回率) | **87.5%** | 75.0% | 14 个样本在最终 Top-5 中精确召回了目标黄金切片。 |
| **Claim Recall** (事实覆盖率) | **77.9%** | N/A (Stage 14 新增) | 生成回答覆盖了参考答案中 77.9% 的核心事实声明；多条件复杂场景仍有部分细节遗漏。 |
| **Context Precision** (上下文纯度) | **41.2%** | N/A (Stage 14 新增) | **系统当前主要性能限制**。Top-5 候选切片中包含部分未引用的背景描述，为后续迭代重点。 |
| **Faithfulness** (事实忠实度) | **81.4%** | N/A (Stage 14 新增) | 生成内容高度忠实于检索切片，严格杜绝凭空编造。 |

---

## 6. System Invariant & Cleanliness Verification

| 核心检查项 | 状态 | 验证结果 |
| :--- | :---: | :--- |
| **Knowledge Base (14 官方来源 / 234 知识切片 / 234 Embeddings)** | **FROZEN** | 0 变更，0 索引重建 |
| **Golden Dataset (42 总样本 / 26 DEV / 16 TEST)** | **FROZEN** | 0 样本增删，0 标注修改 |
| **Retriever & Parameters (BM25/Dense/RRF/CE)** | **FROZEN** | 0 算法变动，0 权重调参 |
| **Agent State Machine & Prompts** | **FROZEN** | 0 节点修改，0 提示词调整 |
| **Official Metrics (Stage 14 Snapshot)** | **FROZEN** | 保持 87.5% / 77.9% / 41.2% / 81.4% |
| **Golden TEST Rerun Check** | **VERIFIED** | 未执行任何 TEST 集重跑 |
| **RAGChecker Rerun Check** | **VERIFIED** | 未执行任何 RAGChecker 重跑 |
| **Personal Files Safety** | **VERIFIED** | `RAG项目包装.docx/pdf`, `评估与量化.md` 保持未修改未暂存 |
| **git diff --check** | **PASS** | 0 格式或空白冲突 |

---

## 7. Artifact Index

1. `results/stage15_dev_retriever_ablation.json`（DEV 消融实验完整 JSON 产物，本地未跟踪）
2. `results/stage15_local_latency_smoke.json`（本地延迟冒烟完整 JSON 产物，本地未跟踪）
3. `backend/app/evaluation/official_metrics.json`（官方评测快照，生产发布源）
4. `scratch/final_reg_*.png`（8 张 Stage 15B 全量回归全景截图）
