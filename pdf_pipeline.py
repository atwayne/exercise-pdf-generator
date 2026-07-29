"""Shared helpers for filling the LaTeX worksheet template and compiling PDFs."""

import subprocess
from datetime import datetime
from pathlib import Path
from string import Template

# Project root (directory containing this module)
ROOT = Path(__file__).resolve().parent
# Shared worksheet template with string.Template placeholders
TEMPLATE_FILE = ROOT / "templates" / "worksheet.tex"
# Intermediate LaTeX artifacts removed after a successful compile
LATEX_ARTIFACT_EXTS = (".tex", ".log", ".aux")


def format_enumerate_items(bodies):
    """Turn item body strings into indented \\item lines for the template."""
    return "\n".join(f"    \\item {body}" for body in bodies)


def build_answers_section(answer_bodies, *, column_count, itemsep):
    """
    Build a new-page answer key section for the worksheet template.
    answer_bodies are already-formatted item contents (same order as questions).
    """
    items = format_enumerate_items(answer_bodies)
    # Keep structure aligned with the questions page for easy cross-checking
    return (
        "\\newpage\n"
        "\\noindent\\textbf{Answer Key}\n"
        "\n"
        "\\vspace{0.5cm}\n"
        "\n"
        f"\\begin{{multicols}}{{{column_count}}}\n"
        f"\\begin{{enumerate}}[label=\\textbf{{\\arabic*.}}, itemsep={itemsep}]\n"
        f"{items}\n"
        "\\end{enumerate}\n"
        "\\end{multicols}\n"
    )


def render_worksheet(
    *,
    title,
    instructions,
    column_count,
    itemsep,
    items,
    answers_section="",
):
    """Fill templates/worksheet.tex and return the complete LaTeX source."""
    return Template(TEMPLATE_FILE.read_text(encoding="utf-8")).substitute(
        title=title,
        instructions=instructions,
        column_count=column_count,
        itemsep=itemsep,
        items=items,
        answers_section=answers_section,
    )


def write_and_compile(latex_content, output_prefix, *, working_directory=None):
    """
    Write a timestamped .tex file, run pdflatex, and clean artifacts on success.
    Returns the PDF path string when successful, otherwise None.
    """
    # Default to the project root so scripts and pipeline share one output folder
    cwd = Path(working_directory) if working_directory else ROOT
    output_base = f"{output_prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    tex_file = f"{output_base}.tex"
    pdf_file = f"{output_base}.pdf"
    tex_path = cwd / tex_file
    pdf_path = cwd / pdf_file

    # Persist the generated LaTeX source next to the eventual PDF
    tex_path.write_text(latex_content, encoding="utf-8")

    # Compile from the output directory so relative paths stay simple
    result = subprocess.run(
        ["pdflatex", tex_file],
        capture_output=True,
        text=True,
        cwd=cwd,
    )

    if pdf_path.exists():
        # Drop intermediate files; keep only the PDF
        for ext in LATEX_ARTIFACT_EXTS:
            artifact = cwd / f"{output_base}{ext}"
            if artifact.exists():
                artifact.unlink()
        print(f"\nPDF generated successfully: {pdf_file}")
        return pdf_file

    print("Failed to generate PDF. Output:\n", result.stdout, "\nErrors:\n", result.stderr)
    return None
