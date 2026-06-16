<script setup>
import { ref, computed } from 'vue'
import { Bar, Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend } from 'chart.js'
import api from '../api.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend)

const today = new Date().toISOString().slice(0, 10)
const thirtyAgo = new Date(Date.now() - 29 * 86400000).toISOString().slice(0, 10)
const since = ref(thirtyAgo)
const until = ref(today)
const chartPayload = ref(null)
const question = ref('')
const agentAnswer = ref('')
const agentSteps = ref(0)
const loadingChart = ref(false)
const loadingAgent = ref(false)
const loadingExport = ref(false)
const msgChart = ref('')
const msgAgent = ref('')

async function loadChart() {
  msgChart.value = ''
  loadingChart.value = true
  try {
    chartPayload.value = (await api.post('/api/analytics/report/chart', { since: since.value, until: until.value })).data
  } catch (e) {
    msgChart.value = e.response?.data?.detail || 'Lỗi tải dữ liệu. Hãy kết nối Data Sources trước.'
  } finally { loadingChart.value = false }
}

async function exportExcel() {
  loadingExport.value = true
  try {
    const r = (await api.post('/api/analytics/report/export', { since: since.value, until: until.value })).data
    const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'
    window.open(BASE + r.download_url, '_blank')
  } catch (e) {
    msgChart.value = e.response?.data?.detail || 'Lỗi xuất Excel'
  } finally { loadingExport.value = false }
}

async function askAgent() {
  if (!question.value.trim()) return
  msgAgent.value = ''
  agentAnswer.value = ''
  loadingAgent.value = true
  try {
    const r = (await api.post('/api/analytics/ask', { question: question.value })).data
    agentAnswer.value = r.answer
    agentSteps.value = r.steps
  } catch (e) {
    msgAgent.value = e.response?.data?.detail || 'Lỗi Agent. Hãy cấu hình AI Settings trước.'
  } finally { loadingAgent.value = false }
}

const barData = computed(() => {
  if (!chartPayload.value) return null
  const p = chartPayload.value
  return {
    labels: p.labels,
    datasets: [
      { label: 'Chi phí Ads', data: p.datasets[0].data, backgroundColor: 'rgba(229,83,75,0.5)', borderColor: '#e5534b', borderWidth: 1, borderRadius: 4 },
      { label: 'Doanh thu', data: p.datasets[1].data, backgroundColor: 'rgba(63,185,80,0.5)', borderColor: '#3fb950', borderWidth: 1, borderRadius: 4 },
    ]
  }
})

const lineData = computed(() => {
  if (!chartPayload.value) return null
  const p = chartPayload.value
  return {
    labels: p.labels,
    datasets: [{ label: 'Lợi nhuận', data: p.datasets[2].data, borderColor: '#d4af37', backgroundColor: 'rgba(212,175,55,0.1)', fill: true, tension: 0.3, pointRadius: 3 }]
  }
})

const chartOpts = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { labels: { color: '#9a9aa2', font: { size: 12 } } } },
  scales: { x: { ticks: { color: '#9a9aa2' }, grid: { color: '#2a2a30' } }, y: { ticks: { color: '#9a9aa2' }, grid: { color: '#2a2a30' } } }
}

const PROMPTS = [
  'Tổng chi phí Ads và doanh thu tháng này là bao nhiêu?',
  'So sánh chi phí Meta Ads vs TikTok Ads vs Google Ads',
  'ROAS của tôi đang ở mức nào? Có tốt không?',
  'Phân tích hiệu quả quảng cáo 30 ngày qua trên tất cả kênh',
]
</script>

