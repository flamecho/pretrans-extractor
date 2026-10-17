# HuneX「Ogre」系 · dramatic create 移植三作（円環のメモーリア / 赤い砂堕ちる月 / 罪喰い for V）

> > **家族总览（容器/MZX0/指令总则）＋ カレイドイヴ ＋ マジきゅん 见 `hunex-ogre.md`**；
> 路由一句话见 `../engines.md`；主索引见 `../MEMORY.md`。

---

## 円環のメモーリア -カケラ灯し-（PSV PCSG01167, A'sRing / dramatic create 2018）—— **第三种布局/指令集**
- **解密**：PKG(`bg_1`) → `pkg2zip`（**zRIF 在 `<psvdec>/games.json`，PCSG01167 命中**）→
  `psvpfsparser -i app/PCSG01167 -o dec -z <zRIF> -f cma.henkaku.xyz`（`keystone: matched retail hmac`）。
  `eboot.bin`(SCE)→ELF 用 `util/self2elf.py`（pycryptodome，`envs/default`）。
- **`allscr.mrg` = 自包含 mrgd00（count=174，无 `.hed`）**：`[0]`名表（172 槽×32B，末槽空→171 名）
  `[1]`scr_adr.mrg `[2]`颜色表 `[3..173]`171 脚本，names[i]↔member[3+i]（同マジきゅん布局）。
- **指令集（本作专属）**：正文 `_ZM<5hex>(text)`＝一次点击＝一框（**无 `_MSAD` 续接指令**）；
  选项 `_SELR(idx,label,text)`；章标题 `_LVCT(text)`（与 `_LVSV` 同文 → 只取 LVCT）；
  名札 `_MTLK(1,名前)` 与 **`_VTLK(名前)` 两种**（皆丢）。`@*` 演出码 **0 处**；`^`＝框内软换行（8 处，删）。
- **主角占位符 = `＄名`**（全角 ＄，1797 处）→ 主角默认名 **香月 紗結**
  （eboot ELF `@0xb2bd4`=香月 / `@0xb2bdc`=紗結；正文亦见「香月＄名」）。vndb v18291。
- **排除**：`ENMEMO`(系统菜单)、`FUNCTION`(おまけ/共通函数库，唯 4 条 `「は！？」` 已在正篇重复)、
  `LX_DEBUG`(调试)、`MORGUE`(触屏语音 UI 占位 `タッチボイス`)。**无用語辞典**（allpac 全图片）。
