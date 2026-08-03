<template>
  <div class="login-page">
    <div class="animated-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>
    <div class="cursor-glow" ref="cursorGlowRef"></div>

    <button class="login-theme-toggle" @click="toggleTheme" :title="theme === 'dark' ? '切换浅色模式' : '切换深色模式'">
      <Transition name="icon-flip" mode="out-in">
        <svg v-if="theme === 'dark'" key="sun" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
        <svg v-else key="moon" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      </Transition>
    </button>

    <div class="login-stage">
      <div class="login-card glass-strong">
        <div class="login-header">
          <div class="login-logo">
            <span class="logo-ring"></span>
            <img src="/agent-avatar.jpg" alt="助手" class="logo-img" />
          </div>
          <h1 class="login-title" aria-label="Rovio">
            <span
              v-for="(ch, i) in 'Rovio'"
              :key="i"
              class="title-char"
              :style="{ '--d': `${0.35 + i * 0.07}s` }"
            >{{ ch }}</span>
          </h1>
          <p class="login-subtitle">你的智能办公伙伴</p>
        </div>

        <Transition name="form-switch" mode="out-in">
          <!-- 登录表单 -->
          <form v-if="mode === 'login'" key="login" class="login-form" @submit.prevent="onLogin">
            <div class="form-group" style="--d: 0.55s">
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
            <div class="form-group" style="--d: 0.65s">
              <label class="form-label">密码</label>
              <input
                v-model="loginForm.password"
                type="password"
                class="form-input"
                placeholder="请输入密码"
                autocomplete="current-password"
                :disabled="loading"
                @keydown.enter="onLogin"
              />
            </div>

            <Transition name="fade">
              <div v-if="errorMsg" :key="errorMsg" class="form-error">{{ errorMsg }}</div>
            </Transition>

            <button type="submit" class="form-btn" :disabled="loading" style="--d: 0.75s">
              <span class="btn-shine"></span>
              <span v-if="loading" class="btn-spinner"></span>
              <span v-else class="btn-label">登 录</span>
            </button>

            <p class="form-switch" style="--d: 0.85s">
              还没有账号？
              <a href="#" @click.prevent="switchMode('register')">立即注册</a>
            </p>
          </form>

          <!-- 注册表单 -->
          <form v-else key="register" class="login-form" @submit.prevent="onRegister">
            <div class="form-group" style="--d: 0.05s">
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
            <div class="form-group" style="--d: 0.12s">
              <label class="form-label">显示名称</label>
              <input
                v-model="registerForm.displayName"
                type="text"
                class="form-input"
                placeholder="选填，默认使用用户名"
                :disabled="loading"
              />
            </div>
            <div class="form-group" style="--d: 0.19s">
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
            <div class="form-group" style="--d: 0.26s">
              <label class="form-label">确认密码</label>
              <input
                v-model="registerForm.confirmPassword"
                type="password"
                class="form-input"
                placeholder="再次输入密码"
                autocomplete="new-password"
                :disabled="loading"
                @keydown.enter="onRegister"
              />
            </div>

            <Transition name="fade">
              <div v-if="errorMsg" :key="errorMsg" class="form-error">{{ errorMsg }}</div>
            </Transition>

            <button type="submit" class="form-btn" :disabled="loading" style="--d: 0.33s">
              <span class="btn-shine"></span>
              <span v-if="loading" class="btn-spinner"></span>
              <span v-else class="btn-label">注 册</span>
            </button>

            <p class="form-switch" style="--d: 0.4s">
              已有账号？
              <a href="#" @click.prevent="switchMode('login')">立即登录</a>
            </p>
          </form>
        </Transition>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from '@/composables/useTheme.js'
import { login, register, isAdmin } from '@/api/auth.js'
import { resetChatState } from '@/composables/useChat.js'

const router = useRouter()
const route = useRoute()
const { theme, toggle: toggleTheme } = useTheme()

const mode = ref('login')
const loading = ref(false)
const errorMsg = ref('')
const cursorGlowRef = ref(null)

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
    // 登录成功时重置聊天单例状态，避免上一个会话（可能因 token 过期被自动登出）
    // 残留的 conversationsLoaded 标记导致新用户无法加载自己的会话列表。
    resetChatState()
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
    resetChatState()
    router.push('/')
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}

// 鼠标移动：用 RAF 合并连续事件，直接改 cursor-glow 的 transform（合成层），
// 不再往 documentElement 写 CSS 变量，避免触发整文档样式重算与整屏重绘。
let motionRafId = 0
let lastMoveEvent = null

function updateMotion(e) {
  lastMoveEvent = e
  if (motionRafId) return
  motionRafId = requestAnimationFrame(() => {
    motionRafId = 0
    const ev = lastMoveEvent
    if (!ev || !cursorGlowRef.value) return
    cursorGlowRef.value.style.transform = `translate3d(${ev.clientX}px, ${ev.clientY}px, 0)`
  })
}

