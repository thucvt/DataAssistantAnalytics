import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

const api = axios.create({ baseURL: BASE })

// Đính token JWT vào mọi request nếu đã đăng nhập
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// 401 → xóa token và chuyển về login
api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
