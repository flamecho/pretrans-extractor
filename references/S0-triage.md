# 未知游戏 · 判型与攻坚（拿到没做过的一作，从这里开始）

> **本册只解决一件事：这东西是什么，该走哪条路。** 每行末尾给「详见」，只打开命中的那一册。
> 顺序：**A 平台 → B 容器 → C 脚本层 → D 厂商速判 → E 全不匹配时的攻坚 → F 成行/交付**。
> 判型不要凭「看起来像」；每条都给可验证信号。**禁穷举、禁 OCR**（见 `SKILL.md` §0）。

## 两条路径（先决定走哪条，再往下看）

| 情形 | 走法 | 目标 |
|---|---|---|
| **命中已知引擎**（B / C / D 任一表能对上） | **快速路径**：只打开命中的 `engines/<slug>.md`，照它的「容器链路 → 脚本记录 → 成行」执行，优先复用其 `scripts/*.py`（**按引擎查 `../scripts/INDEX-BY-ENGINE.md`**；不知道文件名是哪个 ⇒ `INDEX-BY-SCRIPT.md`；工作版查 `TOOLS-works-<引擎族>.md`；只改路径/键/参数） | 跳过判型与试错；同族续作通常 **30 分钟到可读文本** |
| **未命中**（表里没有、或解出来不成词） | **规范路径**：§E 四步攻坚 → `S4-record-patterns.md` 认记录形状 → `S6-lines.md`/`S6-typing.md` 成行 → `S7-selfcheck.md` 自检 | 不踩坑地拿全文本；慢但可收敛 |

> 判据：**能说出「引擎名 + 容器名 + 记录形状」三件套 ⇒ 走快速路径；说不全 ⇒ 走规范路径。**
> 两条路都必须守 `SKILL.md` §0（宽度感知 / 禁穷举 / 禁 OCR / 不改写 / 一次点击＝一行）。

## A. 先定平台（看母本形态，30 秒）

| 母本长相 | 判定 | 第一步 | 详见 |
|---|---|---|---|
| `app/PCSGxxxxx/` ＋ `work.bin` / `*.zip` 内含 app 树 | **PSV NoNpDrm** | `pkg2zip` → 再 `psvpfsparser -z <zRIF>`（**两层**） | `S2-psv-pfs.md` |
| `*.iso` ＋ `PSP_GAME/` ＋ `EBOOT.BIN` | **PSP** | 直接读 ISO（ISO9660）；EBOOT 头是 `~PSP` 才需解密 | `S2-psp-eboot.md` |
| `*.xci` / `*.nsp` / `*.nca`；TID 形如 `0100xxxxxxxxx000` | **Switch** | `hactool -t xci/nsp --keyset`（Gamecard 用 Standard crypto，不一定需要 titlekey） | `S2-switch-nca.md` |
| `*.exe` ＋ `data/` `*.arc` `*.pak` | **PC** | 先看 exe 版本与资源目录名（决定引擎族） | `S3-archive.md` |
| `*.chd` | 压缩镜像 | `chdman extractcd/extractraw` → ISO | `S1-image-chd.md` |
| `*.nsz` / `*.xcz` | Switch 二次压缩 | `nsz -D` 还原 | `S2-switch-nca.md` |
| 只有 `*.rar` / `*.7z` | 压缩包 | `7z l` 看结构；**头部加密时名单列不出**，密码常在随包小 txt | `SKILL.md` S1 |

## B. 容器层：拿头部特征串对照（`probe.py hex/strings` 看前 64B）

