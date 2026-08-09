# Technical Specification: BibTeX & DOCX Export Implementation

## Overview
This specification details the design for adding **BibTeX (`.bib`)** and **Word (`.docx`)** export capabilities to the AI Research Assistant application, complementing the existing PDF export.

## Requirements
1. **BibTeX Export (`.bib`)**:
   - Includes all screened papers from `state["papers"]`.
   - Tags each entry with `keywords = {cited}` or `keywords = {screened_corpus}` and explanatory `note` fields based on whether the paper was cited in the literature review / report.
   - Generates clean, standard `@article` / `@inproceedings` entries with fields: `author`, `title`, `year`, `journal`/`publisher`, `doi`, `url`, `keywords`, `note`.
2. **Word Export (`.docx`)**:
   - Native `.docx` document generation using `python-docx`.
   - Full academic layout with 1-inch margins, Times New Roman / Calibri fonts, styled headings (Title, H1, H2), callout highlight boxes for research gaps / objectives / hypotheses, and formatted reference lists.
   - Covers all 21 research paper sections.
3. **API Endpoints**:
   - `POST /api/research-mode/export/docx/{thread_id}` (also alias `/api/research/mode/export/docx/{thread_id}`)
   - `POST /api/research-mode/export/bibtex/{thread_id}` (also alias `/api/research/mode/export/bibtex/{thread_id}`)
   - `POST /api/research-mode/export/{thread_id}` (Existing PDF export endpoint preserved)
4. **Frontend UI**:
   - Replaces the single "Export PDF" button with an interactive **Export Dropdown Menu**:
     - 📄 **Export PDF** (`.pdf`)
     - 📝 **Export Word Document** (`.docx`)
     - 📚 **Export BibTeX Citations** (`.bib`)

## Architecture & Implementation Plan

### 1. Dependencies (`requirements.txt`)
- Add `python-docx>=1.1.0`

### 2. BibTeX Generator (`research-bot/backend/app/tools/bibtex_generator.py`)
- Defines `generate_bibtex(state: Dict[str, Any], output_path: str) -> str`:
  - Formats unique citation keys (`AuthorYear` or `AuthorYearTitle`).
  - Scans `state["literature_review"]` to identify cited vs extra screened papers.
  - Emits valid BibTeX syntax with proper escaping of LaTeX special characters.

### 3. DOCX Generator (`research-bot/backend/app/tools/docx_generator.py`)
- Defines `generate_paper_docx(state: Dict[str, Any], output_path: str) -> str`:
  - Creates `Document()` from `docx`.
  - Configures standard styles, margins, headings, paragraph spacing, callout tables.
  - Iterates through `state` sections (Title, Abstract, Introduction, Literature Review, Gap, Objectives, RQs, Conceptual Framework, Hypotheses, Methodology, Results, Discussion, Implications, Limitations, Conclusion, Future Scope, References, Appendices).

### 4. Backend Router (`research-bot/backend/app/api/research_mode.py`)
- Imports `generate_paper_docx` and `generate_bibtex`.
- Adds `POST` endpoints for `/research-mode/export/docx/{thread_id}` and `/research-mode/export/bibtex/{thread_id}` returning `FileResponse`.

### 5. Frontend UI (`research-bot/frontend/`)
- `index.html`: Replaces single PDF export button with `.export-dropdown` button group.
- `style.css`: Styles `.export-dropdown` and `.dropdown-menu` with hover/click toggle, dark mode glassmorphism styling, and smooth positioning.
- `app.js`: Adds `exportReport(format)` method supporting `'pdf'`, `'docx'`, and `'bibtex'`.

## Verification & Testing Strategy
- Unit test for `bibtex_generator.py` (verifying entry syntax, cited vs uncited tagging).
- Unit test for `docx_generator.py` (verifying `.docx` file generation and non-zero byte size).
- Integration test for API endpoints returning 200 OK with proper content types (`application/vnd.openxmlformats-officedocument.wordprocessingml.document` and `text/x-bibtex`).
