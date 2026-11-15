# 作品专用脚本

仅收录解包和最终文本提取入口。适用作品及平台按已确认记录标注；运行前核对资源版本和参数。
通用工具见 [index.md](index.md)，按格式选择见 [by-engine.md](by-engine.md)，必要解析依赖见 [_lib/index.md](_lib/index.md)。

## 解包（95 个）

| 脚本 | 适用作品 | 用途 | 关联格式 |
|---|---|---|---|
| [agastar_unpack.cjs](agastar_unpack.cjs) | アガスターシェルゴサ（PC） | Electron ASAR 资源解包 | — |
| [akasuna_pc_nsa.py](akasuna_pc_nsa.py) | 赤い砂堕ちる月（PC） | NScripter NSA (arc.nsa) 解包 —— 赤い砂堕ちる月 PC 版。 | — |
| [angelpop_xp3.py](angelpop_xp3.py) | Angel ★ Pop（PC） · Ariard-少年アリス - Under the rose | [JP]Angel ★ Pop  data.xp3 索引解析 / 抽取 | — |
| [anki_unpack.py](anki_unpack.py) | アンジェリーク 魔恋の六騎士（PSP） | アンジェリーク 魔恋の六騎士 (PSP/ULJM05986) UNION.CPK 解包 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [ariard_xp3.py](ariard_xp3.py) | Ariard-少年アリス - Under the rose（PC） · Ariard-少年アリス-（PC） · CHOICE | [JP]Ariard-少年アリス - Under the rose  data.xp3 解析 / 抽取 | [kirikiri](../references/engines/kirikiri.md) |
| [blackish_nca.py](blackish_nca.py) | Blackish House sideA（Switch） · 泡沫のユークロニア（Switch） | Blackish House sideA-> -Retour- (NS) 压缩 NCA（LZ4 桶树）解包。 | — |
| [boiz_unpack.py](boiz_unpack.py) | ♂ボ～イズ！！～イケメン陵辱パラダイス～ | [JP]♂ボ～イズ！！～イケメン陵辱パラダイス～  NPA 解包 | — |
| [btf_carve.py](btf_carve.py) | Beyond The Future -Fix The Time Arrows-（PSP） · Beyond The Future -Fix The Time Arrows-（MAGES.×Rejet / M（PSP） | 从 INSTALL.BIN 中按 fileinfo.psb.m.json 的 umd_root 表切出成员文件。 | — |
| [btf_mdf.py](btf_mdf.py) | Beyond The Future -Fix The Time Arrows-（PSP） · Beyond The Future -Fix The Time Arrows-（MAGES.×Rejet / M（PSP） · いざ、出陣！恋戦 第二幕 甲斐編（PSP） · いざ、出陣！恋戦 第二幕 越後編（PSP） | M2 PSB 的 MDF(MT19937) 外壳解密（PSP 版 Kaleido/ADVENGINE）。 | — |
| [btf_pgd.py](btf_pgd.py) | Beyond The Future -Fix The Time Arrows-（PSP） · Beyond The Future -Fix The Time Arrows-（MAGES.×Rejet / M（PSP） · 青春はじめました！A（PSP） | PSP PGD（\0PGD / drm_type=1 / mac_type=1）解密。 | — |
| [btf_unpack.py](btf_unpack.py) | Beyond The Future -Fix The Time Arrows-（PSP） · Beyond The Future -Fix The Time Arrows-（MAGES.×Rejet / M（PSP） | M2「ADVENGINE」PSB 盘 一键解包（PGD → 成员 → MDF → PSB）。 | — |
| [ccdimg.py](ccdimg.py) | 24時、君のハートは盗まれる～怪盗ジェイド～（PC） · Angel Knight（PC） · Apocripha0 Fanbox Happiness Cage（PC） · Apocripha0 アレクディスク · bois ～機械じかけの街～ · bois～機械じかけの街～外伝 呪縛の刻印 · D.Zone · DALLY DASH! · Dolly Night · DRAGEE～てんしのたまご～ · Dual Colors · EverLoyalty ～永遠の忠誠～ · GAME S.S.D.S. ～刹那の英雄～ · Live x Evil 熱砂のプロメテウス · S-Tripper · Wings Innocent | CloneCD / raw-2352 光盘镜像 → ISO9660 目录树 list / extract（不落整盘 ISO 副本）。 | [images](../references/engines/images.md) · [overflow-adv](../references/engines/overflow-adv.md) |
| [chd_iso.py](chd_iso.py) | いっしょにごはん。（PSP） · エルクローネのアトリエ（PSP） · キミカレ（PSP） · マザーグースの秘密の館（PSP） | CHD v5 (zstd/lzma/none) -> 2048B/扇区裸 ISO，无 chdman 依赖。 | — |
| [clep_lzss.py](clep_lzss.py) | クレプシドラ～光と影の十字架～（硬盘版）（PC） | クレプシドラ ARC2 + LZSS 解压器 | — |
| [clonecd_iso.py](clonecd_iso.py) | Silver Chaos Fan Box -Eternal Fantasia- | CloneCD / 裸镜像 → ISO9660 目录树（支持 raw-2352 MODE1 与 2048 纯数据） | — |
| [corda_2fa_unpack.py](corda_2fa_unpack.py) | 金色のコルダ2f アンコール（PSP） | 金色のコルダ2f アンコール (PSP) CDAR v4 解包器. | — |
| [corda_psp_unpack.py](corda_psp_unpack.py) | 金色のコルダ（PSP） | 金色のコルダ (PSP) 容器解包 : ISO9660 -> CDVDAR.DAR (Koei CDAR v2) -> 嵌套 DAR | — |
| [cpk_cri.py](cpk_cri.py) | うたの☆プリンスさまっ♪ Repeat LOVE for Nintendo Switch（Switch） · 終遠のヴィルシュ -EpiClycoris-（Switch） | CRI CPK (@UTF) 容器读取器 —— 最小可用实现（实测格式）。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [crazychain_xci.py](crazychain_xci.py) | CRAZY CHA!N -エルピスの鎖-（Switch） · Glass Heart Princess -for Nintendo Switch-（Switch） · Glass Heart Princess for Nintendo Switch（Switch） · ときめきメモリアル Girl's Side 4th Heart（Switch） · ときめきメモリアル Girl's Side 4th Heart for Nintendo Switch（Switch） · カエル畑DEつかまえて☆彡（Switch） · ニル・アドミラリの天秤 色ドリ撫子（Switch） · 燃えよ！ 乙女道士 ～華遊恋語～（Switch） | CRAZY CHA!N -エルピスの鎖- (Switch XCI) → 切出 secure 分区内的 NCA | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [dcode_carve.py](dcode_carve.py) | DistortedCode ―生者の残り香―（Switch） | XCI / NSP → 逐个 NCA 落盘（按 title 目录分），供后续流式取 romfs。 | — |
| [dump_base.py](dump_base.py) | Knight of Lelouch | even if TEMPEST 本体（未压缩 romfs NCA）→ 裸 romfs 镜像（0 = romfs 头）。 | — |
| [dydc_split.py](dydc_split.py) | DYNAMIC CHORD feat.apple-polisher Remaster Edition（Switch） · DYNAMIC CHORD feat.KYOHSO Remaster Edition（Switch） · DYNAMIC CHORD feat.Liar-S Remaster edition（Switch） | XCI → secure 分区 NCA 手切（nsz 还原的 XCI 哈希不被 hactool 接受，故手工走 HFS0 链）。 | — |
| [edema_xp3.py](edema_xp3.py) | Live x Evil 灼熱のエデマ | [JP]Live x Evil 灼熱のエデマ — XP3 读取 + cxdec.tpm 内容层解密 | — |
| [emu_dec.py](emu_dec.py) | アンジェリーク エトワール（PS2） | 用 unicorn 模拟执行 SLPM 里的解压函数（0x142c80 = type1, 0x142a20 = type2） | — |
| [entis_arc.py](entis_arc.py) | GIGOLO（PC） | Entis / EMSAC-Binary Archive-2  (gigolo.arc, *.arc of Entis GLS titles) | [overflow-adv](../references/engines/overflow-adv.md) |
| [etoile_houteishiki_decode.py](etoile_houteishiki_decode.py) | エトワールの方程式 | reusable decoder for 《エトワールの方程式》(clearcolor, 2004) script. | — |
| [etoile_script.py](etoile_script.py) | アンジェリーク エトワール（PS2） | アンジェリーク エトワール (PS2) DATA02 脚本解包 | — |
| [etoile_script_par.py](etoile_script_par.py) | アンジェリーク エトワール（PS2） | DATA02 脚本解包（多进程版） | — |
| [etoile_unpack.py](etoile_unpack.py) | アンジェリーク エトワール（PS2） | アンジェリーク エトワール (PS2, SLPM_657.15, 2004 Koei/Ruby Party) 归档解包器 | — |
| [euchronia_trail_nca.py](euchronia_trail_nca.py) | 泡沫のユークロニア -trail-（Switch） | Blackish House sideA-> -Retour- (NS) 压缩 NCA（LZ4 桶树）解包。 | — |
| [foris_pack.py](foris_pack.py) | GAME S.S.D.S. ～刹那の英雄～ | FORIS-OS（0verflow 系／S.S.D.S. 等）PACK（*.CMP）解包器。 | — |
| [fpkx.py](fpkx.py) | うるるんクエスト 恋遊記（PS2） · ラスト・エスコート 〜黒蝶スペシャルナイト〜 | FPK 解包（可给外部索引只取指定条目；重名自动加序号，不覆盖）。 | — |
| [garnet_pc_pak.py](garnet_pc_pak.py) | GARNET CRADLE（PC） · GARNET CRADLE Sugary Sparkle（PC） | GsWin / DataPack5 (Takuyo PC) —— .pak 解包 + Scw5.x 脚本解码。 | — |
| [glasu_extract.py](glasu_extract.py) | 硝子の森（PS2） | 硝子の森 (PS2-JP / D3PUBLISHER SIMPLE2000 Vol.13 / HuneX "ebf") 容器 + LZSS | — |
| [hakushaku_afs.py](hakushaku_afs.py) | モノクローム・ファクター cross road（PS2） · 伯爵と妖精 ～夢と絆に想いを馳せて～（PS2） | CRI AFS (\x00SFA) minimal extractor for 5pb PS2 titles. | — |
| [hanayoi_afs.py](hanayoi_afs.py) | スキップ・ビート！（PS2） · 花宵ロマネスク · 花宵ロマネスク PS2（SLPS_258.67 / Marvelous×Vridge）（PS2） · 花宵ロマネスク 愛と哀しみ -それは君のためのアリア | AFS0（AFS\x00）归档索引解析：条目偏移/大小 → 取数据。 | — |
| [handsome_nca.py](handsome_nca.py) | ハンサムロンダリング -the mystic lover-（Switch） | ハンサムロンダリング -the mystic lover- (NS) 压缩 NCA（LZ4 桶树）解包。 | — |
| [handsome_updraw.py](handsome_updraw.py) | ハンサムロンダリング | ハンサムロンダリング 更新档（BKTR + LZ4 桶树）→ 最新 romfs 文件比对/提取。 | — |
| [hws_dpmx.py](hws_dpmx.py) | Hunks Workshop | HWS（Hunks Workshop! / エフジー）DPMX 容器解包。 | — |
| [iso9660.py](iso9660.py) | Blackish House sideA（PC） · Blackish House ←sideZ（PC） · DEAR My SUN!!～ムスコ★育成★狂騒曲～（PS2） · Dessert Love -Sweet Plus-（PS2） · Double Score ～Cattleya×Narcissus～（PC） · Double Score ～Cosmos×Camellia～（PC） · Double Score ～Marguerite×Tulip～（PC） · drastic Killer（PS2） · DYNAMIC CHORD feat.KYOHSO Append Disc（PC） · DYNAMIC CHORD feat.Liar-S Append Disc（PC） · NANA -ナナ-（PS2） · Silver Chaos Fan Box -Eternal Fantasia- · Under the Moon ～クレセント～（PS2） · unENDing Bloody Call · 『っポイ!』ひと夏の経験!？（PS2） · いっしょにごはん。（PSP） · きまぐれストロベリーカフェ（PS2） · とらぶるふぉうちゅんCOMPANY★はぴCURE（PS2） · はつカレっ☆恋愛デビュー宣言!（PSP） · ふしぎ遊戯 朱雀異聞（PS2） · ふしぎ遊戯 玄武開伝 外伝 鏡の巫女（PSP） · エルクローネのアトリエ（PSP） · エンジェル・プロファイル（PS2） · エーデルブルーメ（PS2） · オレンジハニー 〜僕はキミに恋してる〜（PS2） · カスタムドライブ（PSP） · キミカレ（PSP） · クローバー図書館の住人たち（PC） · クローバー図書館の住人たちII（PC） · シュガシュガルーン -恋もおしゃれもピックアップ！（PS2） · スカーレッドライダーゼクス STARDUST LOVERS（PSP） · スキップ・ビート！（PS2） · スト☆マニ ～Strobe☆Mania～（PSP） · セイント ビースト ~螺旋の章~（PS2） · ダイヤの国のアリス ～Wonderful Mirror World～（PSP） · テニスの王子様 RUSH & DREAM !（PS2） · テニスの王子様 SWEAT & TEARS 2（PS2） · デス・コネクション ポータブル（PSP） · トゥルーフォーチュン（PS2） · ナデプロ!! ~キサマも声優やってみろ!~（PS2） · バクダン★ハンダン（PSP） · フルハウスキス（PS2） · フルハウスキス 2（PS2） · プティフール（PS2） · プリンセスナイトメア · マイネリーベ 優美なる記憶（PS2） · マザーグースの秘密の館（PSP） · マーメイドプリズム（PS2） · モノクローム・ファクター cross road（PS2） · ラブ★コン 〜パンチDEコント〜（PS2） · ラブルートゼロ kisskiss☆ラビリンス（PS2） · リトルアンカー（PS2） · リプルのたまご ～Apprentice magician～（PS2） · 二世の契り（Nise no Chigiri）（PSP） · 令嬢探偵 〜オフィスラブ事件慕〜（PS2） · 伯爵と妖精 ～夢と絆に想いを馳せて～（PS2） · 原宿探偵学園 スチールウッド（PSP） · 召しませ浪漫茶房（PS2） · 好きなものは好きだからしょうがない3 RAIN · 幕末恋華・花柳剣士伝（PS2） · 恋は校則に縛られない（PSP） · 恋は校則に縛られない！（PSP） · 恋愛番長2 MidnightLesson!!!（PSP） · 恋花デイズ（PSP） · 悠久ノ桜（PS2） · 放課後colorful＊step～うんどうぶ！～（PSP） · 放課後colorful＊step～ぶんかぶ！～（PSP） · 放課後のLove Beat（PS2） · 放課後は白銀の調べ（PS2） · 星の降る刻（PS2） · 桜蘭高校ホスト部（PS2） · 楽園男子 ～誰も知らない もう一つの楽園～（PSP） · 硝子の森（PS2） · 維新恋華 龍馬外伝（PSP） · 蜜×蜜 ドロップス LOVE×LOVE HONEY LIFE（PS2） · 裏切りは僕の名前を知っている -黄昏に堕ちた祈り-（PS2） · 転生八犬士封魔録（PS2） · 青春はじめました！A（PSP） · 風色サーフ（PS2） | 极简 ISO9660 列目录 / 抽取（无依赖，支持 PSP UMD 镜像）。 | [stcm2l](../references/engines/stcm2l.md) · [system-nnn](../references/engines/system-nnn.md) · [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) |
| [iza2_unpack.py](iza2_unpack.py) | いざ、出陣！恋戦 第二幕 甲斐編（PSP） · いざ、出陣！恋戦 第二幕 越後編（PSP） | いざ、出陣！恋戦 第二幕 甲斐編 —— 批量解壳 + PSB 反编译。 | — |
| [izasen_cpk.py](izasen_cpk.py) | いざ、出陣！恋戦（PSP） | いざ、出陣！恋戦 data.cpk 解包（CPK 名 cp932 修正版） | [cri-archives](../references/engines/cri-archives.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [izasen_stream.py](izasen_stream.py) | いざ、出陣！恋戦（PSP） | いざ、出陣！恋戦 data.cpk → 剧本流还原 | — |
| [jingi_decrypt.py](jingi_decrypt.py) | 仁義なき乙女（PC） · 星の王女3 ～天・地・人の創世記～＋星の約束（PC） | 仁義なき乙女 (CRPT type 3) 解密 —— 复用 tsundere 的 LCG 表/散列/scatter 核心，逐块 seed 复原。 | — |
| [kanuchi_ydp.py](kanuchi_ydp.py) | カヌチ 二つの翼（PSP） | カヌチ 二つの翼 (PSP / Idea Factory 'YDP1') 解包 | [idea-factory-ydp-lsb](../references/engines/idea-factory-ydp-lsb.md) |
| [l7c.py](l7c.py) | 蝶々事件ラブソディック（PSV） | L7CA (Bandai Namco / Vita resource archive) 解包器。 | — |
| [lasting_snow_wbc.py](lasting_snow_wbc.py) | Lasting Snow | Extract text from Lasting Snow (Witch/Katze) system/text_data.wbc. | — |
| [looselips_extract.py](looselips_extract.py) | Loose Lips(SIDE Dry Kissing) · ゲーム3本セット | [Loose Lips series] RPG Maker MV text extractor (Enigma-boxed single exe). | — |
| [meiji_lzs.py](meiji_lzs.py) | 明治活劇 ハイカラ流星組（Switch） · 明治活劇 ハイカラ流星組 －成敗しませう、世直し稼業－（Switch） · 華ヤカ哉、我ガ一族 モダンノスタルジィ for Nintendo Switch（2026-10-30）（Switch） · 華ヤカ哉、我ガ一族 モダンノスタルジィ for Nintendo Switch（38,925 行（Switch） · 華ヤカ哉、我ガ一族 幻燈ノスタルジィ for Nintendo Switch（2026-10-30）（Switch） · 華ヤカ哉、我ガ一族 幻燈ノスタルジィ for Nintendo Switch（76,274 行（Switch） | 明治活劇 ハイカラ流星組 (NS-JP) の .lzs 解凍器 (c) 2026. | [lzs-scd](../references/engines/lzs-scd.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [mist_romfs.py](mist_romfs.py) | ミストニアの翅望 | ミストニアの翅望 —— 压缩 NCA(BKTR/LZ4 bucket-tree) → RomFS 直读（复用 redbell_romfs 的桶树实现）。 | — |
| [mizumelody_arc.py](mizumelody_arc.py) | 水の旋律 ～協奏曲～（PC） | 水の旋律 ～協奏曲～ (PC, KID/mlk ADV 引擎) ARC0 归档解包 | — |
| [ml2_emul.py](ml2_emul.py) | マイネリーベII ~誇りと正義と愛~（PS2） | 直接执行 SLPM_662.47 内的解压例程（unicorn, MIPS64/R5900 子集）. | — |
| [ml2_tkl.py](ml2_tkl.py) | drastic Killer（PS2） · マイネリーベII ~誇りと正義と愛~（PS2） | [PS2-JP] マイネリーベII tkl 容器 + type-2 解压 全链路工具. | — |
| [nana_unpack.py](nana_unpack.py) | NANA -ナナ-（PS2） | [PS2-JP] NANA -ナナ- STORY/ALLSC.NKP 解包（Konami NKP 嵌套）。 | — |
| [neon_nca.py](neon_nca.py) | ネオンクラッシュ -Echoes of the Lost-（Switch） | ネオンクラッシュ (NS) 压缩 NCA（LZ4 桶树）解包 —— 内容密钥由 ticket 解出后经 NCA_KEY 传入。 | — |
| [nso_x.py](nso_x.py) | DistortedCode ―生者の残り香―（Switch） · SWEET CLOWN ~午前三時のオカシな道化師~（Switch） · うたの☆プリンスさまっ♪ All Star（Switch） · ひめひび 続！二学期（Switch） · オメガヴァンパイア（Switch） · 死神と少女（Switch） | NSO0 -> 平铺镜像（text/rodata/data 依次拼接，LZ4 段自动解压）。 | — |
| [nsp_pfs0_dump.py](nsp_pfs0_dump.py) | 十三支演義 偃月三国伝1・2（Switch） | 纯 Python 解析 PFS0(NSP) 并导出条目（hactool 吃不了 CJK 路径）。 | — |
| [omegavamp_nca.py](omegavamp_nca.py) | オメガヴァンパイア（Switch） | オメガヴァンパイア(NS) 专用 NCA/RomFS 按需解密提取器（不改共用 scripts/switch_nca.py）。 | — |
| [oni_xci_nca.py](oni_xci_nca.py) | 9 R.I.P. sequel（Switch） · OVER REQUIEMZ（Switch） · 十鬼の絆（Switch） · 十鬼の絆 for Nintendo Switch（Switch） | XCI → 就地读 NCA → RomFS 枚举/导出（不过 hactool，不落 NCA）。 | [overflow-adv](../references/engines/overflow-adv.md) · [selfpak-utf16-vm](../references/engines/selfpak-utf16-vm.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) · [vridge](../references/engines/vridge.md) |
| [orange_peta.py](orange_peta.py) | オレンジハニー 〜僕はキミに恋してる〜（PS2） | Orange Honey (PS2, guyzware) — PETA(PTH/PTD) 解包 | — |
| [pentagon_vff.py](pentagon_vff.py) | Pentagon Syndrome（PC） | LiveMaker VFF 资源包解包（Pentagon Syndrome / 单 exe 全内嵌） | — |
| [ps2_extract.py](ps2_extract.py) | 「待提取」8本（PS2/PSP/PSV） · アンジェリーク エトワール（PS2） · マイネリーベ 優美なる記憶（PS2） · 風色サーフ（PS2） | PS2 .HD/.BIN extractor for the *Hakarena Heart*-type engine. | — |
| [psp_prx_type9_decrypt.py](psp_prx_type9_decrypt.py) | ★★ マスケティア（PSP） | PSP ~PSP (EncryptType 9) EBOOT.BIN decrypter. | — |
| [qpk.py](qpk.py) | 6本の「国のアリス」シリーズ一括抽出 (主角名 アリス＝リデル) · スクールウォーズ ～全巻パック 本編＆卒業戦線～（PSV） · ロミオＶＳジュリエット（PSV） · 新装版 お菓子な島のピーターパン ~Sweet Never Land~（PSV） · 源氏恋絵巻（PSV） | QuinRose / Qoo-framework QPK/QPI archive reader (PSP). | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [ratw_unpack_vf.py](ratw_unpack_vf.py) | Round Around the World | RATW (LiveMaker) VF 解包：game.ext 目录 + game.dat 数据（offsets 相对 dat）。 | — |
| [redbell_romfs.py](redbell_romfs.py) | レッドベルの慟哭（Switch） | レッドベルの慟哭 —— 压缩 NCA(LZ4 bucket-tree) → RomFS 直读。 | — |
| [rgssad_v1_extract.py](rgssad_v1_extract.py) | Voice(Guy×Luke) ガイルク | 资源解包 | — |
| [rhapsody_vfs.py](rhapsody_vfs.py) | マール王国の人形姫（Switch） · リトルプリンセス マール王国の人形姫２（Switch） · 天使のプレゼント マール王国物語（Switch） | VFS3 容器解包（日本一ソフトウェア / Rhapsody 系列，NS） | [vfs3-pak](../references/engines/vfs3-pak.md) |
| [ripple_unpack.py](ripple_unpack.py) | リプルのたまご（PS2） | リプルのたまご (PS2) HFU2 解包 + 目视 dump 用。 | — |
| [rom2_extract.py](rom2_extract.py) | ひぐらしのなく頃に奉＋Origin · 参千世界遊戯（PSV） · 参千世界遊戯 ～Re Multi Universe Myself～（PSV） · 鳥籠のマリアージュ ～初恋の翼～（PSV） | ROM2 archiver (Kalmia8 / 鳥籠のマリアージュ PSV). | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [rom2](../references/engines/rom2.md) |
| [rom2_list.py](rom2_list.py) | うみねこのなく頃に咲 ～猫箱と夢想の交響曲～（Switch） | ROM2 目录列表 / 按名提取（不整文件入内存） | — |
| [senjyushi_extract.py](senjyushi_extract.py) | 千銃士:Rhodoknight for Nintendo Switch（Switch） · 千銃士Rhodoknight（Switch） | 千銃士:Rhodoknight (NS) 解包 —— 压缩 NCA (LZ4 bucket-tree) → RomFS → 文件。 | — |
| [sgs_kai_ddp.py](sgs_kai_ddp.py) | Paradise（PS2） · Paradise 極-KIWAME- · Paradise 結-MUSUBI-（PS2） · Pigeon Blood · ディストピアの王 · 三国恋戦記 魁（PC） | 三国恋戦記 魁 (Daisy2 / sgs_*.dat, DDP2/DDP3) 解包 + 解密 + 解压 | [daisy2-ddp](../references/engines/daisy2-ddp.md) |
| [sidez_nca.py](sidez_nca.py) | Blackish House ←sideZ -Retour-（Switch） | Blackish House sideZ -Retour- (NS) : 压缩 NCA(BKTR bucket-tree + LZ4) → RomFS。 | — |
| [silentmoon_fpk.py](silentmoon_fpk.py) | Silent Moon | SilentMoon FPK: u32 count, entries {u32 off, u32 size, char name[24]}, raw data. | — |
| [stormlover_assets.py](stormlover_assets.py) | STORM LOVER V（PSV） | STORM LOVER V (PSV PCSG00735) —— 资源解压工具（2026-10-11）。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [tempest_upd_merge.py](tempest_upd_merge.py) | even if TEMPEST 宵闇にかく語りき魔女 Update v1.1.1（BKTR） | even if TEMPEST 宵闇にかく語りき魔女 Update v1.1.1（BKTR）→ 本体 romfs 合并读取。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) |
| [tennis_unpack.py](tennis_unpack.py) | テニスの王子様 RUSH & DREAM !（PS2） | [PS2-JP] テニスの王子様 RUSH & DREAM! 解包. | — |
| [thc_extract.py](thc_extract.py) | とらぶるふぉうちゅんCOMPANY★はぴCURE（PS2） | とらぶるふぉうちゅんCOMPANY★はぴCURE (PS2, Primavera/Interchannel "nlib") 文本提取 | — |
| [udf.py](udf.py) | Under the Moon ～クレセント～（PS2） · らぶ☆どろ ～LoveDrops～（PS2） | 极简 UDF 只读解析（PS2 桥接盘用）：列目录 / 抽取文件。 | — |
| [ukronia_nca.py](ukronia_nca.py) | 泡沫のユークロニア（Switch） | Blackish House sideA-> -Retour- (NS) 压缩 NCA（LZ4 桶树）解包。 | — |
| [ukronia_rawromfs.py](ukronia_rawromfs.py) | 泡沫のユークロニア（Switch） | 把「LZ4 桶树压缩 NCA」的 RomFS 段还原成裸 romfs 镜像（供 bktr_romfs.py --base 使用）。 | — |
| [ukronia_textasset.py](ukronia_textasset.py) | 泡沫のユークロニア（Switch） | ：导出 bundle 内指定 TextAsset 原文到文件。 | — |
| [ukronia_upd.py](ukronia_upd.py) | 泡沫のユークロニア（Switch） | 泡沫のユークロニア 更新档（BKTR）→ 最新 romfs 文件 读取/合并。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) |
| [uma_dec.py](uma_dec.py) | 冬園サクリフィス（Switch） | 资源解包 | [unity](../references/engines/unity.md) |
| [unity_textasset_dump.py](unity_textasset_dump.py) | 神凪ノ杜 五月雨綴り（Switch） · 魔女と亡霊のヴォロンテ（Switch） · 魔女と亡霊のヴォロンテ / Majo to Bourei no Volontés（Switch） | Unity resources.assets → 全 TextAsset 落盘（旁车 / managed text 导出）。 | — |
| [ura_ptd_jrs.py](ura_ptd_jrs.py) | 裏切りは僕の名前を知っている -黄昏に堕ちた祈り-（PS2） | Uragiri wa Boku no Namae o Shitteiru (PS2, Design Factory / Otomate 2010) | — |
| [virche_xci.py](virche_xci.py) | 終遠のヴィルシュ -ErroRsalvation-（Switch） | 重打包 XCI（封装头不自洽）→ 抽 NCA，带「数据起点自证」。 | — |
| [woga_datunpack.py](woga_datunpack.py) | RAKIDOMania black dog · RAKIDOMania yellow star | Tennenouji / woga AIR .dat 解包器。 | — |
| [xci_hfs0.py](xci_hfs0.py) | Honey Vibes（Switch） · My9Swallows TOPSTARS LEAGUE（Switch） · ハンサムロンダリング -the mystic lover-（Switch） · レンドフルール for Nintendo Switch（Switch） · レンドフルール for Nintendo Switch（36,583 行（Switch） · 泡沫のユークロニア -trail-（Switch） · 終遠のヴィルシュ -ErroRsalvation-（Switch） · 闇色の魔珠（Switch） | XCI (HFS0) 手工解析/抽 NCA —— 专治重打包 XCI 的「封装头不自洽」。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) |
| [xp3.py](xp3.py) | aim∴ai（PC） · Alice in Dreamworld（PC） · Angel ★ Pop（PC） · Ariard-少年アリス - Under the rose · Cocoon · Cocoon BN -Cocoon Black Noise- · Collision×Collision · CORE X ~Happy Halloween!~ · Day's Eye · Daytime and Night · Dream Dreamer · END END SUMMER（PC） · FRAGILE · Geheime Basis（PC） · Heavenly Blue · INNOCENT INCEST（PC） · invisible sign -イス- · invisible sign -イス- 眠れる森 · Live x Evil 熱砂のプロメテウス · LOSTPEACE～失われた欠片～ · Lover of vampire · One's Inside · ORPHAN DRUG · Qualia～クオリア～（PC） · Question（PC） · Recall（PC） · REstart · RUSH×UP！ · Scratch · Seven Sex Slaves · Spring Flower · Tether · ToucH もう一度この手が触れる世界 · TrickCall · Truth and False · ViSTA+1.20 · Voice · アカシア通り一番地 · アンダーブルー · アンダーブルー2012 · イカレちんぽ屋 · ウウウルトラC · エロトマニア · クリムゾン・ロワイヤル · 冬桜抄 -さくらがたり-（PC） · 凜々蝶さまのおっしゃる通り！（PC） · 千の祈りのパラドクス（PC） · 君がため、恋し乱れし月の華（PC） · 復讐帝國 · 海色小夜曲ーウミイロセレナーデー（PC） · 篠田新宿探偵事務所 唐獅子牡丹 · 群青ノ雪（PC） · 蝶の毒 華の鎖 · 蝶の毒 華の鎖 初回生産版（PC） · 蝶の毒 華の鎖 ～幻想夜話～ | 蝶の毒 華の鎖 XP3 索引列挙 + ファイル抽出 (KiriKiri XP3) | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [yuris_ypf.py](yuris_ypf.py) | ALL OUT（PC） | YU-RIS YPF 归档提取（归档可内嵌在 exe 尾部，也可为独立 .ypf）。 | — |
| [yuuki_pkg.py](yuuki_pkg.py) | alto -アルト-（PC） | Yuuki! Novel (ゆうき！ノベル) 引擎 —— 容器 PackageFile20 解析 + 文件解密。 | [yuuki-novel](../references/engines/yuuki-novel.md) |
| [zettaikyuu_romfs.py](zettaikyuu_romfs.py) | 絶対階級学園 ~Eden with roses and phantasm~（Switch） | 絶対階級学園 —— 从 prog.nca 流式取 romfs 指定文件（不落 6GB 副本）。 | — |
| [zokuwanai_unpack.py](zokuwanai_unpack.py) | 罪喰い（PSV） · 罪喰い ~千の呪い、千の祈り~ for V（つみくい ～せんののろい、せんのいのり～）（PSV） | 罪喰い for V (PCSG01019, HuneX Ogre) allscr.mrg 解包 + MZX0 解压。 | — |

