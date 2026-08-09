import os
import json
import logging
from typing import Dict, Any, List
from backend.app.graph.research_mode_state import ResearchModeState
from backend.app.llm import get_llm
from backend.app.tools.academic_search import search_academic_papers, screen_papers, format_apa

logger = logging.getLogger(__name__)


async def keyword_extractor_agent(state: ResearchModeState) -> Dict[str, Any]:
    """1. Extracts 6-10 dense, academic search keywords from PS + objectives."""
    logger.info("Running keyword_extractor_agent...")
    ps = state.get("problem_statement", "")
    objs = state.get("research_objectives", [])
    rqs = state.get("research_questions", [])

    llm = get_llm(role="planner")
    prompt = f"""Problem Statement:
{ps}

Research Objectives:
{json.dumps(objs)}

Research Questions:
{json.dumps(rqs)}

Extract 6 to 10 dense, academic search keywords and short search terms suitable for querying academic databases (OpenAlex, Semantic Scholar, ArXiv).
Return ONLY a JSON list of strings. Example: ["superconductivity", "high temperature cuprates", "LK-99 replication"]"""

    try:
        res = await llm.ainvoke(prompt)
        raw = res.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        keywords = json.loads(raw)
        if not isinstance(keywords, list):
            keywords = [ps[:30]]
    except Exception as e:
        logger.error(f"Error in keyword_extractor_agent: {e}")
        keywords = [ps[:50]]

    return {
        "keywords": keywords,
        "hitl_checkpoint": "checkpoint_1",
        "status": "awaiting_approval"
    }


async def paper_fetcher_agent(state: ResearchModeState) -> Dict[str, Any]:
    """2. Fetches raw papers from OpenAlex, Semantic Scholar, ArXiv using keywords."""
    logger.info("Running paper_fetcher_agent...")
    keywords = state.get("keywords", [])
    raw_papers = await search_academic_papers(keywords)
    return {
        "raw_papers": raw_papers,
        "status": "fetching_papers"
    }


async def paper_screener_agent(state: ResearchModeState) -> Dict[str, Any]:
    """3. Screens papers if >50, otherwise passes through."""
    logger.info("Running paper_screener_agent...")
    raw_papers = state.get("raw_papers", [])
    ps = state.get("problem_statement", "")
    objs = state.get("research_objectives", [])

    screened = await screen_papers(raw_papers, ps, objs)
    return {
        "screened_papers": screened,
        "status": "synthesizing"
    }


async def literature_review_agent(state: ResearchModeState) -> Dict[str, Any]:
    """4. Synthesizes screened papers into a themed literature review with inline citations."""
    logger.info("Running literature_review_agent...")
    papers = state.get("screened_papers", [])
    ps = state.get("problem_statement", "")
    objs = state.get("research_objectives", [])

    llm = get_llm(role="aggregator")
    
    papers_summary = "\n".join(
        f"- [{idx+1}] {p.get('authors', ['Anon'])[0]} et al. ({p.get('year', 'n.d.')}). {p.get('title')}: {p.get('abstract')[:250]}"
        for idx, p in enumerate(papers[:30])
    )

    prompt = f"""Problem Statement:
{ps}

Research Objectives:
{json.dumps(objs)}

Screened Papers Corpus:
{papers_summary}

Write a rigorous, themed Literature Review section (800 - 1500 words).
Group findings into logical sub-themes. Use formal academic prose with parenthetical inline citations matching the papers (e.g. (Author et al., 2024)).
Do NOT include markdown title headers (# Literature Review); output only section content formatted in Markdown."""

    res = await llm.ainvoke(prompt)
    return {"literature_review": res.content.strip()}


async def gap_analysis_agent(state: ResearchModeState) -> Dict[str, Any]:
    """5. Identifies what existing literature does NOT cover relative to the PS."""
    logger.info("Running gap_analysis_agent...")
    ps = state.get("problem_statement", "")
    lit_review = state.get("literature_review", "")

    llm = get_llm(role="planner")
    prompt = f"""Problem Statement:
{ps}

Literature Review Summary:
{lit_review[:2000]}

Identify the explicit Research Gap(s) in current literature. Explain clearly what existing studies fail to address, methodological limitations, or unresolved contradictions.
Keep it focused (250 - 500 words)."""

    res = await llm.ainvoke(prompt)
    return {"research_gap": res.content.strip()}


async def framework_agent(state: ResearchModeState) -> Dict[str, Any]:
    """6. Builds conceptual/theoretical framework from lit review + gap + objectives."""
    logger.info("Running framework_agent...")
    ps = state.get("problem_statement", "")
    gap = state.get("research_gap", "")
    objs = state.get("research_objectives", [])

    llm = get_llm(role="planner")
    prompt = f"""Problem Statement:
{ps}

Research Gap:
{gap}

Objectives:
{json.dumps(objs)}

Develop a cohesive Conceptual & Theoretical Framework. Define core constructs, theoretical foundations, and structural relationships between variables/factors.
Keep it structured and explicit (300 - 600 words)."""

    res = await llm.ainvoke(prompt)
    return {
        "conceptual_framework": res.content.strip(),
        "hitl_checkpoint": "checkpoint_2",
        "status": "awaiting_approval"
    }


