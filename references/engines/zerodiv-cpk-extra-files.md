# Zerodiv 自研 ADV —— CPK 内 `event.enc` **之外**的文件（用語辞典 / 他作遗留 / 系统数据）

> 容器与脚本见主册。
> ⚠ **教训**：只出 `event.enc` 会漏掉**用語辞典**（它另存为 CPK 根的 `termItem.dat`）——交付前必查本节。

## 8. CPK 内 event.enc 之外的文件（**必查，别只看 event.enc**）

| 文件 | 内容 | 处理 |
|---|---|---|
| **`termItem.dat`** | **用語辞典**：**N × 322 B** 定长记录 = `見出し語 32 B` ＋ `読み 32 B` ＋ `解説`（`01 <索引1B>` 起头、条内 `\n`）。無印 **108 条** | ✅ **按规范并入成品末尾**（`【見出し語】解説文` 一行一条、不带读音、换行合并）→ `scripts/termdict_extract.py` |
| `termCategory.dat` | 8 个分类标签（語録/人名/土地名/道具名/基本/応用/解説） | ❌ 非条目 |
| `npc_album.dat`・`book.dat`・`text/TextDataEx.bin` | **他作遗留**（ドラッケン学園/ダンジョン/呪文/パーティー） | ❌ 不收（同铁律 12） |
| `table.enc`（道具説明）・`text/TextData.bin`（系统 UI）・`event/tutorial.dat`（教程）・`event/flag.dat`（フラグ名）・`startDebugInfo.txt` | 系统/UI・内部 | ❌ 不收（§0） |

**归属判定法（不靠猜）**：对该文件统计「**本作固有词** vs **他作词**」词频（此例：幕末詞 63 / 他作詞 0 ⇒ 本作；0/52 ⇒ 他作遗留）。
⚠ 条目型文件（dat/bin）多为**定长记录** ⇒ 先算 `len(dat) % N` 找整除的记录长。

- 名字字库（`0x31`/`0x20`）。

## 7. 工具与产物

| 工具 | 用途 |
|---|---|
| `scripts/cpk.py` | UMD.CPK 解包 |
| `scripts/lzo1x.py` | **LZO1X-1 解压**（`lzo1x_decompress`） |
| `scripts/urakata_extract.py` | 提取器（**已参数化**）：解压 → 按 cmd 提文本 → 成行 → 清洗 → 输出 UTF-8 BOM/LF。
  用法 `python scripts/urakata_extract.py <out1 目录> <成品.txt> [urakata\|akatsuki]`（差别仅 `OPCODES`/`DEBUG_KW` 两张表） |

| `pspd/pspdecrypt.exe` | `~PSP` 解密（放工作缓冲目录） |

产物（均 UTF-8 BOM + 纯 LF，句末标点 96.9%）：
- `提取结果/[PSP-JP]裏語 薄桜鬼_全文本.txt` = **33,254 行 / 804,206 字**（`_work_hak/`）
- `提取结果/[PSP-JP]裏語 薄桜鬼 ～暁の調べ～_全文本.txt` = **35,831 行 / 929,719 字**（`_work_ake/`）
报告：`提取结果/解析报告/裏語薄桜鬼_解析报告.md`、`裏語薄桜鬼_暁の調べ_解析报告.md`。

**已知瑕疵（原文如此，未改写）**：两作**同为**「行内引号不配对 4 行」＝**3 处缺 `」` ＋ 1 处多 `」`**（净差 2）；
已逐字节确认（后续指令为 `0x31`/`0x36`/名札，无被丢文本块）。逐行清单见两作解析报告。

## ★ 台詞バリアント機構

同一句在脚本里**并排存多版**（默认名↔宏/代名詞、汉字↔平假名表记；928 对中仅称呼差异 532 对）。
判据（三条）＋ 分类 ＋ 处置口径 → **详见 `engines/zerodiv-talks-variant.md`**。