| 头/特征串 | 容器 | 工具与要点 | 详见 |
|---|---|---|---|
| `CPK ` ＋ `@UTF` | **CRI CPK** | `cpk.py`；表偏移算法有 `>>8` / `&0xFF` 两版，**用 `@UTF` 与解出的文件名验证**；数据区可能再套 CRILAYLA | `engines/cri-cpk-afs.md` |
| `AFS2` / `AFS\0` | **CRI AFS** | 索引区在尾部；花梨式自研「SJIS 索引码」另算 | `engines/cri-cpk-afs.md` |
| `XP3\r\n` | **KiriKiri** | 三种态：标准 / DropWave OTag（`.ks` 为 zlib+UTF-16LE）/ 区间 1 字节 XOR | `engines/kirikiri-xp3.md` |
| `PFS ` / `PSPFS_V1` | PSV PFS / PSP 自研 | PSV 需解密；PSP 版见 oni | `S2-psv-pfs.md` / `engines/oni-psp-tob.md` |
| `NCA3`（明文头在 `0x200`） | **Switch NCA** | PFS0 → NCA3 → RomFS | `engines/platform-switch-nca.md` |
| `PSARC` | Unity / 通用 | 再进 `resources.assets` / `TextAsset` | `engines/unity-adv.md` |
| `MZ\0\0` | **Marvelous MZ 命令流** | 串 `[u16 tag][u16 wc]+wc*4 cp932`；正文 `0x62`（首 u32=msgid）、选项 `0x51` | `engines/mz-cmdstream.md` |
| `HFU2` | **HuneX IKA SEQ** | `26 <cmd> 24 <n>` 字节码；`_ZM`＝一次点击 | `engines/hunex-ika-seq.md` |
| `mrgd00` / `MZX0` | **HuneX Ogre / allscr** | MZX0＝字面 XOR `0xFF`；脚本是 `_CMD()` 文本 DSL | `engines/hunex-ogre.md` |
| `STCM2L`（如 `STCM2L Jul 12 2010`） | **Idea Factory STCM2L** | 记录 `[0][L/4][1][L][text]`；`[u32 size][payload]` 链；**opcode 可能逐文件移位** | `engines/idea-factory-stcm2l.md` |
| `LSDARC V.100` / `SCR 2.00`·`3.00` / `LSD\x1a` | **Takuyo gss** | **按文件头判版本，不按平台推定**；`SCR 3.00` 还打包（`H`uffman/`D`elta/`R`LE） | `engines/takuyo-gss.md` |
| `PSB\0`（外壳可能再套 MDF / PGD） | **M2 ADVENGINE** | `fileinfo.psb.m`＝根索引；`INSDIR/INSTALL.BIN` 常是 PGD（全部数据在里面）；顺序看 `scenelist.json` | `engines/m2-advengine-psb.md` |
| `LIBP` ＋ `exec.dat` | **Malie System** | PC＝Camellia；Vita＝LIBP 明文、offset 块单位 2048 | `engines/malie.md` |
| `ATL.DLL` ＋ `scene.db`（SQLite） | **Aromarie ATL** | 剧本在 SQLite 表里，不在文件系统 | `engines/aromarie-atl.md` |
| `data.dat` ＋ `pct_mess.dat` ＋ `script_*.dat` | **Plan Peace PCT** | 单一归档＋消息池＋字节码三件套 | `engines/planpeace-pct.md` |
| `ROM2` ＋ `*.snr` | **Kalmia8 ROM2/SNR** | — | `engines/rom2-snr.md` |
| `DATA2/*.FPK` ＋ `*.VML` | **D3P PS2（VML）** | 载荷全落 0x21–0x7E ⇒ **JIS 7bit**；正文 `68 00 00 FF`、名札 `64 00 00 FF`、选项 `F6 01 00 FF` | `engines/d3p-ps2-fpk-vml.md` |
| `EMBINS.VVV`（ISO 根目录，或 `DATA/*.VVV`） | **Koei PS2 单模块镜像**（2000 期） | `EMBINS`＝代码+cp932 串池混排；正文＝池内 NUL 结尾串（**一框一点击**）；主角名＝1–16B NUL 空位；⚠`STORY.VVV` 多为图像别上当 | `engines/koei-embins-ps2.md` |
| `*.evb` ＋ `MARC` | **Otomate PSP** | 正文＝2 字节大端字符码；成框**必须前向扫描** | `engines/otomate-evb-marc.md` |
| `YDP1` ＋ `DATA_B/`·`DATA_W/` | **Idea Factory PSP YDP1** | 组表 0x20/条 ＋ 全局目录 0x28/条；**闭合 `Σstored + 头0x10 == filesize`**；脚本组 `SCRIPT_LSB`（`EV*.LSB`，名札与正文零间隔） | `engines/idea-factory-ydp-lsb.md` |
| `*.wsc` / `Rio.arc` | **WillPlus AdvHD** | WSC 每字节 `rotl_8(c,6)`；`op41` 旁白 / `op42` 名＋台词 / `op02` 选项 | `engines/willplus-advhd.md` |
| `KAG3` / `.ks` 明文 | **KAG（同人/旧 PC）** | 标签脚本，按 `*label`＋正文行直取 | `engines/misc-engines.md` |

> 表里没有？**别猜**。先跑 `identify.py`，再按 **E** 走。

## C. 脚本层（容器解开后按后缀/头判）

| 后缀 / 头 | 常见引擎 | 记录格式要点 | 详见 |
|---|---|---|---|
| `.ks` `.tjs` | KiriKiri | 标签 + 行文本 | `engines/kirikiri-xp3.md` |
| `.scd` | Otomate DAT+PAK+SCD | `<u16 len><utf8>`；名札随作变（char_id / `"名前"`） | `engines/gakuenk-dat-scr.md` |
| `.spt` | System-NNN | **4 字节对齐槽**（`[data][NUL][填充]`）⇒ 按网格走 | `engines/system-nnn.md` |
| `.scr`（`LSDARC`） | Takuyo gss | op `0x5a`/`0xfc`/`0xf0`/`0x5c` | `engines/takuyo-gss.md` |
| `*.bytes` | KONAMI（Unity IL2CPP） | 指令 `05 03 <u16>` 引字符串池；池有 XOR 键 | `engines/konami-unity-bytes.md` |
| `.assetbundle` / `resources.assets` | Unity | TextAsset / MonoBehaviour 里找串 | `engines/unity-adv.md` |
| `.dat` ＋ 定长表 | 各家自研 | 先找**索引表**（地址/长度），再用「记录驱动扫描」 | `S3-archive.md` |
| `.txt` ＋ `@命令` | 纯文本 ADV（LTEngine / Matatabi 等） | 直接按行/命令切，注意 `@n` 语义逐作不同 | `engines/lte.md`・`engines/matatabi-unity-textadv.md` |

