import { BookOpen } from 'lucide-react'
import { useEffect, useState } from 'react'
import { listKnowledgeBases } from '../api'
import type { KnowledgeBase } from '../../../shared/types'

export function KnowledgeBasesPage() {
  const [items, setItems] = useState<KnowledgeBase[]>([])

  useEffect(() => {
    listKnowledgeBases().then(setItems)
  }, [])

  return (
    <section className="admin-page knowledge-page">
      <header className="admin-page-header">
        <h1>知识库</h1>
        <p>llm 通过 KnowledgeGateway 使用知识库，不直接读取 kb_ 表。</p>
      </header>
      <div className="knowledge-list">
        {items.length === 0 ? (
          <div className="empty-state">
            <BookOpen size={26} />
            <span>暂无可访问知识库</span>
          </div>
        ) : (
          items.map((item) => (
            <article key={item.id}>
              <h2>{item.name}</h2>
              <p>{item.description ?? item.type}</p>
              <small>{item.status}</small>
            </article>
          ))
        )}
      </div>
    </section>
  )
}

