import os
import logging
from pathlib import Path
from fpdf import FPDF
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Unicode-capable TTFs to try, in order: (regular, bold). Academic text is full of
# subscripts, Greek letters, and en-dashes that the built-in latin-1 fonts cannot encode.
UNICODE_FONT_CANDIDATES = [
    (os.getenv("PDF_FONT_PATH"), os.getenv("PDF_FONT_PATH_BOLD")),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("/Library/Fonts/Arial Unicode.ttf", None),
]

# Fallback transliterations, used only when no Unicode TTF is available on the host
LATIN1_SUBSTITUTIONS = {
    **{chr(0x2080 + d): str(d) for d in range(10)},          # subscript digits
    "\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3",
    **{chr(0x2074 + d): str(d + 4) for d in range(6)},        # superscripts 4-9
    "\u2212": "-", "\u2013": "-", "\u2014": "-", "\u2010": "-", "\u2011": "-",
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2026": "...", "\u2192": "->", "\u2190": "<-", "\u21d2": "=>",
    "\u2248": "~", "\u2264": "<=", "\u2265": ">=", "\u2260": "!=",
    "\u00d7": "x", "\u2022": "-", "\u2032": "'", "\u2033": '"',
    "\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma", "\u03b4": "delta",
    "\u03b5": "epsilon", "\u03b8": "theta", "\u03bb": "lambda", "\u03bc": "mu",
    "\u03c0": "pi", "\u03c1": "rho", "\u03c3": "sigma", "\u03c4": "tau",
    "\u03c6": "phi", "\u03c7": "chi", "\u03c9": "omega", "\u03a9": "Ohm",
    "\u0394": "Delta", "\u03a3": "Sigma", "\u212b": "Angstrom",
}


def _register_unicode_font(pdf: FPDF) -> Optional[Tuple[str, str]]:
    """Registers the first available Unicode TTF. Returns (family, bold_style) or None."""
    for regular, bold in UNICODE_FONT_CANDIDATES:
        if not regular or not Path(regular).is_file():
            continue
        family = "PaperSans"
        try:
            pdf.add_font(family, "", regular)
            if bold and Path(bold).is_file():
                pdf.add_font(family, "B", bold)
                return family, "B"
            # No bold face available: headings stay in the regular weight
            return family, ""
        except Exception as e:
            logger.warning(f"Could not register PDF font {regular}: {e}")
    return None


class AcademicPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, "Autonomous Academic Research Report", border=0, align="R")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", border=0, align="C")

def generate_paper_pdf(state: Dict[str, Any], output_path: str) -> str:
    """Generates a PDF document for a completed ResearchMode paper state using FPDF2."""
    pdf = AcademicPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)

    unicode_font = _register_unicode_font(pdf)
    body_family, bold_style = unicode_font if unicode_font else ("Helvetica", "B")
    bullet = "•" if unicode_font else "-"

    pdf.add_page()

    # Sanitizes text for the active font: Unicode passes through, Helvetica gets
    # scientific characters transliterated before the latin-1 encode.
    def clean(text: Any) -> str:
        if not text:
            return ""
        if isinstance(text, list):
            text = "\n".join(f"{bullet} {item}" for item in text)
        text = str(text)
        if unicode_font:
            return text
        for char, replacement in LATIN1_SUBSTITUTIONS.items():
            if char in text:
                text = text.replace(char, replacement)
        return text.encode("latin-1", "replace").decode("latin-1")

    # Title
    title = state.get("title") or "Academic Research Paper"
    pdf.set_font(body_family, bold_style, 18)
    pdf.set_text_color(20, 30, 55)
    pdf.multi_cell(0, 10, clean(title), align="C")
    pdf.ln(8)

    # Helper for sections
    def add_section(heading: str, body: Any):
        if not body:
            return
        pdf.set_font(body_family, bold_style, 13)
        pdf.set_text_color(40, 60, 110)
        pdf.cell(0, 8, clean(heading), ln=True)
        pdf.set_font(body_family, "", 10)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 6, clean(body))
        pdf.ln(4)

    # Abstract Box
    abstract = state.get("abstract")
    if abstract:
        pdf.set_fill_color(245, 247, 250)
        pdf.set_draw_color(200, 210, 225)
        pdf.rect(pdf.get_x(), pdf.get_y(), 180, 0, style="") # container line
        add_section("Abstract", abstract)

    # Main Sections (final paper order)
    add_section("1. Introduction", state.get("introduction"))
    add_section("2. Literature Review", state.get("literature_review"))
    add_section("3. Research Gap", state.get("research_gap"))
    add_section("4. Research Objectives", state.get("research_objectives"))
    add_section("5. Research Questions", state.get("research_questions"))
    add_section("6. Conceptual Framework", state.get("conceptual_framework"))
    add_section("7. Hypotheses", state.get("hypotheses"))

    methodology = ""
    if state.get("research_design"):
        methodology += f"Research Design:\n{state.get('research_design')}\n\n"
    if state.get("data_collection_plan"):
        methodology += f"Data Collection:\n{state.get('data_collection_plan')}\n\n"
    if state.get("data_analysis_plan"):
        methodology += f"Data Analysis:\n{state.get('data_analysis_plan')}"
    add_section("8. Methodology", methodology)

    add_section("9. Results", state.get("results"))

    discussion = ""
    if state.get("discussion"):
        discussion += f"{state.get('discussion')}\n\n"
    if state.get("implications"):
        discussion += f"Implications:\n{state.get('implications')}"
    add_section("10. Discussion", discussion)

    add_section("11. Limitations", state.get("limitations"))
    add_section("12. Conclusion", state.get("conclusion"))
    add_section("13. Future Scope", state.get("future_scope"))

    refs = state.get("references")
    if refs:
        pdf.add_page()
        add_section("References", refs)

    appendices = state.get("appendices")
    if appendices:
        pdf.add_page()
        add_section("Appendices", appendices)

    pdf.output(output_path)
    return output_path
