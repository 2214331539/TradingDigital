import { request } from '../../shared/api/http'
import type { AuditLog, PageResult, PermissionInfo, RoleInfo, User } from '../../shared/types'

export function listUsers() {
  return request<PageResult<User>>('/platform/users?page_size=100')
}

export function updateUserStatus(userId: string, status: string) {
  return request<User>(`/platform/users/${userId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

export function updateUserRoles(userId: string, role_ids: string[]) {
  return request<User>(`/platform/users/${userId}/roles`, {
    method: 'PATCH',
    body: JSON.stringify({ role_ids }),
  })
}

export function listRoles() {
  return request<RoleInfo[]>('/platform/roles')
}

export function listPermissions() {
  return request<PermissionInfo[]>('/platform/permissions')
}

export function updateRolePermissions(roleId: string, permission_ids: string[]) {
  return request<RoleInfo>(`/platform/roles/${roleId}/permissions`, {
    method: 'PATCH',
    body: JSON.stringify({ permission_ids }),
  })
}

export function listAuditLogs() {
  return request<AuditLog[]>('/audit/logs')
}

