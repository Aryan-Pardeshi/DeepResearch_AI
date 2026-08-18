import asyncio
import logging
import time
import os
import uuid
import pypdf
from langgraph.types import Command
from backend.app.graph.research_mode_builder import get_research_mode_graph
from backend.app.tools.pdf_generator import generate_paper_pdf

class LogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.warnings_and_errors = []

    def emit(self, record):
        if record.levelno >= logging.WARNING:
            self.warnings_and_errors.append((record.levelname, record.getMessage()))

async def run_e2e_test():
    log_handler = LogHandler()
    logging.getLogger().addHandler(log_handler)
    logging.getLogger().setLevel(logging.INFO)

    ps = "Impact of generative AI code assistants on software developer productivity and code security"
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_research_mode_graph()

    initial_state = {
        "thread_id": thread_id,
        "mode": "research",
        "problem_statement": ps,
        "research_objectives": [],
        "research_questions": [],
        "keywords": [],
        "raw_papers": [],
        "screened_papers": [],
        "model_overrides": {},
        "status": "initializing"
    }

    node_timings = {}
    total_start = time.time()

    print(f"--- Starting End-to-End Pipeline Run (thread_id: {thread_id[:8]}) ---")
    print(f"Problem Statement: '{ps}'")

    current_node = None
    node_start_time = None

    # Step 1: Run until Checkpoint 1
    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        evt_type = event.get("event")
        if evt_type == "on_chain_start":
            node = event.get("metadata", {}).get("langgraph_node")
            if node and not node.startswith("__"):
                current_node = node
                node_start_time = time.time()
        elif evt_type == "on_chain_end":
            node = event.get("metadata", {}).get("langgraph_node")
            if node and node == current_node and node_start_time:
                elapsed = time.time() - node_start_time
                node_timings[node] = elapsed
                print(f"  [NODE COMPLETED] {node}: {elapsed:.2f}s")
                current_node = None

    # Step 2: Loop through Checkpoints 1, 2, 3, 4 until completion
    while True:
        state = await graph.aget_state(config)
        if not state or not state.next:
            break

        next_node = list(state.next)[0]
        print(f"  [CHECKPOINT INTERRUPT] {next_node} -> Resuming with approval")

        cp_start = time.time()
        async for event in graph.astream_events(Command(resume={"message": "approve"}), config=config, version="v2"):
            evt_type = event.get("event")
            if evt_type == "on_chain_start":
                node = event.get("metadata", {}).get("langgraph_node")
                if node and not node.startswith("__"):
                    current_node = node
                    node_start_time = time.time()
            elif evt_type == "on_chain_end":
                node = event.get("metadata", {}).get("langgraph_node")
                if node and node == current_node and node_start_time:
                    elapsed = time.time() - node_start_time
                    node_timings[node] = elapsed
                    print(f"  [NODE COMPLETED] {node}: {elapsed:.2f}s")
                    current_node = None

        node_timings[next_node] = time.time() - cp_start

    total_wall_time = time.time() - total_start

    # Fetch final state
    final_state_obj = await graph.aget_state(config)
    final_values = final_state_obj.values if final_state_obj else {}

    print(f"\n--- Total Wall Time: {total_wall_time:.2f}s ---")
    print("\n--- Per-Node Timing ---")
    for n, t in node_timings.items():
        print(f"  - {n:20s}: {t:6.2f}s")

    print(f"\n--- Warnings / Errors Raised ({len(log_handler.warnings_and_errors)}) ---")
    for lvl, msg in log_handler.warnings_and_errors:
        print(f"  [{lvl}] {msg}")

    # Check 20 sections population
    sections = [
        "problem_statement", "research_objectives", "research_questions", "keywords",
        "raw_papers", "screened_papers", "literature_review", "research_gap",
        "conceptual_framework", "hypotheses", "research_design", "data_collection_plan",
        "data_analysis_plan", "results", "discussion", "implications",
        "limitations", "conclusion", "future_scope", "references",
        "appendices", "introduction", "abstract", "title"
    ]

    populated = {s: bool(final_values.get(s)) for s in sections}
    all_pop = all(populated.values())
    print(f"\n--- Sections Population Check ({sum(populated.values())}/{len(sections)}) ---")
    for s, ok in populated.items():
        val_summary = f"({len(final_values[s])} items/chars)" if final_values.get(s) else "(EMPTY)"
        print(f"  [{'OK' if ok else 'FAIL'}] {s:22s} {val_summary}")

    # Generate PDF
    pdf_path = f"./data/figures/paper_e2e_{thread_id[:8]}.pdf"
    os.makedirs("./data/figures", exist_ok=True)
    generate_paper_pdf(final_values, pdf_path)
    pdf_size = os.path.getsize(pdf_path)

    print(f"\n--- Exported PDF ---")
    print(f"  Path: {pdf_path}")
    print(f"  File Size: {pdf_size} bytes ({pdf_size / 1024:.1f} KB)")
    
    reader = pypdf.PdfReader(pdf_path)
    print(f"  Total PDF pages: {len(reader.pages)}")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
