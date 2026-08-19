# FORAG (Fashion-Care Outdoor RAG)

> **基于 LangGraph 与混合检索的户外功能服装智能养护可追溯问答系统**

---

## 1. 项目背景与核心价值

冲锋衣（GORE-TEX）、DWR 防泼水涂层与高端羽绒服装等户外装备具备复杂且严苛的清洗、烘干与性能恢复要求。用错洗涤剂或高温烘干极易造成面料透气膜分层与涂层损毁。然而，互联网上养护资料零散且偏方频出；通用大语言模型直接回答易产生参数幻觉，且无法提供可靠的行内出处溯源。

**FORAG 的核心价值**在于将户外服装养护问答从「大模型直接凭空生成」转变为「**可检索、可判断、可追溯、可评估**」的证据驱动闭环系统。

---

## 2. 五个核心模块 (Five-Part Architecture)

整个系统划分为五个高度工程化的核心模块：

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        FORAG 总体架构 (Five Parts)                      │
└────────────────────────────────────────────────────────────────────────┘
  Part 1: 数据与专业知识库构建 (14 官方来源 / 234 结构化切片 / E5 向量 / ES 9.5.1)
                            │
                            ▼
  Part 2: 混合检索与证据重排 (BM25 + Dense 双路召回 → RRF 融合 → Cross-Encoder 重排)
                            │
                            ▼
  Part 3: 证据驱动的 RAG 问答闭环 (Query Analysis → Evidence Judge → Rewrite → [E#] 生成)
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
  Part 4: 评测与实验验证        Part 5: Web 系统与交互工程
  (Golden 42 / RAGChecker / 消融)  (FastAPI / Vue 3 / Vite / 过程可视化)
```

1. **Part 1：数据与专业知识库构建**：从 Arc'teryx、GORE-TEX、Patagonia、Nikwax、Grangers 等 **14 个官方来源**采集权威资料，经结构感知递归切分为 **234 个规范知识切片**，在 Elasticsearch 9.5.1 中建立 BM25 倒排与 384 维向量混合索引。
2. **Part 2：混合检索与证据重排**：采用 BM25 与 Dense 向量双路召回（各 Top-20），通过 RRF（$k=60$）倒数排名融合去重合成 Top-30 候选池，再经多语言 Cross-Encoder 深度重排输出 Top-5 证据切片。
3. **Part 3：证据驱动的问答闭环**：基于 LangGraph 状态机编排意图解析、证据充分性判定（Evidence Judge）、增量改写检索（Query Rewrite，最大 1 次）与行内出处 `[E#]` 引用生成。
4. **Part 4：评测与实验验证**：基于包含 42 条样本的 Golden Dataset（DEV 26 / TEST 16），接入 RAGChecker 0.1.9 自动化评估，并完成 4 种检索变体横向消融与错误归因。
5. **Part 5：Web 系统与工程化交互**：基于 FastAPI 与 Vue 3 + Vite 构建高质感前后端分离应用，提供问答交互、Sources 来源清单、Evidence 候选抽屉、检索执行流图与评测看板。

---

## 3. RAG 核心检索流程

```mermaid
graph TD
    UserQuery[用户提问 Query] --> QA[Query Analysis 意图解析]
    QA --> BM25[BM25 文本检索<br>Top-20]
    QA --> Dense[Dense 向量检索<br>E5-small / Top-20]
    BM25 --> RRF[RRF 倒数排名融合<br>k=60 / Top-30 候选池]
    Dense --> RRF
    RRF --> CE[Cross-Encoder 深度重排<br>mmarco-mMiniLMv2 / Top-5]
    CE --> Judge{Evidence Judge<br>证据充分性判定}
    Judge -- 充分 (sufficient) --> AnsGen[Answer Generation<br>带 [E#] 行内引用生成]
    Judge -- 不足且可改写 --> Rewrite[Query Rewrite<br>第 2 轮增量检索]
    Rewrite --> BM25
    Judge -- 缺少必要信息 --> NeedsInfo[needs_more_information<br>引导补充面料/洗标]
    Judge -- 超出范围/仍不足 --> Insufficient[insufficient_evidence<br>安全终止拒绝编造]
```

---

## 4. 最终系统评测结果 (Stage 14 Official TEST)

系统评测基于 16 条冻结正式 TEST 样本与 RAGChecker 0.1.9 事实级自动化评估框架（Golden Dataset 共 42 条样本）：

| 核心指标 | 官方数值 | 指标定义与客观说明 |
| :--- | :---: | :--- |
| **Success@5 / Recall@5** | **87.5%** (14/16) | 14 个样本在最终 Top-5 中精确召回了目标黄金切片。 |
| **Claim Recall** | **77.9%** | 回答覆盖了参考答案中 77.9% 的核心事实声明；复合条件场景仍有细节遗漏。 |
| **Context Precision** | **41.2%** | **系统当前主要性能限制**。Top-5 候选窗口中仍包含部分未直接引用的背景文字。 |
| **Faithfulness** | **81.4%** | 多数生成内容能够得到检索证据支持；通过证据约束与保守路由降低无依据生成风险。 |

---

## 5. DEV 检索消融实验结果 (Ablation Study)

在 24 条 DEV 可评测样本上的 4 种检索变体横向对比：

| 检索变体 (Variant) | Top-5 命中数 | Recall@5 | 阶段转化与消融发现 |
| :--- | :---: | :---: | :--- |
| **Variant A: BM25 Only** | 4 / 24 | 16.7% | 独占命中 2 条；受专业词与口语表达差异影响大。 |
| **Variant B: Dense Only** | 9 / 24 | 37.5% | 独占命中 7 条；两路检索存在显著互补。 |
| **Variant C: BM25+Dense+RRF Top5** | 9 / 24 | 37.5% | 融合异构排名；为后续重排构建高质量 Top-30 候选池。 |
| **Variant D: Full (RRF + Cross-Encoder)** | 12 / 24 | 50.0% | 救回 7 条、丢弃 4 条，**净增加 +3 hits**，Recall 提升至 50.0%。 |

- **错误归因分析（DEV 12 条未命中）**：
  - 候选召回损失（Candidate-generation loss）：**5 条**（正确证据未进入前置双路召回）。
  - 融合排序损失（Fusion/ranking loss）：**0 条**（召回命中切片均保留在 RRF Top-30 中）。
  - 重排损失（Rerank loss）：**7 条**（正确证据在 Top-30 中，但经 CE 重排后未排进 Top-5）。

---

## 6. 项目目录结构

```text
FORAG/
├── backend/                  # FastAPI 后端与核心逻辑
│   ├── app/
│   │   ├── api/              # API 路由与 Pydantic schemas (/api/chat, /api/metrics, /api/health)
│   │   ├── core/             # 系统配置与环境变量加载 (Pydantic Settings)
│   │   ├── agent/            # LangGraph 状态机、Query Analysis、Evidence Judge、Answer Gen
│   │   ├── evaluation/       # 评测脚本、Golden Dataset 加载与官方指标快照
│   │   ├── kb/               # 知识库采集、清洗、切分与 Elasticsearch 索引构建器
│   │   └── retrieval/        # BM25、Dense 向量检索、RRF 融合与 Cross-Encoder 重排器
│   └── tests/                # 后端测试用例 (Pytest 146 项测试)
├── frontend/                 # Vue 3 + Vite 前端
│   ├── src/
│   │   ├── api/              # 前端 API 客户端封装
│   │   ├── views/            # 核心页面 (ChatView 智能问答, MetricsView 评测看板)
│   │   └── style.css         # 高质感定制样式
│   └── tests/                # 前端原生单元测试 (8 项测试)
├── data/
│   ├── raw/                  # 14 个官方权威来源原始文档
│   └── golden_dataset.jsonl  # 42 条标准黄金评测数据集
├── docs/                     # 完整交付文档
│   ├── USER_GUIDE.md         # 用户使用说明 (14 节详细指南)
│   ├── FINAL_PROJECT_SUMMARY.md # 项目全景技术总结
│   ├── DEFENSE_GUIDE.md      # 答辩逐字稿、30+ 问答库与简历包装
│   └── STAGE15_EXECUTION_REPORT.md # Stage 15 全栈验证与消融报告
├── pyproject.toml            # Python 依赖管理 (uv)
└── package.json              # 根目录与前端配置
```

---

## 7. 环境要求

- **操作系统**：Windows / Linux / macOS
- **Python**：`3.12`（推荐使用 `uv` 管理虚拟环境）
- **Node.js**：`24 LTS` 或更高版本，包含 `npm`
- **Elasticsearch**：`9.5.1`

---

## 8. 快速安装与启动

### 8.1 基础配置
```powershell
# 1. 复制环境变量配置文件
Copy-Item .env.example .env

# 2. 编辑 .env 配置（填入 Elasticsearch 凭证与 Qwen API Key）
# DASHSCOPE_API_KEY=your_api_key_here
```

### 8.2 启动本地 Elasticsearch
```powershell
# 启动本地 Elasticsearch 实例（若内存紧张可指定 JVM 堆大小）
$env:ES_JAVA_OPTS="-Xms1g -Xmx1g"
# 确保 ES 正常监听在 https://localhost:9200
```

### 8.3 启动后端服务 (FastAPI)
```powershell
# 同步 Python 虚拟环境依赖
uv sync

# 启动 FastAPI 后端服务
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
后端交互文档访问地址：<http://127.0.0.1:8000/docs>

### 8.4 启动前端服务 (Vue 3 + Vite)
```powershell
# 进入前端目录
Set-Location frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```
前端界面访问地址：<http://localhost:5173>

---

## 9. 自动化测试与验证

```powershell
# 运行后端全量测试 (146 项测试，包括 CORS、检索链路与 Agent 状态机)
uv run pytest

# 运行前端单元测试 (8 项测试)
Set-Location frontend
npm test

# 运行前端生产打包构建
npm run build
```

---

## 10. API 核心接口

| 接口路径 | 请求方式 | 功能描述 |
| :--- | :---: | :--- |
| `/api/chat` | `POST` | 智能问答核心接口（接收 `{ "question": "..." }`，返回回答、出处 Sources、候选切片 Evidence 与检索过程 trace）。 |
| `/api/metrics` | `GET` | 读取冻结正式 TEST 集的 RAGChecker 评测指标快照。 |
| `/api/health` | `GET` | 服务健康检查接口（校验 Elasticsearch 连接状态与索引可用性）。 |

---

## 11. 当前系统局限性

1. **上下文纯度较低 (Context Precision = 41.2%)**：Top-5 候选切片中包含部分未被引用的背景文字，为后续引入自适应动态重排阈值的重点改进方向。
2. **单轮无状态交互**：当前系统为单轮独立问答，不保留跨轮会话记忆。

---

## 12. 交付文档导航

- 📖 **用户使用说明**：[docs/USER_GUIDE.md](docs/USER_GUIDE.md)（面向最终用户的 14 节提问与交互指南）
- 📑 **项目技术总结**：[docs/FINAL_PROJECT_SUMMARY.md](docs/FINAL_PROJECT_SUMMARY.md)（五部分架构、消融分析与错误归因全景总结）
- 🎓 **答辩与求职指南**：[docs/DEFENSE_GUIDE.md](docs/DEFENSE_GUIDE.md)（5/10 分钟答辩稿、30+ 道高频问答库与 STAR 简历包装）
- 📊 **全栈验证报告**：[docs/STAGE15_EXECUTION_REPORT.md](docs/STAGE15_EXECUTION_REPORT.md)（Stage 15 浏览器 E2E、消融与延迟评测记录）

---

## 13. 项目状态

- **Stage 1 ~ 15**：全部通过全栈验证并闭环封板（`DONE / CLOSED`）。
- **Stage 16 (Final Documentation & Delivery)**：交付材料齐备，进入最终验收。
