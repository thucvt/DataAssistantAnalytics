<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const connections = ref([])
const msg = ref({ text: '', type: '' })

const fb = ref({ token: '', saving: false, info: null, selectedAccount: '', savingAccount: false })
const shopee  = ref({ token: '', shop_id: '',        saving: false, info: null })
const tiktok  = ref({ token: '', advertiser_id: '',  saving: false, info: null })

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

// Facebook: paste token → nhận danh sách ad accounts
async function fbPasteToken() {
  if (!fb.value.token.trim()) return showMsg('Vui lòng nhập Access Token', 'err')
  fb.value.saving = true
  fb.value.info = null
  try {
    const r = await api.post('/api/oauth/facebook/token', { access_token: fb.value.token.trim(), extra: {} })
    fb.value.info = r.data
    fb.value.token = ''
    fb.value.selectedAccount = r.data.ad_accounts?.[0]?.id || ''
    await loadConnections()
  } catch (e) {
    showMsg(e.response?.data?.detail || 'Token Facebook không hợp lệ', 'err')
  } finally {
    fb.value.saving = false
  }
}

// Facebook: xác nhận chọn ad account
async function fbSaveAccount() {
  if (!fb.value.selectedAccount) return showMsg('Vui lòng chọn Ad Account', 'err')
  fb.value.savingAccount = true
  try {
    await api.put('/api/oauth/facebook/adaccount', { ad_account_id: fb.value.selectedAccount }  )
    const chosen = fb.value.info.ad_accounts.find(a => a.id === fb.value.selectedAccount)
    showMsg(`✓ Đã chọn Ad Account: ${chosen?.name || fb.value.selectedAccount}`)
  } catch (e) {
    showMsg(e.response?.data?.detail || 'Lỗi lưu Ad Account', 'err')
  } finally {
    fb.value.savingAccount = false
  }
}

// Generic paste-token save (Shopee, TikTok)
async function pasteToken(provider, state, extraKey, label) {
  if (!state.token.trim()) return showMsg('Vui lòng nhập Access Token', 'err')
  const keyLabel = extraKey === 'shop_id' ? 'Shop ID' : 'Advertiser ID'
  if (!state[extraKey]?.trim()) return showMsg(`Vui lòng nhập ${keyLabel}`, 'err')
  state.saving = true
  state.info = null
  try {
    const r = await api.post(`/api/oauth/${provider}/token`, {
      access_token: state.token.trim(),
      extra: { [extraKey]: state[extraKey].trim() },
    })
    state.info = r.data
    state.token = ''
    await loadConnections()
    showMsg(`✓ Kết nối ${label} thành công · Tài khoản: "${r.data.name}"`)
  } catch (e) {
    showMsg(e.response?.data?.detail || `Token ${label} không hợp lệ`, 'err')
  } finally {
    state.saving = false
  }
}

