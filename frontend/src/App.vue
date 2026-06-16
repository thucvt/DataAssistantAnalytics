<script setup>
import { useRouter, useRoute } from 'vue-router'
import { store } from './store.js'

const router = useRouter()
const route = useRoute()

function logout() {
  store.logout()
  router.push('/login')
}
</script>

<template>
  <!-- Trang login không có sidebar -->
  <div v-if="route.path === '/login'">
    <router-view />
  </div>

  <div v-else class="layout">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">DA</span>
        <span>Data <b>Assistant</b></span>
      </div>

      <nav>
        <router-link to="/"><span class="icon">▦</span> Dashboard</router-link>
        <div class="nav-section">Analytics</div>
        <router-link to="/analytics"><span class="icon">◈</span> Analytics</router-link>
        <div class="nav-section">AI</div>
        <router-link to="/ai-settings"><span class="icon">⚙</span> AI Settings</router-link>
        <router-link to="/token-cost"><span class="icon">◎</span> Chi phí Token</router-link>
        <div class="nav-section">Nguồn dữ liệu</div>
        <router-link to="/data-sources"><span class="icon">⬡</span> Data Sources</router-link>
      </nav>

      <div class="sidebar-footer">
        <div v-if="store.user" class="user-info">
          <div class="user-avatar">{{ (store.user.full_name || store.user.email)[0].toUpperCase() }}</div>
          <div>
            <div style="font-size:13px;font-weight:600;color:var(--text)">{{ store.user.full_name || 'Admin' }}</div>
            <div style="font-size:11px;color:var(--text-dim)">{{ store.user.email }}</div>
          </div>
        </div>
        <button class="btn btn-ghost" style="width:100%;margin-top:10px;justify-content:center;font-size:13px" @click="logout">Đăng xuất</button>
      </div>
    </aside>

    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; }
.sidebar {
  width: 230px; background: var(--bg-card);
  border-right: 1px solid var(--border);
  padding: 20px 14px; display: flex; flex-direction: column;
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
.brand { display: flex; align-items: center; gap: 10px; font-size: 15px; margin-bottom: 24px; }
.brand .logo { width: 33px; height: 33px; border-radius: 9px; background: linear-gradient(145deg, var(--gold-soft), var(--gold)); color: #1a1a1a; font-weight: 800; display: grid; place-items: center; font-size: 14px; }
.nav-section { font-size: 10.5px; font-weight: 700; color: var(--text-dim); letter-spacing: .08em; text-transform: uppercase; padding: 14px 10px 5px; }
nav { display: flex; flex-direction: column; flex: 1; }
nav a { padding: 9px 11px; border-radius: 8px; color: var(--text-dim); font-size: 13.5px; display: flex; align-items: center; gap: 8px; transition: all .15s; }
nav a:hover { background: rgba(255,255,255,0.04); color: var(--text); }
nav a.router-link-active { background: rgba(212,175,55,0.1); color: var(--gold-soft); }
.icon { font-size: 14px; width: 18px; text-align: center; flex-shrink: 0; }
.sidebar-footer { margin-top: auto; padding-top: 16px; border-top: 1px solid var(--border); }
.user-info { display: flex; align-items: center; gap: 10px; }
.user-avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--gold-dim); color: #fff; font-weight: 700; font-size: 13px; display: grid; place-items: center; flex-shrink: 0; }
.content { flex: 1; padding: 30px 36px; overflow-y: auto; min-width: 0; }
</style>
