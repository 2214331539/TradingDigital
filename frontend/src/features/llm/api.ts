import { API_BASE, request } from '../../shared/api/http'
import type {
  AssistantPreset,
  Conversation,
  ConversationDetail,
  LlmProject,
  Message,
  ModelInfo,
  PageResult,
} from '../../shared/types'

export function listConversations(params?: {
  keyword?: string
  archived?: boolean
  pinned?: boolean
}) {
  const query = new URLSearchParams({ page_size: '80' })
  if (params?.keyword) query.set('keyword', params.keyword)
  if (params?.archived !== undefined) query.set('archived', String(params.archived))
  if (params?.pinned !== undefined) query.set('pinned', String(params.pinned))
  return request<PageResult<Conversation>>(`/llm/conversations?${query}`)
}

export function getConversation(id: string) {
  return request<ConversationDetail>(`/llm/conversations/${id}`)
}

export function createConversation(payload: {
  title?: string
  model_id?: string | null
  assistant_preset_id?: string | null
  project_id?: string | null
  temporary?: boolean
}) {
  return request<Conversation>('/llm/conversations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateConversation(
  id: string,
  payload: Partial<
    Pick<Conversation, 'title' | 'archived' | 'pinned' | 'model_id' | 'project_id'>
  >,
) {
  return request<Conversation>(`/llm/conversations/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteConversation(id: string) {
  return request<{ success: boolean }>(`/llm/conversations/${id}`, { method: 'DELETE' })
}

export function listModels() {
  return request<ModelInfo[]>('/llm/models')
}

export function listAssistantPresets() {
  return request<AssistantPreset[]>('/llm/assistant-presets')
}

export function listProjects() {
  return request<LlmProject[]>('/llm/projects')
}

export function createProject(payload: { name: string; description?: string; color?: string | null }) {
  return request<LlmProject>('/llm/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateProject(
  id: string,
  payload: Partial<Pick<LlmProject, 'name' | 'description' | 'color' | 'pinned' | 'archived'>>,
) {
  return request<LlmProject>(`/llm/projects/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function updateMessage(id: string, payload: { feedback?: 'like' | 'dislike' }) {
  return request<Message>(`/llm/messages/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function streamChat(
  payload: {
    conversation_id?: string | null
    model_id?: string | null
    assistant_preset_id?: string | null
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
  const response = await fetch(`${API_BASE}/llm/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
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
        const event = chunk
          .split('\n')
          .find((line) => line.startsWith('event:'))
          ?.replace('event:', '')
          .trim()
        const dataLine = chunk
          .split('\n')
          .find((line) => line.startsWith('data:'))
          ?.replace('data:', '')
          .trim()
        if (!event || !dataLine) continue
        handlers.onEvent(event, JSON.parse(dataLine))
      }
    }
    handlers.onDone?.()
  } catch (error) {
    handlers.onError?.(error instanceof Error ? error : new Error(String(error)))
  }
}

export type { Message }
