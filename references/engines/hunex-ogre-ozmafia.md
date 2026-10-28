# HuneX「Ogre」系 · OZMAFIA!! -vivace-（Nintendo Switch 变体）

> 同族 PSV 版（カレイドイヴ/マジきゅん/円環/赤い砂）细节见 `hunex-ogre.md`；路由见 `../engines.md`。

## OZMAFIA!! -vivace-（Nintendo Switch `01002BE0118AE000`, Poni-Pachet SY）—— **Switch 变体：容器/指令集均与 PSV 版不同**
- **源**：RAR5 **头加密**（密码 `otoame`，注释内注明）→ XCI → `hactool --keyset`（★ `prod.keys` 里 17B 的
  `mariko_master_kek_source_*` 坏条目会让 hactool 报 `must be 32 hex digits`，**先滤掉**）→ RomFS。
- **`allscr.mrg`＝自包含 `mrgd00`（count=750，无 `.hed`）**：`[0]`名表(32B×747) `[1]`scr_adr.mrg `[2]`色表
  `[3..749]`747 脚本（`names[i] ↔ member[3+i]`）；脚本本体 = MZX0。
- **指令集**：`_ZM<6hex>(正文)`=一次点击；`_MSAD`=`@n` 续框（全库 6 处，须并入上一行）；`_SELZ(_标签,idx,选项…)`=选项；
  `_LVSV(章題)`=章題；`_MTLK(1,名)`=名札丢；`_LVSO(char_idx,线路标签)`=存档/章选菜单标签丢。
  控制码仅 `^`(软换行 删)、`@n`(删)、`<基,読>`(取基底语)；**无 `@c/@e/@w/@h`**。ruby 开括号笔误 1 处(`_睫毛,まつげ`→整行定值)。
- ★★ **守卫块 `_IF__(VAR,op,val,LABEL) … _ZY<id>(LABEL)`＝同场景写两份（正文全同、仅语音/立绘不同）** ⇒ **成对折叠**：
  run 常为 `[eq0,eq1,eq0,eq1,…]`（≠ 赤い砂 的整串），须**两两配对**；且**仅当两支正文逐条全同**才折（有差异则两支都留，宁多勿失）；
  run 判定须容忍两支之间夹「无正文语句」(`_STCH` 等)。原始 40,348 条 `_ZM` → 39,222，相邻重复 869→9。
  ⚠ 另有 `_IFF_(VAR,op,val,LABEL)`＝**分支调度**（真分支在 `_ZZ<id>(LABEL)` 之后、文本各不相同）**不可折**。
- **`script_text.mrg`＝他作遗留**：「魔法使いの夜」(TYPE-MOON)（`mrgd00` count=12：`[1]`=日文 23,993 条带注音，
  `[3][5][7][9][11]`=`text en/es/de/it/fr 0…` 占位）；与 `_ZM` 交集仅 462/40,348 ⇒ **整体排除**（0 个 OZMAFIA 名词）。
- **`allpac.mrg`＝图像/UI（4494 条 .MRG/.MZP）**，**无文本用語辞典**。
- **主角/名字宏**（全库只有 `＊Ａ`/`＊Ｂ` 两个）：`＊Ａ`=女主角，默认 **フーカ**（vndb c28257）；`＊Ｂ`=**改名后的ドリアン**，
  ★**默认「ドリアン」而不是「ドリアン・グレイ」**——`W_018A_ORG` 里 24 处字面「ドリアン・グレイ」全在 @524–7047（改名事件前）、
  5 处 `＊Ｂ` 全在 @7943–8434（其后），切换点＝`002_ドリアン名称設定`(`_EVT0(0,11,1,0)` 名字输入→`_JUMP(w_018a_DORIAN_ORG)`)；
  场景自证：アルファーニ「なんて呼べばいいんだろう」→＊Ａ「＊Ｂと、呼べばいいわ」→「今度からそうするね」。
  默认值取 `exefs/main` **名字输入初始值表** `フーカ\0ドリアン\0`（@0x10d3df，第1/第2槽；`ドリアン・グレイ` 全 eboot **0 出现**）。
  另有 `MAIN_START` 的 `_WKST(F3000,ドリアン・グレイ)`（write-only、全库仅此一处）**不作** `＊Ｂ` 默认值口径。
  ⚠ 身份仍是同一角色：`_MTLK(1,＊Ｂ)` 与 `_MTLK(1,ドリアン・グレイ)` **语音前缀同为 `do_`**（本场景 29 = 24+5），立绘同 `do_02`。
- **排除**：`MAIN_START/SUB_SCRIPT/SCENARIO_START/0xx・1xx・2xx_*`（系统）、`TEST_*`、`*テンプレ`、`MAPSEL_START*`、
  `REP01..98`・`REPLAY_END`（回想，**0 正文**）、`*_BUNKI_*`（调度，**0 正文**）。
- **收**：全线路（AX/CA/KY/SC/SO/RO/PA/OZ/W/TRUE 系）＋`MAIN001〜017`(＋`_HANTEI`)＋各 ED/エピローグ＋
  `SW1_*`/`SW2_*`/`SWITCH_001〜005`（-vivace- 追加）＋`OMAKE_001〜014`（おまけ短編）。
  ⚠ `MAIN001_01`(プロローグ) 与 `SW2_MAIN001_01`(GRIMMMAFIA!) 是**两份不同文本**（交集 69 行），均保留。
- 工具 `scripts/ozmafia_extract.py`；成品 39,861 行【PASS】（正文 39,222＋选项 628＋章題 11）。
- ⚠ 官方更新 `1.0.1`（NSP → NCA `b8b3…`＝**BKTR 增量段**）本机 `hactool`(2020) 落不了地
  （`cannot save BKTR section without base romfs` / `Failed to read RomFS directory cache!`）⇒ 成品基于本体 XCI。
  自写 `scripts/ozmafia_nca.py` 已通 NCA 头 XTS＋段表（见 `platform-switch-nca.md`）。
