"""Manual smoke test for Task 5.

Usage:
    python scripts/try_translate.py bank
    python scripts/try_translate.py "The meeting has been postponed"

Requires a working config.yaml with AI credentials.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a script without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai.openai_compat import AIProviderError, OpenAICompatibleProvider
from src.ai.tasks.translate import TranslateTask
from src.config import Config, ConfigError


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/try_translate.py <text>")
        return 2

    text = " ".join(sys.argv[1:])
    try:
        cfg = Config.load()
    except ConfigError as e:
        print(f"[config error] {e}")
        return 1

    provider = OpenAICompatibleProvider(base_url=cfg.ai.base_url, api_key=cfg.ai.api_key)
    task = TranslateTask()
    messages = task.build_messages(text, target_lang=cfg.language.target)

    print(f"--- Translating: {text!r} (model={cfg.ai.model}) ---")
    try:
        for chunk in provider.stream(messages, model=cfg.ai.model):
            print(chunk, end="", flush=True)
        print()
    except AIProviderError as e:
        print(f"\n[AI error] {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
