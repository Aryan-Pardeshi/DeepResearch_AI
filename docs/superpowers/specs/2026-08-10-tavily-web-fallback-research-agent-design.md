# Design Spec: Tavily Web Search Last-Resort Fallback for Research Agents

## Overview
Equip the Research Mode literature retrieval pipeline (`academic_search.py`, `agents.py`) with Tavily Web Search as a **last-resort fallback tool** when academic indexes (OpenAlex, Semantic Scholar, ArXiv) fail to yield sufficient relevant papers.

## Key System Prompt & Fallback Rules

### 1. System Prompt Instruction for Literature & Research Agents
Add explicit prompt directive:
> **LAST-RESORT WEB SEARCH POLICY**: Literature and paper retrieval MUST always prioritize formal academic database indexes (OpenAlex, Semantic Scholar, ArXiv). Tavily Web Search is provided ONLY as a LAST RESORT fallback when academic indexes return zero or insufficient relevant results for a niche topic.

### 2. Automatic Last-Resort Fallback Execution (`fetch_tavily_web_papers`)
- In `academic_search.py`, if academic database queries yield fewer than 5 deduplicated papers across OpenAlex, Semantic Scholar, and ArXiv:
  - Trigger `fetch_tavily_web_papers(keyword)` using Tavily Web Search.
  - Format web search results into paper objects marked with `"source": "tavily_web_fallback"`.
  - Append to corpus so downstream screening and synthesis agents can process them seamlessly.
