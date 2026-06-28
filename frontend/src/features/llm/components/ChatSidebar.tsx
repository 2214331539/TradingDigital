import {
  ArrowLeft,
  Folder,
  LogOut,
  MoreHorizontal,
  PanelLeftClose,
  PenLine,
  Pin,
  Plus,
  Search,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import type { AuthMe, Conversation, LlmProject } from '../../../shared/types'

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
  auth: AuthMe | null
  onLogout: () => void
}) {
  const pinned = conversations.filter((conversation) => conversation.pinned)
  const projectConversationIds = new Set(
    conversations.filter((conversation) => conversation.project_id).map((conversation) => conversation.id),
  )
  const regular = conversations.filter(
    (conversation) => !conversation.pinned && !projectConversationIds.has(conversation.id),
  )

  function item(conversation: Conversation) {
    return (
      <button
        className={`conversation-item ${currentId === conversation.id ? 'active' : ''}`}
        key={conversation.id}
        onClick={() => onSelect(conversation)}
      >
        <span>{conversation.title}</span>
        <span className="conversation-tools">
          {conversation.pinned ? <Pin size={13} fill="currentColor" /> : null}
          <MoreHorizontal size={15} />
        </span>
      </button>
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
          <PenLine size={18} />
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
      {pinned.length > 0 ? (
        <div className="pinned-section">
          <div className="sidebar-section-title">Pinned</div>
          {pinned.map(item)}
        </div>
      ) : null}
      <div className="projects-section">
        <div className="sidebar-section-title">
          <span>Projects</span>
          <button className="icon-button" onClick={onCreateProject} title="新建项目">
            <Plus size={15} />
          </button>
        </div>
        {projects.map((project) => {
          const children = conversations.filter((conversation) => conversation.project_id === project.id)
          return (
            <div className="project-group" key={project.id}>
              <button className="sidebar-command compact project-title" onClick={() => onProjectSelect(project)}>
                <Folder size={18} />
                <span>{project.name}</span>
              </button>
              <div className="project-conversations">{children.slice(0, 3).map(item)}</div>
            </div>
          )
        })}
      </div>
      <nav className="conversation-nav">
        <div className="history-label">Chats</div>
        {regular.map(item)}
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
