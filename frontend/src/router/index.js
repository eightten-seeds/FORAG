import { createRouter, createWebHistory } from 'vue-router'

import ChatView from '../views/ChatView.vue'
import MetricsView from '../views/MetricsView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'chat', component: ChatView },
    { path: '/metrics', name: 'metrics', component: MetricsView },
  ],
})
