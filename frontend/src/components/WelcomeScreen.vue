<template>
  <div class="welcome-container">
    <div class="welcome-card glass-strong">
      <div class="welcome-icon-wrapper">
        <div class="welcome-icon-ring"></div>
        <div class="welcome-icon">🤖</div>
      </div>
      <h1 class="welcome-title">自动化办公助手</h1>
      <p class="welcome-desc">
        基于大语言模型的智能办公伴侣，帮你处理文档、搜索知识库、查询信息、生成报告。请在下方输入你的需求。
      </p>
      <div class="welcome-suggestions">
        <button
          v-for="item in suggestions"
          :key="item.prompt"
          class="suggestion-card glass"
          @click="$emit('send', item.prompt)"
        >
          <span class="suggestion-icon">{{ item.icon }}</span>
          <span class="suggestion-text">{{ item.label }}</span>
          <span class="suggestion-arrow">→</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['send'])

const suggestions = [
  { icon: '📄', label: '自动填写文档', prompt: '帮我自动填写Word模板文件' },
  { icon: '🌤️', label: '查询天气', prompt: '帮我查询今天的天气' },
  { icon: '📊', label: '生成工作报告', prompt: '帮我生成一份个人工作数据报告' },
  { icon: '🔍', label: '联网搜索', prompt: '帮我搜索最新的办公效率工具' },
]
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

.welcome-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}

.suggestion-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  border-radius: var(--radius-pill);
  cursor: pointer;
  font-size: 13px;
  color: var(--text);
  background: #fff;
  border: 1px solid var(--border);
  transition: transform var(--spring), box-shadow var(--spring), background var(--transition), border-color var(--transition);
  font-family: inherit;
  box-shadow: 0 4px 14px var(--shadow-sm);
}

.suggestion-card:hover {
  border-color: rgba(8, 9, 11, 0.3);
  background: #fff;
  transform: translateY(-3px);
  box-shadow: 0 12px 32px var(--shadow);
}

.suggestion-card:hover .suggestion-arrow {
  opacity: 1;
  transform: translateX(0);
}

.suggestion-icon {
  font-size: 16px;
}

.suggestion-text {
  font-weight: 500;
}

.suggestion-arrow {
  opacity: 0;
  transform: translateX(-8px);
  transition: var(--transition);
  color: var(--text-muted);
  font-size: 14px;
}
</style>
