# 引擎 → 可复用脚本

> **每次构建自动重建** —— 不要手改（改引擎册里的工具引用即可）。
>
> 用法：`references/S0-triage.md` 命中引擎 → 打开 `references/engines/<slug>.md`
> 看容器链路与记录形状 → 回到本表挑**最近似**的脚本 → **只改路径 / 键 / 参数**。
> 通用工具（判型 / 探查 / 品检 / 收尾）见 `INDEX.md`，本表不重复。

## 一、按引擎（命中后从这一行开始）

| 引擎册 | 引擎 | 可直接改的脚本 |
|---|---|---|
| `3daisy-scrvita.md` | 3Daisy 自研 | `valpurga_extract.py` |
| `arc0-mlk-adv.md` | KID 自研 mlk/ADV | `mizumelody_arc.py` · `mizumelody_text.py` |
| `aromarie-atl.md` | Aromarie 自研「ATL」引擎 | `moon_atl_extract.py` |
| `asgard-tat.md` | ASGARD 自研「TAT」文本脚本 | `prince5_extract.py` |
| `broccoli-opfflow.md` | Broccoli 自研指令流 | `cpk.py` · `nsp_split.py` |
| `crank-text-mode-adv.md` | 自研「テキスト方式 ADV」 | `baccan_extract.py` · `psarc_extract.py` |
| `cri-cpk-afs.md` | CRI | `cpk.py` · `cpk_v1.py` · `hanayoi_afs.py` · `hanayoi_extract.py` · `hanayoi_run.py` · `izasen_cpk.py` · `izasen_extract2.py` · `izasen_stream.py` |
| `cri-snbin-lzss.md` | CRIWARE 系 ＋ sn.bin LZSS | `cpk_cri.py` · `utapri_as_extract.py` · `utapri_rl_ns_extract.py` · `winscan.py` |
| `d3p-koishiba.md` | 引擎：D3P/Vridge 自研 ADV · **恋は校則に縛られない！** 变体 | `cpk.py` · `iso9660.py` · `koishiba_charset.py` · `koishiba_font.py` · `koishiba_run.py` |
| `d3p-ps2-fpk-vml.md` | D3P PS2 · FPK 归档 + VML 脚本 | `build_text.py` · `fpk.py` · `fpkx.py` · `lastescort_vml.py` |
| `gakuenk-dat-scr.md` | Otomate / Idea Factory 自研「DAT + PAK + SCD」 | `gakuenk_extract.py` · `neoangelique_extract.py` |
| `hunex-als.md` | HuneX · ALS | `lucianj_extract.py` · `lucianv_extract.py` |
| `hunex-hesl.md` | HuneX「HESL / UNAS」系 | `believer_extract.py` · `hunex_hlzs.py` · `vxdst_extract.py` |
| `hunex-hesl-switch.md` | HuneX HESL/HESE · **Switch 变体** | `sspm_extract.py` |
| `hunex-ika-seq.md` | HuneX · IKA SEQ SYSTEM | `arcanafam2_run.py` · `arcanafesta_extract.py` · `arcanafesta_run.py` · `arcanayurei_run.py` · `realrode_extract.py` |
| `hunex-ika-seq-arcana2.md` | HuneX IKA SEQ —— 压缩变体·第 4 作：アルカナ・ファミリア2 | `arcanafam2_run.py` |
| `hunex-ika-seq-arcanafamiglia.md` | HuneX IKA SEQ —— 压缩变体：アルカナ・ファミリア | `arcanafesta_extract.py` · `arcanafesta_run.py` |
| `hunex-ika-seq-b6.md` | HuneX IKA SEQ —— 第 7 作：VitaminX DetectiveB6 | `vitaminb6_extract.py` |
| `hunex-ika-seq-lucian.md` | HuneX IKA SEQ —— 第 5 作：Lucian Bee's: Resurrection Supernova | `lucian_extract.py` |
| `hunex-ika-seq-vitaminx-ep.md` | HuneX IKA SEQ —— 第 10 作：ビタミンX Evolution Plus | `vitaminx_ep_extract.py` |
| `hunex-ika-seq-vitaminxz.md` | HuneX IKA SEQ —— 第 6 作：Vitamin X to Z | `vitaminxz_extract.py` |
| `hunex-ika-seq-vitaminz.md` | HuneX IKA SEQ —— 第 9 作：VitaminZ | `vitz_extract.py` |
| `hunex-ika-seq-vzgrad.md` | HuneX IKA SEQ —— 第 8 作：VitaminZ Graduation | `vzgrad_extract.py` |
| `hunex-ogre.md` | HuneX「Ogre」系 | `majikyun_extract.py` |
| `hunex-ogre-dramaticcreate.md` | HuneX「Ogre」系 · dramatic create 移植三作 | `akasuna_extract.py` · `enkan_extract.py` · `zokuwanai_extract.py` · `zokuwanai_unpack.py` |
| `hunex-ogre-loverevo.md` | HuneX「Ogre」系 · PSP 变体 —— 乙女的恋革命★ラブレボ!! Portable | `loverevo_extract.py` |
| `hunex-ogre-ozmafia.md` | HuneX「Ogre」系 · OZMAFIA!! -vivace | `ozmafia_extract.py` · `ozmafia_nca.py` |
| `idea-factory-stcm2l.md` | STCM2L | `norn9_extract.py` · `pandora_extract.py` · `revice_extract.py` · `stcm2l_extract.py` |
| `idea-factory-stcm2l-ps2-uni2.md` | STCM2L · CRI「UNI2」容器 —— PS2/PSP 样本 | `l2ll_extract.py` |
| `idea-factory-stcm2l-psp-cpk.md` | STCM2L · PSP「CRI CPK」侧 | `cpk.py` · `jewelic_extract.py` · `minus8_extract.py` · `snowboundland_extract.py` |
| `idea-factory-stcm2l-psp-cpk-amen-garnet.md` | STCM2L · PSP「CRI CPK」· アーメン・ノワール ポータブル ＋ ガーネット・クレイドル ポータブル | `amennoir_extract.py` · `cpk.py` · `cpk_v1.py` · `garnet_extract.py` |
| `idea-factory-stcm2l-psp-cpk-kannou.md` | STCM2L · PSP「CRI CPK」侧 ⑥ 官能昔話 ポータブル | `kannou_extract.py` |
| `idea-factory-stcm2l-psp-cpk-niseno.md` | STCM2L · PSP「CRI CPK」侧 ⑦ 二世の契り | `nisenochigiri_extract.py` |
| `idea-factory-stcm2l-psp-uni2.md` | STCM2 · CRI「UNI2」容器 —— PSP 样本 | `arcobaleno_extract.py` · `dcgs_extract.py` |
| `idea-factory-stcm2l-psp-uni2-banchou.md` | STCM2L · UNI2第 5 样本 —— 恋愛番長 命短し、恋せよ乙女！ Love is Power | `koibann_extract.py` |
| `idea-factory-stcm2l-psp-uni2-banchou2.md` | STCM2L · CPK第 7 样本 —— 恋愛番長2 MidnightLesson!!! | `koibann2_extract.py` · `uf_render.py` |
| `idea-factory-stcm2l-psp-uni2-willow.md` | STCM2 · CRI「UNI2」· PSP · ウィル・オ・ウィスプ ポータブル | `willowisp_extract.py` |
| `idea-factory-stcm2l-psv.md` | STCM2L —— PSV 侧 · **UTF-8 系** | `cpk.py` · `marginal4rtg_extract.py` · `norn9_extract.py` · `psycemo6_extract.py` |
| `idea-factory-stcm2l-psv-cp932.md` | STCM2L —— PSV 侧 · **CP932 系** | `binarystar_extract.py` · `cpk.py` · `marginal4_extract.py` · `revice_extract.py` · `rootrexx_extract.py` |
| `idea-factory-stcm2l-psv-g.md` | STCM2L —— PSV 侧 · **变体 G** | `cpk.py` · `hakuoki_zuisouroku_extract.py` |
| `idea-factory-stcm2l-switch.md` | STCM2L · Switch 侧 | `bwolves_extract.py` · `niladmirari_extract.py` · `stcm2l_extract.py` |
| `idea-factory-stcm2l-switch-ghp.md` | STCM2L · Switch 侧 第 3 例 —— Glass Heart Princess for Nintendo Switch | `crazychain_xci.py` · `ghp_extract.py` |
| `idea-factory-ydp-lsb.md` | Idea Factory／Otomate PSP · **YDP1 + LSB** | `kanuchi_dict.py` · `kanuchi_text.py` · `kanuchi_ydp.py` |
| `karin-adv-asb.md` | 花梨エンターテイメント 自研 ADV | `shinjuku_text.py` |
| `kirikiri-xp3.md` | KiriKiri XP3 | `chou_decrypt.py` · `chou_extract.py` · `chou_fix.py` · `crimson_royale_extract.py` · `gensou_decode.py` · `gensou_extract.py` · `xp3.py` |
| `koei-cdar.md` | Koei CDAR v2/v4 | `cdar.py` · `geten_extract.py` · `haruka5_extract.py` · `kazahanaki_extract.py` · `neoange_psp_extract.py` · `tokires_extract.py` |
| `koei-embins-ps2.md` | Koei PS2「EMBINS.VVV」单模块镜像 | `cd_bin2iso.py` · `trois_text.py` |
| `koei-pack-ps2.md` | Koei PS2 「HD/BIN + PACK」归档 | `emu_dec.py` · `etoile_script.py` · `etoile_text.py` · `etoile_unpack.py` · `koei_dec.py` |
| `koei-pasc.md` | Koei Tecmo / Ruby Party 自研「pasc」节点流 | `angelique_extract.py` |
| `konami-unity-bytes.md` | KONAMI 自研 Unity ADV—— ときめきメモリアル Girl's Side 1st Love / 2nd Season for Nintendo | `tokimemo_gs2_extract.py` |
| `konami-unity-bytes-works.md` | KONAMI 自研 Unity ADV—— 逐作差异 | `crazychain_xci.py` · `nsp_split.py` · `tokimemo_gs1_extract.py` · `tokimemo_gs3_extract.py` · `tokimemo_gs4_extract.py` |
| `lastescort-paf.md` | NK/PAF ＋ PSCB | `lastescort_extract.py` |
| `lastescort-vml-ps2.md` | FPK ＋ VML | `lastescort_ps2_extract.py` |
| `lovepeace-adv.md` | 引擎：BROCCOLI / Sanctuary・EMIQ ADV | `lovepeace_extract.py` |
| `lte.md` | LTE 引擎 | `psarc_extract.py` · `yamanote_extract.py` |
| `m2-advengine-psb.md` | M2「ADVENGINE」— PSP/PSV/NS 通用 | `btf_carve.py` · `btf_extract.py` · `btf_mdf.py` · `btf_pgd.py` · `btf_unpack.py` |
| `mages-afs-yourmo.md` | MAGES.PSP 自研 —— CRI AFS ＋ NUL 分段文本池 | `yourmo_extract.py` |
| `mages-sc3-mpk.md` | MAGES. 自家引擎 —— MPK 容器 ＋ SC3 脚本 | `manimani_extract.py` |
| `malie.md` | Malie System | `libp_malievita.py` · `malie_extract.py` · `mysteria_extract.py` · `mysteria_text.py` |
| `matatabi-unity-textadv.md` | Matatabi 自研「纯文本 @命令 ADV」 | `kannagi_extract.py` · `unity_list.py` · `unity_textasset_dump.py` |
| `meiji-haikara-lzs.md` | 自研 .lzs ＋ SCD コマンド列 | `meiji_extract.py` · `meiji_lzs.py` |
| `misc-engines.md` | 其它自研/小众引擎 | `artemis_pfs_extract.py` · `asakiyumemishi_extract.py` · `asakiyumemishi_psp_extract.py` · `brothers_kiss_extract.py` · `koigig_extract.py` · `nsac.py` · `ouma_build_text.py` · `ouma_extract.py` · `ouma_story.py` · `paradigm_paradox_extract.py` · `tiny_machinegun_extract.py` · `tokihako_extract.py` · `tokitama_extract.py` |
| `musketeer-psp-evb.md` | 引擎：5pb/otome 自研 .evb ＋ MARC ＋ CPK | `cpk.py` · `marc_font.py` · `musketeer_charset.py` · `musketeer_extract.py` |
| `mz-cmdstream.md` | MZ 命令流 | `cpk.py` · `makumatsu_extract.py` |
| `naninovel-unity.md` | Unity＋ Naninovel—— 剧本文本提取 | `naninovel_assemble.py` · `naninovel_extract.py` · `ozmafia_nca.py` · `unity_textasset_dump.py` |
| `nis-cpk-snbin.md` | BROCCOLI×NIS Switch 移植 | `cpk.py` · `nso_x.py` · `nsp_split.py` · `utapri_as_extract.py` |
| `nitroplus.md` | Nitroplus NPA / NSS | `lamento_extract.py` · `npa_nrbf.py` |
| `oni-psp-tob.md` | Idea Factory/Otomate 自研 PSP「oni」引擎 | `oga_sts_extract.py` · `oga_tob_extract.py` |
| `orfre-dcvm.md` | 引擎：dramatic create 自研「Orfre」/ DCVM | `orfleur_extract.py` · `orfleur_stbl_extract.py` |
| `orfre-dcvm-history.md` | orfre-dcvm 探查史—— 仅排障时读 | `orfleur_trace.py` · `orfleur_vm.py` · `pc_snr_order.py` |
| `otomate-evb-marc.md` | 引擎：Otomate 自研 .evb ＋ MARC | `cfm_extract.py` · `iso_cut_cpk.py` · `musketeer_charset.py` |
| `otomate-stcm2l-psp-unioncpk.md` | STCM2L · PSP「UNION.CPK」侧 | `anki_extract.py` · `anki_unpack.py` |
| `planpeace-pct.md` | Plan Peace / InterOne 自研「PCT」——data.dat ＋ pct_mess.dat ＋ script_*.dat | `solomon_extract.py` |
| `platform-psv-pfs.md` | PSV NoNpDrm / PFS | —（无自研脚本：按本册链路自己写；若本册讲的是外部工具链，则直接用那些工具） |
| `platform-switch-bezel-bea-scne.md` | Nintendo「Bezel Engine」＋ .nx.bea 剧本读取 | `bezel_extract.py` · `nsp_plainromfs.py` |
| `platform-switch-bktr.md` | Switch「BKTR」PatchRomFS读取 | `bktr_romfs.py` |
| `platform-switch-nca.md` | Switch XCI / NCA / NSP | `ozmafia_nca.py` · `senjyushi_extract.py` · `switch_nca.py` |
| `prince-stride-d3p.md` | 引擎：D3P 系「CRI CPK ＋ 自建字符集/位图字体」· 他作 —— プリンス・オブ・ストライド | `prince_stride_lt.py` · `prince_stride_run.py` · `stormlover_charset.py` · `vamwolf_lt.py` · `vamwolf_run.py` |
| `rejet-pack-adv.md` | Rejet ADV | —（无自研脚本：按本册链路自己写；若本册讲的是外部工具链，则直接用那些工具） |
| `rom2-snr.md` | ROM2 / SNR | `rom2_extract.py` · `sanzen_extract.py` · `torimari_extract.py` |
| `siglus.md` | SiglusEngine | `siglus_scene_extract.py` |
| `stcm2l-op-census.md` | STCM2L「定 op 五步法」 | —（无自研脚本：按本册链路自己写；若本册讲的是外部工具链，则直接用那些工具） |
| `stormlover-d3p.md` | 引擎：D3P 自研 ADV— STORM LOVER 系列 | `stormlover2_charset.py` · `stormlover2_run.py` · `stormlover_assets.py` · `stormlover_charset.py` · `stormlover_font.py` · `stormlover_run.py` |
| `stormlover-d3p-psp.md` | 引擎：D3P 自建 ADV · **PSP 变体** | `stormlover_natsu_charset.py` · `stormlover_natsu_run.py` · `stormlover_psp_cmp.py` · `stormlover_psp_font.py` |
| `system-nnn.md` | System-NNN—— あさき、ゆめみし 系列 | `asakiyumemishi_extract.py` · `asakiyumemishi_psp_extract.py` · `cpk.py` |
| `takuyo-gss.md` | Takuyo gss | `cafe_extract.py` · `himehibi_crawl.py` · `himehibi_disasm.py` · `himehibi_extract.py` · `himehibi_lsdarc.py` |
| `takuyo-gss-psp.md` | Takuyo gss · PSP 变体 | `etude_extract.py` · `himehibi_disasm.py` · `himehibi_lsdarc.py` |
| `takuyo-gss-psp-hoshiiro.md` | Takuyo gss · PSP 变体 3 | `gss_lsdarc.py` · `himehibi_disasm.py` · `hoshiiro_extract.py` |
| `takuyo-gss-psp-littleaid.md` | Takuyo gss · PSP 变体 2 | `gss_lsdarc.py` · `himehibi_disasm.py` · `littleaid_extract.py` |
| `takuyo-gss-psp-symphony.md` | Takuyo gss · PSP 变体 4 | `fsymph_extract.py` · `gss_lsdarc.py` · `himehibi_disasm.py` |
| `takuyo-gss-switch.md` | Takuyo gss —— Switch 变体 | `gss_codec.py` · `gss_lsdarc.py` · `gss_scr3.py` · `kamikoi_extract.py` · `sweetclown_extract.py` |
| `takuyo-gss-switch-scr2.md` | Takuyo gss —— Switch 变体 · SCR 2.00 | `crazychain_xci.py` · `gss_lsdarc.py` · `himehibi_disasm.py` · `himehibi_lsdarc.py` · `kaeru_extract.py` · `sorayume_extract.py` |
| `thfs-mizu.md` | KID 自研 THFS 归档 ＋ % 控制码脚本 | `mizu2_extract.py` · `mizu_extract.py` |
| `unity-adv.md` | Unity + 自研 ADV | `akuyaku_extract.py` · `heiligenstadt_extract.py` · `psarc_extract.py` · `senjyushi_extract.py` · `senjyushi_extract_text.py` · `switch_nca.py` · `verite_extract.py` |
| `unity-adv-hscript.md` | Unity  + 自研 ADV · **纯文本脚本变体** | `crazychain_extract.py` · `crazychain_xci.py` |
| `unity-text-carriers.md` | Unity文本载体速查 —— 2026-10-25/26 批实测 6 型 | `dd_utage.py` · `honeyvibes_extract.py` · `neon_dialog.py` · `redbell_dialog.py` · `utage_extract.py` |
| `vsc-vdp-lsb.md` | VSC · VDP 容器 + LSB 脚本 | `build_ls2.py` · `lsb.py` · `vdp.py` |
| `vsc-vl-file-tml.md` | VSC · vl_file | `roman_extract.py` · `roman_vl.py` |
| `willplus-advhd.md` | WillPlus / AdvHD | `advhd.py` · `bgloss_extract.py` · `blip_extract.py` · `brouge_extract.py` |
| `zerodiv-cpk-extra-files.md` | Zerodiv 自研 ADV —— CPK 内 event.enc **之外**的文件 | `cpk.py` · `lzo1x.py` · `termdict_extract.py` · `urakata_extract.py` |
| `zerodiv-lzo1x.md` | Zerodiv 自研 ADV—— 裏語 薄桜鬼 系 | `cpk.py` · `lzo1x.py` · `urakata_extract.py` |
| `zerodiv-talks-variant.md` | Zerodiv 自研 ADV —— **台詞バリアント機構** | `vn_zerodiv_extract.py` |

## 二、想查「某个 py 是干什么的」

全部 585 个脚本的用途（含**没有**引擎册引用的 355 个）在 [`INDEX-BY-SCRIPT.md`](INDEX-BY-SCRIPT.md)：一行一个，字母序，可直接 grep。
