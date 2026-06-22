# Design Decisions — AI Interview Coach

This document captures the *why* behind the major architecture choices in AI Interview Coach — alternatives considered, trade-offs accepted, and key lessons learned during development. The README explains what the system does; this focuses on why it is built this way.

---

# 1. High-Level Architecture

## Problem

An AI interview system is not a single LLM call. It requires:

- Stateful multi-turn conversation handling
- Guardrails and safety filtering
- Dynamic question generation (technical vs behavioral)
- Answer evaluation with structured scoring
- Report generation and persistence
- External knowledge retrieval (Tavily search)
- Streaming responses to the frontend

A monolithic design quickly becomes unmaintainable once these responsibilities are combined into a single prompt or function chain.

## Decision

The system is split into:

- FastAPI backend (core orchestration + APIs)
- LangGraph multi-agent pipeline (interview logic)
- Redis + ChromaDB (hybrid cache layer)
- Tavily API (web grounding)
- SSE streaming (token streaming)
- React frontend (UI)

## Alternatives Considered

| Approach | Why it was rejected |
|----------|---------------------|
| Monolithic LLM prompt | Untestable, brittle, impossible to debug failures |
| Single Python pipeline | No structured routing or state management |
| Full autonomous agent loop | Too unpredictable for structured interview flow |

## Trade-off

More components, but significantly better modularity, testability, and scalability.

---

# 2. Why LangGraph (Multi-Agent Architecture)

## Problem

Interview execution requires multiple independent responsibilities:

- Guardrail filtering
- Ambiguity resolution
- User profiling
- Question type routing
- Question generation
- Answer evaluation
- Report generation

These steps must share state but remain independently testable.

## Decision

Use **LangGraph** as a structured state machine with:

- Typed shared state (`InterviewState`)
- Explicit node transitions
- Isolated agent nodes per responsibility
- Deterministic routing logic

## Why LangGraph

- Natural fit for state-machine workflows
- Clear separation of concerns per node
- Easier debugging (node-level failure isolation)
- Supports model-tier routing per node

## Alternatives Considered

| Approach | Issue |
|----------|------|
| Single prompt | No modularity or debugging |
| Sequential functions | Hard-coded logic, poor scalability |
| ReAct autonomous agent | Too non-deterministic for interview flow |

## Trade-offs

- More prompts and components (9+ nodes)
- Higher latency due to sequential execution
- Complex state management (reducers required)

---

# 3. Why Structured Outputs

## Problem

LLMs frequently produce inconsistent or malformed outputs, especially in multi-step pipelines.

## Decision

All agent nodes output **structured Pydantic models** instead of raw text.

## Why

- Enforces schema consistency
- Eliminates parsing errors
- Makes downstream routing deterministic
- Improves testability

## Alternatives Considered

| Approach | Issue |
|----------|------|
| Regex parsing | Fragile and error-prone |
| Free-text LLM outputs | Unreliable for pipeline logic |

## Trade-off

Slight prompt overhead for schema enforcement, but dramatically improved reliability.

---

# 4. Why Three-Tier Model Routing

## Decision

Different LLMs are used depending on task complexity:

- **Small/fast model**
  - Guardrails
  - Routing decisions
  - Ambiguity detection

- **Medium model**
  - Question generation
  - Context formatting

- **Large model**
  - Evaluation
  - Final report synthesis

## Why

Not all tasks require the same reasoning power.

## Alternatives Considered

| Approach | Issue |
|----------|------|
| Single large model | Expensive and slow |
| Single small model | Poor reasoning quality |

## Trade-off

More orchestration logic, but significantly reduced cost and latency.

---

# 5. Why Hybrid Cache (Redis + ChromaDB)

## Problem

Tavily search is expensive and slow. LLM agents generate many semantically similar queries.

Example:
- "system design scalability"
- "scalable system design techniques"

Both should hit the same cached result.

## Decision

Hybrid caching system:

Query → Exact cache (Redis / local JSON) → Cache gate → Semantic cache (ChromaDB) → Live Tavily search → store in both caches

## Benchmarks

| Mode | Latency |
|------|--------|
| Live search | 136–479 ms |
| Exact cache | ~0.5 ms |
| Semantic cache | ~40–45 ms |

## Why This Design

- Exact cache handles repeated queries
- Semantic cache handles paraphrases
- Cache gate avoids embedding noise
- Dual-layer system balances speed + recall

## Alternatives Considered

| Approach | Issue |
|----------|------|
| Exact-only cache | Misses paraphrased queries |
| Semantic-only cache | Too slow and noisy |
| No cache | Expensive and redundant API calls |

## Trade-off

Slight complexity increase, major cost + latency reduction.

---

# 6. Why SSE Instead of WebSockets

## Problem

The frontend needs real-time streaming of LLM tokens.

## Decision

Use **Server-Sent Events (SSE)** instead of WebSockets.

## Why SSE

- One-directional stream (server → client only)
- Simpler than WebSockets
- Native browser support (`EventSource`)
- Works naturally with HTTP + FastAPI
- Auto-reconnection support

## Alternatives Considered

| Approach | Issue |
|----------|------|
| WebSockets | Overkill for one-way streaming |
| Polling | High latency and inefficiency |

## Trade-off

No bidirectional communication. If needed later, a separate API endpoint is required.

---

# 7. Evaluation Strategy (DeepEval)

## Metrics Used

- Answer Relevancy
- Correctness (GEval)
- Faithfulness

## Decision

Use LLM-as-judge (DeepEval + GPT-OSS-120B).

## Why

Interview responses are:

- Open-ended
- Non-deterministic
- Not suitable for rule-based evaluation

## Alternatives Considered

| Approach | Issue |
|----------|------|
| Regex / keyword rules | Too brittle |
| Human evaluation | Not scalable |
| Exact match scoring | Not applicable |

## Trade-off

Less deterministic than rule-based systems, but scalable and realistic.

---

# 8. Lessons Learned (What Actually Broke)

## 8.1 LangGraph State Conflicts

Multiple nodes updated shared state incorrectly, causing overwritten values (especially token tracking).

Fix: reducer-based merges in `InterviewState`.

---

## 8.2 Linear Semantic Search Bottleneck

Initial cache used brute-force embedding similarity search.

Fix: ChromaDB HNSW index (`query()`), removing O(n) scaling.

---

## 8.3 Redis / Docker Dependency Issues

Problem: development required external services.

Fix: fallback to embedded Redis + JSON + embedded Chroma mode.

---

## 8.4 Prompt Instability

Small prompt changes caused cascading failures across nodes.

Fix: strict schemas + isolated responsibilities per node.

---

# 9. Future Improvements

- Human calibration of DeepEval scores
- MCP tool integration for extensible agents
- Persistent long-term candidate memory
- Multi-session interview continuity
- Real-time interruption handling (stop / regenerate / edit)

---

# Summary

This system is designed around:

- Structured multi-agent reasoning (LangGraph)
- Deterministic outputs (Pydantic schemas)
- Cost-aware model routing
- Hybrid caching for performance
- Streaming-first UX (SSE)
- Scalable evaluation (LLM-as-judge)

The trade-off is increased system complexity, but with significantly improved reliability, observability, and extensibility.