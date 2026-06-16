<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const connections = ref([])
const configs = ref({
  FACEBOOK_APP_ID: '', FACEBOOK_APP_SECRET: '', FACEBOOK_REDIRECT_URI: '', FACEBOOK_AD_ACCOUNT_ID: '',
  SHOPEE_PARTNER_ID: '', SHOPEE_PARTNER_KEY: '', SHOPEE_REDIRECT_URI: '',
  TIKTOK_APP_ID: '', TIKTOK_APP_SECRET: '', TIKTOK_REDIRECT_URI: '', TIKTOK_ADVERTISER_ID: '',
  GOOGLE_CLIENT_ID: '', GOOGLE_CLIENT_SECRET: '', GOOGLE_REDIRECT_URI: '',
  GOOGLE_ADS_CUSTOMER_ID: '', GOOGLE_ADS_DEVELOPER_TOKEN: '', GOOGLE_ADS_LOGIN_CUSTOMER_ID: '',
})
const msg = ref({ text: '', type: '' })

function showMsg(text, type = 'ok') { msg.value = { text, type }; setTimeout(() => msg.value.text = '', 5000) }

async function loadConnections() {
  try { connections.value = (await api.get('/api/oauth/connections')).data }
  catch (e) { console.error(e) }
}

async function saveConfig(key) {
  if (!configs.value[key]) return showMsg('Nhập giá trị trước', 'err')
  try {
    await api.put('/api/oauth/config', { key, value: configs.value[key] })
    showMsg(`Đã lưu ${key}`)
    configs.value[key] = ''
  } catch (e) { showMsg(e.response?.data?.detail || 'Lỗi khi lưu', 'err') }
}

async function oauthConnect(provider, label) {
  try {
    const r = await api.get(`/api/oauth/${provider}/authorize`)
    window.open(r.data.authorization_url, '_blank', 'width=640,height=720')
    showMsg(`Cửa sổ đăng nhập ${label} đã mở. Sau khi xác nhận, bấm Làm mới.`)
  } catch (e) { showMsg(e.response?.data?.detail || `Chưa cấu hình ${label} credentials`, 'err') }
}

function connStatus(provider) {
  return connections.value.find(c => c.provider === provider)
}

onMounted(loadConnections)
</script>

