<script setup>
import { computed, ref } from 'vue'

import { ragApi } from '../api/rag.js'
import {
  computeProcessSummary,
  createRequestGate,
  formatRequestSeconds,
  presentBusinessStatus,
  presentEvidenceSemantics,
} from './chatPresentation.js'

const question = ref('')
const submittedQuestion = ref('')
const result = ref(null)
const errorMessage = ref('')
const isLoading = ref(false)
const elapsedMs = ref(null)
const activeTab = ref('evidence')
const gate = createRequestGate()

const canSubmit = computed(() => question.value.trim().length > 0)
const responseStatus = computed(() => result.value?.final_response?.status || null)
const statusCopy = computed(() => presentBusinessStatus(responseStatus.value))

const evidenceSemantics = computed(() => {
  const count = result.value?.evidence?.length || 0
  return presentEvidenceSemantics(responseStatus.value, count)
})

const processSummary = computed(() => {
  if (!result.value?.trace) return null
  return computeProcessSummary(result.value.trace, responseStatus.value)
})

const knowledgeCoverage = [
  {
    num: '01',
    title: '防水外壳',
    subtitle: 'GORE-TEX / 冲锋衣',
    desc: '机洗水温、专用洗剂要求与低温烘干激活',
    iconType: 'hardshell',
  },
  {
    num: '02',
    title: 'DWR 防泼水',
    subtitle: '表层面料不挂水',
    desc: '表面浸湿成因、防泼水层热激活与喷剂修复',
    iconType: 'dwr',
  },
  {
    num: '03',
    title: '羽绒服装',
    subtitle: '羽绒服 · 羽绒裤',
    desc: '专业羽绒洗剂、低温慢速烘干与结团拍打恢复',
    iconType: 'down',
  },
  {
    num: '04',
    title: '软壳与抓绒',
    subtitle: 'Softshell · Fleece',
    desc: '日常透气维护、避免织物柔顺剂与阴干建议',
    iconType: 'fleece',
  },
]

const sampleQuestions = [
  'GORE-TEX 冲锋衣应该怎么洗？',
  '冲锋衣现在不挂水珠了怎么办？',
  '羽绒服洗完以后结成一团怎么恢复？',
  'GORE-TEX 衣服应该怎么烘干？',
]

function fillSample(sample) {
  if (isLoading.value) return
  question.value = sample
}

function resetToNewQuestion() {
  result.value = null
  submittedQuestion.value = ''
  errorMessage.value = ''
  question.value = ''
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submitQuestion()
  }
}

function displayError(error) {
  if (error?.status === 422) return '问题不能为空，请输入具体的养护问题。'
  return error?.message || '暂时无法完成请求，请稍后重试。'
}

async function submitQuestion() {
  const normalized = question.value.trim()
  if (!normalized || !gate.begin()) return

  submittedQuestion.value = normalized
  isLoading.value = true
  result.value = null
  errorMessage.value = ''
  elapsedMs.value = null
  const startedAt = performance.now()

  try {
    result.value = await ragApi.chat(normalized)
    elapsedMs.value = performance.now() - startedAt
    activeTab.value = 'evidence'
  } catch (error) {
    errorMessage.value = displayError(error)
  } finally {
    isLoading.value = false
    gate.end()
  }
}
</script>

