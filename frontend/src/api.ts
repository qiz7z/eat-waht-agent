import axios from 'axios'

// FastAPI 后端地址（通过 Vite 代理，开发时用 /api 前缀）
const API_BASE = import.meta.env.VITE_API_BASE || ''

export interface ChatResponse {
  session_id: string
  response: string
  history: Array<{ role: string; content: string }>
  is_ready: boolean
}

export interface HealthResponse {
  status: string
  active_sessions: number
}

let currentSessionId: string | null = null

/**
 * 发送消息给 Agent
 */
export async function sendMessage(message: string): Promise<ChatResponse> {
  const res = await axios.post<ChatResponse>(`${API_BASE}/api/chat`, {
    message,
    session_id: currentSessionId,
  })
  currentSessionId = res.data.session_id
  return res.data
}

/**
 * 重置会话
 */
export async function resetSession(): Promise<ChatResponse> {
  if (!currentSessionId) {
    // 没有会话，直接返回
    return {
      session_id: '',
      response: '已重置，可以重新开始推荐。',
      history: [],
      is_ready: true,
    }
  }
  const res = await axios.post<ChatResponse>(`${API_BASE}/api/reset`, {
    session_id: currentSessionId,
  })
  return res.data
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<HealthResponse> {
  const res = await axios.get<HealthResponse>(`${API_BASE}/api/health`)
  return res.data
}

/**
 * 清除当前会话 ID（新对话）
 */
export function clearSession(): void {
  currentSessionId = null
}
