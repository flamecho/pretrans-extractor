# Takuyo gss · PSP 变体（étude prologue 〜揺れ動く心のかたち〜 Portable）

> 总表/一句话索引见 `../engines.md`；PSV 册见 `takuyo-gss.md`；
> Switch 册见 `takuyo-gss-switch.md`（SCR 3.00 打包）/ `takuyo-gss-switch-scr2.md`（SCR 2.00 未打包）。

## 作品：étude prologue 〜揺れ動く心のかたち〜 Portable（PSP `ULJM-05252`，2007，Takuyo）

- **源**：`[PSP-JP]étude prologue 〜揺れ動く心のかたち〜.zip` → `E'tude Prologue - ...(v1.02).iso`
  （ISO9660，961,478,656 B）。**zip 无密码、ISO 未加密**，`7z x` 两层直解。
- **容器 ＝ `LSDARC V.100`（与 PSV 册完全同构）**：
  `PSP_GAME/USRDIR/{SCRDATA,SYSDATA,BMPDATA,SE,VOICE}.{BIN,ARC}`。
  `SCRDATA` **683 条全 `isPacked=0`**、offset 链式累加**校验通过**（`off[i+1]=off[i]+size[i]`，`size` 按 `0x800/0x1000/0x8000` 对齐）。
- **脚本 ＝ `SCR 2.00`（与 ひめひび 逐字节同格式）**：`"SCR 2.00" + u32 A + u32 B`，
  指令 `u16 opcode | u8 size | u16 id | operand*`；**683/683 按 size 铺满、零失步**。

### ★★ 本作关键新发现

1. **PSP 的 `PSP_GAME/SYSDIR/BOOT.BIN` 是明文 ELF；只有 `EBOOT.BIN` 是 `~PSP` 加密。**
   ⇒ **本作根本不需跑 pspdecrypt**（对照：Zerodiv 系 PSP 作两者皆 `~PSP`）。
   判断法：`head -c4` → `\x7fELF` 即明文；`~PSP` 才需解密。
2. **明文 ELF 内含引擎的「地图事件脚本表」** —— 507 个 **4 字节对齐、NUL 填充的 CP932 脚本名**，
   起始 `0x6edf8`，**紧邻原生函数名字符串 `GET_SCRIPT_NAME`**（其前是 `EVENT_CHECK`/`NOW_LOAD_OFF`）。
   解析法：从 `0x6edf8` 起读 NUL 结尾串，按 `(len+1+3)//4*4` 步进；表尾是 `HIT14_B`，之后转为 `*.BMP` 名表。
   ⚠ **名表内存在小写变体**（表里 `S_MDR_01_a` vs SCRDATA 里 `S_MDR_01_A`）⇒ 匹配须**大小写不敏感**。
3. **本作 opcode 集比 ひめひび/Cafe Cuillere 窄**：**无 `0xfc`（`%s` 消息）、无 `0xf0`（扉文/标题卡）、无注音 ruby**。
   上屏文本只有 `0x5a`（正文，31,228）＋ `0x5c`（选项 `(u32 个数, "显示文本,FLAG", …)`，355 op）。
   替代 `0xf0` 的「场转点」是 `0x5a` 里的 `………\n………………\n………………………`（长点线，仍是一框一击）。
4. **说话人＝`0xfd` 槽 `0c02`**（本作 30,248 次），随后 `0x1e` 调 `PRG_NAME.SCR/NAME` 渲染成 `【名】`；
   `PRG_NAME` 的模板是 `0xfd '@y【'` ＋ 名 ＋ `0x107 '】@w@'`。**提取按 SKILL.md §0 整体丢弃、不加前缀**。
5. **串内控制码**：`\n` 939 处 / `\c` 134 处 ＝ **框内换行（都是合并）**；`\u` 5 处 ＝ 输入待ち（删）；
   `#w0#` ＝ 待ち（删）。⚠ **`\c` 出现在句读边界（`……\cあれ、`），别误判为独立点击**：同一 `0x5a` 内即为同框 ⇒ 合并。
6. **非线形（日历/学园模拟）⇒ 调用图覆盖不全**：
   `0x1e/0x1d` 从 `AUTOEXEC` 只到 `PRG_OPENING`（OP 链）/`PRG_ENDING`（EP 链）/`PRG_MESS`（朝夜），
   `M_*`/`S_*`/`F_*` 等剧情事件**由 `GET_SCRIPT_NAME` 依上表（2）动态派发**。
   ⇒ **顺序认定：① `PRG_OPENING` 的 `0x1e` 调用序（OP_TAT_01…18 → OP_HTM_01…18，含链中插入的 `M_14`/`M_41`、`F_03`/`F_11`/`F_20`）；② BOOT 事件表序（507）；③ `PRG_ENDING` 调用序（EP_*/END_*）；④ `PRG_MESS`；⑤ 其余按 LSDARC 索引序** + `EXCLUDE` 表。