<template>
  <div>
    <h2>Analytics</h2>
    <p class="sub">Phân tích tổng hợp: Meta Ads · Shopee · TikTok Ads · Google Ads Manager. Hỏi AI bằng ngôn ngữ tự nhiên.</p>

    <!-- Bộ lọc thời gian -->
    <div class="card" style="margin-bottom:16px">
      <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap">
        <div class="field" style="margin:0;flex:1;min-width:140px">
          <label>Từ ngày</label><input type="date" v-model="since" />
        </div>
        <div class="field" style="margin:0;flex:1;min-width:140px">
          <label>Đến ngày</label><input type="date" v-model="until" />
        </div>
        <button class="btn btn-gold" :disabled="loadingChart" @click="loadChart">
          <span v-if="loadingChart" class="spinner"></span>
          Xem báo cáo
        </button>
        <button class="btn btn-ghost" :disabled="loadingExport" @click="exportExcel">
          <span v-if="loadingExport" class="spinner"></span>
          Xuất Excel
        </button>
      </div>
      <div v-if="msgChart" class="alert alert-err" style="margin-top:12px;margin-bottom:0">{{ msgChart }}</div>
    </div>

    <!-- Summary cards -->
    <div v-if="chartPayload" class="grid3" style="margin-bottom:16px">
      <div class="card">
        <span class="label">Tổng chi phí Ads</span>
        <div style="font-size:22px;font-weight:700;color:var(--danger)">${{ chartPayload.summary.total_spend.toLocaleString() }}</div>
      </div>
      <div class="card">
        <span class="label">Tổng doanh thu</span>
        <div style="font-size:22px;font-weight:700;color:var(--ok)">{{ chartPayload.summary.total_revenue.toLocaleString() }}</div>
      </div>
      <div class="card">
        <span class="label">Lợi nhuận / ROAS</span>
        <div style="font-size:22px;font-weight:700;color:var(--gold-soft)">{{ chartPayload.summary.total_profit.toLocaleString() }}</div>
        <div style="font-size:13px;color:var(--text-dim);margin-top:4px">ROAS: {{ chartPayload.summary.avg_roas }}x</div>
      </div>
    </div>

    <!-- Charts -->
    <div v-if="chartPayload" class="grid2" style="margin-bottom:16px">
      <div class="card">
        <h3 style="margin-bottom:14px">Chi phí vs Doanh thu</h3>
        <div style="height:220px"><Bar :data="barData" :options="chartOpts" /></div>
      </div>
      <div class="card">
        <h3 style="margin-bottom:14px">Lợi nhuận theo ngày</h3>
        <div style="height:220px"><Line :data="lineData" :options="chartOpts" /></div>
      </div>
    </div>

    <!-- AI Agent chat -->
    <div class="card">
      <h3 style="margin-bottom:6px">Hỏi AI Agent</h3>
      <p style="color:var(--text-dim);font-size:13px;margin-bottom:14px">Agent tự động lấy dữ liệu từ Meta Ads, Shopee, TikTok Ads và Google Ads Manager rồi phân tích cho bạn.</p>

      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">
        <button v-for="p in PROMPTS" :key="p" class="btn btn-ghost" style="font-size:12.5px;padding:6px 13px" @click="question = p">{{ p }}</button>
      </div>

      <div style="display:flex;gap:10px;margin-bottom:12px">
        <textarea v-model="question" rows="2" placeholder="Ví dụ: Tháng này tôi tốn bao nhiêu tiền Ads? ROAS là bao nhiêu?" style="resize:vertical"></textarea>
        <button class="btn btn-gold" style="align-self:flex-end;white-space:nowrap;flex-shrink:0" :disabled="loadingAgent || !question.trim()" @click="askAgent">
          <span v-if="loadingAgent" class="spinner"></span>
          {{ loadingAgent ? 'Đang phân tích…' : 'Hỏi AI' }}
        </button>
      </div>

      <div v-if="msgAgent" class="alert alert-err">{{ msgAgent }}</div>
      <div v-if="agentAnswer" style="background:rgba(212,175,55,0.06);border:1px solid rgba(212,175,55,0.15);border-radius:10px;padding:16px;white-space:pre-wrap;font-size:14px;line-height:1.7">
        <div style="font-size:12px;color:var(--text-dim);margin-bottom:8px">AI Agent ({{ agentSteps }} bước)</div>
        {{ agentAnswer }}
      </div>
    </div>
  </div>
</template>
