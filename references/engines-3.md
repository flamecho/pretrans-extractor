# 项目 _trans —— 引擎路由 ③（**续册**：近两日新增的同族变体册）

> **只放路由行，细节在各册内。**
> 同族主册：`engines/hunex-ogre.md`（HuneX Ogre）· `idea-factory-stcm2l-psp-uni2.md`（UNI2）
> · `idea-factory-stcm2l-switch.md`（Switch）· `takuyo-gss-psp.md`（Takuyo gss PSP）。

| 引擎 | 代表作 | 一句话要点 | 详见 |
|---|---|---|---|
| **HuneX「Ogre」系 · PSP 变体（字形码制）** | 乙女的恋革命★ラブレボ!! Portable（PSP） | 本作文本＝**2 字节字形码**，与 CP932 直写的 カレイドイヴ／マジきゅん **不同族**，不能套用同家族解 | `engines/hunex-ogre-loverevo.md` |
| **STCM2 · CRI「UNI2」· 第 5 样本** | ウィル・オ・ウィスプ ポータブル（PSP） | UNI2 容器第 5 例；与前 4 例的差异见册内对照表 | `engines/idea-factory-stcm2l-psp-uni2-willow.md` |
| **STCM2L · Switch 第 3 例** | Glass Heart Princess for Nintendo Switch（本体＋FD） | Switch 侧 STCM2L 第 3 例（同册另有猛獣／BWS／ニルアド）；本体与 FD 分装 | `engines/idea-factory-stcm2l-switch-ghp.md` |
| **Takuyo gss · PSP 第 2 作** | Little Aid ポータブル（PSP，2007-03-12） | `SCR 1.10` 与 `2.00` **只差版本串**（逐字节 diff 验证），指令编码同构 | `engines/takuyo-gss-psp-littleaid.md` |
| **Takuyo gss · PSP 第 3 作** | 星色のおくりもの（PSP `ULJS00164`，2008-10-08） | 同族第 3 样本；与 étude／Little Aid 的差异见册内 | `engines/takuyo-gss-psp-hoshiiro.md` |
| **Takuyo gss · PSP 第 4 作** | for Symphony ～with all one's heart～ ポータブル（PSP `ULJM05258`） | 同族第 4 样本；v1.01 补丁版 | `engines/takuyo-gss-psp-symphony.md` |

| **HuneX「ALS」系（`SCENE00.AFS` ＋ `.ALS`）** | ルシアンビーズ イビル ヴァイオレット（PSP v9918）／ジャスティス イエロー（PSP v9917，第 2 作） | **与 IKA SEQ 不同族**（EBOOT 无 `IKA SEQ`，有 `SCENE%02d.ALS`）；AFS[7]=`SCENE00.AFS`（VIOLET 127 员/剧本 16–74；YELLOW 113 员/剧本 16–62）；`.ALS`＝头 0x20＋16 位 opcode 流＋**末尾文本池**（池起点＝最后一次 `0D 02`，池序＝流程序）；文本 `%K`=待键／`%n`=框内换行／`%IF0`名`%IL0`姓；★**一条记录可含 2 个 `%K`** ⇒ 逐处断行 | `engines/hunex-als.md` |

