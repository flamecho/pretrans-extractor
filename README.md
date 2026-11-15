# pretrans-extractor

日文 VN / AVG 文本提取工具与 Agent 技能，支持 PC、PS2、PSP、PSV 和 Switch。
输入游戏资源、解包目录或光盘镜像，输出预翻译原文及解析报告。

Python 3.10+ · [MIT 许可](LICENSE) · [版本记录](CHANGELOG.md)

## 使用

作为技能使用时，将仓库安装到 Agent 的 skills 目录，目录名为 `pretrans-extractor`。入口为 [SKILL.md](SKILL.md)；提取任务指定资源路径、范围和输出目录。

直接运行工具时，从仓库根目录调用。先识别主要资源，再按格式选择实现：

```bash
python scripts/identify.py game_dir
python scripts/cpk.py game.cpk unpacked
```

[通用脚本](scripts/index.md)保留共通工具；[作品专用脚本](scripts/works.md)只收录解包和最终文本提取入口，并标注适用作品与平台。
按格式查找实现见[格式与脚本](scripts/by-engine.md)。入口所需解析模块集中在 `scripts/_lib/`。

作品脚本须核对资源版本、路径和参数。提取完成后可运行通用品检：

```bash
python scripts/check_text.py output.txt
```

字符、版式与覆盖核对见[验收](references/verification.md)。

## 输出

- 收录正文、剧情选项和叙事资料；媒体文字按提取范围处理。
- UTF-8 BOM、LF、无空行，保留日文原文。
- 每次点击新增文本一行；同次显示的排版换行合并，同页多次点击另保留整页合并行。
- 姓名、动态文本和显示边界按调用关系解析，保存依据和覆盖情况。

完整约定见[输出规范](references/output.md)、[姓名与宏](references/names-and-macros.md)和[成行](references/layout.md)。

## 文档

| 内容 | 入口 |
|---|---|
| 提取流程 | [文档导航](references/index.md) |
| 引擎与格式，包括 Unity 和光盘镜像 | [格式索引](references/engines/index.md) |
| 字节码、记录及显示调用 | [脚本结构](references/script-structure.md) |
| 编码、字体码表和控制序列 | [解码](references/decode.md) |
| 外部工具及依赖 | [第三方工具](references/third-party.md) |
| 单作产物清理 | [工作区规范](references/workspace.md#收尾与维护) |

引擎册保存共通结构及可识别的变体。作品参数、结果和状态保存在对应报告与工作记录中。

## 配置

`VNTRANS_HOME` 指定工作目录，默认当前目录。部分入口另读取 `VN_OUTDIR`、`SEVENZ`、`PROD_KEYS`、`ZRIF` 或 `PSVDEC`，以脚本参数为准。
Node.js 用于 `.cjs` 入口及内部 Tyrano parser 调用；ASAR 解包需要 `@electron/asar`。`NODE` 可指定 Node 可执行文件。

以下专用解密参数从环境变量读取，值为 32 个十六进制字符（16 字节）：

| 入口或内部模块 | 环境变量 |
|---|---|
| `handsome_updraw.py`、`_lib/handsome_bktr.py` | `VN_HANDSOME_BASE_KEY_HEX` |
| `mist_romfs.py` | `VN_MIST_SECTION_KEY_HEX` |
| `redbell_romfs.py` | `VN_REDBELL_SECTION_KEY_HEX` |
| `senjyushi_extract.py` | `VN_SENJYUSHI_TITLE_KEY_HEX` |

平台工具、密钥与许可证参数单独配置。

发行文件由 [manifest.json](scripts/manifest.json) 明确列出；新增、待确认和中间脚本不会自动收入后续发行版。
