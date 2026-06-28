import type { ApiResponse } from '../types'

export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  `${window.location.protocol}//${window.location.hostname}:8000/api/v1`

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })

  const text = await response.text()
  const payload = text ? (JSON.parse(text) as ApiResponse<T>) : null
  if (!response.ok) {
    throw new Error(payload?.message || payload?.code || response.statusText)
  }
  return payload?.data as T
}