| **Koei PS2「EMBINS.VVV」单模块镜像** | **アンジェリーク トロワ(PS2, 2000)** | 正文＝根目录 `EMBINS.VVV` 里「代码+cp932 串池」混排（0x12F0–0x8C3504），明文不压；串＝一框＝一次点击；**主角名＝1–16 B NUL 空位**（判据见册）；选项＝单 `\n` 结尾且第 2 行起全角空格缩进 | `engines/koei-embins-ps2.md` |
| **Koei PS2「HD/BIN + PACK」** | **アンジェリーク エトワール(PS2)** | `.HD`=u32 尺寸表(无偏移)、`.BIN` 每条 2048 对齐；条目 #0=`FILENAME.LST`(索引即名)；`PACK`＝`A/B/dataOff(=A+B)/dataSize`＋`count/recSize=64` 成员表(name[48]+off/stored/decomp/step)；★内层**已破解**：PACK 头 name 区＝XOR KEY，段首 u32 判 type1(LZSS)/type2(MTF+RLE) | `engines/koei-pack-ps2.md` |
| **Rejet ADV（`PacK` ＋ 明文标签脚本 `.ald`）** | ビタミンR（PSP `ULJS00592`，2013） | `PacK` 头＋**0x400 对齐 gzip 成员流**（4256/4256 可解）；成员＝**明文 CP932 标签脚本**：`<pb>` 换页／`<wait key="true">` 等待＝一次点击，`＠<名>` 名前札、`%name%`/`%family%` 主角宏（默认名在 EBOOT 串池＋`0010.bin`）；`0017.bin`＝用語辞典（首字段＝解说者 id，非常量） | `engines/rejet-pack-adv.md` |
| **BROCCOLI 自研指令流（Switch `0xFF op` 流）** | **うたの☆プリンスさまっ♪ All Star After Secret(NS)** | 脚本＝`novel.cpk` 内 `DATAxx/xx_Story.dat`（无容器无压缩）；指令 `ff <op> <id LE> ...`：`0x0A`(12B 头，样式 00CC/07DE/00D5)・`0x00`(4B)・`0x0E/0x0074`(选项，16B 头)・**id `0x07DD`＝ruby 文本**；★**文本＝逐字节 XOR 0xFF 再 CP932**（`7e8a→「`）；★**框结束＝`0A/00CC` 空载荷**；`0x876E`=㌻改行・`32A4-A6`=㊤㊥㊦演出标记（剔）；主角名＝同框首个 `0A/00D5` | `engines/broccoli-opfflow.md` |

