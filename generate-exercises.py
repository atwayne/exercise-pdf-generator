"""Generate a combined printable PDF with multiple exercise types in groups."""

import argparse
import importlib.util
import sys
from pathlib import Path

from exercise_templates import CUSTOM_OUTPUT_PREFIX, CUSTOM_TITLE, TEMPLATES
from pdf_pipeline import (
    build_group_section,
    build_grouped_answers_section,
    render_grouped_worksheet,
    write_and_compile,
)

# Directory containing this script and the per-type generators
ROOT = Path(__file__).resolve().parent


def _load_module(script_name):
    """Load a hyphenated generator script as a module via importlib."""
    path = ROOT / script_name
    # Unique module name derived from the file stem
    module_name = path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rational_format_question(exercise):
    """Adapt rational (latex, value) tuples to the shared format_question API."""
    latex, _ = exercise
    return _MODULES["rational"].format_question(latex)


def _rational_format_answer(exercise):
    """Adapt rational (latex, value) tuples to the shared format_answer API."""
    _, value = exercise
    return _MODULES["rational"].format_answer(value)


# Lazy-loaded generator modules keyed by exercise type id
_MODULES = {}


def _ensure_modules():
    """Load all generator modules once and cache them."""
    if _MODULES:
        return
    _MODULES.update(
        {
            "average": _load_module("generate-exercises-average-numbers.py"),
            "missing-mean": _load_module("generate-exercises-missing-mean.py"),
            "rational": _load_module("generate-exercises-rational-operation.py"),
            "linear": _load_module("generate-exercises-linear-system.py"),
            "target-sum": _load_module("generate-exercises-target-sum.py"),
            "two-step": _load_module("generate-exercises-two-step-blank.py"),
            "three-step": _load_module("generate-exercises-three-step-result.py"),
            "digit-mul-steps": _load_module(
                "generate-exercises-digit-mul-steps.py"
            ),
            "smart-calc": _load_module("generate-exercises-smart-calc.py"),
            "true-false-fix": _load_module(
                "generate-exercises-true-false-fix.py"
            ),
            "function-machine": _load_module(
                "generate-exercises-function-machine.py"
            ),
            "comparison-blank": _load_module(
                "generate-exercises-comparison-blank.py"
            ),
            "balance": _load_module("generate-exercises-balance.py"),
            "odd-one-out": _load_module("generate-exercises-odd-one-out.py"),
            "sequence": _load_module("generate-exercises-sequence.py"),
            "two-truths": _load_module("generate-exercises-two-truths.py"),
        }
    )


def _exercise_types():
    """Return the registry of exercise types after modules are loaded."""
    _ensure_modules()
    return [
        {
            "id": "average",
            "module": _MODULES["average"],
            "format_question": _MODULES["average"].format_question,
            "format_answer": _MODULES["average"].format_answer,
        },
        {
            "id": "missing-mean",
            "module": _MODULES["missing-mean"],
            "format_question": _MODULES["missing-mean"].format_question,
            "format_answer": _MODULES["missing-mean"].format_answer,
        },
        {
            "id": "rational",
            "module": _MODULES["rational"],
            # Rational stores exercises as (latex, value) tuples
            "format_question": _rational_format_question,
            "format_answer": _rational_format_answer,
        },
        {
            "id": "linear",
            "module": _MODULES["linear"],
            "format_question": _MODULES["linear"].format_question,
            "format_answer": _MODULES["linear"].format_answer,
        },
        {
            "id": "target-sum",
            "module": _MODULES["target-sum"],
            "format_question": _MODULES["target-sum"].format_question,
            "format_answer": _MODULES["target-sum"].format_answer,
        },
        {
            "id": "two-step",
            "module": _MODULES["two-step"],
            "format_question": _MODULES["two-step"].format_question,
            "format_answer": _MODULES["two-step"].format_answer,
        },
        {
            "id": "three-step",
            "module": _MODULES["three-step"],
            "format_question": _MODULES["three-step"].format_question,
            "format_answer": _MODULES["three-step"].format_answer,
        },
        {
            "id": "digit-mul-steps",
            "module": _MODULES["digit-mul-steps"],
            "format_question": _MODULES["digit-mul-steps"].format_question,
            "format_answer": _MODULES["digit-mul-steps"].format_answer,
        },
        {
            "id": "smart-calc",
            "module": _MODULES["smart-calc"],
            "format_question": _MODULES["smart-calc"].format_question,
            "format_answer": _MODULES["smart-calc"].format_answer,
        },
        {
            "id": "true-false-fix",
            "module": _MODULES["true-false-fix"],
            "format_question": _MODULES["true-false-fix"].format_question,
            "format_answer": _MODULES["true-false-fix"].format_answer,
        },
        {
            "id": "function-machine",
            "module": _MODULES["function-machine"],
            "format_question": _MODULES["function-machine"].format_question,
            "format_answer": _MODULES["function-machine"].format_answer,
        },
        {
            "id": "comparison-blank",
            "module": _MODULES["comparison-blank"],
            "format_question": _MODULES["comparison-blank"].format_question,
            "format_answer": _MODULES["comparison-blank"].format_answer,
        },
        {
            "id": "balance",
            "module": _MODULES["balance"],
            "format_question": _MODULES["balance"].format_question,
            "format_answer": _MODULES["balance"].format_answer,
        },
        {
            "id": "odd-one-out",
            "module": _MODULES["odd-one-out"],
            "format_question": _MODULES["odd-one-out"].format_question,
            "format_answer": _MODULES["odd-one-out"].format_answer,
        },
        {
            "id": "sequence",
            "module": _MODULES["sequence"],
            "format_question": _MODULES["sequence"].format_question,
            "format_answer": _MODULES["sequence"].format_answer,
        },
        {
            "id": "two-truths",
            "module": _MODULES["two-truths"],
            "format_question": _MODULES["two-truths"].format_question,
            "format_answer": _MODULES["two-truths"].format_answer,
        },
    ]


