# pretrans-extractor

从日文 VN / AVG 游戏的封包资源中取出剧本文本，整理为纯文本，供制作 LunaTranslator 预翻译文件使用。

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB) ![Version](https://img.shields.io/badge/version-1.3.1-blue)

## 简介

日文游戏的剧本通常存放在加密封包里，由自定义字节码承载。这个工具做三件事：解包、解密、把各引擎的文本按同一套规则整理出来。整理规则中有一条是固定的：**一个文本框（一次点击）= 一行**。

仓库包含两部分：

- `scripts/` —— 可直接运行的 Python 脚本（容器解包工具 + 各引擎提取器 + 探查助手 + 交付前品检 + 收尾工具）；
- `SKILL.md` + `references/` —— 一份 Agent Skill，采用**渐进式披露**：主文件只放必守规则与流程骨架，细节按需读分册。

## 用途与边界

输出用于**制作 LunaTranslator 的预翻译文件**，即提供待翻译的日文原文。

本工具只负责提取原文：

- 不制作汉化补丁（不涉及把译文写回游戏、不生成补丁包）；
- 不做译文回填（不处理翻译结果的注入或对齐）。

翻译与后续处理在别的环节完成。

## 支持范围

已整理约 30 种引擎／容器的处理要点，单引擎细则见 [`references/engines/`](references/engines/)（一引擎一文件）。

| 引擎 / 容器 | 要点 |
|---|---|
| PSV NoNpDrm / PFS | `pkg2zip -x` → `psvpfsparser -z <zRIF>`（或 `-k`） |
| Switch NSP / XCI / NCA | PFS0 → NCA3（明文头 @0x200）→ RomFS |
| CRI CPK | 表长 `>>8`（`cpk.py`）/ `&0xFF`（`cpk_v1.py`）；判据 `@UTF` |
| Koei CDAR v2/v4 | 文本记录 `04 <u16 len> <cp932> 00` |
| Otomate VM | JIS X0208；字体替换槽随作而异 |
| KiriKiri XP3 + DropWave | `.ks/.tjs` = zlib + UTF-16LE；`[message]` = 一次点击 |
| BGI / Ethornell | `.arc` PackFile v2 + DSC；消息栈顶 = 人名 |
| Unity TextAsset（TKG / CSR） | PSARC → `resources.assets` |
| NScripter | Inno Setup；`nscript.dat` XOR 0x84 |
| SiglusEngine | 单 exe = PE + RAR5 SFX；`Scene.pck` |
| Artemis `pf8` | `key = SHA1(file[7:7+idx_size])`，整文件 XOR |
| Regista advGame | 自研 PRNG 流密码 |
| Takuyo gss | `LSDARC` 容器 + `SCR 2.00` |
| HuneX Ogre / MZX0 | `MZX0` → CP932 `_CMD()` |
| Nitroplus NPA / NSS | NPA 归档 + 自研 NSS 脚本；`<PRE boxNN>` = 一个文本对象 |

## 快速开始

### 作为 Agent Skill

把整个仓库放进对应 Agent 的 skills 目录。

```bash
~/.claude/skills/pretrans-extractor/          # Claude
~/.workbuddy/skills/pretrans-extractor/       # WorkBuddy（用户级）
<项目>/.workbuddy/skills/pretrans-extractor/  # WorkBuddy（项目级）
```

触发入口是 `SKILL.md` 的 frontmatter（`name` / `description`）。

### 直接使用脚本

不依赖任何 Agent，纯 Python。

```bash
export VNTRANS_HOME=/path/to/work          # 工作根目录
export VN_OUTDIR=/path/to/work/提取结果     # 输出目录

python scripts/identify.py game_dir        # 判型：容器 / 引擎 / 下一步命令
python scripts/cpk.py game.cpk out/        # 解 CPK
python scripts/probe.py jp extracted/      # 这条链路里到底有没有正文

# 交付前自检（退出码 0 = 通过）
python scripts/check_text.py "提取结果/XX_全文本.txt" --name 主角名
```

各脚本用法见文件头 docstring、[`scripts/INDEX.md`](scripts/INDEX.md)（通用工具）与
[`scripts/INDEX-BY-ENGINE.md`](scripts/INDEX-BY-ENGINE.md)（**按引擎找可改的提取器**）。

> `scripts/` 里的 `*_extract.py` 是**按具体作品写的**，默认输入路径来自编写时的解包目录
> （如 `_work_<game>/…`），首次使用请改脚本顶部的 `SRC` / `OUTDIR`，或用命令行参数指定。
> 通用工具（`identify` / `probe` / `check_text` / `wrapup` / `split_md` 等）可直接用，不依赖这些默认值。

## 整理流程（一条命令）

提取完成后的收尾是重复劳动，所以做成了工具链。**报告头部先写机器可读块**，指标就不用猜：

```yaml
---
作品: 某某作品
平台: PSP
引擎: STCM2L
主角: 姓 名
行数: 31838
日期: 2026-10-18
---
```

然后一条命令跑完：

```bash
python scripts/wrapup.py --report "提取结果/解析报告/XX_解析报告.md" \
                         --text  "提取结果/XX_全文本.txt" --name 主角名
```

| 步 | 工具 | 检查什么 |
|---|---|---|
| ① 成品品检 | `check_text.py` | BOM / CR / U+FFFD / 控制符 / 半角假名 / PUA / 引号配对 / 说话人残留 |
| ①b 行数一致性 | 内置 | 报告声明的行数 vs 成品实际行数（差 >1% 报警） |
| ② 体积体检 | `memcheck.py` | 手册各册是否超 10 KB（≥96% 提前预警） |
| ③ 沉淀草案 | `distill.py` | 报告里的判据按「已覆盖 / 待沉淀 / 单作特例」三分，并给建议落位 |
| ④ 落位片段 | `archive_work.py` | 生成作品索引 / 工具索引 / 日志小节；`--apply` 幂等追加 |

拆分手册时只用 `split_md.py`：只按**语义边界**（标题、编号条目）下刀，带正文行守恒校验，
并按「临时目录 → 校验 → 打印待删清单 → 断言与输出名不相交 → 才删旧」的顺序替换。

平时（改过手册 / 收工前）还有两条：

```bash
python scripts/lint_docs.py       # 断链 / 引擎册未进路由表 / 孤儿册 / 空册 / 超限
python scripts/pending.py         # 有成品无报告 / 有报告未进索引
python scripts/memcheck.py --fix  # 超限时直接给切点（不落盘）
```

## 兼容性

| 层面 | 说明 |
|---|---|
| `scripts/` 下的脚本 | 纯 Python，与 Agent 无关，可独立运行 |
| `SKILL.md` + `references/` | 遵循 Agent Skills 通用约定（`SKILL.md` + `name`/`description` frontmatter）。Claude Code、WorkBuddy 等可识别；其他仅支持自有插件格式的工具需少量适配 |

## 输出规范

产物为 UTF-8 with BOM、纯 LF、无 U+FFFD 的纯文本。整理规则：

- 一次点击 = 一行；同一消息框内的软换行合并；
- 保留日文原文，不翻译，不加说话人前缀；
- 主角名、术语引用、`%s` 等占位符行内展开；
- 清除控制码，注音只保留基字；
- 专有名词经外部资料（vndb、官方站）核对；
- 无法解析的码位保留原码并单独列出，不作猜测；
- 只含正文与选项，不含系统 / UI 文本、说话人表等附属产物。

细则见 [`SKILL.md`](SKILL.md) §0 与 [`references/05-selfcheck.md`](references/05-selfcheck.md)。

## 环境变量

| 变量 | 含义 | 默认 |
|---|---|---|
| `VNTRANS_HOME` | 工作根目录 | 当前目录 |
| `VN_OUTDIR` | 输出目录 | `$VNTRANS_HOME/提取结果` |
| `SEVENZ` | 7-Zip 路径 | `C:\Program Files\7-Zip\7z.exe` |
| `PROD_KEYS` | Switch `prod.keys` | 脚本同级 `prod.keys` |
| `ZRIF` / `PSVDEC` | PSV 解密参数 / psvdec 目录 | 空 / 脚本同级 `psvdec` |

## 目录结构

```
pretrans-extractor/
├── SKILL.md                       # 主文件：必守规则 + 流程骨架 + 导航（先读这个）
├── README.md
├── CHANGELOG.md
├── LICENSE                        # MIT
├── .gitignore
├── docs/release-v1.3.1.md         # v1.3.1 版本说明（本版）
├── docs/release-v1.3.0.md         # v1.3.0 版本说明
├── references/
│   ├── 00-index.md                # 一页导航（阶段 → 文件）
│   ├── 00-triage.md               # 判型：平台 → 容器 → 脚本 → 厂商 → 四步攻坚
│   ├── 01-*.md                    # 取得 / 容器（PFS / EBOOT / NCA / CHD / 解密）
│   ├── 02-*.md                    # 脚本层（结构 / 记录形状 P1–P8 / 24 条反例 / Unity）
│   ├── 03-*.md                    # 解码（宽度 / 码表 / 归档 / 字体 / 名字宏）
│   ├── 04-*.md                    # 成行（定框 / 名札 / 选项 / 回声 / 案例）
│   ├── 05-*.md                    # 交付（自检 / 外部核对 / 完整性 / 收尾流程）
│   ├── 06-*.md                    # 流程与环境（工作区 / 决策纪律）
│   ├── pitfalls/                  # 坑索引 15 册（A 解码 / B 提取 / C 交付 / E 专册）
│   ├── engines.md                 # 引擎**路由表**（一句话索引 + 详见列）
│   ├── engines-2.md               # 路由续册：自研/小众/单作系
│   ├── engines-3.md               # 路由续册：同族变体（STCM2L / UNI2 / HuneX / Takuyo）
│   ├── engines-solo.md            # 路由续册：单作专用自研引擎
│   ├── engines/                   # 单引擎全量分册（一引擎一文件，≤10 KB）
│   └── third-party.md             # 第三方工具与依赖（自备）
└── scripts/
    ├── INDEX.md                   # 11 个通用工具：用法 + 何时跑
    ├── INDEX-BY-ENGINE.md         # 引擎 → 可改的提取器（构建时自动生成）
    ├── identify.py                # S0 判型
    ├── probe.py                   # 限量探查（≤80 行）
    ├── check_text.py              # 交付前品检
    ├── wrapup.py                  # 收尾编排（一条命令）
    ├── distill.py                 # 沉淀草案
    ├── archive_work.py            # 落位片段
    ├── memcheck.py                # 体积体检
    ├── split_md.py                # 按语义边界拆 md（带校验）
    ├── lint_docs.py               # 手册对账（断链 / 孤儿册 / 路由缺失）
    ├── pending.py                 # 未落位检测（有成品没进索引）
    ├── *_extract.py …             # 按作品编写的提取器（239 个，改 SRC/OUTDIR 即可复用）
    ├── cpk.py / psarc_extract.py / cdar.py / xp3.py / nsac.py …   # 通用容器工具
    └── scan*.py / renderfont.py …                                  # 探查与字体助手
```

## 隐私与安全

本包**不包含**：

- 解密密钥文件（Switch `prod.keys` / `title.keys`、PSV zRIF 等）；
- 个人识别信息（用户名、本机绝对路径、私有目录名）；
- 第三方二进制或源码仓库（hactool / pkg2zip / psvdec / Kuriimu2 / GARbro / innoextract 等），改由 [`references/third-party.md`](references/third-party.md) 给出获取方式；
- 游戏资产（字体库、图集）与已提取的成品文本。

脚本中的路径均从环境变量取值，不写死绝对路径。个别脚本会经 `subprocess` 调用 7-Zip，并清理自己创建的临时 / 输出目录；`haruka6_dict.py` 用 `exec` 加载同目录的 `haruka6_extract.py`。除此之外无网络访问、无外部写入。

## 文档

| 内容 | 位置 |
|---|---|
| 规范与流程骨架 | [`SKILL.md`](SKILL.md) |
| **开工第一册：判型** | [`references/00-triage.md`](references/00-triage.md) |
| 一页导航 | [`references/00-index.md`](references/00-index.md) |
| 解密 / 化け修复 | [`references/01-decrypt.md`](references/01-decrypt.md) |
| 脚本结构 / 记录形状 / 反例 | [`references/02-structure.md`](references/02-structure.md) · [`02-record-patterns.md`](references/02-record-patterns.md) · [`02-false-signals.md`](references/02-false-signals.md) |
| 解码 | [`references/03-basics.md`](references/03-basics.md) · [`03-codetable-elf.md`](references/03-codetable-elf.md) |
| 成行 | [`references/04-lines.md`](references/04-lines.md) · [`04-typing.md`](references/04-typing.md) |
| 自检 / 核对 / 完整性 | [`references/05-selfcheck.md`](references/05-selfcheck.md) · [`05-external-report.md`](references/05-external-report.md) · [`05-completeness.md`](references/05-completeness.md) |
| **收尾（一条命令 + 拆分纪律）** | [`references/05-wrapup.md`](references/05-wrapup.md) |
| 坑索引 15 册 | [`references/pitfalls/`](references/pitfalls/) |
| 各引擎做法 | [`references/engines.md`](references/engines.md)（路由表）→ `references/engines/*.md` |
| 第三方工具 | [`references/third-party.md`](references/third-party.md) |
| 脚本索引 | [`scripts/INDEX.md`](scripts/INDEX.md) |
| 更新日志 | [`CHANGELOG.md`](CHANGELOG.md) |

## 依赖

第三方工具与密钥不自带，见 [`references/third-party.md`](references/third-party.md)。

## License

MIT，见 [`LICENSE`](LICENSE)。

## 免责声明

本工具供技术研究，以及对合法拥有的游戏副本做文本提取、LunaTranslator 预翻译文件制作等翻译前置处理使用。不附带任何游戏资源、密钥或受版权保护的文本；提取所得文本的著作权归原作者所有。
