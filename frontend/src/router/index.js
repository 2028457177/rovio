import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getUser, logout } from '@/api/auth.js'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'Chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { requiresAuth: true, role: 'user' },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { requiresAuth: true, role: 'admin' },
  },
  {
    path: '/admin/kb',
    name: 'AdminKb',
    component: () => import('@/views/AdminKbView.vue'),
    meta: { requiresAuth: true, role: 'admin' },
  },
  {
    path: '/kb',
    name: 'UserKb',
    component: () => import('@/views/UserKbView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 避免并发多次验证 token
let tokenVerified = false

async function verifyToken() {
  if (tokenVerified) return true

  const token = getToken()
  if (!token) return false

  try {
    const response = await fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
      if (response.status === 401) {
        logout()
      }
      return false
    }
    tokenVerified = true
    return true
  } catch {
    return true // 网络异常时放行，避免离线时被卡住
  }
}

router.beforeEach(async (to, from, next) => {
  const token = getToken()
  const user = getUser()

  if (to.meta.requiresAuth) {
    if (!token) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
    // 验证 token 是否过期，过期则清除并跳转登录
    const valid = await verifyToken()
    if (!valid) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }
  }

  if (to.meta.guest && token) {
    if (user && user.role === 'admin') {
      next({ name: 'Admin' })
    } else {
      next({ name: 'Chat' })
    }
    return
  }

  if (to.meta.role && user) {
    if (to.meta.role === 'admin' && user.role !== 'admin') {
      next({ name: 'Chat' })
      return
    }
    if (to.meta.role === 'user' && user.role === 'admin') {
      next({ name: 'Admin' })
      return
    }
  }

  next()
})

export default router
