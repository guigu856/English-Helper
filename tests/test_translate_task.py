"""Tests for src.ai.tasks.translate (prompt construction, no network)."""
from __future__ import annotations

from src.ai.tasks.translate import TranslateTask


def test_messages_structure():
    task = TranslateTask()
    msgs = task.build_messages("bank", target_lang="zh")
    assert len(msgs) == 2
    assert msgs[0].role == "system"
    assert msgs[1].role == "user"
    assert msgs[1].content == "bank"
    assert "简体中文" in msgs[0].content


def test_language_label_fallback():
    task = TranslateTask()
    msgs = task.build_messages("run", target_lang="xx")
    # Unknown lang falls back to the code itself (no crash).
    assert "xx" in msgs[0].content


def test_task_name():
    assert TranslateTask.name == "translate"
