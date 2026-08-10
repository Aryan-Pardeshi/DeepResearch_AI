# DOCX Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Word (`.docx`) document export for research papers in both backend API and frontend user interface.

**Architecture:** A new backend generator (`docx_generator.py`) builds native `.docx` files using `python-docx` directly from `ResearchModeState`. FastAPI exposes `POST /api/research-mode/export/docx/{thread_id}`, and the frontend replaces the single PDF button with a styled Export Dropdown supporting PDF and Word downloads.

**Tech Stack:** Python 3.11+, FastAPI, `python-docx>=1.1.0`, Vanilla JS, HTML5, CSS3.

## Global Constraints
- Target directory: `research-bot/`
- Endpoint URL: `POST /api/research-mode/export/docx/{thread_id}` (with alias `/api/research/mode/export/docx/{thread_id}`)
- Export directory: `research-bot/backend/app/static/exports/`
- Output filename: `research_paper_{thread_id[:8]}.docx`
- Content Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`

---

### Task 1: Add `python-docx` dependency

**Files:**
- Modify: `research-bot/requirements.txt`

**Interfaces:**
- Consumes: None
- Produces: `python-docx` library installed in Python environment

- [ ] **Step 1: Add python-docx to requirements.txt**

```text
python-docx>=1.1.0
```

- [ ] **Step 2: Install dependency in .venv**

Run: `.venv\Scripts\python.exe -m pip install "python-docx>=1.1.0"`
Expected: Successfully installed python-docx

- [ ] **Step 3: Verify import works**

Run: `.venv\Scripts\python.exe -c "import docx; print(docx.__version__)"`
Expected: Outputs version (e.g., `1.1.2`)

- [ ] **Step 4: Commit**

```bash
git add research-bot/requirements.txt
git commit -m "deps: add python-docx to requirements.txt"
```

---

### Task 2: Implement `docx_generator.py`

**Files:**
- Create: `research-bot/backend/app/tools/docx_generator.py`
- Test: `research-bot/test_docx_generator.py`

**Interfaces:**
- Consumes: `state: Dict[str, Any]` (ResearchModeState dictionary)
- Produces: `generate_paper_docx(state: Dict[str, Any], output_path: str) -> str`

- [ ] **Step 1: Write test script for docx_generator**

Create `research-bot/test_docx_generator.py`:
```python
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.tools.docx_generator import generate_paper_docx

def test_docx_generation():
    dummy_state = {
        "problem_statement": "Autonomous Multi-Agent Search and Rescue in Subterranean Environments",
        "title": "Autonomous Multi-Agent Robotics in Subterranean Search and Rescue",
        "abstract": "This study explores multi-agent coordination under communication constraints.",
        "keywords": ["Robotics", "Multi-Agent", "Subterranean"],
        "introduction": "Subterranean environments present severe operational challenges...",
        "literature_review": "Prior work by Smith et al. (2024) demonstrated...",
        "research_gap": "Limited real-time adaptivity under total comms loss.",
        "research_objectives": ["Develop decentralized consensus", "Evaluate search coverage"],
        "research_questions": ["How does loss of comms affect latency?"],
        "conceptual_framework": "Decentralized Graph Neural Network framework.",
        "hypotheses": ["H1: Decentralized routing reduces latency by 30%."],
        "research_design": "Experimental simulation benchmark.",
        "data_collection_plan": "Simulated sensor logs across 50 cavern trials.",
        "data_analysis_plan": "ANOVA variance analysis of coverage rates.",
        "results": "Decentralized agents achieved 94% coverage.",
        "discussion": "The findings confirm H1 predictions.",
        "implications": "Crucial for emergency response teams.",
        "limitations": "Simulated noise models may underrepresent extreme dust.",
        "conclusion": "Decentralized multi-agent systems significantly improve resilience.",
        "future_scope": "Field deployment in active mine shafts.",
        "references": ["Smith, J. et al. (2024). Robotics in Caverns. IEEE Trans."],
        "appendices": ["Appendix A: Simulation Hyperparameters"]
    }

    out_file = root_dir / "test_doc_output.docx"
    result_path = generate_paper_docx(dummy_state, str(out_file))

    assert os.path.exists(result_path), "DOCX file was not created"
    assert os.path.getsize(result_path) > 1000, "DOCX file is too small or empty"
    print(f"SUCCESS: DOCX generated at {result_path} ({os.path.getsize(result_path)} bytes)")

if __name__ == "__main__":
    test_docx_generation()
```

- [ ] **Step 2: Run test script to verify it fails**

Run: `.venv\Scripts\python.exe research-bot/test_docx_generator.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app.tools.docx_generator'`

- [ ] **Step 3: Implement `docx_generator.py`**

