# 引擎 → 可复用脚本

> **自动生成**（`gen_script_index.py`，每次构建重建）—— 不要手改。
>
> 用法：`references/00-triage.md` 命中引擎 → 打开 `references/engines/<slug>.md`
> 看容器链路与记录形状 → 回到本表挑**最近似**的脚本 → **只改路径 / 键 / 参数**。
> 通用工具（判型 / 探查 / 品检 / 收尾）见 `INDEX.md`，本表不重复。

## 一、按引擎（命中后从这一行开始）

| 引擎册 | 引擎 | 可直接改的脚本 |
|---|---|---|
| `3daisy-scrvita.md` | 3Daisy 自研 | `valpurga_extract.py` |
| `aromarie-atl.md` | Aromarie 自研「ATL」引擎 | `moon_atl_extract.py` |
| `asgard-tat.md` | ASGARD 自研「TAT」文本脚本 | `prince5_extract.py` |
| `cri-cpk-afs.md` | CRI | `cpk.py` · `cpk_v1.py` · `hanayoi_afs.py` · `hanayoi_extract.py` · `hanayoi_run.py` · `izasen_cpk.py` · `izasen_extract2.py` · `izasen_stream.py` |
| `gakuenk-dat-scr.md` | Otomate / Idea Factory 自研「DAT + PAK + SCD」 | `gakuenk_extract.py` · `neoangelique_extract.py` |
| `hunex-hesl.md` | HuneX「HESL / UNAS」系 | `believer_extract.py` |
| `hunex-ika-seq.md` | HuneX · IKA SEQ SYSTEM | `arcanafam2_run.py` · `arcanafesta_extract.py` · `arcanafesta_run.py` · `arcanayurei_run.py` · `realrode_extract.py` |
| `hunex-ika-seq-arcana2.md` | HuneX IKA SEQ —— 压缩变体·第 4 作：アルカナ・ファミリア2 | `arcanafam2_run.py` |
| `hunex-ika-seq-arcanafamiglia.md` | HuneX IKA SEQ —— 压缩变体：アルカナ・ファミリア | `arcanafesta_extract.py` · `arcanafesta_run.py` |
| `hunex-ika-seq-b6.md` | HuneX IKA SEQ —— 第 7 作：VitaminX DetectiveB6 | `vitaminb6_extract.py` |
| `hunex-ika-seq-lucian.md` | HuneX IKA SEQ —— 第 5 作：Lucian Bee's… | `lucian_extract.py` |
| `hunex-ika-seq-vitaminxz.md` | HuneX IKA SEQ —— 第 6 作：Vitamin X to Z | `vitaminxz_extract.py` |
| `hunex-ika-seq-vitaminz.md` | HuneX IKA SEQ —— 第 9 作：VitaminZ | `vitz_extract.py` |
| `hunex-ika-seq-vzgrad.md` | HuneX IKA SEQ —— 第 8 作：VitaminZ Graduation | `vzgrad_extract.py` |
| `hunex-ogre.md` | HuneX「Ogre」系 | `majikyun_extract.py` |
| `hunex-ogre-dramaticcreate.md` | HuneX「Ogre」系 · dramatic create 移植三作 | `akasuna_extract.py` · `enkan_extract.py` · `zokuwanai_extract.py` · `zokuwanai_unpack.py` |
| `hunex-ogre-loverevo.md` | HuneX「Ogre」系 · PSP 变体 —— 乙女的恋革命★ラブレボ!!… | `loverevo_extract.py` |
| `hunex-ogre-ozmafia.md` | HuneX「Ogre」系 · OZMAFIA!! -vivace | `ozmafia_extract.py` · `ozmafia_nca.py` |
| `idea-factory-stcm2l.md` | STCM2L | `norn9_extract.py` · `pandora_dbg.py` · `pandora_extract.py` · `revice_extract.py` · `stcm2l_extract.py` |
| `idea-factory-stcm2l-ps2-uni2.md` | STCM2L · CRI「UNI2」容器 —— PS2/PSP 样本 | `l2ll_extract.py` |
| `idea-factory-stcm2l-psp-cpk.md` | STCM2L · PSP「CRI CPK」侧 | `cpk.py` · `jewelic_extract.py` · `minus8_extract.py` · `snowboundland_extract.py` |
| `idea-factory-stcm2l-psp-cpk-amen-garnet.md` | STCM2L · PSP「CRI CPK」· アーメン・ノワール ポータブル ＋… | `amennoir_extract.py` · `cpk.py` · `cpk_v1.py` · `garnet_extract.py` |
| `idea-factory-stcm2l-psp-uni2.md` | STCM2 · CRI「UNI2」容器 —— PSP 样本 | `arcobaleno_extract.py` · `dcgs_extract.py` |
| `idea-factory-stcm2l-psp-uni2-willow.md` | STCM2 · CRI「UNI2」· PSP · ウィル・オ・ウィスプ ポータブル | `willowisp_extract.py` |
| `idea-factory-stcm2l-psv.md` | STCM2L —— PSV 侧 · **UTF-8 系** | `cpk.py` · `marginal4rtg_extract.py` · `norn9_extract.py` · `psycemo6_extract.py` |
| `idea-factory-stcm2l-psv-cp932.md` | STCM2L —— PSV 侧 · **CP932 系** | `cpk.py` · `marginal4_extract.py` · `revice_extract.py` · `rootrexx_extract.py` |
| `idea-factory-stcm2l-psv-g.md` | STCM2L —— PSV 侧 · **变体 G** | `cpk.py` · `hakuoki_zuisouroku_extract.py` |
| `idea-factory-stcm2l-switch.md` | STCM2L · Switch 侧 | `bwolves_extract.py` · `niladmirari_extract.py` · `stcm2l_extract.py` |
| `idea-factory-stcm2l-switch-ghp.md` | STCM2L · Switch 侧 第 3 例 —— Glass Heart… | `crazychain_xci.py` · `ghp_extract.py` |
| `karin-adv-asb.md` | 花梨エンターテイメント 自研 ADV | `shinjuku_text.py` |
| `kirikiri-xp3.md` | KiriKiri XP3 | `chou_decrypt.py` · `chou_extract.py` · `chou_fix.py` · `crimson_royale_extract.py` · `gensou_decode.py` · `gensou_extract.py` · `gensou_scan.py` · `xp3.py` |
| `koei-cdar.md` | Koei CDAR v2/v4 | `geten_extract.py` · `haruka5_extract.py` · `kazahanaki_extract.py` · `neoange_psp_extract.py` |
| `koei-pasc.md` | Koei Tecmo / Ruby Party 自研「pasc」节点流 | `angelique_extract.py` |
| `konami-unity-bytes.md` | KONAMI 自研 Unity ADV—— ときめきメモリアル Girl's Side… | `tokimemo_gs2_extract.py` |
| `konami-unity-bytes-works.md` | KONAMI 自研 Unity ADV—— 逐作差异 | `crazychain_xci.py` · `nsp_split.py` · `tokimemo_gs1_extract.py` · `tokimemo_gs3_extract.py` · `tokimemo_gs4_extract.py` |
| `lastescort-paf.md` | NK/PAF ＋ PSCB | `lastescort_extract.py` |
| `lovepeace-adv.md` | 引擎：BROCCOLI / Sanctuary・EMIQ `ADV` | `lovepeace_extract.py` |
| `lte.md` | LTE 引擎 | `psarc_extract.py` · `us_walk.py` · `yamanote_extract.py` |
| `m2-advengine-psb.md` | M2「ADVENGINE」— PSP/PSV/NS 通用 | `btf_carve.py` · `btf_extract.py` · `btf_mdf.py` · `btf_pgd.py` |
| `mages-afs-yourmo.md` | MAGES.PSP 自研 —— CRI AFS ＋ NUL 分段文本池 | `yourmo_extract.py` |
| `mages-sc3-mpk.md` | MAGES. 自家引擎 —— MPK 容器 ＋ SC3 脚本 | `manimani_extract.py` |
| `malie.md` | Malie System | `libp_malievita.py` · `malie_extract.py` · `mysteria_extract.py` · `mysteria_text.py` |
| `matatabi-unity-textadv.md` | Matatabi 自研「纯文本 @命令 ADV」 | `kannagi_extract.py` · `unity_list.py` · `unity_textasset_dump.py` |
| `meiji-haikara-lzs.md` | 自研 `.lzs` ＋ SCD コマンド列 | `meiji_extract.py` · `meiji_lzs.py` |
| `misc-engines.md` | 其它自研/小众引擎 | `artemis_pfs_extract.py` · `asakiyumemishi_extract.py` · `asakiyumemishi_psp_extract.py` · `brothers_kiss_extract.py` · `koigig_extract.py` · `nsac.py` · `ouma_build_text.py` · `ouma_extract.py` · `ouma_story.py` · `paradigm_paradox_extract.py` · `tiny_machinegun_extract.py` · `tokihako_extract.py` · `tokitama_extract.py` |
| `musketeer-psp-evb.md` | 引擎：5pb/otome 自研 `.evb` ＋ `MARC` ＋ `CPK` | `cpk.py` · `marc_font.py` · `musketeer_charset.py` · `musketeer_extract.py` |
| `mz-cmdstream.md` | MZ 命令流 | `cpk.py` · `makumatsu_extract.py` |
| `naninovel-unity.md` | Unity＋ Naninovel—— 剧本文本提取 | `naninovel_assemble.py` · `naninovel_extract.py` · `ozmafia_nca.py` · `unity_textasset_dump.py` |
| `nitroplus.md` | Nitroplus NPA / NSS | `lamento_extract.py` · `npa_nrbf.py` |
| `oni-psp-tob.md` | Idea Factory/Otomate 自研 PSP「oni」引擎 | `oga_sts_extract.py` |
| `orfre-dcvm.md` | 引擎：dramatic create 自研「Orfre」/ DCVM | `orfleur_extract.py` · `orfleur_stbl_extract.py` |
| `orfre-dcvm-history.md` | orfre-dcvm 探查史—— 仅排障时读 | `orfleur_trace.py` · `orfleur_vm.py` · `pc_snr_order.py` |
| `otomate-evb-marc.md` | 引擎：Otomate 自研 `.evb` ＋ MARC | `cfm_extract.py` · `iso_cut_cpk.py` · `musketeer_charset.py` |
| `otomate-vm.md` | Otomate VM | —（无现成脚本：按本册的容器链路 / 记录形状自己写） |
| `planpeace-pct.md` | Plan Peace / InterOne 自研「PCT」——`data.dat` ＋… | `solomon_extract.py` |
| `prince-stride-d3p.md` | 引擎：D3P 系「CRI CPK ＋ 自建字符集/位图字体」· 他作 —— プリンス… | `prince_stride_lt.py` · `prince_stride_run.py` · `stormlover_charset.py` · `vamwolf_lt.py` · `vamwolf_run.py` |
| `psv-pfs.md` | PSV NoNpDrm / PFS | —（无现成脚本：按本册的容器链路 / 记录形状自己写） |
| `rom2-snr.md` | ROM2 / SNR | `rom2_extract.py` · `sanzen_extract.py` · `torimari_extract.py` |
| `siglus.md` | SiglusEngine | `siglus_scene_extract.py` |
| `stormlover-d3p.md` | 引擎：D3P 自研 ADV— STORM LOVER 系列 | `stormlover2_charset.py` · `stormlover2_run.py` · `stormlover_assets.py` · `stormlover_charset.py` · `stormlover_font.py` · `stormlover_run.py` |
| `stormlover-d3p-psp.md` | 引擎：D3P 自建 ADV · **PSP 变体** | `stormlover_natsu_charset.py` · `stormlover_natsu_run.py` · `stormlover_psp_cmp.py` · `stormlover_psp_font.py` |
| `switch-nca.md` | Switch XCI / NCA / NSP | `ozmafia_nca.py` · `senjyushi_extract.py` · `switch_nca.py` |
| `system-nnn.md` | System-NNN—— あさき、ゆめみし 系列 | `asakiyumemishi_extract.py` · `asakiyumemishi_psp_extract.py` · `cpk.py` |
| `takuyo-gss.md` | Takuyo gss | `cafe_extract.py` · `himehibi_crawl.py` · `himehibi_disasm.py` · `himehibi_extract.py` · `himehibi_lsdarc.py` |
| `takuyo-gss-psp.md` | Takuyo gss · PSP 变体 | `etude_extract.py` · `himehibi_disasm.py` · `himehibi_lsdarc.py` |
| `takuyo-gss-psp-hoshiiro.md` | Takuyo gss · PSP 变体 3 | `gss_lsdarc.py` · `himehibi_disasm.py` · `hoshiiro_extract.py` |
| `takuyo-gss-psp-littleaid.md` | Takuyo gss · PSP 变体 2 | `gss_lsdarc.py` · `himehibi_disasm.py` · `littleaid_extract.py` |
| `takuyo-gss-psp-symphony.md` | Takuyo gss · PSP 变体 4 | `fsymph_extract.py` · `gss_lsdarc.py` · `himehibi_disasm.py` |
| `takuyo-gss-switch.md` | Takuyo gss —— Switch 变体 | `gss_codec.py` · `gss_lsdarc.py` · `gss_scr3.py` · `kamikoi_extract.py` |
| `takuyo-gss-switch-scr2.md` | Takuyo gss —— Switch 变体 · `SCR 2.00` | `crazychain_xci.py` · `gss_lsdarc.py` · `himehibi_disasm.py` · `himehibi_lsdarc.py` · `kaeru_extract.py` · `sorayume_extract.py` |
| `text-mode-adv.md` | 自研「テキスト方式 ADV」 | `baccan_extract.py` · `psarc_extract.py` |
| `thfs-mizu.md` | KID 自研 `THFS` 归档 ＋ `%` 控制码脚本 | `mizu2_extract.py` · `mizu_extract.py` |
| `unity-adv.md` | Unity + 自研 ADV | `akuyaku_extract.py` · `heiligenstadt_extract.py` · `psarc_extract.py` · `senjyushi_extract.py` · `senjyushi_extract_text.py` · `switch_nca.py` · `verite_extract.py` |
| `unity-adv-hscript.md` | Unity  + 自研 ADV · **纯文本脚本变体** | `crazychain_extract.py` · `crazychain_xci.py` |
| `willplus-advhd.md` | WillPlus / AdvHD | `advhd.py` · `bgloss_extract.py` · `blip_extract.py` · `brouge_extract.py` |
| `zerodiv-cpk-extra-files.md` | Zerodiv 自研 ADV —— CPK 内 `event.enc`… | `cpk.py` · `lzo1x.py` · `termdict_extract.py` · `urakata_extract.py` |
| `zerodiv-lzo1x.md` | Zerodiv 自研 ADV—— 裏語 薄桜鬼 系 | `cpk.py` · `lzo1x.py` · `urakata_extract.py` |
| `zerodiv-talks-variant.md` | Zerodiv 自研 ADV —— **台詞バリアント機構** | `vn_zerodiv_extract.py` |

