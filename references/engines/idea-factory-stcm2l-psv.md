# STCM2L —— PSV 侧 · **UTF-8 系**（变体 A＋C）

> 路由见 `../engines.md`。
> 共同点：容器均为 **CRI CPK**；指令 = `[u32 is_call][u32 opcode][u32 nparams][u32 length]` ＋ nparams×`[p0,p1,p2]` ＋ data；
> 字符串参数＝指令内局部指针 → `[0][L/4][1][L][text][pad]`（c==1、b==L/4 为签名）。
> **但各作 opcode 体系 / 文本编码 / 换框机制完全不同，务必分开看。**
> **PSV 六变体**：A Norn9（UTF-8＋逐文件 Δ）｜B RE:VICE[D]（CP932·固定 opcode）｜C PsychicEmotion6（UTF-8·近无 Δ）｜D ROOT∞REXX（CP932·固定 opcode＋内联记录）｜E MARGINAL#4 IS（CP932·内联＋三种选项表）｜F MARGINAL#4 RTG（UTF-8·固定 opcode·内联·**选项文本在指令外**）。
> **CP932 系（B＋D＋E）见 `idea-factory-stcm2l-psv-cp932.md`；本册只存 UTF-8 系（A/C/F）。**
> ⚠ **同系列续作可能换字符串编码**：E（IS, 2014, CP932）→ F（RTG, 2017, UTF-8）＝同一发行商、同一 STCM2L 家族、**编码不同**。

---

## A) Norn9 ～Norn+Nonette～ Act Tune（PCSG00833）—— **逐文件 opcode 平移 Δ**

- **字符串编码 = UTF-8**。
- **★★ 每文件 opcode 有常量平移 Δ（本作最大的坑）**：导入函数 ID 整块平移（Δ = 0x10 的整数倍；
  本作 Δ ∈ {0, ±0x10, 0x30, 0x40, 0xe0, 0x120, 0x150}），**但 builtin（`0x1f4` 等换框 / `0x6` goto / `0x3` Mif / `0` / `0x11` / `0x12`）不动**。
  **Δ 检测法＝取「含日文串且平均长度最大（去噪）的 opcode」为 text_op，Δ = text_op − 0xcf9c**
  （用平均长度而非计数：5001 类文件正文极少、flag 串反而更多，计数会选错）。
- 归一化（Δ=0 基准）：`0xcf9c`=push 文本 / `0xd698`=push 人名 / `0xe090`=选项（p0=文本,p1=目标标签）/
  `0x236c`=章题标识 / `0x5414`·`0x4b24`·`0x4cfc`·`0x4ed4`…=flag。
- **换框 = builtin `0x1f4`**（连续 `0xcf9c` 合并成一行）。
- **互斥分支同点击多版本**：`if/else` 两版相邻排放、以 `goto`(0x6) 分隔；「then 版」的 `0x1f4` **紧跟 `goto`**。
  ⇒ 规则：`goto` 断「段」；`0x1f4` 若下一条是 `goto` 也只断段，否则断「点击」；同点击多段取一（优先无 `#Name[`，再取最长）。
- 变量：`#Name[1]`→**こはる** / `#Name[2]`→**深琴** / `#Name[3]`→**七海**（三名可改名女主；占位符版与直写版并存可互证）；`#Scale[…]` 丢。
- **每文件开头 5 行共通导入**（`プロローグに新たな選択肢が追加されました`＋4 行世界观）逐文件重复 88 次 ⇒ 只留一次置全文最前。
- SYSTEM.cpk `dbDictionary.gbin` = **薄桜鬼遗留术语表**（无本作词条）⇒ 整体排除；`script/init/*.DAT` ×7 仅 flag ⇒ 排除；GAME.cpk 全为图像。
- 容器：NoNpDrm zip → `psvpfsparser -z <zRIF>` → `data/STORY.cpk` → `SCRIPT/*.DAT`×88。
- 工具：`scripts/norn9_extract.py`（自包含；自动检测 Δ/text/name/opt）。

---

