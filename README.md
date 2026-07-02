# <img src="https://cdn-1.webcatalog.io/catalog/dolphin-ai/dolphin-ai-icon-filled-256.png?v=1734075877011" width="32" height="32" style="vertical-align: middle;"> DeepResearch

An AI-powered multi-agent research assistant that turns a query into a structured, cited research report — with human-in-the-loop plan approval and real-time streaming.

<video src="vids/2026-07-02 16-05-52.mp4" width="100%" controls></video>

---

## How It Works

```
Query → Validator → Planner (PS + sub-tasks) → HITL Approval → Parallel Researchers → Aggregator → Report
```

1. User submits a research query with optional topic filters (News, Academic, Finance, Patents)
2. A **Planner Agent** generates a Problem Statement + up to 5 independent research sub-tasks
3. User reviews and approves the plan (or requests revisions in natural language)
4. Up to 5 **Parallel Research Workers** search the web simultaneously via Tavily
5. An **Aggregator Agent** synthesizes all findings into a structured markdown report
6. User can download the report as a `.md` file

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Graph | LangGraph (HITL, Send() API, MemorySaver) |
| LLM | DeepSeek Pro (planner, aggregator) + Flash (approval, researchers) |
| Web Search | Tavily API |
| Backend | FastAPI + SSE streaming |
| Frontend | Vanilla JS + Nginx |
| Containerization | Docker + Docker Compose |

---

## Features

- **Multi-agent graph** — parallel researchers fan out via LangGraph's `Send()` API
- **Human-in-the-Loop** — review and revise the research plan before execution
- **Real-time SSE streaming** — live researcher progress updates in the UI
- **Query validation** — rejects vague queries before hitting the LLM
- **Markdown export** — download the final report as a `.md` file
- **Session persistence** — resume interrupted sessions via localStorage
- **Dark/Light mode** — theme toggle with persistent preference

---

## Project Structure

```
research-bot/
├── backend/
│   ├── app/
│   │   ├── agents/          # planner, validator, approval, researcher, aggregator
│   │   ├── api/             # FastAPI routes + SSE
│   │   ├── graph/           # LangGraph state + builder
│   │   ├── tools/           # Tavily search tool
│   │   └── llm.py           # DeepSeek LLM config
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Getting Started

### Prerequisites

- Docker + Docker Compose
- DeepSeek API key → [platform.deepseek.com](https://platform.deepseek.com)
- Tavily API key → [tavily.com](https://tavily.com)

### 1. Clone the repo

```bash
git clone https://github.com/Aryan-Pardeshi/deep-research.git
cd deep-research/research-bot
```

### 2. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env`:
```
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
TAVILY_API_KEY=your_key_here
```

### 3. Run with Docker

```bash
docker compose up -d --build
```

- Frontend → [http://localhost:80](http://localhost:80)
- Backend → [http://localhost:8000](http://localhost:8000)

---

### Local Development (without Docker)

#### Backend

```bash
cd research-bot
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

#### Frontend

Open `frontend/index.html` directly in your browser, or serve with any static file server:

```bash
npx serve frontend
```

> Make sure `API_BASE_URL` in `app.js` points to `http://localhost:8000`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/research/start` | Validate query, generate PS + plan |
| `POST` | `/research/approve` | Resume graph, stream SSE events |
| `GET` | `/research/result/{thread_id}` | Fetch final report by thread |

---

## Author

Built by [Aryan Pardeshi](https://github.com/Aryan-Pardeshi) — open to AI/ML internship opportunities.

Connect: [LinkedIn](https://linkedin.com/in/aryan-pardeshi-dev) · [GitHub](https://github.com/Aryan-Pardeshi)