- **原文笔误 3 处**（整行定值表修，报告单列）：半角 `､｡`(0xA4/0xA1)、多一个 `」`、孤立 `\`(0x5C)；
  **注音 1 处** `<しらきまち>白葵町|` → 基底语 `白葵町`。
- **成品**：29,817 行（正文 29,537＋选项 112＋章标题 168）。工具 `scripts/enkan_extract.py`。

---

## 赤い砂堕ちる月（PSV PCSG00780, Landkarte / dramatic create 2016）—— **第四种布局：`_IF__` 守卫块 + 无续接指令**
- **解密**：同 PSV 常规（`work.bin`→`zzzrif.py`→`pkg2zip -x`→`psvpfsparser`；zRIF **命中 games.json PCSG00780**；
  **日文路径须 ASCII hardlink**）。
- **`allscr.mrg` = 自包含 mrgd00（count=158，无 `.hed`）**：`[0]`156 槽名表（末槽空→155 名）
  `[1] scr_adr.mrg`（＝ASCII **标签→偏移表**，非显示序）`[2]`颜色表 `[3..157]`155 脚本，names[i]↔member[3+i]（同 マジきゅん 布局）。
- **指令**：`_ZM<hex>(text)`＝一次点击（**无 `_MSAD`、无 `@n`**，多行只靠 `^`）；`_SELR` **两形态**（1 逗号 / 2 逗号带分支号）；
  名札 `_MTLK` 丢；`_ATSV(3,1,章題)`＝**战斗章保存标题**（菜单用）丢；`_ASMB/_ASBS/_ASBE/_ASDG` 丢。
- **★ 守卫块 `_IF__(变量,op,值,标签) … _ZY<id>(标签)`；相邻且「同变量＋条件互斥」＝同一点击的备选 ⇒ 只留第一支**：
  `F038 eq0..4`＝主人公 **5 性格**（章一选择决定，同场景写 5 份，多仅立绘异）；`G241 eq0/ne0`＝相遇标记 if-else（文本多全同）。
  **条件相同者＝两个独立跳块（两体都执行）不可丢**（本作仅 3 处，全在无正文 `ROOT`）。
  原始 `_ZM` 54,534 → 折叠后 30,162 行（**只留 `F038==0` 措辞**；要全 5 版则不折叠）。
- **控制码**：`^` 删；`@c(r,g,b)` 文字色删；`<基底語,読み>` 注音取**基底語**（第二段必为假名）；`＊Ｂ`＝**主角名**（29,983 处；`＊Ａ` 未用）
  → 春霞（eboot.elf 结局名表 `0xefcbc`「汪明と火＄春霞」；vndb v3820/c37881 Nameable）；相容字 1 处 `0xFA9C`→U+FA10→归一 **塚**。
- **排除**：`TEST_SCRIPT`（开发菜单）、`TEST_BATTLE`（CG/回想调试 `番号:NN/292 実名：BGxxx`）、`START_SCRIPT/ROOT/MAP01_01`（无正文）。
- **★ 无文本用語辞典**：`allpac` 的 `DEV823DICTIONARY.MRG`（＋CHRONOLOGY/PROFILE/NAME）＝**字形/位图数据**
  （嵌套 mrgd00＋MZX0，解压＝常值填充 `\x10\x10…`），非文本（同 カレイドイヴ）。
- **成品**：30,162 行（空行 0；台词 24,962＋旁白/选项 5,200；选项块 131）。工具 `scripts/akasuna_extract.py`。

---

## 罪喰い ~千の呪い、千の祈り~ for V（PSV PCSG01019, Operetta / dramatic create 2017）—— **第五种布局：`_MSAD` 续接 + 空守卫块**
- **解密**：源＝**NoNpDrm zip 内的「app0 文件树」**（`data/`＋`eboot.bin`＋`sce_pfs/`＋`sce_sys/`），但 **app0 整体仍是 PFS 密文**
  （`icon.png`/`eboot.bin` 皆高熵 7.997、无魔数）⇒ 仍须 `psvpfsparser`。**zRIF 未命中 games.json ⇒ 用包内 `sce_sys/package/work.bin`（512B 明文，content id@0x10 / klicensee@0x50:0x60）现场生成**；
  `psvpfsparser -i <app0目录> -o dec -z <zRIF> -f cma.henkaku.xyz`（前台＋联网）→ `keystone: matched retail hmac`。
- **`allscr.mrg` = 自包含 mrgd00（count=118，无 `.hed`）**：`[0]`名表（116 槽×32B，末空→115 名）`[1] scr_adr.mrg` `[2]`颜色表 `[3..117]`115 脚本，
  **name(member i)=names[i-3]**（★注意：不是 names[i]）。`data/scr.nam`・`data/scr_adr.mrg` 是**同一份的独立副本**。
- **指令**：正文 `_ZM<id>(text)`＝一次点击；**`_MSAD(text)`＝续接同框**（前一条 `_ZM` 以 `^` 收尾；2,032 条 `^`-结尾 `_ZM` ↔ 2,032 条 `_MSAD`＋77 条 `_MSAD`-接-`_MSAD`）⇒ **合并成一行**；
  选项 `_SELR(idx,text)`（**单逗号形**）；名札 `_MTLK1(,名前)` 丢；`_LVSV(n)`＝**纯数字章节号**（存档索引，非上屏）丢。
- **★★ 守卫块 `_IF__(var,op,val,label) … _ZY<id>(label)` 内 `_ZM` 计数全为 0**（429 块实测）⇒ 只包立绘/语音/跳转，**不承载分歧正文 ⇒ 文本线性、无需折叠**
  （≠ 赤い砂 的 5 性格同场景写 5 份）。
- **控制码**：`^` 删；`@w1/@h1/@r` 演出码删；**注音 `<基底語,読み>` → 取基底語**（178 对；`<私,わたくし>`→私、`<女,おな><子,ご>`→女子）；`＊Ｂ`＝**主角名**（9,453；9,337 在名札）→**薫**，`＊Ａ`（姓=庵崎）**0 处**。
- **★ 未解析控制码 `0xEC4E`**（cp932 未映射，**全篇仅 3 处、皆在 `_ZM` 行首**）：判为引擎控制码（同族 マジきゅん `0xEC4C`＝姓/名分隔）⇒ **剔除**，不硬猜字形（字体页＝81B 头＋MZX0 位图，码位→字形映射未知 ∎ 不做 OCR）。
- **主角默认名 = 庵崎 薫**：取 **eboot.elf 的「ボイス設定」名单**（`0xd5b10` 起 `【庵崎　薫】/【永海　連】/【上樹　守人】/【陸　至央】/【陸　任史】/【田井　蒼太】/【カゲロウ】/【庵崎　司】/【田井　素子】`）——**在机权威全名表，优于 vndb**（vndb v18295 只给 romaji）。
- **排除**：`TEST_SCRIPT`(开发菜单)、`TEMPLATE`。**无用語辞典文本**（`DEV_MYSTERY.MRG`/`DEV_NAME.MRG` 皆位图/压缩二进制；脚本层无非 `_ZM/_MSAD/_SELR` 日文指令）。
- **原文笔误 1 处**（整行定值表修）：`066_TOU_900` 句尾多一个 `」`。
- **成品**：30,118 行（台词 14,970＋心内 3,377＋旁白/选项 11,771；选项 301/100 组；有正文脚本 82/115；27 处相邻重复＝引擎真实两次点击）。工具 `scripts/zokuwanai_extract.py`＋`scripts/zokuwanai_unpack.py`。
