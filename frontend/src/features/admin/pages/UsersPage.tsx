import { useEffect, useState } from 'react'
import { listRoles, listUsers, updateUserRoles, updateUserStatus } from '../api'
import type { RoleInfo, User } from '../../../shared/types'

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [roles, setRoles] = useState<RoleInfo[]>([])

  async function reload() {
    const [userData, roleData] = await Promise.all([listUsers(), listRoles()])
    setUsers(userData.items)
    setRoles(roleData)
  }

  useEffect(() => {
    reload()
  }, [])

  return (
    <section className="admin-page">
      <header className="admin-page-header">
        <h1>用户</h1>
        <p>企业成员由 SSO 登录后自动同步。</p>
      </header>
      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th>用户</th>
              <th>状态</th>
              <th>角色</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>
                  <strong>{user.name ?? user.email}</strong>
                  <small>{user.email}</small>
                </td>
                <td>{user.status}</td>
                <td>
                  <select
                    value={user.roles[0] ?? ''}
                    onChange={async (event) => {
                      await updateUserRoles(user.id, [event.target.value])
                      reload()
                    }}
                  >
                    {roles.map((role) => (
                      <option key={role.id} value={role.id}>
                        {role.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <button
                    className="ghost-button"
                    onClick={async () => {
                      await updateUserStatus(user.id, user.status === 'active' ? 'disabled' : 'active')
                      reload()
                    }}
                  >
                    {user.status === 'active' ? '禁用' : '启用'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

