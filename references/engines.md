# 项目 _trans —— 引擎路由（索引）

> 引擎**细节已按家族拆到同目录 `engines/*.md`**。
> **用法：先在本表定位引擎，再只读对应的那一个 `engines/*.md`**。
> 主索引见 `references/00-index.md`；作品清单见 `references/engines.md`；工具见 `scripts/INDEX.md`。
> ★ **2026-10-18 后新增的同族变体路由行已拆到 `engines-3.md`**（本表又近上限）。
> ★ **单作专用自研引擎已拆到 `engines-solo.md`**（2026-10-14，本表超 10 KB）。
> ★ **「HuneX IKA SEQ SYSTEM v3.1/v4.2」（本表最长一行）已拆到 `engines-2.md`**（2026-10-18，本表四度超 10 KB）。
> ★ **「D3P 系（CRI CPK ＋ 自建位图字体）」与「BROCCOLI / Sanctuary・EMIQ `ADV`」2 行已拆到 `engines-2.md`**（2026-10-17，本表三度超 10 KB）。
> ★ **「自研 / 小众 / 单作系」7 行（含 **MAGES.（旧 KID/5pb.）AFS 文本池**）已拆到 `engines-2.md`**（2026-10-16，本表二度超 10 KB；含「其它自研/小众」「Unity＋自研 ADV 纯文本变体」「テキスト方式 ADV」「LTE」「Aromarie ATL」）。

## 引擎一句话索引 ＋ 详见文件

