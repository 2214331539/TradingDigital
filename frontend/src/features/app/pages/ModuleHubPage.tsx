import { ArrowRight, BookOpen, Bot, Building2, LogOut } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../../app/providers/auth-context'
import { ThemeToggle } from '../../../shared/components/ThemeToggle'

type ModuleCard = {
  title: string
  description: string
  path: string
  permission: string
  icon: typeof Bot
}

const MODULES: ModuleCard[] = [
  {
    title: 'llm',
    description: '进入 ChatGPT 风格的模型对话工作区。',
    path: '/app/llm',
    permission: 'llm.chat.use',
    icon: Bot,
  },
  {
    title: '知识库',
    description: '管理企业知识库、数据源与工具接入。',
    path: '/app/knowledge',
    permission: 'kb.knowledge_base.read',
    icon: BookOpen,
  },
  {
    title: '企业管理',
    description: '用户、角色、权限与审计日志管理。',
    path: '/admin',
    permission: 'platform.admin.access',
    icon: Building2,
  },
]

export function ModuleHubPage() {
  const { auth, hasPermission, logout } = useAuth()
  const modules = MODULES.filter((item) => hasPermission(item.permission))

  return (
    <main className="module-hub">
      <header className="module-hub-header">
        <div>
          <span className="module-hub-kicker">TradeDigital</span>
          <h1>电商数字化</h1>
        </div>
        <div className="module-hub-account">
          <span className="user-avatar">{auth?.user.name?.slice(0, 1) ?? auth?.user.email.slice(0, 1)}</span>
          <span>
            <strong>{auth?.user.name ?? auth?.user.email}</strong>
            <small>{auth?.enterprise.name}</small>
          </span>
          <ThemeToggle />
          <button className="icon-button" onClick={logout} title="退出登录">
            <LogOut size={17} />
          </button>
        </div>
      </header>

      <section className="module-hub-panel">
        <div className="module-hub-title">
          <h2>选择功能模块</h2>
          <p>登录后先进入平台模块入口，再进入独立业务工作区。</p>
        </div>
        <div className="module-card-grid">
          {modules.map((item) => {
            const Icon = item.icon
            return (
              <Link className="module-card" to={item.path} key={item.path}>
                <span className="module-card-icon">
                  <Icon size={22} />
                </span>
                <span>
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </span>
                <ArrowRight size={18} />
              </Link>
            )
          })}
        </div>
      </section>
    </main>
  )
}
