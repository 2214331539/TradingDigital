import { Folder, MoreHorizontal, PenLine, Pin, PinOff, Share, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ChatInput } from './ChatInput'
import { ThemeToggle } from '../../../shared/components/ThemeToggle'
import type { Conversation, LlmProject } from '../../../shared/types'

function formatDate(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('en-US', { month: 'short', day: 'numeric' })
}

export function ProjectView({
  project,
  conversations,
  input,
  generating,
  onInput,
  onSend,
  onStop,
  onSelect,
  onTogglePin,
  onRename,
  onDelete,
}: {
  project: LlmProject
  conversations: Conversation[]
  input: string
  generating: boolean
  onInput: (value: string) => void
  onSend: () => void
  onStop: () => void
  onSelect: (conversation: Conversation) => void
  onTogglePin: (project: LlmProject) => void
  onRename: (project: LlmProject) => void
  onDelete: (project: LlmProject) => void
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [tab, setTab] = useState<'chats' | 'sources'>('chats')

  useEffect(() => {
    if (!menuOpen) return
    const close = () => setMenuOpen(false)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [menuOpen])

  const projectChats = conversations.filter((conversation) => conversation.project_id === project.id)

  return (
    <div className="project-view">
      <header className="project-view-header">
        <div className="project-view-title">
          <Folder size={22} />
          <h1>{project.name}</h1>
        </div>
        <div className="project-view-actions">
          <ThemeToggle />
          <button className="share-button" title="分享">
            <Share size={16} />
            Share
          </button>
          <div className="project-view-menu-anchor">
            <button
              className="icon-button"
              title="项目选项"
              onClick={(event) => {
                event.stopPropagation()
                setMenuOpen((value) => !value)
              }}
            >
              <MoreHorizontal size={18} />
            </button>
            {menuOpen ? (
              <div className="chat-item-menu" onClick={(event) => event.stopPropagation()}>
                <button onClick={() => { onTogglePin(project); setMenuOpen(false) }}>
                  {project.pinned ? <PinOff size={15} /> : <Pin size={15} />}
                  {project.pinned ? 'Unpin' : 'Pin'}
                </button>
                <button onClick={() => { onRename(project); setMenuOpen(false) }}>
                  <PenLine size={15} />
                  Rename
                </button>
                <button className="danger" onClick={() => { onDelete(project); setMenuOpen(false) }}>
                  <Trash2 size={15} />
                  Delete
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <div className="project-view-body">
        <ChatInput
          value={input}
          generating={generating}
          placeholder={`New chat in ${project.name}`}
          onChange={onInput}
          onSend={onSend}
          onStop={onStop}
        />

        <div className="project-tabs">
          <button className={tab === 'chats' ? 'active' : ''} onClick={() => setTab('chats')}>
            Chats
          </button>
          <button className={tab === 'sources' ? 'active' : ''} onClick={() => setTab('sources')}>
            Sources
          </button>
        </div>

        {tab === 'chats' ? (
          projectChats.length > 0 ? (
            <ul className="project-chat-list">
              {projectChats.map((conversation) => (
                <li key={conversation.id}>
                  <button onClick={() => onSelect(conversation)}>
                    <span className="project-chat-main">
                      <strong>{conversation.title}</strong>
                    </span>
                    <span className="project-chat-date">{formatDate(conversation.last_message_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="project-empty">该项目还没有会话，在上方输入开始第一个对话。</p>
          )
        ) : (
          <p className="project-empty">暂无来源文件。</p>
        )}
      </div>
    </div>
  )
}
