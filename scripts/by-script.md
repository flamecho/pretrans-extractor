# 脚本 → 用途（全部 964 个）

> **每次构建自动重建** —— 不要手改。
> 按引擎挑脚本请看 [`by-engine.md`](by-engine.md)（命中引擎后从那一行开始）。
> 本册用于查脚本用途及关联格式；`—` 表示来源记录未关联格式。

| 脚本 | 用途 | 关联格式 |
|---|---|---|
| `_probe_dialogue.py` | — | — |
| `_probe_dup.py` | — | — |
| `_probe_hash.py` | — | — |
| `_probe_hash2.py` | — | — |
| `_probe_mana.py` | — | — |
| `_probe_mana2.py` | — | — |
| `_probe_nameop.py` | — | — |
| `_probe_nonstcm.py` | — | — |
| `_probe_recall_audit.py` | Recall 审计探针：① 选项载体形态 ② 零文本 .ks 性质核验 | — |
| `_probe_recall_exclude.py` | 为排除列表建证据：每个零-box/plugin 文件的显示标签计数 + TJS 代码块标记 | — |
| `_probe_recall_leak.py` | 定位 [playse... leakage 源 + 相邻重复行来源 | — |
| `_probe_recall_name_opt.py` | 确认 [name] 用法（属性 vs 内容）及选项/link/ch 形态 | — |
| `_probe_recall_options.py` | Recall 选项/系统文件深度探针 | — |
| `_probe_recall_playse.py` | 精确打印含 空間歪み 的原始行（repr），定位 playse 标签泄漏成因 | — |
| `_probe_recall_tags.py` | 全 .ks 标签频率统计（去重到顶层 tag 名），确认页面/段界/选项/宏 | — |
| `_probe_recall_zerobox.py` | 核验高-ja 的 0-box 文件：ja 在 iscript 内 vs 外，外显文本样本，页界标签计数 | — |
| `_probe_ruru.py` | — | — |
| `_probe_script202.py` | — | — |
| `_probe_syn2.py` | — | — |
| `_probe_syn3.py` | — | — |
| `_probe_syn4.py` | — | — |
| `_probe_syn5.py` | — | — |
| `_probe_syn6.py` | — | — |
| `_probe_syn7.py` | — | — |
| `_probe_syn8.py` | — | — |
| `_probe_syn9.py` | — | — |
| `_probe_synopsis.py` | — | — |
| `_trace_233.py` | — | — |
| `_verify_files.py` | — | — |
| `_verify_merge.py` | — | — |
| `_verify_orphan.py` | — | — |
| `_verify_output.py` | — | — |
| `abukoi2_extract.py` | [PSV-JP]アブナイ恋の捜査室 ~Eternal Happiness~ 文本提取器 | — |
| `abunai_extract.py` | アブナイ恋の捜査室 (PSP, QuinRose/Gigno) —— .ks 文本 DSL → 全文本 | — |
| `acacia_extract.py` | [JP]アカシア通り一番地 — KiriKiri XP3 ＋ KAG3 全文本提取（双版对照） | — |
| `advhd.py` | WillPlus / AdvHD (.wsc bytecode) shared engine. | `naninovel` · `stcm2l` |
| `agastar_audit.py` | — | — |
| `agastar_extract.py` | アガスターシェルゴサ v3.55: consume the packaged Tyrano native parser's tokens. | — |
| `agastar_prepare.py` | — | — |
| `aid_dw_extract.py` | [PC-JP]Alice in Dreamworld —— KiriKiri/KAG3 cp932 脚本 → 全文本（一次点击一行） | — |
| `aim_extract.py` | [JP]aim∴ai（KiriKiri/KAG3）全文本提取：.ks → 一次点击一行 | `kirikiri` |
| `air_abc.py` | Adobe AIR / SWF 的 ABC(ActionScript 3 字节码) 解析器 + 反汇编器 | — |
| `air_body.py` | ABC 方法体（method_body_info）定位器 | — |
| `air_body2.py` | 更宽松的方法体定位：不限定 d0 30 序言，改用「6 个 u30 精确落在 code 起点 + 尾部结构自洽」 | — |
| `air_kvs_dat.py` | Adobe AIR / Flash 「*.kvs + *.dat」资源归档解包器 | — |
| `air_scan.py` | 批量反汇编所有方法，按「字节运算 + ByteArray 读写」特征筛解密候选 | — |
| `air_win.py` | 打印某个 ABC 偏移附近的反汇编窗口 | — |
| `akasuna_extract.py` | 赤い砂堕ちる月 (PSV / PCSG00780 / Landkarte & dramatic create 2016) 全文本提取器 | — |
| `akasuna_pc_extract.py` | 赤い砂堕ちる月 (PC / NScripter + NSLua / Landkarte 2013) 全文本提取 —— 双版对照 | — |
| `akasuna_pc_nsa.py` | NScripter NSA (arc.nsa) 解包 —— 赤い砂堕ちる月 PC 版 | — |
| `akuyaku_extract.py` | 悪役令嬢は隣国の王太子に溺愛される (Switch, OPERAHOUSE, Unity / CSR1.00) 全文本提取 | `naninovel` · `stcm2l` |
| `alice_extract.py` | 白と黒のアリス for Nintendo Switch —— .qui(Lisp DSL) → 全文本（双版对照） | — |
| `alicis_extract.py` | [PC-JP]籠の中のアリシス（WillPlus / AdvHD, WSC）文本提取器 —— 自包含、argv 式 | — |
| `alto_extract.py` | [JP]alto -アルト- 文本提取驱动（Yuuki! Novel / PackageFile20） | — |
| `altor_extract.py` | ALTOR（PC / KiriKiri XP3 + KAGeXpress 3.0）一步出成品 | — |
| `am2_extract.py` | [JP]AM2：00～猫と月夜のブランコ～ —— WillPlus AdvHD (WSC v1.0) 文本提取 | — |
| `amennoir_extract.py` | アーメン・ノワール ポータブル (PSP, Idea Factory / Design Factory 2012, ULJM06064) | `stcm2l` |
| `angel_build.py` | Angel Profile (PS2) —— 生成交付文本 | — |
| `angel_extract.py` | Angel Profile (PS2) 文本抽取 —— 常量池顺序还原 | — |
| `angel_lua.py` | Angel Profile (PS2) Lua 5.0-variant chunk parser. | — |
| `angelfeather_extract.py` | Angel's Feather (PC / BlueImpact 自研 AF 1.03 / BSF1) 全文本提取 —— 单文件自包含版 | `himauri` · `livemaker` · `stcm2l` … |
| `angelique_extract.py` | アンジェリーク ルトゥール (PSV, PCSG00696) 剧本正文+选项提取 [Koei Tecmo / Ruby Party 自研「pasc」节点流] | — |
| `angelknight_ssb.py` | [JP]Angel Knight (PC / SaiSys / Ferret-ZUI) 正文提取 | `himauri` · `livemaker` · `stcm2l` … |
| `angelpop_extract.py` | [JP]Angel ★ Pop 正文提取（KiriKiri KAG3 / cp932 .ks） | `naninovel` · `stcm2l` |
| `angelpop_xp3.py` | [JP]Angel ★ Pop data.xp3 索引解析 / 抽取 | `naninovel` · `stcm2l` |
| `animamundi_extract.py` | [JP]アニマムンディ 終りなき闇の舞踏 — 全文本提取（修订版 v3） | — |
| `anki_extract.py` | アンジェリーク 魔恋の六騎士 (PSP, ULJM05986, Otomate 2011-11-17, vndb v8799) | — |
| `anki_unpack.py` | アンジェリーク 魔恋の六騎士 (PSP/ULJM05986) UNION.CPK 解包 | — |
| `anotherrewind_extract.py` | [JP]Another Rewind（LiveMaker / LiveNovel）正文+选项提取 | `himauri` · `livemaker` · `stcm2l` … |
| `apricot_extract.py` | 怪盗アプリコット ポータブル (PSP, Takuyo gss) 全文本提取 | — |
| `apricot_gaiden_extract.py` | 怪盗アプリコット 外伝 満編（PC / Takuyo GSS, SCRDATA = LSDARC V.100 + SCR 1.10） | — |
| `arcanafam2_run.py` | アルカナ・ファミリア2 (PSP, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取 | — |
| `arcanafesta_extract.py` | アルカナ・ファミリア フェスタ・レガーロ! (PSP, HuneX「IKA SEQ SYSTEM v3.4/v4.2」) 全文本提取 | — |
| `arcanafesta_run.py` | アルカナ・ファミリア フェスタ・レガーロ! (PSP) 成品生成 | — |
| `arcanayurei_run.py` | アルカナ・ファミリア 幽霊船の魔術師 (PSP, HuneX「IKA SEQ SYSTEM v3.4」) 全文本提取 | — |
| `arcobaleno_extract.py` | アルコバレーノ! ポータブル (PSP, ULJM05609) 剧本文本提取 | `stcm2l` |
| `ariard_extract.py` | Ariard / Latte (KiriKiri/KAG3) 成行器 —— 第八变体 XP3 专用 | `kirikiri` |
| `ariard_xp3.py` | [JP]Ariard-少年アリス - Under the rose data.xp3 解析 / 抽取 | `kirikiri` |
| `artemis_pfs_extract.py` | Artemis Engine (iMel) 全文本提取工具 —— 以《滄海天記》(NS-JP) 定案 | `artemis` · `nis-cpk-snbin` |
| `asakiyumemishi_extract.py` | あさき、ゆめみし～ひととせ～ (PC / 澪 / System-NNN「NNNLib」引擎) 全文本提取 · 定稿 | `naninovel` · `stcm2l` |
| `asakiyumemishi_psp_extract.py` | あさき、ゆめみし (PSP-JP / System-NNN「NNNLib」engine) 全文本提取 · 定稿 | — |
| `asuka_extract.py` | [PC-JP]あすか！～僕ら星灯高校野球団～ 全文本提取器 (Madoka GScript / CRPT) | — |
| `audit_batch.py` | 批次审计：① 变量/宏错误填充残留 ② 双版对照断行位置自洽性 | — |
| `audit_choice.py` | Completeness audit for CHOICE extraction. | — |
| `ayanomiya_extract.py` | Kogado Aya ARCW archive and script extractor. Python 3, standard library. | — |
| `baccan_extract.py` | 爽海バッカニアーズ! 剧本文本提取（テキスト方式ADV / プチレーヴ） | `naninovel` · `stcm2l` |
| `bakudan_extract.py` | バクダン★ハンダン（PSP / ULJM-06057，Otomate 2012-06-14）全文本提取 | — |
| `bakudan_run.py` | バクダン★ハンダン（PSP / ULJM-06057，Idea Factory / Otomate）—— 全文本提取 | — |
| `bea_scne_extract.py` | — | `bezel-bea` |
| `believer_extract.py` | BELIEVER! (PSV, PCSG00539) HuneX / UNAS('HESL') script text extractor. | `hunex-hesl` · `naninovel` · `stcm2l` |
| `benihana_extract.py` | 越えざるは紅い花 after disc～綾なす未来～（YU-RIS / YPF v500）全文本提取 | — |
| `beru_extract.py` | 私立ベルばら学園 ～ベルサイユのばらReimagination～ (NS) —— STCM2L 全文本提取 | — |
| `bezel_extract.py` | even if TEMPEST 連なるときの暁（Switch / Nintendo **Bezel Engine**）剧本文本提取 | — |
| `bezel_scb_lib.py` | [NS-JP]恋してしまった星の王子 ～誓願院編～ 文本提取（Bezel Engine / SCNE / scb_）链路与判据 | `bezel-bea` |
| `bgloss_extract.py` | Butterfly Gloss (WillPlus / AdvHD) text extractor. | `naninovel` · `stcm2l` |
| `binarystar_extract.py` | [PSV-JP] BinaryStar (PCSG00389, Otomate × Design Factory, 2014) 剧本文本提取 | — |
| `bir_base_extract.py` | ビルシャナ戦姫 ～源平飛花夢想～ (NS, 本体) → 全文本 | `vridge` |
| `bir_extract.py` | ビルシャナ戦姫 ～一樹の風～ (NS) → 全文本 | — |
| `bir_extract2.py` | ビルシャナ戦姫 ～一樹の風～ (NS) → 全文本 | — |
| `bktr_merge.py` | 官方更新档（BKTR Patch RomFS）→ 本体 romfs 合并读取（hactool 对这类重打包件报 | — |
| `bktr_romfs.py` | NS 更新档「Patch RomFS / BKTR」读取器（不依赖 hactool，可直接读 .nsp/.nca） | `nis-cpk-snbin` |
| `blackish_nca.py` | Blackish House sideA-> -Retour- (NS) 压缩 NCA（LZ4 桶树）解包 | — |
| `blackish_pc_extract.py` | [PC-JP] Blackish House sideA→（honeybee black 2016 / PC） | — |
| `blip_extract.py` | Butterfly Lip (PC / WillPlus-AdvHD) text extractor. | `naninovel` · `stcm2l` |
| `boiz_extract.py` | [JP]♂ボ～イズ！！～イケメン陵辱パラダイス～（体験版） 文本提取 | `himauri` · `livemaker` · `stcm2l` … |
| `boiz_unpack.py` | [JP]♂ボ～イズ！！～イケメン陵辱パラダイス～ NPA 解包 | `himauri` · `livemaker` · `stcm2l` … |
| `brothers_kiss_extract.py` | ブラザーズ～恋するお兄さま＆もっと恋するお兄さま～ (Tiaramode, 2007, BGI/Ethornell) | `naninovel` · `stcm2l` |
| `brouge_extract.py` | Butterfly Rouge (PC / WillPlus-AdvHD) text extractor. | `naninovel` · `stcm2l` |
| `brute_ks.py` | — | — |
| `bt_extract.py` | バトラーズ～召しませお嬢様～ / ～ナイトモード～ (Tiaramode, BGI/Ethornell v0) | — |
| `btf_carve.py` | 从 INSTALL.BIN 中按 fileinfo.psb.m.json 的 umd_root 表切出成员文件 | — |
| `btf_extract.py` | [PSP-JP] Beyond The Future -Fix The Time Arrows- 全文本提取 | — |
| `btf_mdf.py` | M2 PSB 的 MDF(MT19937) 外壳解密（PSP 版 Kaleido/ADVENGINE） | — |
| `btf_pgd.py` | PSP PGD（\\0PGD / drm_type=1 / mac_type=1）解密 | — |
| `btf_s2_extract.py` | BUSTAFELLOWS シーズン2（NS-JP）全文本提取 —— 自研 UTXT 容器 | — |
| `btf_unpack.py` | M2「ADVENGINE」PSB 盘 一键解包（PGD → 成员 → MDF → PSB） | — |
| `build_choice_text.py` | CHOICE (KiriKiri KAG) 文本提取 → 提取结果/CHOICE.txt | — |
| `build_kure.py` | クレプシドラ 成品构建：scenario(ARC2) -> LZSS -> 正文成行 | — |
| `build_ls2.py` | ラスト・エスコート2 ～深夜の甘い棘～ 全文本生成 | — |
| `build_text.py` | ラスト・エスコート 〜黒蝶スペシャルナイト〜 全文本生成 | `koei-embins-ps2` |
| `busta_extract.py` | BUSTAFELLOWS（NS-JP, Unity 2018.4 IL2CPP, global-metadata v24）文本提取 | `unity` |
| `bwolves_extract.py` | BLACK WOLVES SAGA -Wei\u00df und Schwarz- (Switch, STCM2L) \u5267\u672c\u63d0\u53d6\u5668. | `stcm2l` |
| `byakko_extract.py` | BYAKKO ～四神部隊炎恋記～ (NS-JP) 文本提取 | — |
| `cafe_extract.py` | Cafe Cuillere (PSV PCSG01197, DWANGO/Takuyo, gss engine) text extractor. | `naninovel` · `stcm2l` |
| `ccdimg.py` | CloneCD / raw-2352 光盘镜像 → ISO9660 目录树 list / extract（不落整盘 ISO 副本） | `images` · `overflow-adv` |
| `cd_apply.py` | 用 cd_solve 的「条目→相手役」映射跑一次成品（诊断用，不写 提取结果/） | — |
| `cd_bin2iso.py` | MODE1/2352 · MODE2/2352 裸镜像 -> 2048 用户数据 ISO | `koei-embins-ps2` |
| `cd_blocks.py` | カスタムドライブ：用「单男角条目块」反查 相手役 id 字段 —— 报告 §11 步骤 2 的可重跑证据 | — |
| `cd_hdr.py` | カスタムドライブ 条目头（0x2000 B）探针 —— 报告 §11 步骤 1 的可重跑证据 | — |
| `cd_nameplate.py` | カスタムドライブ 名札（说话人）核验探针 —— 报告 §10 的可重跑证据 | — |
| `cd_ops.py` | カスタムドライブ L0 opcode 统计 —— 报告 §11 步骤 2 的可重跑证据 | — |
| `cd_solve.py` | カスタムドライブ FF0C（相手役の下名）定位器 —— 报告 §11 的可重跑证据/落地依据 | — |
| `cdar.py` | CDAR 容器读取库（被 cdar_extract.py import）：索引表 + 条目解压 | `nis-cpk-snbin` |
| `cdar_extract.py` | 递归解包 CDAR 容器（可下钻嵌套），逐条目落成原始字节 | `koei-cdar` · `nis-cpk-snbin` |
| `cend_extract.py` | Cendrillon palikA (NS) —— STCM2L 全文本提取 | — |
| `cfm_extract.py` | Confidential Money (PSP / Otomate 2012) .evb -> text. | — |
| `charset_audit.py` | 非日文字符台账审计：把每部成品里「kana/汉字/CJK标点/全角符号」以外的字符全部列出， | — |
| `chd_iso.py` | CHD v5 (zstd/lzma/none) -> 2048B/扇区裸 ISO，无 chdman 依赖 | — |
| `chou_decrypt.py` | 蝶の毒 華の鎖 XP3 内テキスト復号（区間 XOR 鍵推定）v3 | — |
| `chou_extract.py` | 蝶の毒 華の鎖 全テキスト抽出（KAG3 スクリプト → 表示テキスト） | — |
| `chou_fix.py` | 蝶の毒 華の鎖：復号後の局所的な文字化けを既知の正解で補正する表 | — |
| `chouchou_build.py` | 蝶々事件ラブソディック（PSV, L7CA + Lua5.3 变体字节码）正文提取 | — |
| `clep_lzss.py` | クレプシドラ ARC2 + LZSS 解压器 | — |
| `clonecd_iso.py` | CloneCD / 裸镜像 → ISO9660 目录树（支持 raw-2352 MODE1 与 2048 纯数据） | — |
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
| `cpk.py` | CRI CPK unpacker (纯 Python, 无依赖). | `cri-archives` · `dat-pak-scd` · `nis-cpk-snbin` … |
| `cpk_cri.py` | CRI CPK (@UTF) 容器读取器 —— 最小可用实现（实测格式） | `nis-cpk-snbin` |
| `cpk_v1.py` | CRI CPK unpacker (v1 ITOC-style + v2/v3 @UTF), 纯 Python. | `cri-archives` · `dat-pak-scd` · `nis-cpk-snbin` … |
| `cr_dict.py` | SYSTEM.cpk → DATABASE/dbDictionary_0{1,2}.gbin —— Code:Realize 用語辞典 | `stcm2l` |
| `cr_extract.py` | [NS-JP]Code：Realize ～彩虹の花束～ for Nintendo Switch —— STCM2L 文本提取 | `stcm2l` |
| `crankin_extract.py` | クランク・イン (Crank In) — PSV / PCSG00941 / プチレーヴ (Puchireve) | `naninovel` · `stcm2l` |
| `crazychain_extract.py` | CRAZY CHA!N -エルピスの鎖- (Nintendo Switch) 全文本提取 | — |
| `crazychain_xci.py` | CRAZY CHA!N -エルピスの鎖- (Switch XCI) → 切出 secure 分区内的 NCA | `nis-cpk-snbin` · `stcm2l` |
| `crimson_royale_extract.py` | クリムゾン・ロワイヤル (QuinRose, 2009 / KiriKiri KAG3, DropWave OTag system) | `naninovel` · `nis-cpk-snbin` · `stcm2l` |
| `cxm_extract.py` | Collar x Malice for Nintendo Switch (NS-JP) 全文本提取 | `stcm2l` |
| `cxm_stream.py` | Collar x Malice (NS-JP) STCM2L May 18 2015 记录流（纯结构，零猜测） | `stcm2l` |
| `danzai_maria_psp_extract.py` | 断罪のマリア ラ･カンパネラ PSP: script-only LIBP/Malie extraction. | — |
| `dareura_audit.py` | — | — |
| `dareura_extract.py` | 誰にでも裏がある -True or Lie？-: use the checked RealLive reader. | — |
| `dareura_layout_audit.py` | Check automatic overflow using the read rlvm TextWindow wrapping rules. | — |
| `dareura_scope.py` | Resolve the replay jump from its source table, then build RealLive scope. | — |
| `dc_extract.py` | デス・コネクション ポータブル（PSP ULJM05823 / Otomate 2011） | — |
| `dc_glossary.py` | デス・コネクション ポータブル —— 用語辞典（fid 22 見出し語表 ＋ fid 23 解説チャンク） | — |
| `dcgs_extract.py` | D.C. Girl's Symphony Pocket (PSP, ULJM05690) 剧本文本提取 | `nis-cpk-snbin` |
| `dcode_carve.py` | XCI / NSP → 逐个 NCA 落盘（按 title 目录分），供后续流式取 romfs | — |
| `dcode_extract.py` | [NS-JP]DistortedCode ―生者の残り香― text extract (TAKUYO gss / SCR 3.00). | — |
| `dcode_scr.py` | GSS / SCR3 脚本批量解码入口（复用 himehibi_lsdarc 与 gss_scr3 两个库） | — |
| `dd_dump.py` | 把 7drops.scenarios.asset 里所有 .book 摊平成 TSV 供人工判读语义 | — |
| `dd_mkelf.py` | 把 NSO 平铺镜像包成最小 ELF64（AArch64），供 LibCpp2IL(TypeTreeGeneratorAPI) 读取 | — |
| `dd_utage.py` | Utage .book 解析（格式依据 storycraft/unity-utage-book 的 reader.rs） | `unity` |
| `ddengine_text.py` | DDEngine / DDSystem（「Daylight」2008）—— dl_text.dat 全文本提取 | `himauri` · `livemaker` · `stcm2l` … |
| `desperadrops_extract.py` | DesperaDrops (NS-JP) 全文本提取 —— Utage 引擎 / .book 二进制 | — |
| `dessert_extract.py` | Dessert Love -Sweet Plus- (PS2) 全文本提取 | — |
| `dia_alice_extract.py` | ダイヤの国のアリス ～Wonderful Mirror World～ (PSP) 全文本提取 | — |
| `diag21.py` | — | — |
| `diag_noscramble.py` | — | — |
| `diary_ystb.py` | Diary（[PC-JP] Operetta 2011 / YU-RIS・YSTB v0x199）全文本提取 | — |
| `digit_extract.py` | [NS-JP]数乱digit For Nintendo Switch —— SCD 字节码文本提取 | — |
| `digit_scd.py` | yield (off, op, payload) | — |
| `director_build.py` | King of Beast 成品构建器 | — |
| `director_d8_text.py` | Director 8（XFIR 小端）text cast member（XMED）→ 一成员一框的正文文本 | `himauri` · `livemaker` · `stcm2l` … |
| `director_dsl_text.py` | Director 上的「自研 DSL 脚本引擎」→ 一 MSG 一框的正文文本 | `himauri` · `livemaker` · `stcm2l` … |
| `director_rifx_xmed.py` | Director RIFX(大端) + XMED「指令 DSL」文本提取器 —— GUISARD 本編（2003 / サンダルダッシュ） | `himauri` · `livemaker` · `stcm2l` … |
| `director_stxt_text.py` | Macromedia Director（Afterburner 保护）→ 台本 CSV → 「一次点击 = 一行」 | `overflow-adv` |
| `director_text.py` | King of Beast / Macromedia Director 8 文本提取器 | — |
| `director_xmed_dsl.py` | [Director 8.5 / XFIR 小端] XMED 内的「尖括号指令 DSL」→ 成品正文（一次点击 = 一行） | `himauri` · `livemaker` · `stcm2l` … |
| `director_xmed_text.py` | Director（8.5 / Afterburner 已由 ProjectorRays 解成 .dir）→ 全文本 | `himauri` · `livemaker` · `stcm2l` … |
| `dk_final.py` | [PS2-JP]drastic Killer 成品生成（一次点击 = 一行） | — |
| `dk_lib.py` | drastic Killer 容器库: ISO -> DATAxx.HD/BIN -> PACK -> 解压条目 | — |
| `dk_scpt.py` | SCPT 单条全解析：op 序列 + 池串 | — |
| `dk_stat.py` | DATA01 全条目解码闭合统计（写报告用） | — |
| `dk_trace.py` | 逐指令 trace（把 0x19 的 a/b 与 06 的串名解析出来） | — |
| `dl_df_extract.py` | DIABOLIK LOVERS DARK FATE (PSV, PCSG00530) 文本提取 | `dat-pak-scd` |
| `dl_ge_extract.py` | DIABOLIK LOVERS GRAND EDITION for Nintendo Switch —— 文本提取 | `himauri` · `livemaker` · `stcm2l` … |
| `dlcl_extract.py` | DIABOLIK LOVERS CHAOS LINEAGE (NS-JP) —— script.cpk 全文本提取 | `stcm2l` |
| `dms_extract.py` | DEAR My SUN!! ～ムスコ★育成★狂騒曲～（PS2 / HuneX IKA SEQ, SLPS_258.10）全文本提取 | — |
| `doublescore_advhd.py` | WillPlus / AdvHD —— Double Score 系列（Marguerite×Tulip 等）变体 | — |
| `dsb_extract.py` | Darling Special Backlash ～恋のエキゾースト・ヒート～ (PS2-JP, SLPM_656.53) | — |
| `dscatt_extract.py` | Double Score ～Cattleya×Narcissus～ 专用入口 | — |
| `dual_compliance_will.py` | — | — |
| `dump_base.py` | even if TEMPEST 本体（未压缩 romfs NCA）→ 裸 romfs 镜像（0 = romfs 头） | — |
| `dump_spt.py` | dump raw bytes around a literal hit in a .spt (XOR 0xFF decoded). | — |
| `dup_probe.py` | 双版拼接探针：找「同一行内同一句出现两次」的行 | — |
| `dyc_extract.py` | DYNAMIC CHORD feat.[rêve parfait] Remaster edition (NS-JP, 010076902126e000) | — |
| `dycko_extract.py` | [PC-JP] DYNAMIC CHORD feat.KYOHSO Append Disc（honeybee black / ASGARD / PC 2016） | — |
| `dycls_extract.py` | [PC-JP] DYNAMIC CHORD feat.Liar-S Append Disc（honeybee black / ASGARD, PC-ISO） | — |
| `dycpc_extract.py` | [PC-JP] DYNAMIC CHORD feat.apple-polisher（honeybee black 2016-11-04 / PC） | — |
| `dydc_extract3.py` | DYNAMIC CHORD Remaster 系列 3 部（Liar-S / KYOHSO / apple-polisher）全文本提取 | — |
| `dydc_split.py` | XCI → secure 分区 NCA 手切（nsz 还原的 XCI 哈希不被 hactool 接受，故手工走 HFS0 链） | — |
| `dydc_stats.py` | 三作解析自证数据（供报告引用） | — |
| `dystopia_extract.py` | [JP] ディストピアの王 (Daisy2 / DDP3) text extractor. | — |
| `edelblume_extract.py` | [PS2-JP] エーデルブルーメ (SLPM-66976 / Design Factory・Otomate 2008) 剧本文本提取 | — |
| `edema_extract.py` | [JP]Live x Evil 灼熱のエデマ — KiriKiri XP3 / KAG3 全文本提取器 | — |
| `edema_xp3.py` | [JP]Live x Evil 灼熱のエデマ — XP3 读取 + cxdec.tpm 内容层解密 | — |
| `ees_extract.py` | END END SUMMER (KiriKiri / KAG3 派生) 文本提取 —— 双版对照 | — |
| `emsg_eternity.py` | EMSG（Eternity 引擎 / white plum『Jewel Garden』系）消息库提取器 | — |
| `emu.py` | 模拟器辅助：截屏 + 发键（Windows，PIL + ctypes，无第三方 GUI 依赖） | — |
| `emu_bring.py` | 把模拟器（PCSX2/PPSSPP）窗口置前并截图 | — |
| `emu_dec.py` | 用 unicorn 模拟执行 SLPM 里的解压函数（0x142c80 = type1, 0x142a20 = type2） | — |
| `enbu_extract.py` | 戦場の円舞曲 for Nintendo Switch —— 全文本提取器 | — |
| `enkan_extract.py` | 円環のメモーリア -カケラ灯し- (PSV / PCSG01167 / A'sRing & Dramatic Create) 全文本提取器 | — |
| `entis_arc.py` | Entis / EMSAC-Binary Archive-2 (gigolo.arc, *.arc of Entis GLS titles) | `overflow-adv` |
| `entis_sx.py` | Entis / Sakura-OS Executable (gigolo.sx) 文本字面量提取 | `overflow-adv` |
| `epic_extract.py` | 終遠のヴィルシュ -EpiClycoris- —— STCM2L(Switch/2018型) → 全文本 | `naninovel` · `stcm2l` |
| `epriru_extract.py` | [JP]エイプリルーるののこりもの（LiveMaker 3，2009 同人 / キタユメ | — |
| `eroto_extract.py` | [JP]エロトマニア（吉里吉里2 / KAG3，2016 女性向け18禁BL）文本提取驱动 | — |
| `eroto_unxp3.py` | XP3 脚本层解包（LiveMaker/KiriKiri 通用）：解出 .ks/.tjs/.txt/.sli/.asd 并列出全部成员分类 | — |
| `etoile_final.py` | SCPT 目录 -> 最终全文本（一行 = 一次点击） | — |
| `etoile_houteishiki_decode.py` | reusable decoder for 《エトワールの方程式》(clearcolor, 2004) script. | — |
| `etoile_houteishiki_extract.py` | [JP]エトワールの方程式 extractor. L0: RE_NOTES.md (Etoile.exe 0x415E60/0x404770/0x419C30/0x419CD0/0x41A1A8/0x41A370). | — |
| `etoile_script.py` | アンジェリーク エトワール (PS2) DATA02 脚本解包 | — |
| `etoile_script_par.py` | DATA02 脚本解包（多进程版） | — |
| `etoile_text.py` | 从解包出的 SCPT 里提取台词文本（一行 = 一个 message box） | — |
| `etoile_unpack.py` | アンジェリーク エトワール (PS2, SLPM_657.15, 2004 Koei/Ruby Party) 归档解包器 | — |
| `etude_extract.py` | Extract all displayed text from étude prologue 〜揺れ動く心のかたち〜 Portable | — |
| `euchronia_trail_dup.py` | 定位成品的「相邻重复行」源于哪个脚本、何种结构（用于判是否互斥分支重复） | — |
| `euchronia_trail_extract.py` | 泡沫のユークロニア 剧本成行器（TIS 风格 [命令] 脚本） | `naninovel` · `stcm2l` |
| `euchronia_trail_nca.py` | Blackish House sideA-> -Retour- (NS) 压缩 NCA（LZ4 桶树）解包 | — |
| `extract_alice.py` | Extract scenario text from the Alice-series PSP games (QuinRose). | `nis-cpk-snbin` |
| `extract_choice_text.py` | Reverse KiriKiri script scramble (KirikiriDescrambler). data = zlib-decompressed payload. | — |
| `extract_gunjo.py` | 群青ノ雪 (KiriKiri/KAG3) 文本提取 | — |
| `extract_orphan_drug.py` | ORPHAN DRUG (FUSYRO / KiriKiri KAG3) 文本提取 | — |
| `extract_question.py` | [JP]Question (KiriKiri/KAG3) 全文本提取 —— 专用提取器（S6） | `kirikiri` |
| `extract_text.py` | PSP アラビアンズ・シリーズ 脚本テキスト抽出 | `nis-cpk-snbin` |
| `fhk2_extract.py` | フルハウスキス 2 (PS2, Capcom/TENKY, SLPM-662.88) —— 全文本提取（定稿） | — |
| `fix_multi_brackets.py` | 一行多个框的拆行（独白 （A）（B） / 台词 「A」「B」） | — |
| `fix_wrap_pairs.py` | 框内软换行被切成两行的修复（跨行续行收拢 / 缺引号补齐） | — |
| `foris_pack.py` | FORIS-OS（0verflow 系／S.S.D.S. 等）PACK（*.CMP）解包器 | `naninovel` · `stcm2l` |
| `foris_script_xml.py` | FORIS-OS（0verflow 系／S.S.D.S. 等）剧本 XML → 一次点击一行的正文 | `naninovel` · `stcm2l` |
| `fortissimo_extract.py` | 《フォルティッシモ》 (PS Vita / PCSG01131 / KADOKAWA x Otomate / 2018-03-08) 全文本提取 | `dat-pak-scd` · `naninovel` · `nis-cpk-snbin` … |
| `fpk.py` | FPK 容器头解析：条目表（名 / 偏移 / 大小）→ 可选导出 JSON，附扩展名直方图 | `koei-embins-ps2` |
| `fpkx.py` | FPK 解包（可给外部索引只取指定条目；重名自动加序号，不覆盖） | `koei-embins-ps2` |
| `fsymph_extract.py` | for Symphony ポータブル (PSP-JP, Takuyo, ULJM05258, v1.01) full-text extractor. | — |
| `fukushu_extract.py` | 復讐帝國（PC-JP / KiriKiri + RAT 系自定义 LineMode）文本提取器 | — |
| `fullscan.py` | 逐个归档条目试解压，按「含日文字数」排序 —— 先定位正文在哪一层容器 | — |
| `fuyuzakura_text.py` | [PC-JP]冬桜抄 -さくらがたり-（KiriKiri KAG3 · data.xp3）全文本提取 | — |
| `gakeppuchi_extract.py` | 崖っぷち令嬢は無気力悪魔で乙女を捨てたい（YU-RIS / YPF v500）全文本提取 | — |
| `gakuenk_extract.py` | 学園K -Wonderful School Days- V Edition (PSV, PCSG00654, Otomate / Idea Factory) | `dat-pak-scd` |
| `galtia_extract.py` | GALTIA（PIL/SLASH, Artemis Engine）剧本 → 成行 | — |
| `garnet_extract.py` | ガーネット・クレイドル ポータブル ～鍵の姫巫女～ (PSP, 2011 / STCM2L "Minku 07.0") | `stcm2l` |
| `garnet_pc_extract.py` | GsWin / DataPack5 (Takuyo PC) —— Scw5.x 剧本文本提取（一次点击 = 一行） | — |
| `garnet_pc_pak.py` | GsWin / DataPack5 (Takuyo PC) —— .pak 解包 + Scw5.x 脚本解码 | — |
| `genji_extract.py` | QuinRose Qoo (PSV) —— [PSV-JP]源氏恋絵巻 剧本成行 | — |
| `gensou_decode.py` | 蝶の毒 華の鎖 ～幻想夜話～ XP3 内テキスト復号 v3（確定復元表方式） | — |
| `gensou_extract.py` | 蝶の毒 華の鎖 ～幻想夜話～ 全テキスト抽出（KAG3 スクリプト → 表示テキスト） | — |
| `gessan_extract.py` | 月影の鎖 -狂爛モラトリアム- (NS) 文本提取 — Takuyo gss / SCR 2.00 / LSDARC V.100 | — |
| `geten_extract.py` | 下天の華 with 夢灯り (PSVita PCSG00921) 全文本抽取器 | `naninovel` · `stcm2l` |
| `ghp_extract.py` | Glass Heart Princess for Nintendo Switch —— 全文本提取器 | — |
| `ginkoku_build2.py` | 成行（v2）：源 = _work_ginkoku/out2（按 tpm 真算法解出的台本） | — |
| `ginkoku_cx_run2.py` | 用 cx_vm2 的真算法批量解密 scenario/*.txt → out2/，并做坏字节统计 | — |
| `ginkoku_cx_vm2.py` | 銀の冠碧の涙 —— 按 silverblue.tpm 真实代码重写的 CX 解密器（无任何补丁表） | — |
| `glasu_extract.py` | 硝子の森 (PS2-JP / D3PUBLISHER SIMPLE2000 Vol.13 / HuneX "ebf") 容器 + LZSS | — |
| `glasu_text.py` | 硝子の森（PS2-JP / D3P SIMPLE2000 Vol.13 / HuneX "ebf" Ver 0.30）文本提取 | — |
| `glyph_pick.py` | 在「语境候选字」之间做字形比对（仅用于验证假设，勿当 OCR 用） | — |
| `goes_extract.py` | Goes! (PCSG00367) 文本提取 | — |
| `grim_extract.py` | グリム・ザ・バウンティハンター（PSP / QuinRose / KiriKiri KAG .ks）文本提取 | — |
| `gs2_scb_extract.py` | 恋してしまった星の王子 ～制裁院編～（NS / Bezel Engine）文本提取器 | `bezel-bea` |
| `gsce_block_xor_decrypt.py` | — | — |
| `gspak.py` | GsWin「DataPack5」/ .scw 读取器（メサイア / 復讐帝國 之后同族引擎通用件） | — |
| `gss_codec.py` | GSS / LSDARC 'LSD\\x1a' codec (Takuyo gss engine). | `naninovel` · `stcm2l` |
| `gss_lsdarc.py` | LSDARC V.100 container (Takuyo gss). Index = "<NAME>.BIN", data = "<NAME>.ARC". | `naninovel` · `stcm2l` |
| `gss_scr3.py` | SCR 3.00 (Takuyo gss / Switch) disassembler. | `naninovel` · `stcm2l` |
| `hakken_extract.py` | 転生八犬士封魔録 (PS2-JP, SLPM_663.96) —— SC.AFS 全文本提取 | — |
| `hakuoki_kf_extract.py` | [NS-JP]薄桜鬼 真改 風華伝 文本提取（STCM2L / Switch / UTF-8） | `stcm2l` |
| `hakuoki_ns_build.py` | 薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— 成品构建（正文＋选项＋扉文＋用語辞典） | — |
| `hakuoki_ns_extract.py` | 薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— STCM2L 文本提取器（v1，逐文件调试输出） | — |
| `hakuoki_ns_extract2.py` | 薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— STCM2L 提取器 v2 | — |
| `hakuoki_zuisouroku_extract.py` | 薄桜鬼 随想録 面影げ花 (PSV, PCSG00485, Idea Factory / Otomate) | — |
| `hakushaku_afs.py` | CRI AFS (\x00SFA) minimal extractor for 5pb PS2 titles. | — |
| `hakushaku_extract.py` | Hakushaku to Yousei (PS2, 5pb) scene text extractor. | — |
| `hanayoi_afs.py` | AFS0（AFS\0）归档索引解析：条目偏移/大小 → 取数据 | — |
| `hanayoi_extract.py` | 返回 (lines, unknown) | `koei-embins-ps2` |
| `hanayoi_run.py` | 批量驱动 hanayoi_extract.py：多脚本合并成一份成品（一次点击 = 一行） | — |
| `hanazakari_extract.py` | 花朧 ～戦国伝乱奇～ (PSV, PCSG00855, Otomate/Idea Factory) 文本提取 | — |
| `handsome_bktr.py` | ハンサムロンダリング 更新档（Patch RomFS / BKTR）比对工具 | — |
| `handsome_nca.py` | ハンサムロンダリング -the mystic lover- (NS) 压缩 NCA（LZ4 桶树）解包 | — |
| `handsome_updraw.py` | ハンサムロンダリング 更新档（BKTR + LZ4 桶树）→ 最新 romfs 文件比对/提取 | — |
| `happygift_extract.py` | — | — |
| `happygift_flow.py` | — | — |
| `happygift_inspect.py` | — | — |
| `haruka2_appmatrix.py` | 从 BOOT.BIN 读取 16x16「呼び名」称呼矩阵 | `naninovel` · `stcm2l` |
| `haruka2_eem_extract.py` | 遙かなる時空の中で２ (PSP) 全文本提取 — 最终版 | — |
| `haruka2_eemlib.py` | Return (headerFields, sectionA, sectionB) for KOEID0 entry i. | `naninovel` · `stcm2l` |
| `haruka4_extract.py` | Extractor for 遥かなる時空の中で4 (PSP, Koei / Ruby Party). | — |
| `haruka5_extract.py` | 遙かなる時空の中で5 (PSP / ULJM-05821, Koei / Ruby Party) 全文本提取器 | — |
| `haruka6_dedup.py` | 遥かなる時空の中で6 DX —— 变体分支后处理：保留「默认名版」，删除「不含名字/泛指」的替代句 | `naninovel` · `stcm2l` |
| `haruka6_dict.py` | 遥かなる時空の中で6 DX —— 用語辞典（見出し語＋解説）构建器 v2 | `naninovel` · `stcm2l` |
| `haruka6_extract.py` | 遥かなる時空の中で6 DX (Switch) 全文本提取器 v2 | — |
| `haruka_extract.py` | Extractor for Koei / Ruby Party "Harukanaru Toki no Naka de" (遥かなる時空の中で) scripts. | — |
| `hatsukoi_extract.py` | [NS-JP]大人の初恋、はじめます（Nintendo Switch / Bezel Engine）剧本文本提取 | `bezel-bea` |
| `hb_extract.py` | [NS-JP]花笑む彼と & bloom（Him the Smile & Bloom）文本提取 —— Utage（宴） | `unity` |
| `heiligenstadt_extract.py` | 《ハイリゲンシュタットの歌》 (PS Vita / PCSG01070 / eXtend / Unity 5.6.1p4) 全文本提取 | `naninovel` · `nis-cpk-snbin` · `stcm2l` |
| `hg_extract.py` | ひぐらしのなく頃に奉＋Origin (NS) main.snr → 全文本 | `rom2` |
| `hime3_extract.py` | 星の王女3（美蕾 MADOKA GScript / CRPT type 3）文本提取 | — |
| `himehibi2_eboot.py` | ひめひび 続！二学期 —— 第 2 段：eboot 串表抽取 + 成品组装 | — |
| `himehibi2_extract.py` | Extract all displayed text from ひめひび ─New Princess Days!!─ 続！二学期 | — |
| `himehibi2ns_extract.py` | ひめひび ─New Princess Days!!─ 続！二学期 (NS-JP 01009B4012FC6000) 全文本提取 | — |
| `himehibi_crawl.py` | ordered list of callee script names (0x1e / 0x1d). | — |
| `himehibi_disasm.py` | SCR 2.00 (Takuyo gss / LSDARC) disassembler with auto-calibrated operand sizes. | — |
| `himehibi_extract.py` | Extract all displayed text from ひめひび -Princess Days- (PSV, Takuyo gss / LSDARC 'SCR 2.00'). | — |
| `himehibi_lsdarc.py` | LSDARC V.100 (Takuyo gss engine) reader. | — |
| `himehibi_ns_extract.py` | ひめひび -Princess Days-（NS-JP, 0100F8D0129F4000）全文本提取 | — |
| `himpac.py` | Himauri (SH System) HXP 容器解包 —— Him4 / Him5 | `himauri` · `livemaker` · `stcm2l` … |
| `himscript.py` | Himauri Script Engine (.him) → 文本 | `himauri` · `livemaker` · `stcm2l` … |
| `hiyoku_extract.py` | [JP]比翼は愛薊の彼方へ ～久遠の想～ (PC / SandalDash) text extractor. | — |
| `honeyvibes_extract.py` | Honey Vibes (NS 0100FB301E70A000) 剧本提取 —— Unity + 纯文本脚本 | — |
| `hoshifuru_extract.py` | 星の降る刻 (PS2-JP) —— UNION/SCRIPT.UNI 文本提取 | — |
| `hoshiiro_extract.py` | 星色のおくりもの (PSP-JP, 2008 Takuyo) full-text extractor. | — |
| `hoshinooujo_yoshitsune_codemap.py` | — | — |
| `hoshinooujo_yoshitsune_extract.py` | [PC-JP]星の王女 ～宇宙意識に目覚めた義経～ final extractor. | — |
| `hoshinoujo2_text.py` | [PC-JP]星の王女2（PC / 美蕾 MADOKA GScript・GSCE 编译包）全文本提取 | — |
| `hoshinoujo_extract.py` | 星の王女 (PC-JP, 2003) — Madoka GScript 旧式 .sce (CRPT 加密) 全文本提取 v1 | — |
| `hoshioji_extract.py` | [NS-JP]恋してしまった星の王子 ～誓願院編～ 文本提取（Bezel Engine / SCNE / scb_） | `bezel-bea` |
| `hoshitsubasa_extract_v10.py` | — | — |
| `houkago_gsc_extract.py` | Extract the verified HOUKAGO_KKN XFL/GSC script build, with click/page maps. | — |
| `hunex_hlzs.py` | HuneX HLZS（LZSS）解码器：dict 0x1000 / maxlen 0x12，解 script_dialog_xx.hdlg 等 HLZS 载荷 | — |
| `hws_dpmx.py` | HWS（Hunks Workshop! / エフジー）DPMX 容器解包 | — |
| `hy_extract.py` | 華ヤカ哉、我ガ一族 幻燈ノスタルジィ for Nintendo Switch（NS-JP, ichicolumn 自研 .lzs + SCD） | `lzs-scd` |
| `ikare_text.py` | [JP]イカレちんぽ屋（TVP/KiriKiri + KAG3）→ 一次点击＝一行 | — |
| `il2cpp_fields.py` | 纯 Python 读 IL2CPP global-metadata.dat 的类型定义/字段表（不反编译、零依赖） | — |
| `incest_crack.py` | 周期 keystream 破解：c[i] = p[i] ^ key[i % P]，key 每文件独立 | — |
| `incest_filter.py` | INNOCENT INCEST —— XP3 filter 解密（依据 sindata.tpm rva 0x1000 反汇编） | — |
| `incest_xp3.py` | INNOCENT INCEST data.xp3 —— 索引解析（带 flag/adler32），供攻坚探查用 | — |
| `innocentria_extract.py` | Extract Innocentria (NScripter 2.48 / game script ver.1.1). | — |
| `inspect_msgs.py` | 列出某 .spt 中以 \0 分隔的消息序列（解码 + 字节），用于肉眼确认格式 | — |
| `iowatch.py` | 按秒采样进程 I/O 计数与文本槽变化，定位"一次点击读了多少字节、出现哪些新文本" | — |
| `iso9660.py` | 极简 ISO9660 列目录 / 抽取（无依赖，支持 PSP UMD 镜像） | `stcm2l` |
| `iso_cut_cpk.py` | ISO9660 内指定 LBA 的 CPK 切出并解包 —— PSP（Zerodiv / CRI CPK 系）通用驱动 | `nis-cpk-snbin` |
| `isshoni_gohan_extract.py` | いっしょにごはん | — |
| `iza2_build.py` | いざ、出陣！恋戦 第二幕 ～甲斐編～ —— 按 scenelist 顺序组装全文本 | — |
| `iza2_unpack.py` | いざ、出陣！恋戦 第二幕 甲斐編 —— 批量解壳 + PSB 反编译 | — |
| `izasen_cpk.py` | いざ、出陣！恋戦 data.cpk 解包（CPK 名 cp932 修正版） | — |
| `izasen_extract2.py` | いざ、出陣！恋戦（PSP）全文本提取 v2：按 [next file] 链定顺序 | — |
| `izasen_stream.py` | いざ、出陣！恋戦 data.cpk → 剧本流还原 | — |
| `jade_yks.py` | 24時、君のハートは盗まれる～怪盗ジェイド～ 文本抽取（YKC 容器 → YKS 脚本 → 台詞/地の文） | — |
| `jewelic_extract.py` | Jewelic Nightmare (PSP, Otomate 2013, ULJM06326) 全文本提取 | `stcm2l` |
| `jingi_decrypt.py` | 仁義なき乙女 (CRPT type 3) 解密 —— 复用 tsundere 的 LCG 表/散列/scatter 核心，逐块 seed 复原 | — |
| `jingi_extract.py` | 仁義なき乙女（美蕾 MADOKA GScript / CRPT type 3）文本提取 | — |
| `jingi_text.py` | [PC-JP]仁義なき乙女 恋恋三昧（Madoka GScript / CRPT .sce）全文本提取 | — |
| `jk_extract.py` | JACKIN.img（CloneCD raw-2352 MODE1，LBA24 后插 2000 扇区）→ 按路径提取文件 | — |
| `jusanshi.py` | 十三支演義 偃月三国伝1・2 (NS) 正文提取 —— 容器链全部打通版 | `naninovel` · `stcm2l` |
| `jusanshi_dialog.py` | 十三支演義 偃月三国伝1・2 正文提取（AdvScript / MessagePack 容器） | — |
| `kaeru_extract.py` | カエル畑DEつかまえて☆彡 (NS-JP, TAKUYO) text extract. | — |
| `kag3_ks.py` | KAG3（KiriKiri 2.x）.ks 剧本 → 双版对照文本 | — |
| `kag_extract.py` | KiriKiri/KAG3 シナリオ(.ks) テキスト抽出 | — |
| `kaleido_extract.py` | カレイドイヴ (PSV / PCSG00520 / estciel & HuneX) 全文本提取器 | `hunex-hesl` · `naninovel` · `nis-cpk-snbin` … |
| `kamidachi_extract.py` | Ren'Py（RPA-3.0 + .rpy 明文源码）文本提取驱动 —— [PC-JP]神立ノ雨、鬼ノ唄 | — |
| `kamigami_scr_extract.py` | 神々の悪戯 Unite Edition（NS）→ 全文本 | `unity` |
| `kamikoi_extract.py` | 神さまと恋ゴコロ (NS-JP) text extract ---- Takuyo gss / LSDARC 'SCR 3.00'. | `naninovel` · `stcm2l` |
| `kamisama102_extract.py` | NScripter 文本提取器（源自 [PC-JP]神様を殺す102の方式） | — |
| `kamisama_extract.py` | もし、この世界に神様がいるとするならば | `naninovel` · `stcm2l` |
| `kannagi_extract.py` | 神凪ノ杜 五月雨綴り (NS-JP, Unity 2021 IL2CPP, Matatabi) 剧本正文 + 选项提取 | — |
| `kannou_extract.py` | 官能昔話 ポータブル (PSP, ULJM06015, vndb v9071) 全文本提取 | `stcm2l` |
| `kanuchi_dict.py` | カヌチ 二つの翼 用語辞典（ライブラリ）提取 | `idea-factory-ydp-lsb` |
| `kanuchi_text.py` | カヌチ 二つの翼 (PSP / Idea Factory 'YDP1' -> SCRIPT_LSB) 剧本文本提取 | `idea-factory-ydp-lsb` |
| `kanuchi_ydp.py` | カヌチ 二つの翼 (PSP / Idea Factory 'YDP1') 解包 | `idea-factory-ydp-lsb` |
| `kare_dx_extract.py` | カレと彼の間で DX: reuse rlvm-derived rl_decomp/rl_parse. | — |
| `katakago_extract.py` | [PC-JP]貴方の鳥籠（LiveMaker 3 / VF ver=102 / TpWord 102）驱动 | — |
| `kazahanaki_extract.py` | 遙かなる時空の中で5 風花記 (PSP / ULJM-05950, Koei / Ruby Party) 全文本提取器 | `naninovel` · `stcm2l` |
| `kaze_extract.py` | 風色サーフ (PS2) 全文本抽出器 | — |
| `kedamono_ns_build.py` | 猛獣使いと王子様 ～Flower & Snow～ for Nintendo Switch —— 成品构建 | — |
| `kedamono_ns_extract.py` | 猛獣使いと王子様 ～Flower & Snow～ (NS) STCM2L 提取：一次点击 = 一行 | — |
| `kimigatame_text.py` | [PC-JP]君がため、恋し乱れし月の華 | — |
| `kimikare_extract.py` | キミカレ ～キミとカレはじめました～ (PSP, 2012 / STCM2L) 文本提取 | — |
| `klap_extract.py` | KLAP!! for Nintendo Switch (NS) STCM2L 文本提取（STCM2L Apr 12 2018 18:22:39 变体） | — |
| `klap_trace.py` | KLAP!! STCM2L 单段 opcode 追踪：看「一行多句」在代码层是怎么分隔的 | — |
| `kochouran_extract.py` | Otomedou Kochouran: strict XP3 reader and game-specific KAG extraction. | — |
| `kochouran_kag.py` | Source-aware KAG lexer for Otomedou Kochouran (KAG 3.30). | — |
| `kochouran_text.py` | Extract Kochouran KAG text using source control flow and Win32 font advances. | — |
| `koei_dec.py` | アンジェリーク エトワール (PS2) PACK 成员解压 —— 由 SLPM 0x142c80 (type1) 反编译还原 | — |
| `koibana_extract.py` | 恋花デイズ (PSP / Otomate, STCM2L in CRI CPK) 文本提取 | — |
| `koibann2_extract.py` | 恋愛番長2 MidnightLesson!!! (PSP-JP / Rejet×Otomate 2011) 剧本文本提取 | `stcm2l` |
| `koibann_extract.py` | 恋愛番長 命短し、恋せよ乙女！ Love is Power (PSP-JP / Rejet×Otomate 2010) 剧本文本提取 | `stcm2l` |
| `koigig_extract.py` | KoiGIG ～DEVIL×ANGEL～ (TWOFIVE / DonMaccow, 2007) 文本提取器 | `naninovel` · `stcm2l` |
| `koinohana_extract.py` | [NS-JP]恋の花咲く百花園 text extract (Takuyo gss / SCR 3.00, unpacked OBJ). | — |
| `koishiba_charset.py` | 恋は校則に縛られない！（PSP / Vridge・Kadokawa Games）—— sc.cpk 字符集与专用槽 | — |
| `koishiba_font.py` | 恋は校則に縛られない！（PSP / Vridge・D3P 系）lt.bin 字形渲染 | — |
| `koishiba_run.py` | 恋は校則に縛られない！（PSP）—— USRDIR/DATA/sc.cpk → 全文本 | — |
| `koutari_audit.py` | audit all 16 .spt: dump first samples + counts to decide include/exclude. | — |
| `koutari_extract.py` | 神足町人妖譚 ~迷イ子ノ章~ (PC / System-NNN「NNNLib」) 全文本提取 | — |
| `koutari_extract2.py` | 神足町人妖譚 (PC-JP / System-NNN「NNNLib」engine) 全文本提取 · 定稿（对齐槽版） | — |
| `ks_kag_text.py` | KAG3（KiriKiri）剧本 .ks -> 全文本（双版：段行＋合并行） | `himauri` · `livemaker` · `stcm2l` … |
| `kuro_build.py` | 蒼黒の楔 (NS-JP, Unity/Utage) 剧本 → 全文本（双版对照） | — |
| `kuro_dump.py` | 蒼黒の楔 (NS) — Unity AdvChapterData/AdvImportBook 剧本落盘 | — |
| `l2ll_extract.py` | L2 Love×Loop (PS2 / Idea Factory / SLPM-55191) 剧本文本提取 | `koei-embins-ps2` · `nis-cpk-snbin` |
| `l7c.py` | L7CA (Bandai Namco / Vita resource archive) 解包器 | — |
| `lamento_extract.py` | Lamento -BEYOND THE VOID- (Windows 10 Support Edition) — Nitroplus NPA / NSS | `naninovel` · `stcm2l` |
| `lastconvert_extract.py` | Last Convert (NScripter / nscript.dat, 全字节 XOR 0x84) -> 双版对照文本 | — |
| `lastescort_cmp.py` | 对比 深夜の黒蝶物語（本编）与 黒蝶スペシャルナイト（追加碟）的 ADV.FPK / VML | — |
| `lastescort_extract.py` | ラストエスコート -Club Katze- (PSP) 全文本提取 —— 通用驱动 | — |
| `lastescort_ps2_extract.py` | ラスト・エスコート 〜深夜の黒蝶物語〜 (PS2 / SLPS_255.91 / D3P・Vingt-et-un) 全文本提取 | — |
| `lastescort_vml.py` | ラスト・エスコート 〜黒蝶スペシャルナイト〜 (PS2-JP / D3PUBLISHER, SLPS_256.73) | `koei-embins-ps2` |
| `lasting_snow_wbc.py` | Extract text from Lasting Snow (Witch/Katze) system/text_data.wbc. | — |
| `le_extract.py` | DIABOLIK LOVERS LOST EDEN (PSV, PCSG00910) 文本提取 | `dat-pak-scd` |
| `lf_probe_slots.py` | 探查 STCM2L 的 tag=0x35404 记录：8 槽 = 两套（各 4 槽：标记 + 3 行） | `stcm2l` |
| `libp_malievita.py` | Malie（Vita）Libp 归档读取库：入口表 / 文件名 / 数据切片 | `nis-cpk-snbin` |
| `littleaid_extract.py` | Little Aid Portable (PSP-JP, 2007 Takuyo, ULJM-05...) full-text extractor. | — |
| `littleanchor_extract.py` | リトルアンカー（PS2-JP / SLPS-25929 / Vridge）全文本提取 | — |
| `livemaker_extract.py` | LiveMaker 3 通用文本提取（VF 归档 ＋ LMScript .lsb ＋ LiveNovel TpWord） | `himauri` · `livemaker` · `stcm2l` … |
| `livemaker_parallel_lovers.py` | [JP]Parallel Lovers 前編（LiveMaker 3）文本提取（自定义剧情顺序版） | — |
| `livemaker_sugar.py` | [JP]Sugar（LiveMaker 3 / 野良猫企画 2016）文本提取驱动 | `himauri` · `livemaker` · `stcm2l` … |
| `livemaker_tsukimori.py` | [PC-JP]月と森とあなたとわたし（LiveMaker 3, ver102）提取驱动 | — |
| `livemaker_utahime.py` | [PC-JP]歌姫と王様（LiveMaker 3 / VF ver=102）文本提取 | — |
| `looselips_extract.py` | [Loose Lips series] RPG Maker MV text extractor (Enigma-boxed single exe). | — |
| `lovebeat_extract.py` | 放課後のLove Beat（PS2 / HuneX ADVD, SLPM_655.79）文本提取 | — |
| `lovepeace_extract.py` | 恋戦隊LOVE＆PEACE THE P.S.P. (PSP / BROCCOLI 2012) MES.DAT text extractor. | — |
| `loverevo_extract.py` | 乙女的恋革命★ラブレボ!! Portable (PSP) 全文本提取 | — |
| `loveroot_extract.py` | PS2『ラブルートゼロ kisskiss☆ラビリンス』(Dimple/Asgard 2010) 全文本抽出 | — |
| `lp_extract.py` | DIABOLIK LOVERS LUNATIC PARADE (PSV, PCSG00826) 文本提取 | `dat-pak-scd` |
| `lpv_extract.py` | LoverPretend (NS-JP) STCM2L 文本提取 —— 第一版（正文串有序导出） | — |
| `lpv_extract_final.py` | LoverPretend (NS-JP) 文本提取 —— 定稿 v2 | `stcm2l` |
| `lpv_probe.py` | LoverPretend / STCM2L 节点探针：找 [0][L/4][1][L][utf8 text] 强签名 | — |
| `lpv_scan.py` | LoverPretend STCM2L 节点扫描（L = align4(len+1)，含 NUL+padding） | — |
| `lpv_stream.py` | 按 [op][0x13a][id][0x10] 三元组重建 STCM2L 指令流 | `stcm2l` |
| `lpv_walk.py` | LoverPretend STCM2L 节点链行走器 | `stcm2l` |
| `lsb.py` | LSB 剧本解析（VSC 引擎 / ラスト・エスコート2 ～深夜の甘い棘～ PS2-JP） | — |
| `lua51.py` | Lua 5.1 bytecode 解析（Vita/PSV 乙女作常见：脚本编译为 luac 5.1） | — |
| `lua53.py` | Lua 5.3 luac 解析（PSV 变体：32 位、lua_Number=float32、varint 长度） | — |
| `lucian_extract.py` | Lucian Bee's: Resurrection Supernova (PSP, 2010, HuneX IKA SEQ SYSTEM v3.4) | `hunex-ika` |
| `lucianj_extract.py` | Lucian Bee's: Justice Yellow (PSP, 2010, 5pb./HuneX) —— 全文本提取 | `hunex-als` · `hunex-ika` |
| `lucianv_extract.py` | Lucian Bee's: Evil Violet (PSP, 2010, 5pb) —— 全文本提取 | `hunex-ika` |
| `lucky1_extract.py` | [JP]ラッキードッグ１ (PC / Will-ARCG + Kagura TLV bytecode) text extractor. | — |
| `luckydog_extract.py` | ラッキードッグ1 Secret Diary F（PC-JP，Adobe AIR／jp.co.woga.was 引擎）文本提取器 | `himauri` · `livemaker` · `stcm2l` … |
| `lustras_audit.py` | Independent source, resource and output audit for Innocentria Lustras. | — |
| `lustras_extract.py` | Extract the bundled Innocentria Lustras 1.7 NScripter script. | — |
| `lzo1x.py` | LZO1X-1 (miniLZO) 解压器 + event.enc entry 解压测试 | — |
| `madoka_gscript_extract.py` | Madoka GScript (CRPT) scenario text extractor — engine: 美蕾/MP2. | — |
| `majikyun_extract.py` | マジきゅんっ！ルネッサンス (PSV / PCSG00852 / HuneX & BROCCOLI) 全文本提取器 | `hunex-hesl` · `naninovel` · `stcm2l` |
| `make_pr_ledger.py` | — | — |
| `makumatsu_extract.py` | 《幕末Rock 超魂》(PS Vita / PCSG00425 / Marvelous) 全文本提取 | — |
| `malie_extract.py` | Malie System (GreenWood) 通用提取工具 —— OmegaVampire repack / 断罪のマリア 实证. | `malie` · `nis-cpk-snbin` |
| `manimani_extract.py` | 花咲くまにまに (PSV, PCSG00366, MAGES. / SC3) 文本提取 | — |
| `marc_font.py` | 5pb PSP (Musketeer/EVB engine) MARC font atlas unpacker. | — |
| `marginal4_extract.py` | [PSV-JP] MARGINAL#4 IDOL OF SUPERNOVA (PCSG00448, Otomate x Rejet / Idea Factory) | `dat-pak-scd` |
| `marginal4rtg_extract.py` | [PSV-JP] MARGINAL#4 ROAD TO GALAXY (PCSG01008, Otomate x Rejet / Idea Factory) | `dat-pak-scd` |
| `matsurika_build.py` | マツリカの炯-kEi- 天命華燭伝 文本成行（在 matsurika_extract 之上） | — |
| `matsurika_extract.py` | マツリカの炯-kEi- 天命華燭伝 (NS-JP) 全文本提取 | `vridge` |
| `mdb_scen_text.py` | VB5 自研 AVG（剧本库＝Access Jet .MDB，台本＝日文指令 DSL）→ 「一次点击 = 一行」 | `overflow-adv` |
| `meiji_extract.py` | 明治活劇 ハイカラ流星組 (NS-JP) テキスト抽出. | `nis-cpk-snbin` |
| `meiji_lzs.py` | 明治活劇 ハイカラ流星組 (NS-JP) の .lzs 解凍器 (c) 2026. | `lzs-scd` · `nis-cpk-snbin` |
| `meine_extract.py` | [PS2-JP] マイネリーベ 優美なる記憶 text extractor. | — |
| `mem_harvest_text.py` | — | — |
| `mem_probe.py` | — | — |
| `mem_scan.py` | 读取运行中进程的内存，按编码搜日文串（用于「格式解不开时，直接从运行时抓明文」） | `unity` |
| `mem_watch_harvest.py` | — | — |
| `memcollect.py` | 运行中进程的日文文本高频采样器（PC 游戯 运行时提取） | — |
| `memdump.py` | 从进程内存 dump 一段区间到文件 | — |
| `memdump_win32.py` | 从**正在运行**的 32 位游戏进程里按绝对地址读内存并 dump（不启动游戏） | — |
| `memscan.py` | 扫描另一个进程的内存，按多种编码查找关键词（用于判断某段文本在运行时是否以明文存在） | — |
| `memscan_jp.py` | 从运行中的进程内存里捞 CP932 日文（PC 游戯 文本提取的「运行时」路线） | — |
| `memtext.py` | 遍历进程内指定 guest 地址区间的已提交区域，就地提取 cp932 日文段落 | — |
| `merge_name_variants.py` | 双版拼接合并工具（名字宏双版 / 点名版↔泛称版） | — |
| `mermaid_run.py` | マーメイドプリズム (PS2-JP) 全文本提取 | — |
| `mermaid_scan.py` | マーメイドプリズム (PS2, SLPS_256.96) — ADVIMG.ADP 内 VML 走查/统计 | — |
| `mermaid_vml.py` | マーメイドプリズム VML 提取库（ADP 容器 + JIS7 字符串池 + 32bit op 流） | — |
| `messiah_extract.py` | メサイア（PC / GsWin「DataPack5」+ Scw5.x 脚本）文本提取器 | — |
| `messiah_pp_extract.py` | メサイア～パラノイア・パラドックス～（PC 2008 / GsWin「DataPack5」+ Scw5.x）文本提取器 | — |
| `minus8_extract.py` | マイナスエイト (-8) PSP, Otomate/Rejet, ULJM06341, vndb v12155 —— 全文本提取 | `stcm2l` |
| `mips_xref.py` | 线性扫描 + lui/addiu 地址恢复（PS2 R5900） | — |
| `miryo_extract.py` | [JP]比翼は愛薊の彼方へ ～未了の因～ (PC 2006 / SandalDash) text extractor. | — |
| `mist_extract.py` | ミストニアの翅望 -The Lost Delight- —— Unity/UTXT 文本（与 テミラーナ 同引擎） | — |
| `mist_romfs.py` | ミストニアの翅望 —— 压缩 NCA(BKTR/LZ4 bucket-tree) → RomFS 直读（复用 redbell_romfs 的桶树实现） | — |
| `mitsu_extract.py` | 蜜×蜜ドロップス LOVE×LOVE HONEY LIFE (PS2-JP, SLPM-663.81 / Otomate·Design Factory 2006) | — |
| `mizu2_extract.py` | 水の旋律2 ～緋の記憶～ (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本 | `thfs` |
| `mizu_extract.py` | 水の旋律 (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本 | — |
| `mizumelody_arc.py` | 水の旋律 ～協奏曲～ (PC, KID/mlk ADV 引擎) ARC0 归档解包 | — |
| `mizumelody_text.py` | 水の旋律 ～協奏曲～ (PC) 剧本成行 —— mlk/ADV 脚本 (cp932) | — |
| `mk2_extract.py` | [NS-JP]リトルプリンセス マール王国の人形姫２ —— message.bin → 成行 | `vfs3-pak` |
| `mk3_extract.py` | [NS-JP]天使のプレゼント マール王国物語 —— talk.dat / script.dat → 成行 | `vfs3-pak` |
| `mk_extract.py` | マール王国の人形姫（NS）文本提取器 | `vfs3-pak` |
| `ml2_disasm.py` | 最小 MIPS R5900 反汇编器（capstone 封装）——用于读 SLPM 里的解压函数 | — |
| `ml2_emul.py` | 直接执行 SLPM_662.47 内的解压例程（unicorn, MIPS64/R5900 子集）. | — |
| `ml2_text.py` | 从 SCPT 场景脚本抽取正文/选项（一行＝一次点击） | — |
| `ml2_tkl.py` | [PS2-JP] マイネリーベII tkl 容器 + type-2 解压 全链路工具. | — |
| `ml2_type2.py` | Konami tkl 'type 2' (flags&0xF==2) 解压器 —— 逆向自 SLPM_662.47 0x135e30 | — |
| `ml2_unpack.py` | [DEPRECATED] 已被 ml2_tkl.py 取代（本文件的 flags=1 LZSS / flags=2 实现均不正确） | — |
| `mn_extract.py` | 華ヤカ哉、我ガ一族 モダンノスタルジィ for Nintendo Switch（NS-JP, ichicolumn 自研 .lzs + SCD） | `lzs-scd` |
| `moneyparasite_extract.py` | Money Parasite 〜嘘つきな女〜 (TAKUYO gss / SCR 2.00) text extractor. | — |
| `mono_extract.py` | Monochrome Factor - Cross Road (PS2, 5pb) scene text extractor. | — |
| `moon_atl_extract.py` | 月ノ光太陽ノ影 (PC/ATL engine) 全文本提取 | — |
| `mothergoose_extract.py` | マザーグースの秘密の館（PSP / 2011, Otomate）文本提取 | — |
| `mtj_extract.py` | [NS-JP]マツリカの炯 -kEi- 天命胤異伝 全文本提取 | `otomate-tatc-rson` |
| `musketeer_charset.py` | Musketeer (PSP/5pb) .evb text decoder -- solved 2026-10-13. | `stcm2l` |
| `musketeer_extract.py` | Musketeer (PSP/5pb) .evb -> text. | `stcm2l` |
| `musketeer_render_atlas.py` | 5pb PSP MARC font-atlas renderer (ar999_0000.bin). | — |
| `mysteria_extract.py` | 英国探偵ミステリア The Crown (PSV, Malie System / MalieVita) exec.dat -> text. | `naninovel` · `stcm2l` |
| `mysteria_pc_text.py` | PC Japanese Mysteria: Camellia LIBP (1024-byte sectors, 4096 alignment), Malie VM. | — |
| `mysteria_text.py` | 英国探偵ミステリア The Crown (PSV) —— Malie exec.dat → 全文本（一次点击 = 一行） | `naninovel` · `stcm2l` |
| `nana_extract.py` | [PS2-JP] NANA -ナナ- text extractor. | — |
| `nana_unpack.py` | [PS2-JP] NANA -ナナ- STORY/ALLSC.NKP 解包（Konami NKP 嵌套） | — |
| `naninovel_assemble.py` | 把 naninovel_extract.py 的 _scripts.json 组装成 §0 规范成品 txt | `naninovel` · `stcm2l` |
| `naninovel_extract.py` | Naninovel (Unity IL2CPP) 脚本文本提取器 | `naninovel` · `stcm2l` |
| `nca_romfs.py` | 通用：NSP/NCA 就地读 romfs（不落副本） | `stcm2l` |
| `nca_stream_romfs.py` | Switch 容器流式取 romfs 文件（不落 NCA/NSP 副本，省盘） | `otomate-sscn` |
| `neoange_psp_extract.py` | ネオアンジェリークSpecial (PSP-JP, Koei) 全文本提取 | — |
| `neoangelique_extract.py` | ネオ アンジェリーク 天使の涙 (PSV-JP, PCSG01068, Otomate / Idea Factory) 全文本提取 | — |
| `neon_dialog.py` | ネオンクラッシュ -Echoes of the Lost- 正文提取（成品生成） | `naninovel` · `stcm2l` |
| `neon_findtext.py` | 用 UnityPy 逐个加载 bundle（真解压），统计对象 raw 里的假名数量，找出「文本库」所在 bundle | — |
| `neon_nca.py` | ネオンクラッシュ (NS) 压缩 NCA（LZ4 桶树）解包 —— 内容密钥由 ticket 解出后经 NCA_KEY 传入 | — |
| `niladmirari_extract.py` | ニル・アドミラリの天秤 色ドリ撫子 (Switch) —— 全文本提取器 | `stcm2l` |
| `nisenochigiri_extract.py` | 二世の契り (PSP-JP, Otomate, 2011) 全文本提取 | `stcm2l` |
| `nisenochigiri_fd_extract.py` | FD『二世の契り 想い出の先へ』(PSP-JP, Otomate, STCM2L) 全文本提取 —— 泛化版 | `stcm2l` |
| `noa_unpack.py` | Entis GLS / ERISA 'noa' archive unpacker. | — |
| `norn9_extract.py` | Norn9 ～Norn + Nonette～ Act Tune (PSV, PCSG00833) 剧本文本提取 | `naninovel` · `stcm2l` |
| `npa_nrbf.py` | Nitroplus NPA 内 NRBF（.NET BinaryFormatter）序列化数据的解析器 | `naninovel` · `stcm2l` |
| `npk3.py` | NPK3 (Nitroplus Diesel Engine) unpacker. | — |
| `ns_dual.py` | NScripter（nscript.dat，整文件 XOR <key>）-> 「双版对照」全文本 | `himauri` · `livemaker` · `stcm2l` … |
| `ns_extract.py` | NScripter (nscript.dat) 全文本提取器 —— 「双版对照」口径 | `himauri` · `livemaker` · `stcm2l` … |
| `ns_open.py` | NS 统一入口 —— 一条命令走完 XCI/NSP/NCA 的判定与解包，并**打印为什么选这条路** | `nis-cpk-snbin` |
| `ns_rip.py` | NScripter (nscript.dat) 文本提取器 | — |
| `ns_talkbmp_text.py` | NScripter：正文 + **位图台词（talk_*.bmp ＋ 作者 ; 注释）** 双版对照提取 | `himauri` · `livemaker` · `stcm2l` … |
| `nsac.py` | NSAC (v2) 容器解析/解包 —— eXtend 系 PSVita 作品《逢魔が刻 ～かくりよの縁～》(PCSG00769) | `nis-cpk-snbin` · `nis-nml` |
| `nscripter_dat.py` | NScripter nscript.dat → 双版对照文本（海色小夜曲ーウミイロセレナーデー） | — |
| `nscripter_ivan.py` | NScripter script text extractor — [JP]イワンは見た! (WILD ROSE doujin ADV) | — |
| `nso_x.py` | NSO0 -> 平铺镜像（text/rodata/data 依次拼接，LZ4 段自动解压） | — |
| `nsp_list.py` | 列/取 NSP(XCI 内 PFS0) 的条目 —— 只读 PFS0 头，不涉及解密 | — |
| `nsp_nca_romfs.py` | ワンド オブ フォーチュン Ｒ２（Switch）—— NSP → Program NCA → RomFS 枚举／导出 | `selfpak-utf16-vm` · `stcm2l` · `unity` … |
| `nsp_pfs0_dump.py` | 纯 Python 解析 PFS0(NSP) 并导出条目（hactool 吃不了 CJK 路径） | — |
| `nsp_plainromfs.py` | 通用：NSP/PFS0（或裸 NCA）内**未压缩** RomFS 的就地列出/提取 | — |
| `nsp_romfs_bulk.py` | NSP 内 romfs 批量就地提取（按正则/大小筛选），一次开 NCA 多次落盘 | — |
| `nsp_split.py` | PFS0(NSP) 逐块直拷拆分器 —— 规避 hactool --pfs0dir 对 >1.7GB 成员写全零的问题 | `nis-cpk-snbin` |
| `ofadv_script.py` | Stack OverFlowADV 3.00 SCRIPT.DAT 解析器 | `overflow-adv` |
| `oga_sts_extract.py` | O*G*A 鬼ごっこロワイアル ハンターは孤島で恋をする (PSP-JP / Idea Factory・Otomate) | `stcm2l` |
| `oga_tob_extract.py` | O*G*A 鬼ごっこロワイアル (PSP, Idea Factory/Otomate "oni") —— .tob 字节码级框提取 | — |
| `ojisama_extract.py` | [JP]２人の王子（AbelCain / 「シナリオくん」エンジン）文本提取 | `himauri` · `livemaker` · `stcm2l` … |
| `ol_extract.py` | [NS-JP] オランピアソワレ Catharsis for Nintendo Switch —— STCM2L 文本提取 | `stcm2l` |
| `omegavamp_extract.py` | オメガヴァンパイア (NS) SCRIPT.PAK → 全文本（一行＝一次点击） | — |
| `omegavamp_nca.py` | オメガヴァンパイア(NS) 专用 NCA/RomFS 按需解密提取器（不改共用 scripts/switch_nca.py） | — |
| `oni_extract.py` | [NS-JP]十鬼の絆 (Bond Of Ten Oni) STCM2L 文本提取 | `stcm2l` |
| `oni_xci_nca.py` | XCI → 就地读 NCA → RomFS 枚举/导出（不过 hactool，不落 NCA） | `overflow-adv` · `stcm2l` · `unity` |
| `orange_build.py` | Orange Honey 全文本成行 | — |
| `orange_dump.py` | 导出全部 .OHS 的字符串池为 TSV（file, idx, off, text） | — |
| `orange_ohs.py` | OHS 文本段解密：blob 从 0x28 指向处到文件尾，SBOX(0x40..0x140) 递减异或解密 | — |
| `orange_peta.py` | Orange Honey (PS2, guyzware) — PETA(PTH/PTD) 解包 | — |
| `orfleur_extract.py` | オルフレール ～幸福の花束～ (PSV PCSG00919 / dramatic create「Orfre」DCVM) 文本提取 | `dcvm` |
| `orfleur_stbl_extract.py` | オルフレール ～幸福の花束～ (PSV / PCSG00919, dramatic create「Orfre」/ DCVM) | — |
| `orfleur_trace.py` | Orfre/DCVM 执行序追踪（CFG 走块 + 调用捕获）——用于确定「一次点击=一行」的显示序 | — |
| `orfleur_vm.py` | Orfre/DCVM 线性走链器：用于恢复「一次点击 = 一行」的文本序 | — |
| `os_extract.py` | [NS-JP] オランピアソワレ（本篇）for Nintendo Switch —— STCM2L 文本提取 | `stcm2l` |
| `otome_kayuu_extract.py` | Otomate STCM2L · Switch「函数指针型」文本提取（燃えよ！乙女道士 ～華遊恋語～） | — |
| `ouma_build_text.py` | 《逢魔が刻 ～かくりよの縁～》系统/资料文本整理 | `nis-cpk-snbin` |
| `ouma_extract.py` | 《逢魔が刻 ～かくりよの縁～》(PSVita / PCSG00769) 游戏内文本提取 | `nis-cpk-snbin` |
| `ouma_story.py` | 《逢魔が刻 ～かくりよの縁～》本編 ADV シナリオ抽出 (NML スクリプト) | `nis-cpk-snbin` |
| `ouran_extract.py` | 桜蘭高校ホスト部 (PS2-JP, SLPM-667.38 / Otomate·Idea Factory 2006) 剧本文本提取 | — |
| `overreq_extract.py` | [NS-JP]OVER REQUIEMZ —— 全文本提取（Unity + Otomate 命令式脚本 DSL） | `overflow-adv` · `unity` |
| `oyayubi_psv_extract.py` | PCSG00611: extract narrative text from MalieVita scripts only. | — |
| `ozmafia_extract.py` | OZMAFIA!! -vivace-（Nintendo Switch, 01002BE0118AE000, HuneX「Ogre」系 Switch 变体） | — |
| `ozmafia_nca.py` | NCA 头/key area 检视器（Switch）—— 用于旧 hactool 无法处理的 BKTR 增量补丁 NCA | — |
| `pack_cmp.py` | VividColor «GameSystem» *.cmp PACK 容器工具（PC） | `vividcolor` · `yuuki-novel` |
| `palais_reine_extract.py` | Palais de Reine (PS2 JP, SLPM-66817) compiled native-script text extractor. | — |
| `pandora_extract.py` | PANDORA ～君の名前を、僕は知る～ (PS2, Otomate / Idea Factory 2010) 剧本文本提取 | `naninovel` · `nis-cpk-snbin` · `stcm2l` |
| `panic_extract.py` | Panic Palette (NS-JP, TAKUYO) text extract. | — |
| `paradigm_paradox_extract.py` | Paradigm Paradox (Regista advGame engine) 全文本提取器 —— 定稿 | `naninovel` · `stcm2l` |
| `paradise_jp_extract.py` | [JP]Paradise (PS2 / D3P Daisy2 / DDP3) 全文本提取 | `koei-embins-ps2` |
| `paradise_musubi_extract.py` | [JP]Paradise 結-MUSUBI- (PS2 / D3P Daisy2 / DDP3) 全文本提取 | `koei-embins-ps2` |
| `paradise_pfk_extract.py` | [JP] Paradise 極-KIWAME- (Daisy2 / DDP3) text extractor. | — |
| `pc_snr_order.py` | 从 PC 汉化补丁的 .snr（UTF-16LE KiriKiri 脚本）提取「剧情序」标尺 | `dcvm` |
| `pcube_extract.py` | ピリオドキューブ ～鳥籠のアマデウス～ (PSV, PCSG00853) 剧本文本提取 | — |
| `pe_dis.py` | PE 反汇编辅助（capstone）：按 RVA/VA 定位并打印附近指令 | — |
| `pe_extract.py` | [NS-JP] ピオフィオーレの晩鐘 -Episodio1926- —— STCM2L 文本提取 | `stcm2l` |
| `pentagon_build.py` | Pentagon Syndrome（LiveMaker/LiveNovel LSB v117）成行器 | — |
| `pentagon_extract.py` | Pentagon Syndrome（LiveMaker/LiveNovel LSB v117）文本提取 | — |
| `pentagon_vff.py` | LiveMaker VFF 资源包解包（Pentagon Syndrome / 单 exe 全内嵌） | — |
| `perfect_prince_extract.py` | [JP]Perfect Prince (GimmickHouse 2002) — TextScript(c-system) 全文本提取器 | — |
| `period55.py` | 55 字节周期 XOR 键的爆破与验证（用于 .het 辞书） | `nis-cpk-snbin` |
| `peta_extract.py` | ペット探偵Y's (AMEDEO, RealLive) 文本提取 | — |
| `peterpan_extract.py` | QuinRose Qoo (PSV) —— [PSV-JP]新装版 お菓子な島のピーターパン 剧本成行 | — |
| `petitfleur_text.py` | [JP]Petit Fleur -丘を渡るクリスタルの風- (Macromedia Director 10.1 / RIFX, zlib 分块) | `himauri` · `livemaker` · `stcm2l` … |
| `petitfour_extract.py` | プティフール (PS2-JP, SLPM-66945 / Otomate·Design Factory 2008) 剧本文本提取 | — |
| `pf_extract.py` | [NS-JP] ピオフィオーレの晩鐘 -ricordo- —— STCM2L 文本提取 | `stcm2l` |
| `pigeon_blood_extract.py` | [JP]Pigeon Blood (PC / PIL-SLASH / D3P Daisy2 DDP3) 全文本提取 | — |
| `plasticboys_extract.py` | [JP]Plastic Boys ～水色のキモチ～ 全文本提取 | — |
| `pleasure_text.py` | — | `himauri` · `livemaker` · `stcm2l` … |
| `pnm_extract.py` | Princess Nightmare (PS2, SLPM-66973) script text extractor. | — |
| `poi_extract.py` | 『っポイ!』ひと夏の経験!? (PS2-JP, SLPM-55012 / Otomate·Design Factory 2008) 剧本文本提取 | — |
| `polwhite_audit.py` | Verify source conservation, page layout and character provenance for White EA. | — |
| `polwhite_capture.py` | Capture and advance only an isolated native validation process. | — |
| `polwhite_extract.py` | Polifonica Memories White EA: checked RealLive bytecode, click/page export. | — |
| `polwhite_fe_report.py` | Package checked FE provenance and write the extraction report. | — |
| `polwhite_finish_native.py` | Remove only validation registry keys and restore the user's game window. | — |
| `polwhite_inventory.py` | Inventory archive, disc and installation; verify relevant files only. | — |
| `polwhite_native_validate.py` | Build isolated native-engine excerpts to check two automatic-page candidates. | — |
| `polwhite_probe.py` | Locate the running Polifonica installation and capture its window without input. | — |
| `polwhite_report.py` | Package the verified provenance and write White EA's extraction report. | — |
| `possession_extract.py` | Extractor for Possession Magenta (ポゼッション マゼンタ, PSV, PCSG00509). | `naninovel` · `stcm2l` |
| `powdergray_extract.py` | — | — |
| `prince5_extract.py` | 5人の恋プリンス ~ヒミツの契約結婚~ (PSV, PCSG00590) 文本提取 | — |
| `prince_stride_lt.py` | プリンス・オブ・ストライド (PSV PCSG00491) —— lt.bin 字形图集渲染（2026-10-12） | `naninovel` · `stcm2l` |
| `prince_stride_run.py` | プリンス・オブ・ストライド (PSV PCSG00491) —— sc.cpk → 全文本（2026-10-12） | `naninovel` · `stcm2l` |
| `princessbritania_text.py` | [PC-JP]Princess Britania～ミューズの宝剣～（KiriKiri XP3 ＋ Crafter/RAT 扩展 KAG3 · linemode=free）全文本提取 | — |
| `probe_akaru.py` | — | — |
| `probe_bytes.py` | — | — |
| `probe_dump.py` | — | — |
| `probe_koutari.py` | koutari 侦查：罗列两类可疑行的证据（源文件 + 原始字节） | — |
| `probe_kp.py` | — | — |
| `probe_pr_all.py` | — | — |
| `probe_pr_ascii.py` | — | — |
| `probe_pr_complete.py` | — | — |
| `probe_pr_exeparse.py` | — | — |
| `probe_pr_exeres.py` | — | — |
| `probe_pr_gamedat.py` | — | — |
| `probe_pr_refs.py` | — | — |
| `probe_pr_source.py` | — | — |
| `probe_pr_static.py` | — | — |
| `probe_pr_verify.py` | — | — |
| `probe_runs.py` | — | — |
| `probe_struct.py` | — | — |
| `probe_ui.py` | 扫描所有 spt，列出含 UI/菜单关键词的消息（源文件 + 原文） | — |
| `procboth.py` | 联合监视：游戏文件读取位置变化 + guest 堆中新出现的 cp932 日文串 | — |
| `procfpos.py` | 列出指定进程打开的游戏文件及其当前读写位置（GetFilePointer） | — |
| `prochandles.py` | 列出指定进程当前打开的文件路径 | — |
| `procwatch.py` | 实时监视进程内游戏文件的读取位置变化，定位"引擎刚刚读了哪一段" | — |
| `prometheus_extract.py` | [JP]Live x Evil 熱砂のプロメテウス — KiriKiri XP3 / KAG3 全文本提取器 | — |
| `ps2_extract.py` | PS2 .HD/.BIN extractor for the *Hakarena Heart*-type engine. | — |
| `ps2_game.py` | VM-level extraction: one line per message box (one click). | — |
| `ps2_scene.py` | Classify one 08-record payload. | — |
| `ps2_vm.py` | VM-level .cnut (Squirrel 'SQIR'/PART container) dialogue extractor for | — |
| `psarc_extract.py` | PSARC (Sony) extractor — big-endian classic PSARC. | `nis-cpk-snbin` |
| `psp_prx_type9_decrypt.py` | PSP ~PSP (EncryptType 9) EBOOT.BIN decrypter. | — |
| `psvskip_patch.py` | 让 psvpfsparser 在单文件解密失败时继续（跳过），不整进程退出 | `nis-cpk-snbin` |
| `psycemo6_extract.py` | PsychicEmotion6 (PSV / PCSG00815 / Otomate x Idea Factory / 2015) 全文本提取 | `dat-pak-scd` · `naninovel` · `stcm2l` |
| `psychicrain_text.py` | [PC-JP]Psychic Rain — REAL scenario extractor. | — |
| `psyeclipse_extract.py` | — | — |
| `pwa_crypto.py` | — | — |
| `pwa_extract.py` | — | — |
| `qpk.py` | QuinRose / Qoo-framework QPK/QPI archive reader (PSP). | `nis-cpk-snbin` |
| `qualia_extract.py` | [JP]Qualia～クオリア～ テキスト抽出 (KiriKiri/KAG3, data.xp3 内嵌 PE ラップ) | `kirikiri` |
| `radian_extract.py` | ラディアンテイル（本体，非 FD）—— STCM2L "May 18 2015" 变体 → 全文本 | `stcm2l` |
| `radian_split.py` | ラディアンテイル（STCM2L "May 18 2015" 变体）—— **按源结构把「并框」拆开** | `naninovel` · `stcm2l` |
| `rakido_extract.py` | RAKIDOMania black dog 文本提取器 | — |
| `rakuen_extract.py` | 楽園男子 ～誰も知らない もう一つの楽園～ (PSP, Takuyo gss / LSDARC V.100 'SCR 2.00') | — |
| `ramsnap.py` | 把 guest 内存整段 dump 到文件（分块读，支持 100MB 级区域） | — |
| `rar5_list.py` | RAR5 文件头遍历器：不解压、只读块头，快速列出文件名（大固实包用） | — |
| `ratw_extract.py` | RATW 提取：分离式 VF（game.ext 目录 + game.dat 数据）→ 复用 livemaker_extract 多脚本管线 | — |
| `ratw_unpack_vf.py` | RATW (LiveMaker) VF 解包：game.ext 目录 + game.dat 数据（offsets 相对 dat） | — |
| `rdf_extract.py` | [NS-JP]レンドフルール for Nintendo Switch 全文本提取（Otomate STCM2L / CPK） | `stcm2l` |
| `realrode_extract.py` | Real Rode ポータブル (PSP, HuneX「IKA SEQ SYSTEM v3.1」) 全文本提取 | `hunex-ika` |
| `rear_extract.py` | リアフェレス（Unity）TextAsset 场景脚本提取 → リアフェレス.txt | `naninovel` · `stcm2l` |
| `recall_extract.py` | [JP]Recall (KiriKiri / DropWave OTag 加扰 .ks) 全文本提取器 | — |
| `redbell_dialog.py` | レッドベルの慟哭 正文提取（成品生成） | `naninovel` · `stcm2l` |
| `redbell_extract.py` | レッドベルの慟哭 —— Naninovel Script(ScriptableObject) → 全文本 | — |
| `redbell_romfs.py` | レッドベルの慟哭 —— 压缩 NCA(LZ4 bucket-tree) → RomFS 直读 | — |
| `renderfont.py` | 把字库图集渲染成 PNG（逐码位预览，供人工目视确认字形） | — |
| `renpy_text.py` | Ren'Py .rpy 文本抽取器（通用） | — |
| `renri_extract.py` | [JP]比翼は愛薊の彼方へ ～連理の夢～ (PC 2008 / SandalDash) text extractor. | — |
| `requartz_extract.py` | Re;quartz After Love Story（Adobe AIR ＋ AIRNovel / anbooks「als」）全文本提取 | — |
| `requartz_kojitsudan_extract.py` | [JP]Re;quartz零度◆後日談ノベルゲーム 文本提取器 (NW.js + TyranoScript, .ks) | — |
| `requartz_main_text.py` | [JP]Re;quartz (PC / Adobe AIR, B-cluster engine) .an 剧本 -> 全文本（双版对照） | — |
| `requartz_pc_text.py` | Return list of boxes; each box is a list of [r]-segment strings. | `himauri` · `livemaker` · `stcm2l` … |
| `restart_extract.py` | REstart (吉里吉里 KAG3) 剧本文本提取 —— 双版对照（段行＋合并行） | — |
| `revepc_extract.py` | [PC-JP] DYNAMIC CHORD feat.[rēve parfait] Append Disc（honeybee black / ASGARD） | — |
| `revice_extract.py` | RE:VICE[D] (PSV, PCSG00382, Otomate / Idea Factory) 剧本文本提取 | `naninovel` · `stcm2l` |
| `rgssad_v1_extract.py` | — | — |
| `rhapsody_vfs.py` | VFS3 容器解包（日本一ソフトウェア / Rhapsody 系列，NS） | `vfs3-pak` |
| `rinrin_extract.py` | [PC-JP]凜々蝶さまのおっしゃる通り！（KiriKiri / data.xp3 / cp932 平文 KAG3）文本提取 | — |
| `rio_ll_extract.py` | Laughter Land (WillPlus / RIO bytecode) text extractor. | — |
| `rip9_extract.py` | [NS-JP]9 R.I.P. —— STCM2L(UTF-8) 文本提取 | `stcm2l` |
| `rip9seq_extract.py` | [NS-JP]9 R.I.P. sequel —— STCM2L(UTF-8) 文本提取 | `stcm2l` |
| `ripple_deep.py` | 递归解 HFU2（含嵌套），输出叶子 blob 并统计日文密度 | — |
| `ripple_extract.py` | リプルのたまご ～Apprentice magician～ (PS2, HuneX .ebf) 全文本提取 | — |
| `ripple_unpack.py` | リプルのたまご (PS2) HFU2 解包 + 目视 dump 用 | — |
| `rixcall_extract.py` | — | — |
| `rl_decomp.py` | — | `avg32` |
| `rl_parse.py` | — | `avg32` |
| `rom2_extract.py` | ROM2 archiver (Kalmia8 / 鳥籠のマリアージュ PSV). | `naninovel` · `nis-cpk-snbin` · `rom2` … |
| `rom2_list.py` | ROM2 目录列表 / 按名提取（不整文件入内存） | — |
| `roman_extract.py` | 召しませ浪漫茶房（SIMPLE2000 Vol.98 THE 浪漫茶房 / PS2-JP / SLPM_657.37）全文本提取 | — |
| `roman_tml.py` | 召しませ浪漫茶房 (PS2-JP / SLPM_657.37) —— TML 剧本解析（草案，供调参） | — |
| `roman_vl.py` | 召しませ浪漫茶房 (PS2 / SLPM_657.37) —— VSC 'vl_file' 库：vlLZSS 解压 + PAC(MemPack) 读取 | — |
| `romeo_extract.py` | QuinRose Qoo (PSV) —— ロミオVSジュリエット 剧本成行 | — |
| `rootrexx_extract.py` | ROOT∞REXX (PSV / PCSG00458 / Otomate×Idea Factory / 2015) 全文本提取 | `dat-pak-scd` · `naninovel` · `stcm2l` |
| `rosarium_extract.py` | — | — |
| `rpg999v19_extract.py` | 999,Victory ver1.9（RPGツクールVX Ace / RGSS3）文本提取 | — |
| `rpg999v_extract.py` | RPG Maker VX Ace (RGSS3) 文本提取 | — |
| `rq_extract.py` | Re;quartz零度 (NS) SCRIPT.PAK → 全文本（双版对照） | `himauri` · `livemaker` · `stcm2l` … |
| `rt2_extract.py` | ラディアンテイル ～ファンファーレ！～ (NS) STCM2L 文本提取 —— 2026-10-26 修正版 | `naninovel` · `stcm2l` |
| `run_alice.py` | Batch extract scenario text from the 6 Alice-series PSP ISOs. | `nis-cpk-snbin` |
| `rushup_extract.py` | — | — |
| `rxdata_scripts_dump.py` | RPG Maker XP/VX Scripts.rxdata 解压到 .rb（zlib 逐本解压） | — |
| `ry_extract.py` | ロイヤルズ～愛しの王子さま～ ＆ ～誘惑の王子さま～ (Tiaramode, BGI/Ethornell v1) | — |
| `sa7_extract.py` | SA7 - Silent Ability Seven - (PSV / PCSG00640 / プチレーヴ) 全文本提取器 | — |
| `saint_extract.py` | ［PS2-JP］セイント ビースト ~螺旋の章~ —— SN.BIN 剧本提取 | — |
| `saisys_ssb_text.py` | [JP]Dual Colors (PC / SaiSys / chiffon 2001) 正文提取 | `himauri` · `livemaker` · `stcm2l` … |
| `sanzen_extract.py` | 参千世界遊戯 ～Re Multi Universe Myself～ (PSV, PCSG01194, girls★dynamics / ACTGS「ROM2/SNR」) | `naninovel` · `stcm2l` |
| `sc2003_extract.py` | [JP]SILVER CHAOS（PC / VividColor GameSystem 2003）全文本抽取 | `vividcolor` · `yuuki-novel` |
| `sc7_extract.py` | [NS-JP]7'scarlet for Nintendo Switch 全文本提取（Otomate SScn 字节码） | `otomate-sscn` |
| `scan_jp.py` | 目录级扫描：找「连续假名 run 多」的文件并排序 —— 先圈候选，再细看 | — |
| `scan_nested.py` | 在归档的嵌套条目里扫日文，报 magic / 大小 / 样例 | — |
| `scan_quality.py` | — | — |
| `scandal_extract.py` | 偽りの君とスキャンダル（Switch / Nintendo Bezel Engine）剧本文本提取 | `bezel-bea` |
| `scanjp.py` | 单文件内定位连续假名 run（按偏移列出），用于确认哪一段是正文 | — |
| `scfb_extract.py` | [JP]Silver Chaos Fan Box -Eternal Fantasia- 文本抽取 | `vividcolor` · `yuuki-novel` |
| `schoolwars_extract.py` | スクール・ウォーズ ～全巻パック 本編＆卒業戦線～ (PSV, QuinRose / Courier "KS" engine) | — |
| `sco_vm_text.py` | Dolly Night / ドーリィナイト（パペット 2004）—— main.sco 文本提取 | `himauri` · `livemaker` · `stcm2l` … |
| `scratch_extract.py` | SCRATCH (undo/大樹愁 2006, KiriKiri2 KAG3) 剧本文本提取 —— 双版对照（段行＋合并行） | — |
| `seisyun_bin.py` | 《青春はじめました！》(PSP) cwin 脚本容器解析 | — |
| `seisyun_extract.py` | 《青春はじめました！》脚本 .bin → 一行一次点击的文本 | — |
| `seiyuu_extract.py` | [JP]Seiyuu Danshi! 文本抽取驱动（Ren'Py 7.2.2） | — |
| `senjyushi_extract.py` | 千銃士:Rhodoknight (NS) 解包 —— 压缩 NCA (LZ4 bucket-tree) → RomFS → 文件 | — |
| `senjyushi_extract_text.py` | 千銃士Rhodoknight (NS) —— SceneMasterVO.bin 全文本提取 | — |
| `sgk_extract.py` | 三国恋戦記～思いでがえし～＋学園恋戦記 (NS-JP) —— SCRIPT.PAK 全文本提取 | `selfpak-utf16-vm` |
| `sgs_heiho_extract.py` | 三国恋戦記～オトメの兵法！～ (NS-JP) —— SCRIPT.PAK 全文本提取 | `selfpak-utf16-vm` |
| `sgs_kai_ddp.py` | 三国恋戦記 魁 (Daisy2 / sgs_*.dat, DDP2/DDP3) 解包 + 解密 + 解压 | `daisy2-ddp` · `koei-embins-ps2` · `naninovel` … |
| `sgs_kai_extract.py` | 三国恋戦記 魁 —— 全文本提取（对话/选项/结局/教程） | `naninovel` · `stcm2l` |
| `shini_extract.py` | [NS-JP]死神と少女 (The Reaper And The Girl) text extract. | — |
| `shinjuku_text.py` | 新宿羅生門 ―Rashomon of Shinjuku― (Switch / Idea Factory・ALTERGEAR, 開発:花梨エンターテイメント) | — |
| `shinobi_ns_build.py` | 忍び、恋うつつ for Nintendo Switch —— 成品构建 | — |
| `shinobi_ns_extract.py` | 忍び、恋うつつ (NS) STCM2L 提取：一次点击 = 一行 | — |
| `shinoda_botan_extract.py` | 篠田新宿探偵事務所 唐獅子牡丹 (HolicWorks Disc Blue / 2018-10-26 / PC-JP) | `naninovel` · `stcm2l` |
| `sidez_nca.py` | Blackish House sideZ -Retour- (NS) : 压缩 NCA(BKTR bucket-tree + LZ4) → RomFS | — |
| `sidez_pc_extract.py` | [PC-JP] Blackish House ←sideZ（ASGARD AdvHD / .ws2 字节码）全文本提取 | — |
| `siesta_avg32.py` | Siesta ～すすき野原の夢物語～ 文本提取（AVG32 / AMEDEO） | `avg32` |
| `siglus_scene_extract.py` | SiglusEngine (罪ナル螺旋ノ檻 / Tsuminaru) Scene.pck text extractor. | `naninovel` · `stcm2l` |
| `silentmoon_closure.py` | — | — |
| `silentmoon_extract.py` | Silent Moon (Boys3) 正文提取：ACT_A..H.txt + 同名 .spt 记录 | — |
| `silentmoon_fpk.py` | SilentMoon FPK: u32 count, entries {u32 off, u32 size, char name[24]}, raw data. | — |
| `silentmoon_rle0.py` | Silent Moon (Boys3 engine) member codec: 24-byte RLE0 header + payload. | — |
| `sk_extract.py` | [NS-JP] Code：Realize ～白銀の奇跡～ for Nintendo Switch —— Utage（宴）剧本提取 | `unity` |
| `skipbeat_extract.py` | スキップ・ビート！(PS2, SLPM_551.70) シナリオ抽出 | — |
| `slg_system_sd.py` | SLG System 系（Unicorn-B 2005「Heartner Hearts!」）文本提取器 | `himauri` · `livemaker` · `stcm2l` … |
| `snowboundland_extract.py` | SNOW BOUND LAND (PSP, Otomate / Idea Factory 2013) 剧本文本提取 —— 自包含 | `naninovel` · `stcm2l` |
| `solomon_extract.py` | [PSP-JP] Solomon's Ring ～地の章～ (Plan Peace / InterOne, ULJM06200系) | — |
| `sorayume_extract.py` | ソラ*ユメ (NS-JP, TAKUYO, TitleID 0100e6a027760000) text extract. | — |
| `souten_audit.py` | Verify Souten output against source records and write sourced exceptions. | — |
| `souten_extract.py` | Extract 蒼天の彼方 (PC, System-NNN) from an installed game directory. | — |
| `souten_ungai_extract.py` | Extract the standalone Japanese 雲外蒼天 short story using System-NNN. | — |
| `souten_ungai_proof.py` | Record the installed Ungai executable's text handlers and read-only checks. | — |
| `spelldown_extract.py` | — | — |
| `split_adjacent_quotes.py` | 句中 」「 相邻的筛查／拆分工具（skill references/layout.md §「句中引号只作探针」的落地） | — |
| `springflower_extract.py` | [JP]Spring Flower (FUSYRO / KiriKiri2 KAG3) -> one line per on-screen message box. | — |
| `srxfd_extract.py` | スカーレッドライダーゼクス STARDUST LOVERS (PSP) | `pack-yox` |
| `srxrev_extract.py` | LukPlus ADV (SRX Rev / PSV) lua script -> text extraction. | — |
| `ss_psv_extract.py` | Starry☆Sky PSV（Summer/Autumn/Winter Stories, PCSG00916/917/918）剧本文本提取 | — |
| `ssl_extract.py` | [NS-JP]薄桜鬼SSL ～sweet school life～ 文本提取（STCM2L / Switch / UTF-8） | `stcm2l` |
| `sspm_extract.py` | Starry☆Sky ~Spring Memories~ (NS-JP, 0100a3d026610000) 全文本提取 | — |
| `sss_extract.py` | 七人の性奴隷 / Seven Sex Slaves（KiriKiri2 + KAG3）剧本 -> 全文本（双版） | — |
| `stampout_extract.py` | [JP]STAMP OUT（Monoceros 自研引擎，与 Spell Down 同族：STMD/STSL/GLNK） | — |
| `stc_extract.py` | [NS-JP]スタットコール 救命恋愛24時（Romance MD Always On Call）文本提取 | `naninovel` |
| `stcm2l_extract.py` | STCM2L 剧本文本提取器 —— 猛獣たちとお姫様 for Nintendo Switch | `naninovel` · `nis-cpk-snbin` · `stcm2l` |
| `steam2_extract.py` | スチームプリズン -Beyond the Steam- (NS) → 全文本 | — |
| `steam_extract.py` | スチームプリズン (NS, HuneX Ogre) allscr.mrg + script_text.mrg → 全文本 | — |
| `steam_rebuild.py` | スチームプリズン 按「文本表逐条 = 一次点击」重建（2026-10-26） | — |
| `steelwood_extract.py` | Steel Wood (原宿探偵学園 スチールウッド) DATA/BIN/M*.DAT 剧本提取 | — |
| `step_extract.py` | STEP: rlvm-derived parser/decompressor; current-game GAMEEXE evidence. | — |
| `step_inspect.py` | — | — |
| `step_prepare.py` | — | — |
| `step_query.py` | — | — |
| `stormlover2_charset.py` | STORM LOVER 2nd V (PSV PCSG00736) —— sc.cpk 自建字符集（二级自定义槽） | — |
| `stormlover2_run.py` | STORM LOVER 2nd V (PSV PCSG00736) —— 从 sc.cpk 产出全文本 | — |
| `stormlover_assets.py` | STORM LOVER V (PSV PCSG00735) —— 资源解压工具（2026-10-11） | — |
| `stormlover_charset.py` | STORM LOVER V (PSV PCSG00735) —— sc.cpk 自建字符集（最终版 2026-10-11） | — |
| `stormlover_extract.py` | STORM LOVER V (PSV PCSG00735) sc.cpk 正文提取（2026-10-11） | — |
| `stormlover_font.py` | STORM LOVER V (PCSG00735) 字形图集读取器 —— lt.bin | — |
| `stormlover_natsu_charset.py` | STORM LOVER 夏恋!!（PSP / ULJM-05858?）—— sc.cpk 自建字符集（2026-10-12） | — |
| `stormlover_natsu_run.py` | STORM LOVER 夏恋!!（PSP）—— 从 sc.cpk 产出全文本（2026-10-12） | — |
| `stormlover_psp_cmp.py` | STORM LOVER 夏恋!!（PSP）—— 二级槽「字形 vs 候选字」比对图（人工目视定值） | — |
| `stormlover_psp_font.py` | STORM LOVER 夏恋!!（PSP）—— lt.bin 自建位图字体渲染（2026-10-12） | — |
| `stormlover_run.py` | STORM LOVER V (PSV PCSG00735) —— 从 sc.cpk 产出全文本（2026-10-11） | — |
| `straw_extract.py` | 殺し屋とストロベリー Plus —— scenario01(UnityFS) 内 TextAsset → 全文本 | — |
| `strawberry_extract.py` | PS2『きまぐれストロベリーカフェ』EVT 字节码文本提取（v3） | — |
| `stride_extract.py` | 《[PSV-JP]プリンス・オブ・ストライド》 (PCSG00491) 资源解密 / 解包 / 文本探查工具 | `naninovel` · `stcm2l` |
| `stripper_extract.py` | — | — |
| `strobemania_run.py` | スト☆マニ ～Strobe☆Mania～（PSP / ULJM-05961）—— 全文本提取 | — |
| `struct_probe.py` | 引号/括号结构探针：把「一行里塞了几个框」量化 | `bezel-bea` · `selfpak-utf16-vm` · `stcm2l` … |
| `subordinate2ldk_extract.py` | 上司と秘密の2LDK（Switch / Bezel Engine「SCNE + scb_」）剧本正文提取 | `bezel-bea` |
| `sugar_audit_all.py` | [JP]Sugar —— 全 .lsb 普查（交付前「查看所有文件」核验） | `himauri` · `livemaker` · `stcm2l` … |
| `sugar_build.py` | PAC 0x0425 文本流 → 一次点击一行 | — |
| `sugar_extract.py` | PS2 シュガシュガルーン 恋もおしゃれもピックアップ！ | — |
| `sumire_extract.py` | [PC-JP]すみれの蕾（PC / MADOKA GScript・GSCE 编译剧本）全文本提取 v2 | — |
| `swallows_extract.py` | My9Swallows TOPSTARS LEAGUE —— Unity + 纯文本脚本（与 Honey Vibes 同引擎） | — |
| `sweet19_extract.py` | [JP]Sweet 19 Pain —— ComicPly (ICM95 / CmdVer=14) 全文本提取 | — |
| `sweetclown_extract.py` | [NS-JP]SWEET CLOWN ~午前三時のオカシな道化師~ text extract (Takuyo gss / SCR 3.00). | — |
| `swf_definetext_text.py` | Macromedia Flash / Shockwave（SWF）→ 「一次点击 = 一行」 | `overflow-adv` |
| `switch_nca.py` | Switch NCA 解密器（不依赖 hactool）—— 处理 Titlekey crypto / Standard crypto 的 Program NCA | — |
| `symp_trace.py` | SympathyKiss STCM2L 单段 opcode 追踪（看「同句两版 / 掩码 ＃＃＃ / 断行」在代码层长什么样） | — |
| `sympathy_extract.py` | SympathyKiss (NS) STCM2L 文本提取 | — |
| `sympathy_namescan.py` | 统计正文里的 #Name 宏与候选默认名 | — |
| `system_nnn.py` | Read System-NNN SPT using its header tables and length-prefixed commands. | — |
| `taf_extract.py` | [JP]Truth and False —— KiriKiri/KAG3 专用提取驱动 | — |
| `taisho_ht_extract.py` | 大正×対称アリス HEADS & TAILS（NS）→ 全文本 | `selfpak-utf16-vm` |
| `taisho_pak_extract.py` | 大正×対称アリス all in one（NS）→ 全文本 | `selfpak-utf16-vm` |
| `takahiro_extract.py` | takahiro_com（TyranoScript / NW.js）文本提取 | — |
| `tameboy_extract.py` | [JP]TameBoy（「シナリオくん」1.9x ／ .st1）全文本提取驱动 | — |
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
| `termdict_extract.py` | 用語辞典（termItem.dat）→ 【見出し語】解説文 一行一条，并入成品末尾 | `nis-cpk-snbin` |
| `test_decode.py` | — | — |
| `test_workflow.py` | Regression fixtures for source layout checks and task-scoped wrapup. | — |
| `tether_text.py` | [JP]Tether（KiriKiri / TVP(KiriKiri) KAG3）全文本提取 | — |
| `textbox_stats.py` | 统计用 —— 分作行数 + 文本框封口 op 分布（L0 判据的证据） | — |
| `thc_build.py` | 合成最终交付文本（一次点击 = 一行） | — |
| `thc_extract.py` | とらぶるふぉうちゅんCOMPANY★はぴCURE (PS2, Primavera/Interchannel "nlib") 文本提取 | — |
| `thc_text.py` | 从 thc_extract.py 解出的成员文件中抽取正文（一框一点击） | — |
| `tiabureido_extract.py` | 悠久のティアブレイド for Nintendo Switch —— STCM2L 全文本提取（一次点击＝一行） | — |
| `tik_key.py` | 由 ticket 推 NCA 内容密钥（Titlekey crypto），并用 section 0 的 PFS0/IVFC 魔数自证 | — |
| `timeflies_extract.py` | [JP]Time Flies — KiriKiri KAG3 全文本提取（双版对照） | — |
| `tiny_machinegun_extract.py` | Tiny×MACHINEGUN THE GAME (Rejet / PC-JP) 剧本・辞典文本提取器 —— 端到端定稿 | `naninovel` · `stcm2l` |
| `tlz_liam_text.py` | Takuyo「LIAM」引擎（Fragrance Tale PC 2001）→ 一台本一台词框的正文 | `himauri` · `livemaker` · `stcm2l` … |
| `tmr_srp.py` | TMR-Hiro ADV System .srp → 全文本（PC / クレイジー★ラビッツ 実測） | `himauri` · `livemaker` · `stcm2l` … |
| `tmrpac.py` | TMR-Hiro ADV System 系 .pac 容器解包（PC / クレイジー★ラビッツ 実測） | `himauri` · `livemaker` · `stcm2l` … |
| `toiro_extract.py` | raw NUL-terminated UTF-8 jp strings inside a push operand. | — |
| `toiro_extract2.py` | raw NUL-terminated UTF-8 jp strings inside a push operand (catches custom-format inline strings) | — |
| `tokihako_extract.py` | 時函 -Time Capsule- (Ray, 2009 / PC / NScripter) 全文本提取 | `naninovel` · `stcm2l` |
| `tokimemo_gs1_extract.py` | ときめきメモリアル Girl's Side 1st Love (NS-JP, Unity) 全文本提取器 | — |
| `tokimemo_gs2_extract.py` | ときめきメモリアル Girl's Side 2nd Season (NS-JP, Unity) 全文本提取器 | — |
| `tokimemo_gs3_extract.py` | ときめきメモリアル Girl's Side 3rd Story for Nintendo Switch (NS-JP, Unity) 全文本提取器 | — |
| `tokimemo_gs4_extract.py` | ときめきメモリアル Girl's Side 4th Heart for Nintendo Switch (NS-JP, Unity) 全文本提取器 | — |
| `tokires_extract.py` | ときめきレストラン☆☆☆ Project TRISTARS (PSV / PCSG01171, KONAMI) 全文本提取 v2 | — |
| `tokitama_extract.py` | ときたま！～時函玉手箱～ (Ray, 2010 / PC / NScripter) 全文本提取 | `naninovel` · `stcm2l` |
| `torimari_extract.py` | 鳥籠のマリアージュ ～初恋の翼～ (PSV, PCSG90230, Kalmia8 / ACTGS engine) | `naninovel` · `stcm2l` |
| `touch_text.py` | [JP]ToucH もう一度この手が触れる世界（TVP/KiriKiri ＋ KAG3/KAGEX）全文本提取 | — |
| `towa_build.py` | 悠久ノ桜（Towa no Sakura / PS2-JP）全文本生成 | — |
| `towa_dis.py` | 悠久ノ桜 SLPM_668.45 最小反汇编：ELF32 MIPS(LE) → .text 反汇编落盘 + 立即数索引 | — |
| `towa_extract.py` | 悠遠ノ桜 (Towa no Sakura / PS2-JP) LSB 解析 —— VSC VDP + LSB 族 | — |
| `trois_text.py` | アンジェリーク トロワ (PS2, SLPM_620.22, 2000 Koei/Ruby Party) 正文＋选项提取 | `koei-embins-ps2` |
| `tsukikage_extract.py` | 月影の鎖 -錯乱パラノイア- (NS-JP) text extract ---- TAKUYO gss / SCR 2.00. | — |
| `tsundere_extract.py` | ツンデレ★Ｓ乙女 (PC / 美蕾「Madoka GScript」) 全文本提取器 —— 本项目定稿 | `naninovel` · `stcm2l` |
| `tyb_fd_extract.py` | TOKYOヤマノテBOYS for V FAN DISC（PSV / PCSG01049）全文本提取 | — |
| `udf.py` | 极简 UDF 只读解析（PS2 桥接盘用）：列目录 / 抽取文件 | — |
| `uf_render.py` | 恋愛番長2 font/0（UF_ 自研字体）字形渲染/探查工具 | — |
| `ukronia_bktr.py` | ：BKTR 段（enc=3）解密试验 | — |
| `ukronia_check.py` | ：闭合校验（[next storage] 目标是否都在、排除清单、块/页/选项计数） | — |
| `ukronia_cls.py` | ：剧本文件分类表（每文件正文行数 + 首行样本） | — |
| `ukronia_extract.py` | 泡沫のユークロニア 剧本成行器（TIS 风格 [命令] 脚本） | `naninovel` · `stcm2l` |
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
| `uma_boxes.py` | 冬園サクリフィス UTXT 文本流 -> 文本框（按代码级结构切分） | `unity` |
| `uma_dec.py` | yield (byteoffset, char_or_special) | `unity` |
| `uma_extract_final.py` | 冬園サクリフィス [NS-JP] UTXT 文本提取（代码级切分：仅用 0x00 换行码，无括号启发式） | `unity` |
| `uma_extract_v4.py` | 冬園サクリフィス [NS-JP] UTXT 文本提取（v4） | — |
| `uma_extract_v5.py` | 冬園サクリフィス [NS-JP] 文本提取 v5（引擎行复现） | `unity` |
| `uma_extract_v6.py` | 冬園サクリフィス [NS-JP] 文本提取 v6（按角色号/台词边界分行） | `unity` |
| `uma_rowfit.py` | 按 TT_NewCezanne-DB 的真实 advance 复现引擎折行 | `unity` |
| `uma_text_extract.py` | 冬園サクリフィス (NS-JP) 全文本提取 | — |
| `uma_vm_probe.py` | uma_script_2.bytes 结构探针：找「固定步长上的递增 u16/u32」= 文本单位序号序列 | — |
| `uma_wrap.py` | 推定引擎显示换行：0x00 强制断行 + 定宽自动折行（禁则处理）， | `unity` |
| `unbs_extract.py` | Un:BIRTHDAY SONG～愛を唄う死神～another record（PSV PCSG00912）剧本提取（本作专用） | — |
| `underblue_extract.py` | [JP]アンダーブルー2012 — KiriKiri XP3 ＋ KAG3 全文本提取（双版对照） | — |
| `unending_extract.py` | Extract only SPT script text from unENDing Bloody Call (PSP-JP). | — |
| `unity_list.py` | 列出 Unity AssetBundle / .assets 内的对象（type + name/path_id），不 dump 内容 | — |
| `unity_scriptdatas_text.py` | Friendly lab - unlock();（Tennenouji / Unity 2021）→ 一台本一台词框的正文 | `naninovel` · `stcm2l` · `unity` |
| `unity_textasset_dump.py` | Unity resources.assets → 全 TextAsset 落盘（旁车 / managed text 导出） | — |
| `upd_merge.py` | 通用「NS 官方更新（BKTR 差分）＋ 本体 NCA」→ 最新 romfs 文件 合并器 | — |
| `ura_ptd_jrs.py` | Uragiri wa Boku no Namae o Shitteiru (PS2, Design Factory / Otomate 2010) | — |
| `urakata_extract.py` | 裏語 薄桜鬼 (PSP ULJM06281) 剧本提取器 —— LZO1X 解压版 | — |
| `ururun_build.py` | うるるんクエスト 恋遊記 全文本生成：VML -> 提取结果/*.txt | — |
| `ururun_vml.py` | うるるんクエスト 恋遊記 (PS2-JP / D3PUBLISHER, SLPM_660.28) | — |
| `utage_book_lines.py` | ワンド オブ フォーチュン Ｒ２ ～時空に沈む黙示録～（Switch / Unity + Utage）剧本提取 | — |
| `utage_extract.py` | ハンサムロンダリング -the mystic lover- (NS / Unity + Utage) 剧本文本提取 | — |
| `utapri_aa_check.py` | 交付前自检 —— **本作专用副本**（うたの☆プリンスさまっ♪ Amazing Aria & Sweet Serenade LOVE） | — |
| `utapri_aa_extract.py` | うたの☆プリンスさまっ♪ Amazing Aria & Sweet Serenade LOVE (NS 0100D4300EBF8000) | — |
| `utapri_aa_lzss.py` | うたの☆プリンスさまっ♪ Debut (NS 010088200EFE8000) 剧本提取（本作专用，勿与他作共用） | — |
| `utapri_as_extract.py` | うたの☆プリンスさまっ♪ All Star (NS 0100B3E0149FC000) 剧本提取 | — |
| `utapri_debut_check.py` | 交付前自检（品检）—— 日文游戏剧本文本提取产物的通用检查器 | — |
| `utapri_debut_extract.py` | うたの☆プリンスさまっ♪ Debut (NS 010088200EFE8000) 剧本提取（本作专用，勿与他作共用） | — |
| `utapri_extract.py` | うたの☆プリンスさまっ♪ All Star After Secret (NS/01008030149FE000) 剧本提取 | — |
| `utapri_rl_extract.py` | うたの☆プリンスさまっ♪ Repeat LOVE（PSV / PCSG00914）全文本提取 | — |
| `utapri_rl_ns_extract.py` | うたの☆プリンスさまっ♪ Repeat LOVE (NS 010024200E00A000) 剧本提取 | `nis-cpk-snbin` |
| `utsusemi_extract.py` | 空蝉の廻 (NS-JP) 文本提取 | — |
| `valpurga_extract.py` | [PSV-JP]ヴァルプルガの詩 (PCSG00768) 全文本提取 | `naninovel` · `stcm2l` |
| `vamwolf_lt.py` | Vamwolf Cross† lt.bin 字形图集渲染 | — |
| `vamwolf_run.py` | Vamwolf Cross† (PSV PCSG00467, D3P 系) —— sc.cpk → 全文本 | — |
| `vc_extract.py` | DIABOLIK LOVERS VANDEAD CARNIVAL (PSV, PCSG00472) 文本提取 | `dat-pak-scd` |
| `vdp.py` | VSC VDP 容器解析（ラスト・エスコート2 ～深夜の甘い棘～ / PS2-JP） | `vsc-vdp-lsb` |
| `verify_descramble.py` | — | — |
| `verite_extract.py` | 《薔薇に隠されしヴェリテ》 (PS Vita / PCSG00708 / Unity 5.3.5p5) 全文本提取 | `nis-cpk-snbin` |
| `virche_extract.py` | 終遠のヴィルシュ -ErroRsalvation- (NS) STCM2L 文本提取 | `naninovel` · `stcm2l` |
| `virche_xci.py` | 重打包 XCI（封装头不自洽）→ 抽 NCA，带「数据起点自证」 | `naninovel` · `stcm2l` |
| `vista_extract.py` | [JP]ViSTA+1.20 全文本提取 (KiriKiri / KAG3, 明文 cp932, 无 OTag 加扰) | `kirikiri` |
| `visukio_extract.py` | [JP]VISUKIO（Yuuki! Novel 旧版 PackageFile2 ／ .yne）文本提取驱动 | — |
| `vitaminb6_extract.py` | VitaminX DetectiveB6 (PSP, HuneX「IKA SEQ SYSTEM v4.1 HuneX 2010」) 全文本提取 | `hunex-ika` |
| `vitaminr_extract.py` | VitaminR (PSP, ULJS00592, 2013-08-08, D3P/Rejet) 全文本提取 | `pack-yox` |
| `vitaminx_ep_extract.py` | ビタミンX Evolution Plus（PSP, ULJS00325, HuneX「IKA SEQ SYSTEM v4.1」）全文本提取 | `hunex-ika` |
| `vitaminxz_extract.py` | Vitamin X to Z (PSP, ULJS00347, HuneX「IKA SEQ SYSTEM v4.1」) 全文本提取 | `hunex-ika` |
| `vitz_extract.py` | VitaminZ (PSP, ULJS00240, HuneX「IKA SEQ SYSTEM v3.4 HuneX 2009」) 全文本提取 | `hunex-ika` |
| `vn_memdump.py` | 从运行中的进程按内存区段 dump（Windows，ReadProcessMemory） | — |
| `vn_zerodiv_extract.py` | 裏語 薄桜鬼 / ～暁の調べ～ (PSP ULJM06281 / ULJM06373) 剧本提取器 —— 定稿版 | `naninovel` · `stcm2l` |
| `voice_bq_text.py` | [JP]Voice -Be Quite in the Dark-（TVP/KiriKiri 2.24 ＋ KAG3）全文本提取 | — |
| `voice_extract.py` | [JP]Voice（TVP/KiriKiri 2.24 ＋ KAG3 ／ data.xp3）全文本提取 | — |
| `voice_guy_extract.py` | — | — |
| `vridge_cs_customdrive.py` | カスタムドライブ（PSP / ULJM-06058）—— 二级区定值表 | — |
| `vridge_cs_hatsukare.py` | はつカレっ☆恋愛デビュー宣言!（PSP / ULJM-06199）—— 二级区定值表 | — |
| `vridge_psp_run.py` | Vridge/D3P 系 PSP 作品（sc.cpk + lt.bin 自建字符集）通用提取器 | — |
| `vxdst_extract.py` | VitaminX Destination (PSV-JP, PCSG01115) —— HuneX 'HESL / HESE' 剧本文本提取器 | `hunex-hesl` |
| `vzgrad_extract.py` | VitaminZ Graduation (PSP, ULJS00xxx v1.01, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取 | `hunex-ika` |
| `wgs_enc.py` | 冬園 UTXT：验证 script 里是否含正文（用已知文本反向编码去搜） | — |
| `will_rio_arc.py` | WillPlus / RIO.ARC（WSC 脚本）文本提取 | `himauri` · `livemaker` · `stcm2l` … |
| `willowisp_extract.py` | ウィル・オ・ウィスプ ポータブル (PSP, ULJM05447, Design Factory & Otomate / Idea Factory) 剧本文本提取 | — |
| `win_memdump.py` | Windows 进程内存导出（只读，用于从运行中的游戏抓明文） | — |
| `wings_extract.py` | — | — |
| `winscan.py` | Windows 进程内存扫描器：定位指定进程里 cp932 日文正文最密集的区域并导出 | — |
| `woga_datunpack.py` | Tennenouji / woga AIR .dat 解包器 | — |
| `xci_hfs0.py` | XCI (HFS0) 手工解析/抽 NCA —— 专治重打包 XCI 的「封装头不自洽」 | `nis-cpk-snbin` · `stcm2l` |
| `xci_romfs.py` | XCI -> (内存中)NCA -> RomFS 单文件抽取（不落 NCA/整 romfs，省磁盘） | `stcm2l` |
| `xp3.py` | 蝶の毒 華の鎖 XP3 索引列挙 + ファイル抽出 (KiriKiri XP3) | `kirikiri` · `nis-cpk-snbin` |
| `xp3dec_index.py` | XP3 索引解析（通用）：Kirikiri XP3 的 File/info/segm/adlr 块逐个消费，导出 JSON + 成员名清单 | — |
| `xp3dec_inproc.py` | XP3 逐文件加密的通用解法：在真实游戏进程内 in-process 调用注册的 filter 回调 | — |
| `yamanote_extract.py` | TOKYOヤマノテBOYS for V MAIN DISC（PSV / PCSG01048）全文本提取 | — |
| `yamiiro_extract.py` | 闇色の魔珠 (Daisy2 / PROTOTYPE NS) SCRIPT.PAK → 全文本（双版对照） | — |
| `yaoi_base.py` | 宵闇 本体正文重建（源＝eden dump 的 merged romfs，即 v1.1.1 实际显示文本） | — |
| `yourmo_extract.py` | ユア・メモリーズオフ～Girl's Style～ (PSP-JP, ULJM05435, MAGES. 2008) | — |
| `yuris_allout_extract.py` | YU-RIS / ERIS 剧本正文提取：[JP]ALL OUT | `naninovel` · `stcm2l` |
| `yuris_ypf.py` | YU-RIS YPF 归档提取（归档可内嵌在 exe 尾部，也可为独立 .ypf） | `naninovel` · `stcm2l` |
| `yuris_ystb.py` | YU-RIS YSTB 脚本解析：解开 XOR 段并反汇编成 cmd + 参数 | `naninovel` · `stcm2l` |
| `yuuki_pkg.py` | Yuuki! Novel (ゆうき！ノベル) 引擎 —— 容器 PackageFile20 解析 + 文件解密 | `vividcolor` · `yuuki-novel` |
| `yuuki_yne.py` | Yuuki! Novel (ゆうき！ノベル) 引擎 —— .yne WorkFile 解析（脚本读取） | — |
| `zettaikyuu_extract.py` | 絶対階級学園 ~Eden with roses and phantasm~ (NS) → 提取结果 txt | — |
| `zettaikyuu_nsplist.py` | 列 NSP 内 PFS0 条目（名 / 偏移 / 大小），顺带提示 ticket 的 keygen 与 cert 尺寸 | — |
| `zettaikyuu_romfs.py` | 絶対階級学園 —— 从 prog.nca 流式取 romfs 指定文件（不落 6GB 副本） | — |
| `zokuwanai_extract.py` | 罪喰い ~千の呪い、千の祈り~ for V (PSV / PCSG01019 / HuneX, dramatic create 2017) 全文本提取器 | — |
| `zokuwanai_unpack.py` | 罪喰い for V (PCSG01019, HuneX Ogre) allscr.mrg 解包 + MZX0 解压 | — |
