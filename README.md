# AI Interview Coach

> A production-style multi-agent AI system that conducts realistic technical and behavioral interviews, evaluates answers across multiple dimensions, and streams real-time feedback.

This system demonstrates end-to-end AI system design using a 9-agent LangGraph pipeline, a FastAPI backend, a React frontend, hybrid retrieval caching (Redis + ChromaDB), and an evaluation suite powered by DeepEval.

---

# Why This Project

Most interview preparation tools fall into one of two categories:

- Static question banks with no intelligence
- Single LLM calls with no memory, routing, or evaluation structure

This project explores what happens when interview simulation is designed as a **stateful multi-agent system**, closer to a production AI pipeline than a prompt demo.

It focuses on:

- Multi-agent orchestration (LangGraph)
- Stateful reasoning across sessions
- Retrieval-augmented grounding (Tavily + cache)
- Cost/latency optimization via model routing
- Evaluation-driven AI behavior (LLM-as-judge)

---

## Screenshots

![Interview in Progress](docs/screenshots/interview.png)
![Streaming Response](docs/screenshots/streaming.png)

---

# Key Features

## Multi-Agent Intelligence

A structured 9-agent LangGraph pipeline:
