<script setup>
import { onMounted, ref } from 'vue'

import { ragApi } from '../api/rag.js'

const metricsResponse = ref(null)
const errorMessage = ref('')
const isLoading = ref(true)

onMounted(async () => {
  try {
    metricsResponse.value = await ragApi.getMetrics()
  } catch (error) {
    errorMessage.value = error?.message || '暂时无法加载系统评测结果。'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <div class="metrics-page-container">
    <section class="editorial-metrics-panel luxury-glow-card">
      <!-- Editorial Page Header -->
      <div class="metrics-header-block">
        <div class="metrics-eyebrow-row">
          <span class="eyebrow-text">SYSTEM BENCHMARK & EVALUATION</span>
          <span class="eyebrow-dot">/</span>
          <span class="eyebrow-sub">RAGCHECKER 0.1.9 SPECIFICATION</span>
        </div>
        <h1 class="metrics-main-title">系统评测基准与量化结果</h1>
        <p class="metrics-lead-desc">
          基于冻结的正式 TEST 盲测集（16 个真实场景样本）与 RAGChecker 0.1.9 事实级自动化评测标准。
        </p>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="metrics-loading-state">
        <span class="spinner" aria-hidden="true"></span>
        <span>正在读取正式评测数据…</span>
      </div>

      <!-- Error State -->
      <p v-else-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</p>

      <!-- Content -->
      <template v-else-if="metricsResponse?.available && metricsResponse?.metrics">
        <!-- 1. Core 4-Metric Strip -->
        <div class="core-metrics-strip" aria-label="核心质量指标">
          <!-- Metric 1: Recall@5 -->
          <div class="metric-cell highlight-cell">
            <div class="metric-num">{{ metricsResponse.metrics.recall_at_5 }}%</div>
            <div class="metric-label">Recall@5</div>
            <div class="metric-sub">检索证据召回率</div>
          </div>

          <!-- Metric 2: Claim Recall -->
          <div class="metric-cell">
            <div class="metric-num">{{ metricsResponse.metrics.claim_recall }}%</div>
            <div class="metric-label">Claim Recall</div>
            <div class="metric-sub">参考答案事实覆盖率</div>
          </div>

          <!-- Metric 3: Context Precision (Limitation) -->
          <div class="metric-cell limitation-cell">
            <div class="metric-num">{{ metricsResponse.metrics.context_precision }}%</div>
            <div class="metric-label">Context Precision</div>
            <div class="metric-sub">上下文纯度 · <span class="limitation-text">当前主要限制</span></div>
          </div>

          <!-- Metric 4: Faithfulness -->
          <div class="metric-cell">
            <div class="metric-num">{{ metricsResponse.metrics.faithfulness }}%</div>
            <div class="metric-label">Faithfulness</div>
            <div class="metric-sub">生成真实性与证据支撑度</div>
          </div>
        </div>

        <!-- Secondary Study Info Bar -->
        <div class="study-meta-bar">
          <div class="study-meta-item">
            <span class="meta-label">TEST 测试集规模：</span>
            <strong>{{ metricsResponse.metrics.test_samples }} 样本（全量盲测未污染）</strong>
          </div>
          <span class="meta-divider">/</span>
          <div class="study-meta-item">
            <span class="meta-label">Success@5 命中比例：</span>
            <strong>{{ metricsResponse.metrics.success_at_5 }}% (14/16)</strong>
          </div>
          <span class="meta-divider">/</span>
          <div class="study-meta-item">
            <span class="meta-label">事实级评估框架：</span>
            <strong>RAGChecker 0.1.9</strong>
          </div>
        </div>

        <!-- 2. Editorial Results Analysis -->
        <section class="editorial-analysis-section">
          <div class="analysis-head-row">
            <h2 class="section-title">评测结果客观说明与分析</h2>
            <span class="analysis-sub-tag">01 — 04 VERIFIED OBSERVATIONS</span>
          </div>
          <div class="analysis-editorial-stack">
            <div class="analysis-item-row">
              <span class="item-index">01</span>
              <div class="item-text-group">
                <strong class="item-headline">正确证据最终召回表现稳定 (Recall@5 = 87.5%)</strong>
                <p class="item-body">
                  在 16 个真实测试样本中，14 个样本在最终 Top-5 准确命中了目标黄金切片。最终集成系统相较 standalone retrieval baseline，Recall@5 观察到 +12.5 个百分点差异。由于未对所有集成模块进行独立因果消融，不将该差异归因于单一组件。
                </p>
              </div>
            </div>

            <div class="analysis-item-row">
              <span class="item-index">02</span>
              <div class="item-text-group">
                <strong class="item-headline">多条件组合场景事实覆盖仍有缺口 (Claim Recall = 77.9%)</strong>
                <p class="item-body">
                  在涉及多种面料、洗剂与烘干温度复合要求的复杂问题上，部分次要事实细节未能在最终 5 条切片中完全覆盖，导致事实覆盖率略低于召回率。
                </p>
              </div>
            </div>

            <div class="analysis-item-row">
              <span class="item-index is-limitation">03</span>
              <div class="item-text-group">
                <strong class="item-headline">上下文纯度是当前系统主要限制 (Context Precision = 41.2%)</strong>
                <p class="item-body">
                  由于单条切片包含多句说明以及 Top-5 的候选窗口设定，最终上下文中仍包含较多未直接引用的背景文字。段落级细粒度过滤与更严格的阈值截断是后续主要优化方向。
                </p>
              </div>
            </div>

            <div class="analysis-item-row">
              <span class="item-index">04</span>
              <div class="item-text-group">
                <strong class="item-headline">生成内容证据支撑度 (Faithfulness = 81.4%)</strong>
                <p class="item-body">
                  多数生成内容能够得到检索证据支持，但仍存在弱支持或证据不足的情况；在证据不足或信息缺失时，系统能够按照设计进行安全拒绝或引导补充。
                </p>
              </div>
            </div>
          </div>
        </section>

        <!-- 3. Technical Provenance Table -->
        <section class="technical-provenance-section">
          <h2 class="provenance-title">评测环境与模型快照</h2>
          <div class="provenance-table-grid">
            <div class="prov-cell">
              <span class="prov-label">系统 Commit</span>
              <code class="prov-val">{{ metricsResponse.metrics.system_commit }}</code>
            </div>
            <div class="prov-cell">
              <span class="prov-label">评测 Run ID</span>
              <code class="prov-val">{{ metricsResponse.metrics.official_run_id }}</code>
            </div>
            <div class="prov-cell">
              <span class="prov-label">生成模型</span>
              <span class="prov-val">{{ metricsResponse.metrics.pipeline_llm_model }}</span>
            </div>
            <div class="prov-cell">
              <span class="prov-label">评估模型</span>
              <span class="prov-val">{{ metricsResponse.metrics.ragchecker_checker_model }}</span>
            </div>
            <div class="prov-cell">
              <span class="prov-label">Embedding 向量模型</span>
              <span class="prov-val">{{ metricsResponse.metrics.embedding_model }} (384-dim)</span>
            </div>
            <div class="prov-cell">
              <span class="prov-label">Cross-Encoder 重排模型</span>
              <span class="prov-val">{{ metricsResponse.metrics.reranker_model }}</span>
            </div>
          </div>
        </section>
      </template>

      <!-- Empty State -->
      <div v-else class="metrics-empty-box">
        <p>{{ metricsResponse?.reason || '暂未读取到正式评测数据。' }}</p>
      </div>
    </section>
  </div>
</template>