<template>
  <div class="chat-page-container">
    <!-- Two Column Main Layout -->
    <div class="chat-two-column-layout">
      <!-- ================= LEFT COLUMN: CONVERSATION (~66%) ================= -->
      <section class="left-conversation-column" aria-label="对话与问答区域">
        <!-- 1. Editorial Guidance Section in Empty State -->
        <section v-if="!result && !isLoading" class="editorial-guidance-section luxury-glow-card">
          <div class="hero-header">
            <div class="hero-eyebrow">
              <span class="eyebrow-tag">TECHNICAL APPAREL CARE</span>
              <span class="eyebrow-dot">/</span>
              <span class="eyebrow-sub">GROUNDED RAG SYSTEM</span>
            </div>
            <h1 class="hero-title">户外功能服装养护知识助手</h1>
            <p class="hero-desc">
              基于品牌官方护理资料，为功能服装提供可检索、可追溯的清洗、烘干与防泼水维护建议。
            </p>
            <div class="hero-facts-line">
              <span class="fact-item"><strong class="fact-val">14</strong> 个官方来源</span>
              <span class="facts-divider">·</span>
              <span class="fact-item"><strong class="fact-val">234</strong> 个规范切片</span>
              <span class="facts-divider">·</span>
              <span class="fact-item">多路混合检索与重排</span>
            </div>
          </div>

          <!-- Editorial Numbered Knowledge Coverage with Micro Functional Glyphs -->
          <div class="coverage-editorial-block">
            <div class="block-header-row">
              <h2 class="section-label">知识覆盖领域</h2>
              <span class="section-sub-label">01 — 04 DOMAIN MODULES</span>
            </div>
            <div class="coverage-editorial-grid">
              <div
                v-for="item in knowledgeCoverage"
                :key="item.num"
                class="coverage-editorial-item"
              >
                <div class="item-num-box">
                  <span class="item-num">{{ item.num }}</span>
                  <div class="item-glyph-wrap" aria-hidden="true">
                    <!-- 01 Hardshell Membrane -->
                    <svg v-if="item.iconType === 'hardshell'" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.25">
                      <path d="M2 5L8 2L14 5L8 8L2 5Z" />
                      <path d="M2 8.5L8 11.5L14 8.5" />
                      <path d="M2 12L8 15L14 12" />
                    </svg>
                    <!-- 02 DWR Droplet -->
                    <svg v-else-if="item.iconType === 'dwr'" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.25">
                      <path d="M8 2.5C8 2.5 4 7 4 10C4 12.2 5.8 14 8 14C10.2 14 12 12.2 12 10C12 7 8 2.5 8 2.5Z" />
                      <path d="M2 14.5H14" stroke-dasharray="1.5 1.5" />
                    </svg>
                    <!-- 03 Down Cluster -->
                    <svg v-else-if="item.iconType === 'down'" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.25">
                      <circle cx="8" cy="8" r="2.5" />
                      <path d="M8 2V5M8 11V14M2 8H5M11 8H14M3.8 3.8L6 6M10 10L12.2 12.2M12.2 3.8L10 6M6 10L3.8 12.2" />
                    </svg>
                    <!-- 04 Fleece Grid -->
                    <svg v-else width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.25">
                      <rect x="2.5" y="2.5" width="11" height="11" rx="1.5" />
                      <path d="M2.5 8H13.5M8 2.5V13.5" />
                      <path d="M5.5 5.5H10.5M5.5 10.5H10.5" stroke-dasharray="1 1" />
                    </svg>
                  </div>
                </div>
                <div class="item-body">
                  <div class="item-heading">
                    <strong class="item-title">{{ item.title }}</strong>
                    <span class="item-sub">{{ item.subtitle }}</span>
                  </div>
                  <p class="item-desc">{{ item.desc }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Example Questions (Editorial 2x2 List with Magnetic Hover) -->
          <div class="examples-editorial-block">
            <div class="block-header-row">
              <h2 class="section-label">常见养护咨询</h2>
              <span class="section-sub-label">QUICK VERIFIED QUERIES</span>
            </div>
            <div class="examples-editorial-grid">
              <button
                v-for="sample in sampleQuestions"
                :key="sample"
                type="button"
                class="example-item-btn"
                :disabled="isLoading"
                @click="fillSample(sample)"
              >
                <span class="example-text">{{ sample }}</span>
                <span class="example-arrow" aria-hidden="true">→</span>
              </button>
            </div>
          </div>

          <!-- Usage & Boundary Note -->
          <div class="editorial-usage-note">
            <span class="note-pill-tag">单轮独立问答</span>
            <span class="note-content-text">
              每次提问请包含完整服装与问题信息；本系统专注于官方文档清洗、烘干与 DWR 维护事实，不涉及穿搭购买推荐；信息不足时将引导补充洗标信息。
            </span>
          </div>
        </section>

        <!-- Compact Bar when Answered or Loading -->
        <div v-else class="compact-editorial-bar luxury-glow-card">
          <div class="bar-left">
            <span class="bar-brand-tag">FORAG</span>
            <span class="bar-topic-text">户外功能服装养护知识助手 · 官方资料可追溯</span>
          </div>
          <button type="button" class="new-query-link-btn" @click="resetToNewQuestion">
            + 提新问题
          </button>
        </div>

        <!-- 2. Dynamic Conversation Stream -->
        <div v-if="submittedQuestion" class="conversation-stream">
          <!-- User Chat Bubble -->
          <div class="user-bubble-row">
            <div class="user-chat-bubble">
              <p class="user-bubble-text">{{ submittedQuestion }}</p>
            </div>
          </div>

          <!-- Assistant Loading State -->
          <div v-if="isLoading" class="assistant-loading-row">
            <div class="assistant-loading-box luxury-glow-card" role="status">
              <div class="loading-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </div>
              <span class="loading-status-text">正在检索知识库、评估证据并生成建议…</span>
            </div>
          </div>

          <!-- Assistant Editorial Answer Block -->
          <article v-else-if="result" class="assistant-answer-section">
            <div class="editorial-answer-card luxury-glow-card" :class="`status-${responseStatus}`">
              <!-- Answer Block Header -->
              <div class="answer-header-row">
                <div class="brand-status-lead">
                  <span class="answer-brand-title">FORAG</span>
                  <span class="status-marker-pill" :class="`marker-${responseStatus}`">
                    <span class="status-dot-sm"></span>
                    <span>{{ statusCopy.title }}</span>
                  </span>
                </div>
              </div>

              <p class="answer-lead-desc">{{ statusCopy.description }}</p>

              <!-- Main Answer Text -->
              <div class="answer-body-content">
                <p class="answer-text">{{ result.final_response.answer }}</p>
              </div>

              <!-- Editorial Sources List (Provenance) -->
              <div v-if="result.final_response.sources?.length" class="editorial-sources-block">
                <div class="sources-head-row">
                  <h3 class="sources-title">参考来源清单</h3>
                  <span class="sources-count-sub">{{ result.final_response.sources.length }} 个官方切片已验证</span>
                </div>
                <div class="sources-editorial-list">
                  <div
                    v-for="s in result.final_response.sources"
                    :key="s.evidence_id"
                    class="source-editorial-row"
                  >
                    <span class="source-evidence-badge">[{{ s.evidence_id }}]</span>
                    <div class="source-info-col">
                      <span class="source-primary-title">{{ s.source_title }}</span>
                      <span class="source-secondary-title">{{ s.section_title }}</span>
                    </div>
                    <a
                      :href="s.source_url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="source-link"
                    >
                      查看官方出处 ↗
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>

        <!-- 3. Composer / Input Area -->
        <section class="composer-container">
          <form class="composer-form" @submit.prevent="submitQuestion">
            <div class="composer-input-box luxury-glow-card">
              <label for="question-input" class="visually-hidden">输入养护问题</label>
              <textarea
                id="question-input"
                v-model="question"
                :disabled="isLoading"
                rows="3"
                placeholder="例如：GORE-TEX 冲锋衣洗完不挂水了，应该怎么办？"
                @keydown="handleKeydown"
              />
              <div class="composer-actions-row">
                <div class="composer-hints-group">
                  <span class="composer-hint-main">单轮独立问答 · 请说明面料、品牌与具体问题</span>
                  <span class="composer-hint-sub">Enter 发送 / Shift+Enter 换行</span>
                </div>
                <button
                  type="submit"
                  class="composer-send-btn"
                  :disabled="isLoading || !canSubmit"
                >
                  <span v-if="isLoading">检索中…</span>
                  <span v-else>发送 ↵</span>
                </button>
              </div>
            </div>
          </form>

          <p v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</p>
        </section>
      </section>

      <!-- ================= RIGHT COLUMN: KNOWLEDGE REFERENCE READER (~34%) ================= -->
      <aside class="right-evidence-column" aria-label="检索依据与过程">
        <div class="right-reader-container luxury-glow-card">
          <!-- Reader Tabs Header -->
          <div class="reader-tabs-header">
            <div class="reader-title-group">
              <h2 class="reader-title">检索依据</h2>
              <span class="reader-eyebrow-sub">KNOWLEDGE DOSSIER</span>
            </div>
            <div class="reader-tab-nav" role="tablist">
              <button
                type="button"
                role="tab"
                :aria-selected="activeTab === 'evidence'"
                class="reader-tab-btn"
                :class="{ active: activeTab === 'evidence' }"
                @click="activeTab = 'evidence'"
              >
                {{ evidenceSemantics.tabTitle }}
                <span v-if="result?.evidence?.length" class="tab-count-sub">({{ result.evidence.length }})</span>
              </button>
              <button
                type="button"
                role="tab"
                :aria-selected="activeTab === 'process'"
                class="reader-tab-btn"
                :class="{ active: activeTab === 'process' }"
                @click="activeTab = 'process'"
              >
                检索过程
              </button>
            </div>
          </div>

          <!-- TAB 1: EVIDENCE REFERENCE LIST -->
          <div v-if="activeTab === 'evidence'" class="reader-tab-panel evidence-reader-panel">
            <!-- Empty State Before Submission -->
            <div v-if="!result" class="reader-empty-placeholder">
              <div class="empty-schematic-icon" aria-hidden="true">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.25">
                  <path d="M4 19.5V4.5C4 3.67 4.67 3 5.5 3H18.5C19.33 3 20 3.67 20 4.5V19.5" />
                  <path d="M4 19.5C4 18.67 4.67 18 5.5 18H20" />
                  <path d="M8 7H16M8 11H13" stroke-linecap="round" />
                </svg>
              </div>
              <p class="empty-lead">回答后在此展示检索切片</p>
              <p class="empty-sub">
                系统通过 BM25 与 Dense 混合召回候选切片，并由 Cross-Encoder 重排选出核心证据。
              </p>
              <div class="reader-stats-strip">
                <div class="stat-cell"><span>知识来源</span><strong>14 个官方源</strong></div>
                <div class="stat-cell"><span>知识切片</span><strong>234 条 Chunks</strong></div>
                <div class="stat-cell"><span>精排模型</span><strong>Cross-Encoder</strong></div>
              </div>
            </div>

            <!-- Terminal State with 0 Evidence -->
            <div v-else-if="!result.evidence?.length" class="reader-zero-state">
              <p>当前没有可展示的检索证据。</p>
            </div>

            <!-- Continuous Reference List -->
            <div v-else class="evidence-reference-list">
              <!-- Semantics Banner -->
              <div
                class="evidence-semantics-note"
                :class="{ 'is-candidate-only': evidenceSemantics.isCandidateOnly }"
              >
                <span class="note-icon">{{ evidenceSemantics.isCandidateOnly ? 'ℹ' : '✓' }}</span>
                <span class="note-text">{{ evidenceSemantics.note }}</span>
              </div>

              <!-- Continuous Evidence Items -->
              <div
                v-for="chunk in result.evidence"
                :key="chunk.chunk_id"
                class="evidence-reference-item"
              >
                <div class="item-meta-header">
                  <div class="meta-left">
                    <span class="evidence-tag">E{{ chunk.rank }}</span>
                    <div class="source-titles">
                      <strong class="doc-title">{{ chunk.source_title }}</strong>
                      <span class="sec-title">{{ chunk.section_title }}</span>
                    </div>
                  </div>
                  <span class="chunk-id-text"><code>{{ chunk.chunk_id }}</code></span>
                </div>
                <p class="chunk-body-text">{{ chunk.content }}</p>
              </div>
            </div>
          </div>

          <!-- TAB 2: RETRIEVAL PROCESS ARCHITECTURE -->
          <div v-if="activeTab === 'process'" class="reader-tab-panel process-reader-panel">
            <!-- Process Empty Placeholder -->
            <div v-if="!result" class="reader-empty-placeholder">
              <p class="empty-lead">决策流与检索诊断</p>
              <p class="empty-sub">提交问题后展示 Query Analysis、混合召回、RRF 融合与判定路由。</p>
            </div>

            <!-- Trace Architecture Flow -->
            <div v-else class="process-architecture-flow">
              <!-- Path Summary Banner -->
              <div v-if="processSummary" class="process-path-badge" :class="`path-${processSummary.type}`">
                <span class="path-tag">{{ processSummary.tag }}</span>
                <span class="path-desc">{{ processSummary.text }}</span>
              </div>

              <div class="flow-nodes-stack">
                <!-- Node 1: Query Analysis -->
                <div class="flow-node node-neutral">
                  <div class="node-header">
                    <span class="node-order">1</span>
                    <strong class="node-title">Query Analysis · 意图解析</strong>
                  </div>
                  <p class="node-sub">Qwen 模型完成意图识别与核心检索关键词抽取</p>
                </div>

                <div class="flow-arrow-divider">↓</div>

                <!-- Node 2: Parallel Dual-Channel Recall -->
                <div class="flow-node node-parallel-box">
                  <div class="node-header">
                    <span class="node-order">2</span>
                    <strong class="node-title">多路并行召回 (Hybrid Retrieval)</strong>
                  </div>
                  <div class="parallel-box-grid">
                    <div class="parallel-cell">
                      <span class="cell-label">BM25 文本检索</span>
                      <strong class="cell-val">Top {{ result.trace.retrieval_passes?.[0]?.bm25_count || 20 }}</strong>
                    </div>
                    <div class="parallel-cell">
                      <span class="cell-label">Dense 向量检索</span>
                      <strong class="cell-val">Top {{ result.trace.retrieval_passes?.[0]?.dense_count || 20 }}</strong>
                    </div>
                  </div>
                </div>

                <div class="flow-arrow-divider">↓ 倒数排名融合</div>

                <!-- Node 3: RRF Fusion -->
                <div class="flow-node node-fusion">
                  <div class="node-header">
                    <span class="node-order">3</span>
                    <strong class="node-title">RRF 融合 (k=60)</strong>
                  </div>
                  <p class="node-sub">
                    去重融合至 <strong>Top {{ result.trace.retrieval_passes?.[0]?.rrf_count || 30 }}</strong> 候选切片集合
                  </p>
                </div>

                <div class="flow-arrow-divider">↓ 深度重排</div>

                <!-- Node 4: Cross-Encoder Reranker -->
                <div class="flow-node node-reranker">
                  <div class="node-header">
                    <span class="node-order">4</span>
                    <strong class="node-title">Cross-Encoder 重排</strong>
                  </div>
                  <p class="node-sub">
                    多语言语义交互打分，筛选 <strong>Top {{ result.trace.retrieval_passes?.[0]?.reranked_count || 5 }}</strong> 最优切片
                  </p>
                </div>

                <div class="flow-arrow-divider">↓ 充分性判断</div>

                <!-- Node 5: Evidence Judge -->
                <div
                  class="flow-node node-decision"
                  :class="result.trace.evidence_grade === 'sufficient' ? 'is-sufficient' : 'is-insufficient'"
                >
                  <div class="decision-top-line">
                    <div class="node-header">
                      <span class="node-order">5</span>
                      <strong class="node-title">Evidence Judge 证据判定</strong>
                    </div>
                    <span class="decision-pill" :class="result.trace.evidence_grade === 'sufficient' ? 'pill-pos' : 'pill-warn'">
                      {{ result.trace.evidence_grade === 'sufficient' ? '● 充分' : '● 不足' }}
                    </span>
                  </div>
                  <p class="node-sub">
                    依据：{{ result.trace.evidence_grade === 'sufficient' ? '已定位到官方明确操作指南 (sufficient)' : (result.trace.insufficient_reason || '未能覆盖全部必要养护事实') }}
                  </p>
                </div>

                <!-- Node 6: Rewrite (Conditional on rewrite_count > 0) -->
                <template v-if="result.trace.rewrite_count > 0">
                  <div class="flow-arrow-divider">↓ 触发改写</div>
                  <div class="flow-node node-rewrite">
                    <div class="node-header">
                      <span class="node-order">6</span>
                      <strong class="node-title">Query Rewrite & 第 2 轮检索</strong>
                    </div>
                    <p class="node-sub">基于首轮不足原因重构检索词，完成第 2 轮增量检索</p>
                  </div>
                </template>

                <div class="flow-arrow-divider">↓ 执行决策</div>

                <!-- Final Route Outcome Card -->
                <div class="final-outcome-card">
                  <div class="outcome-top">
                    <span class="outcome-label">最终执行路由</span>
                    <span class="outcome-status-tag">状态: {{ result.trace.final_status }}</span>
                  </div>
                  <div class="outcome-main">
                    <strong class="outcome-title">
                      {{ result.trace.final_route === 'ready_for_generation' ? '✓ 进入回答生成' : (result.trace.final_route === 'insufficient_evidence' ? '⚠️ 证据不足终止' : 'ℹ️ 引导补充信息') }}
                    </strong>
                    <code class="outcome-enum">{{ result.trace.final_route }}</code>
                  </div>
                </div>
              </div>

              <!-- Technical Secondary Metadata Strip -->
              <div class="technical-stats-row">
                <div class="tech-cell"><span>检索轮次</span><strong>{{ result.trace.retrieval_pass_count }} 轮</strong></div>
                <div class="tech-cell"><span>改写次数</span><strong>{{ result.trace.rewrite_count }} 次</strong></div>
                <div class="tech-cell" v-if="elapsedMs !== null"><span>端到端耗时</span><strong>{{ formatRequestSeconds(elapsedMs) }}</strong></div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>
