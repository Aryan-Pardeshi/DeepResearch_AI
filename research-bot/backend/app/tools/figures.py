import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
from typing import Dict, Any, List

def render_prisma_diagram(stats: Dict[str, int], output_path: str) -> str:
    """Renders a standard PRISMA flow diagram of study selection using matplotlib.

    Saves the figure at 200 DPI with tight bounding box and returns output_path.
    """
    retrieved = stats.get("retrieved", 0)
    after_dedup = stats.get("after_dedup", 0)
    screened = stats.get("screened", 0)
    included = stats.get("included", 0)

    dup_removed = max(0, retrieved - after_dedup)
    screen_excluded = max(0, screened - included)

    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    box_style = dict(boxstyle="round,pad=0.5", facecolor="#F7FAFC", edgecolor="#4A5568", linewidth=1.5)
    side_box_style = dict(boxstyle="round,pad=0.4", facecolor="#EDF2F7", edgecolor="#718096", linewidth=1.0)
    arrow_props = dict(arrowstyle="->", color="#4A5568", lw=1.5, mutation_scale=15)

    boxes = [
        (5.0, 8.8, f"Records identified through database searching\n(n = {retrieved})"),
        (5.0, 6.4, f"Records after duplicates removed\n(n = {after_dedup})"),
        (5.0, 4.0, f"Records screened for relevance\n(n = {screened})"),
        (5.0, 1.6, f"Studies included in synthesis\n(n = {included})"),
    ]

    # Draw main stacked boxes
    for x, y, text in boxes:
        ax.text(
            x, y, text,
            ha="center", va="center", fontsize=10.5, fontweight="bold", color="#1A202C",
            bbox=box_style
        )

    # Draw downward arrows between main boxes
    ax.annotate("", xy=(5.0, 7.15), xytext=(5.0, 8.05), arrowprops=arrow_props)
    ax.annotate("", xy=(5.0, 4.75), xytext=(5.0, 5.65), arrowprops=arrow_props)
    ax.annotate("", xy=(5.0, 2.35), xytext=(5.0, 3.25), arrowprops=arrow_props)

    # Draw side exclusion boxes and right-angled arrows
    # Side Box 1: Duplicates removed
    ax.annotate("", xy=(8.2, 7.6), xytext=(5.0, 7.6), arrowprops=arrow_props)
    ax.text(
        8.3, 7.6, f"Duplicates removed\n(n = {dup_removed})",
        ha="left", va="center", fontsize=9.5, color="#2D3748",
        bbox=side_box_style
    )

    # Side Box 2: Records excluded at screening
    ax.annotate("", xy=(8.2, 2.8), xytext=(5.0, 2.8), arrowprops=arrow_props)
    ax.text(
        8.3, 2.8, f"Records excluded at screening\n(n = {screen_excluded})",
        ha="left", va="center", fontsize=9.5, color="#2D3748",
        bbox=side_box_style
    )

    plt.title("PRISMA 2020 Flow Diagram of Study Selection", fontsize=12, fontweight="bold", pad=15, color="#1A202C")
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def render_evidence_table(papers: List[Dict[str, Any]], hypotheses: List[str], output_path: str) -> str:
    """Renders an evidence mapping table figure if hypothesis_support is present.

    Returns output_path if generated, or '' if no paper contains hypothesis_support.
    """
    has_support = any("hypothesis_support" in p for p in papers)
    if not has_support:
        return ""

    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Cap at top 15 papers by relevance score
    sorted_papers = sorted(papers, key=lambda p: (p.get("relevance_score", 0), p.get("citation_count", 0) or 0), reverse=True)[:15]

    h_labels = [f"H{i+1}" for i in range(len(hypotheses))] if hypotheses else ["H1"]
    col_labels = ["Paper Title (Top 15)"] + h_labels
    n_hyp_cols = len(h_labels)

    cell_text = []
    for p in sorted_papers:
        raw_title = p.get("title", "")
        title = (raw_title[:57] + "...") if len(raw_title) > 60 else raw_title
        sup_map = p.get("hypothesis_support") or {}
        row = [title]
        for idx, h in enumerate(hypotheses or ["H1"]):
            h_key = f"H{idx+1}"
            raw_val = str(sup_map.get(h_key) or sup_map.get(h) or "")
            # Support values are typically short ("Yes"/"Supports"), but nothing
            # bounded them, so a verbose model response here overflowed into the
            # neighboring column exactly like the untruncated title did.
            val = (raw_val[:22] + "...") if len(raw_val) > 25 else raw_val
            row.append(val)
        cell_text.append(row)

    # ax.table() splits width evenly across columns by default. The title column
    # needs far more room than the five short H1-H5 verdict columns, so without
    # explicit colWidths every column was squeezed to the same narrow slice and
    # the (already truncated) titles were cut again mid-word.
    title_width = 0.46
    hyp_width = (1.0 - title_width) / max(n_hyp_cols, 1)
    col_widths = [title_width] + [hyp_width] * n_hyp_cols

    fig, ax = plt.subplots(figsize=(11.5, max(2.5, 0.4 * len(cell_text) + 1.0)))
    ax.axis("off")

    table = ax.table(
        cellText=cell_text,
        colLabels=col_labels,
        colWidths=col_widths,
        loc="center",
        cellLoc="left"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.4)

    # cellLoc="left" above applies uniformly; re-center just the H1-H5 columns
    # (both header and body) so short verdicts don't look stranded against the
    # left edge of their narrow column.
    for (row_idx, col_idx), cell in table.get_celld().items():
        if col_idx > 0:
            cell.get_text().set_ha("center")

    plt.title("Evidence Mapping by Hypothesis", fontsize=11, fontweight="bold", pad=10)
    plt.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path