async function oauthConnect(provider, label) {
  try {
    const r = await api.get(`/api/oauth/${provider}/authorize`)
    window.open(r.data.authorization_url, '_blank', 'width=640,height=720')
    showMsg(`Cửa sổ ${label} đã mở. Sau khi xác nhận, bấm Làm mới.`)
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
    <p class="sub">Kết nối nguồn dữ liệu — dán Access Token từ trang quản trị của từng nền tảng.</p>

    <div v-if="msg.text" :class="['alert', msg.type === 'err' ? 'alert-err' : 'alert-ok']">{{ msg.text }}</div>

    <!-- ══ Facebook / Meta Ads ══════════════════════════════════════════════ -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <div class="ds-logo fb">f</div>
          <div>
            <div class="ds-name">Facebook / Meta Ads</div>
            <div class="ds-desc">Graph API v25 · Token từ Graph API Explorer</div>
          </div>
        </div>
        <span :class="['badge', conn('facebook')?.connected ? 'badge-ok' : 'badge-off']">
          {{ conn('facebook')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
        </span>
      </div>

      <div v-if="conn('facebook')?.connected" class="conn-info">
        <span class="conn-check">✓</span> Đang hoạt động
        <span v-if="conn('facebook')?.expires_at" class="conn-exp"> · hết hạn {{ fmtDate(conn('facebook').expires_at) }}</span>
      </div>

      <div class="token-form">
        <div class="step-row">
          <span class="step">1</span>
          Vào <a href="https://developers.facebook.com/tools/explorer/" target="_blank" class="ext-link">Graph API Explorer ↗</a>
          → chọn app → tick <code>ads_read</code> + <code>read_insights</code> → <strong>Generate Access Token</strong>
        </div>
        <div class="step-row"><span class="step">2</span> Dán token:</div>
        <div class="inline-row">
          <textarea v-model="fb.token" rows="2" placeholder="EAAxxxxxxxxxxxxxxxx..." class="mono" style="flex:1;resize:none" />
          <button class="btn btn-gold" style="align-self:stretch" :disabled="fb.saving || !fb.token.trim()" @click="fbPasteToken">
            <span v-if="fb.saving" class="spinner" />{{ fb.saving ? 'Đang xác thực…' : 'Xác thực' }}
          </button>
        </div>

        <!-- Bước 3: dropdown chọn ad account — hiện sau khi xác thực -->
        <template v-if="fb.info">
          <div class="verify-ok" style="margin-bottom:4px">
            ✓ Xin chào <strong>{{ fb.info.name }}</strong>
            <span v-if="fb.info.long_lived"> · Token gia hạn 60 ngày</span>
            <span v-if="fb.info.expires_at"> · Hết hạn: {{ fmtDate(fb.info.expires_at) }}</span>
          </div>
          <div class="step-row"><span class="step">3</span> Chọn tài khoản quảng cáo:</div>
          <div class="inline-row">
            <select v-model="fb.selectedAccount" class="acct-select">
              <option value="" disabled>-- Chọn Ad Account --</option>
              <option v-for="a in fb.info.ad_accounts" :key="a.id" :value="a.id">
                {{ a.name }} ({{ a.id }}) · {{ a.currency }}
              </option>
            </select>
            <button class="btn btn-gold" :disabled="fb.savingAccount || !fb.selectedAccount" @click="fbSaveAccount">
              <span v-if="fb.savingAccount" class="spinner" />{{ fb.savingAccount ? 'Đang lưu…' : 'Xác nhận' }}
            </button>
          </div>
          <p v-if="!fb.info.ad_accounts?.length" style="font-size:12.5px;color:#f87171;margin:0">
            Không tìm thấy Ad Account. Token cần có quyền <code>ads_read</code>.
          </p>
        </template>
      </div>
      <div class="tip">Token sống 60 ngày (nếu gia hạn tự động). Khi hết hạn, lấy token mới từ Explorer và dán lại.</div>
    </div>

    <!-- ══ Shopee ═══════════════════════════════════════════════════════════ -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <div class="ds-logo shopee">S</div>
          <div>
            <div class="ds-name">Shopee</div>
            <div class="ds-desc">Shopee Open Platform · Token từ Partner Portal</div>
          </div>
        </div>
        <span :class="['badge', conn('shopee')?.connected ? 'badge-ok' : 'badge-off']">
          {{ conn('shopee')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
        </span>
      </div>

      <div v-if="conn('shopee')?.connected" class="conn-info">
        <span class="conn-check">✓</span> Đang hoạt động
        <span v-if="conn('shopee')?.expires_at" class="conn-exp"> · hết hạn {{ fmtDate(conn('shopee').expires_at) }}</span>
      </div>

      <div class="token-form">
        <div class="step-row">
          <span class="step">1</span>
          Vào <a href="https://open.shopee.com/merchant-support/intro" target="_blank" class="ext-link">Shopee Partner Portal ↗</a>
          → Test Shop → <strong>Get Token</strong> (hoặc lấy từ OAuth callback sau khi authorize)
        </div>
        <div class="step-row"><span class="step">2</span> Dán Access Token:</div>
        <textarea v-model="shopee.token" rows="3" placeholder="access_token từ Shopee..." class="mono" />
        <div class="step-row">
          <span class="step">3</span>
          Shop ID (hiển thị trong Partner Portal → Test Shop):
        </div>
        <div class="inline-row">
          <input v-model="shopee.shop_id" placeholder="12345678" class="mono" />
          <button class="btn btn-gold" :disabled="shopee.saving || !shopee.token.trim()" @click="pasteToken('shopee', shopee, 'shop_id', 'Shopee')">
            <span v-if="shopee.saving" class="spinner" />{{ shopee.saving ? 'Đang xác thực…' : 'Lưu & Xác thực' }}
          </button>
        </div>
        <div v-if="shopee.info" class="verify-ok">
          ✓ Shop: <strong>{{ shopee.info.name }}</strong>
        </div>
      </div>
      <div class="tip">
        Cần cấu hình <code>SHOPEE_PARTNER_ID</code> + <code>SHOPEE_PARTNER_KEY</code> trong <code>docker-compose.yml</code> để xác thực chữ ký.
      </div>
    </div>

    <!-- ══ TikTok Ads ════════════════════════════════════════════════════════ -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <div class="ds-logo tiktok">T</div>
          <div>
            <div class="ds-name">TikTok Ads</div>
            <div class="ds-desc">Business API v1.3 · Token từ TikTok Business Center</div>
          </div>
        </div>
        <span :class="['badge', conn('tiktok')?.connected ? 'badge-ok' : 'badge-off']">
          {{ conn('tiktok')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
        </span>
      </div>

      <div v-if="conn('tiktok')?.connected" class="conn-info">
        <span class="conn-check">✓</span> Đang hoạt động
      </div>

      <div class="token-form">
        <div class="step-row">
          <span class="step">1</span>
          Vào <a href="https://business-api.tiktok.com/portal/docs" target="_blank" class="ext-link">TikTok Business API Portal ↗</a>
          → App Management → chọn app → <strong>Authorization</strong> → lấy Access Token
        </div>
        <div class="step-row"><span class="step">2</span> Dán Access Token:</div>
        <textarea v-model="tiktok.token" rows="3" placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" class="mono" />
        <div class="step-row">
          <span class="step">3</span>
          Advertiser ID (TikTok Ads Manager → tên tài khoản ở góc trên):
        </div>
        <div class="inline-row">
          <input v-model="tiktok.advertiser_id" placeholder="7xxxxxxxxxxxxxxxxx" class="mono" />
          <button class="btn btn-gold" :disabled="tiktok.saving || !tiktok.token.trim()" @click="pasteToken('tiktok', tiktok, 'advertiser_id', 'TikTok')">
            <span v-if="tiktok.saving" class="spinner" />{{ tiktok.saving ? 'Đang xác thực…' : 'Lưu & Xác thực' }}
          </button>
        </div>
        <div v-if="tiktok.info" class="verify-ok">
          ✓ Advertiser: <strong>{{ tiktok.info.name }}</strong>
        </div>
      </div>
      <div class="tip">Token TikTok không hết hạn theo ngày — hết hạn khi bị thu hồi hoặc app bị xoá.</div>
    </div>

    <!-- ══ Google Ads ════════════════════════════════════════════════════════ -->
    <div class="ds-card">
      <div class="ds-header">
        <div class="ds-title">
          <div class="ds-logo google">G</div>
          <div>
            <div class="ds-name">Google Ads Manager</div>
            <div class="ds-desc">Google Ads API v18 (GAQL) · OAuth tự động</div>
          </div>
        </div>
        <span :class="['badge', conn('google')?.connected ? 'badge-ok' : 'badge-off']">
          {{ conn('google')?.connected ? '● Đã kết nối' : '○ Chưa kết nối' }}
        </span>
      </div>
      <div v-if="conn('google')?.connected" class="conn-info">
        <span class="conn-check">✓</span> Đang hoạt động
        <span v-if="conn('google')?.expires_at" class="conn-exp"> · hết hạn {{ fmtDate(conn('google').expires_at) }}</span>
      </div>
      <div style="margin-top:14px">
        <p style="font-size:13px;color:var(--text-dim);margin:0 0 12px;line-height:1.6">
          Cần cấu hình <code>GOOGLE_CLIENT_ID</code> · <code>GOOGLE_CLIENT_SECRET</code> · <code>GOOGLE_ADS_DEVELOPER_TOKEN</code>
          · <code>GOOGLE_ADS_CUSTOMER_ID</code> trong <code>docker-compose.yml</code> trước.
          Sau đó bấm Kết nối để hoàn tất OAuth — app tự lấy <strong>refresh_token</strong> (không hết hạn).
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
  transition: border-color .2s;
}
.ds-card:hover { border-color: rgba(212,175,55,.25); }

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
.fb     { background: #1877f2; color: #fff; }
.shopee { background: #f53d2d; color: #fff; }
.tiktok { background: #111; color: #fff; border: 1px solid #333; font-size: 17px; }
.google { background: linear-gradient(135deg,#4285f4 25%,#34a853 50%,#fbbc05 75%,#ea4335); color: #fff; }

.conn-info {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; color: var(--text-dim); margin-bottom: 16px;
}
.conn-check { color: #34d399; font-size: 15px; }
.conn-exp   { color: #6b7280; }

.token-form { display: flex; flex-direction: column; gap: 10px; }

.step-row {
  display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
  font-size: 13px; color: var(--text-dim); line-height: 1.6;
}
.step {
  background: rgba(212,175,55,.15); color: var(--gold-soft);
  border-radius: 50%; width: 20px; height: 20px; min-width: 20px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
}
.ext-link { color: var(--gold-soft); text-decoration: underline; text-underline-offset: 2px; }

.mono { font-family: monospace; font-size: 12.5px; }
textarea.mono { resize: vertical; }

.inline-row { display: flex; gap: 10px; align-items: center; }
.inline-row input { flex: 1; min-width: 0; }
.acct-select {
  flex: 1; min-width: 0;
  background: var(--bg-input, #1a1a22); border: 1px solid var(--border);
  color: var(--text); border-radius: 8px; padding: 9px 12px;
  font-size: 13.5px; cursor: pointer;
}
.acct-select:focus { outline: none; border-color: var(--gold-soft); }

.verify-ok {
  font-size: 13px; color: #34d399;
  background: rgba(52,211,153,.07); border: 1px solid rgba(52,211,153,.2);
  border-radius: 8px; padding: 10px 14px;
}
.tip {
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
