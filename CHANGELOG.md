# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 与 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [1.1.0] - 2026-10-07

**结构重构版**：主文件改为「必守规则 + 流程骨架 + 坑索引」，细节下沉到 `references/` 分册，避免加载时被截断。

### 新增

- `references/01-decrypt-decode.md` —— 解密 / 解压 / 化け（乱码）分类与修复 / 官方修正补丁。
- `references/02-script-reverse.md` —— 脚本结构逆向：字符宽度感知、消息格式、字符层、宏、分支回填、点击语义。
- `references/03-pitfalls.md` —— **全量坑 + 真实返工案例**（解码层 / 提取层 / 交付层 / 流程）。
- `references/04-verify-and-report.md` —— 自检、外部核对、验收清单、报告结构。
- `references/05-workspace-and-tools.md` —— 工作区布局、脚本形态、S1–S7 流程、环境要求。
- `scripts/check_text.py` —— 交付前通用品检：BOM / LF / `U+FFFD` / `〓` / 控制符、
  **半角假名**、**私用区 PUA**、**引号配对**、**说话人残留**、主角名出现性、空行 / 超长行 / 相邻重复行。
- 新增提取器：`xp3.py` / `chou_decrypt.py` / `chou_extract.py` / `chou_fix.py`（KiriKiri XP3 系）、
  `npa_nrbf.py`（Nitroplus NPA）、`lamento_extract.py`、`malie_extract.py`、
  `hanayoi_afs.py` / `hanayoi_extract.py` / `hanayoi_run.py`、`shinoda_botan_extract.py`、`vn_memdump.py`。
- `CHANGELOG.md`。

### 变更

- `SKILL.md` 精简为「输出规范 + 自检 + 流程骨架 + 坑索引 + 导航」；原细则移入 `references/`。
- 输出规范独立成 §0，明确「只收直接上屏的文本」「一次点击 = 一行」「不加说话人前缀」。
- `description` 收敛为 3 行。

### 移除

- `references/output-spec.md`、`references/workflow-checklist.md`
  —— 内容分别并入 `SKILL.md` §0 与 `references/04-verify-and-report.md`。

## [1.0.0] - 2026-10-06

首个公开版本：容器解包工具 + 各引擎提取器 + 输出规范 + 30+ 引擎复用要点。

- `SKILL.md` / `README.md` / `LICENSE`(MIT) / `.gitignore`
- `references/`：`engines.md`、`output-spec.md`、`workflow-checklist.md`、`third-party.md`
- `scripts/`：81 个提取/容器/探查脚本 + `INDEX.md` + `koei/` + `hunex/`
