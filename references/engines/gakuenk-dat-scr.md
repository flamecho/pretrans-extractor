# Otomate / Idea Factory 自研「DAT + PAK + SCD」（PSV）

> 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。
> 代表：**学園K -Wonderful School Days- V Edition**（PSV / PCSG00654）／ **ネオ アンジェリーク 天使の涙**（PSV / PCSG01068，变体见文末）。

## 容器链

1. **NoNpDrm zip** → 解出 `PCSG00654/`（含 eboot.bin / sce_pfs / Data）。
2. **PFS 解密**：`<psvdec>/bin/win64/psvpfsparser.exe -i <PCSG00654 目录> -o dec -z <zRIF> -f cma.henkaku.xyz`
   （zRIF 在 `<psvdec>/games.json`；须联网 + 前台；成功判据 `keystone: matched retail hmac`）。
   未解密时 `eboot.bin` / `CORE.DAT` / 连 `.CSV` 都是熵 7.99 —— 一眼可判「还没过第二层」。
3. `Data/CORE.DAT`、`Data/DATA.PAK` 其实都是 **ZIP**（`PK\x03\x04`）。
   - `CORE.DAT` = 普通单文件 zip，内含 `CORE.DAT_`。
   - `DATA.PAK` = **1720 个独立单文件 zip 顺序串联**（每个都自带 central dir + EOCD，故 7z 只认第一个）；
     **每块按 0x200（512 B）对齐**（EOCD 之后补 0 到对齐）。逐块顺序解析 = 可靠。
4. 内层 **`DAT ` 归档**：`[u32 count]` ＋ count × **(name[0x20] + u32 size + u32 offset)** ＋ 数据区。
   ⚠ 字段序是 **size 在前、offset 在后**（用「最后一条 size+off==文件长」验）。
5. 内层文件类型：`.gxt`（Vita 标准贴图）／`.gxp`（shader）／`.vag`（音）／**`.SCD`（剧本，381 个）**／`.LIP`（口型）。
   `DATA.PAK` 成员名带尾下划线（`0000080.DAT_`），**内层名才是真名**（`0000080.SCD`）。

## CORE.DAT_ 关键表（41 条）

`STORYFLOW.BIN` / `CHOICE.BIN`(23 KB) / `CGIDX.BIN` / `EVENT.BIN`(事件名 UTF-8) /
`DATA.IDX`(`PAK ` 头, 1729 条 ×12B) / **`DICT.BIN`(用語辞典 UTF-8)** / `BGMINFO.BIN` / `EYECATCH.BIN` / 字体 `FONT_A/B.gxt` / `KERNING.BIN`。

## SCD 字符串记录（正文 UTF-8）

统一记录：`<u16 len> <len bytes>`（**len 可能含尾 NUL，读后 rstrip('\0')** 即可两者兼容）。
- **旁白**：`fe ff 00 XX 02 00 2d 31 02 00 25 26  <u16 len> <text>`
- **会話**：`0f 00 00 00  <u16 len> char_id("ddd_ddd_ddd")  <u16 len> name  <u16 len> text`
  → **char_id 之后紧跟的短串即名札**（按 §0 丢弃）。
- **選択肢**：`61 00 14 00  <u32 scene_id> <u32 idx> <u32> <u32> <u32>`（20 B payload）→ 指向 `CHOICE.BIN` 的 `(scene_id, idx)` 块。

