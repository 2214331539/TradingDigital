import type {
  AdminUser,
  ApiResponse,
  AssistantPreset,
  Conversation,
  ConversationDetail,
  Dashboard,
  ModelInfo,
  PageResult,
  Project,
  RoleInfo,
  User,
} from '../types'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  `${window.location.protocol}//${window.location.hostname}:8000/api/v1`

export function getToken() {
  return localStorage.getItem('chatai_token')
}

export function setToken(token: string) {
  localStorage.setItem('chatai_token', token)
}

export function clearToken() {
  localStorage.removeItem('chatai_token')
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })
  const payload = (await response.json()) as ApiResponse<T>
  if (!response.ok) {
    throw new Error(payload.message || response.statusText)
  }
  return payload.data
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; user: User }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function me() {
  return request<User>('/auth/me')
}

export async function listConversations(params?: {
  keyword?: string
  project_id?: string
  archived?: boolean
  favorited?: boolean
}) {
  const query = new URLSearchParams()
  query.set('page_size', '80')
  if (params?.keyword) query.set('keyword', params.keyword)
  if (params?.project_id !== undefined) query.set('project_id', params.project_id)
  if (params?.archived !== undefined) query.set('archived', String(params.archived))
  if (params?.favorited !== undefined) query.set('favorited', String(params.favorited))
  return request<PageResult<Conversation>>(`/conversations?${query}`)
}

export async function getConversation(id: string) {
  return request<ConversationDetail>(`/conversations/${id}`)
}

export async function createConversation(payload: Partial<Conversation>) {
  return request<Conversation>('/conversations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateConversation(
  id: string,
  payload: Partial<
    Pick<Conversation, 'title' | 'project_id' | 'is_archived' | 'is_favorited' | 'model_id'>
  >,
) {
  return request<Conversation>(`/conversations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function deleteConversation(id: string) {
  return request<{ success: boolean }>(`/conversations/${id}`, { method: 'DELETE' })
}

export async function availableModels() {
  return request<ModelInfo[]>('/models/available')
}

export async function assistants() {
  return request<AssistantPreset[]>('/assistants')
}

export async function listProjects() {
  return request<Project[]>('/projects')
}

export async function adminDashboard() {
  return request<Dashboard>('/admin/dashboard')
}

export async function adminUsers() {
  return request<PageResult<AdminUser>>('/admin/users?page_size=100')
}

export async function adminRoles() {
  return request<RoleInfo[]>('/admin/roles')
}

export async function adminModels() {
  return request<ModelInfo[]>('/admin/models')
}

export async function adminOperationLogs() {
  return request<
    {
      id: string
      user_id: string | null
      action: string
      target_type: string | null
      result: string
      created_at: string
    }[]
  >('/admin/logs/operations')
}

export async function streamChat(
  payload: {
    conversation_id?: string | null
    model_id?: string | null
    assistant_id?: string | null
    project_id?: string | null
    content: string
    temporary?: boolean
  },
  handlers: {
    onEvent: (event: string, data: any) => void
    onDone?: () => void
    onError?: (error: Error) => void
  },
  signal?: AbortSignal,
) {
  const token = getToken()
  const response = await fetch(`${API_BASE}/chat/completions/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  })

  if (!response.ok || !response.body) {
    const text = await response.text()
    throw new Error(text || 'stream failed')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() ?? ''
      for (const chunk of chunks) {
        const lines = chunk.split('\n')
        const event = lines.find((line) => line.startsWith('event:'))?.replace('event:', '').trim()
        const dataLine = lines.find((line) => line.startsWith('data:'))?.replace('data:', '').trim()
        if (!event || !dataLine) continue
        handlers.onEvent(event, JSON.parse(dataLine))
      }
    }
    handlers.onDone?.()
  } catch (error) {
    handlers.onError?.(error instanceof Error ? error : new Error(String(error)))
  }
}
