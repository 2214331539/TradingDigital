import { ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'

export function ForbiddenPage() {
  return (
    <main className="forbidden-page">
      <ShieldAlert size={28} />
      <h1>403</h1>
      <p>当前账号没有访问该页面的权限。</p>
      <Link to="/app">返回模块入口</Link>
    </main>
  )
}
