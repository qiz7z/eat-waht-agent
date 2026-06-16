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

export interface FoodItem {
  rank: number
  name: string
  category: string
  price_range: string
  popularity: number
  tags: string[]
  description?: string
}

export interface FoodRankingsResponse {
  success: boolean
  count: number
  foods: FoodItem[]
}

export interface SearchFoodResponse {
  success: boolean
  count: number
  results: FoodItem[]
}

export interface FoodStatsResponse {
  total_foods: number
  categories: Record<string, number>
  last_update: string | null
  should_update: boolean
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
 * 获取热门食物排行榜
 */
export async function getFoodRankings(limit: number = 10): Promise<FoodRankingsResponse> {
  const res = await axios.get<FoodRankingsResponse>(`${API_BASE}/api/food_rankings`, {
    params: { limit }
  })
  return res.data
}

/**
 * 搜索食物
 */
export async function searchFood(params: {
  taste?: string
  budget?: string
  meal_time?: string
  category?: string
  limit?: number
}): Promise<SearchFoodResponse> {
  const res = await axios.post<SearchFoodResponse>(`${API_BASE}/api/search_food`, params)
  return res.data
}

/**
 * 获取食物数据库统计
 */
export async function getFoodStats(): Promise<FoodStatsResponse> {
  const res = await axios.get<FoodStatsResponse>(`${API_BASE}/api/food_stats`)
  return res.data
}

/**
 * 清除当前会话 ID（新对话）
 */
export function clearSession(): void {
  currentSessionId = null
}
