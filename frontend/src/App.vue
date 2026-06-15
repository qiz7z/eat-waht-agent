<script setup lang="ts">
import { ref, nextTick, onMounted, computed } from 'vue'
import ChatMessage from './components/ChatMessage.vue'
import TypingIndicator from './components/TypingIndicator.vue'
import { sendMessage as apiSendMessage, resetSession, clearSession } from './api'

// ── State ──
interface Message {
  role: 'user' | 'bot'
  content: string
}

const messages = ref<Message[]>([])
const inputText = ref('')
const isLoading = ref(false)
const isReady = ref(true)
const messagesContainer = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

// ── Welcome message ──
const WELCOME_MSG = `你好！我是你的 **AI 餐饮推荐助手** 👋

今天想吃什么？告诉我你的口味、预算、人数，或者直接说「帮我推荐一个」，我来帮你决定！`

// ── Quick chips ──
const quickChips = [
  { text: '帮我随机推荐一个', label: '🎲 随机推荐' },
  { text: '我想吃辣的，预算30以内', label: '🌶️ 辣味低预算' },
  { text: '最近在减肥，推荐清淡的', label: '🥗 健康轻食' },
]

const quickSuggestions = [
  '清淡', '重口味', '辣的', '10元以下', '10-30元',
  '减肥餐', '聚餐', '独食', '快餐',
]

// ── Context info ──
const contextInfo = computed(() => {
  const now = new Date()
  const h = now.getHours()
  const timeLabel = h < 5 ? '深夜' : h < 10 ? '早餐时间' : h < 14 ? '午餐时间' : h < 17 ? '下午茶时间' : h < 20 ? '晚餐时间' : '夜宵时间'
  const dateStr = now.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })
  return { timeLabel, dateStr }
})

// ── Init ──
onMounted(() => {
  messages.value.push({ role: 'bot', content: WELCOME_MSG })
  scrollToBottom()
})

// ── Scroll ──
async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// ── Send message ──
async function sendMessage(text?: string) {
  const msg = (text || inputText.value).trim()
  if (!msg || isLoading.value) return

  inputText.value = ''
  resetTextareaHeight()

  messages.value.push({ role: 'user', content: msg })
  await scrollToBottom()

  // Handle local reset
  if (/重新开始|重置/i.test(msg)) {
    await handleReset()
    return
  }

  isLoading.value = true
  await scrollToBottom()

  try {
    const res = await apiSendMessage(msg)
    messages.value.push({ role: 'bot', content: res.response })
    isReady.value = res.is_ready
  } catch (err) {
    console.error('Chat error:', err)
    messages.value.push({
      role: 'bot',
      content: '抱歉，连接 AI 服务时出现了问题 😅\n\n请确认后端服务已启动，然后重试。',
    })
  } finally {
    isLoading.value = false
    await scrollToBottom()
  }
}

// ── Reset ──
async function handleReset() {
  try {
    await resetSession()
  } catch {
    // ignore
  }
  clearSession()
  messages.value = []
  isLoading.value = false

  await nextTick()
  messages.value.push({
    role: 'bot',
    content: '好的，我们重新开始！🍜\n\n告诉我你今天想吃什么风格的食物，或者直接说「帮我推荐一个」，我来帮你决定！',
  })
  await scrollToBottom()
}

// ── Keyboard ──
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// ── Auto resize ──
function autoResize(e: Event) {
  const el = e.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

function resetTextareaHeight() {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
  }
}
</script>

