import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../../app/providers/theme-context'

export function ThemeToggle({ className = 'icon-button' }: { className?: string }) {
  const { theme, toggleTheme } = useTheme()
  const isDark = theme === 'dark'

  return (
    <button
      type="button"
      className={`theme-toggle ${className}`}
      onClick={toggleTheme}
      title={isDark ? '切换到浅色主题' : '切换到深色主题'}
      aria-label={isDark ? '切换到浅色主题' : '切换到深色主题'}
    >
      {isDark ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  )
}
