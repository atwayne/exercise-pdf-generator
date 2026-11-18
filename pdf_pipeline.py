"""Shared helpers for filling the LaTeX worksheet template and compiling PDFs."""

import subprocess
from datetime import datetime
from pathlib import Path
from string import Template

# Project root (directory containing this module)
ROOT = Path(__file__).resolve().parent
# Shared worksheet template with string.Template placeholders
TEMPLATE_FILE = ROOT / "templates" / "worksheet.tex"
# Multi-section worksheet template (grouped by exercise type)
GROUPED_TEMPLATE_FILE = ROOT / "templates" / "grouped_worksheet.tex"
# Intermediate LaTeX artifacts removed after a successful compile
LATEX_ARTIFACT_EXTS = (".tex", ".log", ".aux")


def format_enumerate_items(bodies, *, keep_together=True):
    """Turn item body strings into indented \\item lines for the template.

    When keep_together is True, wrap each item in a top-aligned minipage so a
    multi-line exercise cannot split across multicols columns. Answer keys skip
    the minipage so lookup values pack more tightly.
    """
    if keep_together:
        return "\n".join(
            rf"    \item \begin{{minipage}}[t]{{\linewidth}}{body}\end{{minipage}}"
            for body in bodies
        )
    return "\n".join(f"    \\item {body}" for body in bodies)


def wrap_in_columns(inner, column_count):
    """Wrap inner LaTeX in multicols only when more than one column is used.

    A 1-column multicols environment still balances like a multi-column
    list and can place the next item beside the current one. A plain
    enumerate keeps each exercise in a single column.
    """
    count = int(column_count)
    if count <= 1:
        return inner
    return (
        f"\\begin{{multicols}}{{{count}}}\n"
        f"{inner}"
        "\\end{multicols}\n"
    )


def format_inline_answers(bodies):
    """Join numbered answers on one line for a compact lookup key."""
    return r" \quad ".join(
        f"{i}. {body}"
        for i, body in enumerate(bodies, 1)
    )


def build_answers_section(answer_bodies, *, column_count, itemsep):
    """
    Build a new-page answer key section for the worksheet template.
    Standalone sheets use a small-type list; combined sheets use the
    grouped compact key instead.
    """
    items = format_enumerate_items(answer_bodies, keep_together=False)
    enum = (
        f"\\begin{{enumerate}}[label=\\arabic*., "
        f"itemsep={itemsep}, topsep=0pt, parsep=0pt, partopsep=0pt]\n"
        f"{items}\n"
        "\\end{enumerate}\n"
    )
    return (
        "\\newpage\n"
        "\\noindent\\textbf{Answer Key}\\\\[0.12cm]\n"
        "\\begingroup\n"
        "\\footnotesize\n"
        f"{wrap_in_columns(enum, column_count)}"
        "\\endgroup\n"
    )


def build_group_section(
    *,
    group_number,
    title,
    instructions,
    item_bodies,
    column_count,
    itemsep,
    include_vspace=True,
    compact=False,
):
    """
    Build one numbered group: header, instructions, and an enumerate that
    restarts at 1. item_bodies are already-formatted \\item contents.

    compact=True is for the answer key: tighter headers, gaps, and no minipage.
    """
    items = format_enumerate_items(item_bodies, keep_together=not compact)
    if compact:
        # Answer key: compact lookup, still a clear break between typed sections
        vspace = "\\vspace{0.12cm}\n" if include_vspace else ""
        keep = "\\Needspace{2.4cm}\n"
        title_skip = "0.03cm"
        after_header = "0.06cm"
    else:
        # Questions: title+instructions stay close; items keep write-in space
        vspace = "\\vspace{0.20cm}\n" if include_vspace else ""
        keep = "\\Needspace{4.2cm}\n"
        title_skip = "0.04cm"
        after_header = "0.10cm"
    # Question groups include instructions; answer groups omit them.
    # \\* forbids a page break after the header so it cannot sit alone.
    if instructions:
        header = (
            f"{keep}"
            f"\\noindent\\textbf{{{group_number}. {title}}}\\\\*[{title_skip}]\n"
            f"\\noindent {instructions}\\\\*[{after_header}]\n"
        )
    else:
        header = (
            f"{keep}"
            f"\\noindent\\textbf{{{group_number}. {title}}}\\\\*[{after_header}]\n"
        )
    # Rigid itemsep so 2-col balancing cannot stretch some gaps and not others.
    # Do not cancel the last itemsep here: enumitem `after` only hits the last
    # list item (usually the right column), which made some section gaps smaller.
    enum = (
        f"\\begin{{enumerate}}[label=\\textbf{{\\arabic*.}}, "
        f"itemsep={itemsep} plus 0pt minus 0pt, topsep=0pt, parsep=0pt, "
        f"partopsep=0pt]\n"
        f"{items}\n"
        "\\end{enumerate}\n"
    )
    return f"{header}{wrap_in_columns(enum, column_count)}{vspace}"


def build_grouped_answers_section(groups):
    """
    Build a one-page lookup key: small type, two columns, one block per group.

    Each entry in groups is a dict with keys:
    group_number, title, answer_bodies, column_count, itemsep.
    """
    if not groups:
        return ""

    items = []
    for group in groups:
        answers = format_inline_answers(group["answer_bodies"])
        items.append(
            f"\\item[{group['group_number']}. {group['title']}] {answers}\n"
        )

    # Full-width rows so group gaps can be larger without a blank lower half.
    # Same line size as the questions; only the page title is bold.
    return (
        "\\newpage\n"
        "\\noindent\\textbf{Answer Key}\\\\[0.28cm]\n"
        "\\begingroup\n"
        "\\raggedright\n"
        "\\begin{description}["
        "font=\\normalfont, style=sameline, "
        "leftmargin=5.1cm, labelwidth=4.9cm, labelsep=0.2cm, "
        "itemsep=0.72cm, parsep=0pt, topsep=0pt, partopsep=0pt]\n"
        f"{''.join(items)}"
        "\\end{description}\n"
        "\\endgroup\n"
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
    columns_begin = ""
    columns_end = ""
    if int(column_count) > 1:
        columns_begin = f"\\begin{{multicols}}{{{column_count}}}\n"
        columns_end = "\\end{multicols}\n"
    return Template(TEMPLATE_FILE.read_text(encoding="utf-8")).substitute(
        title=title,
        instructions=instructions,
        columns_begin=columns_begin,
        columns_end=columns_end,
        itemsep=itemsep,
        items=items,
        answers_section=answers_section,
    )


def render_grouped_worksheet(
    *,
    title,
    body,
    answers_section="",
    instructions="",
):
    """Fill templates/grouped_worksheet.tex and return the complete LaTeX source."""
    # instructions kept for API compatibility; combined sheets leave it unused
    _ = instructions
    return Template(GROUPED_TEMPLATE_FILE.read_text(encoding="utf-8")).substitute(
        title=title,
        body=body,
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
