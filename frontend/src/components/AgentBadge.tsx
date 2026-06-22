import './AgentBadge.css'

const AGENT_META: Record<string, { icon: string; label: string; color: string }> = {
  guardrail: { icon: '🛡️', label: 'Guardrail', color: 'red' },
  ambiguity: { icon: '🔍', label: 'Ambiguity', color: 'amber' },
  memory: { icon: '🧠', label: 'Memory', color: 'indigo' },
  profile_merge: { icon: '🔗', label: 'Profile Merge', color: 'cyan' },
  router: { icon: '🔀', label: 'Router', color: 'indigo' },
  technical: { icon: '⚙️', label: 'Technical', color: 'cyan' },
  behavioral: { icon: '💬', label: 'Behavioral', color: 'green' },
  evaluation: { icon: '📊', label: 'Evaluation', color: 'amber' },
  fusion: { icon: '⚡', label: 'Fusion', color: 'indigo' },
  report: { icon: '📝', label: 'Report', color: 'green' },
}

interface AgentBadgeProps {
  agent: string
  active?: boolean
  done?: boolean
}

export default function AgentBadge({ agent, active = false, done = false }: AgentBadgeProps) {
  const meta = AGENT_META[agent] ?? { icon: '🤖', label: agent, color: 'indigo' }

  return (
    <div className={`agent-badge ${active ? 'active' : ''} ${done ? 'done' : ''}`}>
      <span className="agent-icon">{meta.icon}</span>
      <span className="agent-label">{meta.label}</span>
      {active && <span className="agent-dot" />}
      {done && <span className="agent-check">✓</span>}
    </div>
  )
}

export function AgentPipeline({ currentAgent }: { currentAgent: string }) {
  const pipeline = [
    'guardrail', 'ambiguity', 'memory', 'router',
    'technical', 'evaluation', 'fusion', 'report',
  ]

  const currentIdx = pipeline.indexOf(currentAgent)

  return (
    <div className="agent-pipeline">
      {pipeline.map((agent, i) => (
        <AgentBadge
          key={agent}
          agent={agent}
          active={agent === currentAgent}
          done={i < currentIdx}
        />
      ))}
    </div>
  )
}
