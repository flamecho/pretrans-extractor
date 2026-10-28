# HuneX HESL/HESE · **Switch 变体**（文本外置 HDLG）

> 路由见 `../engines.md`；同族共性（HLZS/HESL/HESE/码表）见 `hunex-hesl.md`。

## Starry☆Sky ~Spring Memories~（NS-JP `0100a3d026610000`）—— ★**文本外置，HESE 内无日文**

> 2026-10-19 定案。同族容器（HESL/HLZS/HESE），但**指令流里一个假名都没有**，正文改由独立 `.hdlg` 表承载。

- 容器：`script.heslnk` = `HESL@0x200`（count **174**，条目 `{u32 cksum, u32 off(rel 0x200), u32 decSize, u32 pad}`，
  名字表 `@HESL+0xB20`，数据 `@+0x1060`）；**每个条目都是 `HLZS` 压缩**（`HLZS+ver+encSize+decSize+0x10`，载荷 @0x20）。
- ★判据：**174 个 HESE 解压后 `[ぁ-んァ-ン]` 命中 0**（内联串只有 `max`/`min`/`value` 这类变量名）
  ⇒ 别在这里找台词。HESE 指令=`A0 <op>` 框架（`op 0x2e` 带内联变量名字符串）。
- **正文 ＝ `script_dialog_ja.hdlg`**（`HLZS@0x200` → **`HDLG`**）：
  `HDLG + ver(0x10000) + count + dataOffset + u32 offsets[count]`，字符串 UTF-8 内联，NUL 结尾；
  `script_dialog_en/zhcn/zhtw.hdlg` **只存键名**（`TRANS_W000_0000_0`），未翻译 ⇒ 但它们给出了**逐条对应的键表**。
- 表分区（本作 29,697 条）：`0–756` = UI（`TRANS_M/S/N/MEM*` 键、日期、章題/ED 名、改名提示）；`757–` = 正文
  （`TRANS_W###_####_#` 28,788 条 = **169 个脚本块**，与区间长度逐条相等）。
- 成行：**一条 HDLG 条目 = 一框**；`<br>` = 框内软换行（合并）；`<firstname>/<lastname>` = 主角名宏；
  ★`<firstname2>/<lastname2>` = **第二可改名槽**（本作正文 60 处，默认值未证）。
- 工具：`scripts/sspm_extract.py`。