## 最终文本提取（518 个）

| 脚本 | 适用作品 | 用途 | 关联格式 |
|---|---|---|---|
| [abukoi2_extract.py](abukoi2_extract.py) | アブナイ恋の捜査室 ~Eternal Happiness~（PSV） | [PSV-JP]アブナイ恋の捜査室 ~Eternal Happiness~ 文本提取器 | [asgard-tat](../references/engines/asgard-tat.md) |
| [abunai_extract.py](abunai_extract.py) | アブナイ恋の捜査室（PSP） | アブナイ恋の捜査室 (PSP, QuinRose/Gigno) —— .ks 文本 DSL → 全文本 | — |
| [acacia_extract.py](acacia_extract.py) | アカシア通り一番地 | [JP]アカシア通り一番地 — KiriKiri XP3 ＋ KAG3 全文本提取（双版对照） | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [agastar_extract.py](agastar_extract.py) | アガスターシェルゴサ（PC） | アガスターシェルゴサ v3.55: consume the packaged Tyrano native parser's tokens. | — |
| [aid_dw_extract.py](aid_dw_extract.py) | Alice in Dreamworld（PC） | [PC-JP]Alice in Dreamworld —— KiriKiri/KAG3 cp932 脚本 → 全文本（一次点击一行） | — |
| [aim_extract.py](aim_extract.py) | aim∴ai（PC） | [JP]aim∴ai（KiriKiri/KAG3）全文本提取：.ks → 一次点击一行。 | [kirikiri](../references/engines/kirikiri.md) |
| [akasuna_extract.py](akasuna_extract.py) | 赤い砂堕ちる月（PSV） | 赤い砂堕ちる月 (PSV / PCSG00780 / Landkarte & dramatic create 2016) 全文本提取器 | — |
| [akasuna_pc_extract.py](akasuna_pc_extract.py) | 赤い砂堕ちる月（PC） | 赤い砂堕ちる月 (PC / NScripter + NSLua / Landkarte 2013) 全文本提取 —— 双版对照 | — |
| [akuyaku_extract.py](akuyaku_extract.py) | 悪役令嬢は隣国の王太子に溺愛される（Switch） | 悪役令嬢は隣国の王太子に溺愛される (Switch, OPERAHOUSE, Unity / CSR1.00) 全文本提取。 | — |
| [alice_extract.py](alice_extract.py) | 白と黒のアリス for Nintendo Switch（Switch） | 白と黒のアリス for Nintendo Switch —— .qui(Lisp DSL) → 全文本（双版对照） | — |
| [alicis_extract.py](alicis_extract.py) | 籠の中のアリシス（WillPlus / AdvHD, WSC）（PC） | [PC-JP]籠の中のアリシス（WillPlus / AdvHD, WSC）文本提取器 —— 自包含、argv 式。 | — |
| [alto_extract.py](alto_extract.py) | alto -アルト-（PC） | [JP]alto -アルト- 文本提取驱动（Yuuki! Novel / PackageFile20）。 | [yuuki-novel](../references/engines/yuuki-novel.md) |
| [altor_extract.py](altor_extract.py) | ALTOR（PC） | ALTOR（PC / KiriKiri XP3 + KAGeXpress 3.0）一步出成品。 | — |
| [am2_extract.py](am2_extract.py) | AM2（PC） | [JP]AM2：00～猫と月夜のブランコ～ —— WillPlus AdvHD (WSC v1.0) 文本提取。 | — |
| [amennoir_extract.py](amennoir_extract.py) | アーメン・ノワール ポータブル（PSP） · アーメン・ノワール ポータブル（ARMEN NOIR portable | アーメン・ノワール ポータブル (PSP, Idea Factory / Design Factory 2012, ULJM06064) | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [angel_build.py](angel_build.py) | エンジェル・プロファイル（PS2） | Angel Profile (PS2) —— 生成交付文本。 | — |
| [angelfeather_extract.py](angelfeather_extract.py) | Angel's Feather（PC） | Angel's Feather (PC / BlueImpact 自研 AF 1.03 / BSF1) 全文本提取 —— 单文件自包含版 | [blueimpact-bsf1](../references/engines/blueimpact-bsf1.md) |
| [angelique_extract.py](angelique_extract.py) | アンジェリーク ルトゥール（PSV） | アンジェリーク ルトゥール (PSV, PCSG00696) 剧本正文+选项提取   [Koei Tecmo / Ruby Party 自研「pasc」节点流] | — |
| [angelknight_ssb.py](angelknight_ssb.py) | Angel Knight（PC） | [JP]Angel Knight (PC / SaiSys / Ferret-ZUI) 正文提取 | — |
| [angelpop_extract.py](angelpop_extract.py) | Angel ★ Pop（PC） | [JP]Angel ★ Pop  正文提取（KiriKiri KAG3 / cp932 .ks） | — |
| [animamundi_extract.py](animamundi_extract.py) | アニマムンディ 終りなき闇の舞踏 | [JP]アニマムンディ 終りなき闇の舞踏 — 全文本提取（修订版 v3） | — |
| [anki_extract.py](anki_extract.py) | アンジェリーク 魔恋の六騎士（PSP） | アンジェリーク 魔恋の六騎士 (PSP, ULJM05986, Otomate 2011-11-17, vndb v8799) | — |
| [anotherrewind_extract.py](anotherrewind_extract.py) | Another Rewind（PC） · Battle Four Re（PC） | [JP]Another Rewind（LiveMaker / LiveNovel）正文+选项提取 | — |
| [apricot_extract.py](apricot_extract.py) | 怪盗アプリコット（PSP） · 怪盗アプリコット ポータブル（PSP） · 怪盗アプリコット 外伝 満編（PC） | 怪盗アプリコット ポータブル (PSP, Takuyo gss) 全文本提取。 | — |
| [apricot_gaiden_extract.py](apricot_gaiden_extract.py) | 怪盗アプリコット 外伝 満編（PC） | 怪盗アプリコット 外伝 満編（PC / Takuyo GSS, SCRDATA = LSDARC V.100 + SCR 1.10） | — |
| [arcanafam2_run.py](arcanafam2_run.py) | アルカナファミリア2（PSP） · アルカナ・ファミリア2（PSP） | アルカナ・ファミリア2 (PSP, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取。 | — |
| [arcanafesta_run.py](arcanafesta_run.py) | アルカナファミリア_フェスタレガーロ（PSP） · アルカナ・ファミリア フェスタ・レガーロ!（PSP） | アルカナ・ファミリア フェスタ・レガーロ! (PSP) 成品生成。 | — |
| [arcanayurei_run.py](arcanayurei_run.py) | アルカナファミリア_幽霊船の魔術師（PSP） · アルカナ・ファミリア 幽霊船の魔術師（PSP） | アルカナ・ファミリア 幽霊船の魔術師 (PSP, HuneX「IKA SEQ SYSTEM v3.4」) 全文本提取。 | — |
| [arcobaleno_extract.py](arcobaleno_extract.py) | アルコバレーノ! ポータブル（PSP） | アルコバレーノ! ポータブル (PSP, ULJM05609) 剧本文本提取 | — |
| [ariard_extract.py](ariard_extract.py) | Ariard-少年アリス - Under the rose（PC） · Ariard-少年アリス-（PC） | Ariard / Latte (KiriKiri/KAG3) 成行器 —— 第八变体 XP3 专用 | [kirikiri](../references/engines/kirikiri.md) |
| [artemis_pfs_extract.py](artemis_pfs_extract.py) | 滄海天記（Switch） · 结果 | Artemis Engine (iMel) 全文本提取工具 —— 以《滄海天記》(NS-JP) 定案 | [artemis](../references/engines/artemis.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [asakiyumemishi_extract.py](asakiyumemishi_extract.py) | あさき、ゆめみし～ひととせ～（PC） · 外部核对（vndb v12478 + 巴哈姆特 cast） | あさき、ゆめみし～ひととせ～ (PC / 澪 / System-NNN「NNNLib」引擎) 全文本提取 · 定稿 | — |
| [asakiyumemishi_psp_extract.py](asakiyumemishi_psp_extract.py) | あさき、ゆめみし（PSP） · 神足町人妖譚 ~迷イ子ノ章~（PC） | あさき、ゆめみし (PSP-JP / System-NNN「NNNLib」engine) 全文本提取 · 定稿 | — |
| [asuka_extract.py](asuka_extract.py) | あすか！～僕ら星灯高校野球団～（PC） · 仁義なき乙女 恋恋三昧（PC） | [PC-JP]あすか！～僕ら星灯高校野球団～ 全文本提取器 (Madoka GScript / CRPT) | — |
| [ayanomiya_extract.py](ayanomiya_extract.py) | 妖ノ宮（PC） | Kogado Aya ARCW archive and script extractor. Python 3, standard library. | — |
| [baccan_extract.py](baccan_extract.py) | 爽海バッカニアーズ!（PSV） | 爽海バッカニアーズ! 剧本文本提取（テキスト方式ADV / プチレーヴ）。 | — |
| [bakudan_run.py](bakudan_run.py) | バクダン★ハンダン（PSP） | バクダン★ハンダン（PSP / ULJM-06057，Idea Factory / Otomate）—— 全文本提取。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [believer_extract.py](believer_extract.py) | BELIEVER!（PSV） · 记忆/约定 | BELIEVER! (PSV, PCSG00539)  HuneX / UNAS('HESL') script text extractor. | — |
| [benihana_extract.py](benihana_extract.py) | 越えざるは紅い花 after disc～綾なす未来～（YU-RIS / YPF v500）（PC） | 越えざるは紅い花 after disc～綾なす未来～（YU-RIS / YPF v500）全文本提取。 | — |
| [beru_extract.py](beru_extract.py) | 私立ベルばら学園 ～ベルサイユのばらReimagination～（Switch） | 私立ベルばら学園 ～ベルサイユのばらReimagination～ (NS) —— STCM2L 全文本提取 | — |
| [bezel_extract.py](bezel_extract.py) | even if TEMPEST 連なるときの暁（Switch） | even if TEMPEST 連なるときの暁（Switch / Nintendo **Bezel Engine**）剧本文本提取。 | — |
| [bgloss_extract.py](bgloss_extract.py) | Butterfly Gloss · Butterfly Rouge | Butterfly Gloss (WillPlus / AdvHD) text extractor. | — |
| [binarystar_extract.py](binarystar_extract.py) | BinaryStar（PSV） | [PSV-JP] BinaryStar (PCSG00389, Otomate × Design Factory, 2014) 剧本文本提取 | — |
| [bir_base_extract.py](bir_base_extract.py) | ビルシャナ戦姫 ～一樹の風～（FD） · ビルシャナ戦姫 ～源平飛花夢想～（Switch） | ビルシャナ戦姫 ～源平飛花夢想～ (NS, 本体) → 全文本 | [vridge](../references/engines/vridge.md) |
| [bir_extract2.py](bir_extract2.py) | ビルシャナ戦姫 ～一樹の風～（Switch） | ビルシャナ戦姫 ～一樹の風～ (NS) → 全文本 | [vridge](../references/engines/vridge.md) |
| [blackish_pc_extract.py](blackish_pc_extract.py) | Blackish House sideA（PC） | [PC-JP] Blackish House sideA→（honeybee black 2016 / PC） | — |
| [blip_extract.py](blip_extract.py) | Butterfly Lip（PC） | Butterfly Lip (PC / WillPlus-AdvHD) text extractor. | — |
| [boiz_extract.py](boiz_extract.py) | ♂ボ～イズ！！～イケメン陵辱パラダイス～（体験版） | [JP]♂ボ～イズ！！～イケメン陵辱パラダイス～（体験版） 文本提取 | — |
| [brothers_kiss_extract.py](brothers_kiss_extract.py) | ブラザーズ～恋するお兄さま＆もっと恋するお兄さま～ (Tiaramode, 2007, BGI/Ethornell) | ブラザーズ～恋するお兄さま＆もっと恋するお兄さま～  (Tiaramode, 2007, BGI/Ethornell) | — |
| [brouge_extract.py](brouge_extract.py) | Butterfly Rouge（PC） | Butterfly Rouge (PC / WillPlus-AdvHD) text extractor. | — |
| [bt_extract.py](bt_extract.py) | バトラーズ～召しませお嬢様～ / ～ナイトモード～ (Tiaramode, BGI/Ethornell v0) | バトラーズ～召しませお嬢様～ / ～ナイトモード～  (Tiaramode, BGI/Ethornell v0) | — |
| [btf_extract.py](btf_extract.py) | Beyond The Future -Fix The Time Arrows-（PSP） · Beyond The Future -Fix The Time Arrows-（MAGES.×Rejet / M（PSP） | [PSP-JP] Beyond The Future -Fix The Time Arrows- 全文本提取。 | — |
| [btf_s2_extract.py](btf_s2_extract.py) | BUSTAFELLOWS シーズン2（Switch） | BUSTAFELLOWS シーズン2（NS-JP）全文本提取 —— 自研 UTXT 容器 | — |
| [build_choice_text.py](build_choice_text.py) | CHOICE | CHOICE (KiriKiri KAG) 文本提取 → 提取结果/CHOICE.txt | — |
| [build_kure.py](build_kure.py) | クレプシドラ～光と影の十字架～（硬盘版）（PC） | クレプシドラ 成品构建：scenario(ARC2) -> LZSS -> 正文成行 | — |
| [build_ls2.py](build_ls2.py) | ラスト・エスコート2 ～深夜の甘い棘～ | ラスト・エスコート2 ～深夜の甘い棘～ 全文本生成 | — |
| [build_text.py](build_text.py) | ラスト・エスコート 〜黒蝶スペシャルナイト〜 · 好きなものは好きだからしょうがない2 TARGET+NIGHTS（PC） | ラスト・エスコート 〜黒蝶スペシャルナイト〜 全文本生成 | — |
| [busta_extract.py](busta_extract.py) | BUSTAFELLOWS（Switch） | BUSTAFELLOWS（NS-JP, Unity 2018.4 IL2CPP, global-metadata v24）文本提取。 | [unity](../references/engines/unity.md) |
| [bwolves_extract.py](bwolves_extract.py) | BLACK WOLVES SAGA -Weiβ und Schwarz-（Switch） · BLACK WOLVES SAGA -Weiβ und Schwarz- for Nintendo Switch（Switch） | BLACK WOLVES SAGA -Weiß und Schwarz- (Switch, STCM2L) 剧本提取器. | — |
| [byakko_extract.py](byakko_extract.py) | BYAKKO ～四神部隊炎恋記～（Switch） | BYAKKO ～四神部隊炎恋記～ (NS-JP) 文本提取 | — |
| [cafe_extract.py](cafe_extract.py) | Cafe Cuillere（PSV） · Cafe Cuillere ~カフェ キュイエール~（PSV） | Cafe Cuillere (PSV PCSG01197, DWANGO/Takuyo, gss engine) text extractor. | — |
| [cend_extract.py](cend_extract.py) | Cendrillon palikA（Switch） | Cendrillon palikA (NS) —— STCM2L 全文本提取 | — |
| [cfm_extract.py](cfm_extract.py) | Confidential Money ～300日で3000万ドル稼ぐ方法～（PSP） | Confidential Money (PSP / Otomate 2012) .evb -> text. | — |
| [chou_extract.py](chou_extract.py) | 蝶の毒 華の鎖 · 蝶の毒 華の鎖 初回生産版（PC） | 蝶の毒 華の鎖 全テキスト抽出（KAG3 スクリプト → 表示テキスト） | — |
| [chouchou_build.py](chouchou_build.py) | 蝶々事件ラブソディック（PSV） | 蝶々事件ラブソディック（PSV, L7CA + Lua5.3 变体字节码）正文提取。 | — |
| [cloverlib2_extract.py](cloverlib2_extract.py) | クローバー図書館の住人たちⅡ（PC） | クローバー図書館の住人たちⅡ (PC-JP / System-NNN「NNNLib」) 全文本提取 | [system-nnn](../references/engines/system-nnn.md) |
| [cloverlib_extract.py](cloverlib_extract.py) | クローバー図書館の住人たち（PC） | クローバー図書館の住人たち (PC-JP / 澪 / System-NNN「NNNLib」系) 全文本提取 | — |
| [clusteredge_extract.py](clusteredge_extract.py) | クラスターエッジ 〜君を待つ未来への証〜（PS2） | Cluster Edge (PS2, SLPS_256.54) —— DataChain + MSDA 文本提取。 | — |
| [colorful_bunka_extract.py](colorful_bunka_extract.py) | 放課後colorful＊step～ぶんかぶ！～（PSP） | 放課後colorful＊step～ぶんかぶ！～（PSP）全文本提取。 | — |
| [colorful_undo_extract.py](colorful_undo_extract.py) | 放課後colorful＊step～うんどうぶ！～（PSP） | [PSP-JP]放課後colorful＊step～うんどうぶ！～ 全文本提取 | — |
| [corda_2fa_extract.py](corda_2fa_extract.py) | 金色のコルダ2f アンコール（PSP） | 金色のコルダ2f アンコール (PSP) 全文本提取器 v3. | — |
| [corda_2ff_extract.py](corda_2ff_extract.py) | 金色のコルダ2 ff（PSV） · 金色のコルダ2f アンコール（PSP） · 金色のコルダ２ff フォルテッシモ（Koei Tecmo / Ruby Party） | 金色のコルダ2 ff (PSVita, PCSG01124) 全文本提取器 | [koei-cdar](../references/engines/koei-cdar.md) |
| [corda_3_extract.py](corda_3_extract.py) | 金色のコルダ3（PSV） | 金色のコルダ3 (PSVita, PCSG01211) 全文本提取器 | — |
| [corda_3as_extract.py](corda_3as_extract.py) | 金色のコルダ3 AnotherSky（PSV） · 金色のコルダ３ AnotherSky feat.神南 | 金色のコルダ3 AnotherSky feat.神南/至誠館/天音学園 (PSVita PCSG01212) 全文本提取器 | — |
| [corda_octave_extract.py](corda_octave_extract.py) | 2026-10-03 晚（20:40）· 金色のコルダ オクターヴ（Switch） · 金色のコルダ オクターヴ（Switch） | 金色のコルダ オクターヴ (Switch) 全文本提取器 v3  (定稿候选) | — |
| [corda_psp_extract.py](corda_psp_extract.py) | 金色のコルダ（PSP） | 金色のコルダ (PSP) 剧本/文本提取器  (自包含, 无外部依赖) | — |
| [cr_extract.py](cr_extract.py) | Code（Switch） · オランピアソワレ Catharsis for Nintendo Switch（2026-10-29）（Switch） · オランピアソワレ（本篇）for Nintendo Switch（2026-10-29）（Switch） · オランピアソワレ（本篇）for Nintendo Switch（46,055 行（Switch） · ピオフィオーレの晩鐘 -ricordo-（2026-10-29）（Switch） · ピオフィオーレの晩鐘 -ricordo-（46,566 行（Switch） | [NS-JP]Code：Realize ～彩虹の花束～ for Nintendo Switch —— STCM2L 文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [crankin_extract.py](crankin_extract.py) | クランク・イン (Crank In)（PSV） · クランク・イン（Crank In） PSV（PSV） | クランク・イン (Crank In) — PSV / PCSG00941 / プチレーヴ (Puchireve) | — |
| [crazychain_extract.py](crazychain_extract.py) | CRAZY CHA!N -エルピスの鎖-（Switch） · 勿ノ怪契リ（Switch） | CRAZY CHA!N -エルピスの鎖- (Nintendo Switch) 全文本提取 | — |
| [crimson_royale_extract.py](crimson_royale_extract.py) | クリムゾン・ロワイヤル（PC） | クリムゾン・ロワイヤル (QuinRose, 2009 / KiriKiri KAG3, DropWave OTag system) | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [cxm_extract.py](cxm_extract.py) | Collar x Malice for Nintendo Switch（Switch） | Collar x Malice for Nintendo Switch (NS-JP) 全文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [danzai_maria_psp_extract.py](danzai_maria_psp_extract.py) | 断罪のマリア ラ･カンパネラ · 絶対迷宮 秘密のおやゆび姫（PSV） | 断罪のマリア ラ･カンパネラ PSP: script-only LIBP/Malie extraction. | [malie](../references/engines/malie.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [dareura_extract.py](dareura_extract.py) | 誰にでも裏がある -True or Lie？-（PC） | 誰にでも裏がある -True or Lie？-: use the checked RealLive reader. | [reallive](../references/engines/reallive.md) |
| [dc_extract.py](dc_extract.py) | デス・コネクション ポータブル（PSP） | デス・コネクション ポータブル（PSP ULJM05823 / Otomate 2011） | — |
| [dcgs_extract.py](dcgs_extract.py) | D.C. Girl's Symphony Pocket（PSP） · D.C. Girl's Symphony Pocket ~ダ・カーポ～ガールズシンフォニーポケット（PSP） | D.C. Girl's Symphony Pocket (PSP, ULJM05690) 剧本文本提取 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [dcode_extract.py](dcode_extract.py) | DistortedCode ―生者の残り香―（Switch） | [NS-JP]DistortedCode ―生者の残り香― text extract (TAKUYO gss / SCR 3.00). | — |
| [ddengine_text.py](ddengine_text.py) | Daylight～朝に光の冠を～ | DDEngine / DDSystem（「Daylight」2008）—— dl_text.dat 全文本提取 | — |
| [desperadrops_extract.py](desperadrops_extract.py) | DesperaDrops（Switch） | DesperaDrops (NS-JP) 全文本提取 —— Utage 引擎 / .book 二进制 | [unity](../references/engines/unity.md) |
| [dessert_extract.py](dessert_extract.py) | Dessert Love -Sweet Plus-（PS2） | Dessert Love -Sweet Plus- (PS2) 全文本提取。 | [stcm2l](../references/engines/stcm2l.md) · [system-nnn](../references/engines/system-nnn.md) · [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) |
| [dia_alice_extract.py](dia_alice_extract.py) | ダイヤの国のアリス ～Wonderful Mirror World～（PSP） | ダイヤの国のアリス ～Wonderful Mirror World～ (PSP) 全文本提取 | — |
| [diary_ystb.py](diary_ystb.py) | Diary（PC） | Diary（[PC-JP] Operetta 2011 / YU-RIS・YSTB v0x199）全文本提取。 | — |
| [digit_extract.py](digit_extract.py) | 数乱digit For Nintendo Switch（Switch） | [NS-JP]数乱digit For Nintendo Switch —— SCD 字节码文本提取 | — |
| [director_build.py](director_build.py) | King of Beast | King of Beast 成品构建器 | — |
| [director_d8_text.py](director_d8_text.py) | ESCAPE | Director 8（XFIR 小端）text cast member（XMED）→ 一成员一框的正文文本。 | — |
| [director_dsl_text.py](director_dsl_text.py) | EverLoyalty ～永遠の忠誠～ | Director 上的「自研 DSL 脚本引擎」→ 一 MSG 一框的正文文本。 | — |
| [director_rifx_xmed.py](director_rifx_xmed.py) | GUISARD・SHUFFLE～僕らは想いを解き放つ～ · GUISARD～僕らは想いを身に纏う～ | Director RIFX(大端) + XMED「指令 DSL」文本提取器 —— GUISARD 本編（2003 / サンダルダッシュ）。 | — |
| [director_stxt_text.py](director_stxt_text.py) | bois ～機械じかけの街～ | Macromedia Director（Afterburner 保护）→ 台本 CSV → 「一次点击 = 一行」。 | [overflow-adv](../references/engines/overflow-adv.md) |
| [director_xmed_dsl.py](director_xmed_dsl.py) | GUISARD Fandisc～僕らの想いを詰め込んで～ | [Director 8.5 / XFIR 小端] XMED 内的「尖括号指令 DSL」→ 成品正文（一次点击 = 一行） | — |
| [director_xmed_text.py](director_xmed_text.py) | D.Zone · GUISARD Fandisc～僕らの想いを詰め込んで～ · アブディエル | Director（8.5 / Afterburner 已由 ProjectorRays 解成 .dir）→ 全文本 | — |
| [dk_final.py](dk_final.py) | drastic Killer（PS2） | [PS2-JP]drastic Killer 成品生成（一次点击 = 一行）。 | [stcm2l](../references/engines/stcm2l.md) · [system-nnn](../references/engines/system-nnn.md) · [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) |
| [dl_df_extract.py](dl_df_extract.py) | DIABOLIK LOVERS DARK FATE（PSV） | DIABOLIK LOVERS DARK FATE (PSV, PCSG00530) 文本提取 | — |
| [dl_ge_extract.py](dl_ge_extract.py) | DIABOLIK LOVERS GRAND EDITION for Nintendo Switch（Switch） | DIABOLIK LOVERS GRAND EDITION for Nintendo Switch —— 文本提取。 | [stcm2l](../references/engines/stcm2l.md) |
| [dlcl_extract.py](dlcl_extract.py) | DIABOLIK LOVERS CHAOS LINEAGE（Switch） | DIABOLIK LOVERS CHAOS LINEAGE (NS-JP) —— script.cpk 全文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [dms_extract.py](dms_extract.py) | DEAR My SUN!! ～ムスコ★育成★狂騒曲～（PS2） | DEAR My SUN!! ～ムスコ★育成★狂騒曲～（PS2 / HuneX IKA SEQ, SLPS_258.10）全文本提取。 | — |
| [dsb_extract.py](dsb_extract.py) | Darling Special Backlash ～恋のエキゾースト・ヒート～（PS2） | Darling Special Backlash ～恋のエキゾースト・ヒート～ (PS2-JP, SLPM_656.53) | — |
| [dscatt_extract.py](dscatt_extract.py) | Double Score ～Cattleya×Narcissus～（PC） | Double Score ～Cattleya×Narcissus～ 专用入口。 | — |
| [dyc_extract.py](dyc_extract.py) | DYNAMIC CHORD feat.[reve parfait] Remaster edition（Switch） · スチームプリズン -Beyond the Steam-（Switch） | DYNAMIC CHORD feat.[rêve parfait] Remaster edition (NS-JP, 010076902126e000) | — |
| [dycko_extract.py](dycko_extract.py) | DYNAMIC CHORD feat.KYOHSO Append Disc（PC） | [PC-JP] DYNAMIC CHORD feat.KYOHSO Append Disc（honeybee black / ASGARD / PC 2016） | — |
| [dycls_extract.py](dycls_extract.py) | DYNAMIC CHORD feat.Liar-S Append Disc（PC） | [PC-JP] DYNAMIC CHORD feat.Liar-S Append Disc（honeybee black / ASGARD, PC-ISO） | — |
| [dycpc_extract.py](dycpc_extract.py) | DYNAMIC CHORD feat.apple-polisher（PC） · DYNAMIC CHORD feat.KYOHSO Append Disc（PC） | [PC-JP] DYNAMIC CHORD feat.apple-polisher（honeybee black 2016-11-04 / PC） | — |
| [dydc_extract3.py](dydc_extract3.py) | DYNAMIC CHORD feat.apple-polisher Remaster Edition（Switch） · DYNAMIC CHORD feat.KYOHSO Remaster Edition（Switch） · DYNAMIC CHORD feat.Liar-S Remaster edition（Switch） | DYNAMIC CHORD Remaster 系列 3 部（Liar-S / KYOHSO / apple-polisher）全文本提取。 | — |
| [dystopia_extract.py](dystopia_extract.py) | Paradise 結-MUSUBI- · ディストピアの王 | [JP] ディストピアの王 (Daisy2 / DDP3) text extractor. | [daisy2-ddp](../references/engines/daisy2-ddp.md) |
| [edelblume_extract.py](edelblume_extract.py) | エーデルブルーメ (SLPM-66976 / Design Factory・Otomate 2008)（PS2） | [PS2-JP] エーデルブルーメ (SLPM-66976 / Design Factory・Otomate 2008) 剧本文本提取 | — |
| [edema_extract.py](edema_extract.py) | Live x Evil 灼熱のエデマ | [JP]Live x Evil 灼熱のエデマ — KiriKiri XP3 / KAG3 全文本提取器 | — |
| [ees_extract.py](ees_extract.py) | END END SUMMER（PC） | END END SUMMER (KiriKiri / KAG3 派生) 文本提取 —— 双版对照 | — |
| [emsg_eternity.py](emsg_eternity.py) | Jewel Garden | EMSG（Eternity 引擎 / white plum『Jewel Garden』系）消息库提取器 | — |
| [enbu_extract.py](enbu_extract.py) | 戦場の円舞曲 for Nintendo Switch（Switch） | 戦場の円舞曲 for Nintendo Switch —— 全文本提取器 | — |
| [enkan_extract.py](enkan_extract.py) | 円環のメモーリア · 円環のメモーリア -カケラ灯し-（PSV） | 円環のメモーリア -カケラ灯し- (PSV / PCSG01167 / A'sRing & Dramatic Create) 全文本提取器 | — |
| [epic_extract.py](epic_extract.py) | 終遠のヴィルシュ -EpiClycoris-（Switch） | 終遠のヴィルシュ -EpiClycoris- —— STCM2L(Switch/2018型) → 全文本。 | — |
| [epriru_extract.py](epriru_extract.py) | エイプリルーるののこりもの | [JP]エイプリルーるののこりもの（LiveMaker 3，2009 同人 / キタユメ。）文本提取驱动。 | [livemaker](../references/engines/livemaker.md) |
| [eroto_extract.py](eroto_extract.py) | エロトマニア（吉里吉里2 / KAG3，2016 女性向け18禁BL） | [JP]エロトマニア（吉里吉里2 / KAG3，2016 女性向け18禁BL）文本提取驱动。 | — |
| [etoile_final.py](etoile_final.py) | アンジェリーク エトワール（PS2） | SCPT 目录 -> 最终全文本（一行 = 一次点击） | — |
| [etoile_houteishiki_extract.py](etoile_houteishiki_extract.py) | エトワールの方程式 | [JP]エトワールの方程式 extractor. | — |
| [etude_extract.py](etude_extract.py) | étude prologue（PSP） · étude prologue 〜揺れ動く心のかたち〜（PSP） · étude prologue 〜揺れ動く心のかたち〜 Portable（PSP） | Extract all displayed text from étude prologue 〜揺れ動く心のかたち〜 Portable | — |
| [euchronia_trail_extract.py](euchronia_trail_extract.py) | 泡沫のユークロニア -trail-（Switch） | 泡沫のユークロニア 剧本成行器（TIS 风格 [命令] 脚本）。 | — |
| [extract_alice.py](extract_alice.py) | 6本の「国のアリス」シリーズ一括抽出 (主角名 アリス＝リデル) | Extract scenario text from the Alice-series PSP games (QuinRose). | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [extract_gunjo.py](extract_gunjo.py) | 群青ノ雪（PC） | 群青ノ雪 (KiriKiri/KAG3) 文本提取 | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [extract_orphan_drug.py](extract_orphan_drug.py) | ORPHAN DRUG | ORPHAN DRUG (FUSYRO / KiriKiri KAG3) 文本提取 | — |
| [extract_question.py](extract_question.py) | Question（PC） | [JP]Question (KiriKiri/KAG3) 全文本提取 —— 专用提取器（S6） | [kirikiri](../references/engines/kirikiri.md) |
| [extract_text.py](extract_text.py) | Lkyt · Riddle Garden（PC） · エトワールの方程式 · 成果物 | PSP アラビアンズ・シリーズ 脚本テキスト抽出 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [fhk2_extract.py](fhk2_extract.py) | フルハウスキス 2（PS2） | フルハウスキス 2 (PS2, Capcom/TENKY, SLPM-662.88) —— 全文本提取（定稿）。 | — |
| [foris_script_xml.py](foris_script_xml.py) | GAME S.S.D.S. ～刹那の英雄～ | FORIS-OS（0verflow 系／S.S.D.S. 等）剧本 XML → 一次点击一行的正文。 | — |
| [fortissimo_extract.py](fortissimo_extract.py) | フォルティッシモ（PSV） | 《フォルティッシモ》 (PS Vita / PCSG01131 / KADOKAWA x Otomate / 2018-03-08) 全文本提取 | [cri-archives](../references/engines/cri-archives.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [fsymph_extract.py](fsymph_extract.py) | for Symphony（PSP） · for Symphony ～with all one's heart～ ポータブル · for Symphony ～with all one's heart～ ポータブル（自动化任务 2026-10-（PSP） | for Symphony ポータブル (PSP-JP, Takuyo, ULJM05258, v1.01) full-text extractor. | — |
| [fukushu_extract.py](fukushu_extract.py) | 復讐帝國（PC） | 復讐帝國（PC-JP / KiriKiri + RAT 系自定义 LineMode）文本提取器。 | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [fuyuzakura_text.py](fuyuzakura_text.py) | 冬桜抄 -さくらがたり-（PC） | [PC-JP]冬桜抄 -さくらがたり-（KiriKiri KAG3 · data.xp3）全文本提取。 | — |
| [gakeppuchi_extract.py](gakeppuchi_extract.py) | 崖っぷち令嬢は無気力悪魔で乙女を捨てたい（YU-RIS / YPF v500）（PC） | 崖っぷち令嬢は無気力悪魔で乙女を捨てたい（YU-RIS / YPF v500）全文本提取。 | — |
| [gakuenk_extract.py](gakuenk_extract.py) | 学園K -Wonderful School Days- V Edition（PSV） | 学園K -Wonderful School Days- V Edition  (PSV, PCSG00654, Otomate / Idea Factory) | [dat-pak-scd](../references/engines/dat-pak-scd.md) |
| [galtia_extract.py](galtia_extract.py) | GALTIA | GALTIA（PIL/SLASH, Artemis Engine）剧本 → 成行 | — |
| [garnet_extract.py](garnet_extract.py) | ガーネット・クレイドル ポータブル（PSP） · ガーネット・クレイドル ポータブル ～鍵の姫巫女～（2011-02-10 | ガーネット・クレイドル ポータブル ～鍵の姫巫女～ (PSP, 2011 / STCM2L "Minku 07.0") | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [garnet_pc_extract.py](garnet_pc_extract.py) | GARNET CRADLE（PC） · GARNET CRADLE Sugary Sparkle（PC） | GsWin / DataPack5 (Takuyo PC) —— Scw5.x 剧本文本提取（一次点击 = 一行）。 | — |
| [genji_extract.py](genji_extract.py) | 源氏恋絵巻（PSV） | QuinRose Qoo (PSV) —— [PSV-JP]源氏恋絵巻 剧本成行。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [gensou_extract.py](gensou_extract.py) | 蝶の毒 華の鎖 ～幻想夜話～ | 蝶の毒 華の鎖 ～幻想夜話～ 全テキスト抽出（KAG3 スクリプト → 表示テキスト） | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [gessan_extract.py](gessan_extract.py) | 月影の鎖 -狂爛モラトリアム-（Switch） | 月影の鎖 -狂爛モラトリアム- (NS) 文本提取 — Takuyo gss / SCR 2.00 / LSDARC V.100 | — |
| [geten_extract.py](geten_extract.py) | 下天の華 with 夢灯り（PSV） | 下天の華 with 夢灯り (PSVita PCSG00921) 全文本抽取器 | — |
| [ghp_extract.py](ghp_extract.py) | Glass Heart Princess -for Nintendo Switch-（Switch） · Glass Heart Princess for Nintendo Switch（Switch） | Glass Heart Princess for Nintendo Switch —— 全文本提取器 | — |
| [ginkoku_build2.py](ginkoku_build2.py) | 銀の冠碧の涙（PC） | 成行（v2）：源 = _work_ginkoku/out2（按 tpm 真算法解出的台本） | — |
| [glasu_text.py](glasu_text.py) | 硝子の森（PS2） | 硝子の森（PS2-JP / D3P SIMPLE2000 Vol.13 / HuneX "ebf" Ver 0.30）文本提取。 | — |
| [goes_extract.py](goes_extract.py) | Goes!（PSV） | Goes! (PCSG00367) 文本提取 | — |
| [grim_extract.py](grim_extract.py) | グリム・ザ・バウンティハンター（PSP） | グリム・ザ・バウンティハンター（PSP / QuinRose / KiriKiri KAG .ks）文本提取。 | — |
| [gs2_scb_extract.py](gs2_scb_extract.py) | 恋してしまった星の王子 ～制裁院編～ | 恋してしまった星の王子 ～制裁院編～（NS / Bezel Engine）文本提取器 | [bezel-bea](../references/engines/bezel-bea.md) |
| [hakken_extract.py](hakken_extract.py) | 転生八犬士封魔録（PS2） | 転生八犬士封魔録 (PS2-JP, SLPM_663.96) —— SC.AFS 全文本提取。 | — |
| [hakuoki_kf_extract.py](hakuoki_kf_extract.py) | 薄桜鬼 真改 万葉ノ抄 · 薄桜鬼 真改 天雲ノ抄 · 薄桜鬼 真改 月影ノ抄 · 薄桜鬼 真改 銀星ノ抄 · 薄桜鬼 真改 風華伝 for Nintendo Switch（Switch） · 薄桜鬼 真改 黎明録 | [NS-JP]薄桜鬼 真改 風華伝 文本提取（STCM2L / Switch / UTF-8）。 | — |
| [hakuoki_ns_build.py](hakuoki_ns_build.py) | 薄桜鬼 遊戯録 隊士達の大宴会（Switch） | 薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— 成品构建（正文＋选项＋扉文＋用語辞典）。 | — |
| [hakuoki_zuisouroku_extract.py](hakuoki_zuisouroku_extract.py) | 薄桜鬼 随想録 面影げ花（PSV） | 薄桜鬼 随想録 面影げ花 (PSV, PCSG00485, Idea Factory / Otomate) | — |
| [hakushaku_extract.py](hakushaku_extract.py) | 伯爵と妖精 ～夢と絆に想いを馳せて～（PS2） | Hakushaku to Yousei (PS2, 5pb) scene text extractor. | — |
| [hanayoi_run.py](hanayoi_run.py) | 花宵ロマネスク · 花宵ロマネスク PS2（SLPS_258.67 / Marvelous×Vridge）（PS2） · 花宵ロマネスク 愛と哀しみ -それは君のためのアリア | 批量驱动 hanayoi_extract.py：多脚本合并成一份成品（一次点击 = 一行）。 | — |
| [hanazakari_extract.py](hanazakari_extract.py) | 花朧 ～戦国伝乱奇～（PSV） | 花朧 ～戦国伝乱奇～ (PSV, PCSG00855, Otomate/Idea Factory) 文本提取 | — |
| [happygift_extract.py](happygift_extract.py) | 誰にでも裏がある -True or Lie？-（PC） · 誰にでも裏がある Happy Gift（PC） | 最终文本提取 | [reallive](../references/engines/reallive.md) |
| [haruka2_eem_extract.py](haruka2_eem_extract.py) | 遙かなる時空の中で２（PSP） · 遥か2PSP（PSP） | 遙かなる時空の中で２ (PSP) 全文本提取  — 最终版 | — |
| [haruka4_extract.py](haruka4_extract.py) | Extractor for 遥かなる時空の中で4（PSP） | Extractor for 遥かなる時空の中で4 (PSP, Koei / Ruby Party). | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [haruka5_extract.py](haruka5_extract.py) | 追記2 本体(遥か5)に同じ問題があるか検証 · 遙かなる時空の中で5（PSP） · 遥かなる時空の中で5（PSP） | 遙かなる時空の中で5 (PSP / ULJM-05821, Koei / Ruby Party) 全文本提取器 | — |
| [haruka6_dict.py](haruka6_dict.py) | 2026-10-03 晚 · 遥か6 DX（Switch） · 遙かなる時空の中で6 DX（Harukanaru Toki no Naka de 6 DX） · 遥か6DX | 遥かなる時空の中で6 DX —— 用語辞典（見出し語＋解説）构建器 v2 | — |
| [haruka6_extract.py](haruka6_extract.py) | 2026-10-03 晚 · 遥か6 DX（Switch） · 遙かなる時空の中で6 DX（Harukanaru Toki no Naka de 6 DX） · 遥か6DX | 遥かなる時空の中で6 DX (Switch) 全文本提取器 v2 | — |
| [haruka_extract.py](haruka_extract.py) | ★Koei CDAR 完全攻略 + 遥か4/遥か3Ultimate 抽出成功 (計5本) | Extractor for Koei / Ruby Party "Harukanaru Toki no Naka de" (遥かなる時空の中で) scripts. | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [hatsukoi_extract.py](hatsukoi_extract.py) | 大人の初恋、はじめます（Switch） | [NS-JP]大人の初恋、はじめます（Nintendo Switch / Bezel Engine）剧本文本提取。 | [bezel-bea](../references/engines/bezel-bea.md) |
| [hb_extract.py](hb_extract.py) | 花笑む彼と & bloom（Him the Smile & Bloom）（Switch） | [NS-JP]花笑む彼と & bloom（Him the Smile & Bloom）文本提取 —— Utage（宴） | [unity](../references/engines/unity.md) |
| [heiligenstadt_extract.py](heiligenstadt_extract.py) | ハイリゲンシュタットの歌（PSV） | 《ハイリゲンシュタットの歌》 (PS Vita / PCSG01070 / eXtend / Unity 5.6.1p4) 全文本提取 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [hg_extract.py](hg_extract.py) | ひぐらしのなく頃に奉＋Origin（Switch） | ひぐらしのなく頃に奉＋Origin (NS) main.snr → 全文本 | [rom2](../references/engines/rom2.md) |
| [hime3_extract.py](hime3_extract.py) | 星の王女3 ～天・地・人の創世記～＋星の約束（PC） | 星の王女3（美蕾 MADOKA GScript / CRPT type 3）文本提取。 | — |
| [himehibi2_eboot.py](himehibi2_eboot.py) | ひめひび 続！二学期 | ひめひび 続！二学期 —— 第 2 段：eboot 串表抽取 + 成品组装。 | — |
| [himehibi2ns_extract.py](himehibi2ns_extract.py) | ひめひび 続！二学期（Switch） | ひめひび ─New Princess Days!!─ 続！二学期 (NS-JP 01009B4012FC6000) 全文本提取。 | — |
| [himehibi_extract.py](himehibi_extract.py) | Extract all displayed text from ひめひび -Princess Days-（PSV） | Extract all displayed text from ひめひび -Princess Days- (PSV, Takuyo gss / LSDARC 'SCR 2.00'). | — |
| [himehibi_ns_extract.py](himehibi_ns_extract.py) | ひめひび -Princess Days-（Switch） | ひめひび -Princess Days-（NS-JP, 0100F8D0129F4000）全文本提取。 | — |
| [hiyoku_extract.py](hiyoku_extract.py) | 比翼は愛薊の彼方へ ～久遠の想～（PC） | [JP]比翼は愛薊の彼方へ ～久遠の想～ (PC / SandalDash) text extractor. | — |
| [honeyvibes_extract.py](honeyvibes_extract.py) | Honey Vibes（Switch） | Honey Vibes (NS 0100FB301E70A000) 剧本提取 —— Unity + 纯文本脚本。 | — |
| [hoshifuru_extract.py](hoshifuru_extract.py) | 星の降る刻（PS2） | 星の降る刻 (PS2-JP) —— UNION/SCRIPT.UNI 文本提取 | — |
| [hoshiiro_extract.py](hoshiiro_extract.py) | 星色のおくりもの（PSP） | 星色のおくりもの (PSP-JP, 2008 Takuyo) full-text extractor. | — |
| [hoshinooujo_yoshitsune_extract.py](hoshinooujo_yoshitsune_extract.py) | 星の王女 ～宇宙意識に目覚めた義経～ final（PC） | [PC-JP]星の王女 ～宇宙意識に目覚めた義経～ final extractor. | — |
| [hoshinoujo2_text.py](hoshinoujo2_text.py) | 星の王女2（PC） | [PC-JP]星の王女2（PC / 美蕾 MADOKA GScript・GSCE 编译包）全文本提取。 | — |
| [hoshinoujo_extract.py](hoshinoujo_extract.py) | 星の王女（PC） | 星の王女 (PC-JP, 2003) — Madoka GScript 旧式 .sce (CRPT 加密) 全文本提取 v1 | — |
| [hoshioji_extract.py](hoshioji_extract.py) | 恋してしまった星の王子 ～誓願院編～（Switch） | [NS-JP]恋してしまった星の王子 ～誓願院編～ 文本提取（Bezel Engine / SCNE / scb_）。 | [bezel-bea](../references/engines/bezel-bea.md) |
| [hoshitsubasa_extract_v10.py](hoshitsubasa_extract_v10.py) | Hoshi no Oujo Hikari no Tsubasa + Koi no Patissier | 最终文本提取 | — |
| [houkago_gsc_extract.py](houkago_gsc_extract.py) | 放課後は白銀の調べ～急急如律令～（PC） | Extract the verified HOUKAGO_KKN XFL/GSC script build, with click/page maps. | — |
| [hy_extract.py](hy_extract.py) | 百華夜光（PSV） · 華ヤカ哉、我ガ一族 幻燈ノスタルジィ for Nintendo Switch（Switch） · 華ヤカ哉、我ガ一族 幻燈ノスタルジィ for Nintendo Switch（76,274 行（Switch） | 華ヤカ哉、我ガ一族 幻燈ノスタルジィ for Nintendo Switch（NS-JP, ichicolumn 自研 .lzs + SCD） | [lzs-scd](../references/engines/lzs-scd.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [ikare_text.py](ikare_text.py) | イカレちんぽ屋 | [JP]イカレちんぽ屋（TVP/KiriKiri + KAG3）→ 一次点击＝一行。 | — |
| [innocentria_extract.py](innocentria_extract.py) | イノセントリア（PC） | Extract Innocentria (NScripter 2.48 / game script ver.1.1). | — |
| [isshoni_gohan_extract.py](isshoni_gohan_extract.py) | いっしょにごはん。（PSP） | いっしょにごはん。 (PSP, 2011 / STCM2L "Oct  7 2010") 文本提取 | — |
| [iza2_build.py](iza2_build.py) | いざ、出陣！恋戦 第二幕 甲斐編（PSP） | いざ、出陣！恋戦 第二幕 ～甲斐編～ —— 按 scenelist 顺序组装全文本。 | — |
| [izasen_extract2.py](izasen_extract2.py) | いざ、出陣！恋戦（PSP） | いざ、出陣！恋戦（PSP）全文本提取 v2：按 [next file] 链定顺序 | — |
| [jade_yks.py](jade_yks.py) | 24時、君のハートは盗まれる～怪盗ジェイド～（PC） | 24時、君のハートは盗まれる～怪盗ジェイド～ 文本抽取（YKC 容器 → YKS 脚本 → 台詞/地の文）。 | — |
| [jewelic_extract.py](jewelic_extract.py) | Jewelic Nightmare（PSP） | Jewelic Nightmare (PSP, Otomate 2013, ULJM06326) 全文本提取 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [jingi_extract.py](jingi_extract.py) | 仁義なき乙女（美蕾 MADOKA GScript / CRPT type 3）（PC） | 仁義なき乙女（美蕾 MADOKA GScript / CRPT type 3）文本提取。 | — |
| [jingi_text.py](jingi_text.py) | 仁義なき乙女 恋恋三昧（Madoka GScript / CRPT .sce）（PC） | [PC-JP]仁義なき乙女 恋恋三昧（Madoka GScript / CRPT .sce）全文本提取。 | — |
| [jusanshi.py](jusanshi.py) | 十三支演義 偃月三国伝1・2（Switch） | 十三支演義 偃月三国伝1・2 (NS) 正文提取 —— 容器链全部打通版。 | — |
| [kaeru_extract.py](kaeru_extract.py) | カエル畑DEつかまえて☆彡（Switch） | カエル畑DEつかまえて☆彡 (NS-JP, TAKUYO) text extract. | — |
| [kag3_ks.py](kag3_ks.py) | Heavenly Blue | KAG3（KiriKiri 2.x）.ks 剧本 → 双版对照文本。 | — |
| [kag_extract.py](kag_extract.py) | One's Inside | KiriKiri/KAG3 シナリオ(.ks) テキスト抽出。 | — |
| [kaleido_extract.py](kaleido_extract.py) | カレイドイヴ（PSV） · マジきゅんっ！ルネッサンス（PSV） | カレイドイヴ (PSV / PCSG00520 / estciel & HuneX) 全文本提取器 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [kamidachi_extract.py](kamidachi_extract.py) | 神立ノ雨、鬼ノ唄（PC） | Ren'Py（RPA-3.0 + .rpy 明文源码）文本提取驱动 —— [PC-JP]神立ノ雨、鬼ノ唄。 | — |
| [kamigami_scr_extract.py](kamigami_scr_extract.py) | 神々の悪戯 Unite Edition（Switch） | 神々の悪戯 Unite Edition（NS）→ 全文本 | [unity](../references/engines/unity.md) |
| [kamikoi_extract.py](kamikoi_extract.py) | 神さまと恋ゴコロ（Switch） | 神さまと恋ゴコロ (NS-JP) text extract ---- Takuyo gss / LSDARC 'SCR 3.00'. | — |
| [kamisama102_extract.py](kamisama102_extract.py) | 神様を殺す102の方式 | NScripter 文本提取器（源自 [PC-JP]神様を殺す102の方式） | — |
| [kamisama_extract.py](kamisama_extract.py) | もし、この世界に神様がいるとするならば。 | もし、この世界に神様がいるとするならば。 —— resources.assets 内 .kaiso 剧本 → 全文本。 | — |
| [kannagi_extract.py](kannagi_extract.py) | 神凪ノ杜 五月雨綴り（Switch） | 神凪ノ杜 五月雨綴り (NS-JP, Unity 2021 IL2CPP, Matatabi) 剧本正文 + 选项提取。 | — |
| [kannou_extract.py](kannou_extract.py) | 官能昔話 ポータブル（PSP） | 官能昔話 ポータブル (PSP, ULJM06015, vndb v9071) 全文本提取 | — |
| [kanuchi_text.py](kanuchi_text.py) | カヌチ 二つの翼（PSP） | カヌチ 二つの翼 (PSP / Idea Factory 'YDP1' -> SCRIPT_LSB) 剧本文本提取 | [idea-factory-ydp-lsb](../references/engines/idea-factory-ydp-lsb.md) |
| [kare_dx_extract.py](kare_dx_extract.py) | カレと彼の間で -DX ツインズパック版-（PC） · 神曲奏界ポリフォニカ Memories White～エンドレスアリア～（PC） · 神曲奏界ポリフォニカ Memories White～ファーストエモーション～（PC） · 誰にでも裏がある -True or Lie？-（PC） | カレと彼の間で DX: reuse rlvm-derived rl_decomp/rl_parse. | [reallive](../references/engines/reallive.md) |
| [katakago_extract.py](katakago_extract.py) | 貴方の鳥籠（PC） | [PC-JP]貴方の鳥籠（LiveMaker 3 / VF ver=102 / TpWord 102）驱动。 | [livemaker](../references/engines/livemaker.md) |
| [kazahanaki_extract.py](kazahanaki_extract.py) | 2026-10-07（深夜）[PSP-JP]遙かなる時空の中で5 風花記（FD）（PSP） · 遙かなる時空の中で5 風花記（PSP） | 遙かなる時空の中で5 風花記 (PSP / ULJM-05950, Koei / Ruby Party) 全文本提取器 | — |
| [kaze_extract.py](kaze_extract.py) | 風色サーフ（PS2） | 風色サーフ (PS2) 全文本抽出器。 | — |
| [kedamono_ns_build.py](kedamono_ns_build.py) | 猛獣使いと王子様 ～Flower & Snow～ for Nintendo Switch（Switch） | 猛獣使いと王子様 ～Flower & Snow～ for Nintendo Switch —— 成品构建。 | — |
| [kimigatame_text.py](kimigatame_text.py) | 君がため、恋し乱れし月の華（PC） | [PC-JP]君がため、恋し乱れし月の華。 KiriKiri RAT（linemode=free）全文本提取。 | — |
| [kimikare_extract.py](kimikare_extract.py) | キミカレ（PSP） | キミカレ ～キミとカレはじめました～ (PSP, 2012 / STCM2L) 文本提取 | — |
| [klap_extract.py](klap_extract.py) | KLAP!! for Nintendo Switch（Switch） | KLAP!! for Nintendo Switch (NS) STCM2L 文本提取（STCM2L Apr 12 2018 18:22:39 变体）。 | — |
| [kochouran_text.py](kochouran_text.py) | 胡蝶蘭～君が待つあの場所へ～（PC） | Extract Kochouran KAG text using source control flow and Win32 font advances. | — |
| [koibana_extract.py](koibana_extract.py) | 恋花デイズ（PSP） | 恋花デイズ (PSP / Otomate, STCM2L in CRI CPK) 文本提取 | — |
| [koibann2_extract.py](koibann2_extract.py) | 恋愛番長2 MidnightLesson!!!（PSP） | 恋愛番長2 MidnightLesson!!! (PSP-JP / Rejet×Otomate 2011) 剧本文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [koibann_extract.py](koibann_extract.py) | 恋愛番長 命短し、恋せよ乙女！ Love is Power（PSP） | 恋愛番長 命短し、恋せよ乙女！ Love is Power (PSP-JP / Rejet×Otomate 2010) 剧本文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [koigig_extract.py](koigig_extract.py) | KoiGIG ～DEVIL×ANGEL～ (TWOFIVE / DonMaccow, 2007) · 外部核对（vndb v12478 + 巴哈姆特 cast） | KoiGIG ～DEVIL×ANGEL～ (TWOFIVE / DonMaccow, 2007) 文本提取器 | — |
| [koinohana_extract.py](koinohana_extract.py) | 恋の花咲く百花園（Switch） | [NS-JP]恋の花咲く百花園 text extract (Takuyo gss / SCR 3.00, unpacked OBJ). | — |
| [koishiba_run.py](koishiba_run.py) | 恋は校則に縛られない（PSP） · 恋は校則に縛られない！（PSP） | 恋は校則に縛られない！（PSP）—— USRDIR/DATA/sc.cpk → 全文本。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [koutari_extract2.py](koutari_extract2.py) | 神足町人妖譚 ~迷イ子ノ章~（PC） | 神足町人妖譚 (PC-JP / System-NNN「NNNLib」engine) 全文本提取 · 定稿（对齐槽版） | — |
| [ks_kag_text.py](ks_kag_text.py) | Cocoon · Cocoon BN -Cocoon Black Noise- · Collision×Collision · CORE X ~Happy Halloween!~ · Day's Eye · Daytime and Night · Dream Dreamer · EveningGlow · FRAGILE · Geheime Basis（PC） · invisible sign -イス- · RUSH×UP！ · TrickCall · Truth and False · あかやあかしやあやかしの · うつしみよつる · アンダーブルー · ウウウルトラC · 図書室のネヴァジスタTHE FOOL | KAG3（KiriKiri）剧本 .ks -> 全文本（双版：段行＋合并行） | — |
| [kuro_build.py](kuro_build.py) | 蒼黒の楔 ～緋色の欠片 玉依姫奇譚～（Switch） | 蒼黒の楔 (NS-JP, Unity/Utage) 剧本 → 全文本（双版对照） | [unity](../references/engines/unity.md) |
| [l2ll_extract.py](l2ll_extract.py) | D.C. Girl's Symphony Pocket ~ダ・カーポ～ガールズシンフォニーポケット（PSP） · L2 Love×Loop（PS2） | L2 Love×Loop (PS2 / Idea Factory / SLPM-55191) 剧本文本提取 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [lamento_extract.py](lamento_extract.py) | Lamento -BEYOND THE VOID- (Windows 10 Support Edition)（PC） · sweetpool | Lamento -BEYOND THE VOID- (Windows 10 Support Edition)  —  Nitroplus NPA / NSS | [nitroplus](../references/engines/nitroplus.md) |
| [lastconvert_extract.py](lastconvert_extract.py) | Last Convert（PC） | Last Convert (NScripter / nscript.dat, 全字节 XOR 0x84) -> 双版对照文本 | — |
| [lastescort_extract.py](lastescort_extract.py) | ラストエスコート -Club Katze-（PSP） | ラストエスコート -Club Katze- (PSP) 全文本提取 —— 通用驱动 | — |
| [lastescort_ps2_extract.py](lastescort_ps2_extract.py) | ラスト・エスコート 〜深夜の黒蝶物語〜（PS2） | ラスト・エスコート 〜深夜の黒蝶物語〜 (PS2 / SLPS_255.91 / D3P・Vingt-et-un) 全文本提取 | — |
| [le_extract.py](le_extract.py) | DIABOLIK LOVERS LOST EDEN（PSV） | DIABOLIK LOVERS LOST EDEN (PSV, PCSG00910) 文本提取 | — |
| [littleaid_extract.py](littleaid_extract.py) | Little Aid（PSP） · Little Aid ポータブル（PSP） | Little Aid Portable (PSP-JP, 2007 Takuyo, ULJM-05...) full-text extractor. | — |
| [littleanchor_extract.py](littleanchor_extract.py) | リトルアンカー（PS2） | リトルアンカー（PS2-JP / SLPS-25929 / Vridge）全文本提取。 | — |
| [livemaker_parallel_lovers.py](livemaker_parallel_lovers.py) | Parallel Lovers 前編 | [JP]Parallel Lovers 前編（LiveMaker 3）文本提取（自定义剧情顺序版）。 | [livemaker](../references/engines/livemaker.md) |
| [livemaker_sugar.py](livemaker_sugar.py) | Sugar | [JP]Sugar（LiveMaker 3 / 野良猫企画 2016）文本提取驱动。 | [livemaker](../references/engines/livemaker.md) |
| [livemaker_tsukimori.py](livemaker_tsukimori.py) | 月と森とあなたとわたし（PC） | [PC-JP]月と森とあなたとわたし（LiveMaker 3, ver102）提取驱动。 | [livemaker](../references/engines/livemaker.md) |
| [livemaker_utahime.py](livemaker_utahime.py) | 歌姫と王様（PC） | [PC-JP]歌姫と王様（LiveMaker 3 / VF ver=102）文本提取。 | [livemaker](../references/engines/livemaker.md) |
| [lovebeat_extract.py](lovebeat_extract.py) | 放課後のLove Beat（PS2） | 放課後のLove Beat（PS2 / HuneX ADVD, SLPM_655.79）文本提取。 | — |
| [lovepeace_extract.py](lovepeace_extract.py) | 恋戦隊LOVE＆PEACE THE P.S.P.（PSP） · 恋戦隊LOVE＆PEACE_THE_PSP（PSP） | 恋戦隊LOVE＆PEACE THE P.S.P. (PSP / BROCCOLI 2012) MES.DAT text extractor. | — |
| [loverevo_extract.py](loverevo_extract.py) | 乙女的恋革命★ラブレボ!! Portable（PSP） | 乙女的恋革命★ラブレボ!! Portable (PSP) 全文本提取 | — |
| [loveroot_extract.py](loveroot_extract.py) | ラブルートゼロ kisskiss☆ラビリンス（PS2） | PS2『ラブルートゼロ kisskiss☆ラビリンス』(Dimple/Asgard 2010) 全文本抽出。 | — |
| [lp_extract.py](lp_extract.py) | DIABOLIK LOVERS LUNATIC PARADE（PSV） | DIABOLIK LOVERS LUNATIC PARADE (PSV, PCSG00826) 文本提取 | — |
| [lpv_extract_final.py](lpv_extract_final.py) | LoverPretend（Switch） | LoverPretend (NS-JP) 文本提取 —— 定稿 v2 | [stcm2l](../references/engines/stcm2l.md) |
| [lucian_extract.py](lucian_extract.py) | Lucian Bee's（PSP） · Lucian Bees Resurrection Supernova（PSP） | Lucian Bee's: Resurrection Supernova (PSP, 2010, HuneX IKA SEQ SYSTEM v3.4) | — |
| [lucianj_extract.py](lucianj_extract.py) | ルシアンビーズ ジャスティス イエロー（PSP） | Lucian Bee's: Justice Yellow (PSP, 2010, 5pb./HuneX) —— 全文本提取 | [hunex-als](../references/engines/hunex-als.md) |
| [lucianv_extract.py](lucianv_extract.py) | ルシアンビーズ イビル ヴァイオレット（PSP） | Lucian Bee's: Evil Violet (PSP, 2010, 5pb) —— 全文本提取 | — |
| [lucky1_extract.py](lucky1_extract.py) | ラッキードッグ１（PC） | [JP]ラッキードッグ１ (PC / Will-ARCG + Kagura TLV bytecode) text extractor. | — |
| [luckydog_extract.py](luckydog_extract.py) | ラッキードッグ1 Secret Diary F（PC） · ラッキードッグ1 Secret Diary L | ラッキードッグ1 Secret Diary F（PC-JP，Adobe AIR／jp.co.woga.was 引擎）文本提取器。 | — |
| [lustras_extract.py](lustras_extract.py) | ラストラス（PC） | Extract the bundled Innocentria Lustras 1.7 NScripter script. | — |
| [madoka_gscript_extract.py](madoka_gscript_extract.py) | 夢をもう一度＋幸福の風（PC） | Madoka GScript (CRPT) scenario text extractor — engine: 美蕾/MP2. | — |
| [majikyun_extract.py](majikyun_extract.py) | マジきゅんっ！ルネッサンス（PSV） | マジきゅんっ！ルネッサンス (PSV / PCSG00852 / HuneX & BROCCOLI) 全文本提取器 | — |
| [makumatsu_extract.py](makumatsu_extract.py) | 幕末Rock 超魂（PSV） | 《幕末Rock 超魂》(PS Vita / PCSG00425 / Marvelous) 全文本提取 | [mz-cmdstream](../references/engines/mz-cmdstream.md) |
| [manimani_extract.py](manimani_extract.py) | 花咲くまにまに（PSV） | 花咲くまにまに (PSV, PCSG00366, MAGES. / SC3) 文本提取。 | — |
| [marginal4_extract.py](marginal4_extract.py) | MARGINAL#4 IDOL OF SUPERNOVA（PSV） | [PSV-JP] MARGINAL#4 IDOL OF SUPERNOVA  (PCSG00448, Otomate x Rejet / Idea Factory) | — |
| [marginal4rtg_extract.py](marginal4rtg_extract.py) | MARGINAL#4 ROAD TO GALAXY（PSV） | [PSV-JP] MARGINAL#4 ROAD TO GALAXY  (PCSG01008, Otomate x Rejet / Idea Factory) | — |
| [matsurika_build.py](matsurika_build.py) | マツリカの炯-kEi- 天命華燭伝（Switch） | マツリカの炯-kEi- 天命華燭伝 文本成行（在 matsurika_extract 之上） | [vridge](../references/engines/vridge.md) |
| [mdb_scen_text.py](mdb_scen_text.py) | BOY×BOY 〜私立光稜学院誠心寮〜 | VB5 自研 AVG（剧本库＝Access Jet .MDB，台本＝日文指令 DSL）→ 「一次点击 = 一行」。 | [overflow-adv](../references/engines/overflow-adv.md) |
| [meiji_extract.py](meiji_extract.py) | 明治活劇 ハイカラ流星組（Switch） · 明治活劇 ハイカラ流星組 －成敗しませう、世直し稼業－（Switch） | 明治活劇 ハイカラ流星組 (NS-JP) テキスト抽出. | [lzs-scd](../references/engines/lzs-scd.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [meine_extract.py](meine_extract.py) | マイネリーベ 優美なる記憶（PS2） | [PS2-JP] マイネリーベ 優美なる記憶 text extractor. | — |
| [mermaid_run.py](mermaid_run.py) | マーメイドプリズム（PS2） | マーメイドプリズム (PS2-JP) 全文本提取。 | — |
| [messiah_extract.py](messiah_extract.py) | メサイア（PC） | メサイア（PC / GsWin「DataPack5」+ Scw5.x 脚本）文本提取器。 | — |
| [messiah_pp_extract.py](messiah_pp_extract.py) | メサイア～パラノイア・パラドックス～（PC） | メサイア～パラノイア・パラドックス～（PC 2008 / GsWin「DataPack5」+ Scw5.x）文本提取器。 | — |
| [minus8_extract.py](minus8_extract.py) | マイナスエイト（-8）（PSP） | マイナスエイト (-8)  PSP, Otomate/Rejet, ULJM06341, vndb v12155  —— 全文本提取 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [miryo_extract.py](miryo_extract.py) | 比翼は愛薊の彼方へ ～未了の因～（PC） | [JP]比翼は愛薊の彼方へ ～未了の因～ (PC 2006 / SandalDash) text extractor. | [sandaldash-rk1](../references/engines/sandaldash-rk1.md) |
| [mist_extract.py](mist_extract.py) | ミストニアの翅望 -The Lost Delight- | ミストニアの翅望 -The Lost Delight- —— Unity/UTXT 文本（与 テミラーナ 同引擎）。 | — |
| [mitsu_extract.py](mitsu_extract.py) | 蜜×蜜ドロップス LOVE×LOVE HONEY LIFE（PS2） | 蜜×蜜ドロップス LOVE×LOVE HONEY LIFE (PS2-JP, SLPM-663.81 / Otomate·Design Factory 2006) | — |
| [mizu2_extract.py](mizu2_extract.py) | KID / 2009-12-16（PSP） · 水の旋律2 ～緋の記憶～（PSP） | 水の旋律2 ～緋の記憶～ (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本 | [thfs](../references/engines/thfs.md) |
| [mizu_extract.py](mizu_extract.py) | 水の旋律（PSP） · 水の旋律2～緋の記憶～（PSP） | 水の旋律 (PSP-JP) 文本提取 —— THFS 容器 / cp932 内联脚本 | — |
| [mizumelody_text.py](mizumelody_text.py) | 水の旋律 ～協奏曲～（PC） | 水の旋律 ～協奏曲～ (PC) 剧本成行 —— mlk/ADV 脚本 (cp932) | — |
| [mk2_extract.py](mk2_extract.py) | リトルプリンセス マール王国の人形姫２（Switch） | [NS-JP]リトルプリンセス マール王国の人形姫２ —— message.bin → 成行 | [vfs3-pak](../references/engines/vfs3-pak.md) |
| [mk3_extract.py](mk3_extract.py) | 天使のプレゼント マール王国物語（Switch） | [NS-JP]天使のプレゼント マール王国物語 —— talk.dat / script.dat → 成行 | [vfs3-pak](../references/engines/vfs3-pak.md) |
| [mk_extract.py](mk_extract.py) | マール王国の人形姫（Switch） | マール王国の人形姫（NS）文本提取器 | [vfs3-pak](../references/engines/vfs3-pak.md) |
| [ml2_text.py](ml2_text.py) | マイネリーベII ~誇りと正義と愛~（PS2） | 从 SCPT 场景脚本抽取正文/选项（一行＝一次点击）。 | — |
| [mn_extract.py](mn_extract.py) | 華ヤカ哉、我ガ一族 モダンノスタルジィ for Nintendo Switch（Switch） · 華ヤカ哉、我ガ一族 モダンノスタルジィ for Nintendo Switch（38,925 行（Switch） | 華ヤカ哉、我ガ一族 モダンノスタルジィ for Nintendo Switch（NS-JP, ichicolumn 自研 .lzs + SCD） | [lzs-scd](../references/engines/lzs-scd.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [moneyparasite_extract.py](moneyparasite_extract.py) | Money Parasite 〜嘘つきな女〜（Switch） | Money Parasite 〜嘘つきな女〜 (TAKUYO gss / SCR 2.00) text extractor. | — |
| [mono_extract.py](mono_extract.py) | モノクローム・ファクター cross road（PS2） | Monochrome Factor - Cross Road (PS2, 5pb) scene text extractor. | — |
| [moon_atl_extract.py](moon_atl_extract.py) | 月ノ光太陽ノ影（PC） | 月ノ光太陽ノ影 (PC/ATL engine) 全文本提取 | — |
| [mothergoose_extract.py](mothergoose_extract.py) | マザーグースの秘密の館（PSP） | マザーグースの秘密の館（PSP / 2011, Otomate）文本提取 | — |
| [mtj_extract.py](mtj_extract.py) | マツリカの炯 -kEi- 天命胤異伝（Switch） | [NS-JP]マツリカの炯 -kEi- 天命胤異伝 全文本提取 | [otomate-tatc-rson](../references/engines/otomate-tatc-rson.md) |
| [musketeer_extract.py](musketeer_extract.py) | Musketeer（PSP） · ★★ マスケティア（PSP） · マスケティア（PSP） | Musketeer (PSP/5pb) .evb -> text. | — |
| [mysteria_pc_text.py](mysteria_pc_text.py) | 断罪のマリア ラ･カンパネラ · 絶対迷宮 秘密のおやゆび姫（PSV） · 英国探偵ミステリア The Crown（PC） | PC Japanese Mysteria: Camellia LIBP (1024-byte sectors, 4096 alignment), Malie VM. | [malie](../references/engines/malie.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [mysteria_text.py](mysteria_text.py) | 英国探偵ミステリア The Crown（PSV） | 英国探偵ミステリア The Crown (PSV) —— Malie exec.dat → 全文本（一次点击 = 一行）。 | — |
| [nana_extract.py](nana_extract.py) | NANA -ナナ-（PS2） | [PS2-JP] NANA -ナナ- text extractor. | — |
| [naninovel_assemble.py](naninovel_assemble.py) | 魔女と亡霊のヴォロンテ（Switch） | 把 naninovel_extract.py 的 _scripts.json 组装成 §0 规范成品 txt。 | [naninovel](../references/engines/naninovel.md) |
| [neoange_psp_extract.py](neoange_psp_extract.py) | ネオアンジェリークSpecial（PSP） | ネオアンジェリークSpecial (PSP-JP, Koei) 全文本提取 | [koei-cdar](../references/engines/koei-cdar.md) |
| [neoangelique_extract.py](neoangelique_extract.py) | ネオ アンジェリーク 天使の涙（PSV） | ネオ アンジェリーク 天使の涙  (PSV-JP, PCSG01068, Otomate / Idea Factory)  全文本提取 | [dat-pak-scd](../references/engines/dat-pak-scd.md) |
| [neon_dialog.py](neon_dialog.py) | ネオンクラッシュ -Echoes of the Lost-（Switch） | ネオンクラッシュ -Echoes of the Lost- 正文提取（成品生成）。 | — |
| [niladmirari_extract.py](niladmirari_extract.py) | ニル・アドミラリの天秤 色ドリ撫子（Switch） | ニル・アドミラリの天秤 色ドリ撫子 (Switch) —— 全文本提取器 | — |
| [nisenochigiri_extract.py](nisenochigiri_extract.py) | 二世の契り（PSP） | 二世の契り (PSP-JP, Otomate, 2011) 全文本提取 | — |
| [nisenochigiri_fd_extract.py](nisenochigiri_fd_extract.py) | 二世の契り 想い出の先へ（Nise no Chigiri FD）（PSP） | FD『二世の契り 想い出の先へ』(PSP-JP, Otomate, STCM2L) 全文本提取 —— 泛化版。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [norn9_extract.py](norn9_extract.py) | Norn9 ～Norn + Nonette～ Act Tune（PSV） | Norn9 ～Norn + Nonette～ Act Tune  (PSV, PCSG00833) 剧本文本提取 | — |
| [ns_talkbmp_text.py](ns_talkbmp_text.py) | DAN☆ICE | NScripter：正文 + **位图台词（talk_*.bmp ＋ 作者 ; 注释）** 双版对照提取 | — |
| [nscripter_dat.py](nscripter_dat.py) | Last trick Memories-二つの悲しき旋律- · Last trick ～最後の策略～ · Love Me Do · イワンは見た! · 海色小夜曲ーウミイロセレナーデー（PC） | NScripter nscript.dat → 双版对照文本（海色小夜曲ーウミイロセレナーデー）。 | — |
| [nscripter_ivan.py](nscripter_ivan.py) | イワンは見た! | NScripter script text extractor — [JP]イワンは見た! (WILD ROSE doujin ADV) | — |
| [oga_sts_extract.py](oga_sts_extract.py) | O*G*A 鬼ごっこロワイアル ハンターは孤島で恋をする（PSP） | O*G*A 鬼ごっこロワイアル ハンターは孤島で恋をする (PSP-JP / Idea Factory・Otomate) | — |
| [oga_tob_extract.py](oga_tob_extract.py) | O＊G＊A 鬼ごっこロワイアル ハンターは孤島で恋をする（PSP） | O*G*A 鬼ごっこロワイアル (PSP, Idea Factory/Otomate "oni") —— .tob 字节码级框提取 | — |
| [ojisama_extract.py](ojisama_extract.py) | ２人の王子（AbelCain / 「シナリオくん」エンジン） | [JP]２人の王子（AbelCain / 「シナリオくん」エンジン）文本提取 | — |
| [ol_extract.py](ol_extract.py) | オランピアソワレ Catharsis for Nintendo Switch（Switch） · オランピアソワレ Catharsis for Nintendo Switch（48,531 行（Switch） | [NS-JP] オランピアソワレ Catharsis for Nintendo Switch —— STCM2L 文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [omegavamp_extract.py](omegavamp_extract.py) | オメガヴァンパイア（Switch） | オメガヴァンパイア (NS) SCRIPT.PAK → 全文本（一行＝一次点击）。 | — |
| [oni_extract.py](oni_extract.py) | 十鬼の絆（Switch） · 十鬼の絆 for Nintendo Switch（Switch） | [NS-JP]十鬼の絆 (Bond Of Ten Oni) STCM2L 文本提取。 | — |
| [orange_build.py](orange_build.py) | オレンジハニー 〜僕はキミに恋してる〜（PS2） | Orange Honey 全文本成行 | — |
| [orfleur_stbl_extract.py](orfleur_stbl_extract.py) | オルフレール 定案 · オルフレール ～幸福の花束～（PSV） | オルフレール ～幸福の花束～ (PSV / PCSG00919, dramatic create「Orfre」/ DCVM) | [dcvm](../references/engines/dcvm.md) |
| [os_extract.py](os_extract.py) | オランピアソワレ（本篇）for Nintendo Switch（Switch） · オランピアソワレ（本篇）for Nintendo Switch（46,055 行（Switch） | [NS-JP] オランピアソワレ（本篇）for Nintendo Switch —— STCM2L 文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [otome_kayuu_extract.py](otome_kayuu_extract.py) | 燃えよ！ 乙女道士 ～華遊恋語～（Switch） | Otomate STCM2L · Switch「函数指针型」文本提取（燃えよ！乙女道士 ～華遊恋語～） | — |
| [ouma_build_text.py](ouma_build_text.py) | 逢魔が刻 | 《逢魔が刻 ～かくりよの縁～》系统/资料文本整理 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [nis-nml](../references/engines/nis-nml.md) |
| [ouma_extract.py](ouma_extract.py) | 逢魔が刻 | 《逢魔が刻 ～かくりよの縁～》(PSVita / PCSG00769) 游戏内文本提取 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [nis-nml](../references/engines/nis-nml.md) |
| [ouma_story.py](ouma_story.py) | 逢魔が刻 | 《逢魔が刻 ～かくりよの縁～》本編 ADV シナリオ抽出 (NML スクリプト) | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [ouran_extract.py](ouran_extract.py) | 桜蘭高校ホスト部（PS2） | 桜蘭高校ホスト部 (PS2-JP, SLPM-667.38 / Otomate·Idea Factory 2006) 剧本文本提取 | — |
| [overreq_extract.py](overreq_extract.py) | OVER REQUIEMZ（Switch） | [NS-JP]OVER REQUIEMZ —— 全文本提取（Unity + Otomate 命令式脚本 DSL）。 | [overflow-adv](../references/engines/overflow-adv.md) · [unity](../references/engines/unity.md) |
| [oyayubi_psv_extract.py](oyayubi_psv_extract.py) | 絶対迷宮 秘密のおやゆび姫（PSV） | PCSG00611: extract narrative text from MalieVita scripts only. | [malie](../references/engines/malie.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [ozmafia_extract.py](ozmafia_extract.py) | OZMAFIA!! -vivace-（Switch） · スチームプリズン（Switch） · 新テニスの王子様 LET’S GO!! 〜Daily Life〜 from RisingBeat（Switch） | OZMAFIA!! -vivace-（Nintendo Switch, 01002BE0118AE000, HuneX「Ogre」系 Switch 变体） | — |
| [palais_reine_extract.py](palais_reine_extract.py) | Palais de Reine（PS2） | Palais de Reine (PS2 JP, SLPM-66817) compiled native-script text extractor. | — |
| [pandora_extract.py](pandora_extract.py) | PANDORA · PANDORA ～君の名前を、僕は知る～（PS2） | PANDORA ～君の名前を、僕は知る～ (PS2, Otomate / Idea Factory 2010) 剧本文本提取 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [panic_extract.py](panic_extract.py) | Panic Palette ～パニック パレット～（Switch） | Panic Palette (NS-JP, TAKUYO) text extract. | — |
| [paradigm_paradox_extract.py](paradigm_paradox_extract.py) | Paradigm Paradox (Regista advGame engine) · 结果 | Paradigm Paradox (Regista advGame engine) 全文本提取器 —— 定稿。 | — |
| [paradise_jp_extract.py](paradise_jp_extract.py) | Paradise（PS2） | [JP]Paradise (PS2 / D3P Daisy2 / DDP3) 全文本提取。 | [daisy2-ddp](../references/engines/daisy2-ddp.md) |
| [paradise_musubi_extract.py](paradise_musubi_extract.py) | Paradise 結-MUSUBI-（PS2） | [JP]Paradise 結-MUSUBI- (PS2 / D3P Daisy2 / DDP3) 全文本提取。 | [daisy2-ddp](../references/engines/daisy2-ddp.md) |
| [paradise_pfk_extract.py](paradise_pfk_extract.py) | Paradise 極-KIWAME- | [JP] Paradise 極-KIWAME- (Daisy2 / DDP3) text extractor. | [daisy2-ddp](../references/engines/daisy2-ddp.md) |
| [pcube_extract.py](pcube_extract.py) | ピリオドキューブ ～鳥籠のアマデウス～（PSV） | ピリオドキューブ ～鳥籠のアマデウス～ (PSV, PCSG00853) 剧本文本提取 | — |
| [pe_extract.py](pe_extract.py) | ピオフィオーレの晩鐘 -Episodio1926-（Switch） · ピオフィオーレの晩鐘 -Episodio1926-（45,857 行（Switch） | [NS-JP] ピオフィオーレの晩鐘 -Episodio1926- —— STCM2L 文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [pentagon_build.py](pentagon_build.py) | Pentagon Syndrome（PC） | Pentagon Syndrome（LiveMaker/LiveNovel LSB v117）成行器 | — |
| [perfect_prince_extract.py](perfect_prince_extract.py) | Perfect Prince (GimmickHouse 2002) | [JP]Perfect Prince (GimmickHouse 2002) — TextScript(c-system) 全文本提取器 | — |
| [peta_extract.py](peta_extract.py) | ペット探偵Y's (AMEDEO, RealLive) | ペット探偵Y's (AMEDEO, RealLive) 文本提取。 | [reallive](../references/engines/reallive.md) |
| [peterpan_extract.py](peterpan_extract.py) | 新装版 お菓子な島のピーターパン ~Sweet Never Land~（PSV） | QuinRose Qoo (PSV) —— [PSV-JP]新装版 お菓子な島のピーターパン 剧本成行。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [petitfleur_text.py](petitfleur_text.py) | Petit Fleur -丘を渡るクリスタルの風- (Macromedia Director 10.1 / RIFX, zlib 分块) | [JP]Petit Fleur -丘を渡るクリスタルの風-  (Macromedia Director 10.1 / RIFX, zlib 分块) | — |
| [petitfour_extract.py](petitfour_extract.py) | プティフール（PS2） | プティフール (PS2-JP, SLPM-66945 / Otomate·Design Factory 2008) 剧本文本提取 | — |
| [pf_extract.py](pf_extract.py) | ピオフィオーレの晩鐘 -ricordo-（Switch） · ピオフィオーレの晩鐘 -ricordo-（46,566 行（Switch） | [NS-JP] ピオフィオーレの晩鐘 -ricordo- —— STCM2L 文本提取 | [stcm2l](../references/engines/stcm2l.md) |
| [pigeon_blood_extract.py](pigeon_blood_extract.py) | Pigeon Blood（PC） | [JP]Pigeon Blood (PC / PIL-SLASH / D3P Daisy2 DDP3) 全文本提取。 | [daisy2-ddp](../references/engines/daisy2-ddp.md) |
| [plasticboys_extract.py](plasticboys_extract.py) | Plastic Boys ～水色のキモチ～ | [JP]Plastic Boys ～水色のキモチ～ 全文本提取 | — |
| [pleasure_text.py](pleasure_text.py) | PLEASURE☆ | 最终文本提取 | — |
| [pnm_extract.py](pnm_extract.py) | プリンセスナイトメア | Princess Nightmare (PS2, SLPM-66973) script text extractor. | [stcm2l](../references/engines/stcm2l.md) · [system-nnn](../references/engines/system-nnn.md) · [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) |
| [poi_extract.py](poi_extract.py) | 『っポイ!』ひと夏の経験!?（PS2） | 『っポイ!』ひと夏の経験!? (PS2-JP, SLPM-55012 / Otomate·Design Factory 2008) 剧本文本提取 | — |
| [polwhite_extract.py](polwhite_extract.py) | 神曲奏界ポリフォニカ Memories White～エンドレスアリア～（PC） · 神曲奏界ポリフォニカ Memories White～ファーストエモーション～（PC） | Polifonica Memories White EA: checked RealLive bytecode, click/page export. | [reallive](../references/engines/reallive.md) |
| [possession_extract.py](possession_extract.py) | Extractor for Possession Magenta（PSV） | Extractor for Possession Magenta (ポゼッション マゼンタ, PSV, PCSG00509). | — |
| [powdergray_extract.py](powdergray_extract.py) | powdergray | 最终文本提取 | — |
| [prince5_extract.py](prince5_extract.py) | 5人の恋プリンス ~ヒミツの契約結婚~（PSV） | 5人の恋プリンス ~ヒミツの契約結婚~ (PSV, PCSG00590) 文本提取 | [asgard-tat](../references/engines/asgard-tat.md) |
| [prince_stride_run.py](prince_stride_run.py) | プリンス・オブ・ストライド（PSV） | プリンス・オブ・ストライド (PSV PCSG00491) —— sc.cpk → 全文本（2026-10-12）。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [princessbritania_text.py](princessbritania_text.py) | Princess Britania～ミューズの宝剣～（PC） | [PC-JP]Princess Britania～ミューズの宝剣～（KiriKiri XP3 ＋ Crafter/RAT 扩展 KAG3 · linemode=free）全文本提取。 | — |
| [prometheus_extract.py](prometheus_extract.py) | Live x Evil 熱砂のプロメテウス | [JP]Live x Evil 熱砂のプロメテウス — KiriKiri XP3 / KAG3 全文本提取器 | — |
| [ps2_game.py](ps2_game.py) | 「待提取」8本（PS2/PSP/PSV） | 最终文本提取 | — |
| [psycemo6_extract.py](psycemo6_extract.py) | PsychicEmotion6（PSV） | PsychicEmotion6 (PSV / PCSG00815 / Otomate x Idea Factory / 2015) 全文本提取 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [psychicrain_text.py](psychicrain_text.py) | Psychic Rain（PC） | [PC-JP]Psychic Rain — REAL scenario extractor. | [malie](../references/engines/malie.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [psyeclipse_extract.py](psyeclipse_extract.py) | PSYCHIC ECLIPSE-サイキックイクリプス- | 最终文本提取 | — |
| [qualia_extract.py](qualia_extract.py) | Qualia～クオリア～（PC） | [JP]Qualia～クオリア～ テキスト抽出 (KiriKiri/KAG3, data.xp3 内嵌 PE ラップ) | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [radian_extract.py](radian_extract.py) | ラディアンテイル（本体，非 FD）（Switch） | ラディアンテイル（本体，非 FD）—— STCM2L "May 18 2015" 变体 → 全文本。 | — |
| [rakido_extract.py](rakido_extract.py) | RAKIDOMania black dog · RAKIDOMania yellow star | RAKIDOMania black dog 文本提取器。 | — |
| [rakuen_extract.py](rakuen_extract.py) | 楽園男子 ～誰も知らない もう一つの楽園～（PSP） | 楽園男子 ～誰も知らない もう一つの楽園～ (PSP, Takuyo gss / LSDARC V.100 'SCR 2.00') | — |
| [ratw_extract.py](ratw_extract.py) | Round Around the World | RATW 提取：分离式 VF（game.ext 目录 + game.dat 数据）→ 复用 livemaker_extract 多脚本管线。 | [livemaker](../references/engines/livemaker.md) |
| [rdf_extract.py](rdf_extract.py) | レンドフルール for Nintendo Switch（Switch） · レンドフルール for Nintendo Switch（36,583 行（Switch） | [NS-JP]レンドフルール for Nintendo Switch 全文本提取（Otomate STCM2L / CPK） | [stcm2l](../references/engines/stcm2l.md) |
| [realrode_extract.py](realrode_extract.py) | Real Rode ポータブル（PSP） · Real Rode ポータブル（リアルロデ | Real Rode ポータブル (PSP, HuneX「IKA SEQ SYSTEM v3.1」) 全文本提取。 | [hunex-ika](../references/engines/hunex-ika.md) |
| [rear_extract.py](rear_extract.py) | 8本の攻防続き | リアフェレス（Unity）TextAsset 场景脚本提取 → リアフェレス.txt。 | — |
| [recall_extract.py](recall_extract.py) | Recall（PC） | [JP]Recall (KiriKiri / DropWave OTag 加扰 .ks) 全文本提取器。 | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [redbell_dialog.py](redbell_dialog.py) | レッドベルの慟哭（Switch） | レッドベルの慟哭 正文提取（成品生成）。 | — |
| [renpy_text.py](renpy_text.py) | Seiyuu Danshi! | Ren'Py .rpy 文本抽取器（通用） | — |
| [renri_extract.py](renri_extract.py) | 比翼は愛薊の彼方へ ～連理の夢～（PC） | [JP]比翼は愛薊の彼方へ ～連理の夢～ (PC 2008 / SandalDash) text extractor. | [sandaldash-rk1](../references/engines/sandaldash-rk1.md) |
| [requartz_extract.py](requartz_extract.py) | Re;quartz · Re;quartz After Love Story（Adobe AIR ＋ AIRNovel / anbooks「als」） | Re;quartz After Love Story（Adobe AIR ＋ AIRNovel / anbooks「als」）全文本提取。 | — |
| [requartz_kojitsudan_extract.py](requartz_kojitsudan_extract.py) | Re;quartz · Re;quartz零度◆後日談ノベルゲーム | [JP]Re;quartz零度◆後日談ノベルゲーム 文本提取器 (NW.js + TyranoScript, .ks) | — |
| [requartz_main_text.py](requartz_main_text.py) | Re;quartz（PC） | [JP]Re;quartz (PC / Adobe AIR, B-cluster engine) .an 剧本 -> 全文本（双版对照） | — |
| [requartz_pc_text.py](requartz_pc_text.py) | Re;quartz · Re;quartz零度 | 最终文本提取 | — |
| [restart_extract.py](restart_extract.py) | REstart (吉里吉里 KAG3) | REstart (吉里吉里 KAG3) 剧本文本提取 —— 双版对照（段行＋合并行）。 | — |
| [revepc_extract.py](revepc_extract.py) | DYNAMIC CHORD feat.[rēve parfait] Append Disc（honeybee black / ASGARD）（PC） | [PC-JP] DYNAMIC CHORD feat.[rēve parfait] Append Disc（honeybee black / ASGARD） | [stcm2l](../references/engines/stcm2l.md) · [system-nnn](../references/engines/system-nnn.md) · [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) |
| [revice_extract.py](revice_extract.py) | RE:VICE[D]（PSV） · REVICE[D]（PSV） | RE:VICE[D]  (PSV, PCSG00382, Otomate / Idea Factory)  剧本文本提取 | — |
| [rinrin_extract.py](rinrin_extract.py) | 凜々蝶さまのおっしゃる通り！（PC） | [PC-JP]凜々蝶さまのおっしゃる通り！（KiriKiri / data.xp3 / cp932 平文 KAG3）文本提取。 | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [rio_ll_extract.py](rio_ll_extract.py) | Laughter Land | Laughter Land (WillPlus / RIO bytecode) text extractor. | — |
| [rip9_extract.py](rip9_extract.py) | 9 R.I.P.（Switch） | [NS-JP]9 R.I.P. —— STCM2L(UTF-8) 文本提取。 | [stcm2l](../references/engines/stcm2l.md) |
| [rip9seq_extract.py](rip9seq_extract.py) | 9 R.I.P. sequel（Switch） | [NS-JP]9 R.I.P. sequel —— STCM2L(UTF-8) 文本提取。 | [stcm2l](../references/engines/stcm2l.md) |
| [ripple_extract.py](ripple_extract.py) | リプルのたまご ～Apprentice magician～（PS2） | リプルのたまご ～Apprentice magician～ (PS2, HuneX .ebf) 全文本提取。 | — |
| [rixcall_extract.py](rixcall_extract.py) | The Wind from Rixcall | 最终文本提取 | — |
| [roman_extract.py](roman_extract.py) | 召しませ浪漫茶房（PS2） | 召しませ浪漫茶房（SIMPLE2000 Vol.98 THE 浪漫茶房 / PS2-JP / SLPM_657.37）全文本提取 | — |
| [romeo_extract.py](romeo_extract.py) | ロミオＶＳジュリエット（PSV） | QuinRose Qoo (PSV) —— ロミオVSジュリエット 剧本成行。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [rootrexx_extract.py](rootrexx_extract.py) | ROOT∞REXX（PSV） | ROOT∞REXX (PSV / PCSG00458 / Otomate×Idea Factory / 2015) 全文本提取 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [rosarium_extract.py](rosarium_extract.py) | Rosarium～繋がれた少年～ | 最终文本提取 | [reallive](../references/engines/reallive.md) |
| [rpg999v19_extract.py](rpg999v19_extract.py) | 999,Victory ver1.9（RPGツクールVX Ace / RGSS3）（PC） | 999,Victory ver1.9（RPGツクールVX Ace / RGSS3）文本提取 | — |
| [rpg999v_extract.py](rpg999v_extract.py) | 999,Victory -Return- ver1.6（PC） | RPG Maker VX Ace (RGSS3) 文本提取 | — |
| [rq_extract.py](rq_extract.py) | Re;quartz · Re;quartz零度（Switch） | Re;quartz零度 (NS) SCRIPT.PAK → 全文本（双版对照） | — |
| [rt2_extract.py](rt2_extract.py) | ラディアンテイル ～ファンファーレ！～（Switch） | ラディアンテイル ～ファンファーレ！～ (NS) STCM2L 文本提取  —— 2026-10-26 修正版 | — |
| [run_alice.py](run_alice.py) | 6本の「国のアリス」シリーズ一括抽出 (主角名 アリス＝リデル) | Batch extract scenario text from the 6 Alice-series PSP ISOs. | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [rushup_extract.py](rushup_extract.py) | RUSH×UP！ | 最终文本提取 | — |
| [ry_extract.py](ry_extract.py) | ロイヤルズ～愛しの王子さま～ ＆ ～誘惑の王子さま～ (Tiaramode, BGI/Ethornell v1) | ロイヤルズ～愛しの王子さま～ ＆ ～誘惑の王子さま～  (Tiaramode, BGI/Ethornell v1) | — |
| [sa7_extract.py](sa7_extract.py) | SA7 - Silent Ability Seven（PSV） | SA7 - Silent Ability Seven - (PSV / PCSG00640 / プチレーヴ) 全文本提取器 | — |
| [saint_extract.py](saint_extract.py) | セイント ビースト ~螺旋の章~（PS2） | ［PS2-JP］セイント ビースト ~螺旋の章~ —— SN.BIN 剧本提取 | — |
| [saisys_ssb_text.py](saisys_ssb_text.py) | Dual Colors（PC） · Love Mission · Love Mission 特別編 | [JP]Dual Colors (PC / SaiSys / chiffon 2001) 正文提取 | — |
| [sanzen_extract.py](sanzen_extract.py) | 参千世界遊戯（PSV） · 参千世界遊戯 ～Re Multi Universe Myself～（PSV） | 参千世界遊戯 ～Re Multi Universe Myself～ (PSV, PCSG01194, girls★dynamics / ACTGS「ROM2/SNR」) | — |
| [sc2003_extract.py](sc2003_extract.py) | SILVER CHAOS（PC） | [JP]SILVER CHAOS（PC / VividColor GameSystem 2003）全文本抽取 | [vividcolor](../references/engines/vividcolor.md) |
| [sc7_extract.py](sc7_extract.py) | 7'scarlet for Nintendo Switch（Switch） · 7'scarlet for Nintendo Switch（21,904 行（Switch） | [NS-JP]7'scarlet for Nintendo Switch 全文本提取（Otomate SScn 字节码） | [otomate-sscn](../references/engines/otomate-sscn.md) |
| [scandal_extract.py](scandal_extract.py) | 偽りの君とスキャンダル（Switch） | 偽りの君とスキャンダル（Switch / Nintendo Bezel Engine）剧本文本提取。 | [bezel-bea](../references/engines/bezel-bea.md) |
| [scfb_extract.py](scfb_extract.py) | Silver Chaos Fan Box -Eternal Fantasia- | [JP]Silver Chaos Fan Box -Eternal Fantasia- 文本抽取 | [vividcolor](../references/engines/vividcolor.md) |
| [schoolwars_extract.py](schoolwars_extract.py) | スクールウォーズ ～全巻パック 本編＆卒業戦線～（PSV） | スクール・ウォーズ ～全巻パック 本編＆卒業戦線～ (PSV, QuinRose / Courier "KS" engine) | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [sco_vm_text.py](sco_vm_text.py) | Dolly Night | Dolly Night / ドーリィナイト（パペット 2004）—— main.sco 文本提取。 | — |
| [scratch_extract.py](scratch_extract.py) | SCRATCH | SCRATCH (undo/大樹愁 2006, KiriKiri2 KAG3) 剧本文本提取 —— 双版对照（段行＋合并行）。 | — |
| [seisyun_extract.py](seisyun_extract.py) | 青春はじめました！ | 《青春はじめました！》脚本 .bin → 一行一次点击的文本。 | — |
| [seiyuu_extract.py](seiyuu_extract.py) | Seiyuu Danshi! | [JP]Seiyuu Danshi! 文本抽取驱动（Ren'Py 7.2.2） | — |
| [senjyushi_extract_text.py](senjyushi_extract_text.py) | 千銃士:Rhodoknight for Nintendo Switch（Switch） · 千銃士Rhodoknight（Switch） · 千銃士Rhodoknight for Nintendo Switch（Switch） | 千銃士Rhodoknight (NS) —— SceneMasterVO.bin 全文本提取 | — |
| [sgk_extract.py](sgk_extract.py) | 三国恋戦記～思いでがえし～＋学園恋戦記（Switch） | 三国恋戦記～思いでがえし～＋学園恋戦記 (NS-JP) —— SCRIPT.PAK 全文本提取 | [selfpak-utf16-vm](../references/engines/selfpak-utf16-vm.md) |
| [sgs_heiho_extract.py](sgs_heiho_extract.py) | 三国恋戦記～オトメの兵法！～（Switch） | 三国恋戦記～オトメの兵法！～ (NS-JP) —— SCRIPT.PAK 全文本提取 | [selfpak-utf16-vm](../references/engines/selfpak-utf16-vm.md) |
| [sgs_kai_extract.py](sgs_kai_extract.py) | 三国恋戦記 魁（PC） | 三国恋戦記 魁 —— 全文本提取（对话/选项/结局/教程） | [daisy2-ddp](../references/engines/daisy2-ddp.md) |
| [shini_extract.py](shini_extract.py) | 死神と少女（Switch） | [NS-JP]死神と少女 (The Reaper And The Girl) text extract. | — |
| [shinjuku_text.py](shinjuku_text.py) | 新宿羅生門（Switch） · 新宿羅生門 ―Rashomon of Shinjuku―（Switch） | 新宿羅生門 ―Rashomon of Shinjuku― (Switch / Idea Factory・ALTERGEAR, 開発:花梨エンターテイメント) | — |
| [shinobi_ns_build.py](shinobi_ns_build.py) | 忍び、恋うつつ for Nintendo Switch（Switch） | 忍び、恋うつつ for Nintendo Switch —— 成品构建。 | — |
| [shinoda_botan_extract.py](shinoda_botan_extract.py) | 篠田新宿探偵事務所 唐獅子牡丹（PC） | 篠田新宿探偵事務所 唐獅子牡丹  (HolicWorks Disc Blue / 2018-10-26 / PC-JP) | — |
| [sidez_pc_extract.py](sidez_pc_extract.py) | Blackish House ←sideZ（ASGARD AdvHD / .ws2 字节码）（PC） | [PC-JP] Blackish House ←sideZ（ASGARD AdvHD / .ws2 字节码）全文本提取。 | — |
| [siesta_avg32.py](siesta_avg32.py) | Siesta ～すすき野原の夢物語～ | Siesta ～すすき野原の夢物語～ 文本提取（AVG32 / AMEDEO） | [avg32](../references/engines/avg32.md) |
| [siglus_scene_extract.py](siglus_scene_extract.py) | 罪ナル螺旋ノ檻 | SiglusEngine (罪ナル螺旋ノ檻 / Tsuminaru) Scene.pck text extractor. | — |
| [silentmoon_extract.py](silentmoon_extract.py) | Silent Moon (Boys3) | Silent Moon (Boys3) 正文提取：ACT_A..H.txt + 同名 .spt 记录。 | — |
| [sk_extract.py](sk_extract.py) | Code（Switch） | [NS-JP] Code：Realize ～白銀の奇跡～ for Nintendo Switch —— Utage（宴）剧本提取 | [unity](../references/engines/unity.md) |
| [skipbeat_extract.py](skipbeat_extract.py) | スキップ・ビート！（PS2） | スキップ・ビート！(PS2, SLPM_551.70) シナリオ抽出。 | — |
| [slg_system_sd.py](slg_system_sd.py) | Heartner Hearts! | SLG System 系（Unicorn-B 2005「Heartner Hearts!」）文本提取器。 | — |
| [snowboundland_extract.py](snowboundland_extract.py) | SNOW BOUND LAND（PSP） · SNOW_BOUND_LAND（PSP） | SNOW BOUND LAND (PSP, Otomate / Idea Factory 2013) 剧本文本提取  —— 自包含 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [solomon_extract.py](solomon_extract.py) | Solomon's Ring ～地の章～（PSP） · Solomon's Ring ～水の章～（Plan Peace / InterOne，2012-12-20 系列，vndb v11502）（PSP） · Solomon's Ring ～緋の章～（Hi no Shou / 緋の章）（Plan Peace / InterOne Inc.，2012-12-20 系列，vndb v11502，release r23769）（PSP） · Solomon's Ring ～風の章～（Kaze no Shou / 風の章 / エレメント＝風）（PSP） · 自动化（PSP） | [PSP-JP] Solomon's Ring ～地の章～  (Plan Peace / InterOne, ULJM06200系) | [planpeace-pct](../references/engines/planpeace-pct.md) |
| [sorayume_extract.py](sorayume_extract.py) | ソラユメ（Switch） | ソラ*ユメ (NS-JP, TAKUYO, TitleID 0100e6a027760000) text extract. | — |
| [souten_extract.py](souten_extract.py) | 蒼天の彼方（PC） | Extract 蒼天の彼方 (PC, System-NNN) from an installed game directory. | — |
| [souten_ungai_extract.py](souten_ungai_extract.py) | 蒼天の彼方～雲外蒼天～（PC） | Extract the standalone Japanese 雲外蒼天 short story using System-NNN. | — |
| [spelldown_extract.py](spelldown_extract.py) | Spell Down | 最终文本提取 | — |
| [springflower_extract.py](springflower_extract.py) | Spring Flower | [JP]Spring Flower (FUSYRO / KiriKiri2 KAG3) -> one line per on-screen message box. | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [srxfd_extract.py](srxfd_extract.py) | スカーレッドライダーゼクス STARDUST LOVERS（PSP） | スカーレッドライダーゼクス STARDUST LOVERS (PSP) | [pack-yox](../references/engines/pack-yox.md) |
| [srxrev_extract.py](srxrev_extract.py) | Scared Rider Xechs Rev（PSV） | LukPlus ADV (SRX Rev / PSV) lua script -> text extraction. | — |
| [ss_psv_extract.py](ss_psv_extract.py) | Starry☆Sky ~Autumn Stories~（PSV） · Starry☆Sky ～Winter Stories～（PSV） | Starry☆Sky PSV（Summer/Autumn/Winter Stories, PCSG00916/917/918）剧本文本提取。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [ssl_extract.py](ssl_extract.py) | 薄桜鬼SSL ～sweet school life～ for Nintendo Switch（Switch） | [NS-JP]薄桜鬼SSL ～sweet school life～ 文本提取（STCM2L / Switch / UTF-8）。 | — |
| [sspm_extract.py](sspm_extract.py) | Starry☆Sky ~Spring Memories~（Switch） · Starry☆Sky_SpringMemories（Switch） | Starry☆Sky ~Spring Memories~ (NS-JP, 0100a3d026610000) 全文本提取。 | — |
| [sss_extract.py](sss_extract.py) | Seven Sex Slaves | 七人の性奴隷 / Seven Sex Slaves（KiriKiri2 + KAG3）剧本 -> 全文本（双版） | — |
| [stampout_extract.py](stampout_extract.py) | STAMP OUT | [JP]STAMP OUT（Monoceros 自研引擎，与 Spell Down 同族：STMD/STSL/GLNK） | — |
| [stc_extract.py](stc_extract.py) | スタットコール 救命恋愛24時（Romance MD Always On Call）（Switch） | [NS-JP]スタットコール 救命恋愛24時（Romance MD Always On Call）文本提取 | [naninovel](../references/engines/naninovel.md) |
| [stcm2l_extract.py](stcm2l_extract.py) | 薄桜鬼 遊戯録 隊士達の大宴会（Switch） | STCM2L 剧本文本提取器 —— 猛獣たちとお姫様 for Nintendo Switch | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) |
| [steam2_extract.py](steam2_extract.py) | スチームプリズン -Beyond the Steam-（Switch） | スチームプリズン -Beyond the Steam- (NS) → 全文本 | — |
| [steam_extract.py](steam_extract.py) | スチームプリズン | スチームプリズン (NS, HuneX Ogre) allscr.mrg + script_text.mrg → 全文本 | — |
| [steam_rebuild.py](steam_rebuild.py) | スチームプリズン（Switch） | スチームプリズン 按「文本表逐条 = 一次点击」重建（2026-10-26）。 | — |
| [steelwood_extract.py](steelwood_extract.py) | 原宿探偵学園 スチールウッド（PSP） | Steel Wood (原宿探偵学園 スチールウッド) DATA/BIN/M*.DAT 剧本提取。 | — |
| [step_extract.py](step_extract.py) | STEP -二人の関係は一歩ずつ- | STEP: rlvm-derived parser/decompressor; current-game GAMEEXE evidence. | [reallive](../references/engines/reallive.md) |
| [stormlover2_run.py](stormlover2_run.py) | STORM LOVER 2nd V（PSV） · ★（PSV） | STORM LOVER 2nd V (PSV PCSG00736) —— 从 sc.cpk 产出全文本。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [stormlover_natsu_run.py](stormlover_natsu_run.py) | STORM LOVER 夏恋!!（PSP） | STORM LOVER 夏恋!!（PSP）—— 从 sc.cpk 产出全文本（2026-10-12）。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [stormlover_run.py](stormlover_run.py) | STORM LOVER V（PSV） · ★ STORM LOVER V | STORM LOVER V (PSV PCSG00735) —— 从 sc.cpk 产出全文本（2026-10-11）。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [straw_extract.py](straw_extract.py) | 殺し屋とストロベリー Plus | 殺し屋とストロベリー Plus —— scenario01(UnityFS) 内 TextAsset → 全文本。 | — |
| [strawberry_extract.py](strawberry_extract.py) | きまぐれストロベリーカフェ（PS2） | PS2『きまぐれストロベリーカフェ』EVT 字节码文本提取（v3） | — |
| [stripper_extract.py](stripper_extract.py) | S-Tripper | 最终文本提取 | — |
| [strobemania_run.py](strobemania_run.py) | スト☆マニ ～Strobe☆Mania～（PSP） | スト☆マニ ～Strobe☆Mania～（PSP / ULJM-05961）—— 全文本提取。 | — |
| [subordinate2ldk_extract.py](subordinate2ldk_extract.py) | 上司と秘密の2LDK（Switch） | 上司と秘密の2LDK（Switch / Bezel Engine「SCNE + scb_」）剧本正文提取。 | [bezel-bea](../references/engines/bezel-bea.md) |
| [sugar_build.py](sugar_build.py) | シュガシュガルーン -恋もおしゃれもピックアップ！（PS2） | PAC 0x0425 文本流 → 一次点击一行。 | — |
| [sumire_extract.py](sumire_extract.py) | すみれの蕾 fan disc～ウェディング大作戦～（PC） | [PC-JP]すみれの蕾（PC / MADOKA GScript・GSCE 编译剧本）全文本提取 v2。 | — |
| [swallows_extract.py](swallows_extract.py) | My9Swallows TOPSTARS LEAGUE | My9Swallows TOPSTARS LEAGUE —— Unity + 纯文本脚本（与 Honey Vibes 同引擎）。 | — |
| [sweet19_extract.py](sweet19_extract.py) | Sweet 19 Pain | [JP]Sweet 19 Pain —— ComicPly (ICM95 / CmdVer=14) 全文本提取 | — |
| [sweetclown_extract.py](sweetclown_extract.py) | SWEET CLOWN ~午前三時のオカシな道化師~（Switch） | [NS-JP]SWEET CLOWN ~午前三時のオカシな道化師~ text extract (Takuyo gss / SCR 3.00). | — |
| [swf_definetext_text.py](swf_definetext_text.py) | bois～機械じかけの街～外伝 呪縛の刻印 | Macromedia Flash / Shockwave（SWF）→ 「一次点击 = 一行」。 | [overflow-adv](../references/engines/overflow-adv.md) |
| [sympathy_extract.py](sympathy_extract.py) | SympathyKiss（Switch） | SympathyKiss (NS) STCM2L 文本提取 | — |
| [taf_extract.py](taf_extract.py) | Truth and False | [JP]Truth and False —— KiriKiri/KAG3 专用提取驱动 | — |
| [taisho_ht_extract.py](taisho_ht_extract.py) | 大正×対称アリス HEADS & TAILS（Switch） | 大正×対称アリス HEADS & TAILS（NS）→ 全文本 | [selfpak-utf16-vm](../references/engines/selfpak-utf16-vm.md) |
| [taisho_pak_extract.py](taisho_pak_extract.py) | 大正×対称アリス all in one（Switch） · 大正×対称アリス HEADS & TAILS（Switch） | 大正×対称アリス all in one（NS）→ 全文本 | [selfpak-utf16-vm](../references/engines/selfpak-utf16-vm.md) |
| [takahiro_extract.py](takahiro_extract.py) | takahiro_com（TyranoScript / NW.js） | takahiro_com（TyranoScript / NW.js）文本提取。 | — |
| [tameboy_extract.py](tameboy_extract.py) | TameBoy（「シナリオくん」1.9x ／ .st1） | [JP]TameBoy（「シナリオくん」1.9x ／ .st1）全文本提取驱动。 | [scenario-kun](../references/engines/scenario-kun.md) |
| [temi_extract.py](temi_extract.py) | テミラーナ国の強運姫と悲運騎士団 | テミラーナ国の強運姫と悲運騎士団 (NS, Unity/UTXT) → 全文本 | — |
| [tempest_extract.py](tempest_extract.py) | Knight of Lelouch | even if TEMPEST 宵闇にかく語りき魔女（Switch / Nintendo Bezel Engine）剧本文本提取。 | — |
| [teni_extract.py](teni_extract.py) | 新テニスの王子様 LET'S GO!! 〜Daily Life〜 from RisingBeat | 新テニスの王子様 LET'S GO!! 〜Daily Life〜 from RisingBeat (NS, HuneX Ogre) → 全文本 | — |
| [tenis2_extract.py](tenis2_extract.py) | テニスの王子様 SWEAT & TEARS 2（PS2） | テニスの王子様 SWEAT & TEARS 2 (PS2) 剧本提取。 | [stcm2l](../references/engines/stcm2l.md) · [system-nnn](../references/engines/system-nnn.md) · [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) |
| [tennis_extract.py](tennis_extract.py) | テニスの王子様 RUSH & DREAM!（PS2） | [PS2-JP] テニスの王子様 RUSH & DREAM! 全文本提取. | — |
| [tether_text.py](tether_text.py) | Tether | [JP]Tether（KiriKiri / TVP(KiriKiri) KAG3）全文本提取。 | — |
| [thc_build.py](thc_build.py) | とらぶるふぉうちゅんCOMPANY★はぴCURE（PS2） | 合成最终交付文本（一次点击 = 一行）。 | — |
| [tiabureido_extract.py](tiabureido_extract.py) | 悠久のティアブレイド for Nintendo Switch（Switch） | 悠久のティアブレイド for Nintendo Switch —— STCM2L 全文本提取（一次点击＝一行）。 | — |
| [timeflies_extract.py](timeflies_extract.py) | Time Flies（PC） | [JP]Time Flies — KiriKiri KAG3 全文本提取（双版对照） | — |
| [tiny_machinegun_extract.py](tiny_machinegun_extract.py) | Tiny×MACHINEGUN · 外部核对（vndb v12478 + 巴哈姆特 cast） | Tiny×MACHINEGUN THE GAME  (Rejet / PC-JP)  剧本・辞典文本提取器  —— 端到端定稿 | — |
| [tlz_liam_text.py](tlz_liam_text.py) | Fragrance Tale（PC） · Fragrance Tale ～フレグランス・テイル～（PC） | Takuyo「LIAM」引擎（Fragrance Tale PC 2001）→ 一台本一台词框的正文。 | — |
| [tmr_srp.py](tmr_srp.py) | TMR-Hiro ADV System .srp（PC） | TMR-Hiro ADV System .srp → 全文本（PC / クレイジー★ラビッツ 実測） | [tmr-hiro](../references/engines/tmr-hiro.md) |
| [toiro_extract2.py](toiro_extract2.py) | といろ小町 〜紅に染まるそのときまで〜（PC） | 最终文本提取 | — |
| [tokihako_extract.py](tokihako_extract.py) | 外部核对（vndb v12478 + 巴哈姆特 cast） · 時函 -Time Capsule-（PC） | 時函 -Time Capsule-  (Ray, 2009 / PC / NScripter)  全文本提取 | — |
| [tokimemo_gs1_extract.py](tokimemo_gs1_extract.py) | ときめきメモリアル Girl's Side 1st Love（Switch） · ときめきメモリアル Girl's Side 1st Love for Nintendo Switch（KONAMI（Switch） · ときめきメモリアル Girl's Side 1st Love for Nintendo Switch（KONAMI / Unit（Switch） | ときめきメモリアル Girl's Side 1st Love (NS-JP, Unity) 全文本提取器。 | — |
| [tokimemo_gs2_extract.py](tokimemo_gs2_extract.py) | ときめきメモリアル Girl's Side 2nd Season（Switch） · ときめきメモリアル Girl's Side 2nd Season for Nintendo Switch（KONAMI（Switch） · ときめきメモリアル Girl's Side 2nd Season for Nintendo Switch（KONAMI / Un（Switch） | ときめきメモリアル Girl's Side 2nd Season (NS-JP, Unity) 全文本提取器。 | — |
| [tokimemo_gs3_extract.py](tokimemo_gs3_extract.py) | ときめきメモリアル Girl's Side 3rd Story（Switch） · ときめきメモリアル Girl's Side 3rd Story for Nintendo Switch（Switch） · ときめきメモリアル Girl's Side 3rd Story for Nintendo Switch（KONAMI / Uni（Switch） | ときめきメモリアル Girl's Side 3rd Story for Nintendo Switch (NS-JP, Unity) 全文本提取器。 | — |
| [tokimemo_gs4_extract.py](tokimemo_gs4_extract.py) | ときめきメモリアル Girl's Side 4th Heart（Switch） · ときめきメモリアル Girl's Side 4th Heart for Nintendo Switch（Switch） | ときめきメモリアル Girl's Side 4th Heart for Nintendo Switch (NS-JP, Unity) 全文本提取器。 | — |
| [tokires_extract.py](tokires_extract.py) | ときめきレストラン☆☆☆ Project TRISTARS（PSV） | ときめきレストラン☆☆☆ Project TRISTARS (PSV / PCSG01171, KONAMI) 全文本提取 v2 | — |
| [tokitama_extract.py](tokitama_extract.py) | ときたま！～時函玉手箱～（PC） · 外部核对（vndb v12478 + 巴哈姆特 cast） | ときたま！～時函玉手箱～  (Ray, 2010 / PC / NScripter)  全文本提取 | — |
| [torimari_extract.py](torimari_extract.py) | 鳥籠のマリアージュ ～初恋の翼～（PSV） | 鳥籠のマリアージュ ～初恋の翼～ (PSV, PCSG90230, Kalmia8 / ACTGS engine) | — |
| [touch_text.py](touch_text.py) | ToucH もう一度この手が触れる世界 | [JP]ToucH もう一度この手が触れる世界（TVP/KiriKiri ＋ KAG3/KAGEX）全文本提取。 | — |
| [towa_build.py](towa_build.py) | 悠久ノ桜（PS2） | 悠久ノ桜（Towa no Sakura / PS2-JP）全文本生成 | [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) |
| [trois_text.py](trois_text.py) | アンジェリーク トロワ（PS2） | アンジェリーク トロワ (PS2, SLPM_620.22, 2000 Koei/Ruby Party) 正文＋选项提取 | [koei-embins-ps2](../references/engines/koei-embins-ps2.md) · [koei-pack-ps2](../references/engines/koei-pack-ps2.md) |
| [tsukikage_extract.py](tsukikage_extract.py) | 月影の鎖 -錯乱パラノイア-（Switch） | 月影の鎖 -錯乱パラノイア- (NS-JP) text extract ---- TAKUYO gss / SCR 2.00. | — |
| [tsundere_extract.py](tsundere_extract.py) | あすか！～僕ら星灯高校野球団～（PC） · ツンデレ★Ｓ乙女（PC） | ツンデレ★Ｓ乙女 (PC / 美蕾「Madoka GScript」) 全文本提取器 —— 本项目定稿 | — |
| [tyb_fd_extract.py](tyb_fd_extract.py) | TOKYOヤマノテBOYS for V FAN DISC（PSV） | TOKYOヤマノテBOYS for V FAN DISC（PSV / PCSG01049）全文本提取。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [um_extract.py](um_extract.py) | うみねこのなく頃に咲 ～猫箱と夢想の交響曲～（Switch） | うみねこのなく頃に咲 (NS) main.snr → 全文本 | — |
| [uma_extract_final.py](uma_extract_final.py) | 冬園サクリフィス（Switch） | 冬園サクリフィス [NS-JP] UTXT 文本提取（代码级切分：仅用 0x00 换行码，无括号启发式） | [unity](../references/engines/unity.md) |
| [unbs_extract.py](unbs_extract.py) | Un（PSV） | Un:BIRTHDAY SONG～愛を唄う死神～another record（PSV PCSG00912）剧本提取（本作专用）。 | — |
| [underblue_extract.py](underblue_extract.py) | アンダーブルー2012 | [JP]アンダーブルー2012 — KiriKiri XP3 ＋ KAG3 全文本提取（双版对照） | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [unending_extract.py](unending_extract.py) | unENDing Bloody Call | Extract only SPT script text from unENDing Bloody Call (PSP-JP). | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [system-nnn](../references/engines/system-nnn.md) · [unity](../references/engines/unity.md) · [vsc-vdp-lsb](../references/engines/vsc-vdp-lsb.md) |
| [unity_scriptdatas_text.py](unity_scriptdatas_text.py) | Friendly lab - unlock();（Tennenouji 2023-08-24 / 原手机版 2013）（PC） | Friendly lab - unlock();（Tennenouji / Unity 2021）→ 一台本一台词框的正文。 | [unity](../references/engines/unity.md) |
| [ururun_build.py](ururun_build.py) | うるるんクエスト 恋遊記（PS2） | うるるんクエスト 恋遊記 全文本生成：VML -> 提取结果/*.txt | — |
| [utage_book_lines.py](utage_book_lines.py) | ワンド オブ フォーチュン Ｒ（Switch） · ワンド オブ フォーチュン Ｒ for Nintendo Switch（Switch） · ワンド オブ フォーチュン Ｒ２ ＦＤ（Switch） · ワンド オブ フォーチュン Ｒ２ ＦＤ ～君に捧げるエピローグ～（Switch） · ワンド オブ フォーチュン Ｒ２ ＦＤ ～君に捧げるエピローグ～ for Nintendo Switch（Switch） · ワンド オブ フォーチュン Ｒ２ ～時空に沈む黙示録～（Switch） | ワンド オブ フォーチュン Ｒ２ ～時空に沈む黙示録～（Switch / Unity + Utage）剧本提取 | [unity](../references/engines/unity.md) |
| [utage_extract.py](utage_extract.py) | ハンサムロンダリング -the mystic lover- | ハンサムロンダリング -the mystic lover- (NS / Unity + Utage) 剧本文本提取。 | [unity](../references/engines/unity.md) |
| [utapri_aa_extract.py](utapri_aa_extract.py) | うたの☆プリンスさまっ♪ Amazing Aria & Sweet Serenade LOVE（Switch） | うたの☆プリンスさまっ♪ Amazing Aria & Sweet Serenade LOVE (NS 0100D4300EBF8000) | — |
| [utapri_as_extract.py](utapri_as_extract.py) | うたの☆プリンスさまっ♪ All Star（Switch） | うたの☆プリンスさまっ♪ All Star (NS 0100B3E0149FC000) 剧本提取。 | — |
| [utapri_debut_extract.py](utapri_debut_extract.py) | うたの☆プリンスさまっ♪ Debut（Switch） | うたの☆プリンスさまっ♪ Debut (NS 010088200EFE8000) 剧本提取（本作专用，勿与他作共用）。 | — |
| [utapri_extract.py](utapri_extract.py) | うたの☆プリンスさまっ♪ All Star After Secret（Switch） | うたの☆プリンスさまっ♪ All Star After Secret (NS/01008030149FE000) 剧本提取。 | — |
| [utapri_rl_extract.py](utapri_rl_extract.py) | うたの☆プリンスさまっ♪ Repeat LOVE（PSV） | うたの☆プリンスさまっ♪ Repeat LOVE（PSV / PCSG00914）全文本提取。 | — |
| [utapri_rl_ns_extract.py](utapri_rl_ns_extract.py) | うたの☆プリンスさまっ♪ Repeat LOVE for Nintendo Switch（Switch） | うたの☆プリンスさまっ♪ Repeat LOVE (NS 010024200E00A000) 剧本提取。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [utsusemi_extract.py](utsusemi_extract.py) | 空蝉の廻（Switch） | 空蝉の廻 (NS-JP) 文本提取 | — |
| [valpurga_extract.py](valpurga_extract.py) | ヴァルプルガの詩（PSV） | [PSV-JP]ヴァルプルガの詩 (PCSG00768) 全文本提取 | — |
| [vamwolf_run.py](vamwolf_run.py) | Vamwolf Cross†（PSV） | Vamwolf Cross† (PSV PCSG00467, D3P 系) —— sc.cpk → 全文本。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [vc_extract.py](vc_extract.py) | DIABOLIK LOVERS VANDEAD CARNIVAL（PSV） | DIABOLIK LOVERS VANDEAD CARNIVAL (PSV, PCSG00472) 文本提取 | — |
| [verite_extract.py](verite_extract.py) | 薔薇に隠されしヴェリテ（PSV） | 《薔薇に隠されしヴェリテ》 (PS Vita / PCSG00708 / Unity 5.3.5p5) 全文本提取 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [virche_extract.py](virche_extract.py) | 終遠のヴィルシュ -EpiClycoris-（Switch） · 終遠のヴィルシュ -ErroRsalvation-（Switch） | 終遠のヴィルシュ -ErroRsalvation- (NS) STCM2L 文本提取。 | — |
| [vista_extract.py](vista_extract.py) | ViSTA+1.20 | [JP]ViSTA+1.20 全文本提取  (KiriKiri / KAG3, 明文 cp932, 无 OTag 加扰) | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [visukio_extract.py](visukio_extract.py) | VISUKIO（Yuuki! Novel 旧版 PackageFile2 ／ .yne） | [JP]VISUKIO（Yuuki! Novel 旧版 PackageFile2 ／ .yne）文本提取驱动。 | — |
| [vitaminb6_extract.py](vitaminb6_extract.py) | VitaminX DetectiveB6（PSP） | VitaminX DetectiveB6 (PSP, HuneX「IKA SEQ SYSTEM v4.1 HuneX 2010」) 全文本提取。 | — |
| [vitaminr_extract.py](vitaminr_extract.py) | ビタミンR（PSP） | VitaminR (PSP, ULJS00592, 2013-08-08, D3P/Rejet) 全文本提取。 | [pack-yox](../references/engines/pack-yox.md) |
| [vitaminx_ep_extract.py](vitaminx_ep_extract.py) | ビタミンX（PSP） · ビタミンX Evolution Plus（PSP） | ビタミンX Evolution Plus（PSP, ULJS00325, HuneX「IKA SEQ SYSTEM v4.1」）全文本提取。 | [hunex-ika](../references/engines/hunex-ika.md) |
| [vitaminxz_extract.py](vitaminxz_extract.py) | Vitamin X to Z（PSP） | Vitamin X to Z (PSP, ULJS00347, HuneX「IKA SEQ SYSTEM v4.1」) 全文本提取。 | — |
| [vitz_extract.py](vitz_extract.py) | VitaminZ（PSP） | VitaminZ (PSP, ULJS00240, HuneX「IKA SEQ SYSTEM v3.4 HuneX 2009」) 全文本提取。 | — |
| [vn_zerodiv_extract.py](vn_zerodiv_extract.py) | 裏語 薄桜鬼 / ～暁の調べ～（PSP） | 裏語 薄桜鬼 / ～暁の調べ～ (PSP ULJM06281 / ULJM06373) 剧本提取器 —— 定稿版 | — |
| [voice_bq_text.py](voice_bq_text.py) | Voice -Be Quite in the Dark- | [JP]Voice -Be Quite in the Dark-（TVP/KiriKiri 2.24 ＋ KAG3）全文本提取。 | — |
| [voice_extract.py](voice_extract.py) | Voice | [JP]Voice（TVP/KiriKiri 2.24 ＋ KAG3 ／ data.xp3）全文本提取。 | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [voice_guy_extract.py](voice_guy_extract.py) | Voice(Guy×Luke) ガイルク | 最终文本提取 | — |
| [vxdst_extract.py](vxdst_extract.py) | VitaminX Destination（PSV） | VitaminX Destination (PSV-JP, PCSG01115) —— HuneX 'HESL / HESE' 剧本文本提取器 | [hunex-hesl](../references/engines/hunex-hesl.md) |
| [vzgrad_extract.py](vzgrad_extract.py) | VitaminZ Graduation（PSP） | VitaminZ Graduation (PSP, ULJS00xxx v1.01, HuneX「IKA SEQ SYSTEM v4.2」) 全文本提取。 | — |
| [will_rio_arc.py](will_rio_arc.py) | Vampire Sweetie（PC） | WillPlus / RIO.ARC（WSC 脚本）文本提取。 | — |
| [willowisp_extract.py](willowisp_extract.py) | ウィル・オ・ウィスプ ポータブル（PSP） | ウィル・オ・ウィスプ ポータブル (PSP, ULJM05447, Design Factory & Otomate / Idea Factory) 剧本文本提取 | — |
| [wings_extract.py](wings_extract.py) | Wings Innocent | 最终文本提取 | — |
| [yamanote_extract.py](yamanote_extract.py) | TOKYOヤマノテBOYS for V MAIN DISC（PSV） | TOKYOヤマノテBOYS for V MAIN DISC（PSV / PCSG01048）全文本提取。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [yamiiro_extract.py](yamiiro_extract.py) | 闇色の魔珠 | 闇色の魔珠 (Daisy2 / PROTOTYPE NS) SCRIPT.PAK → 全文本（双版对照） | — |
| [yourmo_extract.py](yourmo_extract.py) | ユア・メモリーズオフ · ユア・メモリーズオフ～Girl's Style～（PSP） | ユア・メモリーズオフ～Girl's Style～ (PSP-JP, ULJM05435, MAGES. 2008) | — |
| [yuris_allout_extract.py](yuris_allout_extract.py) | ALL OUT（PC） | YU-RIS / ERIS 剧本正文提取：[JP]ALL OUT | — |
| [zettaikyuu_extract.py](zettaikyuu_extract.py) | 絶対階級学園 ~Eden with roses and phantasm~（Switch） | 絶対階級学園 ~Eden with roses and phantasm~ (NS) → 提取结果 txt | — |
| [zokuwanai_extract.py](zokuwanai_extract.py) | 罪喰い（PSV） · 罪喰い ~千の呪い、千の祈り~ for V（PSV） | 罪喰い ~千の呪い、千の祈り~ for V (PSV / PCSG01019 / HuneX, dramatic create 2017) 全文本提取器 | — |
