import { createContext, useContext } from 'react'
import type { AuthMe } from '../../shared/types'

export type AuthState = {
  auth: AuthMe | null
  loading: boolean
  isAuthenticated: boolean
  hasPermission: (permission: string) => boolean
  reload: () => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

