# Technical Specification: DOCX Export Implementation

## Overview
This specification details the design for adding **Word (`.docx`)** export capabilities to the AI Research Assistant application, complementing the existing PDF export.

## Requirements
1. **Word Export (`.docx`)**:
   - Native `.docx` document generation using `python-docx`.
   - Full academic layout with 1-inch margins, Times New Roman / Calibri fonts, styled headings (Title, H1, H2), callout highlight boxes for research gaps / objectives / hypotheses, and formatted reference lists.
   - Covers all 21 research paper sections.
2. **API Endpoints**:
   - `POST /api/research-mode/export/docx/{thread_id}` (also alias `/api/research/mode/export/docx/{thread_id}`)
   - `POST /api/research-mode/export/{thread_id}` (Existing PDF export endpoint preserved)
3. **Frontend UI**:
   - Updates the export button into an interactive **Export Dropdown Menu**:
     - 📄 **Export PDF** (`.pdf`)
     - 📝 **Export Word Document** (`.docx`)

## Architecture & Implementation Plan

### 1. Dependencies (`requirements.txt`)
- Add `python-docx>=1.1.0`

### 2. DOCX Generator (`research-bot/backend/app/tools/docx_generator.py`)
- Defines `generate_paper_docx(state: Dict[str, Any], output_path: str) -> str`:
  - Creates `Document()` from `docx`.
  - Configures standard styles, margins, headings, paragraph spacing, callout tables.
  - Iterates through `state` sections (Title, Abstract, Introduction, Literature Review, Gap, Objectives, RQs, Conceptual Framework, Hypotheses, Methodology, Results, Discussion, Implications, Limitations, Conclusion, Future Scope, References, Appendices).

### 3. Backend Router (`research-bot/backend/app/api/research_mode.py`)
- Imports `generate_paper_docx`.
- Adds `POST` endpoint for `/research-mode/export/docx/{thread_id}` returning `FileResponse`.

### 4. Frontend UI (`research-bot/frontend/`)
- `index.html`: Replaces single PDF export button with `.export-dropdown` button group.
- `style.css`: Styles `.export-dropdown` and `.dropdown-menu` with hover/click toggle, dark mode glassmorphism styling, and smooth positioning.
- `app.js`: Adds `exportReport(format)` method supporting `'pdf'` and `'docx'`.

## Verification & Testing Strategy
- Unit test for `docx_generator.py` (verifying `.docx` file generation and non-zero byte size).
- Integration test for API endpoint returning 200 OK with content type `application/vnd.openxmlformats-officedocument.wordprocessingml.document`.
