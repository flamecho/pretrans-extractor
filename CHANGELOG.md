# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 与 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [1.2.0] - 2026-10-10

**知识库分层 + 决策纪律版**。把「一个巨型坑文件 + 一个巨型引擎文件」改成**按阶段 / 按引擎拆分**，
并新增三条最高优先级的作业纪律与两个流程步。

### 新增

- **三条最高优先级纪律**（`SKILL.md` §0）：① 禁止穷举 ② 禁止 OCR ③ 禁止无规划试错
  （动手前先立假设 + 证伪条件；同一假设 2 次探查无新信息即换路；单点 >3 次未收敛即汇报）。
- **流程新增两步**：**S0 识别**（`scripts/identify.py`：一次调用给出「引擎 + 建议命令 + 该读哪份引擎分册」）
  与 **S8 收尾**（每作交付后自动跑 `memcheck.py` + 落记忆，不等用户提醒）。
- **上下文卫生纪律**（`SKILL.md` §2 / `references/05` §6）：探查限量 ≤80 行、只读「这一步」需要的、不预读、大文件主动拆。
- **新脚本**：`identify.py`（容器→引擎识别）、`probe.py`（限量探查）、`memcheck.py`（体积体检）。
- **新增提取器**：`believer_extract.py`（HuneX HESL/HESE）、`advhd.py` + `blip/bgloss/brouge_extract.py`
  （WillPlus AdvHD `.wsc`）、`libp_malievita.py` / `mysteria_extract.py` / `mysteria_text.py`（Malie Vita）、
  `rom2_extract.py` / `torimari_extract.py`（ROM2·SNR）、`norn9_extract.py` / `pandora_extract.py`（STCM2L 平台变体）、
  `gensou_decode.py` / `gensou_extract.py` / `gensou_scan.py`、`haruka5_extract.py` / `kazahanaki_extract.py`、
  `shinoda_botan_extract.py`、`vn_memdump.py` 等。
- **新增坑条目**：A14（WSC `rotl_8` / 选项目标指令须按表分派）、A15（脚本 magic 之前的前缀区块另含正文）、
  A16（归档块单位需反推，取错＝整体错位）、A17（opcode 逐文件平移）、A18（同族指令头布局随平台变）、
  A9（自建码表用一条已知明文锚定基址）、B7（互斥分支＝同一点击多版本正文）、B8（共通导入块去重）、
  C8（辞典载体可能是同发行商他作遗留串）。

### 变更

- `SKILL.md` 重写：明确「开工只读本文件；§3 索引已覆盖全部坑，细节按阶段读」。
- `references/03-pitfalls.md` → 拆为 **`03a-decode-basics` / `03b-decode-archive` / `03c-decode-wsc-ops` /
  `03d-extract-lines` / `03e-deliver-flow`** 五个按阶段分册。
- `references/engines.md` → 改为**路由表**（一句话索引 + 「详见」列），引擎细节拆到
  **`references/engines/<slug>.md`**（一引擎一文件，18 册，各 ≤10 KB）。

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
