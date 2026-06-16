<script setup>
import { ref, onMounted } from 'vue'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8080'
const info = ref(null)
const error = ref('')

onMounted(async () => {
  try {
    const res = await fetch(`${API}/api/info`)
    if (!res.ok) throw new Error('Backend chưa sẵn sàng')
    info.value = await res.json()
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <h1>Dashboard</h1>
  <p class="sub">Tổng quan hệ thống Data Assistant Analytics.</p>

  <div class="cards">
    <div class="card">
      <div class="k">Trạng thái Backend</div>
      <div class="v" v-if="info">● Đang chạy</div>
      <div class="v err" v-else-if="error">● {{ error }}</div>
      <div class="v" v-else>Đang kiểm tra…</div>
    </div>
    <div class="card">
      <div class="k">Phiên bản</div>
      <div class="v">Phase {{ info?.phase ?? '—' }}</div>
    </div>
    <div class="card">
      <div class="k">Ứng dụng</div>
      <div class="v">{{ info?.app_name ?? 'Data Assistant Analytics' }}</div>
    </div>
  </div>

  <p class="note">
    Các module AI Settings, Token Cost, Data Sources sẽ được bổ sung ở Phase 2–4 theo master plan.
  </p>
</template>

<style scoped>
h1 { font-size: 24px; }
.sub { color: var(--text-dim); margin: 6px 0 26px; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 12px; padding: 20px;
}
.card .k { color: var(--text-dim); font-size: 13px; margin-bottom: 8px; }
.card .v { font-size: 18px; color: var(--gold-soft); font-weight: 600; }
.card .v.err { color: #e5534b; }
.note { color: var(--text-dim); font-size: 13px; margin-top: 28px; }
</style>
