# Implementation Plan: AI English Helper

## Overview

基于 `docs/ideas/ai-english-helper.md` 的 MVP 规范，按「取词源 → 缓存 → AI → 浮窗 → 托盘」五层架构，以**垂直切片**方式分 3 个 Phase、8 个 Task 落地。每个 Task 留在可运行状态，每个 Phase 末设 Checkpoint。

## Architecture Decisions

- **分层抽象**：`TextSource` / `AIProvider` / `Task` 三个接口先定好，MVP 各实现一个
- **缓存放 Pipeline 里**：`CacheLayer` 不是独立模块，而是 `Storage` 上的查询/写入方法，由 `Pipeline` 调度
- **先命令行跑通，再加 UI**：Phase 2 结束就能在终端用，把 UI（PyQt 浮窗）隔离在 Phase 3，降低调试复杂度
- **默认快捷键改 `Ctrl+Alt+D`**：避开 VSCode 删除行、终端 EOF 等占用

## Task List

### Phase 1: 基础骨架

#### Task 1: 项目骨架 + 依赖 · XS
**描述**：建目录结构、依赖清单、gitignore、示例配置、README。

**Acceptance criteria**
- [ ] 目录结构按 plan 建好
- [ ] `pip install -r requirements.txt` 成功
- [ ] `python -m src.main` 能启动并打印欢迎信息

**Files**：`requirements.txt`、`.gitignore`、`config.example.yaml`、`README.md`、`src/main.py`、`src/__init__.py`
**Dependencies**：无

---

#### Task 2: 配置加载 · XS
**描述**：yaml 配置读取，支持环境变量覆盖（尤其 `api_key`）。

**Acceptance criteria**
- [ ] `Config.load()` 从 `config.yaml` 读到所有字段
- [ ] 环境变量 `EH_API_KEY` 可覆盖 yaml
- [ ] 缺失字段有清晰报错

**Verification**：`pytest tests/test_config.py`
**Files**：`src/config.py`、`tests/test_config.py`
**Dependencies**：Task 1

---

#### Task 3: 数据模型 + SQLite 初始化 · S
**描述**：定义核心 dataclass + SQLite 建表 + 缓存层 DAO。

**Acceptance criteria**
- [ ] `CapturedText` / `TaskRequest` / `TaskResult` dataclass 定义
- [ ] SQLite 按 spec 建 `queries` 表 + 索引，幂等
- [ ] `cache.get(key)` / `cache.put(...)` / `cache.bump_hit(key)` / `cache.regenerate(key, result)` 正确
- [ ] `cache_key` 生成用 `sha256(text.strip().lower() + task + lang + model)`

**Verification**：`pytest tests/test_cache.py` 覆盖命中/未命中/计数/覆写
**Files**：`src/core/models.py`、`src/storage/db.py`、`src/storage/cache.py`、`tests/test_cache.py`
**Dependencies**：Task 2

### Checkpoint A
- [ ] 依赖装干净
- [ ] 所有单测通过
- [ ] `data/english-helper.db` 成功建表

---

### Phase 2: 取词 + AI（核心路径）

#### Task 4: ClipboardSource + HotkeyManager · M
**描述**：全局 `Ctrl+Alt+D` 触发 → 模拟 Ctrl+C 取词 → 还原剪贴板 → 控制台打印。

**Acceptance criteria**
- [ ] `TextSource` 抽象接口
- [ ] `ClipboardSource` 备份 → Ctrl+C → 读 → 还原，小 sleep 等待复制完成
- [ ] `HotkeyManager` 注册全局热键（可配置）
- [ ] Smoke test：Chrome / VSCode / Windsurf / PDF / 终端 各试，都能取到词且剪贴板还原

**Files**：`src/sources/base.py`、`src/sources/clipboard.py`、`src/core/hotkey.py`、`src/main.py`
**Dependencies**：Task 2

---

#### Task 5: AIProvider + TranslateTask · M
**描述**：OpenAI 兼容 Provider + 翻译 Task（多义释义 + 音标）。

