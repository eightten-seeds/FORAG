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
      <div class="brand-group">
        <RouterLink to="/" class="brand-link">
          <span class="brand-name">FORAG</span>
          <span class="brand-sub">户外功能服装养护知识助手</span>
        </RouterLink>
      </div>

      <div class="header-right">
        <div v-if="backendAvailable !== null" class="backend-state-badge" :class="{ unavailable: !backendAvailable }">
          <span class="status-dot"></span>
          <span>{{ backendAvailable ? '知识库在线' : '知识库离线' }}</span>
        </div>
        <nav aria-label="主导航" class="nav-links">
          <RouterLink to="/" class="nav-item">智能问答</RouterLink>
          <RouterLink to="/metrics" class="nav-item">系统评测</RouterLink>
        </nav>
      </div>
    </header>

    <main class="main-content">
      <RouterView />
    </main>

    <footer class="site-footer">
      <div class="footer-content">
        <span>FORAG · 户外功能服装智能养护垂直 RAG 系统</span>
        <span class="footer-dot">·</span>
        <span>基于 14 个品牌官方资料来源与 234 个规范知识切片</span>
        <span class="footer-dot">·</span>
        <span>多路混合检索与 Agent 可追溯生成</span>
      </div>
    </footer>
  </div>
</template>
