export type ApiResponse<T> = {
  code: string
  message: string
  data: T
}

export type User = {
  id: string
  username: string
  email: string
  status: string
  roles: string[]
  permissions: string[]
}

export type Conversation = {
  id: string
  title: string
  project_id: string | null
  model_id: string | null
  assistant_id: string | null
  status: string
  is_archived: boolean
  is_favorited: boolean
  is_temporary: boolean
  message_count: number
  last_message_at: string | null
  created_at: string
  updated_at: string
}

export type Message = {
  id: string
  conversation_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  status: 'pending' | 'streaming' | 'completed' | 'stopped' | 'failed'
  model_id: string | null
  created_at: string
  updated_at: string
}

export type ConversationDetail = Conversation & {
  messages: Message[]
}

export type ModelInfo = {
  id: string
  name: string
  provider: string
  model_key: string
  context_length: number
  max_output_tokens: number
  enabled: boolean
  is_default: boolean
}

export type AssistantPreset = {
  id: string
  name: string
  description: string | null
  icon: string | null
  default_model_id: string | null
}

export type Project = {
  id: string
  name: string
  description: string | null
  icon: string
  color: string | null
  sort_order: number
  is_archived: boolean
  created_at: string
  updated_at: string
}

export type PageResult<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
}

export type AdminUser = {
  id: string
  username: string
  email: string
  status: string
  roles: string[]
  last_login_at: string | null
  created_at: string
}

export type RoleInfo = {
  id: string
  name: string
  code: string
  description: string | null
  is_system: boolean
}

export type Dashboard = {
  total_users: number
  active_users_today: number
  messages_today: number
  model_calls_today: number
  avg_latency_ms: number
  failure_rate: number
  current_admin: string
}
