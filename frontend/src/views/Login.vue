<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'
import { store } from '../store.js'

const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function login() {
  error.value = ''
  loading.value = true
  try {
    const r = await api.post('/api/auth/login', { email: email.value, password: password.value })
    store.setAuth(r.data.access_token, null)
    const me = await api.get('/api/auth/me')
    store.user = me.data
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Đăng nhập thất bại'
  } finally { loading.value = false }
}
</script>

<template>
  <div class="login-wrap">
    <div class="login-box">
      <div class="brand">
        <div class="logo">DA</div>
        <h1>Data <span>Assistant</span></h1>
      </div>
      <p class="sub">Đăng nhập vào Admin Panel</p>
      <div v-if="error" class="alert alert-err">{{ error }}</div>
      <div class="field"><label>Email</label><input v-model="email" type="email" placeholder="admin@company.com" @keyup.enter="login" /></div>
      <div class="field"><label>Mật khẩu</label><input v-model="password" type="password" placeholder="••••••••" @keyup.enter="login" /></div>
      <button class="btn btn-gold" style="width:100%;justify-content:center" :disabled="loading" @click="login">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? 'Đang xử lý…' : 'Đăng nhập' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-wrap { min-height:100vh; display:grid; place-items:center; background: radial-gradient(700px 400px at 80% 0%, rgba(212,175,55,0.08), transparent), var(--bg); padding:20px; }
.login-box { width:100%; max-width:400px; }
.brand { display:flex; align-items:center; gap:12px; margin-bottom:6px; }
.logo { width:40px; height:40px; border-radius:11px; background:linear-gradient(145deg,var(--gold-soft),var(--gold)); color:#1a1a1a; font-weight:800; font-size:18px; display:grid; place-items:center; }
h1 { font-size:20px; } h1 span { color:var(--gold); }
.sub { color:var(--text-dim); font-size:13.5px; margin-bottom:24px; }
</style>
