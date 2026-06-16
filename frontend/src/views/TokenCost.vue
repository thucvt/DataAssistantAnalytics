<script setup>
import { ref, onMounted, computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js'
import api from '../api.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

const usage = ref(null)
const days = ref(30)
const loading = ref(false)

async function load() {
  loading.value = true
  try { usage.value = (await api.get(`/api/ai/usage?days=${days.value}`)).data }
  catch (e) { console.error(e) }
  finally { loading.value = false }
}

const chartData = computed(() => {
  if (!usage.value?.by_day?.length) return null
  return {
    labels: usage.value.by_day.map(d => d.date),
    datasets: [{
      label: 'Tổng token',
      data: usage.value.by_day.map(d => d.total_tokens),
      backgroundColor: 'rgba(212,175,55,0.45)',
      borderColor: '#d4af37',
      borderWidth: 1,
      borderRadius: 4,
    }]
  }
})

const chartOptions = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { labels: { color: '#9a9aa2' } } },
  scales: {
    x: { ticks: { color: '#9a9aa2' }, grid: { color: '#2a2a30' } },
    y: { ticks: { color: '#9a9aa2' }, grid: { color: '#2a2a30' } },
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h2>Chi phí AI</h2>
    <p class="sub">Theo dõi lượng token và ước tính chi phí API của mọi nhà cung cấp LLM.</p>

    <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px">
      <select v-model="days" @change="load" style="width:160px">
        <option :value="7">7 ngày qua</option>
        <option :value="30">30 ngày qua</option>
        <option :value="90">90 ngày qua</option>
      </select>
      <button class="btn btn-ghost" :disabled="loading" @click="load">
        <span v-if="loading" class="spinner"></span>
        Làm mới
      </button>
    </div>

    <div v-if="usage" class="grid3" style="margin-bottom:20px">
      <div class="card">
        <span class="label">Tổng lượt gọi</span>
        <div style="font-size:26px;font-weight:700;color:var(--gold-soft)">{{ usage.totals.requests.toLocaleString() }}</div>
      </div>
      <div class="card">
        <span class="label">Tổng token</span>
        <div style="font-size:26px;font-weight:700;color:var(--gold-soft)">{{ usage.totals.total_tokens.toLocaleString() }}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-top:4px">{{ usage.totals.prompt_tokens.toLocaleString() }} prompt + {{ usage.totals.completion_tokens.toLocaleString() }} completion</div>
      </div>
      <div class="card">
        <span class="label">Chi phí ước tính</span>
        <div style="font-size:26px;font-weight:700;color:var(--gold-soft)">${{ usage.totals.estimated_cost.toFixed(4) }}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-top:4px">USD</div>
      </div>
    </div>

    <!-- Biểu đồ token theo ngày -->
    <div class="card" style="margin-bottom:16px">
      <h3 style="margin-bottom:16px">Token theo ngày</h3>
      <div style="height:240px">
        <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
        <div v-else style="color:var(--text-dim);text-align:center;padding-top:80px">Chưa có dữ liệu</div>
      </div>
    </div>

    <!-- Phân bổ theo model -->
    <div class="card">
      <h3 style="margin-bottom:14px">Phân bổ theo Model</h3>
      <div v-if="usage?.by_model?.length">
        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <thead>
            <tr style="color:var(--text-dim);border-bottom:1px solid var(--border)">
              <th style="text-align:left;padding:8px 0">Model</th>
              <th style="text-align:right;padding:8px 0">Lượt gọi</th>
              <th style="text-align:right;padding:8px 0">Token</th>
              <th style="text-align:right;padding:8px 0">Chi phí (USD)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in usage.by_model" :key="m.model" style="border-bottom:1px solid var(--border)">
              <td style="padding:10px 0"><span class="tag">{{ m.model }}</span></td>
              <td style="text-align:right;padding:10px 0">{{ m.requests }}</td>
              <td style="text-align:right;padding:10px 0">{{ m.total_tokens.toLocaleString() }}</td>
              <td style="text-align:right;padding:10px 0;color:var(--gold-soft)">${{ m.cost.toFixed(6) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else style="color:var(--text-dim);font-size:13.5px">Chưa có lịch sử gọi LLM nào.</div>
    </div>
  </div>
</template>
