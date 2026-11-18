"""
Worksheet templates for generate-exercises.py.

Edit this file to add, remove, or change combined worksheets.
Each template key is the CLI id used with --template / -t.

Fields:
  title          PDF document title
  output_prefix  Filename prefix (timestamp is appended on generate)
  description    Short blurb shown in the interactive menu / --list-templates
  counts         Map of exercise type id -> number of questions

Valid exercise type ids (omit or set 0 to skip):
  average, missing-mean, rational, linear, target-sum, two-step, three-step,
  digit-mul-steps, smart-calc, true-false-fix, function-machine,
  comparison-blank, balance, odd-one-out, sequence, two-truths
"""

# Used when the user picks Custom instead of a named template
CUSTOM_TITLE = "Custom"
CUSTOM_OUTPUT_PREFIX = "custom"

# Predefined templates — add new entries here
TEMPLATES = {
    "means": {
        "title": "Means",
        "output_prefix": "means",
        "description": "Average + missing mean",
        "counts": {
            "average": 10,
            "missing-mean": 5,
        },
    },
    "arithmetic": {
        "title": "Arithmetic",
        "output_prefix": "arithmetic",
        "description": "Two-step blank + three-step result",
        "counts": {
            "two-step": 10,
            "three-step": 10,
        },
    },
    "arithmetic-2": {
        "title": "Arithmetic",
        "output_prefix": "arithmetic2",
        "description": "Two-step blank + three-step result",
        "counts": {
            "two-step": 8,
            "three-step": 8,
            "missing-mean": 4,
        },
    },
    "anders": {
            "title": "Anders",
            "output_prefix": "anders",
            "description": "Anders's daily exercises",
            "counts": {
                "two-step": 8,
                "smart-calc": 8,
                "missing-mean": 4,
            },
    },
    "anders-puzzles": {
            "title": "Anders",
            "output_prefix": "anders_puzzles",
            "description": "Anders's puzzle exercises",
            "counts": {
                "true-false-fix": 3,
                "function-machine": 3,
                "comparison-blank": 3,
                "balance": 3,
                "odd-one-out": 2,
                "sequence": 3,
                "two-truths": 2,
            },
    },
    "fay": {
            "title": "Fay",
            "output_prefix": "fay",
            "description": "Fay's daily exercises",
            "counts": {
                "two-step": 8,
                "smart-calc": 6,
                "missing-mean": 6,
            },
    },
    "arithmetic-3": {
        "title": "Arithmetic",
        "output_prefix": "arithmetic3",
        "description": "Two-step blank + three-step result + digit-mul-steps",
        "counts": {
            "three-step": 6,
            "missing-mean": 4,
            "digit-mul-steps": 4,
        },
    },
    "rationals": {
        "title": "Rationals",
        "output_prefix": "rationals",
        "description": "Rational ops + linear systems",
        "counts": {
            "rational": 12,
            "linear": 6,
        },
    },
    "targets": {
        "title": "Targets",
        "output_prefix": "targets",
        "description": "Target sum only",
        "counts": {
            "target-sum": 18,
        },
    },
    "digit-mul": {
        "title": "Digit Multiplication Steps",
        "output_prefix": "digit_mul",
        "description": "Two-digit x two-digit stepped blanks",
        "counts": {
            "digit-mul-steps": 10,
        },
    },
    "smart-calc": {
        "title": "Smart Calculation",
        "output_prefix": "smart_calc",
        "description": "Regroup all-plus or all-minus chains",
        "counts": {
            "smart-calc": 18,
        },
    },
    "mixed": {
        "title": "Mixed",
        "output_prefix": "mixed",
        "description": "Light mix of all types",
        "counts": {
            "average": 4,
            "missing-mean": 4,
            "rational": 4,
            "linear": 3,
            "target-sum": 4,
            "two-step": 4,
            "three-step": 4,
            "digit-mul-steps": 3,
            "smart-calc": 4,
        },
    },
}