async def hypotheses_agent(state: ResearchModeState) -> Dict[str, Any]:
    """7. Generates 2-5 falsifiable, testable hypotheses grounded in framework."""
    logger.info("Running hypotheses_agent...")
    framework = state.get("conceptual_framework", "")
    gap = state.get("research_gap", "")

    llm = get_llm(role="planner")
    prompt = f"""Conceptual Framework:
{framework}

Research Gap:
{gap}

Formulate 2 to 5 specific, falsifiable, testable research hypotheses (H1, H2, H3...).
Return ONLY a JSON list of strings. Example: ["H1: Factor A positively predicts Outcome B under condition C.", "H2: ..."]"""

    try:
        res = await llm.ainvoke(prompt)
        raw = res.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        hypotheses = json.loads(raw)
    except Exception as e:
        logger.error(f"Error in hypotheses_agent: {e}")
        hypotheses = ["H1: Primary intervention leads to measurable performance improvements over baseline."]

    return {
        "hypotheses": hypotheses,
        "hitl_checkpoint": "checkpoint_3",
        "status": "awaiting_approval"
    }


async def methodology_agent(state: ResearchModeState) -> Dict[str, Any]:
    """8. Proposes research design, data collection plan, and data analysis plan."""
    logger.info("Running methodology_agent...")
    hypotheses = state.get("hypotheses", [])
    framework = state.get("conceptual_framework", "")

    llm = get_llm(role="planner")
    prompt = f"""Hypotheses:
{json.dumps(hypotheses)}

Framework:
{framework[:1500]}

Propose a detailed Methodology comprising:
1. Research Design (experimental, quasi-experimental, observational, or empirical literature synthesis design)
2. Data Collection Plan (sources, sampling, parameters)
3. Data Analysis Plan (statistical/analytical methods, verification)

Return a JSON object with keys: "research_design", "data_collection_plan", "data_analysis_plan"."""

    try:
        res = await llm.ainvoke(prompt)
        raw = res.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        design = data.get("research_design", "")
        coll = data.get("data_collection_plan", "")
        ana = data.get("data_analysis_plan", "")
    except Exception as e:
        logger.error(f"Error in methodology_agent: {e}")
        design = "Empirical systematic review and quantitative meta-analysis design."
        coll = "Systematic retrieval across electronic database indexes (OpenAlex, Semantic Scholar, ArXiv)."
        ana = "Comparative statistical effect estimation and qualitative thematic synthesis."

    return {
        "research_design": design,
        "data_collection_plan": coll,
        "data_analysis_plan": ana,
        "hitl_checkpoint": "checkpoint_4",
        "status": "awaiting_approval"
    }


async def results_agent(state: ResearchModeState) -> Dict[str, Any]:
    """9. Synthesizes findings from screened papers relevant to each hypothesis."""
    logger.info("Running results_agent...")
    hypotheses = state.get("hypotheses", [])
    papers = state.get("screened_papers", [])

    llm = get_llm(role="aggregator")
    papers_str = "\n".join(f"- {p.get('title')}: {p.get('abstract')[:200]}" for p in papers[:25])

    prompt = f"""Hypotheses:
{json.dumps(hypotheses)}

Empirical Evidence Corpus:
{papers_str}

Synthesize the empirical Results for each hypothesis based on evidence from the literature corpus. Indicate whether each hypothesis is supported, partially supported, or unsupported by empirical evidence.
Length: 500 - 900 words."""

    res = await llm.ainvoke(prompt)
    return {"results": res.content.strip()}


async def discussion_agent(state: ResearchModeState) -> Dict[str, Any]:
    """10. Interprets results, connects to hypotheses, explores contradictions."""
    logger.info("Running discussion_agent...")
    results = state.get("results", "")
    hypotheses = state.get("hypotheses", [])
    lit_review = state.get("literature_review", "")

    llm = get_llm(role="aggregator")
    prompt = f"""Results:
{results[:2000]}

Hypotheses:
{json.dumps(hypotheses)}

Literature Context:
{lit_review[:1000]}

Write the Discussion section. Contextualize the findings within prior research, explain unexpected outcomes or contradictions, and examine theoretical underlying mechanisms.
Length: 400 - 800 words."""

    res = await llm.ainvoke(prompt)
    return {"discussion": res.content.strip()}


async def implications_agent(state: ResearchModeState) -> Dict[str, Any]:
    """11. Theoretical and practical implications."""
    logger.info("Running implications_agent...")
    discussion = state.get("discussion", "")

    llm = get_llm(role="planner")
    prompt = f"""Discussion:
{discussion[:2000]}

Detail both Theoretical Implications (contributions to scholarly literature) and Practical/Managerial Implications (actionable real-world applications).
Length: 300 - 500 words."""

    res = await llm.ainvoke(prompt)
    return {"implications": res.content.strip()}


