import {
  Archive,
  ArrowLeft,
  ChevronRight,
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

const PROJECTS_VISIBLE = 6

export function ChatSidebar({
  conversations,
  projects,
  currentId,
  activeProjectId,
  search,
  onSearch,
  onNewChat,
  onSelect,
  onProjectSelect,
  onProjectNewChat,
  onCreateProject,
  onProjectTogglePin,
  onProjectRename,
  onProjectDelete,
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
  activeProjectId: string | null
  search: string
  onSearch: (value: string) => void
  onNewChat: () => void
  onSelect: (conversation: Conversation) => void
  onProjectSelect: (project: LlmProject) => void
  onProjectNewChat: (project: LlmProject) => void
  onCreateProject: () => void
  onProjectTogglePin: (project: LlmProject) => void
  onProjectRename: (project: LlmProject, name: string) => void
  onProjectDelete: (project: LlmProject) => void
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
  const [open, setOpen] = useState({ pinned: true, projects: true, chats: true })
  const [showAllProjects, setShowAllProjects] = useState(false)

  useEffect(() => {
    if (!menuId) return
    const close = () => setMenuId(null)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [menuId])

  const pinnedChats = conversations.filter((conversation) => conversation.pinned)
  const projectConversationIds = new Set(
    conversations.filter((conversation) => conversation.project_id).map((conversation) => conversation.id),
  )
  const chats = conversations.filter(
    (conversation) => !conversation.pinned && !projectConversationIds.has(conversation.id),
  )
  const visibleProjects = showAllProjects ? projects : projects.slice(0, PROJECTS_VISIBLE)

  function toggle(section: 'pinned' | 'projects' | 'chats') {
    setOpen((value) => ({ ...value, [section]: !value[section] }))
  }

  function startRename(id: string, value: string) {
    setMenuId(null)
    setRenamingId(id)
    setRenameValue(value)
  }

  function renameInput(commit: () => void) {
    return (
      <input
        className="conversation-rename"
        autoFocus
        value={renameValue}
        onChange={(event) => setRenameValue(event.target.value)}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => {
          if (event.key === 'Enter') commit()
          if (event.key === 'Escape') setRenamingId(null)
        }}
        onBlur={commit}
      />
    )
  }

  function chatItem(conversation: Conversation, nested = false) {
    if (renamingId === conversation.id) {
      return (
        <div className={`conversation-item ${nested ? 'nested' : ''}`} key={conversation.id}>
          {renameInput(() => {
            const next = renameValue.trim()
            if (next && next !== conversation.title) onRename(conversation, next)
            setRenamingId(null)
          })}
        </div>
      )
    }
    return (
      <div
        className={`conversation-item ${nested ? 'nested' : ''} ${currentId === conversation.id ? 'active' : ''} ${menuId === conversation.id ? 'menu-open' : ''}`}
        key={conversation.id}
      >
        <button className="conversation-open" onClick={() => onSelect(conversation)} title={conversation.title}>
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
              <button onClick={() => startRename(conversation.id, conversation.title)}>
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

  function projectRow(project: LlmProject) {
    const children = conversations.filter((conversation) => conversation.project_id === project.id)
    const isActive = activeProjectId === project.id
    const menuKey = `project:${project.id}`
    return (
      <div className="project-group" key={project.id}>
        <div className={`conversation-item project-item ${isActive ? 'active' : ''} ${menuId === menuKey ? 'menu-open' : ''}`}>
          {renamingId === menuKey ? (
            renameInput(() => {
              const next = renameValue.trim()
              if (next && next !== project.name) onProjectRename(project, next)
              setRenamingId(null)
            })
          ) : (
            <>
              <button className="conversation-open" onClick={() => onProjectSelect(project)} title={project.name}>
                <Folder size={17} className="project-icon" />
                <span>{project.name}</span>
                {project.pinned ? <Pin size={12} className="pin-indicator" fill="currentColor" /> : null}
              </button>
              <div className="conversation-tools">
                <button
                  className="conversation-more"
                  title="在该项目中新建会话"
                  onClick={(event) => {
                    event.stopPropagation()
                    onProjectNewChat(project)
                  }}
                >
                  <Plus size={16} />
                </button>
                <button
                  className="conversation-more"
                  title="项目选项"
                  onClick={(event) => {
                    event.stopPropagation()
                    setMenuId((value) => (value === menuKey ? null : menuKey))
                  }}
                >
                  <MoreHorizontal size={16} />
                </button>
                {menuId === menuKey ? (
                  <div className="chat-item-menu" onClick={(event) => event.stopPropagation()}>
                    <button onClick={() => { onProjectNewChat(project); setMenuId(null) }}>
                      <SquarePen size={15} />
                      New chat
                    </button>
                    <button onClick={() => { onProjectTogglePin(project); setMenuId(null) }}>
                      {project.pinned ? <PinOff size={15} /> : <Pin size={15} />}
                      {project.pinned ? 'Unpin' : 'Pin'}
                    </button>
                    <button onClick={() => startRename(menuKey, project.name)}>
                      <PenLine size={15} />
                      Rename
                    </button>
                    <button className="danger" onClick={() => { onProjectDelete(project); setMenuId(null) }}>
                      <Trash2 size={15} />
                      Delete
                    </button>
                  </div>
                ) : null}
              </div>
            </>
          )}
        </div>
        {isActive && children.length > 0 ? (
          <div className="project-conversations">{children.map((child) => chatItem(child, true))}</div>
        ) : null}
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
          <input placeholder="Search chats" value={search} onChange={(event) => onSearch(event.target.value)} />
        </label>
      </div>

      <nav className="conversation-nav">
        <section className="sidebar-block">
          <button className="sidebar-block-head" onClick={() => toggle('pinned')}>
            <span>Pinned Chats</span>
            <ChevronRight size={15} className={`section-chevron ${open.pinned ? 'open' : ''}`} />
          </button>
          {open.pinned ? (
            pinnedChats.length > 0 ? (
              pinnedChats.map((conversation) => chatItem(conversation))
            ) : (
              <p className="history-empty">置顶的会话会出现在这里。</p>
            )
          ) : null}
        </section>

        <section className="sidebar-block">
          <div className="sidebar-block-head">
            <button className="block-head-toggle" onClick={() => toggle('projects')}>
              <span>Projects</span>
              <ChevronRight size={15} className={`section-chevron ${open.projects ? 'open' : ''}`} />
            </button>
            <button className="icon-button" onClick={onCreateProject} title="新建项目">
              <Plus size={16} />
            </button>
          </div>
          {open.projects ? (
            projects.length > 0 ? (
              <>
                <div className="projects-scroll">{visibleProjects.map((project) => projectRow(project))}</div>
                {projects.length > PROJECTS_VISIBLE ? (
                  <button className="sidebar-command muted show-more" onClick={() => setShowAllProjects((value) => !value)}>
                    <span>{showAllProjects ? 'Show less' : 'Show more'}</span>
                  </button>
                ) : null}
              </>
            ) : (
              <button className="sidebar-command compact muted" onClick={onCreateProject}>
                <Folder size={18} />
                <span>New project</span>
              </button>
            )
          ) : null}
        </section>

        <section className="sidebar-block">
          <button className="sidebar-block-head" onClick={() => toggle('chats')}>
            <span>Chats</span>
            <ChevronRight size={15} className={`section-chevron ${open.chats ? 'open' : ''}`} />
          </button>
          {open.chats ? (
            chats.length > 0 ? (
              chats.map((conversation) => chatItem(conversation))
            ) : (
              <p className="history-empty">还没有会话，开始一个新对话吧。</p>
            )
          ) : null}
        </section>
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