Create `research-bot/backend/app/tools/docx_generator.py`:
```python
import logging
from pathlib import Path
from typing import Dict, Any, List
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

logger = logging.getLogger(__name__)

def _set_cell_background(cell, fill_hex: str):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def generate_paper_docx(state: Dict[str, Any], output_path: str) -> str:
    """Generates a styled academic Word document (.docx) from ResearchModeState."""
    doc = docx.Document()

    # Set 1-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    # Title
    title_text = state.get("title") or state.get("problem_statement") or "Research Report"
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title_p.add_run(title_text)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = RGBColor(0x1A, 0x2B, 0x4C)
    title_p.paragraph_format.space_after = Pt(12)

    # Abstract Box
    abstract_text = state.get("abstract", "").strip()
    if abstract_text:
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        _set_cell_background(cell, "F0F4F8")
        
        ap = cell.paragraphs[0]
        arun_bold = ap.add_run("ABSTRACT\n")
        arun_bold.bold = True
        arun_bold.font.size = Pt(10)
        arun_bold.font.color.rgb = RGBColor(0x1A, 0x2B, 0x4C)
        
        arun_text = ap.add_run(abstract_text)
        arun_text.font.size = Pt(10.5)
        arun_text.font.italic = True
        ap.paragraph_format.space_after = Pt(4)

        # Keywords
        keywords = state.get("keywords", [])
        if keywords:
            kw_str = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
            kw_p = cell.add_paragraph()
            kw_bold = kw_p.add_run("Keywords: ")
            kw_bold.bold = True
            kw_bold.font.size = Pt(9.5)
            kw_text = kw_p.add_run(kw_str)
            kw_text.font.size = Pt(9.5)
            kw_text.font.italic = True

        doc.add_paragraph() # Spacer

    # Helper for adding sections
    def add_section(heading_title: str, content: Any, is_list: bool = False):
        if not content:
            return
        h = doc.add_heading(level=1)
        hrun = h.add_run(heading_title)
        hrun.font.name = 'Times New Roman'
        hrun.font.size = Pt(14)
        hrun.font.bold = True
        hrun.font.color.rgb = RGBColor(0x1A, 0x2B, 0x4C)
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(6)

        if is_list and isinstance(content, list):
            for item in content:
                p = doc.add_paragraph(style='List Bullet')
                p.add_run(str(item))
        elif isinstance(content, list):
            for item in content:
                p = doc.add_paragraph()
                p.add_run(str(item))
        else:
            p = doc.add_paragraph()
            p.add_run(str(content))

    # Core Sections
    add_section("1. Introduction", state.get("introduction"))
    add_section("2. Literature Review", state.get("literature_review"))
    add_section("3. Research Gap", state.get("research_gap"))
    add_section("4. Research Objectives", state.get("research_objectives"), is_list=True)
    add_section("5. Research Questions", state.get("research_questions"), is_list=True)
    add_section("6. Conceptual Framework", state.get("conceptual_framework"))
    add_section("7. Hypotheses", state.get("hypotheses"), is_list=True)
    add_section("8. Research Design", state.get("research_design"))
    add_section("9. Data Collection Plan", state.get("data_collection_plan"))
    add_section("10. Data Analysis Plan", state.get("data_analysis_plan"))
    add_section("11. Results", state.get("results"))
    add_section("12. Discussion", state.get("discussion"))
    add_section("13. Practical & Theoretical Implications", state.get("implications"))
    add_section("14. Limitations", state.get("limitations"))
    add_section("15. Conclusion", state.get("conclusion"))
    add_section("16. Future Scope", state.get("future_scope"))
    add_section("17. References", state.get("references"), is_list=True)
    add_section("18. Appendices", state.get("appendices"), is_list=True)

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    logger.info(f"Generated DOCX report at: {out_path}")
    return str(out_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe research-bot/test_docx_generator.py`
Expected: PASS with `SUCCESS: DOCX generated at ...`

- [ ] **Step 5: Commit**

```bash
git add research-bot/backend/app/tools/docx_generator.py research-bot/test_docx_generator.py
git commit -m "feat(docx): implement docx_generator module for academic Word documents"
```

---

### Task 3: Add DOCX Export API Endpoint

**Files:**
- Modify: `research-bot/backend/app/api/research_mode.py:340-365`

**Interfaces:**
- Consumes: `POST /api/research-mode/export/docx/{thread_id}`
- Produces: `FileResponse` with `.docx` binary stream

- [ ] **Step 1: Add import and DOCX endpoint in research_mode.py**

In `research-bot/backend/app/api/research_mode.py`, import `generate_paper_docx`:
```python
from backend.app.tools.docx_generator import generate_paper_docx
```

Add endpoint definition:
```python
@router.post("/research-mode/export/docx/{thread_id}")
@router.post("/research/mode/export/docx/{thread_id}")
async def export_research_mode_docx(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    graph = get_research_mode_graph()
    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Research Mode thread not found")

    temp_dir = Path(__file__).resolve().parent.parent / "static" / "exports"
    temp_dir.mkdir(parents=True, exist_ok=True)
    docx_path = temp_dir / f"paper_{thread_id}.docx"

    try:
        generate_paper_docx(state.values, str(docx_path))
        return FileResponse(
            path=str(docx_path),
            filename=f"research_paper_{thread_id[:8]}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        logger.error(f"Failed to generate DOCX: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {str(e)}")
```

- [ ] **Step 2: Commit**

```bash
git add research-bot/backend/app/api/research_mode.py
git commit -m "feat(api): add POST /research-mode/export/docx/{thread_id} endpoint"
```