**Acceptance criteria**
- [ ] `AIProvider.stream(messages)` 抽象 + `OpenAICompatibleProvider` 实现
- [ ] `TranslateTask`：prompt 要求输出「音标 (IPA) + 多种常见词义 + 每义简注」
- [ ] 脚本 `scripts/try_translate.py`：输入单词 → 流式打印
- [ ] 测 `bank` / `run` / `ephemeral`，均能给出多义

**Files**：`src/ai/base.py`、`src/ai/openai_compat.py`、`src/ai/tasks/base.py`、`src/ai/tasks/translate.py`、`scripts/try_translate.py`
**Dependencies**：Task 2、3

---

#### Task 6: Pipeline 串起来（带缓存） · S
**描述**：把 source → cache → ai 串成一条管道，流式输出。

**Acceptance criteria**
- [ ] `Pipeline.run(action_id) -> Iterator[str]`
- [ ] 命中缓存：直接 yield 历史结果 + `bump_hit`，不调 AI
- [ ] 未命中：流式调 AI + 边流边拼接 + 流完 `put`
- [ ] `regenerate=True` 强制绕过缓存并覆写
- [ ] `main.py` 改走 pipeline，热键 → 控制台流式打印

**Files**：`src/core/pipeline.py`、`src/main.py`
**Dependencies**：Task 3、4、5

### Checkpoint B
- [ ] 端到端不带 UI 可用：热键取词 → 缓存/AI → 流式打印
- [ ] 同词二次查询无网络请求（日志验证）
- [ ] 用 3 天，验证「快捷键取词体验是否够爽」这条假设

---

### Phase 3: UI

#### Task 7: PyQt 浮窗 · M
**描述**：光标附近浮窗、流式渲染、X/ESC/失焦三合一关闭 + 悬停暂停失焦 + 重新生成按钮。

**Acceptance criteria**
- [ ] 无边框置顶窗，出现在光标附近（多屏 DPI 安全）
- [ ] 流式 chunk 追加，Markdown 渲染
- [ ] X 按钮 / ESC / 失焦 三种关闭，鼠标悬停浮窗时暂停失焦关闭
- [ ] 「重新生成」按钮调用 `pipeline.run(..., regenerate=True)`

**Files**：`src/ui/popup.py`、`src/main.py`
**Dependencies**：Task 6

---

#### Task 8: 托盘 + 设置页 + 开机自启 · M
**描述**：托盘常驻、设置页编辑配置、Windows 开机自启开关。

**Acceptance criteria**
- [ ] 系统托盘图标 + 菜单（设置 / 历史 / 退出）
- [ ] 设置页编辑 `api_key` / `base_url` / `model` / `hotkey` / `target_lang` / 自启
- [ ] 改配置后不需重启生效（重注册热键 + 重建 provider）
- [ ] 自启通过 `HKCU\...\Run` 注册表切换

**Files**：`src/ui/tray.py`、`src/ui/settings.py`、`src/autostart.py`
**Dependencies**：Task 7

### Checkpoint C
- [ ] MVP 全部 Acceptance 满足
- [ ] 自用 1 周，跑通所有 Key Assumptions

---

## Risks and Mitigations

| 风险 | 影响 | 缓解 |
|------|------|------|
| 剪贴板还原在富文本应用丢格式 | 中 | MVP 只还原 text；记录不兼容场景 |
| `keyboard` 库热键在个别应用失效 | 中 | 备选 `pynput`，Provider 化热键层 |
| OpenAI SDK 在非官方 base_url 行为差异 | 低 | Provider 封装，易替换 |
| PyQt 多屏 DPI 下浮窗定位偏 | 中 | `QCursor.pos()` + 屏幕几何校正 |
| Prompt 多义输出格式不稳定 | 中 | 写 golden sample，加重试 |

## Open Questions

- Prompt 输出 Markdown vs JSON → 建议 **Markdown**，流式体验好
- 默认快捷键 → 建议 `Ctrl+Alt+D`，避开常用占用

## Parallelization

- 串行为主（依赖链较紧）
- Task 4 和 Task 5 可并行（互不依赖）
