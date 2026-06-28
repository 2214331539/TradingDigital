import { AudioLines, ChevronDown, Mic, Plus, Send, Square } from 'lucide-react'
import type { ChangeEvent, KeyboardEvent } from 'react'

export function ChatInput({
  value,
  generating,
  onChange,
  onSend,
  onStop,
}: {
  value: string
  generating: boolean
  onChange: (value: string) => void
  onSend: () => void
  onStop: () => void
}) {
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSend()
    }
  }

  function onInput(event: ChangeEvent<HTMLTextAreaElement>) {
    onChange(event.target.value)
    event.target.style.height = 'auto'
    event.target.style.height = `${Math.min(event.target.scrollHeight, 180)}px`
  }

  return (
    <div className="composer">
      <button className="composer-icon" title="添加">
        <Plus size={20} />
      </button>
      <textarea
        value={value}
        placeholder="Ask anything"
        rows={1}
        onChange={onInput}
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
