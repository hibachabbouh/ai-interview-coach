import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import "./InterviewPage.css";


const API_BASE = 'http://localhost:8002';
const DEFAULT_TARGET_QUESTIONS = 5;

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function InterviewPage() {
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        "Hello! I am your AI Interview Coach. Let's practice for your next technical interview. What topic would you like to focus on today?",
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  // Session identity — persists across turns
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [turn, setTurn] = useState(0);
  const [awaitingAnswer, setAwaitingAnswer] = useState(false);
  const [currentQuestion, setCurrentQuestion] = useState<string | null>(null);

  // Multi-question session tracking — mirrors what the backend stores in Redis
  const [questionCount, setQuestionCount] = useState(0);
  const [targetQuestionCount] = useState(DEFAULT_TARGET_QUESTIONS);
  const [scoreHistory, setScoreHistory] = useState<number[]>([]);
  const [averageScore, setAverageScore] = useState<number | null>(null);
  const [sessionComplete, setSessionComplete] = useState(false);

  // Profile reused automatically — no need to restate topic
  const [role, setRole] = useState<string | null>(null);
  const [company, setCompany] = useState<string | null>(null);
  const [experienceLevel, setExperienceLevel] = useState<string | null>(null);

  // Auto-scroll ref
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const resetSessionState = () => {
    setSessionId(crypto.randomUUID());
    setTurn(0);
    setAwaitingAnswer(false);
    setCurrentQuestion(null);
    setQuestionCount(0);
    setScoreHistory([]);
    setAverageScore(null);
    setSessionComplete(false);
    setRole(null);
    setCompany(null);
    setExperienceLevel(null);
    setMessages([
      {
        role: 'assistant',
        content:
          "Let's start a new session! What topic would you like to focus on today?",
      },
    ]);
  };

  const sendMessage = async (text: string) => {
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_BASE}/interview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: text,
          session_id: sessionId,
          language: 'en',
          turn,
          awaiting_answer: awaitingAnswer,
          current_question: currentQuestion,
          target_question_count: targetQuestionCount,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      // ── Guardrail blocked ──────────────────────────────────
      if (data.allowed === false && data.guardrail_reason) {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `Your message was flagged: ${data.guardrail_reason}\n\nPlease try rephrasing or share a real experience — even a university project counts!`,
          },
        ]);
        return;
      }

      // Sync profile + session counters from backend (source of truth)
      if (data.role) setRole(data.role);
      if (data.company) setCompany(data.company);
      if (data.experience_level) setExperienceLevel(data.experience_level);
      if (typeof data.question_count === 'number') setQuestionCount(data.question_count);
      if (Array.isArray(data.score_history)) setScoreHistory(data.score_history);
      if (data.average_score != null) setAverageScore(data.average_score);

      // ── Question generated ──────────────────────────────────
      if (data.awaiting_answer && data.question) {
        const qLabel = `Question ${data.question_count}/${data.target_question_count ?? targetQuestionCount}`;
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: `**${qLabel}**\n\n${data.question}` },
        ]);
        setAwaitingAnswer(true);
        setCurrentQuestion(data.question);
        setTurn(t => t + 1);
        return;
      }

      // ── Evaluation complete ─────────────────────────────────
      const rawSummary = data.summary ?? data.final_report ?? data.title ?? '';
      const summary = rawSummary
        .replace(/^⚠️.*?\n+/g, '')
        .replace(/^This type of request.*?\n+/gi, '')
        .trim() || 'Answer evaluated.';

      const score = data.final_overall_score != null
        ? `\n\nScore: ${(data.final_overall_score * 10).toFixed(1)} / 10`
        : '';

      const nextSteps = data.next_steps?.length
        ? `\n\nNext steps:\n${(data.next_steps as string[]).map((s: string) => `• ${s}`).join('\n')}`
        : '';

      const reply = summary + score + nextSteps;

      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);

      setAwaitingAnswer(false);
      setCurrentQuestion(null);
      setTurn(t => t + 1);

      if (data.session_complete) {
        setSessionComplete(true);
        const avg = data.average_score != null ? (data.average_score * 10).toFixed(1) : 'N/A';
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `Session complete! You answered ${data.question_count}/${data.target_question_count} questions.\n\nAverage score: ${avg} / 10\n\nClick "New Session" to start a fresh interview.`,
          },
        ]);
      } else if (!data.awaiting_answer) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: 'Ready for the next question? Just say "give me another question" or ask for a specific topic.' },
        ]);
      }

    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading || sessionComplete) return;
    const text = inputText.trim();
    setInputText('');
    sendMessage(text);
  };

  const handleAnotherQuestion = () => {
    if (isLoading || sessionComplete) return;
    sendMessage('give me another question');
  };

  const progressPct = targetQuestionCount > 0
    ? Math.round((questionCount / targetQuestionCount) * 100)
    : 0;

  const getScoreColor = (s: number) =>
    s >= 0.7 ? '#10b981' : s >= 0.4 ? '#f59e0b' : '#ef4444';

  return (
    <div className="interview-page">

      {/* Header row */}
      <div className="ip-header">
        <div className="ip-title">
          Interview Session
          <span>AI-powered mock interview with real-time feedback</span>
        </div>

        {(role || questionCount > 0) && (
          <button
            type="button"
            onClick={resetSessionState}
            className="btn btn-secondary btn-sm"
          >
            New Session
          </button>
        )}
      </div>

      {/* Session info bar */}
      {(role || questionCount > 0) && (
        <div className="ip-session-bar">
          <div className="ip-profile">
            {role && (
              <span className="ip-profile-tag">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                {role}{experienceLevel ? ` · ${experienceLevel}` : ''}
              </span>
            )}
            {company && (
              <span className="ip-profile-tag">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                </svg>
                {company}
              </span>
            )}
          </div>

          <div className="ip-session-right">
            <div className="ip-progress-track">
              <div
                className="ip-progress-fill"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <span className="ip-counter">
              {questionCount}/{targetQuestionCount} questions
            </span>
            {averageScore != null && (
              <span className="ip-avg-score">
                Avg {(averageScore * 10).toFixed(1)}/10
              </span>
            )}
          </div>
        </div>
      )}

      {/* Score history chart */}
      {scoreHistory.length > 0 && (
        <div className="ip-score-chart">
          <div className="ip-score-chart-label">Score History</div>
          <div className="ip-score-bars">
            {scoreHistory.map((s, i) => (
              <div key={i} className="ip-score-bar-wrap">
                <div
                  className="ip-score-bar"
                  style={{
                    height: `${Math.max(6, s * 40)}px`,
                    background: getScoreColor(s),
                  }}
                  title={`Q${i + 1}: ${(s * 10).toFixed(1)}/10`}
                />
                <span className="ip-score-bar-q">Q{i + 1}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main chat window */}
      <div className="ip-chat-wrap">

        {/* Top status bar */}
        <div className="ip-chat-topbar">
          <span className="ip-chat-topbar-dot" />
          <span className="ip-chat-topbar-label">
            {sessionComplete
              ? 'Session complete'
              : isLoading
              ? 'AI is thinking...'
              : awaitingAnswer
              ? 'Awaiting your answer'
              : 'Active session'}
          </span>
          {sessionComplete && (
            <span className="badge badge-green">Complete</span>
          )}
          {awaitingAnswer && !sessionComplete && (
            <span className="badge badge-indigo">Question active</span>
          )}
        </div>

        {/* Awaiting answer banner */}
        {awaitingAnswer && (
          <div className="ip-awaiting-banner">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4l3 3" />
            </svg>
            Please type your answer to the question above before continuing.
          </div>
        )}

        {/* Messages */}
        <div className="ip-messages">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`ip-message ${msg.role === 'user' ? 'ip-message-user' : 'ip-message-assistant'}`}
            >
              <div className="ip-message-label">
                {msg.role === 'user' ? 'You' : 'AI Coach'}
              </div>
              <div className={`ip-bubble ${msg.role === 'user' ? 'ip-bubble-user' : 'ip-bubble-assistant'}`}>
                {msg.role === 'user' ? (
                  msg.content
                ) : (
                  <div className="ip-markdown">
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{
      // Open links in new tab safely
      a: ({ node: _node, ...props }) => (
        <a {...props} target="_blank" rel="noopener noreferrer" />
      ),
    }}
  >
    {msg.content}
  </ReactMarkdown>
</div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="ip-message ip-message-assistant">
              <div className="ip-message-label">AI Coach</div>
              <div className="ip-bubble-loading">
                <span className="ip-thinking-dot" />
                <span className="ip-thinking-dot" />
                <span className="ip-thinking-dot" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* "Next question" button */}
        {!awaitingAnswer && !sessionComplete && questionCount > 0 && (
          <div className="ip-actions">
            <button
              type="button"
              onClick={handleAnotherQuestion}
              disabled={isLoading}
              className="btn btn-secondary ip-next-btn"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
              Next question
            </button>
          </div>
        )}

        {/* Input form */}
        <form className="ip-input-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            placeholder={
              sessionComplete
                ? 'Session complete — start a new session to continue'
                : awaitingAnswer
                ? 'Type your answer here...'
                : 'What topic would you like to practice?'
            }
            className="ip-input"
            disabled={sessionComplete}
            id="interview-input"
            autoComplete="off"
          />
          <button
            type="submit"
            className="btn btn-primary ip-send-btn"
            disabled={isLoading || sessionComplete}
            id="interview-send-btn"
          >
            {isLoading ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" style={{ animation: 'spin 0.8s linear infinite' }}>
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
            ) : (
              <>
                Send
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}