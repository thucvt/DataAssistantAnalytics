<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const connections = ref([])
const msg = ref({ text: '', type: '' })

// Facebook form state
const fb = ref({ token: '', ad_account_id: '', saving: false, info: null })

function showMsg(text, type = 'ok') {
  msg.value = { text, type }
  setTimeout(() => msg.value.text = '', 6000)
}

async function loadConnections() {
  try { connections.value = (await api.get('/api/oauth/connections')).data }
  catch (e) { console.error(e) }
}

function conn(provider) {
  return connections.value.find(c => c.provider === provider)
}

// ── Facebook token paste ────────────────────────────────────────────────────
async function saveFbToken() {
  if (!fb.value.token.trim()) return showMsg('Vui lòng nhập Access Token', 'err')
  fb.value.saving = true
  fb.value.info = null
  try {
    const r = await api.post('/api/oauth/facebook/token', {
      access_token: fb.value.token.trim(),
      extra: fb.value.ad_account_id ? { ad_account_id: fb.value.ad_account_id.trim() } : {},
    })
    fb.value.info = r.data
    fb.value.token = ''
    await loadConnections()
    showMsg(r.data.long_lived
      ? `✓ Kết nối thành công với tài khoản "${r.data.name}" — Token đã gia hạn 60 ngày`
      : `✓ Kết nối thành công với tài khoản "${r.data.name}"`)
  } catch (e) {
    showMsg(e.response?.data?.detail || 'Token không hợp lệ', 'err')
  } finally {
    fb.value.saving = false
  }
}

// ── Các nền tảng khác — OAuth flow ─────────────────────────────────────────
async function oauthConnect(provider, label) {
  try {
    const r = await api.get(`/api/oauth/${provider}/authorize`)
    window.open(r.data.authorization_url, '_blank', 'width=640,height=720')
    showMsg(`Cửa sổ đăng nhập ${label} đã mở. Sau khi xác nhận, bấm Làm mới.`)
  } catch (e) {
    showMsg(e.response?.data?.detail || `Chưa cấu hình ${label} trong .env`, 'err')
  }
}

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

onMounted(loadConnections)
</script>

