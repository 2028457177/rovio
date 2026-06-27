const API_BASE = '/api'
const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function setUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function removeUser() {
  localStorage.removeItem(USER_KEY)
}

export function isAdmin() {
  const user = getUser()
  return user && user.role === 'admin'
}

export function logout() {
  removeToken()
  removeUser()
}

export async function login(username, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.error || '登录失败')
  }

  setToken(data.token)
  setUser(data.user)
  return data
}

export async function register(username, password, displayName = '') {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, display_name: displayName }),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.error || '注册失败')
  }

  setToken(data.token)
  setUser(data.user)
  return data
}

export async function fetchMe() {
  const token = getToken()
  if (!token) return null

  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    if (response.status === 401) {
      logout()
    }
    return null
  }

  const data = await response.json()
  setUser(data.user)
  return data.user
}
