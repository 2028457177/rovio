<template>
  <div class="login-page">
    <div class="animated-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>
    <div class="cursor-glow"></div>

    <div class="login-card glass-strong">
      <div class="login-header">
        <div class="login-logo">
          <img src="/agent-avatar.jpg" alt="助手" class="logo-img" />
          <div class="logo-glow"></div>
        </div>
        <h1 class="login-title">Rovio</h1>
        <p class="login-subtitle">智能 AI 助手</p>
        <button class="login-theme-toggle" @click="toggleTheme" :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'">
          <svg v-if="theme === 'dark'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        </button>
      </div>

      <Transition name="form-switch" mode="out-in">
        <!-- 登录表单 -->
        <form v-if="mode === 'login'" key="login" class="login-form" @submit.prevent="onLogin">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input
              v-model="loginForm.username"
              type="text"
              class="form-input"
              placeholder="请输入用户名"
              autocomplete="username"
              :disabled="loading"
            />
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <input
              v-model="loginForm.password"
              type="password"
              class="form-input"
              placeholder="请输入密码"
              autocomplete="current-password"
              :disabled="loading"
            />
          </div>

          <Transition name="fade">
            <div v-if="errorMsg" class="form-error">{{ errorMsg }}</div>
          </Transition>

          <button type="submit" class="form-btn" :disabled="loading">
            <span v-if="loading" class="btn-spinner"></span>
            <span v-else>登 录</span>
          </button>

          <p class="form-switch">
            还没有账号？
            <a href="#" @click.prevent="switchMode('register')">立即注册</a>
          </p>
        </form>

        <!-- 注册表单 -->
        <form v-else key="register" class="login-form" @submit.prevent="onRegister">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input
              v-model="registerForm.username"
              type="text"
              class="form-input"
              placeholder="3-50 个字符"
              autocomplete="username"
              :disabled="loading"
            />
          </div>
          <div class="form-group">
            <label class="form-label">显示名称</label>
            <input
              v-model="registerForm.displayName"
              type="text"
              class="form-input"
              placeholder="选填，默认使用用户名"
              :disabled="loading"
            />
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <input
              v-model="registerForm.password"
              type="password"
              class="form-input"
              placeholder="至少 6 个字符"
              autocomplete="new-password"
              :disabled="loading"
            />
          </div>
          <div class="form-group">
            <label class="form-label">确认密码</label>
            <input
              v-model="registerForm.confirmPassword"
              type="password"
              class="form-input"
              placeholder="再次输入密码"
              autocomplete="new-password"
              :disabled="loading"
            />
          </div>

          <Transition name="fade">
            <div v-if="errorMsg" class="form-error">{{ errorMsg }}</div>
          </Transition>

          <button type="submit" class="form-btn" :disabled="loading">
            <span v-if="loading" class="btn-spinner"></span>
            <span v-else>注 册</span>
          </button>

          <p class="form-switch">
            已有账号？
            <a href="#" @click.prevent="switchMode('login')">立即登录</a>
          </p>
        </form>
      </Transition>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from '@/composables/useTheme.js'
import { login, register, isAdmin } from '@/api/auth.js'

const router = useRouter()
const route = useRoute()
const { theme, toggle: toggleTheme } = useTheme()

const mode = ref('login')
const loading = ref(false)
const errorMsg = ref('')

const loginForm = ref({
  username: '',
  password: '',
})

const registerForm = ref({
  username: '',
  displayName: '',
  password: '',
  confirmPassword: '',
})

function switchMode(newMode) {
  mode.value = newMode
  errorMsg.value = ''
}

async function onLogin() {
  errorMsg.value = ''

  if (!loginForm.value.username || !loginForm.value.password) {
    errorMsg.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  try {
    await login(loginForm.value.username, loginForm.value.password)
    if (isAdmin()) {
      router.push('/admin')
    } else {
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    }
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}

async function onRegister() {
  errorMsg.value = ''

  const { username, displayName, password, confirmPassword } = registerForm.value

  if (!username || !password) {
    errorMsg.value = '用户名和密码不能为空'
    return
  }
  if (username.length < 3 || username.length > 50) {
    errorMsg.value = '用户名长度应为 3-50 个字符'
    return
  }
  if (password.length < 6) {
    errorMsg.value = '密码长度不能少于 6 个字符'
    return
  }
  if (password !== confirmPassword) {
    errorMsg.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    await register(username, password, displayName)
    router.push('/')
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}

function updateMotion(e) {
  const cx = (e.clientX / window.innerWidth) * 100
  const cy = (e.clientY / window.innerHeight) * 100
  const mx = (e.clientX / window.innerWidth - 0.5) * 2
  const my = (e.clientY / window.innerHeight - 0.5) * 2
  const root = document.documentElement
  root.style.setProperty('--cx', `${cx}%`)
  root.style.setProperty('--cy', `${cy}%`)
  root.style.setProperty('--mx', mx)
  root.style.setProperty('--my', my)
}

onMounted(() => {
  window.addEventListener('mousemove', updateMotion, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('mousemove', updateMotion)
})
</script>

<style scoped>
.login-page {
  width: 100%;
  height: 100vh;
  height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: 40px 36px;
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 60px var(--shadow);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
  position: relative;
}

.login-theme-toggle {
  position: absolute;
  top: 0;
  right: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--panel);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--spring-fast), color var(--transition), background var(--transition), border-color var(--transition);
}

.login-theme-toggle:hover {
  color: var(--accent);
  border-color: var(--accent);
  transform: rotate(20deg);
}

.login-logo {
  position: relative;
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: linear-gradient(180deg, #1f2329, var(--accent));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba(8, 10, 14, 0.2);
  overflow: hidden;
}

.logo-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  position: relative;
  z-index: 1;
}

.logo-glow {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  background: rgba(8, 10, 14, 0.12);
  filter: blur(10px);
  z-index: -1;
  animation: pulse-glow 2.5s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.1); }
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.login-subtitle {
  font-size: 13px;
  color: var(--text-muted);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input {
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  color: var(--text);
  background: var(--panel);
  outline: none;
  transition: border-color var(--transition), box-shadow var(--transition), background var(--transition);
}

.form-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-light);
}

.form-input::placeholder {
  color: var(--text-muted);
}

.form-error {
  font-size: 13px;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
}

.form-btn {
  margin-top: 4px;
  padding: 12px;
  background: var(--accent);
  color: var(--bg);
  border: none;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background var(--transition), transform var(--spring-fast), box-shadow var(--spring-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
}

.form-btn:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px var(--shadow);
}

.form-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--text);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  opacity: 0.7;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.form-switch {
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
}

.form-switch a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
  transition: color var(--transition);
}

.form-switch a:hover {
  color: var(--accent-hover);
}

/* 表单切换动画 */
.form-switch-enter-active,
.form-switch-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.form-switch-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.form-switch-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
