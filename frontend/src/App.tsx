import {
  Archive,
  AudioLines,
  Check,
  ChevronDown,
  Copy,
  Folder,
  Globe2,
  Images,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquarePlus,
  Mic,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  PenLine,
  Pin,
  Plus,
  RefreshCcw,
  Search,
  Send,
  Settings,
  Share2,
  Shield,
  SlidersHorizontal,
  Sparkles,
  Square,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  Users,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent, ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import './App.css'
import {
  adminDashboard,
  adminModels,
  adminOperationLogs,
  adminRoles,
  adminUsers,
  assistants,
  availableModels,
  clearToken,
  deleteConversation,
  getConversation,
  getToken,
  listConversations,
  listProjects,
  login,
  me,
  streamChat,
  updateConversation,
} from './lib/api'
import type {
  AdminUser,
  Conversation,
  Dashboard,
  Message,
  ModelInfo,
  Project,
  RoleInfo,
  User,
} from './types'

type View = 'chat' | 'admin'

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [booting, setBooting] = useState(true)
  const [view, setView] = useState<View>('chat')

  useEffect(() => {
    if (!getToken()) {
      setBooting(false)
      return
    }
    me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setBooting(false))
  }, [])

  if (booting) {
    return (
      <main className="boot-screen">
        <div className="mark">C</div>
      </main>
    )
  }

  if (!user) {
    return <LoginPage onLogin={setUser} />
  }

  return (
    <AppShell
      user={user}
      view={view}
      onViewChange={setView}
      onLogout={() => {
        clearToken()
        setUser(null)
        setView('chat')
      }}
    />
  )
}

function LoginPage({ onLogin }: { onLogin: (user: User) => void }) {
  const [email, setEmail] = useState('user@chatai.local')
  const [password, setPassword] = useState('User@123456')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await login(email, password)
      localStorage.setItem('chatai_token', data.access_token)
      onLogin(data.user)
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="login-mark">C</div>
        <h1>ChatAI</h1>
        <div className="field">
          <label>邮箱</label>
          <input value={email} onChange={(event) => setEmail(event.target.value)} />
        </div>
        <div className="field">
          <label>密码</label>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        {error ? <p className="form-error">{error}</p> : null}
        <button className="primary-button" disabled={loading} type="submit">
          {loading ? '登录中' : '登录'}
        </button>
      </form>
    </main>
  )
}

function AppShell({
  user,
  view,
  onViewChange,
  onLogout,
}: {
  user: User
  view: View
  onViewChange: (view: View) => void
  onLogout: () => void
}) {
  const canAdmin = user.permissions.includes('user:read') || user.roles.includes('super_admin')

  return (
    <div className="app-shell">
      {view === 'chat' ? (
        <ChatWorkspace user={user} canAdmin={canAdmin} onAdmin={() => onViewChange('admin')} onLogout={onLogout} />
      ) : (
        <AdminWorkspace user={user} onChat={() => onViewChange('chat')} onLogout={onLogout} />
      )}
    </div>
  )
}

