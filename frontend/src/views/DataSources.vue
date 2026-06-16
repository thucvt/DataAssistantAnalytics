<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const connections = ref([])
const msg = ref({ text: '', type: '' })

function showMsg(text, type = 'ok') {
  msg.value = { text, type }
  setTimeout(() => msg.value.text = '', 5000)
}

async function loadConnections() {
  try { connections.value = (await api.get('/api/oauth/connections')).data }
  catch (e) { console.error(e) }
}

async function connect(provider, label) {
  try {
    const r = await api.get(`/api/oauth/${provider}/authorize`)
    window.open(r.data.authorization_url, '_blank', 'width=640,height=720')
    showMsg(`Cửa sổ đăng nhập ${label} đã mở. Sau khi xác nhận, bấm Làm mới.`)
  } catch (e) {
    showMsg(e.response?.data?.detail || `Lỗi kết nối ${label}. Kiểm tra cấu hình .env`, 'err')
  }
}

function conn(provider) {
  return connections.value.find(c => c.provider === provider)
}

onMounted(loadConnections)
</script>

<template>
  <div>
    <h2>Data Sources</h2>
    <p class="sub">Kết nối nguồn dữ liệu quảng cáo và bán hàng. Bấm <strong>Kết nối</strong> để ủy quyền qua OAuth.</p>

    <div v-if="msg.text" :class="['alert', msg.type === 'err' ? 'alert-err' : 'alert-ok']">{{ msg.text }}</div>

    <div class="ds-grid">

      <!-- Facebook / Meta Ads -->
      <div class="ds-card">
        <div class="ds-logo fb">f</div>
        <div class="ds-info">
          <div class="ds-name">Facebook / Meta Ads</div>
          <div class="ds-desc">Chi phí quảng cáo qua Graph API v25</div>
          <span :class="['badge', conn('facebook')?.connected ? 'badge-ok' : 'badge-off']">
            {{ conn('facebook')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
          </span>
        </div>
        <button class="btn btn-gold ds-btn" @click="connect('facebook', 'Facebook')">
          Kết nối
        </button>
      </div>

      <!-- Shopee -->
      <div class="ds-card">
        <div class="ds-logo shopee">S</div>
        <div class="ds-info">
          <div class="ds-name">Shopee</div>
          <div class="ds-desc">Doanh thu qua Shopee Open Platform</div>
          <span :class="['badge', conn('shopee')?.connected ? 'badge-ok' : 'badge-off']">
            {{ conn('shopee')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
          </span>
        </div>
        <button class="btn btn-gold ds-btn" @click="connect('shopee', 'Shopee')">
          Kết nối
        </button>
      </div>

      <!-- TikTok Ads -->
      <div class="ds-card">
        <div class="ds-logo tiktok">T</div>
        <div class="ds-info">
          <div class="ds-name">TikTok Ads</div>
          <div class="ds-desc">Chi phí quảng cáo qua TikTok Business API v1.3</div>
          <span :class="['badge', conn('tiktok')?.connected ? 'badge-ok' : 'badge-off']">
            {{ conn('tiktok')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
          </span>
        </div>
        <button class="btn btn-gold ds-btn" @click="connect('tiktok', 'TikTok')">
          Kết nối
        </button>
      </div>

      <!-- Google Ads -->
      <div class="ds-card">
        <div class="ds-logo google">G</div>
        <div class="ds-info">
          <div class="ds-name">Google Ads Manager</div>
          <div class="ds-desc">Chi phí quảng cáo qua Google Ads API v18 (GAQL)</div>
          <span :class="['badge', conn('google')?.connected ? 'badge-ok' : 'badge-off']">
            {{ conn('google')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
          </span>
        </div>
        <button class="btn btn-gold ds-btn" @click="connect('google', 'Google')">
          Kết nối
        </button>
      </div>

    </div>

    <button class="btn-refresh" @click="loadConnections">↻ Làm mới trạng thái</button>

    <div class="hint-box">
      <strong>Lưu ý:</strong> Để nút Kết nối hoạt động, admin cần điền credentials của từng nền tảng vào file
      <code>docker-compose.yml</code> (các biến <code>FACEBOOK_APP_ID</code>, <code>TIKTOK_APP_ID</code>…)
      rồi khởi động lại container.
    </div>
  </div>
</template>

<style scoped>
h2 { margin: 0 0 4px; font-size: 22px; }
.sub { color: var(--text-dim); font-size: 13.5px; margin: 0 0 24px; }

.ds-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 800px) { .ds-grid { grid-template-columns: 1fr; } }

.ds-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 14px; padding: 22px 20px;
  display: flex; align-items: center; gap: 16px;
  transition: border-color .2s;
}
.ds-card:hover { border-color: rgba(212,175,55,.3); }

.ds-logo {
  width: 48px; height: 48px; border-radius: 12px;
  display: grid; place-items: center;
  font-size: 22px; font-weight: 800; flex-shrink: 0;
}
.fb      { background: #1877f2; color: #fff; }
.shopee  { background: #f53d2d; color: #fff; }
.tiktok  { background: #111;    color: #fff; border: 1px solid #333; font-size: 18px; }
.google  { background: linear-gradient(135deg,#4285f4 25%,#34a853 50%,#fbbc05 75%,#ea4335 100%); color: #fff; }

.ds-info { flex: 1; min-width: 0; }
.ds-name { font-size: 15px; font-weight: 700; margin-bottom: 3px; }
.ds-desc { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }

.ds-btn { white-space: nowrap; flex-shrink: 0; }

.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11.5px; font-weight: 600; }
.badge-ok  { background: rgba(52,211,153,.12); color: #34d399; }
.badge-off { background: rgba(156,163,175,.1);  color: #6b7280; }

.btn-refresh {
  background: none; border: none; color: var(--text-dim);
  font-size: 13px; cursor: pointer; margin-top: 16px; padding: 0;
}
.btn-refresh:hover { color: var(--gold-soft); }

.hint-box {
  margin-top: 20px; padding: 14px 18px;
  background: rgba(212,175,55,.06); border: 1px solid rgba(212,175,55,.18);
  border-radius: 10px; font-size: 13px; color: var(--text-dim); line-height: 1.6;
}
.hint-box code { color: var(--gold-soft); background: rgba(212,175,55,.1); padding: 1px 5px; border-radius: 4px; }

.alert { padding: 12px 16px; border-radius: 9px; font-size: 13.5px; margin-bottom: 18px; }
.alert-ok  { background: rgba(52,211,153,.08); border: 1px solid rgba(52,211,153,.25); color: #34d399; }
.alert-err { background: rgba(239,68,68,.08);  border: 1px solid rgba(239,68,68,.3);   color: #f87171; }
</style>
