<template>
  <div
    class="message-row"
    :class="{ 'message-user': role === 'user', 'message-bot': role === 'bot' }"
  >
    <!-- Bot avatar -->
    <div v-if="role === 'bot'" class="avatar avatar-bot">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/>
        <path d="M2 12l10 5 10-5"/>
      </svg>
    </div>

    <!-- Bubble -->
    <div class="bubble" :class="role === 'user' ? 'bubble-user' : 'bubble-bot'">
      <div v-if="role === 'bot'" class="bubble-content" v-html="renderedContent"></div>
      <div v-else class="bubble-content">{{ content }}</div>
    </div>

    <!-- User avatar -->
    <div v-if="role === 'user'" class="avatar avatar-user">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  role: 'user' | 'bot'
  content: string
}>()

const renderedContent = computed(() => {
  return parseContent(props.content)
})

function parseContent(text: string): string {
  // Convert markdown-ish formatting
  let html = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br/>')

  return html
}
</script>

<style scoped>
.message-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  animation: msgIn 0.28s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

.message-user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.avatar-bot {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  box-shadow: 0 2px 8px rgba(255, 107, 53, 0.25);
}

.avatar-user {
  background: linear-gradient(135deg, #6B7280 0%, #4B5563 100%);
  border-radius: 50%;
}

.bubble {
  max-width: 80%;
  padding: 14px 16px;
}

.bubble-bot {
  background: #FFFFFF;
  border: 1.5px solid var(--border);
  border-radius: 18px 18px 18px 4px;
  box-shadow: 0 2px 12px rgba(255, 107, 53, 0.07);
}

.bubble-user {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  color: #fff;
  border-radius: 18px 18px 4px 18px;
}

.bubble-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
}

.bubble-user .bubble-content {
  color: #fff;
}

.bubble-content :deep(strong) {
  font-weight: 600;
}

.bubble-content :deep(em) {
  font-style: italic;
  color: var(--primary-light);
}

.bubble-user .bubble-content :deep(em) {
  color: rgba(255, 255, 255, 0.85);
}

.bubble-content :deep(code) {
  background: var(--primary-bg);
  color: var(--primary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

@keyframes msgIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .bubble {
    max-width: 85%;
  }
}
</style>