## C) PsychicEmotion6（PCSG00815，2016 Otomate×IF）—— **UTF-8、无逐文件 Δ 平移（仅 Δ∈{0,−0x10}）**

- 容器：NoNpDrm zip → `psvpfsparser -z <zRIF> -f cma.henkaku.xyz`（**前台运行**，否则假报 `expected value`）。
  ★ **cpk 必须落在 `PCSG00815/data/` 下且补全 `thumbnail/`**，否则报 "Directory … does not exist"。
  剧本 = `data/STORY.cpk` → `SCRIPT/*.DAT` ×104（`init/` 5 件＝系统初始化，排除）；`SYSTEM.cpk`＝UI/表；
  `GAME.cpk`＝822 张 `.tid`（无文本）。
- ★★ **CPK 坑**：① `cpk_v1` 的 TOC FileOffset 基址 **+0x1000 偏移**不可靠 → 按「ContentOffset 起、Align 对齐、
  TOC 偏移序」顺序排布；② CRILAYLA 解压**必须用 `cpk.py` 的 `crilayla_decompress`**（含**变长长度编码**；
  `cpk_v1` 版是定长 8-bit，本作解不出）。每件 `FileSize = 16 + csize + 0x100`，解出头部 `STCM2L`。
- 指令 = `[ic][opcode][np][len]` ＋ np×`[p0,p1,p2]` ＋ data；**字符串 = UTF-8**，
  记录 `[0][L/4][1][L][text][pad]`（L=align4(len+1)）。
- ★ **Δ 极小**：TEXT 目标地址 ∈ {`0xCD7C`, `0xCD6C`}（Δ∈{0,−0x10}），**NAME = TEXT+0x6FC**、
  **OPT = TEXT+0x10F4** —— 相对偏移恒定。Δ 自适应＝「引用含日文串最多的 call 目标」= TEXT。
- 语义：`TEXT`=正文/心声（连推合并）；`OPT`(np=2, p0=选项文本, p1=跳转目标)=**选项**（一行一条、按序）；
  `NAME`=名札（丢）；builtin **`0x1F4`=换框＝一次点击**；builtin `0x6`=goto。
- ★ **互斥版本＝`goto` 分段**：同一文本框内 `goto` 分隔的段是「写死默认名版 / `#Name[2]` 版」，
  **取一段、优先「不含 `#Name`」者**（并列取最长）。全库 407 框按此归并（否则 2 倍重复）。
- 宏仅 `#Name[1]`=**月嶋**（姓）/`#Name[2]`=**ヒカリ**（名）；主角默认名 **月嶋ヒカリ**（vndb v17641 实证）。
- 原始笔误 1 处（缺 `）`，整行定值修）＋ 源内调试注释 1 处（`/*03867*/`，剔除）。
- 工具：`scripts/psycemo6_extract.py`。产物 **30,924 行**【PASS】。

---

## F) MARGINAL#4 ROAD TO GALAXY（PCSG01008，2017 Otomate×Rejet）—— **UTF-8、固定 opcode、文本记录内联、选项文本在「指令外」**

- 容器：NoNpDrm **pkg**（+同目录 `work.bin`）⇒ `pkg2zip -x <Windows 绝对路径> <zRIF>`（⚠ **不认 `/c/…` 正斜杠**，报 `cannot open`）
  → `psvpfsparser -i app/PCSG01008 -o dec -k <work.bin[0x50:0x60]> -f cma.henkaku.xyz`（前台+放行网络）。
  zRIF 从 `psvdec-main/games.json['PCSG01008']` 取。
- 资源分布：**`STORY.cpk` = `SCRIPT/*.DAT`×140 ＋ `SCRIPT/init/*.DAT`×6**（正文全在此）；
  `GAME.cpk`＝图像（`.tid`537/`.CL3`451）＋`WORK/NOTE/*.gbin`×78（演奏数据，无文本）；
  `SYSTEM.cpk`＝`DATABASE/*.gbin|.gstr`（**整套是『薄桜鬼 真改 風ノ章』遗留**，见末条）。
