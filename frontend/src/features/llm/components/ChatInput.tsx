import { AudioLines, ChevronDown, Mic, Plus, Send, Square } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { KeyboardEvent } from 'react'

export function ChatInput({
  value,
  generating,
  placeholder = 'Ask anything',
  onChange,
  onSend,
  onStop,
}: {
  value: string
  generating: boolean
  placeholder?: string
  onChange: (value: string) => void
  onSend: () => void
  onStop: () => void
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize whenever the (controlled) value changes — including when the
  // parent clears it after sending, so the box collapses back to one row.
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`
  }, [value])

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSend()
    }
  }

  return (
    <div className="composer">
      <button className="composer-icon" title="添加">
        <Plus size={20} />
      </button>
      <textarea
        ref={textareaRef}
        value={value}
        placeholder={placeholder}
        rows={1}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
      />
      <div className="composer-tools">
        <button className="composer-pill" title="模式">
          Instant
          <ChevronDown size={15} />
        </button>
        <button className="composer-round" title="Voice input">
          <Mic size={18} />
        </button>
      </div>
      <button
        className="send-button"
        disabled={!value.trim() && !generating}
        onClick={generating ? onStop : onSend}
      >
        {generating ? <Square size={15} fill="currentColor" /> : value.trim() ? <Send size={16} /> : <AudioLines size={22} />}
      </button>
    </div>
  )
}
