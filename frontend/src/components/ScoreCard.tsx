import './ScoreCard.css'

interface Scores {
  overall: number
  technical?: number
  communication?: number
  confidence?: number
}

interface ScoreCardProps {
  scores: Scores
  strengths?: string[]
  weaknesses?: string[]
  visible?: boolean
}

function ScoreCircle({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, value * 10))
  const radius = 32
  const circ = 2 * Math.PI * radius
  const dash = (pct / 100) * circ
  const color = value >= 7 ? '#10b981' : value >= 5 ? '#f59e0b' : '#ef4444'

  return (
    <div className="score-circle-wrap">
      <svg className="score-circle-svg" viewBox="0 0 80 80" width="80" height="80">
        {/* Track */}
        <circle cx="40" cy="40" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
        {/* Progress */}
        <circle
          cx="40" cy="40" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeDashoffset={circ / 4}   /* start from top */
          style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.4,0,0.2,1)', filter: `drop-shadow(0 0 4px ${color})` }}
        />
        <text x="40" y="44" textAnchor="middle" className="score-circle-value" fill={color}>
          {value.toFixed(1)}
        </text>
      </svg>
      <span className="score-circle-label">{label}</span>
    </div>
  )
}

export default function ScoreCard({ scores, strengths = [], weaknesses = [], visible = true }: ScoreCardProps) {
  if (!visible) return null

  return (
    <div className="score-card glass anim-fade-up">
      <div className="score-card-header">
        <h3>Interview Results</h3>
        <span className={`overall-badge ${scores.overall >= 7 ? 'good' : scores.overall >= 5 ? 'ok' : 'low'}`}>
          {scores.overall >= 7 ? '🎉 Great' : scores.overall >= 5 ? '👍 Good' : '📚 Keep Practicing'}
        </span>
      </div>

      <div className="score-circles">
        <ScoreCircle label="Overall" value={scores.overall} />
        {scores.technical    != null && <ScoreCircle label="Technical"     value={scores.technical} />}
        {scores.communication != null && <ScoreCircle label="Communication" value={scores.communication} />}
        {scores.confidence   != null && <ScoreCircle label="Confidence"    value={scores.confidence} />}
      </div>

      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className="score-lists">
          {strengths.length > 0 && (
            <div className="score-list">
              <div className="score-list-title strengths-title">✅ Strengths</div>
              <ul>
                {strengths.map((s, i) => <li key={i}>{s}</li>)}
              </ul>
            </div>
          )}
          {weaknesses.length > 0 && (
            <div className="score-list">
              <div className="score-list-title weaknesses-title">⚡ To Improve</div>
              <ul>
                {weaknesses.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
