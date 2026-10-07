## pretrans-extractor v1.1.0

**结构重构版**：主文件瘦身为「必守规则 + 流程骨架 + 坑索引」，细节拆到 `references/` 分册，避免加载时被截断。

### 新增

| 分册 | 内容 |
|---|---|
| `references/01-decrypt-decode.md` | 解密 / 解压 / 化け（乱码）分类与修复 / 官方修正补丁 |
| `references/02-script-reverse.md` | 脚本结构：字符宽度感知、消息格式、字符层、宏、分支回填、点击语义 |
| `references/03-pitfalls.md` | **全量坑 + 真实返工案例**（解码层 / 提取层 / 交付层 / 流程） |
| `references/04-verify-and-report.md` | 自检 / 外部核对 / 验收清单 / 报告结构 |
| `references/05-workspace-and-tools.md` | 工作区布局、脚本形态、S1–S7 流程、环境要求 |
| `scripts/check_text.py` | 交付前通用品检（BOM / LF / `U+FFFD` / `〓` / 控制符、半角假名、PUA、引号配对、说话人残留、主角名出现性） |

新增提取器：

- KiriKiri XP3 系 —— `xp3.py`、`chou_decrypt.py`、`chou_extract.py`、`chou_fix.py`
- Nitroplus NPA —— `npa_nrbf.py`、`lamento_extract.py`
- 其他 —— `malie_extract.py`、`hanayoi_afs.py` / `hanayoi_extract.py` / `hanayoi_run.py`、`shinoda_botan_extract.py`、`vn_memdump.py`

### 变更

- `SKILL.md` 精简（细则移入 `references/`）；`description` 收敛为 3 行
- 输出规范独立成 §0，明确「只收直接上屏的文本」『一次点击 = 一行』「不加说话人前缀」

### 移除

- `references/output-spec.md`、`references/workflow-checklist.md`
  —— 内容并入 `SKILL.md` §0 与 `references/04-verify-and-report.md`

---

**安装**：把整个仓库放进 Agent 的 skills 目录（如 `~/.workbuddy/skills/pretrans-extractor/`），或直接当工具箱用（纯 Python）。
详见 [README](https://github.com/flamecho/pretrans-extractor#readme)。

**依赖**：第三方工具与密钥不自带，见 [`references/third-party.md`](https://github.com/flamecho/pretrans-extractor/blob/main/references/third-party.md)。

> 本仓库不含任何解密密钥、授权串或游戏资源；请仅对**合法拥有**的游戏副本使用。
