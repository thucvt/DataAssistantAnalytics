<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'
import { store } from '../store.js'

const router = useRouter()
const info = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    info.value = (await api.get('/api/info')).data
    if (!store.user) store.user = (await api.get('/api/auth/me')).data
  } catch (e) {
    if (e.response?.status === 401) router.push('/login')
    else error.value = e.message
  }
})

const NAV = [
  { to: '/analytics', icon: '◈', title: 'Analytics', desc: 'Báo cáo tổng hợp Meta Ads + Shopee, hỏi AI Agent' },
  { to: '/ai-settings', icon: '⚙', title: 'AI Settings', desc: 'Quản lý provider LLM và API keys (Super Admin)' },
  { to: '/token-cost', icon: '◎', title: 'Chi phí Token', desc: 'Theo dõi token đã dùng và chi phí theo ngày' },
  { to: '/data-sources', icon: '⬡', title: 'Data Sources', desc: 'Kết nối Facebook Ads và Shopee' },
]
</script>

<template>
  <div>
    <h2>Dashboard</h2>
    <p class="sub">Chào mừng{{ store.user ? ', ' + (store.user.full_name || store.user.email) : '' }}! Hệ thống đang hoạt động.</p>

    <div v-if="error" class="alert alert-err">{{ error }}</div>

    <div class="grid3" style="margin-bottom:24px">
      <div class="card">
        <span class="label">Trạng thái hệ thống</span>
        <div v-if="info" style="color:var(--ok);font-weight:600;font-size:15px">● Đang chạy</div>
        <div v-else style="color:var(--text-dim)"><span class="spinner"></span></div>
      </div>
      <div class="card">
        <span class="label">Phiên bản</span>
        <div style="font-size:15px;font-weight:600">Phase {{ info?.phase ?? '…' }}</div>
      </div>
      <div class="card">
        <span class="label">Quyền tài khoản</span>
        <span v-if="store.user?.is_superadmin" class="badge badge-ok">Super Admin</span>
        <span v-else-if="store.user" class="badge badge-warn">User</span>
        <span v-else class="spinner"></span>
      </div>
    </div>

    <div class="grid2">
      <router-link v-for="n in NAV" :key="n.to" :to="n.to" class="nav-card">
        <div class="nav-icon">{{ n.icon }}</div>
        <div>
          <div style="font-weight:600;margin-bottom:4px">{{ n.title }}</div>
          <div style="font-size:13px;color:var(--text-dim)">{{ n.desc }}</div>
        </div>
        <div style="margin-left:auto;color:var(--text-dim);font-size:20px">›</div>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.nav-card { display:flex; align-items:center; gap:16px; padding:18px 20px; background:var(--bg-card); border:1px solid var(--border); border-radius:var(--radius); transition:all .2s; }
.nav-card:hover { border-color:var(--gold-dim); background:rgba(212,175,55,0.04); }
.nav-icon { width:40px;height:40px;border-radius:10px;background:rgba(212,175,55,0.1);color:var(--gold-soft);display:grid;place-items:center;font-size:20px;flex-shrink:0; }
</style>
