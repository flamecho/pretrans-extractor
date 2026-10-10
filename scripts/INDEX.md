# scripts/ 索引 —— 哪个引擎用哪个脚本

所有脚本默认从**环境变量**取路径（`VNTRANS_HOME` / `VN_OUTDIR` / `SEVENZ` / `PROD_KEYS` /
`ZRIF` / `PSVDEC`），见 `SKILL.md` §5。多数脚本用法：`python <script>.py <输入> <输出目录>`，
具体 argv 见各文件头部 docstring。

> `*_extract.py` 多为**针对某一款具体游戏**定稿的提取器，但其中的**容器解析 + 操作码语义 +
> 字符层处理**可直接移植到同引擎的其它作品。移植时优先复用「容器读取」与「消息指令定位」两段。

## 一、交付工具（先跑这几个）

| 脚本 | 作用 |
|---|---|
| `identify.py` | **S0 识别**：`python identify.py <文件或目录> [--deep]` —— 一次调用给出「引擎 ＋ 建议命令 ＋ 该读哪份 `references/engines/*.md`」 |
| `check_text.py` | **交付前自检**：BOM/LF/`U+FFFD`/`〓`/控制符、半角假名、PUA、引号配对、说话人残留、主角名出现性、空行/超长行/重复行。`--name` 指定主角名，退出码 0 = 通过 |
| `probe.py` | **限量探查**（≤80 行）：逐条打印 `RAW` 十六进制 ＋ `DEC` 解码，替代 `xxd` 整文件 dump |
| `memcheck.py` | **体积体检**：`.md > 10 KB` 亮 `[W]`、主索引 > 8 KB 亮 `[E]` —— 提醒当场拆文件 |

## 二、通用容器 / 封包

| 脚本 | 引擎 / 格式 | 说明 |
|---|---|---|
| `cpk.py` / `cpk_v1.py` | CRI CPK | 表长 `>>8` / `&0xFF` 两种变体；判据 `@UTF` |
| `psarc_extract.py` | PSARC (zlib) | PSV/PS3/PS4 通用 |
| `cdar.py` / `cdar_extract.py` | Koei CDAR v2/v4 | 文本记录 `04 <u16> <cp932> 00`；框边界 BOUND/M91/C7 |
| `nsac.py` | NIS NSAC v2 | 逢魔が刻 等 |
| `qpk.py` | QPK | ハートのアリス 等 |
| `xp3.py` | KiriKiri XP3 | 索引枚举 + 文件抽取 |
| `npa_nrbf.py` + `npa_schemes.json` | Nitroplus NPA | 归档读取；25 套预置方案 |
| `rom2_extract.py` | ROM2 / SNR（Kalmia8·ACTGS） | `ROM2` 容器 + `main.snr` 剧本 |
| `libp_malievita.py` | Malie LIBP (MalieVita) | Vita 版 LIBP 读取 |
| `ps2_extract.py` / `ps2_game.py` / `ps2_scene.py` / `ps2_vm.py` | PS2 剧本 VM | PS2 平台脚本解析 |
| `lztest.py` | 压缩算法 | LZ 系算法试验/验证 |

## 三、解密 / 化け修复

| 脚本 | 引擎 / 格式 | 说明 |
|---|---|---|
| `chou_decrypt.py` | KiriKiri XP3（区间 1 字节 XOR） | 解密 + 键推定（字符似然模型） |
| `chou_fix.py` | KiriKiri XP3 | **定值复元表**：`REKEY` / `OVERRIDES` / `TEXT_PATCH` + `apply_fix()` |
| `chou_extract.py` | KiriKiri KAG3 | XP3 内 KAG3 脚本 → 显示文本 |
| `gensou_decode.py` / `gensou_extract.py` / `gensou_scan.py` | KiriKiri XP3（幻想夜話） | 定值复元表解密 / 提取 / 残存化け统计 |
| `advhd.py` | WillPlus / AdvHD `.wsc` | 全字节 `rotl_8(c,6)` 解密 + 文本指令（`op41/42/02`） |
| `malie_extract.py` | Malie System（Camellia LIBP / AlphaROM） | PC/Vita 两路；OmegaVampire / 断罪のマリア 实证 |

## 四、各引擎 / 作品提取器