| 引擎 | 代表作 | 一句话要点 | 详见 |
|---|---|---|---|
| NoNpDrm / PSV PFS | PSV 通用 | pkg2zip → `psvpfsparser -z <zRIF>`；见 `references/00-index.md` 铁律 11 | `engines/platform-psv-pfs.md` |
| Switch XCI / NCA / NSP | Paradigm Paradox・滄海天記・悪役令嬢 | PFS0→NCA3(明文头@0x200)→RomFS；`--keyset/--titlekey` 传**加密**值 | `engines/platform-switch-nca.md` |
| Koei CDAR v2/v4 | コルダ・遥か・下天の華・**ネオアンSpecial(PSP)** | 文本 `04 <u16 len> <cp932> 00`；框边界 BOUND/C7/M91；v4 两套定长插值表；FD 改内联记录插入。★PSP 変体：头无名称表・须去重・**宏＝变量表实证** | `engines/koei-cdar.md` |
| Otomate VM | BAW・フォルティッシモ | JIS X0208；块 `…0xff68…`；**字体槽禁跨作** | `engines/otomate-evb-marc.md`（并入其 MARC 段） |
| STCM2L（Idea Factory） | 猛獣/BLACK WOLVES SAGA/**Glass Heart Princess(NS)**・**ニルアド(NS)**・PANDORA・L2 Love×Loop(PS2)・**D.C. Girl's Symphony Pocket(PSP/UNI2)**・**アーメン・ノワール ポータブル(PSP/CPK)**・**Jewelic Nightmare(PSP/CPK)**・**二世の契り(PSP/CPK)**・Norn9/RE:VICE[D]/PE6/ROOT∞REXX/MARGINAL#4(PSV) | 链 `[u32 size][payload]`；文本记录 `[0][L/4][1][L][text]`；PS2 容器＝CRI UNI2；PSV 指令 `[is_call][opcode][nparams][length]`（各作布局不同）。**续作可能换编码**（E=CP932 → F=UTF-8）。★**Switch 侧已 4 型**（猛獣／BWS／GHP／**ニルアド＝头长 `28+12k`・`k=3` 才是选项・CP932**） | `engines/idea-factory-stcm2l.md` ＋ Switch:`engines/idea-factory-stcm2l-switch.md` ＋ PSV：`engines/idea-factory-stcm2l-psv.md`(UTF-8 A/C/F)・`engines/idea-factory-stcm2l-psv-cp932.md`(CP932 B/D/E)・`engines/idea-factory-stcm2l-psv-g.md`(CP932 **G＝薄桜鬼 随想録**：`0x4BC` 不断点击、**空 `0x4BA`/分支 op 双分段**) ＋ PSP：CPK=`…-psp-cpk.md`（SBL／**Jewelic ④＝变体箱+名札烘进正文**／**⑥官能昔話＝`0xd2`续行・`0xd3`框末（与⑤相反）→`…-psp-cpk-kannou.md`**／**⑦二世の契り＝`0xd2`续行・`0xd3`／`0x01`框末＋**变体尾 `[0][1][cmd]`**→`…-psp-cpk-niseno.md`**）／`…-cpk-2.md`（アーメン＋ガーネット）／**UNION.CPK 无 TOC**=`engines/otomate-stcm2l-psp-unioncpk.md`（魔恋の六騎士：k 不固定・`SEL_` 选项）／**UNI2**=`engines/idea-factory-stcm2l-psp-uni2.md`（DCGS＋アルコバレーノ!；⑤ウィル→`-2`）★判型**「槽数」**：正文4/名札1/选项2） |
| CRI CPK ／ CRI AFS | 通用 ／ 花宵ロマネスク | `cpk.py`(>>8) / `cpk_v1.py`(&0xFF)，判据 `@UTF`；AFS＝自研「SJIS 索引码」（`FFF0`=框、`FFE6/7`=姓/名宏，数字·全角拉丁整体错位 −1 槽） | `engines/cri-cpk-afs.md` |
| KiriKiri XP3（3 态） | クリムゾン・ロワイヤル・蝶の毒 初回版/幻想夜話 | 标准／DropWave OTag（`.ks/.tjs`=zlib+UTF-16LE）／**区间 1 字节 XOR**（孤立字节另键→逐位置定值复元表） | `engines/kirikiri-xp3.md` |
| Malie System（Camellia LIBP / MalieVita） | OmegaVampire・英国探偵ミステリア | PC：LIBP=Camellia；Vita：LIBP **明文** ＋ **offset 块单位 2048**、exec.dat 名=ASCII、STRT=CP932；AlphaROM 壳须运行时 dump | `engines/malie.md` |
| WillPlus / AdvHD（`.wsc`） | Butterfly Lip / Gloss / Rouge | arc＝ext 组容器（21B/条）；**WSC 每字节 `rotl_8(c,6)`**；文本 `op41`旁白/`op42`名+台词/`op02`选项，目标指令须按表分派 | `engines/willplus-advhd.md` |
| Unity ＋ 自研 ADV | ハイリゲンシュタット・ヴェリテ・悪役令嬢・**魔女と亡霊のヴォロンテ(NS)** | PSARC→`resources.assets`(TextAsset)／TKG `0x10 MSG_PARAM`=点击／CSR1.00 `06 01`·`06 03`=文本框 | `engines/unity-adv.md`；**Naninovel 系**：`engines/naninovel-unity.md` |
| HuneX Ogre（allscr / MZX0） | カレイドイヴ・円環のメモーリア・マジきゅん・赤い砂堕ちる月・**罪喰い for V** | `MZX0`(字面 XOR 0xFF)→CP932 `_CMD()`；`@n`/`_MSAD` 语义**逐作不同**（赤い砂＝守卫块 `_IF__(F038 eq 0..4)` 5 性格分歧折叠；**罪喰い**＝`_MSAD` 续接同框须合并、守卫块内 0 正文不折叠、注音 `<詞,読>`）；UI 在 eboot→ELF | `engines/hunex-ogre.md` |
| **HuneX Ogre · Switch 变体** | **OZMAFIA!! -vivace-** | 自包含 mrgd00（count=750，**无 `.hed`**）；正文 `_ZM<6hex>`、选项 `_SELZ`、章題 `_LVSV`、名札 `_MTLK`；**守卫块 `_IF__(G241,eq0/1)…_ZY` 成对折叠**（`_IFF_`＝分支调度**不可折**）；`script_text.mrg`=「魔法使いの夜」他作遗留 ⇒ 整体排除；更新 1.0.1 为 BKTR | `engines/hunex-ogre-ozmafia.md` |
| **HuneX HESL/UNAS（HGTC/HPAC/HLZS/HFNT/CSB/HESL/HESE）** | **BELIEVER!**・**VitaminX Destination**・**StarrySky Spring(NS)** | 与 Ogre 不同族；`script.heslnk`→`charset.csb`(**字符表**)＋`HESE`；文本码＝**`csb[code-0x8000-6]`**；`0x8000`=框内换行(合并)、`0x2C`=软换行；★2 作已见**选项`19`**／**章題`1b 0x26`**／**主角名宏`0x0b`姓・`0x0a`名**；★**NS＝文本外置**（HESE 内 0 假名 → `script_dialog_ja.hdlg` 的 `HDLG` 表） | `engines/hunex-hesl.md`／NS:`engines/hunex-hesl-switch.md` |
| Takuyo gss | ひめひび・Cafe Cuillere（PSV） / **神さまと恋ゴコロ・カエル畑DEつかまえて☆彡・ソラユメ・SWEET CLOWN（NS）** / **étude prologue・Little Aid（PSP）** | `LSDARC V.100`；PSV=`SCR 2.00` **未打包**，**NS=`SCR 3.00`**（头 `LSD\x1a`＋enc/pack，pack `H`=Huffman/`D`=16bit增量/`R`=RLE 须自解；**也可全未打包**：SWEET CLOWN 386/386 `isPacked=0`）；★★**串内 `\c`＝清框换页（断行）／`\n`＝框内软换行（合并），本族无 B 类 ⇒ 单版**；★**`0x5a` 固定名 与 `0xfc` `%s` 互斥成对**（`0x22/0x21/0x23` 分隔，替换后逐字同）⇒ 按 `(0x5a,0xfc)` 型别去重；★**脚本版本按文件头判，不可按平台推定**（カエル畑・ソラユメ＝NS 但 `SCR 2.00` 未打包，opcode 表与 ひめひび **一致未平移**；**Little Aid＝PSP 但 `SCR 1.10`＝与 `SCR 2.00` 指令编码逐字节同构、pack=N/H**）；文本 op `0x5a/0xfc/0xf0/0x5c`；★**调试旗 `c808`**（`INIT` 置 0、无处置 1 ⇒ 其 `0x22` 块内选项＝开发菜单，剔）；★**PSP 版 `SYSDIR/BOOT.BIN`＝明文 ELF**（免解密）且内含**引擎事件表**（étude：4B 对齐 CP932 脚本名 @`0x6edf8`）／**名字输入默认值表**（Little Aid：`[西村][あかり][西]`）；★**非线性作的顺序须靠引擎自身分派表**（étude＝BOOT 事件表；Little Aid＝`STORYCTRL.SCR` 的 637 条 `0x1e`）；★**场景标题卡可经 `0xfd/0x107` 槽拼接生成**（Little Aid `5802`） | `engines/takuyo-gss.md` ＋ NS:`engines/takuyo-gss-switch.md`（SCR 3.00：神さま＝打包／SWEET CLOWN＝未打包＋XCI 紧密打包手切＋BKTR 用 nstool 叠加）／`engines/takuyo-gss-switch-scr2.md`（SCR 2.00 未打包：カエル畑・ソラユメ）／**PSP:`engines/takuyo-gss-psp.md`**（étude）＋ **`…-psp-littleaid.md`**（Little Aid `SCR 1.10`／H）＋ **`…-psp-hoshiiro.md`**（星色：标题卡 `0xf0`／名札 `d402`）＋ **`…-psp-symphony.md`**（for Symphony：**双主人公选性别**／名槽 `0c02`+姓槽 `2002`／`0x5c` 选项自带 `『』`） |
| **Otomate/Idea Factory 自研（DAT + PAK + SCD）** | **学園K -Wonderful School Days- V Edition・ネオ アンジェリーク 天使の涙（PSV）** | `CORE.DAT`/`DATA.PAK` 皆 **zip**；`DATA.PAK`＝单文件 zip 串联、每块 512B 对齐（7z 只认第一个）；容器 `DAT `＝`[count]+count×(name[0x20]+size+offset)`；剧本 `.SCD`：串＝`<u16 len><utf8>`。⚠**逐作变**：名札（学園K＝char_id／ネオアン＝记录内 `"名前"`）、主角宏（`%&`／`&`+`#`愛称）、追加载体（ネオアン＝`LT*.txt` 書簡＋`STORYFLOW.BIN` 章題）。★扫描器「含控制符整条丢弃」曾静默漏收 41%（`\`+0x08） | `engines/gakuenk-dat-scr.md` |
| **M2「ADVENGINE」（Squirrel/Sqrat ＋ PSB）** | **Beyond The Future -Fix The Time Arrows-（PSP）**；同族＝所有 `*_info.psb.m`＋`*_body.bin` 数据盘 | `fileinfo.psb.m`（MDF 壳 PSB）＝UMD 根索引，`[?,size,offset]` 指向 **`INSDIR/INSTALL.BIN`＝PGD 加密的全部数据**；键＝EBOOT 里紧跟 `DISC_ID` 的 13 字符，MDF seed＝键＋名（keylen 131）；解 PGD 后成员仍是 MDF → PSB；剧本 PSB `Scn`：`scenes[].texts[]`（一框一项、`\n` 软换行）/`selects[]`，**顺序看 `scenelist.json`**；map/chara 选项按 `eval` 重复两条须折叠；标签 `%C`/`%<n>#hex;`/`\w` 全剥 | `engines/m2-advengine-psb.md` |
| **Otomate 自研 `.evb` ＋ MARC（PSP）** | **Confidential Money**（同族＝マスケティア） | `USRDIR/ca000_0000.cpk`→1228 `ev*.evb`；正文＝**2 字节大端字符码串**，字符表与 マスケティア **逐槽同**；★**成框必须前向扫描**（反扫 `(0x81,0x0A)` 被当字符 ⇒ 起点错位，`（`→`戊`）；★**一次点击＝`0A 00` 框**，`0A`/`0x1F` 均**同页内换行须合并**（看句中率：`0A` 34%＝折行、`1F` 6%＝手动断行）；**扉文 `――日本。 00 00 FB FF` 不以 `0A 00` 收尾**；`1D 00`=主角名；`8DD7…8DD8`=強調包裹**去壳留字** | `engines/otomate-evb-marc.md` |

## 维护约定

- **册名＝族前缀 ＋ 变体**（2026-10-27 定）：`<厂商或引擎>-<平台或变体>.md`
  - **厂商 / 引擎族**：`hunex-` · `idea-factory-` · `takuyo-` · `koei-` · `cri-` · `d3p-` · `konami-` ·
    `mages-` · `otomate-` · `zerodiv-` · `stormlover-` · `vsc-` …（同族天然相邻）
  - **平台级通识**（不是某厂商的引擎）用 **`platform-`**：`platform-switch-nca.md` ·
    `platform-psv-pfs.md` · `platform-switch-bktr.md` · `platform-switch-bezel-bea-scne.md`
  - **合集 / 方法**用 **`misc-`** 或不加：`misc-engines.md`（杂项合册）、`stcm2l-op-census.md`（族内方法）
  - **引擎名本身即唯一标识**的不加前缀：`malie.md` · `siglus.md` · `lte.md` · `nitroplus.md`
  ⇒ 目的：`ls engines/` 时同族相邻，`platform-*` 一眼与厂商册分开——**别用平台名当族前缀**
  （`switch-nca` 这种会被误当成某厂商的 Switch 变体）。
- **新增引擎 ⇒ 新建 `engines/<slug>.md`，本表只加一行**（一句话要点 ＋ 详见文件）。**别往本文件堆细节。**
- 已有引擎的新发现 ⇒ 追加到对应 `engines/*.md`；每个引擎文件自包含（容器→解密→脚本→成行→排除→工具）。
- **超 10 KB ⇒ 拆**（新建分册，别压缩）：本表已按此把 PSP 变体拆到 `engines/stormlover-d3p-psp.md`、把**单作专用自研引擎**拆到 `engines-solo.md`。
