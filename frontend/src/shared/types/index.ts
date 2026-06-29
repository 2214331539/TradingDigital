export type ApiResponse<T> = {
  code: string
  message: string
  data: T
}

export type Enterprise = {
  id: string
  name: string
  code: string
  status: string
}

export type User = {
  id: string
  enterprise_id: string
  email: string
  name: string | null
  avatar_url: string | null
  status: string
  roles: string[]
  permissions: string[]
  last_login_at: string | null
  created_at: string
}

export type AuthMe = {
  user: User
  enterprise: Enterprise
  roles: string[]
  permissions: string[]
  isAuthenticated: boolean
}

export type PageResult<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
}

export type Conversation = {
  id: string
  title: string
  assistant_preset_id: string | null
  assistant_id: string | null
  model_id: string | null
  project_id: string | null
  status: string
  archived: boolean
  is_archived: boolean
  pinned: boolean
  is_favorited: boolean
  temporary: boolean
  is_temporary: boolean
  message_count: number
  last_message_at: string | null
  created_at: string
  updated_at: string
}

export type Message = {
  id: string
  conversation_id: string
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  metadata_json: Record<string, unknown> | null
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
  provider_code: string
  provider: string
  model_key: string
  display_name: string
  name: string
  type: string
  context_length: number
  max_output_tokens: number
  support_streaming: boolean
  enabled: boolean
  is_default: boolean
}

export type AssistantPreset = {
  id: string
  name: string
  description: string | null
  system_prompt: string
  visibility: string
  icon: string | null
  default_model_id: string | null
}

export type LlmProject = {
  id: string
  enterprise_id: string
  user_id: string
  name: string
  description: string | null
  color: string | null
  pinned: boolean
  archived: boolean
  created_at: string
  updated_at: string
}

export type RoleInfo = {
  id: string
  code: string
  name: string
  description: string | null
  is_system: boolean
  permissions: string[]
}

export type PermissionInfo = {
  id: string
  code: string
  name: string
  module: string
  resource: string
  action: string
  description: string | null
}

export type AuditLog = {
  id: string
  enterprise_id: string
  user_id: string | null
  module: string
  action: string
  resource_type: string | null
  resource_id: string | null
  detail_json: Record<string, unknown> | null
  ip_address: string | null
  user_agent: string | null
  created_at: string
}

export type KnowledgeBase = {
  id: string
  name: string
  description: string | null
  type: string
  status: string
  created_by: string
  created_at: string
  updated_at: string
}
