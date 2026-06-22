import './SearchResults.css'

interface Result {
  title?: string
  url?: string
  content?: string
  score?: number
}

interface SearchResultsProps {
  results: Result[]
  query: string
  cacheHit: boolean
  source: string
}

export default function SearchResults({ results, query, cacheHit, source }: SearchResultsProps) {
  if (results.length === 0) {
    return (
      <div className="results-empty">
        <span>🔍</span>
        <p>No results found for "<strong>{query}</strong>"</p>
      </div>
    )
  }

  return (
    <div className="results-wrap">
      <div className="results-meta">
        <span className="results-count">{results.length} result{results.length !== 1 ? 's' : ''}</span>
        <span className={`results-source badge ${cacheHit ? 'badge-green' : 'badge-cyan'}`}>
          {cacheHit ? '⚡ Cache Hit' : '🌐 Live Search'}
        </span>
      </div>

      <div className="results-list stagger">
        {results.map((r, i) => (
          <article key={i} className="result-card glass anim-fade-up">
            <div className="result-header">
              <div className="result-favicon">
                {r.url && (
                  <img
                    src={`https://www.google.com/s2/favicons?domain=${new URL(r.url).hostname}&sz=32`}
                    alt=""
                    width="16" height="16"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                )}
              </div>
              <div className="result-domain">
                {r.url ? new URL(r.url).hostname.replace('www.', '') : ''}
              </div>
              {r.score != null && (
                <span className="result-score">{(r.score * 100).toFixed(0)}%</span>
              )}
            </div>

            {r.title && (
              <h3 className="result-title">
                {r.url
                  ? <a href={r.url} target="_blank" rel="noopener noreferrer">{r.title}</a>
                  : r.title}
              </h3>
            )}

            {r.content && (
              <p className="result-snippet">
                {r.content.length > 220 ? r.content.slice(0, 220) + '…' : r.content}
              </p>
            )}

            {r.url && (
              <a href={r.url} target="_blank" rel="noopener noreferrer" className="result-url">
                {r.url.length > 60 ? r.url.slice(0, 60) + '…' : r.url}
              </a>
            )}
          </article>
        ))}
      </div>
    </div>
  )
}