<template>
  <div class="app-layout">
    <!-- ── LEFT SIDEBAR ── -->
    <aside class="sidebar">
      <!-- Brand -->
      <div class="sidebar-brand">
        <div class="brand-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div>
          <h1 class="brand-title">今天吃什么</h1>
          <p class="brand-subtitle">AI 智能餐饮推荐</p>
        </div>
      </div>

      <div class="sidebar-divider"></div>

      <!-- Context info -->
      <div class="sidebar-card">
        <p class="card-title">当前信息</p>
        <div class="card-items">
          <div class="stat-item">
            <span class="stat-dot dot-orange"></span>
            <span class="stat-text">{{ contextInfo.timeLabel }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-dot dot-sky"></span>
            <span class="stat-text">天气：晴天</span>
          </div>
          <div class="stat-item">
            <span class="stat-dot dot-green"></span>
            <span class="stat-text">{{ contextInfo.dateStr }}</span>
          </div>
        </div>
      </div>

      <!-- Quick start -->
      <div class="sidebar-card card-tip">
        <p class="card-title tip-title">快速开始</p>
        <ul class="tip-list">
          <li>告诉我你的口味偏好</li>
          <li>说说今天的预算</li>
          <li>可以直接问"帮我推荐一个"</li>
          <li>输入"重新开始"重置会话</li>
        </ul>
      </div>

      <div class="sidebar-spacer"></div>

      <!-- Reset button -->
      <button class="btn-reset" @click="handleReset">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10"/>
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg>
        重新开始推荐
      </button>
      <p class="sidebar-footer">由 LangChain + OpenAI 驱动</p>
    </aside>

    <!-- ── MAIN CHAT ── -->
    <main class="chat-main">
      <div class="chat-container">
        <!-- Header -->
        <div class="chat-header">
          <div>
            <h2 class="header-title">和 AI 聊聊吃什么</h2>
            <p class="header-desc">综合口味、预算、天气、心情给你推荐最合适的一餐</p>
          </div>
          <div class="header-status">
            <span class="status-dot" :class="isReady ? 'status-ready' : 'status-error'"></span>
            <span class="status-text">{{ isReady ? 'AI 就绪' : '未连接' }}</span>
          </div>
        </div>

        <!-- Messages -->
        <div ref="messagesContainer" class="messages-area">
          <ChatMessage
            v-for="(msg, i) in messages"
            :key="i"
            :role="msg.role"
            :content="msg.content"
          />

          <!-- Quick chips after welcome -->
          <div v-if="messages.length === 1" class="quick-chips-wrap">
            <button
              v-for="chip in quickChips"
              :key="chip.text"
              class="chip"
              @click="sendMessage(chip.text)"
            >
              {{ chip.label }}
            </button>
          </div>

          <TypingIndicator v-if="isLoading" />
        </div>

        <!-- Quick suggestion row -->
        <div class="suggestions-row">
          <button
            v-for="s in quickSuggestions"
            :key="s"
            class="chip"
            @click="sendMessage(s)"
          >
            {{ s }}
          </button>
        </div>

        <!-- Input area -->
        <div class="input-area">
          <div class="input-bar">
            <textarea
              ref="textareaRef"
              v-model="inputText"
              rows="1"
              placeholder="说说你想吃什么…（回车发送，Shift+回车换行）"
              class="input-field"
              :disabled="isLoading"
              @input="autoResize"
              @keydown="handleKeydown"
            ></textarea>
            <button
              class="send-btn"
              :disabled="isLoading || !inputText.trim()"
              @click="sendMessage()"
              title="发送"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
          <p class="input-hint">AI 推荐仅供参考，最终决定由你做主 🙂</p>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
/* ── Layout ── */
.app-layout {
  display: flex;
  height: 100dvh;
  max-width: 1280px;
  margin: 0 auto;
  overflow: hidden;
}

/* ── Sidebar ── */
.sidebar {
  width: 280px;
  flex-shrink: 0;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
}

.brand-icon {
  width: 44px;
  height: 44px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
}

.brand-title {
  font-size: 20px;
  font-weight: 800;
  line-height: 1.2;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-subtitle {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.sidebar-divider {
  height: 1px;
  background: var(--border);
  margin: 0 8px;
}

.sidebar-card {
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.card-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 12px;
  background: var(--bg-secondary);
  font-size: 13px;
}

.stat-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-orange { background: var(--primary); }
.dot-sky { background: #38BDF8; }
.dot-green { background: var(--success); }

.stat-text {
  color: var(--text-secondary);
}

.card-tip {
  background: linear-gradient(145deg, var(--primary-bg) 0%, #FFF7ED 100%);
  border-color: var(--border-light);
}

.tip-title {
  color: var(--primary-dark);
}

.tip-list {
  font-size: 12px;
  color: var(--text-secondary);
  padding-left: 16px;
  margin: 0;
}

.tip-list li {
  margin-bottom: 6px;
  line-height: 1.5;
}

.sidebar-spacer {
  flex: 1;
}

.btn-reset {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1.5px solid var(--border);
  border-radius: 50px;
  background: #fff;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s;
}

.btn-reset:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-bg);
}

.sidebar-footer {
  text-align: center;
  font-size: 11px;
  color: var(--text-tertiary);
  padding-bottom: 8px;
}

/* ── Chat main ── */
.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 16px 16px 16px 0;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1.5px solid var(--border-light);
  border-radius: 24px;
  overflow: hidden;
}

/* ── Header ── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--bg-secondary);
}

.header-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.header-desc {
  font-size: 12px;
  color: var(--text-tertiary);
  margin: 4px 0 0;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-ready {
  background: var(--success);
}

.status-error {
  background: var(--error);
}

.status-text {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ── Messages ── */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scroll-behavior: smooth;
}

.quick-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 4px 48px;
}

/* ── Suggestions row ── */
.suggestions-row {
  display: flex;
  gap: 8px;
  padding: 8px 24px;
  border-top: 1px solid var(--bg-secondary);
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.suggestions-row::-webkit-scrollbar {
  display: none;
}

/* ── Chips ── */
.chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 16px;
  border: 1.5px solid var(--border);
  border-radius: 50px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  background: #fff;
  cursor: pointer;
  transition: all 0.18s ease;
  user-select: none;
  white-space: nowrap;
  flex-shrink: 0;
}

.chip:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-bg);
  transform: translateY(-1px);
}

.chip:active {
  transform: scale(0.96);
}

/* ── Input ── */
.input-area {
  padding: 16px 24px;
  border-top: 1px solid var(--bg-secondary);
}

.input-bar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 12px 16px;
  background: #fff;
  border: 2px solid var(--border);
  border-radius: 24px;
  transition: border-color 0.18s, box-shadow 0.18s;
}

.input-bar:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.12);
}

.input-field {
  flex: 1;
  outline: none;
  border: none;
  background: transparent;
  resize: none;
  font-family: inherit;
  font-size: 15px;
  color: var(--text-primary);
  line-height: 1.5;
  max-height: 120px;
}

.input-field::placeholder {
  color: var(--text-tertiary);
}

.input-field:disabled {
  opacity: 0.5;
}

.send-btn {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.18s ease;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  transform: scale(1.08);
  box-shadow: 0 4px 16px rgba(255, 107, 53, 0.4);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.94);
}

.send-btn:disabled {
  background: #D1C8C0;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.input-hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
  margin: 8px 0 0;
}

/* ── Mobile ── */
@media (max-width: 768px) {
  .sidebar {
    display: none;
  }

  .chat-main {
    padding: 0;
  }

  .chat-container {
    border-radius: 0;
    height: 100dvh;
  }

  .chat-header {
    padding: 16px;
  }

  .messages-area {
    padding: 12px 16px;
  }

  .input-area {
    padding: 12px 16px;
  }

  .suggestions-row {
    padding: 8px 16px;
  }
}
</style>
