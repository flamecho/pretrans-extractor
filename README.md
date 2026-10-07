# pretrans-extractor

从日文 VN / AVG 游戏的封包资源中取出剧本文本，整理为纯文本，供制作 LunaTranslator 预翻译文件使用。

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB) ![Version](https://img.shields.io/badge/version-1.1.0-blue)

## 简介

日文游戏的剧本通常存放在加密封包里，由自定义字节码承载。本项目做三件事：解包、解密、把各引擎的文本按同一套规则整理出来。整理规则中有一条是固定的：**一个文本框（一次点击）= 一行**。

仓库包含两部分：

- `scripts/` —— 可直接运行的 Python 脚本（容器解包工具 + 各引擎提取器 + 探查助手 + 交付前品检）；
- `SKILL.md` + `references/` —— 一份 Agent Skill，采用**渐进式披露**：主文件只放必守规则与流程骨架，细节按需读分册。

## 用途与边界

输出用于**制作 LunaTranslator 的预翻译文件**，即提供待翻译的日文原文。

本项目只负责提取原文：

- 不制作汉化补丁（不涉及把译文写回游戏、不生成补丁包）；
- 不做译文回填（不处理翻译结果的注入或对齐）。

翻译与后续处理在别的环节完成。

## 支持范围

已整理约 30 种引擎／容器的处理要点。以下为部分条目，完整清单见 [`references/engines.md`](references/engines.md)。

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

python scripts/cpk.py game.cpk out/        # 解 CPK
python scripts/scan_nested.py game_dir     # 逐层扫描，定位含日文的层

# 交付前自检（退出码 0 = 通过）
python scripts/check_text.py "提取结果/XX_全文本.txt" --name 主角名
```

各脚本用法见文件头 docstring 与 [`scripts/INDEX.md`](scripts/INDEX.md)。

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

细则见 [`SKILL.md`](SKILL.md) §0（输出规范）与 [`references/04-verify-and-report.md`](references/04-verify-and-report.md)。

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
├── SKILL.md                       # 主文件：必守规则 + 流程骨架 + 坑索引（先读这个）
├── README.md
├── CHANGELOG.md
├── LICENSE                        # MIT
├── .gitignore
├── docs/release-v1.1.0.md         # v1.1.0 版本说明
├── references/
│   ├── 01-decrypt-decode.md       # 解密 / 解压 / 化け修复 / 官方补丁
│   ├── 02-script-reverse.md       # 脚本结构、消息格式、宏、分支回填、点击语义
│   ├── 03-pitfalls.md             # 全量坑 + 真实返工案例（开工前必读）
│   ├── 04-verify-and-report.md    # 自检 / 外部核对 / 验收 / 报告
│   ├── 05-workspace-and-tools.md  # 工作区、脚本形态、流程约定
│   ├── engines.md                 # 30+ 引擎逐条复用要点
│   └── third-party.md             # 第三方工具与依赖（自备）
└── scripts/
    ├── INDEX.md                   # 脚本 → 引擎 映射
    ├── check_text.py              # 交付前通用品检
    ├── *_extract.py               # 各引擎提取器
    ├── cpk.py / psarc_extract.py / cdar.py / xp3.py / nsac.py …   # 通用容器工具
    ├── scan*.py / renderfont.py …                                  # 探查与字体助手
    ├── koei/                      # Koei CDAR 相关 C# 参考实现
    └── hunex/                     # HuneX MZX0 / mrgd00 解包器
```

## 隐私与安全

仓库内容已做过清理，**不包含**：

- 解密密钥文件（Switch `prod.keys` / `title.keys`、PSV zRIF 等）；
- 个人识别信息（用户名、本机绝对路径、私有目录名）；
- 第三方二进制或源码仓库（hactool / pkg2zip / psvdec / Kuriimu2 / GARbro / innoextract 等），改由 [`references/third-party.md`](references/third-party.md) 给出获取方式；
- 游戏资产（字体库、图集）与已提取的成品文本。

脚本中原先写死的路径均已改为环境变量取值。个别脚本会经 `subprocess` 调用 7-Zip，并清理自己创建的临时 / 输出目录；`haruka6_dict.py` 用 `exec` 加载同目录的 `haruka6_extract.py`。除此之外无网络访问、无外部写入。

## 文档

| 内容 | 位置 |
|---|---|
| 规范与流程骨架 | [`SKILL.md`](SKILL.md) |
| 解密 / 化け修复 | [`references/01-decrypt-decode.md`](references/01-decrypt-decode.md) |
| 脚本结构逆向 | [`references/02-script-reverse.md`](references/02-script-reverse.md) |
| 全量坑与案例 | [`references/03-pitfalls.md`](references/03-pitfalls.md) |
| 自检 / 核对 / 报告 | [`references/04-verify-and-report.md`](references/04-verify-and-report.md) |
| 工作区与工具约定 | [`references/05-workspace-and-tools.md`](references/05-workspace-and-tools.md) |
| 各引擎做法 | [`references/engines.md`](references/engines.md) |
| 第三方工具 | [`references/third-party.md`](references/third-party.md) |
| 脚本索引 | [`scripts/INDEX.md`](scripts/INDEX.md) |
| 更新日志 | [`CHANGELOG.md`](CHANGELOG.md) |

## 依赖

第三方工具与密钥不自带，见 [`references/third-party.md`](references/third-party.md)。

## License

MIT，见 [`LICENSE`](LICENSE)。

## 免责声明

本项目供技术研究，以及对合法拥有的游戏副本做文本提取、LunaTranslator 预翻译文件制作等翻译前置处理使用。不附带任何游戏资源、密钥或受版权保护的文本；提取所得文本的著作权归原作者所有。
