# 00 · 导航（按流程阶段）

> **一页定位**：先看「两条路径」，再按当前所处的阶段打开**那一册**。没有列到的不要预读。
> 编号（①〜ⓨ / A1〜A19 / B1〜B31）在重组中保持原样，旧引用不会失效。

## 两条路径

| 情形 | 做法 | 目标 |
|---|---|---|
| **命中已知引擎** | 走 `00-triage.md` 的表 → 只读命中的 `engines/<slug>.md` → 复用 `../scripts/INDEX.md` 的脚本 | 同族续作快速出文本 |
| **未命中** | `00-triage.md` §E 四步攻坚 → `02-record-patterns.md` 认形状 → `04-*` 成行 → `05-*` 自检 | 慢但可收敛、不踩坑 |

## 阶段 → 文件

| 阶段 | 做什么 | 读这些 |
|---|---|---|
| **S0 判型** | 平台 / 容器 / 引擎 | **`00-triage.md`** |
| **S1 取得** | 母本、压缩包、镜像 | `01-image-chd.md`（CHD/NSZ） |
| **S2 容器** | PSV / PSP / Switch / 解密总纲 | `01-psv-pfs.md` · `01-psp-eboot.md` · `01-switch-nca.md` · `01-decrypt.md` |
| **S3 解压 / 归档** | 归档结构、块单位、Δ、自校验 | `03-archive.md` · `03-archive-family.md` · `03-archive-delta.md` · `03-wsc-ops.md` |
| **S4 脚本** | 脚本结构、记录形状、反例 | `02-structure.md` · **`02-record-patterns.md`** · **`02-false-signals.md`** · `02-stcm2l.md` |
| **S4' Unity** | IL2CPP / Naninovel / `.bytes` | `02-unity.md` · `02-unity-bytes.md` · `02-unity-bytes-works.md` |
| **S5 解码** | 宽度、码表、字体槽、名字宏 | `03-basics.md` · `03-codetable-elf.md` · `03-selffont.md` · `03-names-macro.md` |
| **S6 成行** | 一次点击＝一行、名札、选项、定框 | `04-lines.md` · `04-typing.md` · `04-lines-names.md` · `04-lines-options.md` · `04-lines-echo.md` · `04-lines-cases.md` |
| **S7 交付** | 自检、外部核对、完整性、报告 | `05-selfcheck.md` · `05-external-report.md` · `05-completeness.md` · `05-deliver-pitfalls.md` |
| **S8 收尾** | **一条命令跑完品检/体积/沉淀/落位** ＋ 工作区、记忆、纪律 | **`05-wrapup.md`** · `06-workspace.md` · `06-discipline.md` |

## 坑索引分册（按层，原 `00*` 重组）

| 册 | 层 | 内容 |
|---|---|---|
| `pitfalls/A1-decode-core.md` | 解码 | 核心判据 ①〜⑮（宽度 / 替换槽 / PUA / 归档 / opcode / 平台） |
| `pitfalls/A2-decode-late.md` | 解码 | 后期 ㉒〜㉙（未压缩判定 / assembly 内文本 / LZSS 变体） |
| `pitfalls/B1-lines.md` | 提取 | 成行 / 断框 / 命名 / 选项 |
| `pitfalls/B2-tags-resume.md` | 提取 | 标签脚本 / 续行边界 / 点击 vs 段 |
| `pitfalls/B3-lines-cont.md` | 提取 | 成行续 |
| `pitfalls/B4-late-1.md` | 提取 | 后期 ㉝〜（解码＋提取混合） |
| `pitfalls/B5-late-2.md` | 提取 | 后期 ㊶〜㊽（解码＋提取混合） |
| `pitfalls/B6-late-3.md` | 提取 | 后期 ⓒ〜（解码＋提取混合） |
| `pitfalls/B7-late-4.md` | 提取 | 后期 ⓒ〜ⓝ（提取层） |
| `pitfalls/B8-late-5.md` | 提取 | 后期 ⓞ〜ⓥ（标签数据表串 / 一命令多串 / 多块＝多文件 / 工具判型会错 / 载体错位 / XOR 0xDA / 串表首条残留 / 引号净差） |
| `pitfalls/B9-late-6.md` | 提取 | 后期 ⓦ〜ⓩ4（tag 字节任意 / `N-6` 越界 / 剧本·系统分装 / Δ 退化 / 开发测试块 / 表槽位 / 池首重复） |
| `pitfalls/C1-deliver.md` | 交付 | 交付层 ＋ 流程 |
| `pitfalls/C2-deliver-2.md` | 交付 | 交付 / 流程层 续 |
| `pitfalls/E1-m2-psb.md` | 专册 | M2 ADVENGINE／PSB·PGD |
| `pitfalls/E2-cri-kag.md` | 专册 | CRI CPK 块流 / CRILAYLA / KAG `.ks` |

## 引擎知识

| 入口 | 用法 |
|---|---|
| 工作区 `engines.md` | **路由表**：一句话索引 ＋ 「详见」列（`ENGINES-2` / `ENGINES-solo` 为续册） |
| `engines/<slug>.md`（工作区） | 单引擎全量（一引擎一文件 ≤10 KB）；**只读命中的那一个** |

## 脚本

`../scripts/INDEX.md`（按引擎 / 容器分类）。

| 阶段 | 脚本 |
|---|---|
| S0 判型 | `identify.py` |
| S2 探正文 | `probe.py` |
| S7 品检 | `check_text.py` |
| S8 收尾 | **`wrapup.py`**（编排）→ `memcheck.py` / **`distill.py`**（沉淀草案）/ **`archive_work.py`**（落位片段） |
| 手册维护 | **`split_md.py`**（按语义边界拆，带校验与原子替换） |