function ChatWorkspace({
  user,
  canAdmin,
  onAdmin,
  onLogout,
}: {
  user: User
  canAdmin: boolean
  onAdmin: () => void
  onLogout: () => void
}) {
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window === 'undefined') return true
    return window.innerWidth > 980
  })
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [current, setCurrent] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [models, setModels] = useState<ModelInfo[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [selectedAssistant, setSelectedAssistant] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [modelOpen, setModelOpen] = useState(false)
  const [productOpen, setProductOpen] = useState(false)
  const [conversationMenuOpen, setConversationMenuOpen] = useState(false)
  const [isTemporary, setIsTemporary] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const abortRef = useRef<AbortController | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    reloadConversations()
    listProjects()
      .then(setProjects)
      .catch(() => setProjects([]))
    availableModels().then((rows) => {
      setModels(rows)
      setSelectedModel(rows.find((row) => row.is_default)?.id ?? rows[0]?.id ?? null)
    })
    assistants().then((rows) => {
      setSelectedAssistant(rows[0]?.id ?? null)
    })
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, generating])

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
      if (event.key === 'Escape') {
        setSearchOpen(false)
        setAccountOpen(false)
        setSettingsOpen(false)
        setModelOpen(false)
        setProductOpen(false)
        setConversationMenuOpen(false)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  async function reloadConversations() {
    const data = await listConversations()
    setConversations(data.items)
  }

  async function selectConversation(conversation: Conversation) {
    setError('')
    setIsTemporary(false)
    setSearchOpen(false)
    setConversationMenuOpen(false)
    const detail = await getConversation(conversation.id)
    setCurrent(detail)
    setMessages(detail.messages)
    setSelectedModel(detail.model_id)
    setSelectedAssistant(detail.assistant_id)
  }

  function newChat(temporary = false) {
    setCurrent(null)
    setMessages([])
    setInput('')
    setError('')
    setIsTemporary(temporary)
    setProductOpen(false)
    setConversationMenuOpen(false)
  }

  async function sendMessage() {
    const content = input.trim()
    if (!content || generating) return
    const controller = new AbortController()
    abortRef.current = controller
    setGenerating(true)
    setError('')
    setInput('')

    await streamChat(
      {
        conversation_id: current?.id,
        model_id: selectedModel,
        assistant_id: selectedAssistant,
        content,
        temporary: isTemporary,
      },
      {
        onEvent(event, data) {
          if (event === 'message_start') {
            setCurrent(data.conversation)
            setMessages((prev) => [...prev, data.user_message, data.assistant_message])
          }
          if (event === 'delta') {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === data.message_id
                  ? { ...message, content: message.content + data.content, status: 'streaming' }
                  : message,
              ),
            )
          }
          if (event === 'message_end') {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === data.message_id
                  ? { ...message, content: data.content, status: 'completed' }
                  : message,
              ),
            )
            reloadConversations()
          }
          if (event === 'error') {
            setError(data.message)
          }
        },
        onDone() {
          setGenerating(false)
          abortRef.current = null
        },
        onError(err) {
          if (err.name !== 'AbortError') setError(err.message)
          setGenerating(false)
        },
      },
      controller.signal,
    ).catch((err) => {
      setError(err instanceof Error ? err.message : '发送失败')
      setGenerating(false)
    })
  }

  function stopGeneration() {
    abortRef.current?.abort()
    abortRef.current = null
    setGenerating(false)
    setMessages((prev) =>
      prev.map((message) =>
        message.status === 'streaming' ? { ...message, status: 'stopped' } : message,
      ),
    )
  }

  async function toggleFavorite(conversation: Conversation) {
    const updated = await updateConversation(conversation.id, {
      is_favorited: !conversation.is_favorited,
    })
    setCurrent((prev) => (prev?.id === updated.id ? { ...prev, ...updated } : prev))
    setConversationMenuOpen(false)
    reloadConversations()
  }

  async function archiveConversation(conversation: Conversation) {
    await updateConversation(conversation.id, { is_archived: true })
    if (current?.id === conversation.id) newChat()
    setConversationMenuOpen(false)
    reloadConversations()
  }

  async function removeConversation(conversation: Conversation) {
    await deleteConversation(conversation.id)
    if (current?.id === conversation.id) newChat()
    setConversationMenuOpen(false)
    reloadConversations()
  }

  const filteredConversations = useMemo(() => {
    if (!search.trim()) return conversations
    const value = search.toLowerCase()
    return conversations.filter((conversation) => conversation.title.toLowerCase().includes(value))
  }, [conversations, search])

  const knownProjectIds = new Set(projects.map((project) => project.id))
  const pinnedConversations = filteredConversations.filter((conversation) => conversation.is_favorited)
  const projectGroups = projects
    .map((project) => ({
      project,
      items: filteredConversations.filter(
        (conversation) => conversation.project_id === project.id && !conversation.is_favorited,
      ),
    }))
    .filter((group) => !search.trim() || group.items.length > 0)
  const regularConversations = filteredConversations.filter(
    (conversation) =>
      !conversation.is_favorited &&
      (!conversation.project_id || !knownProjectIds.has(conversation.project_id)),
  )
  const groups = groupConversations(regularConversations)
  const activeModel = models.find((model) => model.id === selectedModel)
  const isEmpty = messages.length === 0
  const hasMiddleSections = pinnedConversations.length > 0 || projectGroups.length > 0

  function renderConversationItem(conversation: Conversation, nested = false) {
    return (
      <button
        className={`conversation-item ${nested ? 'nested' : ''} ${current?.id === conversation.id ? 'active' : ''}`}
        key={conversation.id}
        onClick={() => selectConversation(conversation)}
      >
        <span>{conversation.title}</span>
        <span className="conversation-tools">
          {conversation.is_favorited ? <Pin size={13} fill="currentColor" /> : null}
          <MoreHorizontal size={15} />
        </span>
      </button>
    )
  }

  return (
    <div className="chat-layout" data-sidebar={sidebarOpen ? 'open' : 'closed'}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <button className="brand-button" onClick={() => newChat(false)}>
            <div className="mark small">C</div>
            <span>ChatAI</span>
          </button>
          <button className="icon-button" onClick={() => setSidebarOpen(false)} title="关闭侧栏">
            <PanelLeftClose size={18} />
          </button>
        </div>

        <div className="sidebar-primary">
          <button className="sidebar-command" onClick={() => newChat(false)}>
            <PenLine size={18} />
            <span>New chat</span>
          </button>
          <label className="sidebar-command search-command">
            <Search size={18} />
            <input
              placeholder="Search chats"
              value={search}
              onFocus={() => setSearchOpen(true)}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>

        {pinnedConversations.length > 0 ? (
          <div className="sidebar-section pinned-section">
            <div className="sidebar-section-title">
              <span>Pinned</span>
            </div>
            {pinnedConversations.map((conversation) => renderConversationItem(conversation))}
          </div>
        ) : null}

        {projectGroups.length > 0 ? (
          <div className="sidebar-section projects-section">
            <div className="sidebar-section-title">
              <span>Projects</span>
            </div>
            {projectGroups.map(({ project, items }) => (
              <section className="project-group" key={project.id}>
                <button className="sidebar-command compact project-title">
                  <Folder size={17} />
                  <span>{project.name}</span>
                </button>
                {items.length > 0 ? (
                  <div className="project-conversations">
                    {items.map((conversation) => renderConversationItem(conversation, true))}
                  </div>
                ) : null}
              </section>
            ))}
          </div>
        ) : null}

        <nav className={`conversation-nav ${!hasMiddleSections ? 'no-sections' : ''}`}>
          <div className="history-label">Chats</div>
          {groups.map((group) => (
            <section key={group.label} className="conversation-group">
              <p>{group.label}</p>
              {group.items.map((conversation) => renderConversationItem(conversation))}
            </section>
          ))}
        </nav>
        <div className="sidebar-footer">
          {canAdmin ? (
            <button className="account-button" onClick={onAdmin}>
              <Shield size={18} />
              <span>管理后台</span>
            </button>
          ) : null}
          <button className="account-card" onClick={() => setAccountOpen((value) => !value)}>
            <span className="user-avatar">{user.username.slice(0, 1).toUpperCase()}</span>
            <span className="account-copy">
              <strong>{user.username}</strong>
              <small>Pro</small>
            </span>
            <MoreHorizontal size={16} />
          </button>
          {accountOpen ? (
            <AccountMenu
              canAdmin={canAdmin}
              onAdmin={onAdmin}
              onSettings={() => {
                setSettingsOpen(true)
                setAccountOpen(false)
              }}
              onLogout={onLogout}
            />
          ) : null}
        </div>
      </aside>

      <main className={`chat-main ${isEmpty ? 'is-empty' : 'has-chat'}`}>
        <header className="chat-header">
          {!sidebarOpen ? (
            <button className="icon-button" onClick={() => setSidebarOpen(true)} title="展开侧栏">
              <PanelLeftOpen size={18} />
            </button>
          ) : (
            <button className="mobile-menu icon-button" onClick={() => setSidebarOpen(true)}>
              <Menu size={18} />
            </button>
          )}
          <div className="product-switcher">
            <button className="product-button" onClick={() => setProductOpen((value) => !value)}>
              <span>ChatAI</span>
              <ChevronDown size={16} />
            </button>
            {isTemporary ? <span className="temp-chip">临时</span> : null}
            {productOpen ? (
              <ProductMenu
                onNewChat={() => newChat(false)}
                onTemporary={() => newChat(true)}
                onSettings={() => {
                  setSettingsOpen(true)
                  setProductOpen(false)
                }}
              />
            ) : null}
          </div>
          <button className="model-picker" onClick={() => setModelOpen((value) => !value)}>
            <span>{activeModel?.name ?? '选择模型'}</span>
            <ChevronDown size={15} />
          </button>
          {modelOpen ? (
            <ModelPanel
              models={models}
              selectedModel={selectedModel}
              onSelect={(id) => {
                setSelectedModel(id)
                setModelOpen(false)
              }}
            />
          ) : null}
          <div className="header-actions">
            {current ? (
              <button className="share-button">
                <Share2 size={16} />
                Share
              </button>
            ) : null}
            {current ? (
              <>
                <button
                  className="icon-button"
                  onClick={() => setConversationMenuOpen((value) => !value)}
                  title="More"
                >
                  <MoreHorizontal size={20} />
                </button>
                {conversationMenuOpen ? (
                  <section className="conversation-menu">
                    <button onClick={() => toggleFavorite(current)}>
                      <Pin size={17} fill={current.is_favorited ? 'currentColor' : 'none'} />
                      {current.is_favorited ? '取消置顶' : '置顶'}
                    </button>
                    <button onClick={() => archiveConversation(current)}>
                      <Archive size={17} />
                      归档
                    </button>
                    <button className="danger" onClick={() => removeConversation(current)}>
                      <Trash2 size={17} />
                      删除
                    </button>
                  </section>
                ) : null}
              </>
            ) : null}
          </div>
        </header>

        <section className="message-scroll">
          {isEmpty ? (
            <EmptyChat
              temporary={isTemporary}
            />
          ) : (
            <>
              {isTemporary ? <div className="temporary-banner">当前为临时聊天</div> : null}
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              <div ref={endRef} />
            </>
          )}
        </section>

        <footer className="composer-shell">
          {error ? (
            <div className="inline-error">
              <X size={15} />
              {error}
            </div>
          ) : null}
          <div className="composer">
            <button className="composer-icon" title="添加">
              <Plus size={20} />
            </button>
            <textarea
              value={input}
              placeholder="Ask anything"
              rows={1}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event: KeyboardEvent<HTMLTextAreaElement>) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  sendMessage()
                }
              }}
            />
            <div className="composer-tools">
              <button className="composer-pill instant-pill">
                Instant
                <ChevronDown size={15} />
              </button>
              <button className="composer-round" title="Voice input">
                <Mic size={18} />
              </button>
            </div>
            <button
              className="send-button"
              disabled={!input.trim() && !generating}
              onClick={generating ? stopGeneration : sendMessage}
            >
              {generating ? (
                <Square size={15} fill="currentColor" />
              ) : input.trim() ? (
                <Send size={16} />
              ) : (
                <AudioLines size={22} />
              )}
            </button>
          </div>
          {isEmpty ? (
            <div className="composer-suggestions">
              <button onClick={() => setInput('Create an image prompt for a product launch poster')}>
                <Images size={17} />
                Create an image
              </button>
              <button onClick={() => setInput('Help me write and edit a concise product update')}>
                <PenLine size={17} />
                Write or edit
              </button>
              <button onClick={() => setInput('Look up recent information and summarize the key points')}>
                <Globe2 size={17} />
                Look something up
              </button>
            </div>
          ) : null}
          <p className="composer-note">
            ChatAI can make mistakes. Check important info.
          </p>
        </footer>
        {searchOpen ? (
          <SearchDialog
            search={search}
            conversations={filteredConversations}
            onSearch={setSearch}
            onClose={() => setSearchOpen(false)}
            onSelect={selectConversation}
          />
        ) : null}
        {settingsOpen ? (
          <SettingsDialog
            user={user}
            activeModel={activeModel}
            onClose={() => setSettingsOpen(false)}
          />
        ) : null}
      </main>
    </div>
  )
}

