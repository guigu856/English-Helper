"""Translate task: multi-meaning dictionary output with IPA."""
from __future__ import annotations

from src.ai.base import ChatMessage
from .base import Task


LANG_LABEL = {
    "zh": "简体中文",
    "ja": "日本語",
    "en": "English",
    "ko": "한국어",
}


SYSTEM_PROMPT = """你是一个精准、简洁的英语词典助手。根据输入类型严格输出以下 Markdown 结构，不要寒暄、不要解释：

【单词或短语】严格按这个格式（不要加任何其他内容）：
### /IPA/

**n.** 翻译1；翻译2；翻译3
- 简短释义1（{target_label}）
- 简短释义2（{target_label}）

**v.** 翻译1；翻译2
- 简短释义（{target_label}）

（第一行是 ### 开头的音标；然后每个词性一段，**词性缩写加粗**如 **n.** / **v.** / **adj.** / **adv.**；用 - 列出释义。覆盖 2-5 种常见含义，**不要只给一个意思**。）

【句子或长短语】严格按这个格式：
> 完整流畅的{target_label}译文

**要点**
- 关键短语或语法点 1
- 关键短语或语法点 2

规则：
- 严格遵循上述 Markdown 结构。
- 单词必须给音标（使用美式 IPA）。
- 所有释义/翻译使用{target_label}。
- 总字数不超过 200 字。
"""


class TranslateTask(Task):
    name = "translate"

    def build_messages(self, text: str, *, target_lang: str) -> list[ChatMessage]:
        label = LANG_LABEL.get(target_lang, target_lang)
        return [
            ChatMessage(role="system", content=SYSTEM_PROMPT.format(target_label=label)),
            ChatMessage(role="user", content=text),
        ]