## 二、按脚本（这个 py 是干什么的）

| 脚本 | 用途 | 出自引擎册 |
|---|---|---|
| `advhd.py` | WillPlus / AdvHD (.wsc bytecode) shared engine. | `willplus-advhd` |
| `akasuna_extract.py` | 赤い砂堕ちる月 (PSV / PCSG00780 / Landkarte & dramatic create… | `hunex-ogre-dramaticcreate` |
| `akuyaku_extract.py` | 悪役令嬢は隣国の王太子に溺愛される (Switch, OPERAHOUSE, Unity / CSR1.00) 全文本提取 | `unity-adv` |
| `amennoir_extract.py` | アーメン・ノワール ポータブル (PSP, Idea Factory / Design Factory 2012… | `idea-factory-stcm2l-psp-cpk-amen-garnet` |
| `angelique_extract.py` | アンジェリーク ルトゥール (PSV, PCSG00696) 剧本正文+选项提取 [Koei Tecmo / Ruby… | `koei-pasc` |
| `arcanafam2_run.py` | アルカナ・ファミリア2 (PSP, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取 | `hunex-ika-seq-arcana2` · `hunex-ika-seq` |
| `arcanafesta_extract.py` | アルカナ・ファミリア フェスタ・レガーロ! (PSP, HuneX「IKA SEQ SYSTEM v3.4/v4.2」) 全文本提取 | `hunex-ika-seq-arcanafamiglia` · `hunex-ika-seq` |
| `arcanafesta_run.py` | アルカナ・ファミリア フェスタ・レガーロ! (PSP) 成品生成 | `hunex-ika-seq-arcanafamiglia` · `hunex-ika-seq` |
| `arcanayurei_run.py` | アルカナ・ファミリア 幽霊船の魔術師 (PSP, HuneX「IKA SEQ SYSTEM v3.4」) 全文本提取 | `hunex-ika-seq` |
| `arcobaleno_extract.py` | アルコバレーノ! ポータブル (PSP, ULJM05609) 剧本文本提取 | `idea-factory-stcm2l-psp-uni2` |
| `artemis_pfs_extract.py` | Artemis Engine (iMel) 全文本提取工具 —— 以《滄海天記》(NS-JP) 定案 | `misc-engines` |
| `asakiyumemishi_extract.py` | あさき、ゆめみし～ひととせ～ (PC / 澪 / System-NNN「NNNLib」引擎) 全文本提取 · 定稿 | `misc-engines` · `system-nnn` |
| `asakiyumemishi_psp_extract.py` | あさき、ゆめみし (PSP-JP / System-NNN「NNNLib」engine) 全文本提取 · 定稿 | `misc-engines` · `system-nnn` |
| `baccan_extract.py` | 爽海バッカニアーズ! 剧本文本提取（テキスト方式ADV / プチレーヴ） | `text-mode-adv` |
| `believer_extract.py` | BELIEVER! (PSV, PCSG00539) HuneX / UNAS('HESL') script text… | `hunex-hesl` |
| `bgloss_extract.py` | Butterfly Gloss (WillPlus / AdvHD) text extractor. | `willplus-advhd` |
| `blip_extract.py` | Butterfly Lip (PC / WillPlus-AdvHD) text extractor. | `willplus-advhd` |
| `brothers_kiss_extract.py` | ブラザーズ～恋するお兄さま＆もっと恋するお兄さま～ (Tiaramode, 2007, BGI/Ethornell) | `misc-engines` |
| `brouge_extract.py` | Butterfly Rouge (PC / WillPlus-AdvHD) text extractor. | `willplus-advhd` |
| `btf_carve.py` | 从 INSTALL.BIN 中按 fileinfo.psb.m.json 的 umd_root 表切出成员文件 | `m2-advengine-psb` |
| `btf_extract.py` | [PSP-JP] Beyond The Future -Fix The Time Arrows- 全文本提取 | `m2-advengine-psb` |
| `btf_mdf.py` | M2 PSB 的 MDF(MT19937) 外壳解密（PSP 版 Kaleido/ADVENGINE） | `m2-advengine-psb` |
| `btf_pgd.py` | PSP PGD（\\0PGD / drm_type=1 / mac_type=1）解密 | `m2-advengine-psb` |
| `bwolves_extract.py` | BLACK WOLVES SAGA -Wei\u00df und Schwarz- (Switch, STCM2L)… | `idea-factory-stcm2l-switch` |
| `cafe_extract.py` | Cafe Cuillere (PSV PCSG01197, DWANGO/Takuyo, gss engine)… | `takuyo-gss` |
| `cfm_extract.py` | Confidential Money (PSP / Otomate 2012) `.evb` -> text. | `otomate-evb-marc` |
| `chou_decrypt.py` | 蝶の毒 華の鎖 XP3 内テキスト復号（区間 XOR 鍵推定）v3 | `kirikiri-xp3` |
| `chou_extract.py` | 蝶の毒 華の鎖 全テキスト抽出（KAG3 スクリプト → 表示テキスト） | `kirikiri-xp3` |
| `chou_fix.py` | 蝶の毒 華の鎖：復号後の局所的な文字化けを既知の正解で補正する表 | `kirikiri-xp3` |
| `cpk.py` | CRI CPK unpacker (纯 Python, 无依赖). | `cri-cpk-afs` · `idea-factory-stcm2l-psp-cpk-amen-garnet` · `idea-factory-stcm2l-psp-cpk` … |
| `cpk_v1.py` | CRI CPK unpacker (v1 ITOC-style + v2/v3 @UTF), 纯 Python. | `cri-cpk-afs` · `idea-factory-stcm2l-psp-cpk-amen-garnet` |
| `crazychain_extract.py` | CRAZY CHA!N -エルピスの鎖- (Nintendo Switch) 全文本提取 | `unity-adv-hscript` |
| `crazychain_xci.py` | CRAZY CHA!N -エルピスの鎖- (Switch XCI) → 切出 secure 分区内的 NCA | `idea-factory-stcm2l-switch-ghp` · `konami-unity-bytes-works` · `takuyo-gss-switch-scr2` … |
| `crimson_royale_extract.py` | クリムゾン・ロワイヤル (QuinRose, 2009 / KiriKiri KAG3, DropWave OTag… | `kirikiri-xp3` |
| `dcgs_extract.py` | D.C. Girl's Symphony Pocket (PSP, ULJM05690) 剧本文本提取 | `idea-factory-stcm2l-psp-uni2` |
| `enkan_extract.py` | 円環のメモーリア -カケラ灯し- (PSV / PCSG01167 / A'sRing & Dramatic… | `hunex-ogre-dramaticcreate` |
| `etude_extract.py` | Extract all displayed text from étude prologue 〜揺れ動く心のかたち〜… | `takuyo-gss-psp` |
| `fsymph_extract.py` | for Symphony ポータブル (PSP-JP, Takuyo, ULJM05258, v1.01)… | `takuyo-gss-psp-symphony` |
| `gakuenk_extract.py` | 学園K -Wonderful School Days- V Edition (PSV, PCSG00654… | `gakuenk-dat-scr` |
| `garnet_extract.py` | ガーネット・クレイドル ポータブル ～鍵の姫巫女～ (PSP, 2011 / STCM2L "Minku 07.0") | `idea-factory-stcm2l-psp-cpk-amen-garnet` |
| `gensou_decode.py` | 蝶の毒 華の鎖 ～幻想夜話～ XP3 内テキスト復号 v3（確定復元表方式） | `kirikiri-xp3` |
| `gensou_extract.py` | 蝶の毒 華の鎖 ～幻想夜話～ 全テキスト抽出（KAG3 スクリプト → 表示テキスト） | `kirikiri-xp3` |
| `gensou_scan.py` | 蝶の毒 華の鎖 ～幻想夜話～ 残存化けの統計的検出 | `kirikiri-xp3` |
| `geten_extract.py` | 下天の華 with 夢灯り (PSVita PCSG00921) 全文本抽取器 | `koei-cdar` |
| `ghp_extract.py` | Glass Heart Princess for Nintendo Switch —— 全文本提取器 | `idea-factory-stcm2l-switch-ghp` |
| `gss_codec.py` | GSS / LSDARC 'LSD\\x1a' codec (Takuyo gss engine). | `takuyo-gss-switch` |
| `gss_lsdarc.py` | LSDARC V.100 container (Takuyo gss). Index = "<NAME>.BIN"… | `takuyo-gss-psp-hoshiiro` · `takuyo-gss-psp-littleaid` · `takuyo-gss-psp-symphony` … |
| `gss_scr3.py` | SCR 3.00 (Takuyo gss / Switch) disassembler. | `takuyo-gss-switch` |
| `hakuoki_zuisouroku_extract.py` | 薄桜鬼 随想録 面影げ花 (PSV, PCSG00485, Idea Factory / Otomate) | `idea-factory-stcm2l-psv-g` |
| `hanayoi_afs.py` | AFS0（AFS\0）归档索引解析：条目偏移/大小 → 取数据 | `cri-cpk-afs` |
| `hanayoi_extract.py` | 返回 (lines, unknown) | `cri-cpk-afs` |
| `hanayoi_run.py` | 批量驱动 hanayoi_extract.py：多脚本合并成一份成品（一次点击 = 一行） | `cri-cpk-afs` |
| `haruka5_extract.py` | 遙かなる時空の中で5 (PSP / ULJM-05821, Koei / Ruby Party) 全文本提取器 | `koei-cdar` |
| `heiligenstadt_extract.py` | 《ハイリゲンシュタットの歌》 (PS Vita / PCSG01070 / eXtend / Unity… | `unity-adv` |
| `himehibi_crawl.py` | ordered list of callee script names (0x1e / 0x1d). | `takuyo-gss` |
| `himehibi_disasm.py` | SCR 2.00 (Takuyo gss / LSDARC) disassembler with… | `takuyo-gss-psp-hoshiiro` · `takuyo-gss-psp-littleaid` · `takuyo-gss-psp-symphony` … |
| `himehibi_extract.py` | Extract all displayed text from ひめひび -Princess Days- (PSV… | `takuyo-gss` |
| `himehibi_lsdarc.py` | LSDARC V.100 (Takuyo gss engine) reader. | `takuyo-gss-psp` · `takuyo-gss-switch-scr2` · `takuyo-gss` |
| `hoshiiro_extract.py` | 星色のおくりもの (PSP-JP, 2008 Takuyo) full-text extractor. | `takuyo-gss-psp-hoshiiro` |
| `iso_cut_cpk.py` | ISO9660 内指定 LBA 的 CPK 切出并解包 —— PSP（Zerodiv / CRI CPK 系）通用驱动 | `otomate-evb-marc` |
| `izasen_cpk.py` | いざ、出陣！恋戦 data.cpk 解包（CPK 名 cp932 修正版） | `cri-cpk-afs` |
| `izasen_extract2.py` | いざ、出陣！恋戦（PSP）全文本提取 v2：按 [next file] 链定顺序 | `cri-cpk-afs` |
| `izasen_stream.py` | いざ、出陣！恋戦 data.cpk → 剧本流还原 | `cri-cpk-afs` |
| `jewelic_extract.py` | Jewelic Nightmare (PSP, Otomate 2013, ULJM06326) 全文本提取 | `idea-factory-stcm2l-psp-cpk` |
| `kaeru_extract.py` | カエル畑DEつかまえて☆彡 (NS-JP, TAKUYO) text extract. | `takuyo-gss-switch-scr2` |
| `kamikoi_extract.py` | 神さまと恋ゴコロ (NS-JP) text extract ---- Takuyo gss / LSDARC 'SCR… | `takuyo-gss-switch` |
| `kannagi_extract.py` | 神凪ノ杜 五月雨綴り (NS-JP, Unity 2021 IL2CPP, Matatabi) 剧本正文 + 选项提取 | `matatabi-unity-textadv` |
| `kazahanaki_extract.py` | 遙かなる時空の中で5 風花記 (PSP / ULJM-05950, Koei / Ruby Party) 全文本提取器 | `koei-cdar` |
| `koigig_extract.py` | KoiGIG ～DEVIL×ANGEL～ (TWOFIVE / DonMaccow, 2007) 文本提取器 | `misc-engines` |
| `l2ll_extract.py` | L2 Love×Loop (PS2 / Idea Factory / SLPM-55191) 剧本文本提取 | `idea-factory-stcm2l-ps2-uni2` |
| `lamento_extract.py` | Lamento -BEYOND THE VOID- (Windows 10 Support Edition) —… | `nitroplus` |
| `lastescort_extract.py` | ラストエスコート -Club Katze- (PSP) 全文本提取 —— 通用驱动 | `lastescort-paf` |
| `libp_malievita.py` | Malie（Vita）Libp 归档读取库：入口表 / 文件名 / 数据切片 | `malie` |
| `littleaid_extract.py` | Little Aid Portable (PSP-JP, 2007 Takuyo, ULJM-05...)… | `takuyo-gss-psp-littleaid` |
| `lovepeace_extract.py` | 恋戦隊LOVE＆PEACE THE P.S.P. (PSP / BROCCOLI 2012) MES.DAT text… | `lovepeace-adv` |
| `loverevo_extract.py` | 乙女的恋革命★ラブレボ!! Portable (PSP) 全文本提取 | `hunex-ogre-loverevo` |
| `lucian_extract.py` | Lucian Bee's: Resurrection Supernova (PSP, 2010, HuneX IKA… | `hunex-ika-seq-lucian` |
| `lzo1x.py` | LZO1X-1 (miniLZO) 解压器 + event.enc entry 解压测试 | `zerodiv-cpk-extra-files` · `zerodiv-lzo1x` |
| `majikyun_extract.py` | マジきゅんっ！ルネッサンス (PSV / PCSG00852 / HuneX & BROCCOLI) 全文本提取器 | `hunex-ogre` |
| `makumatsu_extract.py` | 《幕末Rock 超魂》(PS Vita / PCSG00425 / Marvelous) 全文本提取 | `mz-cmdstream` |
| `malie_extract.py` | Malie System (GreenWood) 通用提取工具 —— OmegaVampire repack… | `malie` |
| `manimani_extract.py` | 花咲くまにまに (PSV, PCSG00366, MAGES. / SC3) 文本提取 | `mages-sc3-mpk` |
| `marc_font.py` | 5pb PSP (Musketeer/EVB engine) MARC font atlas unpacker. | `musketeer-psp-evb` |
| `marginal4_extract.py` | [PSV-JP] MARGINAL#4 IDOL OF SUPERNOVA (PCSG00448, Otomate x… | `idea-factory-stcm2l-psv-cp932` |
| `marginal4rtg_extract.py` | [PSV-JP] MARGINAL#4 ROAD TO GALAXY (PCSG01008, Otomate x… | `idea-factory-stcm2l-psv` |
| `meiji_extract.py` | 明治活劇 ハイカラ流星組 (NS-JP) テキスト抽出. | `meiji-haikara-lzs` |
| `meiji_lzs.py` | 明治活劇 ハイカラ流星組 (NS-JP) の .lzs 解凍器 (c) 2026. | `meiji-haikara-lzs` |
| `minus8_extract.py` | マイナスエイト (-8) PSP, Otomate/Rejet, ULJM06341, vndb v12155 ——… | `idea-factory-stcm2l-psp-cpk` |
| `mizu2_extract.py` | 水の旋律2 ～緋の記憶～ (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本 | `thfs-mizu` |
| `mizu_extract.py` | 水の旋律 (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本 | `thfs-mizu` |
| `moon_atl_extract.py` | 月ノ光太陽ノ影 (PC/ATL engine) 全文本提取 | `aromarie-atl` |
| `musketeer_charset.py` | Musketeer (PSP/5pb) .evb text decoder -- solved 2026-10-13. | `musketeer-psp-evb` · `otomate-evb-marc` |
| `musketeer_extract.py` | Musketeer (PSP/5pb) `.evb` -> text. | `musketeer-psp-evb` |
| `mysteria_extract.py` | 英国探偵ミステリア The Crown (PSV, Malie System / MalieVita)… | `malie` |
| `mysteria_text.py` | 英国探偵ミステリア The Crown (PSV) —— Malie exec.dat → 全文本（一次点击 = 一行） | `malie` |
| `naninovel_assemble.py` | 把 naninovel_extract.py 的 _scripts.json 组装成 §0 规范成品 txt | `naninovel-unity` |
| `naninovel_extract.py` | Naninovel (Unity IL2CPP) 脚本文本提取器 | `naninovel-unity` |
| `neoange_psp_extract.py` | ネオアンジェリークSpecial (PSP-JP, Koei) 全文本提取 | `koei-cdar` |
| `neoangelique_extract.py` | ネオ アンジェリーク 天使の涙 (PSV-JP, PCSG01068, Otomate / Idea Factory)… | `gakuenk-dat-scr` |
| `niladmirari_extract.py` | ニル・アドミラリの天秤 色ドリ撫子 (Switch) —— 全文本提取器 | `idea-factory-stcm2l-switch` |
| `norn9_extract.py` | Norn9 ～Norn + Nonette～ Act Tune (PSV, PCSG00833) 剧本文本提取 | `idea-factory-stcm2l-psv` · `idea-factory-stcm2l` |
| `npa_nrbf.py` | Nitroplus NPA 内 NRBF（.NET BinaryFormatter）序列化数据的解析器 | `nitroplus` |
| `nsac.py` | NSAC (v2) 容器解析/解包 —— eXtend 系 PSVita 作品《逢魔が刻… | `misc-engines` |
| `nsp_split.py` | PFS0(NSP) 逐块直拷拆分器 —— 规避 hactool --pfs0dir 对 >1.7GB 成员写全零的问题 | `konami-unity-bytes-works` |
| `oga_sts_extract.py` | O*G*A 鬼ごっこロワイアル ハンターは孤島で恋をする (PSP-JP / Idea Factory・Otomate) | `oni-psp-tob` |
| `orfleur_extract.py` | オルフレール ～幸福の花束～ (PSV PCSG00919 / dramatic create「Orfre」DCVM)… | `orfre-dcvm` |
| `orfleur_stbl_extract.py` | オルフレール ～幸福の花束～ (PSV / PCSG00919, dramatic create「Orfre」… | `orfre-dcvm` |
| `orfleur_trace.py` | Orfre/DCVM 执行序追踪（CFG 走块 + 调用捕获）——用于确定「一次点击=一行」的显示序 | `orfre-dcvm-history` |
| `orfleur_vm.py` | Orfre/DCVM 线性走链器：用于恢复「一次点击 = 一行」的文本序 | `orfre-dcvm-history` |
| `ouma_build_text.py` | 《逢魔が刻 ～かくりよの縁～》系统/资料文本整理 | `misc-engines` |
| `ouma_extract.py` | 《逢魔が刻 ～かくりよの縁～》(PSVita / PCSG00769) 游戏内文本提取 | `misc-engines` |
| `ouma_story.py` | 《逢魔が刻 ～かくりよの縁～》本編 ADV シナリオ抽出 (NML スクリプト) | `misc-engines` |
| `ozmafia_extract.py` | OZMAFIA!! -vivace-（Nintendo Switch, 01002BE0118AE000… | `hunex-ogre-ozmafia` |
| `ozmafia_nca.py` | NCA 头/key area 检视器（Switch）—— 用于旧 hactool 无法处理的 BKTR 增量补丁 NCA | `hunex-ogre-ozmafia` · `naninovel-unity` · `switch-nca` |
| `pandora_dbg.py` | pandora_extract 的调试视图：按地址反查所属文件，并打印附近字符串 | `idea-factory-stcm2l` |
| `pandora_extract.py` | PANDORA ～君の名前を、僕は知る～ (PS2, Otomate / Idea Factory 2010)… | `idea-factory-stcm2l` |
| `paradigm_paradox_extract.py` | Paradigm Paradox (Regista advGame engine) 全文本提取器 —— 定稿 | `misc-engines` |
| `pc_snr_order.py` | 从 PC 汉化补丁的 .snr（UTF-16LE KiriKiri 脚本）提取「剧情序」标尺 | `orfre-dcvm-history` |
| `prince5_extract.py` | 5人の恋プリンス ~ヒミツの契約結婚~ (PSV, PCSG00590) 文本提取 | `asgard-tat` |
| `prince_stride_lt.py` | プリンス・オブ・ストライド (PSV PCSG00491) —— lt.bin 字形图集渲染（2026-10-12） | `prince-stride-d3p` |
| `prince_stride_run.py` | プリンス・オブ・ストライド (PSV PCSG00491) —— sc.cpk → 全文本（2026-10-12） | `prince-stride-d3p` |
| `psarc_extract.py` | PSARC (Sony) extractor — big-endian classic PSARC. | `lte` · `text-mode-adv` · `unity-adv` |
| `psycemo6_extract.py` | PsychicEmotion6 (PSV / PCSG00815 / Otomate x Idea Factory… | `idea-factory-stcm2l-psv` |
| `realrode_extract.py` | Real Rode ポータブル (PSP, HuneX「IKA SEQ SYSTEM v3.1」) 全文本提取 | `hunex-ika-seq` |
| `revice_extract.py` | RE:VICE[D] (PSV, PCSG00382, Otomate / Idea Factory) 剧本文本提取 | `idea-factory-stcm2l-psv-cp932` · `idea-factory-stcm2l` |
| `rom2_extract.py` | ROM2 archiver (Kalmia8 / 鳥籠のマリアージュ PSV). | `rom2-snr` |
| `rootrexx_extract.py` | ROOT∞REXX (PSV / PCSG00458 / Otomate×Idea Factory / 2015)… | `idea-factory-stcm2l-psv-cp932` |
| `sanzen_extract.py` | 参千世界遊戯 ～Re Multi Universe Myself～ (PSV, PCSG01194… | `rom2-snr` |
| `senjyushi_extract.py` | 千銃士:Rhodoknight (NS) 解包 —— 压缩 NCA (LZ4 bucket-tree) → RomFS → 文件 | `switch-nca` · `unity-adv` |
| `senjyushi_extract_text.py` | 千銃士Rhodoknight (NS) —— SceneMasterVO.bin 全文本提取 | `unity-adv` |
| `shinjuku_text.py` | 新宿羅生門 ―Rashomon of Shinjuku― (Switch / Idea… | `karin-adv-asb` |
| `siglus_scene_extract.py` | SiglusEngine (罪ナル螺旋ノ檻 / Tsuminaru) Scene.pck text extractor. | `siglus` |
| `snowboundland_extract.py` | SNOW BOUND LAND (PSP, Otomate / Idea Factory 2013) 剧本文本提取… | `idea-factory-stcm2l-psp-cpk` |
| `solomon_extract.py` | [PSP-JP] Solomon's Ring ～地の章～ (Plan Peace / InterOne… | `planpeace-pct` |
| `sorayume_extract.py` | ソラ*ユメ (NS-JP, TAKUYO, TitleID 0100e6a027760000) text… | `takuyo-gss-switch-scr2` |
| `stcm2l_extract.py` | STCM2L 剧本文本提取器 —— 猛獣たちとお姫様 for Nintendo Switch | `idea-factory-stcm2l-switch` · `idea-factory-stcm2l` |
| `stormlover2_charset.py` | STORM LOVER 2nd V (PSV PCSG00736) —— sc.cpk 自建字符集（二级自定义槽） | `stormlover-d3p` |
| `stormlover2_run.py` | STORM LOVER 2nd V (PSV PCSG00736) —— 从 sc.cpk 产出全文本 | `stormlover-d3p` |
| `stormlover_assets.py` | STORM LOVER V (PSV PCSG00735) —— 资源解压工具（2026-10-11） | `stormlover-d3p` |
| `stormlover_charset.py` | STORM LOVER V (PSV PCSG00735) —— sc.cpk 自建字符集（最终版 2026-10-11） | `prince-stride-d3p` · `stormlover-d3p` |
| `stormlover_font.py` | STORM LOVER V (PCSG00735) 字形图集读取器 —— lt.bin | `stormlover-d3p` |
| `stormlover_natsu_charset.py` | STORM LOVER 夏恋!!（PSP / ULJM-05858?）—— sc.cpk 自建字符集（2026-10-12） | `stormlover-d3p-psp` |
| `stormlover_natsu_run.py` | STORM LOVER 夏恋!!（PSP）—— 从 sc.cpk 产出全文本（2026-10-12） | `stormlover-d3p-psp` |
| `stormlover_psp_cmp.py` | STORM LOVER 夏恋!!（PSP）—— 二级槽「字形 vs 候选字」比对图（人工目视定值） | `stormlover-d3p-psp` |
| `stormlover_psp_font.py` | STORM LOVER 夏恋!!（PSP）—— lt.bin 自建位图字体渲染（2026-10-12） | `stormlover-d3p-psp` |
| `stormlover_run.py` | STORM LOVER V (PSV PCSG00735) —— 从 sc.cpk 产出全文本（2026-10-11） | `stormlover-d3p` |
| `switch_nca.py` | Switch NCA 解密器（不依赖 hactool）—— 处理 Titlekey crypto / Standard crypto 的 Program NCA | `switch-nca` · `unity-adv` |
| `termdict_extract.py` | 用語辞典（termItem.dat）→ `【見出し語】解説文` 一行一条，并入成品末尾 | `zerodiv-cpk-extra-files` |
| `tiny_machinegun_extract.py` | Tiny×MACHINEGUN THE GAME (Rejet / PC-JP) 剧本・辞典文本提取器 —— 端到端定稿 | `misc-engines` |
| `tokihako_extract.py` | 時函 -Time Capsule- (Ray, 2009 / PC / NScripter) 全文本提取 | `misc-engines` |
| `tokimemo_gs1_extract.py` | ときめきメモリアル Girl's Side 1st Love (NS-JP, Unity) 全文本提取器 | `konami-unity-bytes-works` |
| `tokimemo_gs2_extract.py` | ときめきメモリアル Girl's Side 2nd Season (NS-JP, Unity) 全文本提取器 | `konami-unity-bytes` |
| `tokimemo_gs3_extract.py` | ときめきメモリアル Girl's Side 3rd Story for Nintendo Switch (NS-JP, Unity) 全文本提取器 | `konami-unity-bytes-works` |
| `tokimemo_gs4_extract.py` | ときめきメモリアル Girl's Side 4th Heart for Nintendo Switch (NS-JP, Unity) 全文本提取器 | `konami-unity-bytes-works` |
| `tokitama_extract.py` | ときたま！～時函玉手箱～ (Ray, 2010 / PC / NScripter) 全文本提取 | `misc-engines` |
| `torimari_extract.py` | 鳥籠のマリアージュ ～初恋の翼～ (PSV, PCSG90230, Kalmia8 / ACTGS engine) | `rom2-snr` |
| `unity_list.py` | 列出 Unity AssetBundle / .assets 内的对象（type + name/path_id），不 dump 内容 | `matatabi-unity-textadv` |
| `unity_textasset_dump.py` | Unity `resources.assets` → 全 TextAsset 落盘（旁车 / managed text 导出） | `matatabi-unity-textadv` · `naninovel-unity` |
| `urakata_extract.py` | 裏語 薄桜鬼 (PSP ULJM06281) 剧本提取器 —— LZO1X 解压版 | `zerodiv-cpk-extra-files` · `zerodiv-lzo1x` |
| `us_walk.py` | Parse .NET #US heap of a PE assembly and dump the ordered… | `lte` |
| `valpurga_extract.py` | [PSV-JP]ヴァルプルガの詩 (PCSG00768) 全文本提取 | `3daisy-scrvita` |
| `vamwolf_lt.py` | Vamwolf Cross† lt.bin 字形图集渲染 | `prince-stride-d3p` |
| `vamwolf_run.py` | Vamwolf Cross† (PSV PCSG00467, D3P 系) —— sc.cpk → 全文本 | `prince-stride-d3p` |
| `verite_extract.py` | 《薔薇に隠されしヴェリテ》 (PS Vita / PCSG00708 / Unity 5.3.5p5) 全文本提取 | `unity-adv` |
| `vitaminb6_extract.py` | VitaminX DetectiveB6 (PSP, HuneX「IKA SEQ SYSTEM v4.1 HuneX 2010」) 全文本提取 | `hunex-ika-seq-b6` |
| `vitaminxz_extract.py` | Vitamin X to Z (PSP, ULJS00347, HuneX「IKA SEQ SYSTEM v4.1」) 全文本提取 | `hunex-ika-seq-vitaminxz` |
| `vitz_extract.py` | VitaminZ (PSP, ULJS00240, HuneX「IKA SEQ SYSTEM v3.4 HuneX 2009」) 全文本提取 | `hunex-ika-seq-vitaminz` |
| `vn_zerodiv_extract.py` | 裏語 薄桜鬼 / ～暁の調べ～ (PSP ULJM06281 / ULJM06373) 剧本提取器 —— 定稿版 | `zerodiv-talks-variant` |
| `vzgrad_extract.py` | VitaminZ Graduation (PSP, ULJS00xxx v1.01, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取 | `hunex-ika-seq-vzgrad` |
| `willowisp_extract.py` | ウィル・オ・ウィスプ ポータブル (PSP, ULJM05447, Design Factory & Otomate… | `idea-factory-stcm2l-psp-uni2-willow` |
| `xp3.py` | 蝶の毒 華の鎖 XP3 索引列挙 + ファイル抽出 (KiriKiri XP3) | `kirikiri-xp3` |
| `yamanote_extract.py` | TOKYOヤマノテBOYS for V MAIN DISC（PSV / PCSG01048）全文本提取 | `lte` |
| `yourmo_extract.py` | ユア・メモリーズオフ～Girl's Style～ (PSP-JP, ULJM05435, MAGES. 2008) | `mages-afs-yourmo` |
| `zokuwanai_extract.py` | 罪喰い ~千の呪い、千の祈り~ for V (PSV / PCSG01019 / HuneX, dramatic… | `hunex-ogre-dramaticcreate` |
| `zokuwanai_unpack.py` | 罪喰い for V (PCSG01019, HuneX Ogre) allscr.mrg 解包 + MZX0 解压 | `hunex-ogre-dramaticcreate` |

## 三、没有任何引擎册引用（薄壳 / 一次性脚本 / 漏记）

共 64 个。**不要凭文件名猜**——先看「用途」列，再 `head` 确认。

| 脚本 | 用途 |
|---|---|
| `cdar.py` | CDAR 容器读取库（被 cdar_extract.py import）：索引表 + 条目解压 |
| `cdar_extract.py` | 递归解包 CDAR 容器（可下钻嵌套），逐条目落成原始字节 |
| `corda_2fa_extract.py` | 金色のコルダ2f アンコール (PSP) 全文本提取器 v3. |
| `corda_2fa_get.py` | 按路径取出 CDAR v4 里某个叶子文件: corda_2fa_get.py <DATA.BIN> <base>… |
| `corda_2fa_scan.py` | 金色のコルダ2f アンコール (PSP) - 递归解包 + 分类导出. |
| `corda_2fa_unpack.py` | 金色のコルダ2f アンコール (PSP) CDAR v4 解包器. |
| `corda_2ff_extract.py` | 金色のコルダ2 ff (PSVita, PCSG01124) 全文本提取器 |
| `corda_2ff_g1t.py` | 金色のコルダ2 ff : Koei G1T (GT1G0600) 字体图集解码 -> PNG |
| `corda_3_extract.py` | 金色のコルダ3 (PSVita, PCSG01211) 全文本提取器 |
| `corda_3as_extract.py` | 金色のコルダ3 AnotherSky feat.神南/至誠館/天音学園 (PSVita PCSG01212)… |
| `corda_boxcheck.py` | 诊断: 同一文本框被拆? 对某个 コルダ 提取器, 找「间隔含追加码 1e7e02b205」的记录对, |
| `corda_octave_extract.py` | 金色のコルダ オクターヴ (Switch) 全文本提取器 v3 (定稿候选) |
| `corda_psp_extract.py` | 金色のコルダ (PSP) 剧本/文本提取器 (自包含, 无外部依赖) |
| `corda_psp_unpack.py` | 金色のコルダ (PSP) 容器解包 : ISO9660 -> CDVDAR.DAR (Koei CDAR v2) ->… |
| `crankin_extract.py` | クランク・イン (Crank In) — PSV / PCSG00941 / プチレーヴ (Puchireve) |
| `extract_alice.py` | Extract scenario text from the Alice-series PSP games… |
| `extract_text.py` | PSP アラビアンズ・シリーズ 脚本テキスト抽出 |
| `fortissimo_extract.py` | 《フォルティッシモ》 (PS Vita / PCSG01131 / KADOKAWA x Otomate… |
| `fullscan.py` | 逐个归档条目试解压，按「含日文字数」排序 —— 先定位正文在哪一层容器 |
| `haruka2_appmatrix.py` | 从 BOOT.BIN 读取 16x16「呼び名」称呼矩阵 |
| `haruka2_eem_extract.py` | 遙かなる時空の中で２ (PSP) 全文本提取 — 最终版 |
| `haruka2_eemlib.py` | Return (headerFields, sectionA, sectionB) for KOEID0 entry… |
| `haruka4_extract.py` | Extractor for 遥かなる時空の中で4 (PSP, Koei / Ruby Party). |
| `haruka6_dedup.py` | 遥かなる時空の中で6 DX —— 变体分支后处理：保留「默认名版」，删除「不含名字/泛指」的替代句 |
| `haruka6_dict.py` | 遥かなる時空の中で6 DX —— 用語辞典（見出し語＋解説）构建器 v2 |
| `haruka6_extract.py` | 遥かなる時空の中で6 DX (Switch) 全文本提取器 v2 |
| `haruka_extract.py` | Extractor for Koei / Ruby Party "Harukanaru Toki no Naka… |
| `himehibi2_eboot.py` | ひめひび 続！二学期 —— 第 2 段：eboot 串表抽取 + 成品组装 |
| `himehibi2_extract.py` | Extract all displayed text from ひめひび ─New Princess Days!!─… |
| `himehibi_scan.py` | 把 LSDARC 解出的脚本扫一遍，确认哪些脚本含正文（探路用） |
| `izasen_cpk2.py` | いざ、出陣！恋戦 data.cpk 解包（v2：CRILAYLA 修正 + FileOffset 绝对偏移） |
| `izasen_cpk3.py` | いざ、出陣！恋戦 data.cpk → .ks 解包（v3） |
| `izasen_extract.py` | いざ、出陣！恋戦（PSP）全文本提取：逻辑流 → KAG 脚本 → 正文/选项 |
| `izasen_ks.py` | いざ、出陣！恋戦 data.cpk → scenario/*.ks（内容锚定版） |
| `izasen_ks2.py` | いざ、出陣！恋戦 data.cpk → scenario/*.ks（终版） |
| `kaleido_extract.py` | カレイドイヴ (PSV / PCSG00520 / estciel & HuneX) 全文本提取器 |
| `lztest.py` | 对 KOEID0.BIN 各条目试 zlib 与原始解压，按输出熵排序判断压缩方案（一次性实验） |
| `musketeer_render_atlas.py` | 5pb PSP MARC font-atlas renderer (ar999_0000.bin). |
| `opcode_audit.py` | 通用「有没有漏文本」审计（自定义 bytecode ADV 通用） |
| `pe_dis.py` | PE 反汇编辅助（capstone）：按 RVA/VA 定位并打印附近指令 |
| `period55.py` | 55 字节周期 XOR 键的爆破与验证（用于 .het 辞书） |
| `possession_extract.py` | Extractor for Possession Magenta (ポゼッション マゼンタ, PSV… |
| `ps2_extract.py` | PS2 .HD/.BIN extractor for the *Hakarena Heart*-type engine. |
| `ps2_game.py` | VM-level extraction: one line per message box (one click). |
| `ps2_scene.py` | Classify one 08-record payload. |
| `ps2_vm.py` | VM-level .cnut (Squirrel 'SQIR'/PART container) dialogue… |
| `psp_prx_type9_decrypt.py` | PSP ~PSP (EncryptType 9) EBOOT.BIN decrypter. |
| `qpk.py` | QuinRose / Qoo-framework QPK/QPI archive reader (PSP). |
| `rear_extract.py` | リアフェレス（Unity）TextAsset 场景脚本提取 → リアフェレス.txt |
| `renderfont.py` | 把字库图集渲染成 PNG（逐码位预览，供人工目视确认字形） |
| `run_alice.py` | Batch extract scenario text from the 6 Alice-series PSP… |
| `scan_jp.py` | 目录级扫描：找「连续假名 run 多」的文件并排序 —— 先圈候选，再细看 |
| `scan_nested.py` | 在归档的嵌套条目里扫日文，报 magic / 大小 / 样例 |
| `scanjp.py` | 单文件内定位连续假名 run（按偏移列出），用于确认哪一段是正文 |
| `sgs_kai_ddp.py` | 三国恋戦記 魁 (Daisy2 / sgs_*.dat, DDP2/DDP3) 解包 + 解密 + 解压 |
| `sgs_kai_extract.py` | 三国恋戦記 魁 —— 全文本提取（对话/选项/结局/教程） |
| `shinoda_botan_extract.py` | 篠田新宿探偵事務所 唐獅子牡丹 (HolicWorks Disc Blue / 2018-10-26 / PC-JP) |
| `sjis_scan.py` | 单文件 SJIS 双字节串提取，并按「段」分类计数（区分正常串与化け） |
| `stormlover_extract.py` | STORM LOVER V (PSV PCSG00735) sc.cpk 正文提取（2026-10-11） |
| `stride_extract.py` | 《[PSV-JP]プリンス・オブ・ストライド》 (PCSG00491) 资源解密 / 解包 / 文本探查工具 |
| `tsundere_extract.py` | ツンデレ★Ｓ乙女 (PC / 美蕾「Madoka GScript」) 全文本提取器 —— 本项目定稿 |
| `unity_scan.py` | Unity 资产文本扫描：UTF-8 / UTF-16LE / CP932 逐个试，报日文字数 |
| `unity_scan2.py` | Unity 资产文本扫描（按 UTF-8 字节模式直接匹配，不做解码） |
| `vn_memdump.py` | 从运行中的进程按内存区段 dump（Windows，ReadProcessMemory） |