## D. 厂商 / 品牌 → 引擎（没有魔数时最快的旁证）

| 品牌 / 现象 | 多半是 | 详见 |
|---|---|---|
| Otomate / Idea Factory（PS2/PSP/PSV/NS） | STCM2L（PSP 双容器：CPK / UNI2）；PSP 另见 `.evb`+MARC、**`YDP1`+LSB（カヌチ 系）** | `engines/idea-factory-stcm2l.md`・`engines/otomate-evb-marc.md`・`engines/idea-factory-ydp-lsb.md` |
| Koei / Ruby Party | CDAR v2/v4 · pasc 节点流 · **PS2 早期＝`EMBINS.VVV` 串池** · 2004 PS2＝HD/BIN+PACK | `engines/koei-cdar.md`・`engines/koei-pasc.md`・`engines/koei-embins-ps2.md` |
| HuneX | Ogre（allscr/MZX0）/ IKA SEQ（HFU2）/ HESL | `engines/hunex-*.md` |
| Takuyo | gss（LSDARC + SCR x.xx） | `engines/takuyo-gss.md` |
| 5pb. / MAGES. | MPK+SC3 / AFS 文本池 | `engines/mages-sc3-mpk.md`・`engines/mages-afs-yourmo.md` |
| D3P | CRI CPK ＋ 自建位图字体；PS2 期乙女作另走 FPK＋`.VML`（JIS 7bit） | `engines/stormlover-d3p.md`・`engines/d3p-ps2-fpk-vml.md` |
| dramatic create（移植） | 多沿用原作 HuneX Ogre，但**布局逐作不同** | `engines/hunex-ogre-dramaticcreate.md` |
| 同人/旧 PC | KiriKiri / NScripter / Siglus / BGI | `engines/misc-engines.md` |

## E. 全都不匹配时的攻坚顺序（通用，按此四步，不要跳）

1. **先找明文**：`probe.py strings --jp` / `jp` 看是否有可直接读的假名汉字串。
   - 有 → 直接定界（找记录头/长度域），跳过码表问题。
2. **没有明文 → 找字符表**：ELF/字体/独立表文件；**用一条已知明文锚定基址**（禁穷举）。
3. **有压缩 → 先认压缩**：`zlib`（`78 9C`）、`LZSS` 变体、`MZX0`、CRILAYLA、Huffman；**认错压缩比认错加密更常见**。
4. **自定义字节码 → 找「表」而不是找「指令」**：地址表/长度表/字符串池通常比 opcode 语义好认；
   用**文本记录驱动扫描**（记录自带长度自定界）⇒ 永不失步；**先认形状见 `S4-record-patterns.md`**（P1〜P8）。
5. **定「一次点击」边界**：找连续文本记录之间**必现的标志**（12B `[0][cmd][flag]`、`_ZM`、`0x10/0x11` 节点等）；
   找不到标志时，按「同一指针推进的连续串＝同一框」假设并用**引号配对**验收。

> 每步下结论前，先对照 `S4-false-signals.md`（27 条「看着像判据其实会骗」的反例）。
> 卡住时回到 `00-discipline.md`：**同假设 2 次无新信息 ⇒ 换路；单点 >3 次 ⇒ 汇报**。

## F. 成行与交付（判型之后固定不变）

- 成行：**先过 `S6-lines-proof.md`（断框判据必须 L0/L1，L2 只作探针）** → `S6-lines.md`（规则）＋ `S6-typing.md`（定框）；
- 名札/主角宏：`S6-lines-names.md`（识别）・`S6-lines-names.md`（保留判定）・`S5-names-macro.md`；
- 自检：`S7-selfcheck.md` ＋ `scripts/check_text.py`；
- 报告：`S7-external-report.md`。

## G. 新发现往哪写（保持可迁移）

| 新东西 | 写哪 |
|---|---|
| 新引擎 | 新建 `engines/<slug>.md`（**首段必须是「识别特征 → 容器链路 → 脚本记录 → 成行 → 易错」**）＋ `engines.md` 加一行 |
| 已知引擎的新变体 | 追加到该引擎册；若布局差异大，另立 `-<变体>.md` |
| 通用判据（跨引擎成立） | `S5-basics` / `S3-archive` / `S3-archive-delta` 等对应阶段册 ＋ `pitfalls/` 对应层 |
| 仅某作成立的巧合 | **不写进 skill**（写 `WORKS-<族>.md` 的作品块） |

## H. 未命中之后必须回填

`§E` 走通后**当场**补：本册 `§B` 加一行 ＋ `engines/<slug>.md` ＋ `engines.md` 路由。
细则与判据见 `S8-wrapup.md` §「未命中后的回填」。