| 脚本 | 引擎 | 作品示例 |
|---|---|---|
| `artemis_pfs_extract.py` | Artemis `pf8` | 滄海天記 |
| `brothers_kiss_extract.py` | BGI / Ethornell | ブラザーズ |
| `asakiyumemishi_extract.py` | System-NNN `.spt` | あさき、ゆめみし～ひととせ～ |
| `crimson_royale_extract.py` | KiriKiri XP3 + DropWave | クリムゾン・ロワイヤル |
| `crankin_extract.py` | 自研「テキスト方式 ADV」 | クランク・イン |
| `siglus_scene_extract.py` | SiglusEngine | 罪ナル螺旋ノ檻 |
| `sgs_kai_extract.py` + `sgs_kai_ddp.py` | Daisy2 DDP3 | 三国恋戦記 魁 |
| `stcm2l_extract.py` | STCM2L（Idea Factory） | 猛獣たちとお姫様 |
| `norn9_extract.py` | STCM2L (PSV) | Norn9 Act Tune |
| `pandora_extract.py` / `pandora_dbg.py` | STCM2L (PS2) | PANDORA ～君の名前を、僕は知る～ |
| `tiny_machinegun_extract.py` | LTEngine | Tiny×MACHINEGUN |
| `tokihako_extract.py` / `tokitama_extract.py` | NScripter | 時函 / ときたま！ |
| `koigig_extract.py` | MNP `ARC!`/MMA | KoiGIG |
| `kaleido_extract.py` | HuneX Ogre / MZX0 | カレイドイヴ |
| `believer_extract.py` | HuneX HESL/HESE | BELIEVER! |
| `heiligenstadt_extract.py` | Unity PSARC | ハイリゲンシュタットの歌 |
| `verite_extract.py` | Unity TKG ADV | 薔薇に隠されしヴェリテ |
| `akuyaku_extract.py` | Unity `CSR1.00` | 悪役令嬢は隣国の王太子に溺愛される |
| `paradigm_paradox_extract.py` | Regista advGame | Paradigm Paradox |
| `fortissimo_extract.py` | Otomate VM | フォルティッシモ |
| `geten_extract.py` | Koei CDAR v4 | 下天の華 |
| `ouma_extract.py` / `ouma_story.py` / `ouma_build_text.py` | NIS-NML | 逢魔が刻 |
| `stride_extract.py` | CRIWARE + 自研数值 VM | プリンス・オブ・ストライド |
| `tsundere_extract.py` | Madoka GScript `CRPT` | ツンデレ★Ｓ乙女 |
| `lamento_extract.py` | Nitroplus NPA + NSS | Lamento -BEYOND THE VOID- |
| `hanayoi_afs.py` / `hanayoi_extract.py` / `hanayoi_run.py` | CRI AFS + 自研索引码 | 花宵ロマネスク（PS2） |
| `torimari_extract.py` | ROM2 / SNR | 鳥籠のマリアージュ ～初恋の翼～ |
| `mysteria_extract.py` / `mysteria_text.py` | Malie System (MalieVita) | 英国探偵ミステリア The Crown |
| `blip_extract.py` / `bgloss_extract.py` / `brouge_extract.py` | WillPlus / AdvHD | Butterfly Lip / Gloss / Rouge |
| `kazahanaki_extract.py` | Koei / Ruby Party | 遥か5 風花記（PSP） |
| `shinoda_botan_extract.py` | （PC-JP） | 篠田新宿探偵事務所 唐獅子牡丹 |
| `gensou_extract.py` | KiriKiri KAG3 | 蝶の毒 華の鎖 ～幻想夜話～ |
| `vn_memdump.py` | 运行时内存转储 | 加壳引擎（AlphaROM 等）取明文 |
| `vn_zerodiv_extract.py` / `possession_extract.py` / `rear_extract.py` | 其它 PSV 系 | ZeroDiv / Possession Magenta / リアフェレス |
| `extract_alice.py` / `extract_text.py` / `run_alice.py` | QPK/CPK | ハートのアリス |
| `corda_*_extract.py` | Koei CDAR | 金色のコルダ 系列（1 / 2ff / 2fenc / 3FS / 3AS / オクターヴ / PSP） |
| `haruka_extract.py` / `haruka4_extract.py` / `haruka5_extract.py` / `haruka6_extract.py` / `haruka2_eem_extract.py` | Koei CDAR / EEM | 遥か 系列 |
| `corda_2fa_get.py` / `corda_2fa_scan.py` / `corda_2fa_unpack.py` / `corda_psp_unpack.py` / `corda_boxcheck.py` | Koei CDAR 辅助 | 取包 / 扫描 / 解包 / 框校验 |
| `corda_2ff_g1t.py` | G1T 字形 | 从 G1T 图集渲染字形（核对替换槽） |
| `haruka2_appmatrix.py` / `haruka2_eemlib.py` / `haruka6_dict.py` / `haruka6_dedup.py` | 遥か 辅助 | 变量表 / 词典 / 去重 |

## 五、Takuyo gss（LSDARC + SCR 2.00）

| 脚本 | 作用 |
|---|---|
| `himehibi_lsdarc.py` | `LSDARC V.100` 容器读取 |
| `himehibi_disasm.py` | `SCR 2.00` 反汇编（`u16 op + u8 size` 自定界） |
| `himehibi_crawl.py` | 调用图爬取（含 `0x10c` 动态脚本展开） |
| `himehibi_scan.py` | 脚本扫描 |
| `himehibi_extract.py` / `himehibi2_extract.py` | ひめひび 1 学期 / 続！二学期 提取 |
| `himehibi2_eboot.py` | eboot 解析（默认主角名 / 人名槽定位） |

## 六、探查 / 字符 / 字体助手

| 脚本 | 作用 |
|---|---|
| `scanjp.py` / `scan_jp.py` / `sjis_scan.py` | 统计字节流中的日文覆盖率（定位文本层） |
| `scan_nested.py` | 嵌套容器逐层扫描 |
| `fullscan.py` | 全盘 / 全镜像扫描日文 |
| `unity_scan.py` / `unity_scan2.py` | Unity 资源（TextAsset / AssetBundle）探查 |
| `gensou_scan.py` | 残存化け统计检测 |
| `renderfont.py` | 从字形图集渲染指定码位（**核对字体替换槽**） |
| `marc_font.py` | MARC 字体库解析 |
| `pe_dis.py` | PE 反汇编（eboot / 加壳分析） |
| `period55.py` | 5pb 周期脚本 |

## 七、参考实现（非 Python）

| 文件 | 说明 |
|---|---|
| `koei/*.cs` | Kuriimu2 的 Koei CDAR 插件源码（C#），可读容器/文本解析逻辑 |
| `hunex/hunex_decomp_mzx0.py` | HuneX `MZX0` 解压（字面 XOR 0xFF） |
| `hunex/mrg_extract_tool.py` / `hunex/mzp_extract_tool.py` | HuneX `mrgd00` 容器解包 |
| `hunex/Constants.py` | HuneX 脚本指令常量 |
| `hunex/comp_script.md` | HuneX 脚本编译/解包笔记 |
