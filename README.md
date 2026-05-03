# English Helper

> **Windows 桌面 AI 英语助手** · 任意应用选中英文 → `F8` → 光标旁浮窗流式输出词典级释义。
>
> 不抢焦点 · 不打断阅读 · 本地缓存秒回 · 单键操作。

个人自用工具，全程由 AI Agent 协作开发完成。零浏览器扩展依赖，PDF / IDE / 终端 / 任何应用里都能划词。

## Features

- **F8 单键取词** —— 全局热键，可在 `config.yaml` 改
- **OpenAI 兼容接口** —— DeepSeek / Kimi / OpenAI / Ollama 任选
- **SQLite 查询缓存** —— 命中直接返回，零延迟
- **流式 Markdown 浮窗** —— 光标旁渲染，X / ESC / 失焦关闭，悬停暂停
- **系统托盘** —— 暂停 / 关于 / 退出 / 开机自启
- **Windows 注册表自启** —— 登录自动驻留

## Quick Start

```powershell
# 1. 环境
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 配置 API key
copy config.example.yaml config.yaml
notepad config.yaml   # 填 ai.api_key

# 3. 启动（无控制台窗口）
Start-Process .\.venv\Scripts\pythonw.exe run.pyw

# 开发模式（带控制台日志）
.\.venv\Scripts\python.exe -m src.main
```

选中任意英文 → 按 **F8** → 浮窗出现。右键托盘图标可暂停/退出/开启自启。

## Architecture

三层抽象，每层都是 ABC + 具体实现，可独立替换：

```
UI Layer (PyQt6)              popup.py · tray.py · worker.py · main.py
         │
         ▼
Core Layer (无 IO 依赖)        pipeline.py · models.py · hotkey.py
         │
   ┌─────┼─────┐
   ▼     ▼     ▼
Sources  AI    Storage         三个可独立替换的「插槽」
```

关键设计：
- **跨线程焦点修复** —— hotkey 线程先完成 Ctrl+C 取词再 emit 信号显示 popup，避免 popup 抢焦点导致取词为空
- **缓存幂等** —— `INSERT ... ON CONFLICT DO UPDATE` 保留 `is_starred` / `hit_count`
- **autostart 跨 cwd** —— `run.pyw` 启动器自校正 cwd，注册表项启动后不依赖工作目录

## Tests

```powershell
pytest -q
# 26 passed
```

覆盖：config 加载、cache CRUD + 幂等、pipeline 命中/未命中/重新生成、translate prompt、autostart 注册表往返。

## Docs

- 产品一页纸：`docs/ideas/ai-english-helper.md`
- 实施计划：`docs/ideas/implementation-plan.md`

## Known Limitations

- **经典「命令提示符」（conhost / 老式 cmd）** 不支持 `Ctrl+C` 复制选中文本，在其中取词会返回空。推荐用 Windows Terminal（`wt`）打开 cmd/PowerShell，功能正常。
- **剪贴板历史（Win+V）会留痕**：Windows 剪贴板历史服务会记录每次 Ctrl+C 写入，程序无法抑制。建议在系统设置关闭剪贴板历史：`设置 → 系统 → 剪贴板 → 剪贴板历史 = 关`。
- **非文本剪贴板内容丢失**：取词过程会备份并还原剪贴板**文本**；图片 / 文件 / 富文本等非文本内容取词后会变空。
- **管理员权限应用**：目标应用若以管理员身份运行，热键和 `Ctrl+C` 可能收不到（需以管理员身份启动本程序）。

## Roadmap

- [x] **Phase 1** 骨架：config / SQLite / 缓存 / 数据模型
- [x] **Phase 2** 端到端 MVP：热键 + 取词 + AI 流式 + 缓存（控制台版）
- [x] **Phase 3** 桌面化：PyQt6 浮窗 + 系统托盘 + 开机自启
- [ ] **Phase 4** 进阶：收藏夹 UI · UIAutomation 取词源 · PyInstaller 打包 .exe

## Tech Stack

Python 3.12 · PyQt6 · OpenAI SDK (compat mode) · SQLite · `keyboard` · `pyperclip` · `winreg`
