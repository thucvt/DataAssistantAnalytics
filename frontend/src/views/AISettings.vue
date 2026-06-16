<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const settings = ref(null)
const loading = ref(false)
const msg = ref({ text: '', type: '' })
const keyInputs = ref({ openai: '', anthropic: '', gemini: '' })
const newProvider = ref('openai')
const newModel = ref('')

const MODELS = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-opus-4-8'],
  gemini: ['gemini-1.5-pro', 'gemini-1.5-flash'],
}

function showMsg(text, type = 'ok') { msg.value = { text, type }; setTimeout(() => msg.value.text = '', 3500) }

async function load() {
  try { settings.value = (await api.get('/api/ai/settings')).data }
  catch (e) { showMsg(e.response?.data?.detail || 'Lỗi tải cấu hình', 'err') }
}

async function saveProvider() {
  loading.value = true
  try {
    settings.value = (await api.put('/api/ai/settings', { provider: newProvider.value, model: newModel.value })).data
    showMsg('Đã lưu provider mặc định')
  } catch (e) { showMsg(e.response?.data?.detail || 'Lỗi', 'err') }
  finally { loading.value = false }
}

async function saveKey(provider) {
  const key = keyInputs.value[provider]
  if (!key) return showMsg('Nhập API key trước', 'err')
  loading.value = true
  try {
    settings.value = (await api.put('/api/ai/keys', { provider, api_key: key })).data
    keyInputs.value[provider] = ''
    showMsg(`Đã lưu ${provider} API key`)
  } catch (e) { showMsg(e.response?.data?.detail || 'Lỗi', 'err') }
  finally { loading.value = false }
}

async function deleteKey(provider) {
  if (!confirm(`Xóa API key của ${provider}?`)) return
  loading.value = true
  try {
    settings.value = (await api.delete(`/api/ai/keys/${provider}`)).data
    showMsg(`Đã xóa ${provider} key`)
  } catch (e) { showMsg(e.response?.data?.detail || 'Lỗi', 'err') }
  finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <div>
    <h2>AI Settings</h2>
    <p class="sub">Cấu hình nhà cung cấp LLM và API Keys. Keys được mã hóa trước khi lưu vào Database.</p>

    <div v-if="msg.text" :class="['alert', msg.type === 'err' ? 'alert-err' : 'alert-ok']">{{ msg.text }}</div>

    <div v-if="settings" class="grid2" style="margin-bottom:20px">
      <div class="card">
        <span class="label">Provider đang dùng</span>
        <div style="font-size:22px;font-weight:700;color:var(--gold-soft);text-transform:capitalize">{{ settings.active_provider }}</div>
      </div>
      <div class="card">
        <span class="label">Model mặc định</span>
        <div style="font-size:16px;font-weight:600;color:var(--text)">{{ settings.active_model }}</div>
      </div>
    </div>

    <!-- Chọn provider -->
    <div class="card" style="margin-bottom:16px">
      <h3 style="margin-bottom:16px">Đổi Provider / Model</h3>
      <div class="grid2">
        <div class="field">
          <label>Provider</label>
          <select v-model="newProvider" @change="newModel = MODELS[newProvider][0]">
            <option value="openai">OpenAI (GPT)</option>
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="gemini">Google (Gemini)</option>
          </select>
        </div>
        <div class="field">
          <label>Model</label>
          <select v-model="newModel">
            <option v-for="m in MODELS[newProvider]" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
      </div>
      <button class="btn btn-gold" :disabled="loading" @click="saveProvider">Lưu thay đổi</button>
    </div>

    <!-- API Keys -->
    <div class="card">
      <h3 style="margin-bottom:16px">API Keys</h3>
      <div v-for="provider in ['openai', 'anthropic', 'gemini']" :key="provider" style="margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid var(--border)">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
          <span style="font-weight:600;text-transform:capitalize;min-width:90px">{{ provider }}</span>
          <span v-if="settings?.keys_configured?.[provider]" class="badge badge-ok">● Đã cấu hình</span>
          <span v-else class="badge badge-warn">○ Chưa có key</span>
          <button v-if="settings?.keys_configured?.[provider]" class="btn btn-danger" style="padding:4px 12px;font-size:12px;margin-left:auto" @click="deleteKey(provider)">Xóa</button>
        </div>
        <div style="display:flex;gap:10px">
          <input v-model="keyInputs[provider]" type="password" :placeholder="`Nhập ${provider} API key mới…`" />
          <button class="btn btn-ghost" style="white-space:nowrap;flex-shrink:0" :disabled="loading" @click="saveKey(provider)">Lưu key</button>
        </div>
      </div>
    </div>
  </div>
</template>