function EmptyChat({
  temporary,
}: {
  temporary: boolean
}) {
  return (
    <div className="empty-chat">
      <h2>Ready when you are.</h2>
      {temporary ? <p>Temporary chat</p> : null}
    </div>
  )
}

function SearchDialog({
  search,
  conversations,
  onSearch,
  onClose,
  onSelect,
}: {
  search: string
  conversations: Conversation[]
  onSearch: (value: string) => void
  onClose: () => void
  onSelect: (conversation: Conversation) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  return (
    <div className="modal-backdrop search-backdrop" onMouseDown={onClose}>
      <section className="search-dialog" onMouseDown={(event) => event.stopPropagation()}>
        <div className="search-dialog-input">
          <Search size={19} />
          <input
            ref={inputRef}
            placeholder="搜索聊天"
            value={search}
            onChange={(event) => onSearch(event.target.value)}
          />
          <kbd>Esc</kbd>
        </div>
        <div className="search-results">
          {conversations.length === 0 ? (
            <div className="search-empty">没有找到聊天</div>
          ) : (
            conversations.slice(0, 12).map((conversation) => (
              <button key={conversation.id} onClick={() => onSelect(conversation)}>
                <MessageSquarePlus size={17} />
                <span>
                  <strong>{conversation.title}</strong>
                  <small>{formatTime(conversation.updated_at)}</small>
                </span>
              </button>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

function ModelPanel({
  models,
  selectedModel,
  onSelect,
}: {
  models: ModelInfo[]
  selectedModel: string | null
  onSelect: (id: string) => void
}) {
  return (
    <section className="model-panel">
      <div className="menu-label">模型</div>
      {models.map((model) => (
        <button
          key={model.id}
          className={model.id === selectedModel ? 'selected' : ''}
          onClick={() => onSelect(model.id)}
        >
          <span>
            <strong>{model.name}</strong>
            <small>
              {model.provider === 'mock' ? '本地开发模式' : model.provider}
              {' · '}
              {model.context_length.toLocaleString()} 上下文
            </small>
          </span>
          {model.id === selectedModel ? <Check size={17} /> : null}
        </button>
      ))}
      <div className="model-panel-footer">
        <SlidersHorizontal size={15} />
        模型由管理员在后台配置
      </div>
    </section>
  )
}

function ProductMenu({
  onNewChat,
  onTemporary,
  onSettings,
}: {
  onNewChat: () => void
  onTemporary: () => void
  onSettings: () => void
}) {
  return (
    <section className="product-menu">
      <button onClick={onNewChat}>
        <PenLine size={17} />
        新聊天
      </button>
      <button onClick={onTemporary}>
        <Sparkles size={17} />
        临时聊天
      </button>
      <button onClick={onSettings}>
        <Settings size={17} />
        设置
      </button>
    </section>
  )
}

function AccountMenu({
  canAdmin,
  onAdmin,
  onSettings,
  onLogout,
}: {
  canAdmin: boolean
  onAdmin: () => void
  onSettings: () => void
  onLogout: () => void
}) {
  return (
    <section className="account-menu">
      <button onClick={onSettings}>
        <Settings size={17} />
        设置
      </button>
      {canAdmin ? (
        <button onClick={onAdmin}>
          <Shield size={17} />
          管理后台
        </button>
      ) : null}
      <button>
        <Archive size={17} />
        归档的聊天
      </button>
      <button className="danger" onClick={onLogout}>
        <LogOut size={17} />
        退出登录
      </button>
    </section>
  )
}

function SettingsDialog({
  user,
  activeModel,
  onClose,
}: {
  user: User
  activeModel?: ModelInfo
  onClose: () => void
}) {
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <section className="settings-dialog" onMouseDown={(event) => event.stopPropagation()}>
        <aside className="settings-tabs">
          <h2>设置</h2>
          <button className="active">通用</button>
          <button>个人资料</button>
          <button>数据控制</button>
          <button>安全</button>
        </aside>
        <div className="settings-panel">
          <div className="settings-header">
            <h3>通用</h3>
            <button className="icon-button" onClick={onClose}>
              <X size={18} />
            </button>
          </div>
          <div className="setting-row">
            <span>
              <strong>主题</strong>
              <small>跟随系统外观</small>
            </span>
            <select defaultValue="system">
              <option value="system">系统</option>
              <option value="light">浅色</option>
              <option value="dark">深色</option>
            </select>
          </div>
          <div className="setting-row">
            <span>
              <strong>默认模型</strong>
              <small>{activeModel?.name ?? 'ChatAI Default'}</small>
            </span>
            <button>管理</button>
          </div>
          <div className="setting-row">
            <span>
              <strong>账号</strong>
              <small>{user.email}</small>
            </span>
            <button>查看</button>
          </div>
          <div className="setting-row">
            <span>
              <strong>数据控制</strong>
              <small>导出、归档和删除会话数据</small>
            </span>
            <button>打开</button>
          </div>
        </div>
      </section>
    </div>
  )
}

function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <article className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser ? (
        <div className="assistant-avatar" aria-hidden="true">
          <Sparkles size={16} />
        </div>
      ) : null}
      <div className="message-bubble">
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex, rehypeHighlight]}
          >
            {message.content || ' '}
          </ReactMarkdown>
        )}
        <div className="message-actions">
          <button onClick={() => navigator.clipboard.writeText(message.content)}>
            <Copy size={14} />
          </button>
          {!isUser ? (
            <>
              <button>
                <RefreshCcw size={14} />
              </button>
              <button>
                <ThumbsUp size={14} />
              </button>
              <button>
                <ThumbsDown size={14} />
              </button>
            </>
          ) : (
            <button>
              <PenLine size={14} />
            </button>
          )}
          {!isUser && message.status === 'streaming' ? <span className="typing-dot" /> : null}
        </div>
      </div>
    </article>
  )
}