onMounted(() => {
  window.addEventListener('mousemove', updateMotion, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('mousemove', updateMotion)
  if (motionRafId) cancelAnimationFrame(motionRafId)
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

.login-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  padding: 20px;
  width: 100%;
  max-width: 460px;
}

.login-card {
  width: 100%;
  padding: 44px 40px 36px;
  border-radius: var(--radius-lg);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.6) inset,
    0 24px 64px var(--shadow);
  animation: card-in 0.8s var(--ease-out-expo) both;
  position: relative;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(28px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* —— 主题切换：页面右上角浮动 —— */
.login-theme-toggle {
  position: fixed;
  top: 22px;
  right: 22px;
  z-index: 10;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--glass);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color var(--transition), border-color var(--transition), transform var(--spring-fast), box-shadow var(--transition);
  animation: card-in 0.8s var(--ease-out-expo) 0.5s both;
}

.login-theme-toggle:hover {
  color: var(--accent);
  border-color: rgba(var(--accent-rgb), 0.4);
  transform: rotate(18deg) scale(1.06);
  box-shadow: 0 8px 24px var(--shadow-sm);
}

.icon-flip-enter-active,
.icon-flip-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.icon-flip-enter-from {
  opacity: 0;
  transform: rotate(-90deg) scale(0.6);
}

.icon-flip-leave-to {
  opacity: 0;
  transform: rotate(90deg) scale(0.6);
}

/* —— 品牌区 —— */
.login-header {
  text-align: center;
  margin-bottom: 34px;
  position: relative;
}

.login-logo {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto 18px;
  border-radius: 50%;
  animation: logo-in 0.9s var(--ease-out-expo) 0.1s both;
}

@keyframes logo-in {
  from {
    opacity: 0;
    transform: scale(0.6);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.logo-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
  position: relative;
  z-index: 1;
  box-shadow: 0 10px 28px rgba(var(--accent-rgb), 0.28);
}

/* 旋转的渐变光环 */
.logo-ring {
  position: absolute;
  inset: -5px;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    rgba(var(--accent-rgb), 0) 0deg,
    rgba(var(--accent-rgb), 0.65) 90deg,
    rgba(var(--accent-rgb), 0) 180deg,
    rgba(var(--accent-rgb), 0.3) 270deg,
    rgba(var(--accent-rgb), 0) 360deg
  );
  animation: ring-spin 4s linear infinite;
  z-index: 0;
}

@keyframes ring-spin {
  to { transform: rotate(360deg); }
}

.login-title {
  font-family: var(--font-display);
  font-size: 34px;
  font-weight: 900;
  letter-spacing: 2px;
  color: var(--text);
  margin-bottom: 6px;
}

.title-char {
  display: inline-block;
  animation: char-in 0.7s var(--ease-out-expo) var(--d, 0s) both;
}

@keyframes char-in {
  from {
    opacity: 0;
    transform: translateY(18px) rotate(4deg);
  }
  to {
    opacity: 1;
    transform: translateY(0) rotate(0);
  }
}

.login-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 3px;
  animation: char-in 0.7s var(--ease-out-expo) 0.75s both;
}

/* —— 表单 —— */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
  animation: char-in 0.6s var(--ease-out-expo) var(--d, 0s) both;
}

.form-label {
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.5px;
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
  transition: border-color var(--transition), box-shadow var(--transition), transform var(--transition);
}

.form-input:hover {
  border-color: rgba(var(--accent-rgb), 0.3);
}

.form-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3.5px rgba(var(--accent-rgb), 0.14);
}

.form-input::placeholder {
  color: var(--text-muted);
}

/* 错误提示：进入时抖动 */
.form-error {
  font-size: 13px;
  color: var(--danger);
  background: var(--danger-soft);
  border: 1px solid var(--danger-border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  animation: err-shake 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}

@keyframes err-shake {
  10%, 90% { transform: translateX(-1px); }
  20%, 80% { transform: translateX(2px); }
  30%, 50%, 70% { transform: translateX(-3px); }
  40%, 60% { transform: translateX(3px); }
}

/* —— 主按钮：光泽扫过 —— */
.form-btn {
  margin-top: 6px;
  padding: 13px;
  background: linear-gradient(180deg, var(--accent-hover), var(--accent));
  color: var(--accent-contrast);
  border: none;
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 2px;
  font-family: inherit;
  cursor: pointer;
  transition: transform var(--spring-fast), box-shadow var(--spring-fast), filter var(--transition);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 10px 26px rgba(var(--accent-rgb), 0.32);
  animation: char-in 0.6s var(--ease-out-expo) var(--d, 0s) both;
}

.btn-shine {
  position: absolute;
  inset: 0;
  background: linear-gradient(105deg, transparent 35%, rgba(255, 255, 255, 0.28) 50%, transparent 65%);
  background-size: 220% 100%;
  background-position: 130% 0;
  transition: background-position 0.7s ease;
  pointer-events: none;
}

.form-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(var(--accent-rgb), 0.42);
  filter: brightness(1.05);
}

.form-btn:hover:not(:disabled) .btn-shine {
  background-position: -130% 0;
}

.form-btn:active:not(:disabled) {
  transform: translateY(0) scale(0.985);
}

.form-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.btn-spinner {
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(255, 248, 242, 0.4);
  border-top-color: var(--accent-contrast);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.form-switch {
  text-align: center;
  font-size: 13px;
  color: var(--text-muted);
  animation: char-in 0.6s var(--ease-out-expo) var(--d, 0s) both;
}

.form-switch a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 700;
  position: relative;
  transition: color var(--transition);
}

.form-switch a::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -2px;
  width: 100%;
  height: 1.5px;
  background: var(--accent);
  transform: scaleX(0);
  transform-origin: right;
  transition: transform 0.3s var(--ease-out-expo);
}

.form-switch a:hover::after {
  transform: scaleX(1);
  transform-origin: left;
}

.login-footnote {
  font-size: 12px;
  letter-spacing: 1.5px;
  color: var(--text-muted);
  opacity: 0.8;
  animation: char-in 0.8s var(--ease-out-expo) 1s both;
}

/* 表单切换动画 */
.form-switch-enter-active,
.form-switch-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.form-switch-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.form-switch-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 480px) {
  .login-card {
    padding: 36px 26px 30px;
  }

  .login-title {
    font-size: 28px;
  }
}
</style>
