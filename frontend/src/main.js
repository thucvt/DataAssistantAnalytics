import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Login from './views/Login.vue'
import Dashboard from './views/Dashboard.vue'
import AISettings from './views/AISettings.vue'
import TokenCost from './views/TokenCost.vue'
import DataSources from './views/DataSources.vue'
import Analytics from './views/Analytics.vue'
import './style.css'
import { store } from './store.js'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login, meta: { public: true } },
    { path: '/', component: Dashboard },
    { path: '/ai-settings', component: AISettings },
    { path: '/token-cost', component: TokenCost },
    { path: '/data-sources', component: DataSources },
    { path: '/analytics', component: Analytics },
  ],
})

router.beforeEach((to) => {
  if (!to.meta.public && !store.isLoggedIn) return '/login'
})

createApp(App).use(router).mount('#app')
