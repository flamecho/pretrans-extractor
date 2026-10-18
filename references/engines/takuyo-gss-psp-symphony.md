# Takuyo gss · PSP 变体 4（for Symphony ～with all one's heart～ ポータブル）

> 总表/一句话索引见 `../engines.md`。
> 同族其余：`takuyo-gss.md`（PSV）／`takuyo-gss-switch*.md`（NS）／`takuyo-gss-psp.md`（étude）／
> `takuyo-gss-psp-littleaid.md`／`takuyo-gss-psp-hoshiiro.md`。

## 作品：for Symphony ポータブル（PSP `ULJM05258`，v1.01，2007，Takuyo／vndb v2628）

- **源**：`[PSP-JP]For Symphony ~With All One's Heart~.zip` → 裸 ISO `For Symphony - With All One's Heart Portable (Japan) (v1.01).iso`（1,072,136,192 B）。ISO9660，**未加密**，`7z x` 两层直解。
- **容器＝`LSDARC V.100`**：`USRDIR/{SCRDATA,SYSDATA,BMPDATA,SE,VOICE}.{BIN,ARC}`。
  `SCRDATA` **1,402 条全 `isPacked=0`**，偏移链校验通过（`end==len(BIN)`＝32,990）。
- **脚本＝`SCR 1.10`**（与 Little Aid 同版本）：`u16 opcode｜u8 size｜u16 id｜operand*`。
  **1,402/1,402 按 `size` 精确铺满、零失步**（直接复用 `himehibi_disasm`，`start=16`）。
- **`SYSDIR/BOOT.BIN`＝明文 ELF**（`\x7fELF`），`EBOOT.BIN` 才 `~PSP` ⇒ 本作不需 pspdecrypt。
  ELF 内**无脚本名表**（只有 `OBJ/MAN_START.SCR` / `OBJ/WOMAN_START.SCR` 两条入口串）。

### ★★ 本作关键点

1. **双主人公、开局选性别**：`MAN_START.SCR` / `WOMAN_START.SCR` 是两条唯一入口，共用同一批内容脚本。
   同一存档可玩男女两版 ⇒ **全文本＝男线全文＋女线全文**（两线剧本文件互不重叠，见 §3）。
2. **名字默认值块在 ELF**：`藤井`（姓）／`和真`（男名）／`悠希`（女名）；另有 `名前：%s %s`、
   `%s　%s` 等拼接格式串，佐证「姓＋名」两段式输入。
3. **两个名字槽**：**`0c02`＝名、`2002`＝姓**。判据三条（互相独立）：
   ① `"%s%s"` 的槽序为 `[2002,0c02]` ⇒ 姓在前（`藤井和真`）；
   ② 只挂 `2002` 的上下文全是 `%sさん／%s君／あの…%sさん`（35/31/18 次）；
   ③ 只挂 `0c02` 的上下文全是 `%s先輩／%sセンパイ／%s？／ねえ、%s。`（呼び捨て）。
   ⇒ 交付按路线填默认名（男线→和真、女线→悠希），姓恒为 `藤井`（1395 行）；`0xfc` 共 2,908 条。
4. **剧本名＝路线×角色×季节四维**：
   `P_`=春、`S_`=夏、`A_`=秋、`W_`=冬；字母码＝角色（**男线 `AA`–`EE`＝ヒロイン5人、
   女线 `FF`–`JJ`＝攻略対象5人**；`ME`/`FE`＝男/女线共通追加シーン）。
   `ED_AA`–`ED_EE`＝男线5结局，`ED_FF`–`ED_JJ`＝女线5结局。
5. **顺序只能取分派表**（引擎自身表）：
   男线 `M_SPRING`(→P_) → `M_SUMMER`(→S_) → `M_<c>_AUT`(→A_c) → `M_<c>_WIN`(→W_c) → `ED_c`，c=AA..EE；
   女线 `W_SPRING` → `W_SUMMER` → `W_<c>_AUT` → `W_<c>_WIN` → `ED_c`，c=FF..JJ。
   ⚠ **`DEBUG.SCR` 连到全部脚本**，从 `MAN_START` 做 DFS 会把女线一起吞掉（两路 DFS 1375/1377 重合）
   ⇒ **按表逐张取，不递归**。
6. **文本 opcode**：`0x5a` 正文（36,675）／`0xfc` 带 `%s` 正文（2,908）／`0x5c` 选项（全 412 组 1,077 串，剔除 `DEBUG` 94 组后实用 **318 组 808 串**）。
   **无 `0xf0`（扉文/标题卡）**，**无注音 ruby**，串内控制码只有 `\n`（14,659，框内换行→合并）与
   `\c`（62，删）；无 `@` 系。
7. **选项串自带 `『…』`**（如 `『一緒に学校に行く』,R02`）⇒ 引擎按原串绘制，**保留引号、不剥**。
8. **孤儿脚本＝カットシーン**：20 个有文本的脚本零引用（`0x1e/0x1d` 全为静态（script,label）串；
   另做原始字节搜名亦 0 命中）——`P_AA00/P_AA32/P_AA33/P_BB06/P_BB34/P_CC42/P_GG01_1/P_GG35/P_GG36/P_HH19/P_HH33/P_JJ17/S_EE11/S_II03_5/W_JJ07_2/W_JJ15`（合计 **268 行**）。
   按「未上屏不收」剔除，报告单列（其中 P_AA00 是另一版开场闹钟独白）。

### 排除表（17 个系统脚本，逐条核实无正文／仅调试）

`AUTOEXEC` `AUTOSELECT` `FADE` `INIT` `LOOP` `MAIN` `NAME` `OPTION` `RELOAD` `SELECT` `SOUND`
`STAFF` `YURASHI` `MAN_START` `WOMAN_START`（均 0 条正文）；
`DEBUG`（10 条＝性別/角色选择调试菜单＋`■■夏へ■■` 等调试选项 94 组）、
`SETEST`（78 条＝SE 试听名）⇒ 剔。

### 用語辞典 / 豆知識

容器内无文本类 dat/bin（`SYSDATA`＝2 个 PGF 字体）；成品全库 `【`＝0，`用語`／`辞典` 各仅 1–2 次且均在上屏台词里
⇒ **无辞典载体**。

### 工具 / 报告 / 重跑

- `scripts/fsymph_extract.py`（复用 `gss_lsdarc.py` ＋ `himehibi_disasm.py`）：
  分派表定序＋路线判归属＋按路线填名槽；旁文件 `_work_fsymph/scripts.txt`（每脚本 路线/行数）。
- 重跑：
  `python scripts/fsymph_extract.py -o "提取结果/[PSP-JP]for Symphony_全文本.txt"`（默认读 `_src_fsymph/iso/PSP_GAME/USRDIR`）
- 成品 `提取结果/[PSP-JP]for Symphony_全文本.txt`：**40,035 行**（正文 39,227 ＋ 选项 808）
  ＝男线 21,348 行／720 脚本 ＋ 女线 18,687 行／621 脚本。
- 报告 `提取结果/解析报告/[PSP-JP]for Symphony_解析报告.md`。