def _format_counts_summary(counts):
    """Human-readable summary of non-zero counts for menus and previews."""
    parts = [f"{type_id} {n}" for type_id, n in counts.items() if n > 0]
    return ", ".join(parts) if parts else "(empty)"


def list_templates():
    """Print predefined templates and exit-friendly text."""
    print("Available templates:\n")
    for template_id, template in TEMPLATES.items():
        summary = _format_counts_summary(template["counts"])
        print(f"  {template_id:12}  {template['description']}")
        print(f"               {summary}\n")


def _selection_from_template(template_id):
    """Build a selection dict from a predefined template id."""
    template = TEMPLATES[template_id]
    return {
        "template_id": template_id,
        "title": template["title"],
        "output_prefix": template["output_prefix"],
        "counts": dict(template["counts"]),
    }


def _selection_from_custom(counts):
    """Build a selection dict for a custom count mix."""
    return {
        "template_id": None,
        "title": CUSTOM_TITLE,
        "output_prefix": CUSTOM_OUTPUT_PREFIX,
        "counts": counts,
    }


def prompt_template_choice():
    """Interactive menu: pick a predefined template id, or None for Custom."""
    template_ids = list(TEMPLATES.keys())
    print("Select a worksheet template:\n")
    for i, template_id in enumerate(template_ids, 1):
        template = TEMPLATES[template_id]
        summary = _format_counts_summary(template["counts"])
        print(f"  {i}. {template_id} — {template['description']}")
        print(f"     ({summary})")
    custom_index = len(template_ids) + 1
    print(f"  {custom_index}. custom — choose counts for each exercise type\n")

    while True:
        raw = input(f"Choice [1-{custom_index}]: ").strip().lower()
        if not raw:
            continue
        # Accept either the menu number or the template id / "custom"
        if raw == "custom" or raw == str(custom_index):
            return None
        if raw in TEMPLATES:
            return raw
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(template_ids):
                return template_ids[index - 1]
        print(f"Invalid choice. Enter 1-{custom_index}, a template id, or custom.")


def prompt_custom_counts():
    """Ask how many questions for each exercise type (0 or empty skips)."""
    types = _exercise_types()
    print("\nCustom selection — enter how many questions for each type.")
    print("Press Enter or 0 to skip a type.\n")
    counts = {}
    for entry in types:
        mod = entry["module"]
        label = mod.TITLE
        type_id = entry["id"]
        while True:
            raw = input(f"  {label} ({type_id}) [0]: ").strip()
            if raw == "":
                counts[type_id] = 0
                break
            if raw.isdigit() and int(raw) >= 0:
                counts[type_id] = int(raw)
                break
            print("    Please enter a non-negative integer.")
    return counts


