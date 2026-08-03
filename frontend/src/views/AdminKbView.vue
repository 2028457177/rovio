<template>
  <div class="admin-page">
    <div class="animated-bg">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="orb orb-4"></div>
    </div>

    <header class="admin-header glass">
      <div class="header-left">
        <div class="admin-logo">
          <img src="/favicon.png" alt="Rovio" />
        </div>
        <div class="title-block">
          <div class="title-row">
            <h1 class="header-title serif">知识库管理</h1>
            <span class="header-badge">管理员</span>
          </div>
          <p class="header-sub">全局知识库建设 · 索引与检索质量管理</p>
        </div>
      </div>
      <div class="header-right">
        <span class="admin-name">{{ adminName }}</span>
        <button class="btn-nav" @click="goUserAdmin" title="用户管理">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
          用户管理
        </button>
        <button class="btn-settings" @click="goSettings" title="账号设置">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
          </svg>
        </button>
        <button class="btn-logout" @click="onLogout">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          退出登录
        </button>
      </div>
    </header>

    <div class="admin-body">
      <KbManager scope="admin" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getUser, logout } from '@/api/auth.js'
import KbManager from '@/components/kb/KbManager.vue'

const router = useRouter()
const adminName = ref('')

onMounted(() => {
  const user = getUser()
  adminName.value = user?.display_name || user?.username || '管理员'
})

function goUserAdmin() {
  router.push('/admin')
}

function goSettings() {
  router.push('/settings')
}

function onLogout() {
  logout()
  router.push('/login')
}
</script>

<style scoped>
.admin-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  background: var(--bg);
}

.admin-header {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.5rem;
  margin: 1rem 1.25rem 0;
  border-radius: var(--radius);
  border: 1px solid var(--border-light);
}

.header-left { display: flex; align-items: center; gap: 0.75rem; }

.admin-logo { width: 34px; height: 34px; border-radius: 10px; overflow: hidden; }
.admin-logo img { width: 100%; height: 100%; object-fit: cover; }

.title-block { display: flex; flex-direction: column; gap: 0.1rem; }
.title-row { display: flex; align-items: center; gap: 0.6rem; }

.header-title { font-size: 1.15rem; font-weight: 600; letter-spacing: 0.02em; }

.header-sub { font-size: 0.72rem; color: var(--text-muted); }

.header-badge {
  font-size: 0.68rem;
  padding: 0.15rem 0.6rem;
  border-radius: var(--radius-pill);
  background: var(--accent);
  color: var(--accent-contrast);
}

.header-right { display: flex; align-items: center; gap: 0.6rem; }

.admin-name { font-size: 0.85rem; color: var(--text-secondary); margin-right: 0.3rem; }

.btn-nav {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.85rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--text);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all var(--transition);
}
.btn-nav:hover { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); }

.btn-settings {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}
.btn-settings:hover { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); }

.btn-logout {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.4rem 0.9rem;
  border: 1px solid var(--danger-border);
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--danger);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all var(--transition);
}
.btn-logout:hover { background: var(--danger); color: #fff; }

.admin-body {
  position: relative;
  z-index: 5;
  flex: 1;
  display: flex;
  min-height: 0;
  padding: 1.25rem;
}

.serif { font-family: var(--font-display); }

@media (max-width: 720px) {
  .admin-header { flex-wrap: wrap; gap: 0.5rem; }
  .admin-name { display: none; }
  .header-sub { display: none; }
}
</style>
