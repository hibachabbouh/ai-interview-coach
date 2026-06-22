import { useEffect, useRef } from 'react'
import './TokenStream.css'

interface TokenStreamProps {
  text: string
  isStreaming: boolean
  placeholder?: string
}

export default function TokenStream({ text, isStreaming, placeholder }: TokenStreamProps) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [text])

  if (!text && !isStreaming) {
    return (
      <div className="stream-empty">
        <div className="stream-empty-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
        <p>{placeholder ?? 'Your AI response will appear here in real time…'}</p>
      </div>
    )
  }

  return (
    <div className="stream-box">
      <div className="stream-header">
        <span className="stream-label">AI Response</span>
        {isStreaming && (
          <span className="stream-live">
            <span className="live-dot" />
            Streaming
          </span>
        )}
      </div>

      <div className="stream-content">
        <span className="stream-text">{text}</span>
        {isStreaming && <span className="cursor" aria-hidden="true" />}
      </div>

      <div ref={endRef} />
    </div>
  )
}
