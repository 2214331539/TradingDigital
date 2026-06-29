import {
  Archive,
  ArrowLeft,
  Folder,
  LogOut,
  MoreHorizontal,
  PanelLeftClose,
  PenLine,
  Pin,
  PinOff,
  Plus,
  Search,
  Share,
  SquarePen,
  Trash2,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { AuthMe, Conversation, LlmProject } from '../../../shared/types'

const DAY = 86400000

function startOfTodayMs(): number {
  const date = new Date()
  date.setHours(0, 0, 0, 0)
  return date.getTime()
}

function conversationTime(conversation: Conversation): number {
  const raw = conversation.last_message_at ?? conversation.updated_at ?? conversation.created_at
  const time = raw ? new Date(raw).getTime() : Number.NaN
  return Number.isNaN(time) ? 0 : time
}

// Mirror ChatGPT's history buckets: Today / Yesterday / Previous 7 Days /
// Previous 30 Days / then month (with year once it differs from the current one).
function bucketFor(conversation: Conversation): { order: number; label: string } {
  const time = conversationTime(conversation)
  const today = startOfTodayMs()
  if (time >= today) return { order: 0, label: 'Today' }
  if (time >= today - DAY) return { order: 1, label: 'Yesterday' }
  if (time >= today - 7 * DAY) return { order: 2, label: 'Previous 7 Days' }
  if (time >= today - 30 * DAY) return { order: 3, label: 'Previous 30 Days' }
  const date = new Date(time)
  const ref = new Date()
  const monthsAgo = (ref.getFullYear() - date.getFullYear()) * 12 + (ref.getMonth() - date.getMonth())
  const month = date.toLocaleString('en-US', { month: 'long' })
  const label = date.getFullYear() === ref.getFullYear() ? month : `${month} ${date.getFullYear()}`
  return { order: 4 + monthsAgo, label }
}

function groupByTime(items: Conversation[]): { label: string; items: Conversation[] }[] {
  const sorted = [...items].sort((a, b) => conversationTime(b) - conversationTime(a))
  const groups = new Map<string, { order: number; label: string; items: Conversation[] }>()
  for (const conversation of sorted) {
    const bucket = bucketFor(conversation)
    const group = groups.get(bucket.label) ?? { order: bucket.order, label: bucket.label, items: [] }
    group.items.push(conversation)
    groups.set(bucket.label, group)
  }
  return [...groups.values()].sort((a, b) => a.order - b.order)
}

export function ChatSidebar({
  conversations,
  projects,
  currentId,
  search,
  onSearch,
  onNewChat,
  onSelect,
  onProjectSelect,
  onCreateProject,
  onToggleSidebar,
  onRename,
  onTogglePin,
  onArchive,
  onDelete,
  auth,
  onLogout,
}: {
  conversations: Conversation[]
  projects: LlmProject[]
  currentId: string | null
  search: string
  onSearch: (value: string) => void
  onNewChat: () => void
  onSelect: (conversation: Conversation) => void
  onProjectSelect: (project: LlmProject) => void
  onCreateProject: () => void
  onToggleSidebar: () => void
  onRename: (conversation: Conversation, title: string) => void
  onTogglePin: (conversation: Conversation) => void
  onArchive: (conversation: Conversation) => void
  onDelete: (conversation: Conversation) => void
  auth: AuthMe | null
  onLogout: () => void
}) {
  const [menuId, setMenuId] = useState<string | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  useEffect(() => {
    if (!menuId) return
    const close = () => setMenuId(null)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [menuId])

  const pinned = conversations.filter((conversation) => conversation.pinned)
  const projectConversationIds = new Set(
    conversations.filter((conversation) => conversation.project_id).map((conversation) => conversation.id),
  )
  const history = conversations.filter(
    (conversation) => !conversation.pinned && !projectConversationIds.has(conversation.id),
  )
  const historyGroups = groupByTime(history)

  function startRename(conversation: Conversation) {
    setMenuId(null)
    setRenamingId(conversation.id)
    setRenameValue(conversation.title)
  }

  function commitRename(conversation: Conversation) {
    const next = renameValue.trim()
    if (next && next !== conversation.title) onRename(conversation, next)
    setRenamingId(null)
  }

  function item(conversation: Conversation, nested = false) {
    if (renamingId === conversation.id) {
      return (
        <div className={`conversation-item ${nested ? 'nested' : ''}`} key={conversation.id}>
          <input
            className="conversation-rename"
            autoFocus
            value={renameValue}
            onChange={(event) => setRenameValue(event.target.value)}
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => {
              if (event.key === 'Enter') commitRename(conversation)
              if (event.key === 'Escape') setRenamingId(null)
            }}
            onBlur={() => commitRename(conversation)}
          />
        </div>
      )
    }
    return (
      <div
        className={`conversation-item ${nested ? 'nested' : ''} ${currentId === conversation.id ? 'active' : ''} ${menuId === conversation.id ? 'menu-open' : ''}`}
        key={conversation.id}
      >
        <button className="conversation-open" onClick={() => onSelect(conversation)} title={conversation.title}>
          {conversation.pinned ? <Pin size={13} className="pin-indicator" fill="currentColor" /> : null}
          <span>{conversation.title}</span>
        </button>
        <div className="conversation-tools">
          <button
            className="conversation-more"
            title="选项"
            onClick={(event) => {
              event.stopPropagation()
              setMenuId((value) => (value === conversation.id ? null : conversation.id))
            }}
          >
            <MoreHorizontal size={16} />
          </button>
          {menuId === conversation.id ? (
            <div className="chat-item-menu" onClick={(event) => event.stopPropagation()}>
              <button onClick={() => { onTogglePin(conversation); setMenuId(null) }}>
                {conversation.pinned ? <PinOff size={15} /> : <Pin size={15} />}
                {conversation.pinned ? 'Unpin' : 'Pin'}
              </button>
              <button onClick={() => startRename(conversation)}>
                <PenLine size={15} />
                Rename
              </button>
              <button onClick={() => setMenuId(null)}>
                <Share size={15} />
                Share
              </button>
              <button onClick={() => { onArchive(conversation); setMenuId(null) }}>
                <Archive size={15} />
                Archive
              </button>
              <button className="danger" onClick={() => { onDelete(conversation); setMenuId(null) }}>
                <Trash2 size={15} />
                Delete
              </button>
            </div>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <aside className="sidebar llm-sidebar">
      <div className="sidebar-top">
        <button className="brand-button" onClick={onNewChat}>
          <span>ChatGPT</span>
        </button>
        <button className="icon-button" onClick={onToggleSidebar} title="折叠边栏">
          <PanelLeftClose size={18} />
        </button>
      </div>
      <div className="sidebar-primary">
        <button className="sidebar-command" onClick={onNewChat}>
          <SquarePen size={18} />
          <span>New chat</span>
        </button>
        <label className="sidebar-command search-command">
          <Search size={18} />
          <input
            placeholder="Search chats"
            value={search}
            onChange={(event) => onSearch(event.target.value)}
          />
        </label>
      </div>

      <nav className="conversation-nav">
        <div className="sidebar-block">
          <div className="sidebar-block-head">
            <span>Projects</span>
            <button className="icon-button" onClick={onCreateProject} title="新建项目">
              <Plus size={16} />
            </button>
          </div>
          {projects.length === 0 ? (
            <button className="sidebar-command compact muted" onClick={onCreateProject}>
              <Folder size={18} />
              <span>New project</span>
            </button>
          ) : (
            projects.map((project) => {
              const children = conversations.filter((conversation) => conversation.project_id === project.id)
              return (
                <div className="project-group" key={project.id}>
                  <button className="sidebar-command compact project-title" onClick={() => onProjectSelect(project)}>
                    <Folder size={18} />
                    <span>{project.name}</span>
                  </button>
                  <div className="project-conversations">{children.slice(0, 4).map((child) => item(child, true))}</div>
                </div>
              )
            })
          )}
        </div>

        {pinned.length > 0 ? (
          <div className="history-group">
            <div className="history-group-label">Pinned</div>
            {pinned.map((conversation) => item(conversation))}
          </div>
        ) : null}

        {historyGroups.map((group) => (
          <div className="history-group" key={group.label}>
            <div className="history-group-label">{group.label}</div>
            {group.items.map((conversation) => item(conversation))}
          </div>
        ))}

        {history.length === 0 && pinned.length === 0 ? (
          <p className="history-empty">还没有会话，开始一个新对话吧。</p>
        ) : null}
      </nav>

      <div className="sidebar-footer">
        <Link className="account-button" to="/app">
          <ArrowLeft size={17} />
          <span>Modules</span>
        </Link>
        <button className="account-card" onClick={onLogout}>
          <span className="user-avatar">{auth?.user.name?.slice(0, 1) ?? auth?.user.email.slice(0, 1)}</span>
          <span className="account-copy">
            <strong>{auth?.user.name ?? auth?.user.email}</strong>
            <small>{auth?.enterprise.name}</small>
          </span>
          <LogOut size={17} />
        </button>
      </div>
    </aside>
  )
}
