import { useEffect, useState } from 'react'
import { listAuditLogs } from '../api'
import type { AuditLog } from '../../../shared/types'

export function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])

  useEffect(() => {
    listAuditLogs().then(setLogs)
  }, [])

  return (
    <section className="admin-page">
      <header className="admin-page-header">
        <h1>审计日志</h1>
        <p>记录登录、权限不足、角色变更、模型调用等关键行为。</p>
      </header>
      <div className="table-panel">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>模块</th>
              <th>动作</th>
              <th>资源</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{new Date(log.created_at).toLocaleString()}</td>
                <td>{log.module}</td>
                <td>{log.action}</td>
                <td>{log.resource_type ?? '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
