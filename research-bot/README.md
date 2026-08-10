---
title: DeepResearch
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# DeepResearch

Multi-agent research assistant. Give it a problem statement and it searches OpenAlex,
Semantic Scholar, and ArXiv, screens the corpus for relevance, and writes a full
academic paper with a PRISMA flow diagram, verified citations, and PDF/DOCX export.
Four human-in-the-loop checkpoints let you steer the scope, framework, hypotheses,
and methodology before it commits to them.

## Configuration

Set these under **Settings → Variables and secrets**.

Secrets:

| Name | Required | Purpose |
|------|----------|---------|
| `LLM_API_KEY` | yes | OpenAI-compatible API key |
| `TAVILY_API_KEY` | for DeepSearch mode | Web search |
| `CONFIG_API_TOKEN` | no | Enables the in-browser settings page, sent as `X-Config-Token` |

Variables:

| Name | Default | Purpose |
|------|---------|---------|
| `LLM_BASE_URL` | `https://api.deepseek.com` | Any OpenAI-compatible endpoint |
| `LLM_MODEL_PLANNER` | `deepseek-chat` | Overridable per run in the UI |
| `LLM_MODEL_RESEARCHER` | `deepseek-chat` | Screening; a cheaper model suits this |
| `LLM_MODEL_AGGREGATOR` | `deepseek-chat` | Long-form writing |
| `OPENALEX_EMAIL` | — | Required by OpenAlex and Unpaywall for the polite pool |
| `CORE_API_KEY` | — | Free key that recovers extra open-access full texts |

The configuration API fails closed. Without `CONFIG_API_TOKEN` the in-browser
settings page cannot write, which is deliberate: that endpoint can rewrite
`LLM_API_KEY` and `LLM_BASE_URL`, so it must not be reachable unauthenticated on a
public URL. Set the keys as secrets above and you never need it.

## Storage

Graph checkpoints, the LLM response cache, and generated figures live in
`/app/data`. On the free tier this is ephemeral — it is wiped when the Space
restarts or rebuilds, so a run in progress loses its resume state. Attach
persistent storage, or point `RESEARCH_DB_PATH` at an external database, to keep
sessions across restarts.

## Running locally

```bash
cp .env.example .env      # then fill in your keys
docker compose up --build
```

Then open http://localhost:8000. For local use, add `ALLOW_OPEN_CONFIG_API=1` to
`.env` if you want the in-browser settings page to work without a token.