7. **系统脚本的例外**：`PRG_MESS` 虽是系统脚本，却有 **18 条真台詞**（地图指令时的主人公独白
   「アルバイト行こう」「さて、帰るか」）⇒ **不可整脚本剔除**；反之 `PRG_BG` 的 3 条全是调试提示＋转场点 ⇒ 剔。
   **判据只能用「逐条看内容」，不能凭脚本名。**
8. **双主人公、固定名**：郡司 達也 / 佐伯 瞳（vndb v1893 双 Protagonist）。
   正文里两人名字**全部字面内联**（599 / 580 次），全库 **无 `%s`、无名称宏、`INIT`/`PRG_MAP` 无名前入力例程**
   ⇒ **固定名，无输出层改名**。名札表 55 种，vndb 12 主役全中。
9. **原文瑕疵**：① 全角 `（` 配半角 `)` 2 处（`M_SAN_TAT_10`、`S_SIN_02_A`，后者另带衍字 `」`）→ **整行定值表修**；
   ② 半角 `､`(U+FF64，源字节 `0xA4`) 6 处用在どもり处 ⇒ 归一为全角 `、`
   （判据＝**同语料全角同型**「そ、そう…」116 处 vs 半角「そ､そうね」1 处）。

### 排除表（19 个脚本，逐条核实无正文）

`AUTOEXEC` `INIT` `INITFLG` `MAIN`(调试菜单) `PRG_BG` `PRG_DEBUG_NOMAL/VOICE/GRAPH` `PRG_MAP`
`PRG_OPENING`(跳过提示 UI) `PRG_ENDING` `PRG_NAME` `PRG_STAND` `PRG_DATE` `RELOAD` `YURASHI` `RUNBLE`
`SELECT` `SELECT2`。另 `MAIN` 引用的 `tougou.scr`（CERO 分级合辑）**包内不存在**。

### 用語辞典

**无独立载体**（容器内无文本类 dat/bin；全库检索 `【`/`用語`/`豆知識` 仅命中台词）。
唯一两条内联豆知識注記在 `M_02`/`M_16`（`注意：見出し語。解説文。`）——**随术语即时上屏，按不改写保留原位**。

### 工具 / 报告

- `scripts/etude_extract.py`（复用 `himehibi_lsdarc.py` ＋ `himehibi_disasm.py`）：
  自带 BOOT 事件表解析、`EXCLUDE`、分相 `ORDER`、`TEXT_PATCH`（键必须唯一命中，否则中止）、`PUNCT_FIX`。
  工作目录可用环境变量 `ETUDE_DIR` 覆盖（默认 `../_work_etude/iso/PSP_GAME`）。
- 成品 `提取结果/étude prologue 全文本.txt`（**31,917 行**＝正文 31,212 ＋ 选项 705）；报告 `提取结果/解析报告/étude prologue_解析报告.md`。

---

## 作品 2：Little Aid ポータブル（PSP）

**⇒ 见 `takuyo-gss-psp-littleaid.md`**。

> ★ **作品 3：星色のおくりもの**（PSP 第 3 作，`SCR 2.00` 未打包，21,167 行）⇒ 见 **`takuyo-gss-psp-hoshiiro.md`**。

> ★ **作品 4：for Symphony ポータブル**（`ULJM05258`，v1.01 补丁版）⇒ `takuyo-gss-psp-symphony.md`。
> ★ **作品 5：怪盗アプリコット ポータブル**（2007-09 压盘，PSP）—— 同族 `LSDARC V.100` ＋ `SCR 2.00`，
> 但**首见 `0xfc` ＝ 正文＋名变量**：串后紧跟 2 B 槽 id（**小端**，`'3002'`＝`0x230` 名／`'3c02'`＝`0x23c` 姓），默认值只在
> `AUTOEXEC/INIT` 写入；名札 `0xfd (6,f805)` → 槽 `0x5f8`（源 `0x608` 带空格名／字面串）。**节序不可按字节序**
> （`ANZU00` 字节序 F,G,H,I,J,A…E），须按调度脚本 `0x1e` 调用序。成品 15,727 行；详见该作的解析报告与
> `提取结果/解析报告/怪盗アプリコット_解析报告.md`。
