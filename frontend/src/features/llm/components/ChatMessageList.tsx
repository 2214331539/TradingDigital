import { Check, Copy, MoreHorizontal, RefreshCcw, ThumbsDown, ThumbsUp } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import type { Message } from '../../../shared/types'

export function ChatMessageList({
  messages,
  onFeedback,
  onRegenerate,
}: {
  messages: Message[]
  onFeedback: (message: Message, feedback: 'like' | 'dislike') => void
  onRegenerate: (message: Message) => void
}) {
  const [copiedId, setCopiedId] = useState<string | null>(null)

  async function copyMessage(message: Message) {
    await navigator.clipboard.writeText(message.content)
    setCopiedId(message.id)
    window.setTimeout(() => setCopiedId(null), 1200)
  }

  if (messages.length === 0) {
    return (
      <div className="empty-chat">
        <h2>Ready when you are.</h2>
      </div>
    )
  }

  return (
    <>
      {messages.map((message) => (
        <article className={`message-row ${message.role}`} key={message.id}>
          <div className="message-bubble">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeHighlight, rehypeKatex]}
            >
              {message.content || (message.status === 'streaming' ? ' ' : '')}
            </ReactMarkdown>
            <div className="message-actions">
              {message.status === 'streaming' ? <span className="typing-dot" /> : null}
              {message.content ? (
                <button title="复制" onClick={() => copyMessage(message)}>
                  {copiedId === message.id ? <Check size={16} /> : <Copy size={16} />}
                </button>
              ) : null}
              {message.role === 'assistant' && message.status !== 'streaming' ? (
                <>
                  <button
                    title="赞"
                    aria-pressed={message.metadata_json?.feedback === 'like'}
                    onClick={() => onFeedback(message, 'like')}
                  >
                    <ThumbsUp size={16} />
                  </button>
                  <button
                    title="踩"
                    aria-pressed={message.metadata_json?.feedback === 'dislike'}
                    onClick={() => onFeedback(message, 'dislike')}
                  >
                    <ThumbsDown size={16} />
                  </button>
                  <button title="重新生成" onClick={() => onRegenerate(message)}>
                    <RefreshCcw size={16} />
                  </button>
                  <button title="更多">
                    <MoreHorizontal size={16} />
                  </button>
                </>
              ) : null}
            </div>
          </div>
        </article>
      ))}
    </>
  )
}
