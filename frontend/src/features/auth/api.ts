import { API_BASE, request } from '../../shared/api/http'
import type { AuthMe } from '../../shared/types'

export function ssoLoginUrl(redirect = '/app') {
  const query = new URLSearchParams({
    enterprise_code: 'default',
    redirect_after_login: redirect,
  })
  return `${API_BASE}/auth/sso/login?${query}`
}

export function getMe() {
  return request<AuthMe>('/auth/me')
}

export function logout() {
  return request<{ success: boolean }>('/auth/logout', { method: 'POST' })
}
