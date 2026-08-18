import os
import pypdf
import matplotlib
matplotlib.use("Agg")
from backend.app.tools.figures import render_prisma_diagram
from backend.app.tools.pdf_generator import generate_paper_pdf

def test_prisma_and_pdf_layout():
    # 1. Test PRISMA figure and log numbers agreement
    stats = {"retrieved": 185, "after_dedup": 142, "screened": 40, "included": 15}
    prisma_path = "./data/figures/test_prisma_b.png"
    out_path = render_prisma_diagram(stats, prisma_path)

    print(f"Generated PRISMA PNG at: {out_path}")
    print(f"Stats input to figure: retrieved={stats['retrieved']}, after_dedup={stats['after_dedup']}, screened={stats['screened']}, included={stats['included']}")
    print(f"PNG file exists: {os.path.exists(out_path)}, size: {os.path.getsize(out_path)} bytes")

    # 2. Test PDF layout metrics
    dummy_state = {
        "title": "Empirical Evaluation of Digital Health Interventions",
        "abstract": "Background: This study synthesizes evidence on digital health interventions...\nMethods: Systematic review of database indexes.",
        "keywords": ["digital health", "mhealth", "telemedicine"],
        "introduction": "Digital health technologies have expanded rapidly...",
        "literature_review": "Prior literature shows mixed results regarding efficacy...",
        "research_gap": "Few studies examine long-term adherence across demographics.",
        "conceptual_framework": "Framed around Technology Acceptance Model (TAM)...",
        "hypotheses": ["H1: Mobile reminders increase adherence by >=20%."],
        "research_design": "Observational cohort design...",
        "data_collection_plan": "Multi-center electronic health record sampling...",
        "data_analysis_plan": "Hierarchical linear regression modeling...",
        "results": "Results indicate strong support for H1 across all subgroups.",
        "discussion": "The findings align with modern behavioral health models.",
        "limitations": "Constrained by self-reported adherence metrics.",
        "conclusion": "Digital interventions demonstrate clear clinical utility.",
        "references": ["Smith, J. (2023). Mobile health systems. Journal of Digital Medicine, 10, 45-52."],
        "figures": {"prisma": out_path}
    }

    pdf_file = "./data/test_layout_c.pdf"
    os.makedirs("./data", exist_ok=True)
    generate_paper_pdf(dummy_state, pdf_file)

    print(f"\nGenerated test PDF at: {pdf_file}")
    reader = pypdf.PdfReader(pdf_file)
    p1 = reader.pages[0]

    width_pt = float(p1.mediabox.width)
    height_pt = float(p1.mediabox.height)
    print(f"Page 1 dimensions: {width_pt}pt x {height_pt}pt (Expected 612.0pt x 792.0pt - US Letter)")
    
    p1_text = p1.extract_text()
    has_title = "Empirical Evaluation of Digital Health Interventions" in p1_text
    has_abstract = "Abstract" in p1_text
    has_intro = "1. Introduction" in p1_text

    print(f"Page 1 contains title: {has_title}")
    print(f"Page 1 contains abstract: {has_abstract}")
    print(f"Page 1 contains Section 1 Introduction (proving no separate title page): {has_intro}")
    print(f"Total PDF pages: {len(reader.pages)}")

if __name__ == "__main__":
    test_prisma_and_pdf_layout()
