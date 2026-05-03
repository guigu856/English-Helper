# English Helper

Windows 桌面 AI 英语助手。任意应用里选中英文 → 按快捷键 → 光标旁浮窗显示 AI 翻译与释义。

## Features (MVP)

- 全局快捷键取词（默认 `F8`，可在 `config.yaml` 改）
- OpenAI 兼容接口（DeepSeek / Kimi / OpenAI / Ollama 等）
- SQLite 查询缓存，命中直接返回
- 流式渲染浮窗（X / ESC / 失焦 关闭，悬停暂停）
- 系统托盘常驻 + 开机自启

## Quick Start

```powershell
# 1. 环境
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. 配置
copy config.example.yaml config.yaml
# 编辑 config.yaml，填 api_key

# 3. 运行
python -m src.main
```

## Docs

- 产品一页纸：`docs/ideas/ai-english-helper.md`
- 实施计划：`docs/ideas/implementation-plan.md`

## Known Limitations

- **经典「命令提示符」（conhost / 老式 cmd）** 不支持 `Ctrl+C` 复制选中文本，在其中取词会返回空。推荐用 Windows Terminal（`wt`）打开 cmd/PowerShell，功能正常。
- **剪贴板历史（Win+V）会留痕**：Windows 剪贴板历史服务会记录每次 Ctrl+C 写入，程序无法抑制。建议在系统设置关闭剪贴板历史：`设置 → 系统 → 剪贴板 → 剪贴板历史 = 关`。
- **非文本剪贴板内容丢失**：取词过程会备份并还原剪贴板**文本**；图片 / 文件 / 富文本等非文本内容取词后会变空。
- **管理员权限应用**：目标应用若以管理员身份运行，热键和 `Ctrl+C` 可能收不到（需以管理员身份启动本程序）。

## Status

Phase 2 完成：热键取词 + 缓存 + AI 翻译（控制台流式）端到端可用。下一步 Phase 3：PyQt 浮窗 + 托盘。
