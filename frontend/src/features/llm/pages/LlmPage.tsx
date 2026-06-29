import { Archive, Image, MoreHorizontal, PanelLeftOpen, PenLine, Pin, Search, Share, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  createProject,
  deleteConversation,
  getConversation,
  listAssistantPresets,
  listConversations,
  listModels,
  listProjects,
  streamChat,
  updateConversation,
  updateMessage,
} from '../api'
import { useAuth } from '../../../app/providers/auth-context'
import { ChatInput } from '../components/ChatInput'
import { ChatMessageList } from '../components/ChatMessageList'
import { ChatSidebar } from '../components/ChatSidebar'
import { ModelSelector } from '../components/ModelSelector'
import { ThemeToggle } from '../../../shared/components/ThemeToggle'
import type { AssistantPreset, Conversation, LlmProject, Message, ModelInfo } from '../../../shared/types'

export function LlmPage() {
  const { auth, logout } = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [current, setCurrent] = useState<Conversation | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [models, setModels] = useState<ModelInfo[]>([])
  const [presets, setPresets] = useState<AssistantPreset[]>([])
  const [projects, setProjects] = useState<LlmProject[]>([])
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null)
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [temporary, setTemporary] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(() => window.innerWidth > 980)
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [generating, setGenerating] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    reloadConversations()
    reloadProjects()
    listModels().then((rows) => {
      setModels(rows)
      setSelectedModel(rows.find((row) => row.is_default)?.id ?? rows[0]?.id ?? null)
    })
    listAssistantPresets().then((rows) => {
      setPresets(rows)
      setSelectedPreset(rows[0]?.id ?? null)
    })
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => reloadConversations(search), 180)
    return () => window.clearTimeout(timer)
  }, [search])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, generating])

  async function reloadConversations(keyword = search) {
    const data = await listConversations({ keyword: keyword.trim() || undefined })
    setConversations(data.items)
  }

  async function reloadProjects() {
    setProjects(await listProjects())
  }

  async function selectConversation(conversation: Conversation) {
    setError('')
    const detail = await getConversation(conversation.id)
    setCurrent(detail)
    setMessages(detail.messages)
    setSelectedModel(detail.model_id)
    setSelectedPreset(detail.assistant_preset_id)
    setActiveProjectId(detail.project_id)
    setTemporary(detail.temporary)
    if (window.innerWidth <= 980) setSidebarOpen(false)
  }

  function newChat() {
    setCurrent(null)
    setMessages([])
    setInput('')
    setError('')
    setTemporary(false)
    if (window.innerWidth <= 980) setSidebarOpen(false)
  }

  async function sendContent(content: string) {
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
        assistant_preset_id: selectedPreset,
        project_id: current?.project_id ?? activeProjectId,
        content,
        temporary,
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
          if (event === 'error') setError(data.message)
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

  async function sendMessage() {
    const content = input.trim()
    if (!content || generating) return
    setInput('')
    await sendContent(content)
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

  async function togglePin() {
    if (!current) return
    const updated = await updateConversation(current.id, { pinned: !current.pinned })
    setCurrent(updated)
    reloadConversations()
  }

  async function archiveCurrent() {
    if (!current) return
    await updateConversation(current.id, { archived: true })
    newChat()
    reloadConversations()
  }

  async function removeCurrent() {
    if (!current) return
    await deleteConversation(current.id)
    newChat()
    reloadConversations()
  }

  async function createProjectFromSidebar() {
    const name = window.prompt('Project name')
    if (!name?.trim()) return
    const project = await createProject({ name: name.trim() })
    setProjects((prev) => [project, ...prev])
    setActiveProjectId(project.id)
    newChat()
  }

  function selectProject(project: LlmProject) {
    setActiveProjectId(project.id)
    setCurrent(null)
    setMessages([])
    setSearch('')
    setError('')
    if (window.innerWidth <= 980) setSidebarOpen(false)
  }

  async function moveCurrentToProject(projectId: string | null) {
    if (!current) {
      setActiveProjectId(projectId)
      return
    }
    const updated = await updateConversation(current.id, { project_id: projectId })
    setCurrent(updated)
    setActiveProjectId(updated.project_id)
    reloadConversations()
  }

  async function feedbackMessage(message: Message, feedback: 'like' | 'dislike') {
    const updated = await updateMessage(message.id, { feedback })
    setMessages((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
  }

  async function regenerateFrom(message: Message) {
    const index = messages.findIndex((item) => item.id === message.id)
    const previousUser = messages
      .slice(0, index)
      .reverse()
      .find((item) => item.role === 'user')
    if (!previousUser) return
    await sendContent(previousUser.content)
  }

  const filtered = useMemo(() => {
    if (!activeProjectId) return conversations
    return conversations.filter((conversation) => conversation.project_id === activeProjectId)
  }, [activeProjectId, conversations])

  const activeProject = projects.find((project) => project.id === activeProjectId)

  return (
    <div className="chat-layout llm-page" data-sidebar={sidebarOpen ? 'open' : 'closed'}>
      <ChatSidebar
        conversations={filtered}
        projects={projects}
        currentId={current?.id ?? null}
        search={search}
        onSearch={setSearch}
        onNewChat={newChat}
        onSelect={selectConversation}
        onProjectSelect={selectProject}
        onCreateProject={createProjectFromSidebar}
        onToggleSidebar={() => setSidebarOpen(false)}
        auth={auth}
        onLogout={logout}
      />
      <main className={`chat-main ${messages.length === 0 ? 'is-empty' : 'has-chat'}`}>
        <header className="chat-header">
          {!sidebarOpen ? (
            <button className="icon-button sidebar-open-button" onClick={() => setSidebarOpen(true)} title="展开边栏">
              <PanelLeftOpen size={18} />
            </button>
          ) : null}
          <div className="product-switcher">
            <button className="product-button">
              <span>ChatGPT</span>
            </button>
          </div>
          <ModelSelector models={models} selectedModel={selectedModel} onSelect={setSelectedModel} />
          <label className="preset-selector">
            <select
              value={selectedPreset ?? ''}
              onChange={(event) => setSelectedPreset(event.target.value || null)}
            >
              {presets.map((preset) => (
                <option key={preset.id} value={preset.id}>
                  {preset.name}
                </option>
              ))}
            </select>
          </label>
          {activeProject ? <span className="temp-chip">{activeProject.name}</span> : null}
          {temporary ? <span className="temp-chip">Temporary</span> : null}
          {current ? (
            <div className="header-actions">
              <ThemeToggle />
              <button className="share-button" title="分享">
                <Share size={16} />
                Share
              </button>
              <button className="icon-button" onClick={togglePin} title="置顶">
                <Pin size={17} fill={current.pinned ? 'currentColor' : 'none'} />
              </button>
              <button className="icon-button" onClick={archiveCurrent} title="归档">
                <Archive size={17} />
              </button>
              <button className="icon-button danger" onClick={removeCurrent} title="删除">
                <Trash2 size={17} />
              </button>
              <button className="icon-button" title="更多">
                <MoreHorizontal size={18} />
              </button>
            </div>
          ) : (
            <div className="header-actions">
              <ThemeToggle />
              <button className="ghost-button" onClick={() => setTemporary((value) => !value)}>
                {temporary ? 'Temporary on' : 'Temporary'}
              </button>
              <button className="share-button" title="分享">
                <Share size={16} />
                Share
              </button>
            </div>
          )}
        </header>

        <section className="message-scroll">
          <ChatMessageList messages={messages} onFeedback={feedbackMessage} onRegenerate={regenerateFrom} />
          <div ref={endRef} />
        </section>

        <footer className="composer-shell">
          {messages.length === 0 && activeProject ? (
            <div className="temporary-banner">New chats will be saved in {activeProject.name}.</div>
          ) : null}
          {error ? (
            <div className="inline-error">
              <X size={15} />
              {error}
            </div>
          ) : null}
          <ChatInput
            value={input}
            generating={generating}
            onChange={setInput}
            onSend={sendMessage}
            onStop={stopGeneration}
          />
          {messages.length === 0 ? (
            <div className="composer-suggestions">
              <button onClick={() => setInput('Create an image for a product launch')}>
                <Image size={18} />
                Create an image
              </button>
              <button onClick={() => setInput('Write or edit this text: ')}>
                <PenLine size={18} />
                Write or edit
              </button>
              <button onClick={() => setInput('Look something up about ')}>
                <Search size={18} />
                Look something up
              </button>
            </div>
          ) : null}
          <p className="composer-note">llm can make mistakes. Check important info.</p>
          {projects.length > 0 ? (
            <label className="project-attach">
              <span>Project</span>
              <select
                value={current?.project_id ?? activeProjectId ?? ''}
                onChange={(event) => moveCurrentToProject(event.target.value || null)}
              >
                <option value="">No project</option>
                {projects.map((project) => (
                  <option value={project.id} key={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </footer>
      </main>
    </div>
  )
}