<template>
  <div>
    <h2>Data Sources</h2>
    <p class="sub">Kết nối nguồn dữ liệu. Nhập App credentials rồi bấm <strong>Lưu</strong>, sau đó bấm <strong>Kết nối</strong>.</p>

    <div v-if="msg.text" :class="['alert', msg.type === 'err' ? 'alert-err' : 'alert-ok']">{{ msg.text }}</div>

    <!-- ── Facebook / Meta Ads ── -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <span class="ds-icon fb-icon">f</span>
          <div>
            <h3>Facebook / Meta Ads</h3>
            <p>Chi phí quảng cáo từ Meta Ads Manager (Graph API v21)</p>
          </div>
        </div>
        <div class="ds-actions">
          <span :class="['badge', connStatus('facebook')?.connected ? 'badge-ok' : 'badge-warn']">
            {{ connStatus('facebook')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
          </span>
          <button class="btn btn-gold" @click="oauthConnect('facebook', 'Facebook')">Kết nối</button>
        </div>
      </div>
      <div class="grid2">
        <div class="field">
          <label>App ID</label>
          <div class="inline-save">
            <input v-model="configs.FACEBOOK_APP_ID" placeholder="12345678901234" />
            <button class="btn btn-ghost" @click="saveConfig('FACEBOOK_APP_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>App Secret</label>
          <div class="inline-save">
            <input v-model="configs.FACEBOOK_APP_SECRET" type="password" placeholder="••••••••" />
            <button class="btn btn-ghost" @click="saveConfig('FACEBOOK_APP_SECRET')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Ad Account ID (act_xxxxxxxxx)</label>
          <div class="inline-save">
            <input v-model="configs.FACEBOOK_AD_ACCOUNT_ID" placeholder="act_123456789" />
            <button class="btn btn-ghost" @click="saveConfig('FACEBOOK_AD_ACCOUNT_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Redirect URI</label>
          <div class="inline-save">
            <input v-model="configs.FACEBOOK_REDIRECT_URI" placeholder="http://localhost:8080/api/oauth/facebook/callback" />
            <button class="btn btn-ghost" @click="saveConfig('FACEBOOK_REDIRECT_URI')">Lưu</button>
          </div>
        </div>
      </div>
      <button class="btn-refresh" @click="loadConnections">↻ Làm mới trạng thái</button>
    </div>

    <!-- ── Shopee ── -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <span class="ds-icon shopee-icon">S</span>
          <div>
            <h3>Shopee</h3>
            <p>Doanh thu đơn hàng từ Shopee Open Platform (HMAC-SHA256)</p>
          </div>
        </div>
        <div class="ds-actions">
          <span :class="['badge', connStatus('shopee')?.connected ? 'badge-ok' : 'badge-warn']">
            {{ connStatus('shopee')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
          </span>
          <button class="btn btn-gold" @click="oauthConnect('shopee', 'Shopee')">Kết nối</button>
        </div>
      </div>
      <div class="grid2">
        <div class="field">
          <label>Partner ID</label>
          <div class="inline-save">
            <input v-model="configs.SHOPEE_PARTNER_ID" placeholder="1234567" />
            <button class="btn btn-ghost" @click="saveConfig('SHOPEE_PARTNER_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Partner Key</label>
          <div class="inline-save">
            <input v-model="configs.SHOPEE_PARTNER_KEY" type="password" placeholder="••••••••" />
            <button class="btn btn-ghost" @click="saveConfig('SHOPEE_PARTNER_KEY')">Lưu</button>
          </div>
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Redirect URI</label>
          <div class="inline-save">
            <input v-model="configs.SHOPEE_REDIRECT_URI" placeholder="http://localhost:8080/api/oauth/shopee/callback" />
            <button class="btn btn-ghost" @click="saveConfig('SHOPEE_REDIRECT_URI')">Lưu</button>
          </div>
        </div>
      </div>
      <button class="btn-refresh" @click="loadConnections">↻ Làm mới trạng thái</button>
    </div>

    <!-- ── TikTok Ads ── -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <span class="ds-icon tiktok-icon">T</span>
          <div>
            <h3>TikTok Ads</h3>
            <p>Chi phí quảng cáo từ TikTok Business API v1.3</p>
          </div>
        </div>
        <div class="ds-actions">
          <span :class="['badge', connStatus('tiktok')?.connected ? 'badge-ok' : 'badge-warn']">
            {{ connStatus('tiktok')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
          </span>
          <button class="btn btn-gold" @click="oauthConnect('tiktok', 'TikTok')">Kết nối</button>
        </div>
      </div>
      <div class="grid2">
        <div class="field">
          <label>App ID</label>
          <div class="inline-save">
            <input v-model="configs.TIKTOK_APP_ID" placeholder="7xxxxxxxxxxxxxxxxx" />
            <button class="btn btn-ghost" @click="saveConfig('TIKTOK_APP_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>App Secret</label>
          <div class="inline-save">
            <input v-model="configs.TIKTOK_APP_SECRET" type="password" placeholder="••••••••" />
            <button class="btn btn-ghost" @click="saveConfig('TIKTOK_APP_SECRET')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Advertiser ID (nếu biết trước)</label>
          <div class="inline-save">
            <input v-model="configs.TIKTOK_ADVERTISER_ID" placeholder="7xxxxxxxxxxxxxxxxx" />
            <button class="btn btn-ghost" @click="saveConfig('TIKTOK_ADVERTISER_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Redirect URI</label>
          <div class="inline-save">
            <input v-model="configs.TIKTOK_REDIRECT_URI" placeholder="http://localhost:8080/api/oauth/tiktok/callback" />
            <button class="btn btn-ghost" @click="saveConfig('TIKTOK_REDIRECT_URI')">Lưu</button>
          </div>
        </div>
      </div>
      <button class="btn-refresh" @click="loadConnections">↻ Làm mới trạng thái</button>
    </div>

    <!-- ── Google Ads Manager ── -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <span class="ds-icon google-icon">G</span>
          <div>
            <h3>Google Ads Manager</h3>
            <p>Chi phí quảng cáo từ Google Ads API v18 (GAQL)</p>
          </div>
        </div>
        <div class="ds-actions">
          <span :class="['badge', connStatus('google')?.connected ? 'badge-ok' : 'badge-warn']">
            {{ connStatus('google')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
          </span>
          <button class="btn btn-gold" @click="oauthConnect('google', 'Google')">Kết nối</button>
        </div>
      </div>
      <div class="grid2">
        <div class="field">
          <label>Client ID</label>
          <div class="inline-save">
            <input v-model="configs.GOOGLE_CLIENT_ID" placeholder="xxxx.apps.googleusercontent.com" />
            <button class="btn btn-ghost" @click="saveConfig('GOOGLE_CLIENT_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Client Secret</label>
          <div class="inline-save">
            <input v-model="configs.GOOGLE_CLIENT_SECRET" type="password" placeholder="GOCSPX-••••••••" />
            <button class="btn btn-ghost" @click="saveConfig('GOOGLE_CLIENT_SECRET')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Developer Token</label>
          <div class="inline-save">
            <input v-model="configs.GOOGLE_ADS_DEVELOPER_TOKEN" type="password" placeholder="••••••••" />
            <button class="btn btn-ghost" @click="saveConfig('GOOGLE_ADS_DEVELOPER_TOKEN')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Customer ID (không dấu gạch)</label>
          <div class="inline-save">
            <input v-model="configs.GOOGLE_ADS_CUSTOMER_ID" placeholder="1234567890" />
            <button class="btn btn-ghost" @click="saveConfig('GOOGLE_ADS_CUSTOMER_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Login Customer ID (MCC, nếu có)</label>
          <div class="inline-save">
            <input v-model="configs.GOOGLE_ADS_LOGIN_CUSTOMER_ID" placeholder="0987654321" />
            <button class="btn btn-ghost" @click="saveConfig('GOOGLE_ADS_LOGIN_CUSTOMER_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Redirect URI</label>
          <div class="inline-save">
            <input v-model="configs.GOOGLE_REDIRECT_URI" placeholder="http://localhost:8080/api/oauth/google/callback" />
            <button class="btn btn-ghost" @click="saveConfig('GOOGLE_REDIRECT_URI')">Lưu</button>
          </div>
        </div>
      </div>
      <button class="btn-refresh" @click="loadConnections">↻ Làm mới trạng thái</button>
    </div>
  </div>
</template>

<style scoped>
h2 { margin: 0 0 4px; font-size: 22px; }
.sub { color: var(--text-dim); font-size: 13.5px; margin: 0 0 24px; }

.ds-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 22px 24px;
  margin-bottom: 18px;
}
.ds-header {
  display: flex; align-items: flex-start;
  justify-content: space-between; gap: 16px;
  margin-bottom: 20px; flex-wrap: wrap;
}
.ds-title { display: flex; align-items: center; gap: 14px; }
.ds-title h3 { margin: 0 0 3px; font-size: 16px; }
.ds-title p { margin: 0; font-size: 12.5px; color: var(--text-dim); }
.ds-actions { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

.ds-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: grid; place-items: center;
  font-size: 18px; font-weight: 800; flex-shrink: 0;
}
.fb-icon     { background: #1877f2; color: #fff; }
.shopee-icon { background: #f53d2d; color: #fff; }
.tiktok-icon { background: #010101; color: #fff; border: 1px solid #333; }
.google-icon { background: linear-gradient(135deg,#4285f4 25%,#34a853 50%,#fbbc05 75%,#ea4335 100%); color: #fff; }

.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 18px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 12px; color: var(--text-dim); font-weight: 500; letter-spacing: .02em; }
.inline-save { display: flex; gap: 8px; }
.inline-save input { flex: 1; min-width: 0; }

.btn-refresh {
  background: none; border: none; color: var(--text-dim);
  font-size: 12.5px; cursor: pointer; margin-top: 14px;
  padding: 4px 0;
}
.btn-refresh:hover { color: var(--gold-soft); }

.badge { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge-ok   { background: rgba(52,211,153,.12); color: #34d399; }
.badge-warn { background: rgba(251,191,36,.1);  color: #fbbf24; }

.alert { padding: 12px 16px; border-radius: 9px; font-size: 13.5px; margin-bottom: 18px; }
.alert-ok  { background: rgba(52,211,153,.08); border: 1px solid rgba(52,211,153,.25); color: #34d399; }
.alert-err { background: rgba(239,68,68,.08);  border: 1px solid rgba(239,68,68,.3);   color: #f87171; }
</style>
