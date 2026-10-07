# 工作区、工具与流程约定

## 1. 工作区（`<工作区>`）

| 用途 | 位置 |
|---|---|
| **工作缓冲**（解包目录、`_src_*` / `_work_*`、探查脚本） | 工作区根 |
| **提取结果**（成品 txt + 解析报告同放） | `提取结果/` |
| **定稿脚本**（跨作复用） | `scripts/` 顶层 |
| **探查脚本归档** | `scripts/_archive/<game>/`（可选，自行建立） |
| **通用品检** | `scripts/check_text.py` |
| 自建成品汇总库（可选） | `<你的成品汇总库>/` |
| 清理记录 | `清理记录_YYYY-MM-DD.txt`（追加式：删/归档/保留/重跑步骤） |
| 引擎全量要点 | `references/engines.md`（本 skill 内） |
| 项目记忆（可选） | `.workbuddy/memory/`（跨作铁律 / 引擎细节 / 日志） |

**源母本**多在 `<原始 dump 目录>/`。脚本路径约定：走环境变量（`VNTRANS_HOME` / `VN_OUTDIR` / `SEVENZ` /
`PROD_KEYS` / `ZRIF` / `PSVDEC`），**不硬编码绝对路径**。

**并行 agent**：本工作区可能同时有别的 agent 在跑 → 覆盖 `scripts/` 或重跑前先看产物 mtime 与内容。

## 2. 常用脚本形态

- `*_extract.py` — 容器 → 消息列表 → txt（一作/一引擎一张表）
- `*_decrypt.py` — 解密/解压（区间键模型 + 定值复元表）
- `*_fix.py` — 定值复元表（`REKEY` / `OVERRIDES` / `TEXT_PATCH` + `apply_fix()`）
- `check_text.py` — 交付前自检（见 `04-verify-and-report.md`）
- `probe.py` / `region.py` — 逐条打印 `RAW` 十六进制 + `DEC` 解码 / 带注释的区间转储
- `renderfont.py` + 字库 — 从字形图集（GXT/G1T 等）渲染指定槽位，**读图核对**
- 消息中间件 `.pkl` — 解容器与出 txt 解耦，便于反复调行粒度

## 3. 标准流程（S1〜S7 速查）

| 步 | 做什么 | 关键判据 |
|---|---|---|
| **S1 源** | 定位母本；`7z l` 看结构 | 头部加密？密码在同目录小 txt；**同捆更新程序先解**（见 `01-decrypt-decode.md` §5） |
| **S2 容器** | 解外层，拿脚本资源 | 先认魔数：`XP3`/`CPK`/`PFS`/`NCA`/`PSARC`/`NSAC`/`AFS`/`DATA.BIN`… |
| **S3 解密** | 还原文件内容 | ① 已知魔数反推键 → ② 字符似然模型 → ③ 定值复元表 |
| **S4 脚本结构** | 认容器与记录格式 | 用「文本记录驱动扫描」自定界 ⇒ 永不失步 |
| **S5 文本解码** | 码表 / 替换槽 / 宏 | 假名块先定；替换槽不信 cp932 |
| **S6 提取成行** | 按输出规范落地 | 续写形态**全集**（`03-pitfalls.md` B1） |
| **S7 自检 + 报告** | 自检 + 写报告 | 报告必须含**重跑步骤** |

## 4. 环境

- managed python：`python`
- 7-Zip：`C:/Program Files/7-Zip/7z.exe`
- pip：`-i https://pypi.org/simple`（GitHub raw 被墙走 `api.github.com`）

## 5. 记忆维护

- 每作完成后：当日日志追加（结论 / 工具 / 产物 / 重跑），跨作铁律进长期笔记，
  引擎细节进 `references/engines.md`，作品索引加一行。
- **用户说「清理产物」时**：① 按约定清理；② **顺手检查本 skill 是否需要修订/补充**（新踩的坑要沉淀）。