async def limitations_agent(state: ResearchModeState) -> Dict[str, Any]:
    """12. Honest, specific limitations of the study."""
    logger.info("Running limitations_agent...")
    methodology = state.get("research_design", "")
    results = state.get("results", "")

    llm = get_llm(role="planner")
    prompt = f"""Methodology & Design:
{methodology[:1000]}

Results Summary:
{results[:1000]}

State the explicit Limitations of this study (sample size/corpus constraints, analytical boundaries, potential confounding factors, publication bias).
Length: 200 - 400 words."""

    res = await llm.ainvoke(prompt)
    return {"limitations": res.content.strip()}


async def conclusion_agent(state: ResearchModeState) -> Dict[str, Any]:
    """13. Concise summary of contributions."""
    logger.info("Running conclusion_agent...")
    ps = state.get("problem_statement", "")
    results = state.get("results", "")

    llm = get_llm(role="planner")
    prompt = f"""Problem Statement:
{ps}

Results & Key Findings:
{results[:1500]}

Write a clear, authoritative Conclusion summarizing key research insights and overall contribution.
Length: 200 - 350 words."""

    res = await llm.ainvoke(prompt)
    return {"conclusion": res.content.strip()}


async def future_scope_agent(state: ResearchModeState) -> Dict[str, Any]:
    """14. 3-5 concrete, specific future research directions."""
    logger.info("Running future_scope_agent...")
    limitations = state.get("limitations", "")
    discussion = state.get("discussion", "")

    llm = get_llm(role="planner")
    prompt = f"""Limitations:
{limitations[:1000]}

Discussion:
{discussion[:1000]}

Propose 3 to 5 concrete Future Research Directions.
Return ONLY a JSON list of strings. Example: ["1. Investigate long-term stability using experimental trial X.", "2. ..."]"""

    try:
        res = await llm.ainvoke(prompt)
        raw = res.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        future_scope = json.loads(raw)
    except Exception as e:
        logger.error(f"Error in future_scope_agent: {e}")
        future_scope = ["Validate findings across expanded multi-center empirical trials."]

    return {"future_scope": future_scope}


async def references_agent(state: ResearchModeState) -> Dict[str, Any]:
    """15. Compiles all cited papers into formatted APA reference list."""
    logger.info("Running references_agent...")
    papers = state.get("screened_papers", []) or state.get("raw_papers", [])
    references = [format_apa(p) for p in papers if p.get("title")]
    return {"references": references}


async def introduction_agent(state: ResearchModeState) -> Dict[str, Any]:
    """16. Written LAST, retrospectively frames the entire paper."""
    logger.info("Running introduction_agent...")
    ps = state.get("problem_statement", "")
    objs = state.get("research_objectives", [])
    rqs = state.get("research_questions", [])
    results = state.get("results", "")

    llm = get_llm(role="aggregator")
    prompt = f"""Problem Statement:
{ps}

Objectives:
{json.dumps(objs)}

Research Questions:
{json.dumps(rqs)}

Synthesized Key Results:
{results[:1500]}

Write a comprehensive Introduction section for this academic paper.
Include: Background & Context, Problem Definition, Significance & Scope, and Paper Roadmap.
Length: 500 - 900 words."""

    res = await llm.ainvoke(prompt)
    return {"introduction": res.content.strip()}


async def abstract_agent(state: ResearchModeState) -> Dict[str, Any]:
    """17. Written LAST, structured ~250-word abstract: background / objective / method / results / conclusion."""
    logger.info("Running abstract_agent...")
    intro = state.get("introduction", "")
    method = state.get("research_design", "")
    results = state.get("results", "")
    conclusion = state.get("conclusion", "")

    llm = get_llm(role="planner")
    prompt = f"""Introduction Overview:
{intro[:600]}

Methodology:
{method[:400]}

Key Results:
{results[:600]}

Conclusion:
{conclusion[:400]}

Write a structured academic Abstract (~200 - 250 words) with the explicit subheadings:
Background, Objective, Methods, Results, Conclusion."""

    res = await llm.ainvoke(prompt)
    return {"abstract": res.content.strip()}


async def title_agent(state: ResearchModeState) -> Dict[str, Any]:
    """18. Finalizes paper title after all content is complete."""
    logger.info("Running title_agent...")
    ps = state.get("problem_statement", "")
    abstract = state.get("abstract", "")

    llm = get_llm(role="planner")
    prompt = f"""Problem Statement:
{ps}

Abstract:
{abstract}

Generate a compelling, formal academic paper title.
Return ONLY the title string, without quotes."""

    res = await llm.ainvoke(prompt)
    title = res.content.strip().replace('"', '')
    return {
        "title": title,
        "hitl_checkpoint": "completed",
        "status": "completed"
    }
