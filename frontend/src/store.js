import { reactive } from 'vue'

export const store = reactive({
  user: null,
  token: localStorage.getItem('token') || '',

  setAuth(token, user) {
    this.token = token
    this.user = user
    localStorage.setItem('token', token)
  },
  logout() {
    this.token = ''
    this.user = null
    localStorage.removeItem('token')
  },
  get isLoggedIn() { return !!this.token },
  get isSuperAdmin() { return this.user?.is_superadmin },
})
