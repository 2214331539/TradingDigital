import { request } from '../../shared/api/http'
import type { KnowledgeBase } from '../../shared/types'

export function listKnowledgeBases() {
  return request<KnowledgeBase[]>('/kb/knowledge-bases')
}