---

### Task 4: Frontend UI Export Dropdown

**Files:**
- Modify: `research-bot/frontend/index.html`
- Modify: `research-bot/frontend/style.css`
- Modify: `research-bot/frontend/app.js`

**Interfaces:**
- Consumes: User click on Export dropdown button
- Produces: Browser download of PDF or DOCX file

- [ ] **Step 1: Update index.html**

In `research-bot/frontend/index.html`, replace the existing export PDF button:
```html
<div class="export-dropdown" id="exportDropdownContainer" style="display: none;">
  <button id="exportMainBtn" class="btn btn-secondary dropdown-toggle" onclick="toggleExportMenu(event)">
    📥 Export Report <span class="caret">▼</span>
  </button>
  <div class="dropdown-menu" id="exportMenu">
    <button class="dropdown-item" onclick="exportReport('pdf')">📄 Export as PDF (.pdf)</button>
    <button class="dropdown-item" onclick="exportReport('docx')">📝 Export as Word (.docx)</button>
  </div>
</div>
```

- [ ] **Step 2: Update style.css**

Add dropdown styles to `research-bot/frontend/style.css`:
```css
/* Export Dropdown Styling */
.export-dropdown {
  position: relative;
  display: inline-block;
}

.dropdown-menu {
  display: none;
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 6px;
  background: rgba(30, 41, 59, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
  min-width: 200px;
  z-index: 1000;
  overflow: hidden;
}

.dropdown-menu.show {
  display: block;
}

.dropdown-item {
  width: 100%;
  padding: 10px 16px;
  background: transparent;
  border: none;
  color: #e2e8f0;
  text-align: left;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.dropdown-item:hover {
  background: rgba(59, 130, 246, 0.3);
  color: #ffffff;
}
```

- [ ] **Step 3: Update app.js**

In `research-bot/frontend/app.js`, add `toggleExportMenu` and update `exportReport(format)`:
```javascript
function toggleExportMenu(event) {
  if (event) event.stopPropagation();
  const menu = document.getElementById("exportMenu");
  if (menu) {
    menu.classList.toggle("show");
  }
}

// Close dropdown when clicking outside
document.addEventListener("click", () => {
  const menu = document.getElementById("exportMenu");
  if (menu && menu.classList.contains("show")) {
    menu.classList.remove("show");
  }
});

async function exportReport(format = 'pdf') {
  if (!currentThreadId) return;
  const menu = document.getElementById("exportMenu");
  if (menu) menu.classList.remove("show");

  const endpoint = format === 'docx' ? `/api/research-mode/export/docx/${currentThreadId}` : `/api/research-mode/export/${currentThreadId}`;
  const ext = format === 'docx' ? 'docx' : 'pdf';

  try {
    const res = await fetch(endpoint, { method: "POST" });
    if (!res.ok) throw new Error(`Export failed (${res.status})`);
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `research_paper_${currentThreadId.substring(0, 8)}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Failed to export ${ext.toUpperCase()}: ${err.message}`);
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add research-bot/frontend/index.html research-bot/frontend/style.css research-bot/frontend/app.js
git commit -m "feat(frontend): add Export dropdown supporting PDF and Word (.docx)"
```

---

### Task 5: End-to-End Integration Verification

**Files:**
- Create: `research-bot/test_docx_integration.py`

- [ ] **Step 1: Write integration test script**

Create `research-bot/test_docx_integration.py`:
```python
import asyncio
import httpx
import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.graph.research_mode_builder import get_research_mode_graph

async def test_integration():
    graph = get_research_mode_graph()
    thread_id = "test_docx_integration_thread"
    config = {"configurable": {"thread_id": thread_id}}

    # Seed state in checkpoint
    initial_input = {
        "problem_statement": "Multi-Agent UAV Coordination in Subterranean Rescue Operations",
        "research_objectives": ["Formulate robust routing under signal loss"],
        "research_questions": ["What is maximum tolerable comms latency?"],
        "keywords": ["UAV", "Multi-Agent", "Subterranean"]
    }

    # Run scope_definition node
    await graph.ainvoke(initial_input, config=config)
    state = await graph.aget_state(config)
    assert state.values.get("problem_statement") == initial_input["problem_statement"]

    # Test docx generator directly with state
    from backend.app.tools.docx_generator import generate_paper_docx
    out_file = root_dir / f"test_integration_{thread_id}.docx"
    res_path = generate_paper_docx(state.values, str(out_file))

    assert os.path.exists(res_path)
    assert os.path.getsize(res_path) > 1000
    print(f"Integration Test PASS: DOCX generated successfully at {res_path} ({os.path.getsize(res_path)} bytes)")

if __name__ == "__main__":
    asyncio.run(test_integration())
```

- [ ] **Step 2: Run integration test**

Run: `.venv\Scripts\python.exe research-bot/test_docx_integration.py`
Expected: PASS with `Integration Test PASS: DOCX generated successfully...`

- [ ] **Step 3: Commit integration test**

```bash
git add research-bot/test_docx_integration.py
git commit -m "test(docx): add end-to-end integration test for docx export"
```
