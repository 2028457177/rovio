import { createRouter, createWebHistory } from 'vue-router'
import { getToken, getUser } from '@/api/auth.js'

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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = getToken()
  const user = getUser()

  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  if (to.meta.guest && token) {
    // 已登录用户访问登录页，根据角色跳转
    if (user && user.role === 'admin') {
      next({ name: 'Admin' })
    } else {
      next({ name: 'Chat' })
    }
    return
  }

  // 角色路由保护：管理员不能访问普通用户页面，反之亦然
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
