import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getMe, logout as logoutRequest } from '../../features/auth/api'
import type { AuthMe } from '../../shared/types'
import { AuthContext } from './auth-context'
import type { AuthState } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthMe | null>(null)
  const [loading, setLoading] = useState(true)

  async function reload() {
    setLoading(true)
    try {
      setAuth(await getMe())
    } catch {
      setAuth(null)
    } finally {
      setLoading(false)
    }
  }

  async function logout() {
    try {
      await logoutRequest()
    } finally {
      setAuth(null)
      window.location.assign('/login')
    }
  }

  useEffect(() => {
    reload()
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      auth,
      loading,
      isAuthenticated: Boolean(auth?.isAuthenticated),
      hasPermission: (permission: string) => Boolean(auth?.permissions.includes(permission)),
      reload,
      logout,
    }),
    [auth, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
