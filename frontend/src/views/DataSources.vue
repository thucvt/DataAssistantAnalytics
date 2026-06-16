<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const connections = ref([])
const configs = ref({ FACEBOOK_APP_ID: '', FACEBOOK_APP_SECRET: '', FACEBOOK_REDIRECT_URI: '', SHOPEE_PARTNER_ID: '', SHOPEE_PARTNER_KEY: '', SHOPEE_REDIRECT_URI: '' })
const msg = ref({ text: '', type: '' })
const loading = ref(false)

function showMsg(text, type = 'ok') { msg.value = { text, type }; setTimeout(() => msg.value.text = '', 4000) }

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
  } catch (e) { showMsg(e.response?.data?.detail || 'Lỗi', 'err') }
}

async function connectFacebook() {
  try {
    const r = await api.get('/api/oauth/facebook/authorize')
    window.open(r.data.authorization_url, '_blank', 'width=600,height=700')
    showMsg('Cửa sổ đăng nhập Facebook đã mở. Sau khi xác nhận, nhấn Làm mới.')
  } catch (e) { showMsg(e.response?.data?.detail || 'Chưa cấu hình Facebook App ID/Redirect URI', 'err') }
}

async function connectShopee() {
  try {
    const r = await api.get('/api/oauth/shopee/authorize')
    window.open(r.data.authorization_url, '_blank', 'width=600,height=700')
    showMsg('Cửa sổ đăng nhập Shopee đã mở. Sau khi xác nhận, nhấn Làm mới.')
  } catch (e) { showMsg(e.response?.data?.detail || 'Chưa cấu hình Shopee Partner ID/Key', 'err') }
}

function connStatus(provider) {
  return connections.value.find(c => c.provider === provider)
}

onMounted(loadConnections)
</script>

<template>
  <div>
    <h2>Data Sources</h2>
    <p class="sub">Kết nối nguồn dữ liệu. Cấu hình App credentials trước, sau đó bấm Kết nối.</p>

    <div v-if="msg.text" :class="['alert', msg.type === 'err' ? 'alert-err' : 'alert-ok']">{{ msg.text }}</div>

    <!-- Facebook / Meta Ads -->
    <div class="card" style="margin-bottom:16px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <div>
          <h3>Facebook / Meta Ads</h3>
          <p style="color:var(--text-dim);font-size:13px;margin-top:4px">Lấy chi phí quảng cáo từ Meta Ads Manager</p>
        </div>
        <div style="display:flex;align-items:center;gap:12px">
          <span v-if="connStatus('facebook')?.connected" class="badge badge-ok">● Đã kết nối</span>
          <span v-else class="badge badge-warn">○ Chưa kết nối</span>
          <button class="btn btn-gold" @click="connectFacebook">Kết nối Facebook</button>
        </div>
      </div>
      <div class="grid2">
        <div class="field">
          <label>App ID</label>
          <div style="display:flex;gap:8px">
            <input v-model="configs.FACEBOOK_APP_ID" placeholder="123456789" />
            <button class="btn btn-ghost" style="white-space:nowrap;flex-shrink:0" @click="saveConfig('FACEBOOK_APP_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>App Secret</label>
          <div style="display:flex;gap:8px">
            <input v-model="configs.FACEBOOK_APP_SECRET" type="password" placeholder="••••••••" />
            <button class="btn btn-ghost" style="white-space:nowrap;flex-shrink:0" @click="saveConfig('FACEBOOK_APP_SECRET')">Lưu</button>
          </div>
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Redirect URI (phải trùng trong Facebook App Dashboard)</label>
          <div style="display:flex;gap:8px">
            <input v-model="configs.FACEBOOK_REDIRECT_URI" placeholder="http://localhost:8080/api/oauth/facebook/callback" />
            <button class="btn btn-ghost" style="white-space:nowrap;flex-shrink:0" @click="saveConfig('FACEBOOK_REDIRECT_URI')">Lưu</button>
          </div>
        </div>
      </div>
      <button class="btn btn-ghost" @click="loadConnections" style="font-size:13px">Làm mới trạng thái</button>
    </div>

    <!-- Shopee -->
    <div class="card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <div>
          <h3>Shopee</h3>
          <p style="color:var(--text-dim);font-size:13px;margin-top:4px">Lấy doanh thu đơn hàng từ Shopee Open Platform</p>
        </div>
        <div style="display:flex;align-items:center;gap:12px">
          <span v-if="connStatus('shopee')?.connected" class="badge badge-ok">● Đã kết nối</span>
          <span v-else class="badge badge-warn">○ Chưa kết nối</span>
          <button class="btn btn-gold" @click="connectShopee">Kết nối Shopee</button>
        </div>
      </div>
      <div class="grid2">
        <div class="field">
          <label>Partner ID</label>
          <div style="display:flex;gap:8px">
            <input v-model="configs.SHOPEE_PARTNER_ID" placeholder="1234567" />
            <button class="btn btn-ghost" style="white-space:nowrap;flex-shrink:0" @click="saveConfig('SHOPEE_PARTNER_ID')">Lưu</button>
          </div>
        </div>
        <div class="field">
          <label>Partner Key</label>
          <div style="display:flex;gap:8px">
            <input v-model="configs.SHOPEE_PARTNER_KEY" type="password" placeholder="••••••••" />
            <button class="btn btn-ghost" style="white-space:nowrap;flex-shrink:0" @click="saveConfig('SHOPEE_PARTNER_KEY')">Lưu</button>
          </div>
        </div>
        <div class="field" style="grid-column:1/-1">
          <label>Redirect URI</label>
          <div style="display:flex;gap:8px">
            <input v-model="configs.SHOPEE_REDIRECT_URI" placeholder="http://localhost:8080/api/oauth/shopee/callback" />
            <button class="btn btn-ghost" style="white-space:nowrap;flex-shrink:0" @click="saveConfig('SHOPEE_REDIRECT_URI')">Lưu</button>
          </div>
        </div>
      </div>
      <button class="btn btn-ghost" @click="loadConnections" style="font-size:13px">Làm mới trạng thái</button>
    </div>
  </div>
</template>
