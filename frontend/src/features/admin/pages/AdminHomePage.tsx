import { Activity, ShieldCheck, UsersRound } from 'lucide-react'
import { useAuth } from '../../../app/providers/auth-context'

export function AdminHomePage() {
  const { auth } = useAuth()

  return (
    <section className="admin-page">
      <header className="admin-page-header">
        <h1>企业管理</h1>
        <p>{auth?.enterprise.name}</p>
      </header>
      <div className="admin-metrics">
        <article>
          <UsersRound size={20} />
          <span>用户与角色</span>
          <strong>IAM</strong>
        </article>
        <article>
          <ShieldCheck size={20} />
          <span>权限控制</span>
          <strong>RBAC</strong>
        </article>
        <article>
          <Activity size={20} />
          <span>审计追踪</span>
          <strong>Audit</strong>
        </article>
      </div>
    </section>
  )
}
