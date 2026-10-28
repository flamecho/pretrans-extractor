# 脚本 → 用途（全部 585 个）

> **每次构建自动重建** —— 不要手改。
> 按引擎挑脚本请看 [`INDEX-BY-ENGINE.md`](INDEX-BY-ENGINE.md)（命中引擎后从那一行开始）。
> 本册用于反查：「这个 py 干什么」「这个作品做过吗」。`出自引擎册` 为 `—` 表示引擎册没引用它。

| 脚本 | 用途 | 出自引擎册 |
|---|---|---|
| `abunai_extract.py` | アブナイ恋の捜査室 (PSP, QuinRose/Gigno) —— .ks 文本 DSL → 全文本 | — |
| `advhd.py` | WillPlus / AdvHD (.wsc bytecode) shared engine. | `willplus-advhd` |
| `akasuna_extract.py` | 赤い砂堕ちる月 (PSV / PCSG00780 / Landkarte & dramatic create 2016) 全文本提取器 | `hunex-ogre-dramaticcreate` |
| `akasuna_pc_extract.py` | 赤い砂堕ちる月 (PC / NScripter + NSLua / Landkarte 2013) 全文本提取 —— 双版对照 | — |
| `akasuna_pc_nsa.py` | NScripter NSA (arc.nsa) 解包 —— 赤い砂堕ちる月 PC 版 | — |
| `akuyaku_extract.py` | 悪役令嬢は隣国の王太子に溺愛される (Switch, OPERAHOUSE, Unity / CSR1.00) 全文本提取 | `unity-adv` |
| `alice_extract.py` | 白と黒のアリス for Nintendo Switch —— .qui(Lisp DSL) → 全文本（双版对照） | — |
| `amennoir_extract.py` | アーメン・ノワール ポータブル (PSP, Idea Factory / Design Factory 2012, ULJM06064) | `idea-factory-stcm2l-psp-cpk-amen-garnet` |
| `angel_build.py` | Angel Profile (PS2) —— 生成交付文本 | — |
| `angel_extract.py` | Angel Profile (PS2) 文本抽取 —— 常量池顺序还原 | — |
| `angel_lua.py` | Angel Profile (PS2) Lua 5.0-variant chunk parser. | — |
| `angelique_extract.py` | アンジェリーク ルトゥール (PSV, PCSG00696) 剧本正文+选项提取 [Koei Tecmo / Ruby Party 自研「pasc」节点流] | `koei-pasc` |
| `anki_extract.py` | アンジェリーク 魔恋の六騎士 (PSP, ULJM05986, Otomate 2011-11-17, vndb v8799) | `otomate-stcm2l-psp-unioncpk` |
| `anki_unpack.py` | アンジェリーク 魔恋の六騎士 (PSP/ULJM05986) UNION.CPK 解包 | `otomate-stcm2l-psp-unioncpk` |
| `apricot_extract.py` | 怪盗アプリコット ポータブル (PSP, Takuyo gss) 全文本提取 | — |
| `apricot_gaiden_extract.py` | 怪盗アプリコット 外伝 満編（PC / Takuyo GSS, SCRDATA = LSDARC V.100 + SCR 1.10） | — |
| `arcanafam2_run.py` | アルカナ・ファミリア2 (PSP, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取 | `hunex-ika-seq-arcana2` · `hunex-ika-seq` |
| `arcanafesta_extract.py` | アルカナ・ファミリア フェスタ・レガーロ! (PSP, HuneX「IKA SEQ SYSTEM v3.4/v4.2」) 全文本提取 | `hunex-ika-seq-arcanafamiglia` · `hunex-ika-seq` |
| `arcanafesta_run.py` | アルカナ・ファミリア フェスタ・レガーロ! (PSP) 成品生成 | `hunex-ika-seq-arcanafamiglia` · `hunex-ika-seq` |
| `arcanayurei_run.py` | アルカナ・ファミリア 幽霊船の魔術師 (PSP, HuneX「IKA SEQ SYSTEM v3.4」) 全文本提取 | `hunex-ika-seq` |
| `arcobaleno_extract.py` | アルコバレーノ! ポータブル (PSP, ULJM05609) 剧本文本提取 | `idea-factory-stcm2l-psp-uni2` |
| `artemis_pfs_extract.py` | Artemis Engine (iMel) 全文本提取工具 —— 以《滄海天記》(NS-JP) 定案 | `misc-engines` |
| `asakiyumemishi_extract.py` | あさき、ゆめみし～ひととせ～ (PC / 澪 / System-NNN「NNNLib」引擎) 全文本提取 · 定稿 | `misc-engines` · `system-nnn` |
| `asakiyumemishi_psp_extract.py` | あさき、ゆめみし (PSP-JP / System-NNN「NNNLib」engine) 全文本提取 · 定稿 | `misc-engines` · `system-nnn` |
| `audit_batch.py` | 批次审计：① 变量/宏错误填充残留 ② 双版对照断行位置自洽性 | — |
| `baccan_extract.py` | 爽海バッカニアーズ! 剧本文本提取（テキスト方式ADV / プチレーヴ） | `crank-text-mode-adv` |
| `bakudan_extract.py` | バクダン★ハンダン（PSP / ULJM-06057，Otomate 2012-06-14）全文本提取 | — |
| `bakudan_run.py` | バクダン★ハンダン（PSP / ULJM-06057，Idea Factory / Otomate）—— 全文本提取 | — |
| `believer_extract.py` | BELIEVER! (PSV, PCSG00539) HuneX / UNAS('HESL') script text extractor. | `hunex-hesl` |
| `benihana_extract.py` | 越えざるは紅い花 after disc～綾なす未来～（YU-RIS / YPF v500）全文本提取 | — |
| `beru_extract.py` | 私立ベルばら学園 ～ベルサイユのばらReimagination～ (NS) —— STCM2L 全文本提取 | — |
| `bezel_extract.py` | even if TEMPEST 連なるときの暁（Switch / Nintendo **Bezel Engine**）剧本文本提取 | `platform-switch-bezel-bea-scne` |
| `bgloss_extract.py` | Butterfly Gloss (WillPlus / AdvHD) text extractor. | `willplus-advhd` |
| `binarystar_extract.py` | [PSV-JP] BinaryStar (PCSG00389, Otomate × Design Factory, 2014) 剧本文本提取 | `idea-factory-stcm2l-psv-cp932` |
| `bir_extract.py` | ビルシャナ戦姫 ～一樹の風～ (NS) → 全文本 | — |
| `bir_extract2.py` | ビルシャナ戦姫 ～一樹の風～ (NS) → 全文本 | — |
| `bktr_merge.py` | 官方更新档（BKTR Patch RomFS）→ 本体 romfs 合并读取（hactool 对这类重打包件报 | — |
| `bktr_romfs.py` | NS 更新档「Patch RomFS / BKTR」读取器（不依赖 hactool，可直接读 .nsp/.nca） | `platform-switch-bktr` |
| `blackish_nca.py` | Blackish House sideA-> -Retour- (NS) 压缩 NCA（LZ4 桶树）解包 | — |
| `blackish_pc_extract.py` | [PC-JP] Blackish House sideA→（honeybee black 2016 / PC） | — |
| `blip_extract.py` | Butterfly Lip (PC / WillPlus-AdvHD) text extractor. | `willplus-advhd` |
| `brothers_kiss_extract.py` | ブラザーズ～恋するお兄さま＆もっと恋するお兄さま～ (Tiaramode, 2007, BGI/Ethornell) | `misc-engines` |
| `brouge_extract.py` | Butterfly Rouge (PC / WillPlus-AdvHD) text extractor. | `willplus-advhd` |
| `btf_carve.py` | 从 INSTALL.BIN 中按 fileinfo.psb.m.json 的 umd_root 表切出成员文件 | `m2-advengine-psb` |
| `btf_extract.py` | [PSP-JP] Beyond The Future -Fix The Time Arrows- 全文本提取 | `m2-advengine-psb` |
| `btf_mdf.py` | M2 PSB 的 MDF(MT19937) 外壳解密（PSP 版 Kaleido/ADVENGINE） | `m2-advengine-psb` |
| `btf_pgd.py` | PSP PGD（\\0PGD / drm_type=1 / mac_type=1）解密 | `m2-advengine-psb` |
| `btf_s2_extract.py` | BUSTAFELLOWS シーズン2（NS-JP）全文本提取 —— 自研 UTXT 容器 | — |
| `btf_unpack.py` | M2「ADVENGINE」PSB 盘 一键解包（PGD → 成员 → MDF → PSB） | `m2-advengine-psb` |
| `build_kure.py` | クレプシドラ 成品构建：scenario(ARC2) -> LZSS -> 正文成行 | — |
| `build_ls2.py` | ラスト・エスコート2 ～深夜の甘い棘～ 全文本生成 | `vsc-vdp-lsb` |
| `build_text.py` | ラスト・エスコート 〜黒蝶スペシャルナイト〜 全文本生成 | `d3p-ps2-fpk-vml` |
| `bwolves_extract.py` | BLACK WOLVES SAGA -Wei\u00df und Schwarz- (Switch, STCM2L) \u5267\u672c\u63d0\u53d6\u5668. | `idea-factory-stcm2l-switch` |
| `byakko_extract.py` | BYAKKO ～四神部隊炎恋記～ (NS-JP) 文本提取 | — |
| `cafe_extract.py` | Cafe Cuillere (PSV PCSG01197, DWANGO/Takuyo, gss engine) text extractor. | `takuyo-gss` |
| `cd_apply.py` | 用 cd_solve 的「条目→相手役」映射跑一次成品（诊断用，不写 提取结果/） | — |
| `cd_bin2iso.py` | MODE1/2352 · MODE2/2352 裸镜像 -> 2048 用户数据 ISO | `koei-embins-ps2` |
| `cd_blocks.py` | カスタムドライブ：用「单男角条目块」反查 相手役 id 字段 —— 报告 §11 步骤 2 的可重跑证据 | — |
| `cd_hdr.py` | カスタムドライブ 条目头（0x2000 B）探针 —— 报告 §11 步骤 1 的可重跑证据 | — |
| `cd_nameplate.py` | カスタムドライブ 名札（说话人）核验探针 —— 报告 §10 的可重跑证据 | — |
| `cd_ops.py` | カスタムドライブ L0 opcode 统计 —— 报告 §11 步骤 2 的可重跑证据 | — |
| `cd_solve.py` | カスタムドライブ FF0C（相手役の下名）定位器 —— 报告 §11 的可重跑证据/落地依据 | — |
| `cdar.py` | CDAR 容器读取库（被 cdar_extract.py import）：索引表 + 条目解压 | `koei-cdar` |
| `cdar_extract.py` | 递归解包 CDAR 容器（可下钻嵌套），逐条目落成原始字节 | — |
| `cend_extract.py` | Cendrillon palikA (NS) —— STCM2L 全文本提取 | — |
| `cfm_extract.py` | Confidential Money (PSP / Otomate 2012) .evb -> text. | `otomate-evb-marc` |
| `charset_audit.py` | 非日文字符台账审计：把每部成品里「kana/汉字/CJK标点/全角符号」以外的字符全部列出， | — |
| `chd_iso.py` | CHD v5 (zstd/lzma/none) -> 2048B/扇区裸 ISO，无 chdman 依赖 | — |
| `chou_decrypt.py` | 蝶の毒 華の鎖 XP3 内テキスト復号（区間 XOR 鍵推定）v3 | `kirikiri-xp3` |
| `chou_extract.py` | 蝶の毒 華の鎖 全テキスト抽出（KAG3 スクリプト → 表示テキスト） | `kirikiri-xp3` |
| `chou_fix.py` | 蝶の毒 華の鎖：復号後の局所的な文字化けを既知の正解で補正する表 | `kirikiri-xp3` |
| `chouchou_build.py` | 蝶々事件ラブソディック（PSV, L7CA + Lua5.3 变体字节码）正文提取 | — |
| `clep_lzss.py` | クレプシドラ ARC2 + LZSS 解压器 | — |
| `cloverlib2_extract.py` | クローバー図書館の住人たちⅡ (PC-JP / System-NNN「NNNLib」) 全文本提取 | — |
| `cloverlib_extract.py` | クローバー図書館の住人たち (PC-JP / 澪 / System-NNN「NNNLib」系) 全文本提取 | — |
| `clusteredge_extract.py` | Cluster Edge (PS2, SLPS_256.54) —— DataChain + MSDA 文本提取 | — |
| `colorful_bunka_extract.py` | 放課後colorful＊step～ぶんかぶ！～（PSP）全文本提取 | — |
| `colorful_undo_extract.py` | [PSP-JP]放課後colorful＊step～うんどうぶ！～ 全文本提取 | — |
| `corda_2fa_extract.py` | 金色のコルダ2f アンコール (PSP) 全文本提取器 v3. | — |
| `corda_2fa_get.py` | 按路径取出 CDAR v4 里某个叶子文件: corda_2fa_get.py <DATA.BIN> <base> <path> <out> | — |
| `corda_2fa_unpack.py` | 金色のコルダ2f アンコール (PSP) CDAR v4 解包器. | — |
| `corda_2ff_extract.py` | 金色のコルダ2 ff (PSVita, PCSG01124) 全文本提取器 | — |
| `corda_2ff_g1t.py` | 金色のコルダ2 ff : Koei G1T (GT1G0600) 字体图集解码 -> PNG | — |
| `corda_3_extract.py` | 金色のコルダ3 (PSVita, PCSG01211) 全文本提取器 | — |
| `corda_3as_extract.py` | 金色のコルダ3 AnotherSky feat.神南/至誠館/天音学園 (PSVita PCSG01212) 全文本提取器 | — |
| `corda_boxcheck.py` | 诊断: 同一文本框被拆? 对某个 コルダ 提取器, 找「间隔含追加码 1e7e02b205」的记录对, | — |
| `corda_octave_extract.py` | 金色のコルダ オクターヴ (Switch) 全文本提取器 v3 (定稿候选) | — |
| `corda_psp_extract.py` | 金色のコルダ (PSP) 剧本/文本提取器 (自包含, 无外部依赖) | — |
| `corda_psp_unpack.py` | 金色のコルダ (PSP) 容器解包 : ISO9660 -> CDVDAR.DAR (Koei CDAR v2) -> 嵌套 DAR | — |
| `cpk.py` | CRI CPK unpacker (纯 Python, 无依赖). | `broccoli-opfflow` · `cri-cpk-afs` · `d3p-koishiba` … |
| `cpk_cri.py` | CRI CPK (@UTF) 容器读取器 —— 最小可用实现（实测格式） | `cri-snbin-lzss` |
| `cpk_v1.py` | CRI CPK unpacker (v1 ITOC-style + v2/v3 @UTF), 纯 Python. | `cri-cpk-afs` · `idea-factory-stcm2l-psp-cpk-amen-garnet` |
| `crankin_extract.py` | クランク・イン (Crank In) — PSV / PCSG00941 / プチレーヴ (Puchireve) | — |
| `crazychain_extract.py` | CRAZY CHA!N -エルピスの鎖- (Nintendo Switch) 全文本提取 | `unity-adv-hscript` |
| `crazychain_xci.py` | CRAZY CHA!N -エルピスの鎖- (Switch XCI) → 切出 secure 分区内的 NCA | `idea-factory-stcm2l-switch-ghp` · `konami-unity-bytes-works` · `takuyo-gss-switch-scr2` … |
| `crimson_royale_extract.py` | クリムゾン・ロワイヤル (QuinRose, 2009 / KiriKiri KAG3, DropWave OTag system) | `kirikiri-xp3` |
| `dc_extract.py` | デス・コネクション ポータブル（PSP ULJM05823 / Otomate 2011） | — |
| `dc_glossary.py` | デス・コネクション ポータブル —— 用語辞典（fid 22 見出し語表 ＋ fid 23 解説チャンク） | — |
| `dcgs_extract.py` | D.C. Girl's Symphony Pocket (PSP, ULJM05690) 剧本文本提取 | `idea-factory-stcm2l-psp-uni2` |
| `dcode_carve.py` | XCI / NSP → 逐个 NCA 落盘（按 title 目录分），供后续流式取 romfs | — |
| `dcode_extract.py` | [NS-JP]DistortedCode ―生者の残り香― text extract (TAKUYO gss / SCR 3.00). | — |
| `dcode_scr.py` | GSS / SCR3 脚本批量解码入口（复用 himehibi_lsdarc 与 gss_scr3 两个库） | — |
| `dd_dump.py` | 把 7drops.scenarios.asset 里所有 .book 摊平成 TSV 供人工判读语义 | — |
| `dd_mkelf.py` | 把 NSO 平铺镜像包成最小 ELF64（AArch64），供 LibCpp2IL(TypeTreeGeneratorAPI) 读取 | — |
| `dd_utage.py` | Utage .book 解析（格式依据 storycraft/unity-utage-book 的 reader.rs） | `unity-text-carriers` |
| `desperadrops_extract.py` | DesperaDrops (NS-JP) 全文本提取 —— Utage 引擎 / .book 二进制 | — |
| `dessert_extract.py` | Dessert Love -Sweet Plus- (PS2) 全文本提取 | — |
| `dia_alice_extract.py` | ダイヤの国のアリス ～Wonderful Mirror World～ (PSP) 全文本提取 | — |
| `diary_ystb.py` | Diary（[PC-JP] Operetta 2011 / YU-RIS・YSTB v0x199）全文本提取 | — |
| `digit_extract.py` | [NS-JP]数乱digit For Nintendo Switch —— SCD 字节码文本提取 | — |
| `digit_scd.py` | yield (off, op, payload) | — |
| `dk_final.py` | [PS2-JP]drastic Killer 成品生成（一次点击 = 一行） | — |
| `dk_lib.py` | drastic Killer 容器库: ISO -> DATAxx.HD/BIN -> PACK -> 解压条目 | — |
| `dk_scpt.py` | SCPT 单条全解析：op 序列 + 池串 | — |
| `dk_stat.py` | DATA01 全条目解码闭合统计（写报告用） | — |
| `dk_trace.py` | 逐指令 trace（把 0x19 的 a/b 与 06 的串名解析出来） | — |
| `dms_extract.py` | DEAR My SUN!! ～ムスコ★育成★狂騒曲～（PS2 / HuneX IKA SEQ, SLPS_258.10）全文本提取 | — |
| `doublescore_advhd.py` | WillPlus / AdvHD —— Double Score 系列（Marguerite×Tulip 等）变体 | — |
| `dsb_extract.py` | Darling Special Backlash ～恋のエキゾースト・ヒート～ (PS2-JP, SLPM_656.53) | — |
| `dscatt_extract.py` | Double Score ～Cattleya×Narcissus～ 专用入口 | — |
| `dump_base.py` | even if TEMPEST 本体（未压缩 romfs NCA）→ 裸 romfs 镜像（0 = romfs 头） | — |
| `dup_probe.py` | 双版拼接探针：找「同一行内同一句出现两次」的行 | — |
| `dyc_extract.py` | DYNAMIC CHORD feat.[rêve parfait] Remaster edition (NS-JP, 010076902126e000) | — |
| `dycko_extract.py` | [PC-JP] DYNAMIC CHORD feat.KYOHSO Append Disc（honeybee black / ASGARD / PC 2016） | — |
| `dycls_extract.py` | [PC-JP] DYNAMIC CHORD feat.Liar-S Append Disc（honeybee black / ASGARD, PC-ISO） | — |
| `dycpc_extract.py` | [PC-JP] DYNAMIC CHORD feat.apple-polisher（honeybee black 2016-11-04 / PC） | — |
| `dydc_extract3.py` | DYNAMIC CHORD Remaster 系列 3 部（Liar-S / KYOHSO / apple-polisher）全文本提取 | — |
| `dydc_split.py` | XCI → secure 分区 NCA 手切（nsz 还原的 XCI 哈希不被 hactool 接受，故手工走 HFS0 链） | — |
| `dydc_stats.py` | 三作解析自证数据（供报告引用） | — |
| `edelblume_extract.py` | [PS2-JP] エーデルブルーメ (SLPM-66976 / Design Factory・Otomate 2008) 剧本文本提取 | — |
| `ees_extract.py` | END END SUMMER (KiriKiri / KAG3 派生) 文本提取 —— 双版对照 | — |
| `emu.py` | 模拟器辅助：截屏 + 发键（Windows，PIL + ctypes，无第三方 GUI 依赖） | — |
| `emu_bring.py` | 把模拟器（PCSX2/PPSSPP）窗口置前并截图 | — |
| `emu_dec.py` | 用 unicorn 模拟执行 SLPM 里的解压函数（0x142c80 = type1, 0x142a20 = type2） | `koei-pack-ps2` |
| `enbu_extract.py` | 戦場の円舞曲 for Nintendo Switch —— 全文本提取器 | — |
| `enkan_extract.py` | 円環のメモーリア -カケラ灯し- (PSV / PCSG01167 / A'sRing & Dramatic Create) 全文本提取器 | `hunex-ogre-dramaticcreate` |
| `epic_extract.py` | 終遠のヴィルシュ -EpiClycoris- —— STCM2L(Switch/2018型) → 全文本 | — |
| `etoile_final.py` | SCPT 目录 -> 最终全文本（一行 = 一次点击） | — |
| `etoile_script.py` | アンジェリーク エトワール (PS2) DATA02 脚本解包 | `koei-pack-ps2` |
| `etoile_script_par.py` | DATA02 脚本解包（多进程版） | — |
| `etoile_text.py` | 从解包出的 SCPT 里提取台词文本（一行 = 一个 message box） | `koei-pack-ps2` |
| `etoile_unpack.py` | アンジェリーク エトワール (PS2, SLPM_657.15, 2004 Koei/Ruby Party) 归档解包器 | `koei-pack-ps2` |
| `etude_extract.py` | Extract all displayed text from étude prologue 〜揺れ動く心のかたち〜 Portable | `takuyo-gss-psp` |
| `euchronia_trail_dup.py` | 定位成品的「相邻重复行」源于哪个脚本、何种结构（用于判是否互斥分支重复） | — |
| `euchronia_trail_extract.py` | 泡沫のユークロニア 剧本成行器（TIS 风格 [命令] 脚本） | — |
| `euchronia_trail_nca.py` | Blackish House sideA-> -Retour- (NS) 压缩 NCA（LZ4 桶树）解包 | — |
| `extract_alice.py` | Extract scenario text from the Alice-series PSP games (QuinRose). | — |
| `extract_text.py` | PSP アラビアンズ・シリーズ 脚本テキスト抽出 | — |
| `fhk2_extract.py` | フルハウスキス 2 (PS2, Capcom/TENKY, SLPM-662.88) —— 全文本提取（定稿） | — |
| `fix_multi_brackets.py` | 一行多个框的拆行（独白 （A）（B） / 台词 「A」「B」） | — |
| `fix_wrap_pairs.py` | 框内软换行被切成两行的修复（跨行续行收拢 / 缺引号补齐） | — |
| `fortissimo_extract.py` | 《フォルティッシモ》 (PS Vita / PCSG01131 / KADOKAWA x Otomate / 2018-03-08) 全文本提取 | — |
| `fpk.py` | FPK 容器头解析：条目表（名 / 偏移 / 大小）→ 可选导出 JSON，附扩展名直方图 | `d3p-ps2-fpk-vml` |
| `fpkx.py` | FPK 解包（可给外部索引只取指定条目；重名自动加序号，不覆盖） | `d3p-ps2-fpk-vml` |
| `fsymph_extract.py` | for Symphony ポータブル (PSP-JP, Takuyo, ULJM05258, v1.01) full-text extractor. | `takuyo-gss-psp-symphony` |
| `fullscan.py` | 逐个归档条目试解压，按「含日文字数」排序 —— 先定位正文在哪一层容器 | — |
| `gakeppuchi_extract.py` | 崖っぷち令嬢は無気力悪魔で乙女を捨てたい（YU-RIS / YPF v500）全文本提取 | — |
| `gakuenk_extract.py` | 学園K -Wonderful School Days- V Edition (PSV, PCSG00654, Otomate / Idea Factory) | `gakuenk-dat-scr` |
| `garnet_extract.py` | ガーネット・クレイドル ポータブル ～鍵の姫巫女～ (PSP, 2011 / STCM2L "Minku 07.0") | `idea-factory-stcm2l-psp-cpk-amen-garnet` |
| `garnet_pc_extract.py` | GsWin / DataPack5 (Takuyo PC) —— Scw5.x 剧本文本提取（一次点击 = 一行） | — |
| `garnet_pc_pak.py` | GsWin / DataPack5 (Takuyo PC) —— .pak 解包 + Scw5.x 脚本解码 | — |
| `genji_extract.py` | QuinRose Qoo (PSV) —— [PSV-JP]源氏恋絵巻 剧本成行 | — |
| `gensou_decode.py` | 蝶の毒 華の鎖 ～幻想夜話～ XP3 内テキスト復号 v3（確定復元表方式） | `kirikiri-xp3` |
| `gensou_extract.py` | 蝶の毒 華の鎖 ～幻想夜話～ 全テキスト抽出（KAG3 スクリプト → 表示テキスト） | `kirikiri-xp3` |
| `gessan_extract.py` | 月影の鎖 -狂爛モラトリアム- (NS) 文本提取 — Takuyo gss / SCR 2.00 / LSDARC V.100 | — |
| `geten_extract.py` | 下天の華 with 夢灯り (PSVita PCSG00921) 全文本抽取器 | `koei-cdar` |
| `ghp_extract.py` | Glass Heart Princess for Nintendo Switch —— 全文本提取器 | `idea-factory-stcm2l-switch-ghp` |
| `ginkoku_build2.py` | 成行（v2）：源 = _work_ginkoku/out2（按 tpm 真算法解出的台本） | — |
| `ginkoku_cx_run2.py` | 用 cx_vm2 的真算法批量解密 scenario/*.txt → out2/，并做坏字节统计 | — |
| `ginkoku_cx_vm2.py` | 銀の冠碧の涙 —— 按 silverblue.tpm 真实代码重写的 CX 解密器（无任何补丁表） | — |
| `glasu_extract.py` | 硝子の森 (PS2-JP / D3PUBLISHER SIMPLE2000 Vol.13 / HuneX "ebf") 容器 + LZSS | — |
| `glasu_text.py` | 硝子の森（PS2-JP / D3P SIMPLE2000 Vol.13 / HuneX "ebf" Ver 0.30）文本提取 | — |
| `glyph_pick.py` | 在「语境候选字」之间做字形比对（仅用于验证假设，勿当 OCR 用） | — |
| `goes_extract.py` | Goes! (PCSG00367) 文本提取 | — |
| `grim_extract.py` | グリム・ザ・バウンティハンター（PSP / QuinRose / KiriKiri KAG .ks）文本提取 | — |
| `gss_codec.py` | GSS / LSDARC 'LSD\\x1a' codec (Takuyo gss engine). | `takuyo-gss-switch` |
| `gss_lsdarc.py` | LSDARC V.100 container (Takuyo gss). Index = "<NAME>.BIN", data = "<NAME>.ARC". | `takuyo-gss-psp-hoshiiro` · `takuyo-gss-psp-littleaid` · `takuyo-gss-psp-symphony` … |
| `gss_scr3.py` | SCR 3.00 (Takuyo gss / Switch) disassembler. | `takuyo-gss-switch` |
| `hakken_extract.py` | 転生八犬士封魔録 (PS2-JP, SLPM_663.96) —— SC.AFS 全文本提取 | — |
| `hakuoki_ns_build.py` | 薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— 成品构建（正文＋选项＋扉文＋用語辞典） | — |
| `hakuoki_ns_extract.py` | 薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— STCM2L 文本提取器（v1，逐文件调试输出） | — |
| `hakuoki_ns_extract2.py` | 薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— STCM2L 提取器 v2 | — |
| `hakuoki_zuisouroku_extract.py` | 薄桜鬼 随想録 面影げ花 (PSV, PCSG00485, Idea Factory / Otomate) | `idea-factory-stcm2l-psv-g` |
| `hakushaku_afs.py` | CRI AFS (\x00SFA) minimal extractor for 5pb PS2 titles. | — |
| `hakushaku_extract.py` | Hakushaku to Yousei (PS2, 5pb) scene text extractor. | — |
| `hanayoi_afs.py` | AFS0（AFS\0）归档索引解析：条目偏移/大小 → 取数据 | `cri-cpk-afs` |
| `hanayoi_extract.py` | 返回 (lines, unknown) | `cri-cpk-afs` |
| `hanayoi_run.py` | 批量驱动 hanayoi_extract.py：多脚本合并成一份成品（一次点击 = 一行） | `cri-cpk-afs` |
| `hanazakari_extract.py` | 花朧 ～戦国伝乱奇～ (PSV, PCSG00855, Otomate/Idea Factory) 文本提取 | — |
| `handsome_bktr.py` | ハンサムロンダリング 更新档（Patch RomFS / BKTR）比对工具 | — |
| `handsome_nca.py` | ハンサムロンダリング -the mystic lover- (NS) 压缩 NCA（LZ4 桶树）解包 | — |
| `handsome_updraw.py` | ハンサムロンダリング 更新档（BKTR + LZ4 桶树）→ 最新 romfs 文件比对/提取 | — |
| `haruka2_appmatrix.py` | 从 BOOT.BIN 读取 16x16「呼び名」称呼矩阵 | — |
| `haruka2_eem_extract.py` | 遙かなる時空の中で２ (PSP) 全文本提取 — 最终版 | — |
| `haruka2_eemlib.py` | Return (headerFields, sectionA, sectionB) for KOEID0 entry i. | — |
| `haruka4_extract.py` | Extractor for 遥かなる時空の中で4 (PSP, Koei / Ruby Party). | — |
| `haruka5_extract.py` | 遙かなる時空の中で5 (PSP / ULJM-05821, Koei / Ruby Party) 全文本提取器 | `koei-cdar` |
| `haruka6_dedup.py` | 遥かなる時空の中で6 DX —— 变体分支后处理：保留「默认名版」，删除「不含名字/泛指」的替代句 | — |
| `haruka6_dict.py` | 遥かなる時空の中で6 DX —— 用語辞典（見出し語＋解説）构建器 v2 | — |
| `haruka6_extract.py` | 遥かなる時空の中で6 DX (Switch) 全文本提取器 v2 | — |
| `haruka_extract.py` | Extractor for Koei / Ruby Party "Harukanaru Toki no Naka de" (遥かなる時空の中で) scripts. | — |
| `heiligenstadt_extract.py` | 《ハイリゲンシュタットの歌》 (PS Vita / PCSG01070 / eXtend / Unity 5.6.1p4) 全文本提取 | `unity-adv` |
| `himehibi2_eboot.py` | ひめひび 続！二学期 —— 第 2 段：eboot 串表抽取 + 成品组装 | — |
| `himehibi2_extract.py` | Extract all displayed text from ひめひび ─New Princess Days!!─ 続！二学期 | — |
| `himehibi2ns_extract.py` | ひめひび ─New Princess Days!!─ 続！二学期 (NS-JP 01009B4012FC6000) 全文本提取 | — |
| `himehibi_crawl.py` | ordered list of callee script names (0x1e / 0x1d). | `takuyo-gss` |
| `himehibi_disasm.py` | SCR 2.00 (Takuyo gss / LSDARC) disassembler with auto-calibrated operand sizes. | `takuyo-gss-psp-hoshiiro` · `takuyo-gss-psp-littleaid` · `takuyo-gss-psp-symphony` … |
| `himehibi_extract.py` | Extract all displayed text from ひめひび -Princess Days- (PSV, Takuyo gss / LSDARC 'SCR 2.00'). | `takuyo-gss` |
| `himehibi_lsdarc.py` | LSDARC V.100 (Takuyo gss engine) reader. | `takuyo-gss-psp` · `takuyo-gss-switch-scr2` · `takuyo-gss` |
| `himehibi_ns_extract.py` | ひめひび -Princess Days-（NS-JP, 0100F8D0129F4000）全文本提取 | — |
| `honeyvibes_extract.py` | Honey Vibes (NS 0100FB301E70A000) 剧本提取 —— Unity + 纯文本脚本 | `unity-text-carriers` |
| `hoshifuru_extract.py` | 星の降る刻 (PS2-JP) —— UNION/SCRIPT.UNI 文本提取 | — |
| `hoshiiro_extract.py` | 星色のおくりもの (PSP-JP, 2008 Takuyo) full-text extractor. | `takuyo-gss-psp-hoshiiro` |
| `hunex_hlzs.py` | HuneX HLZS（LZSS）解码器：dict 0x1000 / maxlen 0x12，解 script_dialog_xx.hdlg 等 HLZS 载荷 | `hunex-hesl` |
| `il2cpp_fields.py` | 纯 Python 读 IL2CPP global-metadata.dat 的类型定义/字段表（不反编译、零依赖） | — |
| `incest_crack.py` | 周期 keystream 破解：c[i] = p[i] ^ key[i % P]，key 每文件独立 | — |
| `incest_filter.py` | INNOCENT INCEST —— XP3 filter 解密（依据 sindata.tpm rva 0x1000 反汇编） | — |
| `incest_xp3.py` | INNOCENT INCEST data.xp3 —— 索引解析（带 flag/adler32），供攻坚探查用 | — |
| `iowatch.py` | 按秒采样进程 I/O 计数与文本槽变化，定位"一次点击读了多少字节、出现哪些新文本" | — |
| `iso9660.py` | 极简 ISO9660 列目录 / 抽取（无依赖，支持 PSP UMD 镜像） | `d3p-koishiba` |
| `iso_cut_cpk.py` | ISO9660 内指定 LBA 的 CPK 切出并解包 —— PSP（Zerodiv / CRI CPK 系）通用驱动 | `otomate-evb-marc` |
| `isshoni_gohan_extract.py` | いっしょにごはん | — |
| `iza2_build.py` | いざ、出陣！恋戦 第二幕 ～甲斐編～ —— 按 scenelist 顺序组装全文本 | — |
| `iza2_unpack.py` | いざ、出陣！恋戦 第二幕 甲斐編 —— 批量解壳 + PSB 反编译 | — |
| `izasen_cpk.py` | いざ、出陣！恋戦 data.cpk 解包（CPK 名 cp932 修正版） | `cri-cpk-afs` |
| `izasen_extract2.py` | いざ、出陣！恋戦（PSP）全文本提取 v2：按 [next file] 链定顺序 | `cri-cpk-afs` |
| `izasen_stream.py` | いざ、出陣！恋戦 data.cpk → 剧本流还原 | `cri-cpk-afs` |
| `jewelic_extract.py` | Jewelic Nightmare (PSP, Otomate 2013, ULJM06326) 全文本提取 | `idea-factory-stcm2l-psp-cpk` |
| `jusanshi.py` | 十三支演義 偃月三国伝1・2 (NS) 正文提取 —— 容器链全部打通版 | — |
| `jusanshi_dialog.py` | 十三支演義 偃月三国伝1・2 正文提取（AdvScript / MessagePack 容器） | — |
| `kaeru_extract.py` | カエル畑DEつかまえて☆彡 (NS-JP, TAKUYO) text extract. | `takuyo-gss-switch-scr2` |
| `kaleido_extract.py` | カレイドイヴ (PSV / PCSG00520 / estciel & HuneX) 全文本提取器 | — |
| `kamikoi_extract.py` | 神さまと恋ゴコロ (NS-JP) text extract ---- Takuyo gss / LSDARC 'SCR 3.00'. | `takuyo-gss-switch` |
| `kamisama_extract.py` | もし、この世界に神様がいるとするならば | — |
| `kannagi_extract.py` | 神凪ノ杜 五月雨綴り (NS-JP, Unity 2021 IL2CPP, Matatabi) 剧本正文 + 选项提取 | `matatabi-unity-textadv` |
| `kannou_extract.py` | 官能昔話 ポータブル (PSP, ULJM06015, vndb v9071) 全文本提取 | `idea-factory-stcm2l-psp-cpk-kannou` |
| `kanuchi_dict.py` | カヌチ 二つの翼 用語辞典（ライブラリ）提取 | `idea-factory-ydp-lsb` |
| `kanuchi_text.py` | カヌチ 二つの翼 (PSP / Idea Factory 'YDP1' -> SCRIPT_LSB) 剧本文本提取 | `idea-factory-ydp-lsb` |
| `kanuchi_ydp.py` | カヌチ 二つの翼 (PSP / Idea Factory 'YDP1') 解包 | `idea-factory-ydp-lsb` |
| `kazahanaki_extract.py` | 遙かなる時空の中で5 風花記 (PSP / ULJM-05950, Koei / Ruby Party) 全文本提取器 | `koei-cdar` |
| `kaze_extract.py` | 風色サーフ (PS2) 全文本抽出器 | — |
| `kedamono_ns_build.py` | 猛獣使いと王子様 ～Flower & Snow～ for Nintendo Switch —— 成品构建 | — |
| `kedamono_ns_extract.py` | 猛獣使いと王子様 ～Flower & Snow～ (NS) STCM2L 提取：一次点击 = 一行 | — |
| `kimikare_extract.py` | キミカレ ～キミとカレはじめました～ (PSP, 2012 / STCM2L) 文本提取 | — |
| `klap_extract.py` | KLAP!! for Nintendo Switch (NS) STCM2L 文本提取（STCM2L Apr 12 2018 18:22:39 变体） | — |
| `klap_trace.py` | KLAP!! STCM2L 单段 opcode 追踪：看「一行多句」在代码层是怎么分隔的 | — |
| `koei_dec.py` | アンジェリーク エトワール (PS2) PACK 成员解压 —— 由 SLPM 0x142c80 (type1) 反编译还原 | `koei-pack-ps2` |
| `koibana_extract.py` | 恋花デイズ (PSP / Otomate, STCM2L in CRI CPK) 文本提取 | — |
| `koibann2_extract.py` | 恋愛番長2 MidnightLesson!!! (PSP-JP / Rejet×Otomate 2011) 剧本文本提取 | `idea-factory-stcm2l-psp-uni2-banchou2` |
| `koibann_extract.py` | 恋愛番長 命短し、恋せよ乙女！ Love is Power (PSP-JP / Rejet×Otomate 2010) 剧本文本提取 | `idea-factory-stcm2l-psp-uni2-banchou` |
| `koigig_extract.py` | KoiGIG ～DEVIL×ANGEL～ (TWOFIVE / DonMaccow, 2007) 文本提取器 | `misc-engines` |
| `koinohana_extract.py` | [NS-JP]恋の花咲く百花園 text extract (Takuyo gss / SCR 3.00, unpacked OBJ). | — |
| `koishiba_charset.py` | 恋は校則に縛られない！（PSP / Vridge・Kadokawa Games）—— sc.cpk 字符集与专用槽 | `d3p-koishiba` |
| `koishiba_font.py` | 恋は校則に縛られない！（PSP / Vridge・D3P 系）lt.bin 字形渲染 | `d3p-koishiba` |
| `koishiba_run.py` | 恋は校則に縛られない！（PSP）—— USRDIR/DATA/sc.cpk → 全文本 | `d3p-koishiba` |
| `kuro_build.py` | 蒼黒の楔 (NS-JP, Unity/Utage) 剧本 → 全文本（双版对照） | — |
| `kuro_dump.py` | 蒼黒の楔 (NS) — Unity AdvChapterData/AdvImportBook 剧本落盘 | — |
| `l2ll_extract.py` | L2 Love×Loop (PS2 / Idea Factory / SLPM-55191) 剧本文本提取 | `idea-factory-stcm2l-ps2-uni2` |
| `l7c.py` | L7CA (Bandai Namco / Vita resource archive) 解包器 | — |
| `lamento_extract.py` | Lamento -BEYOND THE VOID- (Windows 10 Support Edition) — Nitroplus NPA / NSS | `nitroplus` |
| `lastconvert_extract.py` | Last Convert (NScripter / nscript.dat, 全字节 XOR 0x84) -> 双版对照文本 | — |
| `lastescort_cmp.py` | 对比 深夜の黒蝶物語（本编）与 黒蝶スペシャルナイト（追加碟）的 ADV.FPK / VML | — |
| `lastescort_extract.py` | ラストエスコート -Club Katze- (PSP) 全文本提取 —— 通用驱动 | `lastescort-paf` |
| `lastescort_ps2_extract.py` | ラスト・エスコート 〜深夜の黒蝶物語〜 (PS2 / SLPS_255.91 / D3P・Vingt-et-un) 全文本提取 | `lastescort-vml-ps2` |
| `lastescort_vml.py` | ラスト・エスコート 〜黒蝶スペシャルナイト〜 (PS2-JP / D3PUBLISHER, SLPS_256.73) | `d3p-ps2-fpk-vml` |
| `libp_malievita.py` | Malie（Vita）Libp 归档读取库：入口表 / 文件名 / 数据切片 | `malie` |
| `littleaid_extract.py` | Little Aid Portable (PSP-JP, 2007 Takuyo, ULJM-05...) full-text extractor. | `takuyo-gss-psp-littleaid` |
| `littleanchor_extract.py` | リトルアンカー（PS2-JP / SLPS-25929 / Vridge）全文本提取 | — |
| `lovebeat_extract.py` | 放課後のLove Beat（PS2 / HuneX ADVD, SLPM_655.79）文本提取 | — |
| `lovepeace_extract.py` | 恋戦隊LOVE＆PEACE THE P.S.P. (PSP / BROCCOLI 2012) MES.DAT text extractor. | `lovepeace-adv` |
| `loverevo_extract.py` | 乙女的恋革命★ラブレボ!! Portable (PSP) 全文本提取 | `hunex-ogre-loverevo` |
| `loveroot_extract.py` | PS2『ラブルートゼロ kisskiss☆ラビリンス』(Dimple/Asgard 2010) 全文本抽出 | — |
| `lsb.py` | LSB 剧本解析（VSC 引擎 / ラスト・エスコート2 ～深夜の甘い棘～ PS2-JP） | `vsc-vdp-lsb` |
| `lua51.py` | Lua 5.1 bytecode 解析（Vita/PSV 乙女作常见：脚本编译为 luac 5.1） | — |
| `lua53.py` | Lua 5.3 luac 解析（PSV 变体：32 位、lua_Number=float32、varint 长度） | — |
| `lucian_extract.py` | Lucian Bee's: Resurrection Supernova (PSP, 2010, HuneX IKA SEQ SYSTEM v3.4) | `hunex-ika-seq-lucian` |
| `lucianj_extract.py` | Lucian Bee's: Justice Yellow (PSP, 2010, 5pb./HuneX) —— 全文本提取 | `hunex-als` |
| `lucianv_extract.py` | Lucian Bee's: Evil Violet (PSP, 2010, 5pb) —— 全文本提取 | `hunex-als` |
| `lzo1x.py` | LZO1X-1 (miniLZO) 解压器 + event.enc entry 解压测试 | `zerodiv-cpk-extra-files` · `zerodiv-lzo1x` |
| `majikyun_extract.py` | マジきゅんっ！ルネッサンス (PSV / PCSG00852 / HuneX & BROCCOLI) 全文本提取器 | `hunex-ogre` |
| `makumatsu_extract.py` | 《幕末Rock 超魂》(PS Vita / PCSG00425 / Marvelous) 全文本提取 | `mz-cmdstream` |
| `malie_extract.py` | Malie System (GreenWood) 通用提取工具 —— OmegaVampire repack / 断罪のマリア 实证. | `malie` |
| `manimani_extract.py` | 花咲くまにまに (PSV, PCSG00366, MAGES. / SC3) 文本提取 | `mages-sc3-mpk` |
| `marc_font.py` | 5pb PSP (Musketeer/EVB engine) MARC font atlas unpacker. | `musketeer-psp-evb` |
| `marginal4_extract.py` | [PSV-JP] MARGINAL#4 IDOL OF SUPERNOVA (PCSG00448, Otomate x Rejet / Idea Factory) | `idea-factory-stcm2l-psv-cp932` |
| `marginal4rtg_extract.py` | [PSV-JP] MARGINAL#4 ROAD TO GALAXY (PCSG01008, Otomate x Rejet / Idea Factory) | `idea-factory-stcm2l-psv` |
| `matsurika_build.py` | マツリカの炯-kEi- 天命華燭伝 文本成行（在 matsurika_extract 之上） | — |
| `matsurika_extract.py` | マツリカの炯-kEi- 天命華燭伝 (NS-JP) 全文本提取 | — |
| `meiji_extract.py` | 明治活劇 ハイカラ流星組 (NS-JP) テキスト抽出. | `meiji-haikara-lzs` |
| `meiji_lzs.py` | 明治活劇 ハイカラ流星組 (NS-JP) の .lzs 解凍器 (c) 2026. | `meiji-haikara-lzs` |
| `meine_extract.py` | [PS2-JP] マイネリーベ 優美なる記憶 text extractor. | — |
| `memdump.py` | 从进程内存 dump 一段区间到文件 | — |
| `memscan.py` | 扫描另一个进程的内存，按多种编码查找关键词（用于判断某段文本在运行时是否以明文存在） | — |
| `memtext.py` | 遍历进程内指定 guest 地址区间的已提交区域，就地提取 cp932 日文段落 | — |
| `merge_name_variants.py` | 双版拼接合并工具（名字宏双版 / 点名版↔泛称版） | — |
| `mermaid_run.py` | マーメイドプリズム (PS2-JP) 全文本提取 | — |
| `mermaid_scan.py` | マーメイドプリズム (PS2, SLPS_256.96) — ADVIMG.ADP 内 VML 走查/统计 | — |
| `mermaid_vml.py` | マーメイドプリズム VML 提取库（ADP 容器 + JIS7 字符串池 + 32bit op 流） | — |
| `minus8_extract.py` | マイナスエイト (-8) PSP, Otomate/Rejet, ULJM06341, vndb v12155 —— 全文本提取 | `idea-factory-stcm2l-psp-cpk` |
| `mips_xref.py` | 线性扫描 + lui/addiu 地址恢复（PS2 R5900） | — |
| `mist_extract.py` | ミストニアの翅望 -The Lost Delight- —— Unity/UTXT 文本（与 テミラーナ 同引擎） | — |
| `mist_romfs.py` | ミストニアの翅望 —— 压缩 NCA(BKTR/LZ4 bucket-tree) → RomFS 直读（复用 redbell_romfs 的桶树实现） | — |
| `mitsu_extract.py` | 蜜×蜜ドロップス LOVE×LOVE HONEY LIFE (PS2-JP, SLPM-663.81 / Otomate·Design Factory 2006) | — |
| `mizu2_extract.py` | 水の旋律2 ～緋の記憶～ (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本 | `thfs-mizu` |
| `mizu_extract.py` | 水の旋律 (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本 | `thfs-mizu` |
| `mizumelody_arc.py` | 水の旋律 ～協奏曲～ (PC, KID/mlk ADV 引擎) ARC0 归档解包 | `arc0-mlk-adv` |
| `mizumelody_text.py` | 水の旋律 ～協奏曲～ (PC) 剧本成行 —— mlk/ADV 脚本 (cp932) | `arc0-mlk-adv` |
| `ml2_disasm.py` | 最小 MIPS R5900 反汇编器（capstone 封装）——用于读 SLPM 里的解压函数 | — |
| `ml2_emul.py` | 直接执行 SLPM_662.47 内的解压例程（unicorn, MIPS64/R5900 子集）. | — |
| `ml2_text.py` | 从 SCPT 场景脚本抽取正文/选项（一行＝一次点击） | — |
| `ml2_tkl.py` | [PS2-JP] マイネリーベII tkl 容器 + type-2 解压 全链路工具. | — |
| `ml2_type2.py` | Konami tkl 'type 2' (flags&0xF==2) 解压器 —— 逆向自 SLPM_662.47 0x135e30 | — |
| `ml2_unpack.py` | [DEPRECATED] 已被 ml2_tkl.py 取代（本文件的 flags=1 LZSS / flags=2 实现均不正确） | — |
| `moneyparasite_extract.py` | Money Parasite 〜嘘つきな女〜 (TAKUYO gss / SCR 2.00) text extractor. | — |
| `mono_extract.py` | Monochrome Factor - Cross Road (PS2, 5pb) scene text extractor. | — |
| `moon_atl_extract.py` | 月ノ光太陽ノ影 (PC/ATL engine) 全文本提取 | `aromarie-atl` |
| `mothergoose_extract.py` | マザーグースの秘密の館（PSP / 2011, Otomate）文本提取 | — |
| `musketeer_charset.py` | Musketeer (PSP/5pb) .evb text decoder -- solved 2026-10-13. | `musketeer-psp-evb` · `otomate-evb-marc` |
| `musketeer_extract.py` | Musketeer (PSP/5pb) .evb -> text. | `musketeer-psp-evb` |
| `musketeer_render_atlas.py` | 5pb PSP MARC font-atlas renderer (ar999_0000.bin). | — |
| `mysteria_extract.py` | 英国探偵ミステリア The Crown (PSV, Malie System / MalieVita) exec.dat -> text. | `malie` |
| `mysteria_text.py` | 英国探偵ミステリア The Crown (PSV) —— Malie exec.dat → 全文本（一次点击 = 一行） | `malie` |
| `nana_extract.py` | [PS2-JP] NANA -ナナ- text extractor. | — |
| `nana_unpack.py` | [PS2-JP] NANA -ナナ- STORY/ALLSC.NKP 解包（Konami NKP 嵌套） | — |
| `naninovel_assemble.py` | 把 naninovel_extract.py 的 _scripts.json 组装成 §0 规范成品 txt | `naninovel-unity` |
| `naninovel_extract.py` | Naninovel (Unity IL2CPP) 脚本文本提取器 | `naninovel-unity` |
| `nca_romfs.py` | 通用：NSP/NCA 就地读 romfs（不落副本） | — |
| `nca_stream_romfs.py` | Switch 容器流式取 romfs 文件（不落 NCA/NSP 副本，省盘） | — |
| `neoange_psp_extract.py` | ネオアンジェリークSpecial (PSP-JP, Koei) 全文本提取 | `koei-cdar` |
| `neoangelique_extract.py` | ネオ アンジェリーク 天使の涙 (PSV-JP, PCSG01068, Otomate / Idea Factory) 全文本提取 | `gakuenk-dat-scr` |
| `neon_dialog.py` | ネオンクラッシュ -Echoes of the Lost- 正文提取（成品生成） | `unity-text-carriers` |
| `neon_findtext.py` | 用 UnityPy 逐个加载 bundle（真解压），统计对象 raw 里的假名数量，找出「文本库」所在 bundle | — |
| `neon_nca.py` | ネオンクラッシュ (NS) 压缩 NCA（LZ4 桶树）解包 —— 内容密钥由 ticket 解出后经 NCA_KEY 传入 | — |
| `niladmirari_extract.py` | ニル・アドミラリの天秤 色ドリ撫子 (Switch) —— 全文本提取器 | `idea-factory-stcm2l-switch` |
| `nisenochigiri_extract.py` | 二世の契り (PSP-JP, Otomate, 2011) 全文本提取 | `idea-factory-stcm2l-psp-cpk-niseno` |
| `noa_unpack.py` | Entis GLS / ERISA 'noa' archive unpacker. | — |
| `norn9_extract.py` | Norn9 ～Norn + Nonette～ Act Tune (PSV, PCSG00833) 剧本文本提取 | `idea-factory-stcm2l-psv` · `idea-factory-stcm2l` |
| `npa_nrbf.py` | Nitroplus NPA 内 NRBF（.NET BinaryFormatter）序列化数据的解析器 | `nitroplus` |
| `ns_dual.py` | NScripter（nscript.dat，整文件 XOR <key>）-> 「双版对照」全文本 | — |
| `ns_extract.py` | NScripter (nscript.dat) 全文本提取器 —— 「双版对照」口径 | — |
| `ns_open.py` | NS 统一入口 —— 一条命令走完 XCI/NSP/NCA 的判定与解包，并**打印为什么选这条路** | — |
| `ns_rip.py` | NScripter (nscript.dat) 文本提取器 | — |
| `nsac.py` | NSAC (v2) 容器解析/解包 —— eXtend 系 PSVita 作品《逢魔が刻 ～かくりよの縁～》(PCSG00769) | `misc-engines` |
| `nso_x.py` | NSO0 -> 平铺镜像（text/rodata/data 依次拼接，LZ4 段自动解压） | `nis-cpk-snbin` |
| `nsp_pfs0_dump.py` | 纯 Python 解析 PFS0(NSP) 并导出条目（hactool 吃不了 CJK 路径） | — |
| `nsp_plainromfs.py` | 通用：NSP/PFS0（或裸 NCA）内**未压缩** RomFS 的就地列出/提取 | `platform-switch-bezel-bea-scne` |
| `nsp_romfs_bulk.py` | NSP 内 romfs 批量就地提取（按正则/大小筛选），一次开 NCA 多次落盘 | — |
| `nsp_split.py` | PFS0(NSP) 逐块直拷拆分器 —— 规避 hactool --pfs0dir 对 >1.7GB 成员写全零的问题 | `broccoli-opfflow` · `konami-unity-bytes-works` · `nis-cpk-snbin` |
| `oga_sts_extract.py` | O*G*A 鬼ごっこロワイアル ハンターは孤島で恋をする (PSP-JP / Idea Factory・Otomate) | `oni-psp-tob` |
| `oga_tob_extract.py` | O*G*A 鬼ごっこロワイアル (PSP, Idea Factory/Otomate "oni") —— .tob 字节码级框提取 | `oni-psp-tob` |
| `omegavamp_extract.py` | オメガヴァンパイア (NS) SCRIPT.PAK → 全文本（一行＝一次点击） | — |
| `omegavamp_nca.py` | オメガヴァンパイア(NS) 专用 NCA/RomFS 按需解密提取器（不改共用 scripts/switch_nca.py） | — |
| `orange_build.py` | Orange Honey 全文本成行 | — |
| `orange_dump.py` | 导出全部 .OHS 的字符串池为 TSV（file, idx, off, text） | — |
| `orange_ohs.py` | OHS 文本段解密：blob 从 0x28 指向处到文件尾，SBOX(0x40..0x140) 递减异或解密 | — |
| `orange_peta.py` | Orange Honey (PS2, guyzware) — PETA(PTH/PTD) 解包 | — |
| `orfleur_extract.py` | オルフレール ～幸福の花束～ (PSV PCSG00919 / dramatic create「Orfre」DCVM) 文本提取 | `orfre-dcvm` |
| `orfleur_stbl_extract.py` | オルフレール ～幸福の花束～ (PSV / PCSG00919, dramatic create「Orfre」/ DCVM) | `orfre-dcvm` |
| `orfleur_trace.py` | Orfre/DCVM 执行序追踪（CFG 走块 + 调用捕获）——用于确定「一次点击=一行」的显示序 | `orfre-dcvm-history` |
| `orfleur_vm.py` | Orfre/DCVM 线性走链器：用于恢复「一次点击 = 一行」的文本序 | `orfre-dcvm-history` |
| `otome_kayuu_extract.py` | Otomate STCM2L · Switch「函数指针型」文本提取（燃えよ！乙女道士 ～華遊恋語～） | — |
| `ouma_build_text.py` | 《逢魔が刻 ～かくりよの縁～》系统/资料文本整理 | `misc-engines` |
| `ouma_extract.py` | 《逢魔が刻 ～かくりよの縁～》(PSVita / PCSG00769) 游戏内文本提取 | `misc-engines` |
| `ouma_story.py` | 《逢魔が刻 ～かくりよの縁～》本編 ADV シナリオ抽出 (NML スクリプト) | `misc-engines` |
| `ouran_extract.py` | 桜蘭高校ホスト部 (PS2-JP, SLPM-667.38 / Otomate·Idea Factory 2006) 剧本文本提取 | — |
| `ozmafia_extract.py` | OZMAFIA!! -vivace-（Nintendo Switch, 01002BE0118AE000, HuneX「Ogre」系 Switch 变体） | `hunex-ogre-ozmafia` |
| `ozmafia_nca.py` | NCA 头/key area 检视器（Switch）—— 用于旧 hactool 无法处理的 BKTR 增量补丁 NCA | `hunex-ogre-ozmafia` · `naninovel-unity` · `platform-switch-nca` |
| `pandora_extract.py` | PANDORA ～君の名前を、僕は知る～ (PS2, Otomate / Idea Factory 2010) 剧本文本提取 | `idea-factory-stcm2l` |
| `panic_extract.py` | Panic Palette (NS-JP, TAKUYO) text extract. | — |
| `paradigm_paradox_extract.py` | Paradigm Paradox (Regista advGame engine) 全文本提取器 —— 定稿 | `misc-engines` |
| `pc_snr_order.py` | 从 PC 汉化补丁的 .snr（UTF-16LE KiriKiri 脚本）提取「剧情序」标尺 | `orfre-dcvm-history` |
| `pcube_extract.py` | ピリオドキューブ ～鳥籠のアマデウス～ (PSV, PCSG00853) 剧本文本提取 | — |
| `pe_dis.py` | PE 反汇编辅助（capstone）：按 RVA/VA 定位并打印附近指令 | — |
| `pentagon_build.py` | Pentagon Syndrome（LiveMaker/LiveNovel LSB v117）成行器 | — |
| `pentagon_extract.py` | Pentagon Syndrome（LiveMaker/LiveNovel LSB v117）文本提取 | — |
| `pentagon_vff.py` | LiveMaker VFF 资源包解包（Pentagon Syndrome / 单 exe 全内嵌） | — |
| `period55.py` | 55 字节周期 XOR 键的爆破与验证（用于 .het 辞书） | — |
| `peterpan_extract.py` | QuinRose Qoo (PSV) —— [PSV-JP]新装版 お菓子な島のピーターパン 剧本成行 | — |
| `petitfour_extract.py` | プティフール (PS2-JP, SLPM-66945 / Otomate·Design Factory 2008) 剧本文本提取 | — |
| `pnm_extract.py` | Princess Nightmare (PS2, SLPM-66973) script text extractor. | — |
| `poi_extract.py` | 『っポイ!』ひと夏の経験!? (PS2-JP, SLPM-55012 / Otomate·Design Factory 2008) 剧本文本提取 | — |
| `possession_extract.py` | Extractor for Possession Magenta (ポゼッション マゼンタ, PSV, PCSG00509). | — |
| `prince5_extract.py` | 5人の恋プリンス ~ヒミツの契約結婚~ (PSV, PCSG00590) 文本提取 | `asgard-tat` |
| `prince_stride_lt.py` | プリンス・オブ・ストライド (PSV PCSG00491) —— lt.bin 字形图集渲染（2026-10-12） | `prince-stride-d3p` |
| `prince_stride_run.py` | プリンス・オブ・ストライド (PSV PCSG00491) —— sc.cpk → 全文本（2026-10-12） | `prince-stride-d3p` |
| `procboth.py` | 联合监视：游戏文件读取位置变化 + guest 堆中新出现的 cp932 日文串 | — |
| `procfpos.py` | 列出指定进程打开的游戏文件及其当前读写位置（GetFilePointer） | — |
| `prochandles.py` | 列出指定进程当前打开的文件路径 | — |
| `procwatch.py` | 实时监视进程内游戏文件的读取位置变化，定位"引擎刚刚读了哪一段" | — |
| `ps2_extract.py` | PS2 .HD/.BIN extractor for the *Hakarena Heart*-type engine. | — |
| `ps2_game.py` | VM-level extraction: one line per message box (one click). | — |
| `ps2_scene.py` | Classify one 08-record payload. | — |
| `ps2_vm.py` | VM-level .cnut (Squirrel 'SQIR'/PART container) dialogue extractor for | — |
| `psarc_extract.py` | PSARC (Sony) extractor — big-endian classic PSARC. | `crank-text-mode-adv` · `lte` · `unity-adv` |
| `psp_prx_type9_decrypt.py` | PSP ~PSP (EncryptType 9) EBOOT.BIN decrypter. | — |
| `psvskip_patch.py` | 让 psvpfsparser 在单文件解密失败时继续（跳过），不整进程退出 | — |
| `psycemo6_extract.py` | PsychicEmotion6 (PSV / PCSG00815 / Otomate x Idea Factory / 2015) 全文本提取 | `idea-factory-stcm2l-psv` |
| `qpk.py` | QuinRose / Qoo-framework QPK/QPI archive reader (PSP). | — |
| `radian_extract.py` | ラディアンテイル（本体，非 FD）—— STCM2L "May 18 2015" 变体 → 全文本 | — |
| `radian_split.py` | ラディアンテイル（STCM2L "May 18 2015" 变体）—— **按源结构把「并框」拆开** | — |
| `rakuen_extract.py` | 楽園男子 ～誰も知らない もう一つの楽園～ (PSP, Takuyo gss / LSDARC V.100 'SCR 2.00') | — |
| `ramsnap.py` | 把 guest 内存整段 dump 到文件（分块读，支持 100MB 级区域） | — |
| `realrode_extract.py` | Real Rode ポータブル (PSP, HuneX「IKA SEQ SYSTEM v3.1」) 全文本提取 | `hunex-ika-seq` |
| `rear_extract.py` | リアフェレス（Unity）TextAsset 场景脚本提取 → リアフェレス.txt | — |
| `redbell_dialog.py` | レッドベルの慟哭 正文提取（成品生成） | `unity-text-carriers` |
| `redbell_extract.py` | レッドベルの慟哭 —— Naninovel Script(ScriptableObject) → 全文本 | — |
| `redbell_romfs.py` | レッドベルの慟哭 —— 压缩 NCA(LZ4 bucket-tree) → RomFS 直读 | — |
| `renderfont.py` | 把字库图集渲染成 PNG（逐码位预览，供人工目视确认字形） | — |
| `revepc_extract.py` | [PC-JP] DYNAMIC CHORD feat.[rēve parfait] Append Disc（honeybee black / ASGARD） | — |
| `revice_extract.py` | RE:VICE[D] (PSV, PCSG00382, Otomate / Idea Factory) 剧本文本提取 | `idea-factory-stcm2l-psv-cp932` · `idea-factory-stcm2l` |
| `ripple_deep.py` | 递归解 HFU2（含嵌套），输出叶子 blob 并统计日文密度 | — |
| `ripple_extract.py` | リプルのたまご ～Apprentice magician～ (PS2, HuneX .ebf) 全文本提取 | — |
| `ripple_unpack.py` | リプルのたまご (PS2) HFU2 解包 + 目视 dump 用 | — |
| `rom2_extract.py` | ROM2 archiver (Kalmia8 / 鳥籠のマリアージュ PSV). | `rom2-snr` |
| `rom2_list.py` | ROM2 目录列表 / 按名提取（不整文件入内存） | — |
| `roman_extract.py` | 召しませ浪漫茶房（SIMPLE2000 Vol.98 THE 浪漫茶房 / PS2-JP / SLPM_657.37）全文本提取 | `vsc-vl-file-tml` |
| `roman_tml.py` | 召しませ浪漫茶房 (PS2-JP / SLPM_657.37) —— TML 剧本解析（草案，供调参） | — |
| `roman_vl.py` | 召しませ浪漫茶房 (PS2 / SLPM_657.37) —— VSC 'vl_file' 库：vlLZSS 解压 + PAC(MemPack) 读取 | `vsc-vl-file-tml` |
| `romeo_extract.py` | QuinRose Qoo (PSV) —— ロミオVSジュリエット 剧本成行 | — |
| `rootrexx_extract.py` | ROOT∞REXX (PSV / PCSG00458 / Otomate×Idea Factory / 2015) 全文本提取 | `idea-factory-stcm2l-psv-cp932` |
| `rq_extract.py` | Re;quartz零度 (NS) SCRIPT.PAK → 全文本（双版对照） | — |
| `rt2_extract.py` | ラディアンテイル ～ファンファーレ！～ (NS) STCM2L 文本提取 —— 2026-10-26 修正版 | — |
| `run_alice.py` | Batch extract scenario text from the 6 Alice-series PSP ISOs. | — |
| `sa7_extract.py` | SA7 - Silent Ability Seven - (PSV / PCSG00640 / プチレーヴ) 全文本提取器 | — |
| `saint_extract.py` | ［PS2-JP］セイント ビースト ~螺旋の章~ —— SN.BIN 剧本提取 | — |
| `sanzen_extract.py` | 参千世界遊戯 ～Re Multi Universe Myself～ (PSV, PCSG01194, girls★dynamics / ACTGS「ROM2/SNR」) | `rom2-snr` |
| `scan_jp.py` | 目录级扫描：找「连续假名 run 多」的文件并排序 —— 先圈候选，再细看 | — |
| `scan_nested.py` | 在归档的嵌套条目里扫日文，报 magic / 大小 / 样例 | — |
| `scanjp.py` | 单文件内定位连续假名 run（按偏移列出），用于确认哪一段是正文 | — |
| `schoolwars_extract.py` | スクール・ウォーズ ～全巻パック 本編＆卒業戦線～ (PSV, QuinRose / Courier "KS" engine) | — |
| `seisyun_bin.py` | 《青春はじめました！》(PSP) cwin 脚本容器解析 | — |
| `seisyun_extract.py` | 《青春はじめました！》脚本 .bin → 一行一次点击的文本 | — |
| `senjyushi_extract.py` | 千銃士:Rhodoknight (NS) 解包 —— 压缩 NCA (LZ4 bucket-tree) → RomFS → 文件 | `platform-switch-nca` · `unity-adv` |
| `senjyushi_extract_text.py` | 千銃士Rhodoknight (NS) —— SceneMasterVO.bin 全文本提取 | `unity-adv` |
| `sgs_kai_ddp.py` | 三国恋戦記 魁 (Daisy2 / sgs_*.dat, DDP2/DDP3) 解包 + 解密 + 解压 | — |
| `sgs_kai_extract.py` | 三国恋戦記 魁 —— 全文本提取（对话/选项/结局/教程） | — |
| `shini_extract.py` | [NS-JP]死神と少女 (The Reaper And The Girl) text extract. | — |
| `shinjuku_text.py` | 新宿羅生門 ―Rashomon of Shinjuku― (Switch / Idea Factory・ALTERGEAR, 開発:花梨エンターテイメント) | `karin-adv-asb` |
| `shinobi_ns_build.py` | 忍び、恋うつつ for Nintendo Switch —— 成品构建 | — |
| `shinobi_ns_extract.py` | 忍び、恋うつつ (NS) STCM2L 提取：一次点击 = 一行 | — |
| `shinoda_botan_extract.py` | 篠田新宿探偵事務所 唐獅子牡丹 (HolicWorks Disc Blue / 2018-10-26 / PC-JP) | — |
| `sidez_nca.py` | Blackish House sideZ -Retour- (NS) : 压缩 NCA(BKTR bucket-tree + LZ4) → RomFS | — |
| `sidez_pc_extract.py` | [PC-JP] Blackish House ←sideZ（ASGARD AdvHD / .ws2 字节码）全文本提取 | — |
| `siglus_scene_extract.py` | SiglusEngine (罪ナル螺旋ノ檻 / Tsuminaru) Scene.pck text extractor. | `siglus` |
| `skipbeat_extract.py` | スキップ・ビート！(PS2, SLPM_551.70) シナリオ抽出 | — |
| `snowboundland_extract.py` | SNOW BOUND LAND (PSP, Otomate / Idea Factory 2013) 剧本文本提取 —— 自包含 | `idea-factory-stcm2l-psp-cpk` |
| `solomon_extract.py` | [PSP-JP] Solomon's Ring ～地の章～ (Plan Peace / InterOne, ULJM06200系) | `planpeace-pct` |
| `sorayume_extract.py` | ソラ*ユメ (NS-JP, TAKUYO, TitleID 0100e6a027760000) text extract. | `takuyo-gss-switch-scr2` |
| `split_adjacent_quotes.py` | 句中 」「 相邻的筛查／拆分工具（skill references/S6-lines.md §「句中引号只作探针」的落地） | — |
| `srxfd_extract.py` | スカーレッドライダーゼクス STARDUST LOVERS (PSP) | — |
| `srxrev_extract.py` | LukPlus ADV (SRX Rev / PSV) lua script -> text extraction. | — |
| `ss_psv_extract.py` | Starry☆Sky PSV（Summer/Autumn/Winter Stories, PCSG00916/917/918）剧本文本提取 | — |
| `sspm_extract.py` | Starry☆Sky ~Spring Memories~ (NS-JP, 0100a3d026610000) 全文本提取 | `hunex-hesl-switch` |
| `stcm2l_extract.py` | STCM2L 剧本文本提取器 —— 猛獣たちとお姫様 for Nintendo Switch | `idea-factory-stcm2l-switch` · `idea-factory-stcm2l` |
| `steam2_extract.py` | スチームプリズン -Beyond the Steam- (NS) → 全文本 | — |
| `steam_extract.py` | スチームプリズン (NS, HuneX Ogre) allscr.mrg + script_text.mrg → 全文本 | — |
| `steam_rebuild.py` | スチームプリズン 按「文本表逐条 = 一次点击」重建（2026-10-26） | — |
| `steelwood_extract.py` | Steel Wood (原宿探偵学園 スチールウッド) DATA/BIN/M*.DAT 剧本提取 | — |
| `stormlover2_charset.py` | STORM LOVER 2nd V (PSV PCSG00736) —— sc.cpk 自建字符集（二级自定义槽） | `stormlover-d3p` |
| `stormlover2_run.py` | STORM LOVER 2nd V (PSV PCSG00736) —— 从 sc.cpk 产出全文本 | `stormlover-d3p` |
| `stormlover_assets.py` | STORM LOVER V (PSV PCSG00735) —— 资源解压工具（2026-10-11） | `stormlover-d3p` |
| `stormlover_charset.py` | STORM LOVER V (PSV PCSG00735) —— sc.cpk 自建字符集（最终版 2026-10-11） | `prince-stride-d3p` · `stormlover-d3p` |
| `stormlover_extract.py` | STORM LOVER V (PSV PCSG00735) sc.cpk 正文提取（2026-10-11） | — |
| `stormlover_font.py` | STORM LOVER V (PCSG00735) 字形图集读取器 —— lt.bin | `stormlover-d3p` |
| `stormlover_natsu_charset.py` | STORM LOVER 夏恋!!（PSP / ULJM-05858?）—— sc.cpk 自建字符集（2026-10-12） | `stormlover-d3p-psp` |
| `stormlover_natsu_run.py` | STORM LOVER 夏恋!!（PSP）—— 从 sc.cpk 产出全文本（2026-10-12） | `stormlover-d3p-psp` |
| `stormlover_psp_cmp.py` | STORM LOVER 夏恋!!（PSP）—— 二级槽「字形 vs 候选字」比对图（人工目视定值） | `stormlover-d3p-psp` |
| `stormlover_psp_font.py` | STORM LOVER 夏恋!!（PSP）—— lt.bin 自建位图字体渲染（2026-10-12） | `stormlover-d3p-psp` |
| `stormlover_run.py` | STORM LOVER V (PSV PCSG00735) —— 从 sc.cpk 产出全文本（2026-10-11） | `stormlover-d3p` |
| `straw_extract.py` | 殺し屋とストロベリー Plus —— scenario01(UnityFS) 内 TextAsset → 全文本 | — |
| `strawberry_extract.py` | PS2『きまぐれストロベリーカフェ』EVT 字节码文本提取（v3） | — |
| `stride_extract.py` | 《[PSV-JP]プリンス・オブ・ストライド》 (PCSG00491) 资源解密 / 解包 / 文本探查工具 | — |
| `strobemania_run.py` | スト☆マニ ～Strobe☆Mania～（PSP / ULJM-05961）—— 全文本提取 | — |
| `struct_probe.py` | 引号/括号结构探针：把「一行里塞了几个框」量化 | — |
| `sugar_build.py` | PAC 0x0425 文本流 → 一次点击一行 | — |
| `sugar_extract.py` | PS2 シュガシュガルーン 恋もおしゃれもピックアップ！ | — |
| `swallows_extract.py` | My9Swallows TOPSTARS LEAGUE —— Unity + 纯文本脚本（与 Honey Vibes 同引擎） | — |
| `sweetclown_extract.py` | [NS-JP]SWEET CLOWN ~午前三時のオカシな道化師~ text extract (Takuyo gss / SCR 3.00). | `takuyo-gss-switch` |
| `switch_nca.py` | Switch NCA 解密器（不依赖 hactool）—— 处理 Titlekey crypto / Standard crypto 的 Program NCA | `platform-switch-nca` · `unity-adv` |
| `symp_trace.py` | SympathyKiss STCM2L 单段 opcode 追踪（看「同句两版 / 掩码 ＃＃＃ / 断行」在代码层长什么样） | — |
| `sympathy_extract.py` | SympathyKiss (NS) STCM2L 文本提取 | — |
| `sympathy_namescan.py` | 统计正文里的 #Name 宏与候选默认名 | — |
| `temi_extract.py` | テミラーナ国の強運姫と悲運騎士団 (NS, Unity/UTXT) → 全文本 | — |
| `tempest_dlc_list.py` | 逐个清点 even if TEMPEST 宵闇にかく語りき魔女 的 12 个 DLC（NS-JP） | — |
| `tempest_dlc_text.py` | 宵闇 DLC 正文提取（源＝eden 模拟器 Dump RomFS，update 已合并） | — |
| `tempest_extract.py` | even if TEMPEST 宵闇にかく語りき魔女（Switch / Nintendo Bezel Engine）剧本文本提取 | — |
| `tempest_upd_merge.py` | even if TEMPEST 宵闇にかく語りき魔女 Update v1.1.1（BKTR）→ 本体 romfs 合并读取 | — |
| `teni_extract.py` | 新テニスの王子様 LET'S GO!! 〜Daily Life〜 from RisingBeat (NS, HuneX Ogre) → 全文本 | — |
| `tenis2_extract.py` | テニスの王子様 SWEAT & TEARS 2 (PS2) 剧本提取 | — |
| `tennis_dump.py` | 解出全部 .s 的消息原文（含 gaiji 原字节），落 TSV 供分析. | — |
| `tennis_extract.py` | [PS2-JP] テニスの王子様 RUSH & DREAM! 全文本提取. | — |
| `tennis_scan.py` | [PS2-JP] テニスの王子様 RUSH & DREAM! 脚本解码/文本扫描. | — |
| `tennis_unpack.py` | [PS2-JP] テニスの王子様 RUSH & DREAM! 解包. | — |
| `termdict_extract.py` | 用語辞典（termItem.dat）→ 【見出し語】解説文 一行一条，并入成品末尾 | `zerodiv-cpk-extra-files` |
| `textbox_stats.py` | 统计用 —— 分作行数 + 文本框封口 op 分布（L0 判据的证据） | — |
| `thc_build.py` | 合成最终交付文本（一次点击 = 一行） | — |
| `thc_extract.py` | とらぶるふぉうちゅんCOMPANY★はぴCURE (PS2, Primavera/Interchannel "nlib") 文本提取 | — |
| `thc_text.py` | 从 thc_extract.py 解出的成员文件中抽取正文（一框一点击） | — |
| `tiabureido_extract.py` | 悠久のティアブレイド for Nintendo Switch —— STCM2L 全文本提取（一次点击＝一行） | — |
| `tik_key.py` | 由 ticket 推 NCA 内容密钥（Titlekey crypto），并用 section 0 的 PFS0/IVFC 魔数自证 | — |
| `tiny_machinegun_extract.py` | Tiny×MACHINEGUN THE GAME (Rejet / PC-JP) 剧本・辞典文本提取器 —— 端到端定稿 | `misc-engines` |
| `tokihako_extract.py` | 時函 -Time Capsule- (Ray, 2009 / PC / NScripter) 全文本提取 | `misc-engines` |
| `tokimemo_gs1_extract.py` | ときめきメモリアル Girl's Side 1st Love (NS-JP, Unity) 全文本提取器 | `konami-unity-bytes-works` |
| `tokimemo_gs2_extract.py` | ときめきメモリアル Girl's Side 2nd Season (NS-JP, Unity) 全文本提取器 | `konami-unity-bytes` |
| `tokimemo_gs3_extract.py` | ときめきメモリアル Girl's Side 3rd Story for Nintendo Switch (NS-JP, Unity) 全文本提取器 | `konami-unity-bytes-works` |
| `tokimemo_gs4_extract.py` | ときめきメモリアル Girl's Side 4th Heart for Nintendo Switch (NS-JP, Unity) 全文本提取器 | `konami-unity-bytes-works` |
| `tokires_extract.py` | ときめきレストラン☆☆☆ Project TRISTARS (PSV / PCSG01171, KONAMI) 全文本提取 v2 | `koei-cdar` |
| `tokitama_extract.py` | ときたま！～時函玉手箱～ (Ray, 2010 / PC / NScripter) 全文本提取 | `misc-engines` |
| `torimari_extract.py` | 鳥籠のマリアージュ ～初恋の翼～ (PSV, PCSG90230, Kalmia8 / ACTGS engine) | `rom2-snr` |
| `towa_build.py` | 悠久ノ桜（Towa no Sakura / PS2-JP）全文本生成 | — |
| `towa_dis.py` | 悠久ノ桜 SLPM_668.45 最小反汇编：ELF32 MIPS(LE) → .text 反汇编落盘 + 立即数索引 | — |
| `towa_extract.py` | 悠遠ノ桜 (Towa no Sakura / PS2-JP) LSB 解析 —— VSC VDP + LSB 族 | — |
| `trois_text.py` | アンジェリーク トロワ (PS2, SLPM_620.22, 2000 Koei/Ruby Party) 正文＋选项提取 | `koei-embins-ps2` |
| `tsukikage_extract.py` | 月影の鎖 -錯乱パラノイア- (NS-JP) text extract ---- TAKUYO gss / SCR 2.00. | — |
| `tsundere_extract.py` | ツンデレ★Ｓ乙女 (PC / 美蕾「Madoka GScript」) 全文本提取器 —— 本项目定稿 | — |
| `tyb_fd_extract.py` | TOKYOヤマノテBOYS for V FAN DISC（PSV / PCSG01049）全文本提取 | — |
| `udf.py` | 极简 UDF 只读解析（PS2 桥接盘用）：列目录 / 抽取文件 | — |
| `uf_render.py` | 恋愛番長2 font/0（UF_ 自研字体）字形渲染/探查工具 | `idea-factory-stcm2l-psp-uni2-banchou2` |
| `ukronia_bktr.py` | ：BKTR 段（enc=3）解密试验 | — |
| `ukronia_check.py` | ：闭合校验（[next storage] 目标是否都在、排除清单、块/页/选项计数） | — |
| `ukronia_cls.py` | ：剧本文件分类表（每文件正文行数 + 首行样本） | — |
| `ukronia_extract.py` | 泡沫のユークロニア 剧本成行器（TIS 风格 [命令] 脚本） | — |
| `ukronia_kaek.py` | ：key_area[3] 在所有 KAEK 索引下的试解（16 次，验证 keygen 歧义） | — |
| `ukronia_nca.py` | Blackish House sideA-> -Retour- (NS) 压缩 NCA（LZ4 桶树）解包 | — |
| `ukronia_ncahdr.py` | ：解 NCA 头（AES-XTS header_key），导出各段 FS 头字段（含 section_ctr） | — |
| `ukronia_ncahdr2.py` | ：dump NCA 头明文（段表 + 各段 FS 头），供人工判读 | — |
| `ukronia_novel.py` | ：novel mode（textmode=3）分段统计 | — |
| `ukronia_rawromfs.py` | 把「LZ4 桶树压缩 NCA」的 RomFS 段还原成裸 romfs 镜像（供 bktr_romfs.py --base 使用） | — |
| `ukronia_syn.py` | ：剧本语法普查（命令词频、选项、占位符、块长分布） | — |
| `ukronia_ta.py` | ：列出 Unity bundle 里的 TextAsset（名称/大小/首行），判定正文载体 | — |
| `ukronia_textasset.py` | ：导出 bundle 内指定 TextAsset 原文到文件 | — |
| `ukronia_upd.py` | 泡沫のユークロニア 更新档（BKTR）→ 最新 romfs 文件 读取/合并 | — |
| `um_extract.py` | うみねこのなく頃に咲 (NS) main.snr → 全文本 | — |
| `unbs_extract.py` | Un:BIRTHDAY SONG～愛を唄う死神～another record（PSV PCSG00912）剧本提取（本作专用） | — |
| `unity_list.py` | 列出 Unity AssetBundle / .assets 内的对象（type + name/path_id），不 dump 内容 | `matatabi-unity-textadv` |
| `unity_textasset_dump.py` | Unity resources.assets → 全 TextAsset 落盘（旁车 / managed text 导出） | `matatabi-unity-textadv` · `naninovel-unity` |
| `upd_merge.py` | 通用「NS 官方更新（BKTR 差分）＋ 本体 NCA」→ 最新 romfs 文件 合并器 | — |
| `ura_ptd_jrs.py` | Uragiri wa Boku no Namae o Shitteiru (PS2, Design Factory / Otomate 2010) | — |
| `urakata_extract.py` | 裏語 薄桜鬼 (PSP ULJM06281) 剧本提取器 —— LZO1X 解压版 | `zerodiv-cpk-extra-files` · `zerodiv-lzo1x` |
| `ururun_build.py` | うるるんクエスト 恋遊記 全文本生成：VML -> 提取结果/*.txt | — |
| `ururun_vml.py` | うるるんクエスト 恋遊記 (PS2-JP / D3PUBLISHER, SLPM_660.28) | — |
| `utage_extract.py` | ハンサムロンダリング -the mystic lover- (NS / Unity + Utage) 剧本文本提取 | `unity-text-carriers` |
| `utapri_aa_check.py` | 交付前自检 —— **本作专用副本**（うたの☆プリンスさまっ♪ Amazing Aria & Sweet Serenade LOVE） | — |
| `utapri_aa_extract.py` | うたの☆プリンスさまっ♪ Amazing Aria & Sweet Serenade LOVE (NS 0100D4300EBF8000) | — |
| `utapri_aa_lzss.py` | うたの☆プリンスさまっ♪ Debut (NS 010088200EFE8000) 剧本提取（本作专用，勿与他作共用） | — |
| `utapri_as_extract.py` | うたの☆プリンスさまっ♪ All Star (NS 0100B3E0149FC000) 剧本提取 | `cri-snbin-lzss` · `nis-cpk-snbin` |
| `utapri_debut_check.py` | 交付前自检（品检）—— 日文游戏剧本文本提取产物的通用检查器 | — |
| `utapri_debut_extract.py` | うたの☆プリンスさまっ♪ Debut (NS 010088200EFE8000) 剧本提取（本作专用，勿与他作共用） | — |
| `utapri_extract.py` | うたの☆プリンスさまっ♪ All Star After Secret (NS/01008030149FE000) 剧本提取 | — |
| `utapri_rl_extract.py` | うたの☆プリンスさまっ♪ Repeat LOVE（PSV / PCSG00914）全文本提取 | — |
| `utapri_rl_ns_extract.py` | うたの☆プリンスさまっ♪ Repeat LOVE (NS 010024200E00A000) 剧本提取 | `cri-snbin-lzss` |
| `utsusemi_extract.py` | 空蝉の廻 (NS-JP) 文本提取 | — |
| `valpurga_extract.py` | [PSV-JP]ヴァルプルガの詩 (PCSG00768) 全文本提取 | `3daisy-scrvita` |
| `vamwolf_lt.py` | Vamwolf Cross† lt.bin 字形图集渲染 | `prince-stride-d3p` |
| `vamwolf_run.py` | Vamwolf Cross† (PSV PCSG00467, D3P 系) —— sc.cpk → 全文本 | `prince-stride-d3p` |
| `vdp.py` | VSC VDP 容器解析（ラスト・エスコート2 ～深夜の甘い棘～ / PS2-JP） | `vsc-vdp-lsb` |
| `verite_extract.py` | 《薔薇に隠されしヴェリテ》 (PS Vita / PCSG00708 / Unity 5.3.5p5) 全文本提取 | `unity-adv` |
| `virche_extract.py` | 終遠のヴィルシュ -ErroRsalvation- (NS) STCM2L 文本提取 | — |
| `virche_xci.py` | 重打包 XCI（封装头不自洽）→ 抽 NCA，带「数据起点自证」 | — |
| `vitaminb6_extract.py` | VitaminX DetectiveB6 (PSP, HuneX「IKA SEQ SYSTEM v4.1 HuneX 2010」) 全文本提取 | `hunex-ika-seq-b6` |
| `vitaminr_extract.py` | VitaminR (PSP, ULJS00592, 2013-08-08, D3P/Rejet) 全文本提取 | — |
| `vitaminx_ep_extract.py` | ビタミンX Evolution Plus（PSP, ULJS00325, HuneX「IKA SEQ SYSTEM v4.1」）全文本提取 | `hunex-ika-seq-vitaminx-ep` |
| `vitaminxz_extract.py` | Vitamin X to Z (PSP, ULJS00347, HuneX「IKA SEQ SYSTEM v4.1」) 全文本提取 | `hunex-ika-seq-vitaminxz` |
| `vitz_extract.py` | VitaminZ (PSP, ULJS00240, HuneX「IKA SEQ SYSTEM v3.4 HuneX 2009」) 全文本提取 | `hunex-ika-seq-vitaminz` |
| `vn_memdump.py` | 从运行中的进程按内存区段 dump（Windows，ReadProcessMemory） | — |
| `vn_zerodiv_extract.py` | 裏語 薄桜鬼 / ～暁の調べ～ (PSP ULJM06281 / ULJM06373) 剧本提取器 —— 定稿版 | `zerodiv-talks-variant` |
| `vridge_cs_customdrive.py` | カスタムドライブ（PSP / ULJM-06058）—— 二级区定值表 | — |
| `vridge_cs_hatsukare.py` | はつカレっ☆恋愛デビュー宣言!（PSP / ULJM-06199）—— 二级区定值表 | — |
| `vridge_psp_run.py` | Vridge/D3P 系 PSP 作品（sc.cpk + lt.bin 自建字符集）通用提取器 | — |
| `vxdst_extract.py` | VitaminX Destination (PSV-JP, PCSG01115) —— HuneX 'HESL / HESE' 剧本文本提取器 | `hunex-hesl` |
| `vzgrad_extract.py` | VitaminZ Graduation (PSP, ULJS00xxx v1.01, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取 | `hunex-ika-seq-vzgrad` |
| `willowisp_extract.py` | ウィル・オ・ウィスプ ポータブル (PSP, ULJM05447, Design Factory & Otomate / Idea Factory) 剧本文本提取 | `idea-factory-stcm2l-psp-uni2-willow` |
| `winscan.py` | Windows 进程内存扫描器：定位指定进程里 cp932 日文正文最密集的区域并导出 | `cri-snbin-lzss` |
| `xci_hfs0.py` | XCI (HFS0) 手工解析/抽 NCA —— 专治重打包 XCI 的「封装头不自洽」 | — |
| `xci_romfs.py` | XCI -> (内存中)NCA -> RomFS 单文件抽取（不落 NCA/整 romfs，省磁盘） | — |
| `xp3.py` | 蝶の毒 華の鎖 XP3 索引列挙 + ファイル抽出 (KiriKiri XP3) | `kirikiri-xp3` |
| `yamanote_extract.py` | TOKYOヤマノテBOYS for V MAIN DISC（PSV / PCSG01048）全文本提取 | `lte` |
| `yamiiro_extract.py` | 闇色の魔珠 (Daisy2 / PROTOTYPE NS) SCRIPT.PAK → 全文本（双版对照） | — |
| `yaoi_base.py` | 宵闇 本体正文重建（源＝eden dump 的 merged romfs，即 v1.1.1 实际显示文本） | — |
| `yourmo_extract.py` | ユア・メモリーズオフ～Girl's Style～ (PSP-JP, ULJM05435, MAGES. 2008) | `mages-afs-yourmo` |
| `zettaikyuu_extract.py` | 絶対階級学園 ~Eden with roses and phantasm~ (NS) → 提取结果 txt | — |
| `zettaikyuu_nsplist.py` | 列 NSP 内 PFS0 条目（名 / 偏移 / 大小），顺带提示 ticket 的 keygen 与 cert 尺寸 | — |
| `zettaikyuu_romfs.py` | 絶対階級学園 —— 从 prog.nca 流式取 romfs 指定文件（不落 6GB 副本） | — |
| `zokuwanai_extract.py` | 罪喰い ~千の呪い、千の祈り~ for V (PSV / PCSG01019 / HuneX, dramatic create 2017) 全文本提取器 | `hunex-ogre-dramaticcreate` |
| `zokuwanai_unpack.py` | 罪喰い for V (PCSG01019, HuneX Ogre) allscr.mrg 解包 + MZX0 解压 | `hunex-ogre-dramaticcreate` |