def resolve_selection(args):
    """Resolve title, output prefix, and counts from flags or prompts."""
    if args.template:
        if args.template not in TEMPLATES:
            valid = ", ".join(TEMPLATES)
            print(f"Unknown template '{args.template}'. Valid ids: {valid}", file=sys.stderr)
            sys.exit(1)
        return _selection_from_template(args.template)

    # Interactive: template menu, then optional custom prompts
    template_id = prompt_template_choice()
    if template_id is not None:
        return _selection_from_template(template_id)

    counts = prompt_custom_counts()
    # Reject an empty selection and offer custom again
    while sum(counts.values()) == 0:
        print("\nNo exercises selected. Please choose at least one question.")
        counts = prompt_custom_counts()
    return _selection_from_custom(counts)


def generate_groups(counts):
    """
    Generate exercise groups for every type with a positive count.
    Returns a list of dicts ready for LaTeX rendering and terminal preview.
    """
    groups = []
    group_number = 1
    # Preserve registry order so sections appear consistently
    for entry in _exercise_types():
        type_id = entry["id"]
        count = counts.get(type_id, 0)
        if count <= 0:
            continue
        mod = entry["module"]
        exercises = mod.generate_exercises(count)
        groups.append(
            {
                "group_number": group_number,
                "type_id": type_id,
                "title": mod.TITLE,
                "instructions": mod.INSTRUCTIONS,
                "column_count": mod.COLUMN_COUNT,
                "itemsep": mod.ITEMSEP,
                "exercises": exercises,
                "format_question": entry["format_question"],
                "format_answer": entry["format_answer"],
            }
        )
        group_number += 1
    return groups


def preview_groups(groups):
    """Print a terminal preview of each numbered group."""
    for group in groups:
        print(f"\n{group['group_number']}. {group['title']} ({len(group['exercises'])})")
        mod = _MODULES[group["type_id"]]
        for i, exercise in enumerate(group["exercises"], 1):
            # Prefer a dedicated preview helper when the module provides one
            if hasattr(mod, "preview_line"):
                line = mod.preview_line(exercise)
            elif group["type_id"] == "rational":
                latex, value = exercise
                line = f"{latex}  =  {value}"
            else:
                line = str(exercise)
            print(f"   {i}. {line}")


def build_latex(groups, *, title):
    """Render the grouped worksheet LaTeX including a full answer key."""
    body_parts = []
    answer_groups = []
    for i, group in enumerate(groups):
        question_bodies = [
            group["format_question"](ex) for ex in group["exercises"]
        ]
        answer_bodies = [group["format_answer"](ex) for ex in group["exercises"]]
        include_vspace = i < len(groups) - 1
        body_parts.append(
            build_group_section(
                group_number=group["group_number"],
                title=group["title"],
                instructions=group["instructions"],
                item_bodies=question_bodies,
                column_count=group["column_count"],
                itemsep=group["itemsep"],
                include_vspace=include_vspace,
            )
        )
        answer_groups.append(
            {
                "group_number": group["group_number"],
                "title": group["title"],
                "answer_bodies": answer_bodies,
                "column_count": group["column_count"],
                "itemsep": group["itemsep"],
            }
        )

    # Top-level description is intentionally empty for combined sheets
    return render_grouped_worksheet(
        title=title,
        body="".join(body_parts),
        answers_section=build_grouped_answers_section(answer_groups),
    )


def parse_args(argv=None):
    """Parse CLI flags for template selection and listing."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate a combined PDF worksheet from multiple exercise types. "
            "Without flags, prompts for a predefined template or custom counts."
        )
    )
    parser.add_argument(
        "-t",
        "--template",
        metavar="NAME",
        help="pre-select a predefined template by id (skips the menu)",
    )
    parser.add_argument(
        "--list-templates",
        action="store_true",
        help="print available templates and exit",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Resolve selection, generate grouped exercises, and compile the PDF."""
    args = parse_args(argv)

    if args.list_templates:
        list_templates()
        return

    # Ensure generators are importable before prompting
    _ensure_modules()
    selection = resolve_selection(args)
    counts = selection["counts"]

    if sum(counts.values()) == 0:
        print("No exercises selected.", file=sys.stderr)
        sys.exit(1)

    print(f"\nGenerating [{selection['title']}]: {_format_counts_summary(counts)}")
    groups = generate_groups(counts)
    preview_groups(groups)

    latex_content = build_latex(groups, title=selection["title"])
    write_and_compile(latex_content, selection["output_prefix"])


if __name__ == "__main__":
    main()
