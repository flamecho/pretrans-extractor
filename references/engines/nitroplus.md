# Nitroplus NPA / NSS

> 路由 / 一句话索引见 `../engines.md`。

## Nitroplus NPA / NSS —— Lamento -BEYOND THE VOID- (W10, PC；NITRO CHiRAL 2006)
> 来源：`<原始 dump 目录>/[PC-JP]Lamento -BEYOND THE VOID- Windows 10 Support Edition/L_W10.rar`
> (RAR5 **头部加密**，密码 `Bought_by_XD92_Only_For_Anime-Sharing_2025` ← 同目录 42B `新建文本文档.txt`)
> 成品 `提取结果/Lamento -BEYOND THE VOID-_全文本.txt`（37,310 行）。工具 `scripts/lamento_extract.py`。
> ⚠️ **规范（用户 2026-10-07 定）：只取「显示用」文本 ⇒ `SetBacklog` 不取**（日志专用；含 6 行唯一文本被有意舍弃，见下）。

- **外层**：RAR5（`Encrypted = +`，7z 不带密码连文件名都列不出）。只需解 `nss.npa`(1.7MB)/`system.npa`(2.5KB)/主 exe，CG/voice/sound ~1.9GB 免解。
- **归档 `.npa`（NPA\x01）**：`"NPA\x01"` + u16 0 + u8 0 + **i32 key1 + i32 key2** + u8 compressed + u8 encrypted + i32 total + i32 folder + i32 file + i64 0 + u32 dir_size；entry 从 **偏移 41** 起，每项 `i32 nameLen + name + u8 type + i32 folderId + u32 off + u32 size + u32 unpacked`（步长 `4+nameLen+17`）；`entry.Offset = dir_size + off + 41`。
- **索引名解密**：`raw[x] += DecryptName(x, i, arc_key)`，其中
  `key = (0xFC*x - b(arc_key) - b(curfile)) & 0xFF`，`b(k)=k>>24 + k>>16 + k>>8 + k`（**注意用带符号 32 位**）；
  `arc_key = key1+key2`（LAMENTO）或 **`key1*key2`（其余全部标题）**。名字解出可读即证明走乘积分支。
- **★ 内容加密（本作实证）**：前 `0x1000(+nameLen)` 字节 `buf[i] = key_table[buf[i]] - key - i`（LAMENTO 则无 `-i`），
  `key = ((NameKey - Σndecrypted_name) * nameLen [非LAMENTO: + arc_key, * unpackedSize]) & 0xFF`。
  `key_table` = 由 `Order` 生成的 256 置换（算法见 GARbro `ArcNPA.GenerateKeyTable` / 本仓库 `lamento_extract.py::gen_table`，含 `BASE_TABLE`）。
- **25 套预置方案（NpaTitleId: NotEncrypted/CHAOSHEAD…LAMENTO/SWEETPOOL/…/TOTONO(需再变换)/HANACHIRASU）**
  存于 **GARbro `GameData/Formats.dat`**（头 `GARbroDB` + u32 + zlib；内容是 .NET **BinaryFormatter(NRBF)**）。
  解析法：自写 MS-NRBF 读取器（记录 0..17；类的 member 值为 **Record**（含 String 型！）而非 inline 字符串；
  ClassWithId 引用元数据，enum 被序列化为带 `value__` 的类）。提取出 `EncryptionScheme{TitleId,NameKey,Order}` 25 套。
- **★ 方案认定法**：对每个候选方案试解 entry#0，判定式 = **能否还原合法 zlib 流**（0x78..）。本作唯一命中 **DJANGO**
  （TitleId=7, NameKey=0x87654321, Order=`ee…ee 1e4e66b6`(20B)）→ 解密首行 `#base_path "../"`。
  ⇒ **W10 版 Lamento 的 nss.npa 用的是 DJANGO 方案，不是 LAMENTO**。
- **脚本 `.nss`（Nitroplus 自研 = NScripter 派生）**：**cp932，CRLF**。语法含 `#base_path/#include`、`scene/chapter/cut{}`、`call_chapter/call_scene/call_cut`、`function`、`{Command(...);}` 行内演出、`//` 行注释。
- **文本载体**：
  - `<PRE boxNN>` … `</PRE>` = **一个文本对象 = 一次 `TypeBegin("@boxNN","@textNNN")` 显示**；内部 `[textNNN]` 为标签行。
  - 行内：`<voice name="人名" class=.. src=..>`（语音挂点，含说话人名）、`<RUBY text="…">本体</RUBY>`（注音）、`<FONT>/<I>` 标记、`<?>`。
  - **`<K>`/`<k>`/`<Ｋ>` = クリック待ち（一次点击）**；`CreateText("extextNNN",…,"文本")`（扉文/歌詞）、`SetChoice02/03("A","B"[,C])`（选项）、`TextMirror01/02` 亦含**显示用**文本。
  - ⚠️ **`SetBacklog("…")` = 日志专用 ⇒ 不取**（规范「只要显示用的」）。其文本经 `CreateText`/`extext` 另行上屏；
    两处常改稿不同步（实证 `la0002` 旅人のうた `五本/陽射し/砕け散る`(显示稿) vs `５本/陽光/砕け散った`(日志稿)）⇒ 收入会造成「差一两个字的重复行」。
  - ⚠️ **整块被 `//` 注释掉的 `<PRE>` = 作者废弃的差分/草稿，必须剔除**（否则巨量串行）。⚠️ 有**闭合括号缺失的坏标签** `[text063d`（无 `]`）→ 标签剥离须容许。
- **「一次点击 = 一行」落地**：`<PRE>` 内**空行 = 消息分隔**，`<K>/<?>` = 显式点击；⇒ **按「空行 或 K」切分，段内连续行合并为一行**。
  （据此跨行台词 `「そりゃ……、\n　自分が一番大事ってことか？」` 正确合并；而空行分隔的叙述行各自成行。）
- **顺序**：`la0000` 为纯路由（无文本）；正篇按 `la/lb/lc + 4桁号` 数字序 = 剧情顺序（`la`=第一部 8,769 行 / `lb`=第二部 10,758 行 / `lc`=第三部 17,738 行）；
  路线差分 `…as##/ba##/ra##` 紧随父文件。`extra_rec_*` 仅是 `call_chapter` 跳进正篇（本身 0 行）。
- **主人公**：**コノエ（固定名，无改名机制 → 无名字宏）**，成品中出现 5,573 次。人名全部与 **vndb v432** 一致（标准 cp932，无字体替换槽）。
- **复用资产**：`scripts/npa_nrbf.py`（MS-NRBF / .NET BinaryFormatter 读取器，解析 GARbro `GameData/Formats.dat` 取方案）
  + `scripts/npa_schemes.json`（Nitroplus NPA 全部 **25 套** 预置方案 `{TitleId,NameKey,Order}`）→ 后续任何 NPA 作品可直接换方案复用。

---
