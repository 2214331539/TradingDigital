import { useEffect, useMemo, useState } from 'react'
import { listPermissions, listRoles, updateRolePermissions } from '../api'
import type { PermissionInfo, RoleInfo } from '../../../shared/types'

export function RolesPage() {
  const [roles, setRoles] = useState<RoleInfo[]>([])
  const [permissions, setPermissions] = useState<PermissionInfo[]>([])
  const permissionMap = useMemo(
    () => new Map(permissions.map((permission) => [permission.id, permission])),
    [permissions],
  )

  async function reload() {
    const [roleData, permissionData] = await Promise.all([listRoles(), listPermissions()])
    setRoles(roleData)
    setPermissions(permissionData)
  }

  useEffect(() => {
    reload()
  }, [])

  return (
    <section className="admin-page">
      <header className="admin-page-header">
        <h1>角色</h1>
        <p>权限码固定使用 模块.资源.动作。</p>
      </header>
      <div className="role-grid">
        {roles.map((role) => (
          <article className="role-card" key={role.id}>
            <h2>{role.name}</h2>
            <p>{role.code}</p>
            <div className="permission-list">
              {permissions.map((permission) => (
                <label key={permission.id}>
                  <input
                    type="checkbox"
                    checked={role.permissions.includes(permission.code)}
                    onChange={async (event) => {
                      const nextCodes = event.target.checked
                        ? [...role.permissions, permission.code]
                        : role.permissions.filter((code) => code !== permission.code)
                      const nextIds = nextCodes
                        .map((code) => permissions.find((item) => item.code === code)?.id)
                        .filter(Boolean) as string[]
                      await updateRolePermissions(role.id, nextIds)
                      reload()
                    }}
                  />
                  <span>{permissionMap.get(permission.id)?.code}</span>
                </label>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}

