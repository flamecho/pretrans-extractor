# pretrans-extractor

日文 VN / AVG 文本提取工具与 Agent 技能，收录 PC、PS2、PSP、PSV、Switch 的资源解析方法和提取脚本。
输入为游戏资源、解包目录或光盘镜像，输出为 LunaTranslator 预翻译所需的日文原文及解析报告。

Python 3.10+ · [MIT 许可](LICENSE) · [版本记录](CHANGELOG.md)

## 使用方式

### Agent 技能

将仓库目录安装到 Agent 的 skills 目录，目录名为 `pretrans-extractor`。入口为 [SKILL.md](SKILL.md)。
提取任务中指定资源路径、提取范围和输出目录；Agent 按格式文档选择工具，处理姓名、动态文本及显示边界，并核对结果。

### Python 工具

在仓库根目录运行。先识别目录或主要资源文件：

```bash
python scripts/identify.py game_dir
python scripts/identify.py game.cpk
```

根据 [引擎与格式索引](references/engines/index.md) 核对格式，再从 [格式与脚本](scripts/by-engine.md) 或 [脚本用途](scripts/by-script.md) 选择实现。
例如，CPK 容器可这样解包：

```bash
python scripts/cpk.py game.cpk unpacked
```

解包后，对内部脚本继续判型并提取文本。按作品编写的驱动需核对资源版本、路径和参数；依赖见 [第三方工具](references/third-party.md)。

提取完成后检查文本：

```bash
python scripts/check_text.py output.txt
```

`--report` 用于核对已有解析报告。字符、版式检查与资源覆盖核对见 [验收](references/verification.md)。

## 输出约定

- 收录正文、剧情选项及叙事资料；媒体文字按提取范围处理。
- 文本使用 UTF-8 BOM、LF，无空行，保留日文原文。
- 每次点击新增文本一行，合并同次显示的排版换行；同页多次点击另保留整页合并行。
- 按显示调用关联名札、姓名和动态文本，保存解析依据及覆盖情况。

完整规则见 [输出规范](references/output.md)、[姓名与宏](references/names-and-macros.md) 和 [成行](references/layout.md)。

## 文档入口

| 内容 | 文档 |
|---|---|
| 提取流程与问题定位 | [文档导航](references/index.md) |
| 引擎及格式，包括 Unity、CHD 和原始镜像 | [引擎与格式索引](references/engines/index.md) |
| 字节码、记录结构与显示调用 | [脚本结构](references/script-structure.md) |
| 编码、字体码表与控制序列 | [解码](references/decode.md) |
| 通用工具及命令参数 | [脚本索引](scripts/index.md) |
| 外部工具及 Python 依赖 | [第三方工具](references/third-party.md) |

引擎册按共通结构和可识别的格式变体组织。作品参数、执行结果及处理状态保存在各任务的报告与工作记录中。

## 运行配置

`VNTRANS_HOME` 指定工作目录，默认使用当前目录。部分脚本另读取 `VN_OUTDIR`、`SEVENZ`、`PROD_KEYS`、`ZRIF` 或 `PSVDEC`，具体含义以脚本为准。
解密驱动从环境变量读取专用参数，值为 32 个十六进制字符（16 字节）：

| 驱动 | 环境变量 |
|---|---|
| `handsome_updraw.py`、`handsome_bktr.py` | `VN_HANDSOME_BASE_KEY_HEX` |
| `mist_romfs.py` | `VN_MIST_SECTION_KEY_HEX` |
| `redbell_romfs.py` | `VN_REDBELL_SECTION_KEY_HEX` |
| `senjyushi_extract.py` | `VN_SENJYUSHI_TITLE_KEY_HEX` |
| `ukronia_kaek.py` | `VN_UKRONIA_KEY_AREA_HEX`（加密的 key-area 槽） |

平台工具、解密密钥和许可证参数单独配置。
