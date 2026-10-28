# pretrans-extractor

从日文 VN / AVG 游戏的封包资源中取出剧本文本，整理为纯文本，供制作 LunaTranslator 预翻译文件使用。

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB) ![Version](https://img.shields.io/badge/version-1.4.0-blue)

## 简介

日文游戏的剧本通常存在加密封包里，由自定义字节码承载。这个工具做三件事：**解包 → 解密 → 按同一套规则把各引擎的文本整理出来**。规则里有一条是硬的：**一个文本框（一次点击）＝ 一行**。

仓库两部分：

- `scripts/` —— 可直接运行的 Python：容器解包、**585 个按作品写的提取器**、19 个通用工具（判型 / 探查 / 品检 / 收尾），外加三张索引；
- `SKILL.md` ＋ `references/` —— 一份 Agent Skill，**渐进式披露**：主文件只放必守规则与流程骨架，细节按需读分册。

遇到做过的引擎，最快三步：`S0-triage.md` 判型 → `engines/<slug>.md` 看容器链路与记录形状 → `INDEX-BY-ENGINE.md` 里挑**最近似**的脚本，只改路径 / 键 / 参数。

## 用途与边界

输出用于**制作 LunaTranslator 的预翻译文件**，即提供待翻译的日文原文。本工具只负责提取：不做汉化补丁、不做译文回填。翻译与后续处理在别的环节完成。

## 快速开始

### 作为 Agent Skill

把整个仓库放进对应 Agent 的 skills 目录：

```bash
~/.claude/skills/pretrans-extractor/          # Claude
~/.workbuddy/skills/pretrans-extractor/       # WorkBuddy（用户级）
<项目>/.workbuddy/skills/pretrans-extractor/  # WorkBuddy（项目级）
```

触发入口是 `SKILL.md` 的 frontmatter（`name` / `description`）。

### 直接跑脚本

不依赖任何 Agent，纯 Python。

```bash
export VNTRANS_HOME=/path/to/work           # 工作根目录
export VN_OUTDIR=/path/to/work/提取结果      # 输出目录

python scripts/identify.py game_dir         # 判型：容器 / 引擎 / 下一步命令
python scripts/cpk.py game.cpk out/         # 解 CPK
python scripts/probe.py jp extracted/       # 这条链路里到底有没有正文

# 交付前自检（退出码 0 = 通过）
python scripts/check_text.py "提取结果/XX_全文本.txt" --name 主角名
```

> `scripts/*_extract.py` 是**按具体作品写的**，默认输入路径来自编写时的解包目录（如 `_work_<game>/…`），
> 首次使用请改脚本顶部的 `SRC` / `OUTDIR`，或用命令行参数指定。通用工具不依赖这些默认值。

## 整理流程

提取完成后的收尾是重复劳动，所以做成了工具链。**报告头部先写机器可读块**：

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

然后一条命令跑完，最后只输出**一张待办清单**：

```bash
python scripts/wrapup.py --report "解析报告/XX_解析报告.md" \
                         --text   "提取结果/XX_全文本.txt" --name 主角名
```

| 步 | 工具 | 检查什么 |
|---|---|---|
| ① 成品品检 | `check_text.py` | BOM / CR / U+FFFD / 控制符 / 半角假名 / PUA / 引号配对 / 说话人残留 / 双版声明 / 字符台账 |
| ② 手册对账 | `lint_docs.py` | 断链 / 路由缺失 / 孤儿册 / 空册 / 编号连续 / 排版 / `§N` 引用 / 命令可跑 |
| ③ 沉淀草案 | `distill.py` | 报告里的判据按「已覆盖 / 待沉淀 / 单作特例」三分 |
| ④ 落位片段 | `archive_work.py` | 作品索引 / 工具索引 / 日志小节；`--apply` 幂等追加 |

拆分手册只用 `split_md.py`：只按**语义边界**（标题、编号条目）下刀，带正文行守恒校验，按
「临时目录 → 校验 → 打印待删清单 → 才删旧」的顺序替换。

平时（改过手册 / 收工前）还有三条：

```bash
python scripts/lint_docs.py       # 手册对账
python scripts/pending.py         # 有成品无报告 / 有报告未进索引
python scripts/memcheck.py        # 列各册大小；只对「自动注入上下文」的册告警
```

## 输出规范

产物为 UTF-8 with BOM、纯 LF、无 U+FFFD 的纯文本：

- 一次点击 ＝ 一行；同一消息框内的软换行**合并**；
- 保留日文原文，不翻译，不加说话人前缀；
- 主角名、术语引用、`%s` 等占位符行内展开；
- 清除控制码，注音只保留基字；
- 专有名词经外部资料（vndb、官方站）核对；
- 无法解析的码位**保留原码并单独列出**，不猜；
- 只含正文与选项，不含系统 / UI 文本、说话人表等附属产物。

细则见 [`00-rules.md`](references/00-rules.md)。

## 支持范围

已整理 **102 本单引擎分册**（约 40 个引擎族），入口是路由表 [`engines.md`](references/engines.md)。常见形态：

| 引擎 / 容器 | 要点 |
|---|---|
| PSV NoNpDrm / PFS | `pkg2zip -x` → `psvpfsparser -z <zRIF>`（或 `-k`） |
| Switch NSP / XCI / NCA | PFS0 → NCA3（明文头 @0x200）→ RomFS |
| CRI CPK | 表长 `>>8`（`cpk.py`）/ `&0xFF`（`cpk_v1.py`）；判据 `@UTF` |
| Koei CDAR v2/v4 | 文本记录 `04 <u16 len> <cp932> 00` |
| Otomate VM / STCM2L | JIS X0208；字体替换槽随作而异 |
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

## 目录结构

```
pretrans-extractor/
├── SKILL.md                       # 主文件：必守规则 + 流程骨架 + 导航（先读这个）
├── README.md
├── CHANGELOG.md
├── LICENSE                        # MIT
├── references/
│   ├── 00-*.md                    # 横切层：导航 / 输出规范 / 决策纪律 / 工作区约定
│   ├── S0-triage.md               # 判型：平台 → 容器 → 脚本 → 厂商 → 四步攻坚
│   ├── S1-*.md 〜 S8-*.md         # 取得 / 容器解密 / 解压归档 / 脚本 / 解码 / 成行 / 交付 / 收尾
│   ├── pitfalls/                  # 坑册 13 册（A 解码 / B 提取 / C 交付 / E 专册）
│   ├── engines.md                 # 引擎路由表（一句话索引 + 详见列）
│   ├── engines-2.md / engines-3.md / engines-solo.md   # 路由续册
│   ├── engines/                   # 单引擎全量分册（102 册，一引擎一文件）
│   └── third-party.md             # 第三方工具与依赖（自备）
└── scripts/
    ├── INDEX.md                   # 19 个通用工具：用法 + 何时跑（按阶段排）
    ├── INDEX-BY-ENGINE.md         # 引擎 → 可改的提取器（构建时自动生成）
    ├── INDEX-BY-SCRIPT.md         # 脚本 → 用途 → 出自哪册（反查用）
    ├── *_extract.py …             # 按作品编写的提取器（585 个，改 SRC/OUTDIR 即可复用）
    ├── cpk.py / psarc_extract.py / cdar.py / xp3.py / nsac.py …   # 通用容器工具
    └── scan*.py / renderfont.py …                                  # 探查与字体助手
```

## 环境变量

| 变量 | 含义 | 默认 |
|---|---|---|
| `VNTRANS_HOME` | 工作根目录 | 当前目录 |
| `VN_OUTDIR` | 输出目录 | `$VNTRANS_HOME/提取结果` |
| `SEVENZ` | 7-Zip 路径 | `C:\Program Files\7-Zip\7z.exe` |
| `PROD_KEYS` | Switch `prod.keys` | 脚本同级 `prod.keys` |
| `ZRIF` / `PSVDEC` | PSV 解密参数 / psvdec 目录 | 空 / 脚本同级 `psvdec` |

## 兼容性

| 层面 | 说明 |
|---|---|
| `scripts/` 下的脚本 | 纯 Python，与 Agent 无关，可独立运行 |
| `SKILL.md` + `references/` | 遵循 Agent Skills 通用约定（`SKILL.md` + `name`/`description` frontmatter）。Claude Code、WorkBuddy 等可识别；只支持自有插件格式的工具需少量适配 |

## 隐私与安全

本包**不包含**：解密密钥（Switch `prod.keys` / `title.keys`、PSV zRIF 等）、个人识别信息（用户名、本机绝对路径）、
第三方二进制或源码仓库（hactool / pkg2zip / psvdec / Kuriimu2 / GARbro / innoextract 等，改由
[`third-party.md`](references/third-party.md) 给出获取方式）、游戏资产与已提取的成品文本。

脚本中的路径均从环境变量取值，不写死绝对路径。个别脚本会经 `subprocess` 调用 7-Zip 并清理自己创建的临时目录；
`haruka6_dict.py` 用 `exec` 加载同目录的 `haruka6_extract.py`。除此之外无网络访问、无外部写入。

## 文档

| 内容 | 位置 |
|---|---|
| 规范与流程骨架 | [`SKILL.md`](SKILL.md) |
| **开工第一册：判型** | [`S0-triage.md`](references/S0-triage.md) |
| 一页导航（症状 → 文件） | [`00-index.md`](references/00-index.md) |
| **输出规范全文** | [`00-rules.md`](references/00-rules.md) |
| 解密 / 化け修复 | [`S2-decrypt.md`](references/S2-decrypt.md) |
| 脚本结构 / 记录形状 / 反例 | [`S4-structure.md`](references/S4-structure.md) · [`S4-record-patterns.md`](references/S4-record-patterns.md) · [`S4-false-signals.md`](references/S4-false-signals.md) |
| 解码 | [`S5-basics.md`](references/S5-basics.md) · [`S5-codetable-elf.md`](references/S5-codetable-elf.md) |
| 成行 | [`S6-lines.md`](references/S6-lines.md) · [`S6-typing.md`](references/S6-typing.md) |
| 自检 / 核对 / 完整性 | [`S7-selfcheck.md`](references/S7-selfcheck.md) · [`S7-external-report.md`](references/S7-external-report.md) · [`S7-completeness.md`](references/S7-completeness.md) |
| **收尾（一条命令 + 拆分纪律）** | [`S8-wrapup.md`](references/S8-wrapup.md) |
| 坑册 13 册 | [`pitfalls/`](references/pitfalls/) |
| 各引擎做法 | [`engines.md`](references/engines.md) → `references/engines/*.md` |
| 第三方工具 | [`third-party.md`](references/third-party.md) |
| 通用工具（19 个） | [`scripts/INDEX.md`](scripts/INDEX.md) |
| **按引擎找可改的脚本** | [`scripts/INDEX-BY-ENGINE.md`](scripts/INDEX-BY-ENGINE.md) |
| **反查某个脚本 / 某作品做过没有** | [`scripts/INDEX-BY-SCRIPT.md`](scripts/INDEX-BY-SCRIPT.md) |
| 更新日志 | [`CHANGELOG.md`](CHANGELOG.md) |

## 依赖

第三方工具与密钥不自带，见 [`third-party.md`](references/third-party.md)。

## License

MIT，见 [`LICENSE`](LICENSE)。

## 免责声明

本工具供技术研究，以及对合法拥有的游戏副本做文本提取、LunaTranslator 预翻译文件制作等翻译前置处理使用。不附带任何游戏资源、密钥或受版权保护的文本；提取所得文本的著作权归原作者所有。
