# AI English Helper (MVP)

## Problem Statement
HMW 让我在 Windows 任何应用里选中英文，就能快速获得高质量 AI 翻译与讲解，并为未来扩展（生词本、语法讲解、写作辅助）预留空间。

## Recommended Direction
方向 A：**全局快捷键 + 剪贴板取词 + LLM 翻译卡片**。

先做 1 条路径跑通：`热键 → 取词 → LLM → 浮窗显示`。架构上把 **取词源**、**AI 任务**、**展示层** 三者解耦，后续可插入 OCR、悬浮取词、生词本等模块。

技术栈：Python + PyQt6 + 云端 LLM API（OpenAI 兼容接口）。

## 架构骨架（可扩展性的关键）

```
┌─────────────────────────────────────────────┐
│  HotkeyManager  (注册/分发全局快捷键)         │
└──────────────┬──────────────────────────────┘
               │ trigger(action_id, context)
               ▼
┌─────────────────────────────────────────────┐
│  TextSource (抽象)                           │
│  ├─ ClipboardSource  ← MVP                   │
│  ├─ UIASource        ← v2                    │
│  └─ OCRSource        ← v3                    │
└──────────────┬──────────────────────────────┘
               │ text + metadata(app, lang, context)
               ▼
┌─────────────────────────────────────────────┐
│  CacheLayer  (查 SQLite，命中则跳过 AI)       │
└──────────────┬──────────────────────────────┘
     hit │     │ miss
         │     ▼
         │ ┌─────────────────────────────────┐
         │ │  TaskRouter → AIProvider        │
         │ │  ├─ OpenAICompatibleProvider    │
         │ │  └─ Tasks: translate/grammar… │
         │ └──────────────┬──────────────────┘
         │                │ streaming result
         │                ▼ (写回缓存)
         ▼
┌─────────────────────────────────────────────┐
│  ResultView (PyQt 浮窗，光标附近)            │
│  - 流式渲染 / 复制 / 重新生成 / 收藏到生词本   │
└─────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Storage (SQLite) — 缓存、历史、生词本、设置  │
└─────────────────────────────────────────────┘
```

### 缓存策略
- **命中流程**：取词 → 查 SQLite → 命中直接显示（零延迟、零成本）；未命中调 AI 并写回
- **Cache Key** = `sha256(text_normalized + task + target_lang + model)`
  - `text_normalized` = `text.strip().lower()` （全小写 + trim）
- **不带上下文**：prompt 中要求 AI 给出该词的多种常见含义，避免上下文敏感导致的错配
- **不过期**：浮窗提供「重新生成」按钮，强制绕过缓存
- **命中计数**：每次命中 `hit_count += 1`，未来可据此统计高频词、自动加生词本

### SQLite 表结构

```sql
CREATE TABLE queries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key    TEXT NOT NULL UNIQUE,   -- sha256(text+task+lang+model)
    text         TEXT NOT NULL,          -- 原始文本（保留大小写）
    task         TEXT NOT NULL,          -- 'translate' / 'grammar' / ...
    target_lang  TEXT NOT NULL,          -- 'zh' / 'ja' / ...
    model        TEXT NOT NULL,
    result       TEXT NOT NULL,
    is_starred   INTEGER DEFAULT 0,      -- 生词本预留（MVP 不用）
    hit_count    INTEGER DEFAULT 1,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_cache_key ON queries(cache_key);
CREATE INDEX idx_starred  ON queries(is_starred);
```

## Key Assumptions to Validate
- [ ] 快捷键取词体验够爽 → 用 3 天看是否还在用
- [ ] 剪贴板劫持-还原在 Chrome / VSCode / PDF windsurf /终端 稳定  → 做个 smoke test
- [ ] 云 API 延迟可接受 → 测 P50 / P95 响应时间
- [ ] 一个 prompt 能同时处理「单词 / 短语 / 句子」→ 小样本测试

## MVP Scope（目标 2 周内跑通）

**包含：**
1. 全局快捷键（默认 `Ctrl+D`，可配置）
2. 剪贴板取词 + 无损还原
3. 一个 AI Provider（OpenAI 兼容接口，DeepSeek / Kimi / OpenAI 都能接）
4. 一个 Task：翻译（单词给释义 + 音标 + 例句；句子给译文 + 要点） 这里先做给释意（需要有不同释义 + 音标）
5. 光标附近浮窗，支持流式输出，关闭方式：**X 按钮 + ESC 键 + 失焦**（鼠标悬停时暂停失焦关闭）
6. 设置页：API key、模型、快捷键、目标语言
7. SQLite 存查询缓存（命中则跳过 AI）+ 历史
8. 系统托盘常驻 + 开机自启

## Not Doing（和原因）
- **OCR 取词** — 延后，加了会让 MVP 周期翻倍
- **划词自动弹图标** — 兼容性坑太多，验证完快捷键方案再说
- **生词本 / 记忆曲线** — 学习闭环属于「确定用户后」的事
- **多 AI Provider 同时切换** — 先一个够用，接口预留好
- **多端同步** — 单机足够验证
- **浏览器扩展** — 不做，系统级方案统一体验

## 扩展点（为未来铺路，不实现）
- **新增取词源**：实现 `TextSource` 接口即可
- **新增 AI 任务**：新增 prompt 模板 + 快捷键绑定（e.g. `Ctrl+Shift+D` 解释语法）
- **新增 Provider**：实现 `AIProvider` 接口
- **Plugin 系统**：v2 再考虑，MVP 先用「接口 + 约定目录」方式

## Decisions（已敲定）
- **API**：任意 OpenAI 兼容接口（base_url + api_key 配置切换）
- **常驻**：系统托盘 + 开机自启
- **浮窗关闭**：右上角 X 按钮 + ESC 键 + 失焦关闭（鼠标悬停浮窗时暂停失焦关闭）
- **生词本字段**：MVP 阶段预留 `is_starred`，不实现功能
- **缓存**：先查 SQLite，命中即返回；未命中调 AI 并写回；浮窗有「重新生成」按钮强制绕过
- **大小写**：缓存 key 全小写 + trim；存库保留原文
- **上下文**：不带上下文给 AI，由 prompt 要求 AI 输出多种含义
