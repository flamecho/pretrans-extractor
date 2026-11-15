# 引擎 → 可复用脚本

> 构建时由格式册的通用工具引用和已有工具、作品记录生成。
>
> 用法：`references/identify.md` 命中引擎 → 打开 `references/engines/<slug>.md`
> 核对容器、记录与版本 → 查本表和 by-script.md 的工具说明 → 选择匹配实现。
> 通用工具（判型 / 探查 / 品检 / 收尾）见 `index.md`，本表不重复。

## 一、按引擎（命中后从这一行开始）

| 格式册 | 引擎或格式 | 关联脚本 |
|---|---|---|
| [3daisy-scrvita](../references/engines/3daisy-scrvita.md) | 3Daisy · SCRVITA / TBL / PAK | —（未关联；查 by-script.md 或已有工具记录） |
| [advhd-wsc](../references/engines/advhd-wsc.md) | WillPlus / AdvHD · WSC | —（未关联；查 by-script.md 或已有工具记录） |
| [air-woga](../references/engines/air-woga.md) | Adobe AIR / woga · DAT 与 WAS | —（未关联；查 by-script.md 或已有工具记录） |
| [arc0-mlk-adv](../references/engines/arc0-mlk-adv.md) | ARC0 / MLK · ADV 文本脚本 | —（未关联；查 by-script.md 或已有工具记录） |
| [aromarie-atl](../references/engines/aromarie-atl.md) | Aromarie ATL · SQLite 剧本 | —（未关联；查 by-script.md 或已有工具记录） |
| [artemis](../references/engines/artemis.md) | Artemis · PF 与标签脚本 | `artemis_pfs_extract.py` |
| [asgard-tat](../references/engines/asgard-tat.md) | ASGARD · TAT 脚本 | —（未关联；查 by-script.md 或已有工具记录） |
| [avg32](../references/engines/avg32.md) | AVG32 | `rl_decomp.py` · `rl_parse.py` · `siesta_avg32.py` |
| [bezel-bea](../references/engines/bezel-bea.md) | Bezel · BEA / SCNE / SCB | `bea_scne_extract.py` · `bezel_scb_lib.py` · `gs2_scb_extract.py` · `hatsukoi_extract.py` · `hoshioji_extract.py` · `scandal_extract.py` · `struct_probe.py` · `subordinate2ldk_extract.py` |
| [bgi](../references/engines/bgi.md) | BGI · ARC 与脚本 | —（未关联；查 by-script.md 或已有工具记录） |
| [blueimpact-bsf1](../references/engines/blueimpact-bsf1.md) | BlueImpact · BSF1 | —（未关联；查 by-script.md 或已有工具记录） |
| [broccoli-opfflow](../references/engines/broccoli-opfflow.md) | Broccoli · OPF 指令流 | —（未关联；查 by-script.md 或已有工具记录） |
| [cri-archives](../references/engines/cri-archives.md) | CRI · CPK / AFS | `cpk.py` · `cpk_v1.py` |
| [d3p-code16](../references/engines/d3p-code16.md) | D3P / Vridge · 双字节码流 | —（未关联；查 by-script.md 或已有工具记录） |
| [daisy2-ddp](../references/engines/daisy2-ddp.md) | Daisy2 · DDP2 / DDP3 | `sgs_kai_ddp.py` |
| [dat-pak-scd](../references/engines/dat-pak-scd.md) | DAT / PAK / SCD | `cpk.py` · `cpk_v1.py` · `dl_df_extract.py` · `fortissimo_extract.py` · `gakuenk_extract.py` · `le_extract.py` · `lp_extract.py` · `marginal4_extract.py` · `marginal4rtg_extract.py` · `psycemo6_extract.py` · `rootrexx_extract.py` · `vc_extract.py` |
| [dcvm](../references/engines/dcvm.md) | ROFS / DCVM | `orfleur_extract.py` · `pc_snr_order.py` |
| [ddengine](../references/engines/ddengine.md) | DDEngine · DDP0 / DDP1 | —（未关联；查 by-script.md 或已有工具记录） |
| [director](../references/engines/director.md) | Director · Afterburner | —（未关联；查 by-script.md 或已有工具记录） |
| [evb-marc](../references/engines/evb-marc.md) | EVB / MARC | —（未关联；查 by-script.md 或已有工具记录） |
| [fpk-vml](../references/engines/fpk-vml.md) | FPK / VML | —（未关联；查 by-script.md 或已有工具记录） |
| [gswin](../references/engines/gswin.md) | GsWin · DataPack5 / SCW | —（未关联；查 by-script.md 或已有工具记录） |
| [himauri](../references/engines/himauri.md) | Himauri · HXP / HIM | `angelfeather_extract.py` · `angelknight_ssb.py` · `anotherrewind_extract.py` · `boiz_extract.py` · `boiz_unpack.py` · `ddengine_text.py` · `director_d8_text.py` · `director_dsl_text.py` · `director_rifx_xmed.py` · `director_xmed_dsl.py` · `director_xmed_text.py` · `dl_ge_extract.py` · `himpac.py` · `himscript.py` · `ks_kag_text.py` · `livemaker_extract.py` · `livemaker_sugar.py` · `luckydog_extract.py` · `ns_dual.py` · `ns_extract.py` · `ns_talkbmp_text.py` · `ojisama_extract.py` · `petitfleur_text.py` · `pleasure_text.py` · `requartz_pc_text.py` · `rq_extract.py` · `saisys_ssb_text.py` · `sco_vm_text.py` · `slg_system_sd.py` · `sugar_audit_all.py` · `tlz_liam_text.py` · `tmr_srp.py` · `tmrpac.py` · `will_rio_arc.py` |
| [hunex-als](../references/engines/hunex-als.md) | HuneX · ALS | `lucianj_extract.py` |
| [hunex-hesl](../references/engines/hunex-hesl.md) | HuneX · HESL / HESE / HDLG | `believer_extract.py` · `kaleido_extract.py` · `majikyun_extract.py` · `vxdst_extract.py` |
| [hunex-ika](../references/engines/hunex-ika.md) | HuneX · HFU2 / IKA SEQ | `lucian_extract.py` · `lucianj_extract.py` · `lucianv_extract.py` · `realrode_extract.py` · `vitaminb6_extract.py` · `vitaminx_ep_extract.py` · `vitaminxz_extract.py` · `vitz_extract.py` · `vzgrad_extract.py` |
| [hunex-ogre](../references/engines/hunex-ogre.md) | HuneX Ogre · MRG / MZX0 | —（未关联；查 by-script.md 或已有工具记录） |
| [idea-factory-ydp-lsb](../references/engines/idea-factory-ydp-lsb.md) | YDP1 / LSB | `kanuchi_dict.py` · `kanuchi_text.py` · `kanuchi_ydp.py` |
| [images](../references/engines/images.md) | CHD 与原始光盘镜像 | `ccdimg.py` |
| [karin-adv-asb](../references/engines/karin-adv-asb.md) | Karin ADV · ASB | —（未关联；查 by-script.md 或已有工具记录） |
| [kid-cp932](../references/engines/kid-cp932.md) | KID · CP932 文本与控制码 | —（未关联；查 by-script.md 或已有工具记录） |
| [kirikiri](../references/engines/kirikiri.md) | KiriKiri · XP3 / KAG | `aim_extract.py` · `ariard_extract.py` · `ariard_xp3.py` · `extract_question.py` · `qualia_extract.py` · `vista_extract.py` · `xp3.py` |
| [koei-cdar](../references/engines/koei-cdar.md) | Koei · CDAR | `cdar_extract.py` |
| [koei-embins-ps2](../references/engines/koei-embins-ps2.md) | Koei · EMB / INS | `build_text.py` · `cd_bin2iso.py` · `fpk.py` · `fpkx.py` · `hanayoi_extract.py` · `l2ll_extract.py` · `lastescort_vml.py` · `paradise_jp_extract.py` · `paradise_musubi_extract.py` · `sgs_kai_ddp.py` · `trois_text.py` |
| [koei-pack-ps2](../references/engines/koei-pack-ps2.md) | Koei · PACK | —（未关联；查 by-script.md 或已有工具记录） |
| [koei-pasc](../references/engines/koei-pasc.md) | Koei · PASC | —（未关联；查 by-script.md 或已有工具记录） |
| [kogado-gcore](../references/engines/kogado-gcore.md) | Kogado · GCore | —（未关联；查 by-script.md 或已有工具记录） |
| [livemaker](../references/engines/livemaker.md) | LiveMaker · VF / LSB / TpWord | `angelfeather_extract.py` · `angelknight_ssb.py` · `anotherrewind_extract.py` · `boiz_extract.py` · `boiz_unpack.py` · `ddengine_text.py` · `director_d8_text.py` · `director_dsl_text.py` · `director_rifx_xmed.py` · `director_xmed_dsl.py` · `director_xmed_text.py` · `dl_ge_extract.py` · `himpac.py` · `himscript.py` · `ks_kag_text.py` · `livemaker_extract.py` · `livemaker_sugar.py` · `luckydog_extract.py` · `ns_dual.py` · `ns_extract.py` · `ns_talkbmp_text.py` · `ojisama_extract.py` · `petitfleur_text.py` · `pleasure_text.py` · `requartz_pc_text.py` · `rq_extract.py` · `saisys_ssb_text.py` · `sco_vm_text.py` · `slg_system_sd.py` · `sugar_audit_all.py` · `tlz_liam_text.py` · `tmr_srp.py` · `tmrpac.py` · `will_rio_arc.py` |
| [lovepeace-adv](../references/engines/lovepeace-adv.md) | LovePeace ADV | —（未关联；查 by-script.md 或已有工具记录） |
| [lte](../references/engines/lte.md) | LTE | —（未关联；查 by-script.md 或已有工具记录） |
| [lzs-scd](../references/engines/lzs-scd.md) | LZS / SCD | `hy_extract.py` · `meiji_lzs.py` · `mn_extract.py` |
| [m2-psb](../references/engines/m2-psb.md) | M2 · PSB / MDF | —（未关联；查 by-script.md 或已有工具记录） |
| [mages-sc3](../references/engines/mages-sc3.md) | MAGES · MPK / SC3 | —（未关联；查 by-script.md 或已有工具记录） |
| [malie](../references/engines/malie.md) | Malie | `malie_extract.py` |
| [mnp](../references/engines/mnp.md) | MNP · ARC! / MMA | —（未关联；查 by-script.md 或已有工具记录） |
| [monoceros](../references/engines/monoceros.md) | Monoceros | —（未关联；查 by-script.md 或已有工具记录） |
| [mz-cmdstream](../references/engines/mz-cmdstream.md) | MZ 命令流 | —（未关联；查 by-script.md 或已有工具记录） |
| [naninovel](../references/engines/naninovel.md) | Naninovel | `advhd.py` · `akuyaku_extract.py` · `angelpop_extract.py` · `angelpop_xp3.py` · `asakiyumemishi_extract.py` · `baccan_extract.py` · `believer_extract.py` · `bgloss_extract.py` · `blip_extract.py` · `brothers_kiss_extract.py` · `brouge_extract.py` · `cafe_extract.py` · `crankin_extract.py` · `crimson_royale_extract.py` · `epic_extract.py` · `euchronia_trail_extract.py` · `foris_pack.py` · `foris_script_xml.py` · `fortissimo_extract.py` · `geten_extract.py` · `gss_codec.py` · `gss_lsdarc.py` · `gss_scr3.py` · `haruka2_appmatrix.py` · `haruka2_eemlib.py` · `haruka6_dedup.py` · `haruka6_dict.py` · `heiligenstadt_extract.py` · `jusanshi.py` · `kaleido_extract.py` · `kamikoi_extract.py` · `kamisama_extract.py` · `kazahanaki_extract.py` · `koigig_extract.py` · `lamento_extract.py` · `majikyun_extract.py` · `mysteria_extract.py` · `mysteria_text.py` · `naninovel_assemble.py` · `naninovel_extract.py` · `neon_dialog.py` · `norn9_extract.py` · `npa_nrbf.py` · `pandora_extract.py` · `paradigm_paradox_extract.py` · `possession_extract.py` · `prince_stride_lt.py` · `prince_stride_run.py` · `psycemo6_extract.py` · `radian_split.py` · `rear_extract.py` · `redbell_dialog.py` · `revice_extract.py` · `rom2_extract.py` · `rootrexx_extract.py` · `rt2_extract.py` · `sanzen_extract.py` · `sgs_kai_ddp.py` · `sgs_kai_extract.py` · `shinoda_botan_extract.py` · `siglus_scene_extract.py` · `snowboundland_extract.py` · `stc_extract.py` · `stcm2l_extract.py` · `stride_extract.py` · `tiny_machinegun_extract.py` · `tokihako_extract.py` · `tokitama_extract.py` · `torimari_extract.py` · `tsundere_extract.py` · `ukronia_extract.py` · `unity_scriptdatas_text.py` · `valpurga_extract.py` · `virche_extract.py` · `virche_xci.py` · `vn_zerodiv_extract.py` · `yuris_allout_extract.py` · `yuris_ypf.py` · `yuris_ystb.py` |
| [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) | SN.BIN · 记录流与 LZSS | `artemis_pfs_extract.py` · `bktr_romfs.py` · `cdar.py` · `cdar_extract.py` · `cpk.py` · `cpk_cri.py` · `cpk_v1.py` · `crazychain_xci.py` · `crimson_royale_extract.py` · `dcgs_extract.py` · `extract_alice.py` · `extract_text.py` · `fortissimo_extract.py` · `heiligenstadt_extract.py` · `iso_cut_cpk.py` · `kaleido_extract.py` · `l2ll_extract.py` · `libp_malievita.py` · `malie_extract.py` · `meiji_extract.py` · `meiji_lzs.py` · `ns_open.py` · `nsac.py` · `nsp_split.py` · `ouma_build_text.py` · `ouma_extract.py` · `ouma_story.py` · `pandora_extract.py` · `period55.py` · `psarc_extract.py` · `psvskip_patch.py` · `qpk.py` · `rom2_extract.py` · `run_alice.py` · `stcm2l_extract.py` · `termdict_extract.py` · `utapri_rl_ns_extract.py` · `verite_extract.py` · `xci_hfs0.py` · `xp3.py` |
| [nis-nml](../references/engines/nis-nml.md) | NIS · NSAC / NML | `nsac.py` |
| [nitroplus](../references/engines/nitroplus.md) | Nitroplus · NPA / NSS / NPK3 | —（未关联；查 by-script.md 或已有工具记录） |
| [nk-paf-pscb](../references/engines/nk-paf-pscb.md) | NK / PAF / PSCB | —（未关联；查 by-script.md 或已有工具记录） |
| [nscripter](../references/engines/nscripter.md) | NScripter | —（未关联；查 by-script.md 或已有工具记录） |
| [otomate-sscn](../references/engines/otomate-sscn.md) | Otomate · SSCN | `nca_stream_romfs.py` · `sc7_extract.py` |
| [otomate-tatc-rson](../references/engines/otomate-tatc-rson.md) | TATC / RSON | `mtj_extract.py` |
| [overflow-adv](../references/engines/overflow-adv.md) | OverFlow ADV | `ccdimg.py` · `director_stxt_text.py` · `entis_arc.py` · `entis_sx.py` · `mdb_scen_text.py` · `ofadv_script.py` · `oni_xci_nca.py` · `overreq_extract.py` · `swf_definetext_text.py` |
| [pack-yox](../references/engines/pack-yox.md) | PACK / YOX | `srxfd_extract.py` · `vitaminr_extract.py` |
| [planpeace-pct](../references/engines/planpeace-pct.md) | PlanPeace · PCT | —（未关联；查 by-script.md 或已有工具记录） |
| [reallive](../references/engines/reallive.md) | RealLive | —（未关联；查 by-script.md 或已有工具记录） |
| [regista](../references/engines/regista.md) | Regista · ScrPack | —（未关联；查 by-script.md 或已有工具记录） |
| [rom2](../references/engines/rom2.md) | ROM2 | `hg_extract.py` · `rom2_extract.py` |
| [rpgmaker](../references/engines/rpgmaker.md) | RPG Maker | —（未关联；查 by-script.md 或已有工具记录） |
| [saisys](../references/engines/saisys.md) | Saisys | —（未关联；查 by-script.md 或已有工具记录） |
| [sandaldash-rk1](../references/engines/sandaldash-rk1.md) | SandalDash · RK1 | —（未关联；查 by-script.md 或已有工具记录） |
| [scenario-kun](../references/engines/scenario-kun.md) | Scenario Kun | —（未关联；查 by-script.md 或已有工具记录） |
| [selfpak-utf16-vm](../references/engines/selfpak-utf16-vm.md) | SelfPAK · UTF-16 VM | `nsp_nca_romfs.py` · `sgk_extract.py` · `sgs_heiho_extract.py` · `struct_probe.py` · `taisho_ht_extract.py` · `taisho_pak_extract.py` |
| [siglus](../references/engines/siglus.md) | Siglus | —（未关联；查 by-script.md 或已有工具记录） |
| [spt](../references/engines/spt.md) | 混合编码 SPT | —（未关联；查 by-script.md 或已有工具记录） |
| [stcm2l](../references/engines/stcm2l.md) | STCM2 / STCM2L | `advhd.py` · `akuyaku_extract.py` · `amennoir_extract.py` · `angelfeather_extract.py` · `angelknight_ssb.py` · `angelpop_extract.py` · `angelpop_xp3.py` · `anotherrewind_extract.py` · `arcobaleno_extract.py` · `asakiyumemishi_extract.py` · `baccan_extract.py` · `believer_extract.py` · `bgloss_extract.py` · `blip_extract.py` · `boiz_extract.py` · `boiz_unpack.py` · `brothers_kiss_extract.py` · `brouge_extract.py` · `bwolves_extract.py` · `cafe_extract.py` · `cpk.py` · `cpk_v1.py` · `cr_dict.py` · `cr_extract.py` · `crankin_extract.py` · `crazychain_xci.py` · `crimson_royale_extract.py` · `cxm_extract.py` · `cxm_stream.py` · `ddengine_text.py` · `director_d8_text.py` · `director_dsl_text.py` · `director_rifx_xmed.py` · `director_xmed_dsl.py` · `director_xmed_text.py` · `dl_ge_extract.py` · `dlcl_extract.py` · `epic_extract.py` · `euchronia_trail_extract.py` · `foris_pack.py` · `foris_script_xml.py` · `fortissimo_extract.py` · `garnet_extract.py` · `geten_extract.py` · `gss_codec.py` · `gss_lsdarc.py` · `gss_scr3.py` · `hakuoki_kf_extract.py` · `haruka2_appmatrix.py` · `haruka2_eemlib.py` · `haruka6_dedup.py` · `haruka6_dict.py` · `heiligenstadt_extract.py` · `himpac.py` · `himscript.py` · `iso9660.py` · `jewelic_extract.py` · `jusanshi.py` · `kaleido_extract.py` · `kamikoi_extract.py` · `kamisama_extract.py` · `kannou_extract.py` · `kazahanaki_extract.py` · `koibann2_extract.py` · `koibann_extract.py` · `koigig_extract.py` · `ks_kag_text.py` · `lamento_extract.py` · `lf_probe_slots.py` · `livemaker_extract.py` · `livemaker_sugar.py` · `lpv_extract_final.py` · `lpv_stream.py` · `lpv_walk.py` · `luckydog_extract.py` · `majikyun_extract.py` · `minus8_extract.py` · `musketeer_charset.py` · `musketeer_extract.py` · `mysteria_extract.py` · `mysteria_text.py` · `naninovel_assemble.py` · `naninovel_extract.py` · `nca_romfs.py` · `neon_dialog.py` · `niladmirari_extract.py` · `nisenochigiri_extract.py` · `nisenochigiri_fd_extract.py` · `norn9_extract.py` · `npa_nrbf.py` · `ns_dual.py` · `ns_extract.py` · `ns_talkbmp_text.py` · `nsp_nca_romfs.py` · `oga_sts_extract.py` · `ojisama_extract.py` · `ol_extract.py` · `oni_extract.py` · `oni_xci_nca.py` · `os_extract.py` · `pandora_extract.py` · `paradigm_paradox_extract.py` · `pe_extract.py` · `petitfleur_text.py` · `pf_extract.py` · `pleasure_text.py` · `possession_extract.py` · `prince_stride_lt.py` · `prince_stride_run.py` · `psycemo6_extract.py` · `radian_extract.py` · `radian_split.py` · `rdf_extract.py` · `rear_extract.py` · `redbell_dialog.py` · `requartz_pc_text.py` · `revice_extract.py` · `rip9_extract.py` · `rip9seq_extract.py` · `rom2_extract.py` · `rootrexx_extract.py` · `rq_extract.py` · `rt2_extract.py` · `saisys_ssb_text.py` · `sanzen_extract.py` · `sco_vm_text.py` · `sgs_kai_ddp.py` · `sgs_kai_extract.py` · `shinoda_botan_extract.py` · `siglus_scene_extract.py` · `slg_system_sd.py` · `snowboundland_extract.py` · `ssl_extract.py` · `stcm2l_extract.py` · `stride_extract.py` · `struct_probe.py` · `sugar_audit_all.py` · `tiny_machinegun_extract.py` · `tlz_liam_text.py` · `tmr_srp.py` · `tmrpac.py` · `tokihako_extract.py` · `tokitama_extract.py` · `torimari_extract.py` · `tsundere_extract.py` · `ukronia_extract.py` · `unity_scriptdatas_text.py` · `valpurga_extract.py` · `virche_extract.py` · `virche_xci.py` · `vn_zerodiv_extract.py` · `will_rio_arc.py` · `xci_hfs0.py` · `xci_romfs.py` · `yuris_allout_extract.py` · `yuris_ypf.py` · `yuris_ystb.py` |
| [swallowtail-fpk-spt](../references/engines/swallowtail-fpk-spt.md) | Swallowtail · FPK / SPT / ACT | —（未关联；查 by-script.md 或已有工具记录） |
| [system-nnn](../references/engines/system-nnn.md) | System-NNN · SPT | —（未关联；查 by-script.md 或已有工具记录） |
| [takuyo-gss](../references/engines/takuyo-gss.md) | Takuyo · LSDARC / SCR | —（未关联；查 by-script.md 或已有工具记录） |
| [text-mode-adv](../references/engines/text-mode-adv.md) | 文本方式 ADV | —（未关联；查 by-script.md 或已有工具记录） |
| [thfs](../references/engines/thfs.md) | THFS | `mizu2_extract.py` |
| [tmr-hiro](../references/engines/tmr-hiro.md) | TMR-Hiro ADV | `angelfeather_extract.py` · `angelknight_ssb.py` · `anotherrewind_extract.py` · `boiz_extract.py` · `boiz_unpack.py` · `ddengine_text.py` · `director_d8_text.py` · `director_dsl_text.py` · `director_rifx_xmed.py` · `director_xmed_dsl.py` · `director_xmed_text.py` · `dl_ge_extract.py` · `himpac.py` · `himscript.py` · `ks_kag_text.py` · `livemaker_extract.py` · `livemaker_sugar.py` · `luckydog_extract.py` · `ns_dual.py` · `ns_extract.py` · `ns_talkbmp_text.py` · `ojisama_extract.py` · `petitfleur_text.py` · `pleasure_text.py` · `requartz_pc_text.py` · `rq_extract.py` · `saisys_ssb_text.py` · `sco_vm_text.py` · `slg_system_sd.py` · `sugar_audit_all.py` · `tlz_liam_text.py` · `tmr_srp.py` · `tmrpac.py` · `will_rio_arc.py` |
| [tob-dsarc](../references/engines/tob-dsarc.md) | TOB / PSPFS / DSARC | —（未关联；查 by-script.md 或已有工具记录） |
| [unity](../references/engines/unity.md) | Unity · 资源与脚本格式 | `busta_extract.py` · `cpk.py` · `dd_utage.py` · `hb_extract.py` · `kamigami_scr_extract.py` · `mem_scan.py` · `nsp_nca_romfs.py` · `oni_xci_nca.py` · `overreq_extract.py` · `sk_extract.py` · `struct_probe.py` · `uma_boxes.py` · `uma_dec.py` · `uma_extract_final.py` · `uma_extract_v5.py` · `uma_extract_v6.py` · `uma_rowfit.py` · `uma_wrap.py` · `unity_scriptdatas_text.py` |
| [vfs3-pak](../references/engines/vfs3-pak.md) | VFS3 / PAK | `mk2_extract.py` · `mk3_extract.py` · `mk_extract.py` · `rhapsody_vfs.py` |
| [vividcolor](../references/engines/vividcolor.md) | VividColor · COM / CMP | `pack_cmp.py` · `sc2003_extract.py` · `scfb_extract.py` · `yuuki_pkg.py` |
| [vridge](../references/engines/vridge.md) | Vridge · MEMFS / TAT | `bir_base_extract.py` · `matsurika_extract.py` · `nsp_nca_romfs.py` |
| [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) | VSC · VDP / LSB | `vdp.py` |
| [vsc-vl-file-tml](../references/engines/vsc-vl-file-tml.md) | VSC · PAC / TML | —（未关联；查 by-script.md 或已有工具记录） |
| [will-arcg](../references/engines/will-arcg.md) | Will · ARCG / TLV | —（未关联；查 by-script.md 或已有工具记录） |
| [xfl-gsc](../references/engines/xfl-gsc.md) | XFL / GSC | —（未关联；查 by-script.md 或已有工具记录） |
| [ykc-yks](../references/engines/ykc-yks.md) | YKC / YKS | —（未关联；查 by-script.md 或已有工具记录） |
| [yuris-ypf](../references/engines/yuris-ypf.md) | YU-RIS · YPF / YSTB | —（未关联；查 by-script.md 或已有工具记录） |
| [yuuki-novel](../references/engines/yuuki-novel.md) | Yuuki! Novel | `pack_cmp.py` · `sc2003_extract.py` · `scfb_extract.py` · `yuuki_pkg.py` |
| [zerodiv](../references/engines/zerodiv.md) | Zerodiv | —（未关联；查 by-script.md 或已有工具记录） |

## 二、想查「某个 py 是干什么的」

全部 964 个脚本的用途（含**没有**引擎册引用的 685 个）在 [`by-script.md`](by-script.md)：一行一个，字母序，可直接 grep。
