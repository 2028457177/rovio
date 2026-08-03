<template>
  <div class="welcome-container">
    <div class="welcome-card glass-strong">
      <div class="welcome-icon-wrapper">
        <div class="welcome-icon-ring"></div>
        <div class="welcome-icon">🤖</div>
      </div>
      <h1 class="welcome-title">Rovio</h1>
      <p class="welcome-desc">
        上传 Word 模板（{内容提示|字体|字号}），AI 自动填充并生成文档；支持知识库检索。
      </p>
      <div class="welcome-tags">
        <code>{内容提示|字体|字号}</code>
        <span>例：<code>{姓名|楷体|四号}</code>、<code>{日期}</code>、<code>{金额||三号}</code></span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['send'])
</script>

<style scoped>
.welcome-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.welcome-card {
  text-align: center;
  max-width: 560px;
  padding: 48px 44px;
  animation: welcome-fade 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: var(--radius-lg);
  background: var(--glass-strong);
  transition: background 0.35s ease;
}

[data-theme="dark"] .welcome-card {
  background: rgba(22, 25, 31, 0.92);
}

@keyframes welcome-fade {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.welcome-icon-wrapper {
  position: relative;
  display: inline-block;
  margin-bottom: 28px;
}

.welcome-icon {
  width: 88px;
  height: 88px;
  background:
    radial-gradient(circle at 32% 26%, rgba(255, 255, 255, 0.96), transparent 16%),
    radial-gradient(circle at 50% 50%, #f9fafb, #c5cbd4 68%, #8f98a4 100%);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  position: relative;
  z-index: 1;
  box-shadow:
    inset 0 1px 2px rgba(0,0,0,0.02),
    0 12px 28px rgba(8, 10, 14, 0.15);
  animation: icon-float 3s ease-in-out infinite;
}

[data-theme="dark"] .welcome-icon {
  background:
    radial-gradient(circle at 32% 26%, rgba(255, 255, 255, 0.12), transparent 16%),
    radial-gradient(circle at 50% 50%, #2c313a, #1f2329 68%, #16191f 100%);
}

@keyframes icon-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.welcome-icon-ring {
  position: absolute;
  inset: -10px;
  border-radius: 34px;
  border: 1px dashed rgba(8, 9, 11, 0.15);
  animation: ring-rotate 12s linear infinite;
}

@keyframes ring-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.welcome-title {
  font-size: 30px;
  font-weight: 620;
  margin-bottom: 14px;
  background: linear-gradient(135deg, #1f2329, #2c313a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.3px;
}

.welcome-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.75;
  margin-bottom: 36px;
}

.welcome-tags {
  margin-top: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
  flex-wrap: wrap;
}

.welcome-tags code {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 6px;
  font-family: inherit;
  font-size: 12px;
}
</style>
