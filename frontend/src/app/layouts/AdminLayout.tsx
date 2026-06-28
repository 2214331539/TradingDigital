import { ClipboardList, Home, UsersRound } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

export function AdminLayout() {
  return (
    <div className="admin-layout td-admin-layout">
      <aside className="admin-sidebar">
        <div className="brand-row">
          <div className="mark small">T</div>
          <span>企业管理</span>
        </div>
        <NavLink className="admin-nav" to="/admin" end>
          <Home size={18} />
          总览
        </NavLink>
        <NavLink className="admin-nav" to="/admin/users">
          <UsersRound size={18} />
          用户
        </NavLink>
        <NavLink className="admin-nav" to="/admin/roles">
          <UsersRound size={18} />
          角色
        </NavLink>
        <NavLink className="admin-nav" to="/admin/audit-logs">
          <ClipboardList size={18} />
          审计日志
        </NavLink>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  )
}