- 编码 = **UTF-8**；**opcode 恒定、无逐文件 Δ**（全 146 文件一致）。
- 文本 = `[u32 ic][u32 op][u32 np][u32 len]` ＋ np×`[p0,p1,p2]` ＋ data；记录 `[0][L/4][1][L][utf-8]`。
  全库 `parse()` 自洽（末条指令末 == `export_addr`，140/140）。
- 语义：**0xE714**=TEXT（np=1）；**0xEF20**=名札（np=1，`桐原 アトム`/`#Name[1] #Name[2]`）；
  **0xFB68**=選択肢（np=3，p0=文本/p1=数据/p2=跳转标签 `sure2/3/4`）；
  **0x62F80｜0x63318**=互斥双写正文（np=8＝`[id][t1][t2][t3][id2][t1'][t2'][t3']`，**取组1**＝直写人名版）；
  **0x2250**=章题（`Prologue`/`MARGINAL#4 1話`）；**0x1F4**=换框（主断框）；
  0x5778/0x5168/0x4D98/0x4F80/0x56E8/0x5988=按名访问变量（`end土方`/`switch`/`好感度X`）；0xF850=系统通知。
- ★★ **选项文本常驻「指令之后的数据区」**（`0x737d4` 的指令 → 文本在 `0x73818`，**不在** `[p, p+len)`）。
  ⇒ 只做「内联范围判定」的解析器**选项 100% 漏**；须加「**按绝对偏移直接取记录**」兜底。
  且该 op 在每文件的**库函数区**也有 4 条（参数是常量）⇒ 必须按「能否解出有效记录」过滤。全库选项 **55 行**（≈18 组）。
- ★ **断框须四类**：`0x1F4` ＋ `0xEF20` 名札 ＋ **变量 op**（`304.DAT`『え、何？』框尾无 0x1F4、紧跟 `0x4F80 'switch'`）＋ 章题/选项。
  框粒度＝**≤3 条连续 TEXT 合并成 1 行**（实测 1:2132／2:3052／3:2741，>3 仅 4 处）。
- **主线「选哪个管理人」不在脚本内**：`dbStoryMain.gbin` 用 `MARGINAL#4_track1_OPEN` 等 flag 分派；
  选择界面 = `GAME.cpk/GROUP_SELECT/*.tid`（9 张图）⇒ **图片式无字选项，不收**。
- 主角：**片岡 ユエ**（`#Name[1]`/`#Name[2]`；默认名取自 `SCRIPT/init/0_init.DAT` `"片岡"`@0x37f68＋`"ユエ"`@0x37fcc；vndb v15161 一致）。
- 排除：`init/*.DAT`×6（系统）、`100.DAT`（测试串，**未被 `dbEntryScript.gbin` 收录**）、`901–904.DAT`（数据，零正文）、
  `SYSTEM.cpk/DATABASE/**`（薄桜鬼遗留 ＋ 系统/UI 表）、`str*.gstr`、`GAME.cpk` 图像与演奏数据。
  地名（0x54990/0x548AC/0x636B0，~240 处）默认不收（`--with-loc` 可收）。
- ★ **他作遗留实例**：本作 `SYSTEM.cpk` 整套继承自 **『薄桜鬼 真改 風ノ章』** ——
  `dbDictionary.gbin`（=新選組/会津术语，1625 条零 MARGINAL#4 词条）、`dbExRecord/dbExFeeling`、
  `strGame.gstr`（土方歳三…）、**`strSystem.gstr` 首条直接写着「薄桜鬼 真改　風ノ章」**。
  ⇒ **抽 3–5 条**与本作角色名/曲名对照即可整体排除，**别因为表名像辞典就当本作用語辞典收**。
- 完整性自证：全文件「通用记录扫描」15,537 条日文记录 − 提取取用集 = 165 条未取用，**全为变量名/系统通知**，零正文遗漏。
- 工具：`scripts/marginal4rtg_extract.py`（自包含，依赖 `scripts/cpk.py`）。产物 **7,996 行**【PASS】。
