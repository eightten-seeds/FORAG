<script setup>
import { computed, ref } from 'vue'

import { ragApi } from '../api/rag.js'
import { createRequestGate, formatRequestSeconds, presentBusinessStatus } from './chatPresentation.js'

const question = ref('')
const result = ref(null)
const errorMessage = ref('')
const isLoading = ref(false)
const elapsedMs = ref(null)
const gate = createRequestGate()

const canSubmit = computed(() => question.value.trim().length > 0)
const responseStatus = computed(() => result.value?.final_response?.status || null)
const statusCopy = computed(() => presentBusinessStatus(responseStatus.value))

function displayError(error) {
  if (error?.status === 422) return '问题不能为空，请输入具体的护理问题。'
  return error?.message || '请求失败，请稍后重试。'
}

async function submitQuestion() {
  const normalizedQuestion = question.value.trim()
  if (!normalizedQuestion || !gate.begin()) return

  isLoading.value = true
  result.value = null
  errorMessage.value = ''
  elapsedMs.value = null
  const startedAt = performance.now()
  try {
    result.value = await ragApi.chat(normalizedQuestion)
    elapsedMs.value = performance.now() - startedAt
  } catch (error) {
    errorMessage.value = displayError(error)
  } finally {
    isLoading.value = false
    gate.end()
  }
}
</script>

<template>
  <section class="chat-layout">
    <section class="panel ask-panel" aria-labelledby="chat-title">
      <p class="eyebrow">护理问答</p>
      <h2 id="chat-title">描述你的户外功能服装护理问题</h2>
      <p class="intro">系统会检索当前知识库中的官方护理资料，并生成带来源的回答。</p>

      <form class="question-form" @submit.prevent="submitQuestion">
        <label for="question">问题</label>
        <textarea
          id="question"
          v-model="question"
          :disabled="isLoading"
          rows="5"
          placeholder="例如：防水外套日常清洗和烘干时应注意什么？"
        />
        <div class="form-actions">
          <p v-if="isLoading" class="loading-message" role="status">
            正在检索官方护理资料并生成回答…
          </p>
          <button type="submit" :disabled="isLoading || !canSubmit">
            {{ isLoading ? '正在处理…' : '发送问题' }}
          </button>
        </div>
      </form>

      <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    </section>

    <section v-if="result" class="result-stack" aria-live="polite">
      <section class="panel response-panel">
        <p class="eyebrow">{{ statusCopy.title }}</p>
        <h2>{{ statusCopy.description }}</h2>
        <p class="answer-text">{{ result.final_response.answer }}</p>
        <p v-if="elapsedMs !== null" class="request-timing">
          浏览器请求耗时：{{ formatRequestSeconds(elapsedMs) }}
        </p>
      </section>

      <section v-if="result.final_response.sources.length" class="panel compact-panel">
        <h3>来源</h3>
        <ol class="source-list">
          <li v-for="source in result.final_response.sources" :key="source.evidence_id">
            <strong>[{{ source.evidence_id }}] {{ source.source_title }}</strong>
            <span>{{ source.section_title }}</span>
            <a
              :href="source.source_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              查看来源
            </a>
          </li>
        </ol>
      </section>

      <details class="panel compact-panel">
        <summary>检索证据（{{ result.evidence.length }} 条）</summary>
        <article v-for="item in result.evidence" :key="item.chunk_id" class="evidence-card">
          <p class="evidence-meta">#{{ item.rank }} · {{ item.source_title }} · {{ item.section_title }}</p>
          <p class="evidence-content">{{ item.content }}</p>
        </article>
      </details>

      <details class="panel compact-panel">
        <summary>检索与路由 trace</summary>
        <dl class="trace-grid">
          <div><dt>检索轮次</dt><dd>{{ result.trace.retrieval_pass_count }}</dd></div>
          <div><dt>改写轮次</dt><dd>{{ result.trace.rewrite_count }}</dd></div>
          <div><dt>证据判断</dt><dd>{{ result.trace.evidence_grade }}</dd></div>
          <div><dt>不足原因</dt><dd>{{ result.trace.insufficient_reason || '无' }}</dd></div>
          <div><dt>最终路由</dt><dd>{{ result.trace.final_route }}</dd></div>
          <div><dt>最终状态</dt><dd>{{ result.trace.final_status }}</dd></div>
        </dl>
        <div v-for="pass in result.trace.retrieval_passes" :key="pass.pass_index" class="pass-trace">
          <strong>第 {{ pass.pass_index }} 轮检索</strong>
          <span>BM25 {{ pass.bm25_count }} · Dense {{ pass.dense_count }} · RRF {{ pass.rrf_count }} · Reranked {{ pass.reranked_count }}</span>
        </div>
      </details>
    </section>
  </section>
</template>
