import os
from pathlib import Path
from fpdf import FPDF
from typing import Dict, Any

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
    pdf.add_page()
    
    # Title
    title = state.get("title") or "Academic Research Paper"
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 30, 55)
    pdf.multi_cell(0, 10, title, align="C")
    pdf.ln(8)

    # Helper function to sanitize text for Latin-1 FPDF
    def clean(text: Any) -> str:
        if not text:
            return ""
        if isinstance(text, list):
            text = "\n".join(f"• {item}" for item in text)
        text = str(text)
        # Encode to latin-1 with replacement to avoid character errors
        return text.encode("latin-1", "replace").decode("latin-1")

    # Helper for sections
    def add_section(heading: str, body: Any):
        if not body:
            return
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(40, 60, 110)
        pdf.cell(0, 8, clean(heading), ln=True)
        pdf.set_font("Helvetica", "", 10)
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

    # Main Sections
    add_section("1. Introduction", state.get("introduction"))
    add_section("2. Literature Review", state.get("literature_review"))
    
    gap_fw = ""
    if state.get("research_gap"):
        gap_fw += f"Research Gap:\n{state.get('research_gap')}\n\n"
    if state.get("conceptual_framework"):
        gap_fw += f"Conceptual Framework:\n{state.get('conceptual_framework')}"
    add_section("3. Research Gap & Conceptual Framework", gap_fw)

    add_section("4. Hypotheses", state.get("hypotheses"))

    methodology = ""
    if state.get("research_design"):
        methodology += f"Research Design: {state.get('research_design')}\n\n"
    if state.get("data_collection_plan"):
        methodology += f"Data Collection: {state.get('data_collection_plan')}\n\n"
    if state.get("data_analysis_plan"):
        methodology += f"Data Analysis: {state.get('data_analysis_plan')}"
    add_section("5. Methodology", methodology)

    add_section("6. Results", state.get("results"))
    add_section("7. Discussion", state.get("discussion"))
    add_section("8. Implications", state.get("implications"))
    add_section("9. Limitations", state.get("limitations"))

    conc_fs = ""
    if state.get("conclusion"):
        conc_fs += f"{state.get('conclusion')}\n\n"
    if state.get("future_scope"):
        conc_fs += f"Future Directions:\n{clean(state.get('future_scope'))}"
    add_section("10. Conclusion & Future Scope", conc_fs)

    refs = state.get("references")
    if refs:
        pdf.add_page()
        add_section("References", refs)

    pdf.output(output_path)
    return output_path