function AdminWorkspace({
  user,
  onChat,
  onLogout,
}: {
  user: User
  onChat: () => void
  onLogout: () => void
}) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [roles, setRoles] = useState<RoleInfo[]>([])
  const [models, setModels] = useState<ModelInfo[]>([])
  const [logs, setLogs] = useState<any[]>([])

  useEffect(() => {
    adminDashboard().then(setDashboard)
    adminUsers().then((data) => setUsers(data.items))
    adminRoles().then(setRoles)
    adminModels().then(setModels)
    adminOperationLogs().then(setLogs)
  }, [])

  return (
    <div className="admin-layout">
      <aside className="admin-sidebar">
        <button className="brand-row" onClick={onChat}>
          <div className="mark small">C</div>
          <span>ChatAI</span>
        </button>
        <button className="admin-nav active">
          <LayoutDashboard size={18} />
          总览
        </button>
        <button className="admin-nav">
          <Users size={18} />
          用户
        </button>
        <button className="admin-nav">
          <Shield size={18} />
          权限
        </button>
        <button className="admin-nav">
          <Settings size={18} />
          模型
        </button>
        <div className="admin-spacer" />
        <button className="admin-nav" onClick={onChat}>
          <MessageSquarePlus size={18} />
          返回聊天
        </button>
        <button className="admin-nav" onClick={onLogout}>
          <LogOut size={18} />
          退出
        </button>
      </aside>
      <main className="admin-main">
        <header className="admin-header">
          <div>
            <p>管理后台</p>
            <h1>权限、用户和模型运行状态</h1>
          </div>
          <span className="admin-user">{user.username}</span>
        </header>

        <section className="metric-grid">
          <Metric label="用户总数" value={dashboard?.total_users ?? 0} />
          <Metric label="今日活跃" value={dashboard?.active_users_today ?? 0} />
          <Metric label="今日消息" value={dashboard?.messages_today ?? 0} />
          <Metric label="模型调用" value={dashboard?.model_calls_today ?? 0} />
          <Metric label="平均耗时" value={`${dashboard?.avg_latency_ms ?? 0}ms`} />
          <Metric label="失败率" value={`${Math.round((dashboard?.failure_rate ?? 0) * 100)}%`} />
        </section>

        <section className="admin-panels">
          <AdminPanel title="用户管理">
            <DataTable
              columns={['用户名', '邮箱', '角色', '状态']}
              rows={users.map((item) => [
                item.username,
                item.email,
                item.roles.join(', '),
                item.status === 'active' ? '正常' : '禁用',
              ])}
            />
          </AdminPanel>
          <AdminPanel title="角色管理">
            <DataTable
              columns={['角色', '编码', '系统角色']}
              rows={roles.map((item) => [item.name, item.code, item.is_system ? '是' : '否'])}
            />
          </AdminPanel>
          <AdminPanel title="模型管理">
            <DataTable
              columns={['模型', 'Provider', '状态']}
              rows={models.map((item) => [item.name, item.provider, item.enabled ? '启用' : '禁用'])}
            />
          </AdminPanel>
          <AdminPanel title="操作日志">
            <DataTable
              columns={['操作', '对象', '结果', '时间']}
              rows={logs.slice(0, 8).map((item) => [
                item.action,
                item.target_type ?? '-',
                item.result,
                formatTime(item.created_at),
              ])}
            />
          </AdminPanel>
        </section>
      </main>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="metric-card">
      <p>{label}</p>
      <strong>{value}</strong>
    </div>
  )
}

function AdminPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="admin-panel">
      <div className="panel-title">
        <h2>{title}</h2>
        <MoreHorizontal size={18} />
      </div>
      {children}
    </section>
  )
}

function DataTable({ columns, rows }: { columns: string[]; rows: (string | number)[][] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function groupConversations(conversations: Conversation[]) {
  const now = new Date()
  const groups = [
    { label: '今天', items: [] as Conversation[] },
    { label: '昨天', items: [] as Conversation[] },
    { label: '最近 7 天', items: [] as Conversation[] },
    { label: '最近 30 天', items: [] as Conversation[] },
    { label: '更早', items: [] as Conversation[] },
  ]
  conversations.forEach((conversation) => {
    const date = new Date(conversation.updated_at)
    const diff = now.getTime() - date.getTime()
    const days = diff / (1000 * 60 * 60 * 24)
    if (days < 1 && now.getDate() === date.getDate()) groups[0].items.push(conversation)
    else if (days < 2) groups[1].items.push(conversation)
    else if (days < 7) groups[2].items.push(conversation)
    else if (days < 30) groups[3].items.push(conversation)
    else groups[4].items.push(conversation)
  })
  return groups.filter((group) => group.items.length > 0)
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export default App
