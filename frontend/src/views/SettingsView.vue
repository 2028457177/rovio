<template>
  <div class="settings-page">
    <div class="animated-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>

    <!-- 顶部导航 -->
    <header class="settings-header glass">
      <button class="back-btn" @click="goBack" title="返回">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        <span>返回</span>
      </button>
      <h1 class="settings-title serif">账号设置</h1>
      <div class="header-spacer"></div>
    </header>

    <SettingsPanel />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import SettingsPanel from '@/components/SettingsPanel.vue'

const router = useRouter()

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}
</script>

<style scoped>
.settings-page {
  width: 100%;
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
  overflow: hidden;
}

/* —— 顶部导航 —— */
.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
  flex-shrink: 0;
  z-index: 5;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all var(--transition);
}

.back-btn:hover {
  color: var(--text);
  border-color: rgba(var(--accent-rgb), 0.4);
  background: var(--hover);
}

.settings-title {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--text);
}

.header-spacer {
  width: 86px;
}

@media (max-width: 640px) {
  .settings-header {
    padding: 12px 16px;
  }

  .back-btn {
    padding: 7px 12px;
    font-size: 12.5px;
  }

  .settings-title {
    font-size: 18px;
  }

  .header-spacer {
    width: 70px;
  }
}
</style>
