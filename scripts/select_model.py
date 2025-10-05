#!/usr/bin/env python3
"""Interactive model selector for Makefile targets."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI_MODELS_PATH = PROJECT_ROOT / "gitlab_mr_review" / "ai_models.py"


def _load_ai_models_module():
    spec = importlib.util.spec_from_file_location(
        "gitlab_mr_review.ai_models", AI_MODELS_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError("Unable to locate ai_models module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


ai_models = _load_ai_models_module()
get_default_model = ai_models.get_default_model
list_model_choices = ai_models.list_model_choices
normalize_provider = ai_models.normalize_provider


def _prompt(message: str) -> str:
    try:
        sys.stderr.write(message)
        sys.stderr.flush()
        return input()
    except EOFError:
        return ""
    except KeyboardInterrupt:
        print("\nSelection cancelled.", file=sys.stderr)
        sys.exit(130)


def _print_menu(provider: str, choices: List[dict]) -> None:
    for idx, model in enumerate(choices, start=1):
        default_flag = " (default)" if model.get("is_default") == "true" else ""
        display = model.get("display_name", model.get("model", "unknown"))
        identifier = model.get("model", "")
        print(f"  {idx}) {display} [{identifier}]{default_flag}", file=sys.stderr)
    print(file=sys.stderr)


def select_model(provider: str) -> str:
    provider_key = normalize_provider(provider)
    try:
        choices = list_model_choices(provider_key)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return ""

    if not choices:
        default = get_default_model(provider_key)
        print(
            "No models found in registry; using provider default.",
            file=sys.stderr,
        )
        return f"{default.name}|{default.display_name}"

    _print_menu(provider_key, choices)

    selection = _prompt(
        f"Enter choice [1-{len(choices)}] (press Enter for default): "
    ).strip()

    chosen = None
    if selection.isdigit():
        index = int(selection)
        if 1 <= index <= len(choices):
            chosen = choices[index - 1]

    if chosen is None:
        for model in choices:
            if model.get("is_default") == "true":
                chosen = model
                break

    if chosen is None:
        chosen = choices[0]

    model_name = chosen.get("model", "")
    display_name = chosen.get("display_name", model_name)
    return f"{model_name}|{display_name}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Model selector helper")
    parser.add_argument("provider", help="Provider key (gemini, claude, openai)")
    args = parser.parse_args()

    result = select_model(args.provider)
    if not result:
        return 1

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
