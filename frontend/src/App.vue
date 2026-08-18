<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import { ragApi } from './api/rag.js'

const backendAvailable = ref(null)

onMounted(async () => {
  try {
    await ragApi.getHealth()
    backendAvailable.value = true
  } catch {
    backendAvailable.value = false
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div>
        <p class="eyebrow">FORAG · 可追溯护理问答</p>
        <h1>户外功能服装智能养护问答系统</h1>
      </div>
      <div class="header-actions">
        <p v-if="backendAvailable !== null" class="backend-state" :class="{ unavailable: !backendAvailable }">
          {{ backendAvailable ? '后端可用' : '后端暂不可用' }}
        </p>
        <nav aria-label="主导航">
          <RouterLink to="/">问答</RouterLink>
          <RouterLink to="/metrics">评测指标</RouterLink>
        </nav>
      </div>
    </header>

    <main>
      <RouterView />
    </main>
  </div>
</template>
