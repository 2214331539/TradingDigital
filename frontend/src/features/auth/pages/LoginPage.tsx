import { LogIn } from 'lucide-react'
import { ssoLoginUrl } from '../api'

export function LoginPage() {
  return (
    <main className="login-page tradedigital-login">
      <section className="login-card">
        <div className="login-mark">T</div>
        <h1>电商数字化</h1>
        <p className="login-subtitle">TradeDigital</p>
        <button className="primary-button sso-button" onClick={() => window.location.assign(ssoLoginUrl())}>
          <LogIn size={18} />
          使用企业 SSO 登录
        </button>
      </section>
    </main>
  )
}