| **BROCCOLI×NIS Switch 移植（CRI CPK 6 件 + `sn.bin`）** | **うたの☆プリンスさまっ♪ All Star(NS `0100B3E0149FC000`)** | RomFS＝`bg/bgs/bgm/se/vo/sys.cpk`＋`font48*.xtx`＋**`sn.bin`（剧本，LZSS）**＋`movie/`，**无 novel.cpk**；CPK **EnableFileName=0/TocOffset=0** ⇒ 偏移＝ID 升序＋Align 2048 累积（校验：累积和==ContentSize）；`bgs.cpk` 1849×130,592B 全是 xtx；`sys.cpk` 106 无压缩 UI 成员 | `engines/nis-cpk-snbin.md` |
| **Rejet ADV · 变体 B（`PACK` ＋ `YOX` 串池字节码）** | **スカーレッドライダーゼクス STARDUST LOVERS（PSP，2011-12）** | EBOOT tag 与ビタミンR 同为 **`D91613F0`**；唯一载体 `USRDIR/image.bin`＝`PACK` 头（count=345，表项 **0x90**，`[2]`=offset `[3]`=size **直排可用**，name@+0x10）；脚本 `*.SCE`＝`YOX`：头部 16B→指令流→**尾部明文 CP932 串池**（NUL 分隔、末条 `<名> - end` 自校验）；**取池法＝能按 CP932 解到文件尾的最长后缀**（免反汇编）；每条文本串**恒以 `@I@P` 收尾**（9719/9719）⇒ 换页与等待同体 ⇒ **单版**；`@L` 软换行合并、`@Vs00`姓/`@Vs01`名＝主角宏 | `engines/rejet-pack-adv.md` §变体B |
| **CRIWARE 系 ＋ `sn.bin` LZSS（BROCCOLI 移植）** | うたの☆プリンスさまっ♪ **Repeat LOVE(NS)**・All Star(NS)・After Secret(NS) | romfs 只有 `*.cpk`＋`font*.xtx`＋**`sn.bin`**；sn.bin＝`[u32 解压尺寸][LZSS 0x1000环/0xFEE起点]`；记录 `4F0D` 开框＋`45FFFF` 正文＋`4AFF6A` 收框 ⇒ **单版**。★**同族格式完全一致，开工先 Grep `解析报告/` 查历史**（我盲猜压缩算法浪费数小时） | `engines/cri-snbin-lzss.md` |
| **Switch「BKTR」PatchRomFS（更新档）** | スチームプリズン・テミラーナ・ヴィルシュ・ネオン 等 NS 更新档 | `hactool` 报 `Failed to read RomFS directory cache` ⇒ 不是密钥错，是 patch NCA（crypt_type=4）。BKTR＝**相对 base 的字节级差分＋重定位表**，虚拟空间＝base 整段（含 IVFC hash 层）⇒ 导 base romfs 再合并**注定失败**。用 `scripts/bktr_romfs.py --changed` 先看改动面 | `engines/platform-switch-bktr.md` |
| **STCM2L「定 op 五步法」** | SympathyKiss・KLAP!!・終遠-EpiClycoris・ラディアンテイル 本体/FD | ★**同构建串 ≠ 同结构**（KLAP 与 SympathyKiss 构建串一字不差、op 编号整套不同，直接套用跑出 0 行）。`0x1f4` 四作都是收框；名札/正文靠**两个不同文本 op** 区分（不是 kind 字段）；收框后**引号配平＋最长行 23→100+ 字** 是 L0 自证 | `engines/stcm2l-op-census.md` |
| **Unity 文本载体速查（本批 6 型）** | Honey Vibes・My9・もし神様・テミラーナ・ミストニア・ハンサム 等 | `Data/StreamingAssets/Script/*.h` 命令 DSL／`.kaiso`(UTF-16LE+BOM)／`.qui`(Lisp)／**UTXT+chartable(4413字,行尾`\r\n`参与编号)**／**Utage「宴」`.book`**／**Naninovel 定制 `CMsg`（正文在前导 `CommentScriptLine`，`Text.value` 是语音三元组）** | `engines/unity-text-carriers.md` |
| **IL2CPP metadata 字段表 / 枚举速查** | 十三支演義（卡点）・任何 IL2CPP 作 | 零依赖工具 `scripts/il2cpp_fields.py`：读 `global-metadata.dat` 的 typedef/field 表与枚举（version=29 标定 `typedef 0x58`／`field 12`／`fieldStart@typedef+0x20`／`fieldCount@typedef+0x44`）。★**要字段序不必装 C# Il2CppDumper**；但**方法体（序列化编码宽度）读不到**，那时才需要 dumper | `scripts/il2cpp_fields.py` |
| **KID 自研 `mlk/ADV`**（ARC0 归档 ＋ `.cpp` 文本 DSL） | 水の旋律 ～協奏曲～ / After Story（PC 2006） | ARC0 ＋ 文本 DSL；`mizumelody_arc.py` 解包、`mizumelody_text.py` 成行 | `engines/arc0-mlk-adv.md` |
| **Nintendo「Bezel Engine」＋ `.nx.bea`(SCNE)** | romfs 有 `boot.lua` + `Archive/*.nx.bea`、**无** `Data/Managed` | **不是 Unity**，别找 Assembly-CSharp/TextAsset；SCNE 剧本读取见册内 | `engines/platform-switch-bezel-bea-scne.md` |
| **VSC · VDP 容器 + LSB 脚本** | ラスト・エスコート2（PS2 / ヴァンテアンシステムズ） | VDP 容器 ＋ LSB 字节码；同社 2004 年另一套见 `vsc-vl-file-tml.md` | `engines/vsc-vdp-lsb.md` |
| **VSC · vl_file（PAC/MemPack + vlLZSS + TML）** | 召しませ浪漫茶房（PS2 2004 / SIMPLE2000 Vol.98） | vlLZSS 解压 ＋ TML 字节码 | `engines/vsc-vl-file-tml.md` |
| **STCM2L · UNI2（PSP）第 5 样本** | 恋愛番長 命短し、恋せよ乙女！（PSP `ULJM05742`） | 同族基础见 `idea-factory-stcm2l-psp-uni2.md`；本册只记本作差异 | `engines/idea-factory-stcm2l-psp-uni2-banchou.md` |
| **STCM2L · CPK（PSP）第 7 样本** | 恋愛番長2 MidnightLesson!!!（PSP / Rejet 2012） | 记录尾部锚定 / cmd 逐作变；只记本作差异 | `engines/idea-factory-stcm2l-psp-uni2-banchou2.md` |
