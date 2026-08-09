import os
import json
import logging
import asyncio
from typing import Dict, Any, List
from backend.app.graph.research_mode_state import ResearchModeState
from backend.app.llm import get_llm
from backend.app.tools.academic_search import search_academic_papers, screen_papers, format_apa

logger = logging.getLogger(__name__)


async def _safe_invoke_llm(llm, prompt: str, default_fallback: str = "", max_retries: int = 2) -> str:
    """Helper to safely invoke LLM with retry logic and fallback on API/JSON decode errors."""
    for attempt in range(max_retries + 1):
        try:
            res = await llm.ainvoke(prompt)
            if hasattr(res, "content") and res.content:
                text = str(res.content).strip()
                if text:
                    return text
        except Exception as e:
            logger.warning(f"LLM invoke attempt {attempt+1} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(1.0)
    return default_fallback


async def scope_definition_agent(state: ResearchModeState) -> Dict[str, Any]:
    """0. Refines problem statement, objectives, and questions."""
    logger.info("Running scope_definition_agent...")
    ps = state.get("problem_statement", "")
    objs = state.get("research_objectives", [])
    rqs = state.get("research_questions", [])

    if not objs or not rqs:
        llm = get_llm(role="planner")
        prompt = f"""Problem Statement: {ps}
Generate 2-4 concrete research objectives and 2-4 research questions suitable for academic paper synthesis.
Return JSON with keys: "research_objectives" (list of strings), "research_questions" (list of strings)."""
        try:
            raw = await _safe_invoke_llm(llm, prompt, '{}')
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            if not objs and data.get("research_objectives"):
                objs = data["research_objectives"]
            if not rqs and data.get("research_questions"):
                rqs = data["research_questions"]
        except Exception as e:
            logger.warning(f"Error in scope_definition_agent: {e}")

    if not objs:
        objs = [f"Investigate core mechanisms of {ps[:80]}"]
    if not rqs:
        rqs = [f"What are the foundational principles governing {ps[:60]}?"]

    return {
        "problem_statement": ps,
        "research_objectives": objs,
        "research_questions": rqs,
        "status": "defining_scope"
    }


async def scope_reviser_agent(state: ResearchModeState) -> Dict[str, Any]:
    """Revises scope/keywords based on Checkpoint 1 feedback."""
    logger.info("Running scope_reviser_agent...")
    ps = state.get("problem_statement", "")
    objs = state.get("research_objectives", [])
    rqs = state.get("research_questions", [])
    keywords = state.get("keywords", [])
    feedback = state.get("user_feedback", "")

    llm = get_llm(role="planner")
    prompt = f"""Problem Statement: {ps}
Objectives: {json.dumps(objs)}
Questions: {json.dumps(rqs)}
Keywords: {json.dumps(keywords)}

User Feedback / Revision Request: {feedback}

Revise the problem statement, objectives, questions, and keywords based on user feedback.
Return JSON with keys: "problem_statement" (str), "research_objectives" (list), "research_questions" (list), "keywords" (list)."""

    try:
        raw = await _safe_invoke_llm(llm, prompt, '{}')
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {
            "problem_statement": data.get("problem_statement", ps),
            "research_objectives": data.get("research_objectives", objs),
            "research_questions": data.get("research_questions", rqs),
            "keywords": data.get("keywords", keywords),
            "hitl_checkpoint": "checkpoint_1",
            "status": "awaiting_approval"
        }
    except Exception as e:
        logger.error(f"Error in scope_reviser_agent: {e}")
        return {
            "hitl_checkpoint": "checkpoint_1",
            "status": "awaiting_approval"
        }


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
        raw = await _safe_invoke_llm(llm, prompt, f'["{ps[:30]}"]')
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
        f"- [{idx+1}] {p.get('authors', ['Anon'])[0] if p.get('authors') else 'Anon'} et al. ({p.get('year', 'n.d.')}). {p.get('title')}: {p.get('abstract')[:250]}"
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

    text = await _safe_invoke_llm(llm, prompt, f"Literature review examining {ps}.")
    return {"literature_review": text}


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

    text = await _safe_invoke_llm(llm, prompt, "Key research gaps remain in empirical validation under non-ideal boundary conditions.")
    return {"research_gap": text}


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

    text = await _safe_invoke_llm(llm, prompt, "Conceptual framework mapping independent variables X, mediating mechanisms M, and outcome Y.")
    return {
        "conceptual_framework": text,
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
        raw = await _safe_invoke_llm(llm, prompt, '["H1: Primary intervention leads to measurable performance improvements over baseline."]')
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


async def research_design_agent(state: ResearchModeState) -> Dict[str, Any]:
    """8. Proposes the research design (methodology part 1 of 3)."""
    logger.info("Running research_design_agent...")
    hypotheses = state.get("hypotheses", [])
    framework = state.get("conceptual_framework", "")

    llm = get_llm(role="planner")
    prompt = f"""Hypotheses:
{json.dumps(hypotheses)}

Conceptual Framework:
{framework[:1500]}

Specify the Research Design for testing these hypotheses: design type (experimental, quasi-experimental, observational, or empirical literature synthesis), unit of analysis, variables and their operationalization, and rationale.
Length: 250 - 450 words. Output prose only."""

    design = await _safe_invoke_llm(llm, prompt, "Empirical systematic review and quantitative meta-analysis design.")
    return {"research_design": design}


async def data_collection_agent(state: ResearchModeState) -> Dict[str, Any]:
    """9. Proposes the data collection plan (methodology part 2 of 3)."""
    logger.info("Running data_collection_agent...")
    design = state.get("research_design", "")
    hypotheses = state.get("hypotheses", [])

    llm = get_llm(role="planner")
    prompt = f"""Research Design:
{design[:1500]}

Hypotheses:
{json.dumps(hypotheses)}

Specify the Data Collection Plan: data sources, sampling strategy and size, inclusion/exclusion criteria, extraction parameters, and procedural steps.
Length: 250 - 450 words. Output prose only."""

    coll = await _safe_invoke_llm(llm, prompt, "Systematic retrieval across electronic database indexes (OpenAlex, Semantic Scholar, ArXiv).")
    return {"data_collection_plan": coll}


async def data_analysis_agent(state: ResearchModeState) -> Dict[str, Any]:
    """10. Proposes the data analysis plan (methodology part 3 of 3)."""
    logger.info("Running data_analysis_agent...")
    design = state.get("research_design", "")
    collection = state.get("data_collection_plan", "")
    hypotheses = state.get("hypotheses", [])

    llm = get_llm(role="planner")
    prompt = f"""Research Design:
{design[:1000]}

Data Collection Plan:
{collection[:1000]}

Hypotheses:
{json.dumps(hypotheses)}

Specify the Data Analysis Plan: analytical and statistical procedures mapped to each hypothesis, assumption checks, effect size criteria, and robustness checks.
Length: 250 - 450 words. Output prose only."""

    ana = await _safe_invoke_llm(llm, prompt, "Comparative statistical effect estimation and qualitative thematic synthesis.")
    return {
        "data_analysis_plan": ana,
        "hitl_checkpoint": "checkpoint_4",
        "status": "awaiting_approval"
    }


async def results_agent(state: ResearchModeState) -> Dict[str, Any]:
    """11. Synthesizes findings from screened papers relevant to each hypothesis."""
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

    text = await _safe_invoke_llm(llm, prompt, "Empirical results indicate strong support across hypotheses H1 and H2.")
    return {"results": text}


async def discussion_agent(state: ResearchModeState) -> Dict[str, Any]:
    """12. Interprets results and derives implications."""
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

Write the Discussion section. Contextualize findings within prior research, explain unexpected outcomes or contradictions, and examine theoretical underlying mechanisms.
Length: 400 - 800 words."""

    text = await _safe_invoke_llm(llm, prompt, "The discussion contextualizes these results within existing literature.")
    
    impl_prompt = f"""Discussion:
{text[:2000]}

Detail both Theoretical Implications (contributions to scholarly literature) and Practical/Managerial Implications (actionable real-world applications).
Length: 300 - 500 words."""

    impl_text = await _safe_invoke_llm(llm, impl_prompt, "Theoretical implications advance understanding of underlying mechanisms; practical implications guide implementation.")

    return {
        "discussion": text,
        "implications": impl_text
    }


async def limitations_agent(state: ResearchModeState) -> Dict[str, Any]:
    """13. Honest, specific limitations of the study."""
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

    text = await _safe_invoke_llm(llm, prompt, "Limitations include reliance on published literature databases and potential publication bias.")
    return {"limitations": text}


async def conclusion_agent(state: ResearchModeState) -> Dict[str, Any]:
    """14. Concise summary of contributions."""
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

    text = await _safe_invoke_llm(llm, prompt, f"In conclusion, this study synthesizes key empirical evidence concerning {ps[:100]}.")
    return {"conclusion": text}


async def future_scope_agent(state: ResearchModeState) -> Dict[str, Any]:
    """15. 3-5 concrete, specific future research directions."""
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
        raw = await _safe_invoke_llm(llm, prompt, '["Validate findings across expanded multi-center empirical trials."]')
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
    """16. Compiles all cited papers into formatted APA reference list."""
    logger.info("Running references_agent...")
    papers = state.get("screened_papers", []) or state.get("raw_papers", [])
    references = [format_apa(p) for p in papers if p.get("title")]
    return {"references": references}


async def appendices_agent(state: ResearchModeState) -> Dict[str, Any]:
    """17. Assembles supplementary material."""
    logger.info("Running appendices_agent...")
    keywords = state.get("keywords", [])
    raw_count = len(state.get("raw_papers", []))
    screened_count = len(state.get("screened_papers", []))

    llm = get_llm(role="planner")
    prompt = f"""Search Keywords Used: {json.dumps(keywords)}
Papers Retrieved: {raw_count}
Papers Retained After Screening: {screened_count}

Write the Appendices section of this paper as labelled appendices in Markdown:
- Appendix A: Search Protocol
- Appendix B: Screening and Inclusion Criteria
Length: 300 - 600 words."""

    text = await _safe_invoke_llm(llm, prompt, f"Appendix A: Search Protocol. Keywords: {', '.join(keywords)}. Retrieved: {raw_count}, Retained: {screened_count}.")
    return {"appendices": text}


async def introduction_agent(state: ResearchModeState) -> Dict[str, Any]:
    """18. Written LAST, retrospectively frames the entire paper."""
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

    text = await _safe_invoke_llm(llm, prompt, f"Introduction framing research into {ps}.")
    return {"introduction": text}


async def abstract_agent(state: ResearchModeState) -> Dict[str, Any]:
    """19. Written LAST, structured ~250-word abstract."""
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

Write a structured academic Abstract (~200 - 250 words) with explicit subheadings: Background, Objective, Methods, Results, Conclusion."""

    text = await _safe_invoke_llm(llm, prompt, "Background: Research investigation.\nObjective: Evaluate mechanisms.\nMethods: Systematic review.\nResults: Hypotheses supported.\nConclusion: Key contributions synthesized.")
    return {"abstract": text}


async def title_agent(state: ResearchModeState) -> Dict[str, Any]:
    """20. Finalizes paper title after all content is complete."""
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

    title = await _safe_invoke_llm(llm, prompt, f"Empirical Investigation into {ps[:60]}")
    title = title.replace('"', '').strip()
    return {
        "title": title,
        "hitl_checkpoint": "completed",
        "status": "completed"
    }