<template>
  <div>
    <h2>Data Sources</h2>
    <p class="sub">Kết nối nguồn dữ liệu quảng cáo và bán hàng của bạn.</p>

    <div v-if="msg.text" :class="['alert', msg.type === 'err' ? 'alert-err' : 'alert-ok']">{{ msg.text }}</div>

    <!-- ══ Facebook / Meta Ads ══════════════════════════════════════════════ -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <div class="ds-logo fb">f</div>
          <div>
            <div class="ds-name">Facebook / Meta Ads</div>
            <div class="ds-desc">Dán Access Token từ Graph API Explorer</div>
          </div>
        </div>
        <span :class="['badge', conn('facebook')?.connected ? 'badge-ok' : 'badge-off']">
          {{ conn('facebook')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
        </span>
      </div>

      <!-- Đã kết nối → hiển thị thông tin -->
      <div v-if="conn('facebook')?.connected" class="conn-info">
        <span class="conn-check">✓</span>
        <span>Đã kết nối</span>
        <span v-if="conn('facebook')?.expires_at" class="conn-exp">
          · hết hạn {{ fmtDate(conn('facebook').expires_at) }}
        </span>
      </div>

      <!-- Form nhập token -->
      <div class="token-form">
        <div class="steps">
          <span class="step">1</span>
          Vào
          <a href="https://developers.facebook.com/tools/explorer/" target="_blank" class="ext-link">
            Graph API Explorer ↗
          </a>
          → chọn app → tick quyền <code>ads_read</code> + <code>read_insights</code>
          → <strong>Generate Access Token</strong>
        </div>
        <div class="steps">
          <span class="step">2</span>
          Dán token vào đây:
        </div>
        <textarea
          v-model="fb.token"
          rows="3"
          placeholder="EAAxxxxxxxxxxxxxxxx..."
          style="font-family:monospace;font-size:13px;resize:vertical"
        />
        <div class="steps" style="margin-top:4px">
          <span class="step">3</span>
          Ad Account ID của bạn (tìm trong
          <a href="https://business.facebook.com/settings/ad-accounts" target="_blank" class="ext-link">Business Settings ↗</a>):
        </div>
        <div style="display:flex;gap:10px;align-items:center">
          <input v-model="fb.ad_account_id" placeholder="act_123456789" style="flex:1;font-family:monospace" />
          <button class="btn btn-gold" :disabled="fb.saving || !fb.token.trim()" @click="saveFbToken" style="white-space:nowrap">
            <span v-if="fb.saving" class="spinner" />
            {{ fb.saving ? 'Đang xác thực…' : 'Lưu & Xác thực' }}
          </button>
        </div>
        <div v-if="fb.info" class="verify-ok">
          ✓ Token hợp lệ · Tài khoản: <strong>{{ fb.info.name }}</strong>
          <span v-if="fb.info.long_lived"> · Đã gia hạn 60 ngày</span>
          <span v-if="fb.info.expires_at"> · Hết hạn: {{ fmtDate(fb.info.expires_at) }}</span>
        </div>
      </div>

      <div class="token-tip">
        Token sống 60 ngày (nếu được gia hạn). Khi gần hết hạn, lấy token mới từ Explorer và dán lại.
      </div>
    </div>

    <!-- ══ Shopee ═══════════════════════════════════════════════════════════ -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <div class="ds-logo shopee">S</div>
          <div>
            <div class="ds-name">Shopee</div>
            <div class="ds-desc">Doanh thu đơn hàng từ Shopee Open Platform</div>
          </div>
        </div>
        <span :class="['badge', conn('shopee')?.connected ? 'badge-ok' : 'badge-off']">
          {{ conn('shopee')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
        </span>
      </div>
      <div v-if="conn('shopee')?.connected" class="conn-info">
        <span class="conn-check">✓</span> Đã kết nối
        <span v-if="conn('shopee')?.expires_at" class="conn-exp">
          · hết hạn {{ fmtDate(conn('shopee').expires_at) }}
        </span>
      </div>
      <div style="margin-top:14px">
        <p style="font-size:13px;color:var(--text-dim);margin:0 0 10px">
          Yêu cầu cấu hình <code>SHOPEE_PARTNER_ID</code> + <code>SHOPEE_PARTNER_KEY</code> trong <code>docker-compose.yml</code> trước.
        </p>
        <button class="btn btn-gold" @click="oauthConnect('shopee', 'Shopee')">Kết nối Shopee</button>
      </div>
    </div>

    <!-- ══ TikTok Ads ════════════════════════════════════════════════════════ -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <div class="ds-logo tiktok">T</div>
          <div>
            <div class="ds-name">TikTok Ads</div>
            <div class="ds-desc">Chi phí quảng cáo từ TikTok Business API v1.3</div>
          </div>
        </div>
        <span :class="['badge', conn('tiktok')?.connected ? 'badge-ok' : 'badge-off']">
          {{ conn('tiktok')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
        </span>
      </div>
      <div v-if="conn('tiktok')?.connected" class="conn-info">
        <span class="conn-check">✓</span> Đã kết nối
      </div>
      <div style="margin-top:14px">
        <p style="font-size:13px;color:var(--text-dim);margin:0 0 10px">
          Yêu cầu cấu hình <code>TIKTOK_APP_ID</code> + <code>TIKTOK_APP_SECRET</code> trong <code>docker-compose.yml</code> trước.
        </p>
        <button class="btn btn-gold" @click="oauthConnect('tiktok', 'TikTok')">Kết nối TikTok</button>
      </div>
    </div>

    <!-- ══ Google Ads ════════════════════════════════════════════════════════ -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <div class="ds-logo google">G</div>
          <div>
            <div class="ds-name">Google Ads Manager</div>
            <div class="ds-desc">Chi phí quảng cáo từ Google Ads API v18 (GAQL)</div>
          </div>
        </div>
        <span :class="['badge', conn('google')?.connected ? 'badge-ok' : 'badge-off']">
          {{ conn('google')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
        </span>
      </div>
      <div v-if="conn('google')?.connected" class="conn-info">
        <span class="conn-check">✓</span> Đã kết nối
        <span v-if="conn('google')?.expires_at" class="conn-exp">
          · hết hạn {{ fmtDate(conn('google').expires_at) }}
        </span>
      </div>
      <div style="margin-top:14px">
        <p style="font-size:13px;color:var(--text-dim);margin:0 0 10px">
          Yêu cầu cấu hình <code>GOOGLE_CLIENT_ID</code> + <code>GOOGLE_CLIENT_SECRET</code> + <code>GOOGLE_ADS_DEVELOPER_TOKEN</code> trong <code>docker-compose.yml</code> trước.
        </p>
        <button class="btn btn-gold" @click="oauthConnect('google', 'Google')">Kết nối Google Ads</button>
      </div>
    </div>

    <button class="btn-refresh" @click="loadConnections">↻ Làm mới trạng thái</button>
  </div>
</template>

<style scoped>
h2 { margin: 0 0 4px; font-size: 22px; }
.sub { color: var(--text-dim); font-size: 13.5px; margin: 0 0 24px; }

.ds-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 14px; padding: 22px 24px; margin-bottom: 16px;
}
.ds-header {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 16px; flex-wrap: wrap;
}
.ds-title { display: flex; align-items: center; gap: 14px; }
.ds-name { font-size: 16px; font-weight: 700; margin-bottom: 2px; }
.ds-desc { font-size: 12.5px; color: var(--text-dim); }

.ds-logo {
  width: 44px; height: 44px; border-radius: 11px;
  display: grid; place-items: center;
  font-size: 20px; font-weight: 800; flex-shrink: 0;
}
.fb      { background: #1877f2; color: #fff; }
.shopee  { background: #f53d2d; color: #fff; }
.tiktok  { background: #111; color: #fff; border: 1px solid #333; font-size: 17px; }
.google  { background: linear-gradient(135deg,#4285f4 25%,#34a853 50%,#fbbc05 75%,#ea4335 100%); color: #fff; }

.conn-info {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--text-dim); margin-bottom: 14px;
}
.conn-check { color: #34d399; font-size: 15px; }
.conn-exp { color: #6b7280; }

/* Token form */
.token-form { display: flex; flex-direction: column; gap: 10px; }
.steps {
  font-size: 13px; color: var(--text-dim);
  display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
}
.step {
  background: rgba(212,175,55,.15); color: var(--gold-soft);
  border-radius: 50%; width: 20px; height: 20px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.ext-link { color: var(--gold-soft); text-decoration: underline; text-underline-offset: 2px; }
.ext-link:hover { color: var(--gold); }

.verify-ok {
  font-size: 13px; color: #34d399;
  background: rgba(52,211,153,.07); border: 1px solid rgba(52,211,153,.2);
  border-radius: 8px; padding: 10px 14px;
}
.token-tip {
  margin-top: 12px; font-size: 12px; color: var(--text-dim);
  padding: 8px 12px; background: rgba(255,255,255,.03);
  border-radius: 7px; border: 1px solid var(--border);
}

.badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.badge-ok  { background: rgba(52,211,153,.12); color: #34d399; }
.badge-off { background: rgba(156,163,175,.08); color: #6b7280; }

.btn-refresh {
  background: none; border: none; color: var(--text-dim);
  font-size: 13px; cursor: pointer; margin-top: 4px; padding: 0;
}
.btn-refresh:hover { color: var(--gold-soft); }

code {
  color: var(--gold-soft); background: rgba(212,175,55,.1);
  padding: 1px 5px; border-radius: 4px; font-size: 12px;
}
.alert { padding: 12px 16px; border-radius: 9px; font-size: 13.5px; margin-bottom: 18px; }
.alert-ok  { background: rgba(52,211,153,.08); border: 1px solid rgba(52,211,153,.25); color: #34d399; }
.alert-err { background: rgba(239,68,68,.08);  border: 1px solid rgba(239,68,68,.3);   color: #f87171; }
</style>
