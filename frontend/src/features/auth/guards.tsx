import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../app/providers/auth-context'

export function RequireAuth() {
  const { loading, isAuthenticated } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <main className="boot-screen">
        <div className="mark">T</div>
      </main>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return <Outlet />
}

export function RequirePermission({ permission }: { permission: string }) {
  const { hasPermission } = useAuth()
  if (!hasPermission(permission)) {
    return <Navigate to="/403" replace />
  }
  return <Outlet />
}
