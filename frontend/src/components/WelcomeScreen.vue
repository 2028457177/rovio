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
  max-width: 540px;
  padding: 48px 40px;
  animation: welcome-fade 0.8s cubic-bezier(0.4, 0, 0.2, 1);
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
  background: linear-gradient(135deg, var(--accent), #a78bfa);
  border-radius: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  color: #fff;
  position: relative;
  z-index: 1;
  box-shadow: 0 12px 40px rgba(124, 111, 247, 0.4);
  animation: icon-float 3s ease-in-out infinite;
}

@keyframes icon-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.welcome-icon-ring {
  position: absolute;
  inset: -12px;
  border-radius: 38px;
  border: 2px solid rgba(124, 111, 247, 0.25);
  animation: ring-rotate 8s linear infinite;
}

@keyframes ring-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.welcome-title {
  font-size: 30px;
  font-weight: 800;
  margin-bottom: 14px;
  background: linear-gradient(135deg, #e8eaf6 0%, #a78bfa 50%, #c4b5fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 1px;
}

.welcome-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.8;
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
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary);
  transition: transform var(--spring), box-shadow var(--spring), background var(--transition), border-color var(--transition);
  font-family: inherit;
}

.suggestion-card:hover {
  border-color: rgba(124, 111, 247, 0.4);
  background: rgba(124, 111, 247, 0.15);
  transform: translateY(-3px) scale(1.03);
  box-shadow: 0 8px 24px rgba(124, 111, 247, 0.2);
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
  color: var(--accent);
  font-size: 14px;
}
</style>
