<script setup>
import { onMounted, ref } from 'vue'

import { ragApi } from '../api/rag.js'

const metrics = ref(null)
const errorMessage = ref('')
const isLoading = ref(true)

onMounted(async () => {
  try {
    metrics.value = await ragApi.getMetrics()
  } catch (error) {
    errorMessage.value = error?.message || '无法读取评测状态。'
  } finally {
    isLoading.value = false
  }
})
</script>

<template>
  <section class="panel metrics-panel">
    <p class="eyebrow">评测指标</p>
    <h2>最终系统评测状态</h2>
    <p v-if="isLoading">正在读取后端状态…</p>
    <p v-else-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    <template v-else-if="metrics?.available">
      <p>后端已提供最终系统评测结果。</p>
    </template>
    <template v-else>
      <p>{{ metrics?.reason || '最终系统评测尚未运行。' }}</p>
      <p class="muted">本页不会展示或推断未运行的 Recall、Claim Recall 或 Faithfulness 指标。</p>
    </template>
  </section>
</template>