行内记号：`\` = 框内软换行（**合并**）；`$…$` = **用語辞典词条标记**（去 `$` 留字）；
`%` = 主角**姓**、`&` = 主角**名**、`%&` = 全名（玩家可改名；默认 木野花／沙耶）。

## CHOICE.BIN

`[u32 n_blocks]` ＋ n × `[u32 size][u32 scene_id][u32 idx][u32 n_opts][s32 -1][pad]` ＋ `n_opts × (u32 len + utf8, 4B 对齐)`。
- 164 块 / 352 选项；**153 块由 SCD 的 `61 00` 精确命中**（scene_id = 该 SCD 文件名去前导零，如 100980 ↔ `0100980.SCD`）。
- 剩余 11 块（9 个 5 选项「和谁说话」菜单 + 3035902 的 2 组真实选择）**未被 `61 00` 引用** ⇒ 位置未知，暂置其场景文件末尾。

## DICT.BIN（用語辞典，并入成品末尾）

`[u32 n]` ＋ n × `[u32 size][u32 idx][u32 ?][u32 title_len][title][u32 n_lines]`
＋ `n_lines × (u32 len + utf8, 4B 对齐)`。58 条。**正文按固定行槽切分**（每条 36/40 B），拼接前须 rstrip('\0')。

## 成行要点

- 一次点击 = 一条字符串记录；`\` 合并；`$` 去标记；`%`/`&` inline 换名。
- 名札丢弃（`char_id` 之后紧跟的 ≤12 字短串）。
- 辞典 `【見出し語】解説文` 一行一条，并入末尾。

## 排除

- 1092 个 `.DAT_` 里的 `NNNNNN.gxt` 贴图、`CG/BG/EY/SH*` 贴图、`*_TCH/RANGE.BIN`（触摸区）、`.LIP`、`.vag`、`QuickSynth.xml`。

## 工具

`scripts/gakuenk_extract.py --pak <DATA.PAK> --core <CORE.DAT> --out <txt> [--family 姓 --given 名]`
（内置容器扫描 / SCD 记录扫描 / CHOICE / DICT / 清洗；`--no-dict` 可关辞典）。

---

## 同引擎第 2 作：ネオ アンジェリーク 天使の涙（PSV, PCSG01068）

> 开发 **Koei Tecmo**／发行 **Idea Factory・Otomate**（2017-12-07）。容器链**完全同上**，但**记录层与载体逐作变**。

**源形态不同**：无 `.pkg`，源是已解成 app 目录的 NoNpDrm zip ⇒ 跳过 `pkg2zip`，`7z x` 得 `app/PCSG01068`；
**许可证就在包内** `sce_sys/package/work.bin`（512 B 明文，内容 ID@0x10、klicensee@0x50:0x60）⇒ 无需外部 work.bin。

| 项 | 学園K | ネオ アンジェリーク 天使の涙 |
|---|---|---|
| SCD 数 / 内层 `DAT ` 条数 | 381 / 41 | **527 / 67** |
| 名札 | `<len> char_id("ddd_ddd_ddd") <len> name` | **记录内 `<u16 name_len> \"名前\"`**（`\"\"`=旁白 / `\"&\"`=主角） |
| 记录头 | `fe ff 00 XX 02 00 2d 31 02 00 25 26` | `ff ff ff ff <u16 seq> <u16 kind>` ＋ `02 00 2d 31 <len name> <len text>` |
| 主角宏 | `%`姓 / `&`名 / `%&`全名 | **`&`名（デフォ アンジェリーク）／ `#`愛称（デフォ アンジェ）**；`%`姓 デフォ セリーヌ 但**正文未用** |
| 主角默认名来源 | 脚本内/eboot | **eboot.elf @0x84d34**：`セリーヌ`/`アンジェリーク`/`アンジェ`（ELF 另有 `姓`/`名` 字段标签） |
| 用語辞典 | `DICT.BIN`(58) | **无**；`QUOTE.BIN`(182×8 B，**无文本**)=场景/回想索引 → 非载体 |
| 追加载体 | — | **`DATA.PAK` 内 `LT*.txt`×50 = 角色書簡**（整封并 1 行）＋ **`CORE` 内 `STORYFLOW.BIN` = 497 章題/事件名**（并入末尾） |
| 边框内换行 | `\` | **3 形**：`\`(后接正文) / **`\`+0x08** / `\`+0x09(TAB) |

### ★★扫描器「含控制符整条丢弃」⇒ 静默漏收 41%（最高优先级坑）

`gakuenk.scan_strings` 的 `not any(ord(c)<0x20 and c not in '\n\t' …)` 判定会把**含 `\`+0x08 的整条记录**
当误命中丢弃 ⇒ 本作正文只剩 **21,273 / 应为 37,102（漏 14,141 条 = 41%）**。文本读起来通顺，**极隐蔽**。
**正解**：改为**白名单**——仅当每个控制字节都**紧跟在 `\` 之后**（换行参数）才收；实测只需放行 **0x08**（0x09 已被 TAB 覆盖），零误收。
实现：`scripts/neoangelique_extract.py::scan_strings` / `_ctls_ok`。**任何本引擎作品开工前先做此白名单。**

### 选项 / 成行 / 清洗

- 选项 `61 00 14 00 <u32 scene_id> <u32 idx>` → `CHOICE.BIN`；111 块，内联命中 110，剩 1 块 `(3106,0)` 置 `003106.SCD` 末尾。
- 一行 = 一条 `<len><utf8>` 记录（=一次点击）；框内 `\*` 合并；名札（`^"…"$`，内 ≤16 字）整条丢。
- `&`→アンジェリーク、`#`→アンジェ；U+3000 原文保留（行首尾去）。
- **原文笔误**（缺/错引号）用**整行定值表**修（本作 7 处：`『…」`×2、999999 副本缺 `『`、缺 `（`×1、缺 `「`×3）。
- `999xxx.SCD` 非调试：999000-004=正篇终盘、999050-701=会話トピック、999900-904=カミーユ/双子、999999=あらすじ（与 000000 重复）→ 全收。

**成品**：37,911 行【PASS】。报告 `提取结果/解析报告/[PSV-JP]ネオ アンジェリーク 天使の涙_解析报告.md`。
名札表 120 项，vndb **v21024** 全 12 名 100% 命中。
