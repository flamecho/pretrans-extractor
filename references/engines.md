# 项目 _trans —— 引擎复用要点（全量）

> 引擎复用要点全集。每个引擎含：平台/源、容器格式、解密/解压步骤、脚本结构、文本语义、陷阱、对应脚本。
> 跨引擎的通用铁律见 `SKILL.md`；命令行手册见 `SKILL.md` §工作流。

## 引擎复用要点

- **PSV NoNpDrm**：pkg2zip -x → `<psvdec>/…/psvpfsparser.exe -i app/<ID> -o dec -z <zRIF> -f cma.henkaku.xyz`（zRIF 由你自己的 dump 生成；放行 `cma.henkaku.xyz:80`，前台运行）。
- **Switch XCI/NCA/NSP**（Paradigm Paradox 定案）：XCI 卡带分区可**明文**，root HFS0 偏移在 XCI 头 0x130；NSP(PFS0) 条目 `{u64 off,u64 size,u32 nameoff,u32 pad}`（0x18/条，表在 0x10，数据基址=0x10+N*0x18+strsize）。**NCA3 明文头在 0x200**（0x00 Fixed-Key / 0x100 NPDM 签名）；keygen=`max(hdr[0x206],hdr[0x220])-1`；段头 `@0x400+i*0x200`。**头 XTS 用大端 sector tweak**（`AES(k2, sector.to_bytes(16,'big'))`）。段数据 CTR：key=解密后 key area **slot2**；计数器=`rev(section_ctr)`‖`BE(pos>>4)`，须 16B 对齐起解；key_area 用 `key_area_key_application_XX`(XX=max(crypto,crypto2)-1)；RomFS 在 IVFC 末级。**Titlekey** `=AES_ECB_dec(titlekek_keygen, tik[0x180:0x190])`；★ hactool `--titlekey=` 传**加密 titlekey**。`prod.keys` 里 17B 的 `mariko_master_kek_source_*` 坏条目会让 hactool 报错 → 先过滤。参考 `<kuriimu2 源码>`。
  - ★★ **NSP 实测补充（悪役令嬢，2026-10-05）**：① **hactool 选项须写 `--keyset=<path>`，`-k <path>` 这份 build 不生效**（会回落到默认 prod.keys）。② **`hactool --titlekey=` 收的是 `.tik[0x180:0x190]` 里那段「加密」titlekey**，hactool 会自己再解一遍并打印 `Titlekey (Decrypted) (From CLI)`；真正生效的 titlekey = `AES_ECB_dec(titlekek_N, tik[0x180:0x190])`。③ **titlekek 索引 = NCA 的 Master Key Revision（`max(hdr[0x206],hdr[0x220])-1`），不是 ticket 的 0x285**（两者可差 1：本体 NCA 0x10 / ticket 0x11；更新 NCA 0x11 / ticket 0x12）。④ ticket 布局：sig(0x140)+Issuer(0x40)+TitleKeyBlock(0x100 @0x180)+…，`0x280` 版本、`0x281` titlekey type、`0x285` master key rev、`0x2A0` rights id。⑤ **旧 hactool(2020) 本体（titlekey crypto）能整段解 RomFS**；但遇 **BKTR 增量更新段会 segfault**，`--baseromfs`(用 `--romfs=`/`--section1=` 的产物) 亦报 `Failed to read RomFS directory cache!` ⇒ 增量更新落不了地；此时可**直接解更新段的 section1 并读其中 RomFS 文件表**（文件名明文可辨）来判断更新是否动了文本。⑥ `--exefsdir=`/`--romfsdir=` 可一次解出。⑦ 判定更新只加语言的实例：更新段文件表里同时出现 `adv101.CSR` 与 `adv101_en.CSR` → 仅补英文化。
- **Koei CDAR v2/v4（コルダ/遥か）**：文本记录 `04 <u16 len> <cp932> 00`；一次点击=框边界 BOUND/M91/C7。参考 `koei/Cdar.cs`。工具 `corda_*_extract.py`/`haruka*_extract.py`/`geten_extract.py`。
- **Otomate VM（BAW/フォルティッシモ）**：JIS X0208 字库；块 `…0xff68…`；**字体替换槽随作而异，禁跨作套用**；人名用 vndb 校。
- **STCM2L**（Idea Factory Switch）：行内 UTF-8 明文线性，三级边界。工具 `stcm2l_extract.py`。
- **CRI CPK**：`cpk.py`((m>>8)&0xFF) / `cpk_v1.py`(m&0xFF)；判据 `@UTF`。
- **Regista advGame（Paradigm Paradox）**：资源 `.atd/.ktx/.spd/.zsn/.dbx/.awb/.cpk/scr.pack`。自研 PRNG 流密码（XOR）：密钥 **`"regista"`**→seed=0x2EF；乘数 `0x6C078965`；`s[i]=m*(s[i-1]^(s[i-1]>>30))+i`；每字节 `x13^=x13<<11; x13^=x13>>8; out x10&0xFF`。同法解 `scr.pack` 与 `DATABASE/flowChart.dbx`。剧本容器 `[u32 count][count×{u32 size,u32 aux}]`，数据自 0x800；`AB <u16> <UTF-8> 00`=一行；`47 0D 00 <UTF-8> 00`=说话人名；`5F/AC/6A/BE/4A/49`=跳转；`%R<读音>%R<字数><正文>`=注音(留正文)、`%h1`=主人公名(默认 **ユウキ**)、`%N`=高亮(剔)。工具 `paradigm_paradox_extract.py`。
- **Artemis Engine（滄海天記）**：归档 **PFS「pf8」**：头 11B `"pf8"+u32 index_size+u32 file_count`；条目 `{u32 namelen,name,u32 sep=0,u32 offset,u32 size}`。**加密**：`key=SHA1(file[0x07:0x07+index_size])`(20B)，**整文件逐字节 XOR key 循环**（.mp4/.ogv 除外）★ 社区「只 XOR 前 20B」是错的。剧本 `script/*.ast`（`astver=2.0`，明文 Lua 风）；**一次点击 = 一个含 `text` 的 block = 一行**；正文=顺序拼 `ja[0]`；`rt2`=框内改行(合并)、`ruby`=注音(留正文)、`name`=说话人名(剔)；`select.ja` 每项一行；`game_dic.ast`=用語辞典；`scene*.ast`=回想包装(重复→剔)。工具 `artemis_pfs_extract.py`。
- **BGI/Ethornell（ブラザーズ）**：入口 `BGI.exe`；`.arc`=**PackFile v2**：头 12B `"PackFile    "`+u32 count；条目 **32B**`{name[16],u32 off,u32 size,u32,u32}`；数据紧随表。`data01xx`=剧本。**DSC 压缩**：`"DSC FORMAT 1.00\0"`(16B)+u32 key+u32 out_size+u32 dec_count；0x20 起 512B **加密 Huffman 深度表**（逐字节减 PRNG）；0x220 起 Huffman+LZ（MSB first）；PRNG `v0=20021*(key&0xFFFF); v1=(magic|(key>>16))*20021+key*346+(v0>>16); key=(v1<<16)+(v0&0xFFFF)+1`（`magic=u16@0<<16`）；回引 `code>=256 → len=(code&0xFF)+2, off=getBits(12)+2`。剧本 V1 u32 opcode：`0x0003 <u32 绝对串址>`压串；`0x0140/0143/0145`显示消息(一次点击)；`0x0160`选择支；`0x00F0`载脚本；`0x007F <名址> <行号>`调试→**清栈**；未知只吃 4B。**消息：栈顶=说话人名、次顶=正文**（与他作相反）；仅 1 个=旁白。**选择支：`0x0020` 后紧跟 `0x0003` 压串=一个选项**，在 `0x0160` 成组取。主人公标记 `《鈴音》`→只去括号留名。播放序：从 `main` 按 `0x00F0` 调用图 **DFS 前序**；两盘分开。剔 `scene_*`/`makerlogo`/`omakesetup*`/`*_old`。参考 `Jair4x/ethornell-tools`、`KlparetlR/Bgi_asdis`、`lifegpc/msg-tool::scripts/bgi`。工具 `brothers_kiss_extract.py`。
- **System-NNN（あさき、ゆめみし～ひととせ～）**：`spt/*.spt`(剧本)+`spt/*.xtx`(纯 cp932 配置)+`.fxf`/`scene.dat`+`dwq/*.gpk`+`cdvaw/*.vpk`。**`.spt` = 整文件 XOR 0xFF**；取反后 0x30=魔术字 **`SPTHEADER0`**、0x00 u32=0x20。布局 `[版本][指向表]["SPTHEADER0"][指令流][字符串池][指令块][字符串池][资源名表]`。**字符串池=NUL 结尾 cp932，按执行顺序=点击顺序**；消息=**`<说话人名>\r\n<正文>`**（无 `\r\n`=旁白）；人名表 `spt/charaname.xtx`。标记 `#名`(主人公名)、`？？？`；控制码 `#［Nよみ］`=注音(留正文)、`#名`=主人公名(inline)、`#心`=图标(剔)、`\r\n`=框内换行(合并)。**陷阱**：两消息间偶夹 1~3B 控制数据，cp932 解码时污染下条串首字 → **三级重同步**（①字节级 `^<人名标记>\r\n`(p=0..5) ②字级容忍≤3前置垃圾字 ③首字可疑时逐 p 前进）。工具 `asakiyumemishi_extract.py`。
- **LTEngine（Rejet；Tiny×MACHINEGUN）**：源 = **RAR5 自解压 exe**（PE 段止于 `0x48E00`，其后 `52 61 72 21 1A 07 01 00`）；`7z x` 无密码。目录 `Module/{exe,gd.dat,sd.dat,pf.dat}`+`Resource/{Scenario,Layout,Object,Sound,Texture}.rpd`。**所有 .dat/.rpd 整文件 XOR 0xFF**。`.rpd`=`u32 h0(索引区大小取反)|u32 count|count×{u32 namelen,name(cp932),u32 size,u32 dataoff,u32 flag}`；`Scenario.rpd`=剧本 `.lt`。**`.lt`=明文 cp932 XML 风标签脚本**：`＠<说话人名>`独占一行（**不加前缀**）；**`<pb>`=页断=一次点击**；`<select><case value="…">`=选项；`<jump file=…>`换脚本。陷阱：①`<if condition="A >= B">` 的 `>` 在属性内 → 去标签**必须引号感知**；②内联 `//ＢＧ：…` 按 `//` 截断；③说话人可被 `<color>` 包裹 → 去标签后再判 `＠`；④畸形未闭合标签→吃到行尾丢弃。`.dat`：`gd/sd.dat`=XOR 后 **SQLite**；`gd.dat.tips`=**用語辞典**(`word/explain/variablename`)；`pf.dat`=XOR 后 Boost.Serialization XML。排序：自 `ltstart` 按 `<jump file>` 调用图 **DFS 前序**；★ 目标大小写不一 → **匹配须 case-insensitive**。`シーン回想01–94` 全命中主线 → 剔。工具 `tiny_machinegun_extract.py`。
- **NScripter（時函 / ときたま！ 定案；亦见月東日西/月姬等）**：PC 安装包常为 **Inno Setup**（`Inno Setup Setup Data (5.x)`）→ `innoextract.exe -e -d <dir> <setup.exe>`（免安装/无密码，GitHub `dscharrer/innoextract` 直连可下）。本体 `nscript.dat`（**整文件逐字节 XOR 0x84** → cp932）+ `arc*.nsa` + DLL。**文本语义（`*define` 内无 clickstr/linepage 时）**：`@`=显示+等待点击(同页继续,不清框)；`\`=显示+等待点击(**翻页清框**=一页结束)；`br`=框内空行(不等待)；`/`=取消行末换行；`_`=取消下一次等待。⇒ 按 `@`/`\` 切分，每段=一次点击=一行。★ **进入新 `*label` 时结页**（分支/随机台词互斥，否则并成一行）；※「每页文本为一行」的分页机制已废弃（2026-10-05），勿再套用。★ `clean()` 须去字符串内 `\`（精灵内换行符）。**行判定**：首字符 ASCII 字母/`_`→命令；`*`标签 `;`注释 `~`跳过 `:`续行 `"`csel续行；否则文本。★ **命令行尾随正文** `if <条件> <正文>` 须单独识别（剥条件后余下以日文/全角/`#RRGGBB`/`@\` 开头），并排除 `if $0 == "…" #RRGGBB【名前】` 名札块。★ **选择系统可能自研**：除 `csel`/`selgosub` 外，常用 `mov $select_textN,"选项"`(N=1–4)+`gosub *select`，提问横幅 `mov/add $seltext_spN,"…"` → 都收。行内清理：注音 `(漢字/よみ)`→漢字、`#RRGGBB`、`!s0`/`!d300`、精灵前缀 `^:s/…;`、全角空格首尾。★ **`$var` 人名/文本替换=数据流解析**：①已知人物名映射**优先且不被覆盖**；②其余 `$var` 取「此前最近一次赋值」，默认=首次可静态求值赋值；③运行时计算(itoa/getparam/输入)→置 None 保留 token。坑：不锁定①时条件分支 `mov $x,$y` 会把已知名冲成 None → 大面积漏替换。★★ **GAiji**：`exec_dll "dll\NSFont.dll/gaiji,<字符>,<图片>"` → 该字符是**图标**。如 ときたま 的 `騾`(**U+9A3E**)=`sys\heart.png` → 输出 `♥`。★★ **「大判セリフ」裸名札**（ときたま 8 处）：演出 `gosub *text_win_shade`+`*big_words` 时把说话人名当普通文本行写入（`【　椿　】`），与台词行间**无 `@`/`\`** ⇒ 会被并成一行，按「不加前缀」须剔 `^【[^】]*】$`。常规对白人名叫走 `name "…",0` 不进正文流。工具 `tokihako_extract.py`/`tokitama_extract.py`。
- **MNP（DonMaccow 自研；KoiGIG 定案）**：PC 包常为 **RAR5 自解压 exe** → 内 **UDF ISO**（`*PxMas::Windows 9x`）→ `Setup/Disc1/`+VB6 `setup.lst`。归档 **`ARC!`/MMA**：`0x00 "ARC!"`／`0x04 u32 index_off(=0x24)`／`0x08 u32 entry_size(=0x14)`／`0x0C ver(=1)`／`0x10 count`；条目 **20B** `{u32 off,u32 usize,u32 csize,u32 HeaderSize,u32 Flags}`（`off[i+1]=off[i]+csize[i]`）。**无文件名**：文件名表 = **entry[0]（Flags=0x2F）** 解出的 CP932 行文本。**解密**：密钥 32B（GARbro `Mnp/ArcMMA.cs` DefaultKey）：`Flags&6==4`(0x2D/0x0D)→跳 HeaderSize 取 usize 字节→`ROR8(b^key[i%32],3)`（多为加密 OGG）；`Flags&6==6`(0x2F/0x1F/0x0F)→整段 `XOR key`（首字节应 `0xC0`）后自定义 **LZSS**（ctl MSB-first；match=大端16b `len=(o&0x1F)+3, dist=(o>>5)+1`；literal=`ROL8(b,5)`）。**剧本** `sn_*`（CP932 指令流，`\r\n` 分行）；文本 = `put`(正文,一次点击=1行)／`site`(场景标题)／`item`+`select`(选项)／`nameinput`(输入提示)。★ **行首可带标签 `lb_02:put "…"` → 先剥 `标签:`**。控制码 `\v`/`\c`/`\np` 剔、`\var(nameN)` inline、`\n` 合并。变量默认值在 `data35` 的 `SystemInfo [Config] nameN=`；UI/系统在 `data35.mma`（`[Nameplate] item:N=【…】` 为名札表）。图片=`.mma` 解出头 `{宽,高,BPP,stride}`。工具 `koigig_extract.py`。
- **NScripter `.nsa` 变体（ときたま 定案；非标准 `NSAr`）**：头 **6 字节**；随后每条 `name(NUL结尾)+u8 pad+u32be offset(相对 datastart)+u32be size+u32be size`（尾 13B）；`datastart`=索引结束处第一字节。`read_nsa()` 见 `tokitama_extract.py`。内嵌 `kara_type\*.csv`（`时刻ms,歌詞,フリガナ`）；★ **フリガナ空的行=游戏内跳过**（前奏注记/`おわり`）→ 剔。
- **Unity 系（ハイリゲンシュタット）**：PSARC→resources.assets(TextAsset, DBIN)。工具 `psarc_extract.py`+`heiligenstadt_extract.py`。
- **Unity + 自研 ADV `CSR1.00`（悪役令嬢は隣国の王太子に溺愛される；OPERAHOUSE）**：Switch **NSP**（PFS0）→ NCA → RomFS = Unity 2020.3.47f1 + **IL2CPP**（`Data/Managed/Metadata/global-metadata.dat` 可搜类型/method 名）。文本在 `Data/StreamingAssets/`：`csr/adv{101..410}.CSR`（剧本）+ `localize.csv`（UI/章节/图鉴 Jp,En）+ `localize_name.csv`（说话人名表，ID 0=地の文 1=主人公…98=ナレーション 99=？？？）。**`.CSR` 格式**：`"CSR1.00\0"(8)+u32 header_size+(header_size-12)/8×{u32 label_id,u32 file_off}`；脚本流 `<u16 opcode> [operand]`：**`06 01`/`06 03` = 一个文本框**（后接 UTF-8 串 `\0`）、`04 10` = 提问横幅（后接串）、`04 11` = 选择支（后接 `u8 0` 再接串）；**正文内 `0x01` = 框内换行**（后常跟全角空格缩进，一并合并掉）；少数行前置非文本 token `1e XX XX XX 01`（记录内会再出现一个 text opcode）→ **取最后一个 opcode 之后的正文**即净。`prefab/*.jp`(UnityFS) 内文本只是编辑器占位（`アリア` 等旧 demo 残留），运行时走 localize，**勿收**。**无独立用語辞典档**。★★ **双文本框设计**（`advui.jp` 实测）：`MainText` 850×**150**px = 角色台词，**硬上限 3 行**（实测 2876/2238/1790 条分别为 1/2/3 行，≥4 行 0 条）；`NarrationText` 850×**620**px = 旁白/地の文（ナレーション id98 / 地の文 id0），全屏显示，可达 ~10 行。⇒ **长行 = 旁白单框，不是合并错误**。★★ **引号由 UI 自动加，脚本里没有**：全语料 9,7xx 条中 **「」出现 0 次**（旁白引用用 `『』`、独白内引用用 `“”` 代替）⇒ 「」是引擎补的。按前置 `06 00 <nameid>`（nameid 见 `localize_name.csv`）判定：**`06 01` 且有名字 = 角色台词 → `「…」`（4,876 条）；`06 03` = 内心独白 → `（…）`（2,028 条）；`06 01` 且 nameid∈{0 地の文,98 ナレーション} = 旁白 → 不加（2,553 条）**；`04 10`/`04 11`（提问/选择支）不加。脚本顶部 `BRACKET` 可切换，另出 `_全文本_无括号.txt` 变体。工具 `akuyaku_extract.py`。
- **NIS-NML（逢魔が刻）**：NSAC v2 容器 + `database.dat`。工具 `nsac.py`/`ouma_story.py`/`ouma_extract.py`/`ouma_build_text.py`。
- **SiglusEngine（VisualArt's；罪ナル螺旋ノ檻 定案，亦适用 Rewrite/AB!/SP 等）**：PC 发行常为 **单 exe = PE + RAR5 自解压**（RAR5 签名 `52 61 72 21 1A 07 01 00` 在 **0x48E00**，无密码）→ `7z x` → 内 **ISO9660** → `SetupData/GameData/`；或直接是文件夹版。关键文件：`Scene.pck`（剧本封包）、`Gameexe.dat`（配置）、`SiglusEngine.exe`（常 **AlphaROM 加壳**：节名混淆 `tvyziunz`/`hzgcbvdl`、无导入串 ⇒ **静态扫 key 不可行**）、`g00/`(图)、`koe/bgm/wav/mov/`。
  **加密模型**：`cipher[i] = plain[i] XOR FIXED_KEY[i%256] XOR EXE_KEY[i%16]`；Scene 用 `SCENE_KEY`(256B)，Gameexe 用另一张 `GAMEEXE_KEY`(256B)（两表在 `siglus_rs/crates/siglus_assets` 与 `hiroshil/SiglusEngine/Decryption.cpp` 中均可取）。
  **★ key 恢复（资源破解，不必跑游戏）**：用 `xmoezzz/siglus_static_key_tool`（Rust；`cargo build --release` 后 `--scene Scene.pck --game Gameexe.dat`）。原理：`Scene.pck` **头 92B 明文**（23×i32，`[0]==92`；index/name/size/data 各 (ofs,cnt) 对；`[21]=exe_angou_mod` 必须 ≠0）；每个场景 blob = `[u32 arc_size][u32 org_size]+LZSS`，**每 blob 的 EXE_KEY 索引均从 0 重启** ⇒ 由 `arc_size`(=索引里的 blob 长度) 直接得 key[0..3]；由解压后场景头前 16B 已知明文（`84 00 00 00` 即 `header_size=132`，出现于 dword0/dword3）得 key[9..12]；`org_size` 上界（回引最多 17 字节）+ LZSS 文法符号求解其余 → 唯一解，硬校验（多场景全解压 + Gameexe 全文 UTF-16 校验）。**本作 key = `42 2A BC 1E 47 DB 68 C8 91 74 C2 5B D6 47 99 11`**。LZSS（同 hiroshil `decompress`）：ctl 字节 LSB-first，bit=1→literal(1B)；bit=0→回引 2B `v`，`len=(v&0x0F)+2`、`dist=(v>>4)`。
  **Gameexe.dat**：`[u32 hdr][u32 needKey]` + `XOR GAMEEXE_KEY[i%256]` + `XOR EXE_KEY`（needKey==1 时）→ `[arc][org]+LZSS` → **UTF-16LE 文本**（全 `#` 配置项；**本作无 UI 文本**）。
  **`.ss` 场景块（解压后）= `S_tnm_scn_header`：132B = 33×i32**，字段名（顺序固定）：`header_size, scn_ofs, scn_size, str_index_list_ofs, str_index_cnt, str_list_ofs, str_cnt, label_list_ofs, label_cnt, z_label_list_ofs, z_label_cnt, cmd_label_list_ofs, cmd_label_cnt, scn_prop_list_ofs/cnt, scn_prop_name_index_list_ofs/cnt, scn_prop_name_list_ofs/cnt, scn_cmd_list_ofs/cnt, scn_cmd_name_index_list_ofs/cnt, scn_cmd_name_list_ofs/cnt, call_prop_name_index_list_ofs/cnt, call_prop_name_list_ofs/cnt, namae_list_ofs/cnt, read_flag_list_ofs/cnt`。
  **字符串**：索引表 = `str_index_list_ofs` 起 `str_cnt` 个 `(u32 offset, u32 len)`（**offset 单位=char**）；数据在 `str_list_ofs`；`str[i]` = UTF-16LE 逐 u16 `XOR (28807*i % 65536)`。
  **操作码流**（`scn_ofs..scn_ofs+scn_size`）：`u8 opcode [+操作数]`；`cd`：`0x00 NONE,0x01 NL(+i32 行号),0x02 PUSH(+i32 form,+i32 val),0x03 POP(+i32),0x04 COPY(+i32),0x05 PROPERTY,0x06 COPY_ELM,0x07 DEC_PROP(+2i32),0x08 ELM_POINT,0x09 ARG,0x10 GOTO(+i32),0x11/0x12,0x13 GOSUB(+i32+argformlist),0x14 GOSUBSTR,0x15 RETURN(+argformlist),0x16 EOF,0x20 ASSIGN(+3i32),0x21 OPERATE_1(+i32+u8),0x22 OPERATE_2(+2i32+u8),0x30 COMMAND,0x31 TEXT(+i32 read_flag),0x32 NAME,0x33/0x34 SEL_BLOCK`；`OPERATE_2` 运算符 u8：`0x01=+（字符串拼接）`、`0x10==`；`FM_STR=20`（`PUSH` 的 form）、`FM_INT=10`、`FM_LIST=-1`。
  **★ 文本提取规则（本作定案）**：字符串引用统一为 `02 <FM_STR:20> 00 00 00 <i32 id>`，**其后紧跟的 opcode 决定语义**：`0x31 TEXT`→文本框段（操作数=read_flag 索引）；`0x32 NAME`→说话人名（名札，**按规范不输出前缀**）；`0x22 OPERATE_2 且运算符==0x01`→**选择支按钮文本**；其它（`0x30 COMMAND` 参数、`0x02 PUSH` 串表参数）→图片/音效/内部量，丢弃。
  **★ 文本框归并（解 ruby）**：`read_flag_list[flag]` = 源码行号；**同一行号的多个 TEXT 属同一文本框**。ruby 的读音串走拼接参数（不算 TEXT），基字串才是 TEXT ⇒ 合并后得到完整行（例 `「ったく、` +〔ろく/碌〕+ `に仕事もできねえ…`）。比对标尺：`read_flag_cnt` 会同时给「名札」分配 flag（故 flag 号有跳号）。
  **陷阱**：① 系统场景（`_config/_menu/_saveload/_cg/_voice/_music/_system`…）字符串表**几乎没有可显示文本**（只有字体名/布局串/内部标记），菜单按钮标签是 **g00 贴图**，UI 文本**不可提取**；本作**无用語辞典/TIPS/教程**、无 `.dbs`。② 用「`0x22+0x01`」判选项时，系统场景里的布局串拼接会**误报** → 只在剧情场景采信。③ 全角空格 `\u3000` 是正文一部分，勿清。④ 顺序：场景内严格按 op 流顺序；场景间按 `sceneNNN` 数字序（分支无法线性化）。工具 `siglus_scene_extract.py`。
- **Unity + 自研 ADV `TKG`（薔薇に隠されしヴェリテ；Otomate/IF，PSV PCSG00708 定案）**：**Unity 5.3.5p5**。PSV 侧为 **NoNpDrm dump**（`app/PCSG00708/` 的 eboot/suprx/dll/psarc 全高熵；判据：`sce_sys/package/{head,body,work}.bin` 存在、`param.sfo` 明文而 `template.xml` 加密、`sce_pfs/pflist` 逐文件标 `sys/nenc/空`+SHA-256）。
  **解密**：`<psvdec>/bin/win64/psvpfsparser.exe -i <titleid目录> -o <out> -z <zRIF> -f cma.henkaku.xyz` → 成功标志 **`keystone: matched retail hmac`**；★ **`-i` 传的是「目录」且目录名须 = title id**；`cma.henkaku.xyz` 站点已废但 **zRIF 本地足够，不需要联网**；zRIF 由你自己的 dump 生成（psvdec 的 `games.json`）。之后 `archive.psarc` 变明文 `PSAR`（v1.4/zlib）→ `scripts/psarc_extract.py` → `Media/resources.assets`(+1.28G resS)。
  **★ 文件布局**：`resources.assets` = 全部 TextAsset（剧本），**无 TypeTree**（UnityPy 读不了它的 MonoBehaviour，只能原始字节扫）；**ScriptableObject / 场景 / UI 全在 `Media/StreamingAssets/` 的 AssetBundle**（`scene@2d` 165M / `scene@map` / `mch` / `ui` / `minimap`，**带 TypeTree，`obj.read()` 可直接读**）；`globalgamemanagers` 里 BuildSettings 只注册 1 个内置场景 `SceneBoot`，其余 `SceneManager.LoadSceneAsync("SceneXxx")` 全走 AssetBundle。AssetBundle 头为 `UnityWeb`。
  **TKG 指令流**（`Resources.Load<TextAsset>("EVT/TKG/"+id)` → `TkgData`）：记录 = `int16 cmd; int16 size(整条长度,含4B头); prm[]`；参数在 `cmd_off+4+prm`，`next()` ⇒ `cmd_off += size`。`TKGCMD`：0 EXIT / 1 LABEL / **0x10 MSG_PARAM** / 0x11 MSG_PARAM_RWD / 0x12 MSGWIN_CLR / 0x20–21 FADE / 0x30–32 WAIT 系 / 0x40–42 EFFECT / 0x60–63 JUMP 系 / **0x61 CHOICE_JUMP** / 0x70–75 FLG / 0x80–82 TC / 0x90–94 BG,CG / 0xA0 BGM / 0xA1 SE / 0xA2 NONE。
  **★ MSG_PARAM = 一次点击 = 一个文本框**：`i32×6(msgid,charid,dispType,stop,?,voiceFlag)` + 3×`[u16 len][UTF-8]`（voiceId / **話者名** / **正文**），每段后 `align2`（`prm += (cmd+prm)%2`）。正文替换：`%`→`リーゼ`、`&`→`フォルスター`（= `GMDEF.NAME[0..1]`）、**`$ @ #` 是着色标记须删**（`TalkWindow.setMessage` 里 `Regex.Replace("[\\$\\@\\#]","")`，粉/蓝/紫）、**`0x5C`(\`) 是框内软换行须合并**。
  **★ CHOICE_JUMP 选项文本不在脚本里**：`[u16 len]key + i16 n + i32×n`；选项 = ScriptableObject **`So選択肢.GetQ(key).a[i].txt`**（`Q{id,txt,idx,type,bt正解,a[]{txt,pnt[]}}`）。`key=="依頼"` 是任务受注确认（`SceneAdv選択Q`），画面只显示 `SoQuest.title` ⇒ 不产出独立行。
  **★ 文本来源分布（本作）**：EV###_###(676)+QT###_#(100)+MAP_*(8) = 50,413 文本框；`So選択肢` 218 选项；**`So辞書` = 用語辞典見出し語 170**；`SoBook` 35 / `SoItem` 124 / `SoQuest` 100 / `SoEvtDesc`(m_Name `EVT`) 786 / `SoChart`(有 `tblDef` 字段) 41；`ScnMiniMap.ScnMap.m_text` 41；`BhvMchHost.ones[].page[]{name,msg}` NPC 会話 1,872。**ScriptableObject 判别用字段签名**（`tbl[0]` 的属性集：`a+id`=選択肢 / `bg1st`=EvtDesc / `title+idx`=辞書 / `price買`=Item / `page+name`=Book / `tblDef`=Chart；`dscs`=Quest；`ones`=BhvMchHost）。
  **❗ 图片承载的文本（不可作文本提取）**：**用語辞典正文 = `Resources.Load<Texture>("SH_DICT/DIC{idx:000}_0/1")`**（每条 2 图，`Scn辞書.Scn内容`）；本(読み物)正文 = `BOOKxx_yy` 纹理；**教程 = `ND文章/文章N` RawImage 逐张淡入**（`ScnTutorial.ScnMain`）；BGM/CG 画廊标题 = Sprite(`tbl日/tbl仏`)；UI 按钮标签多为 sprite（`FRMBTN@…`）。⇒ 本作**辞典/教程正文需另走 OCR**。
  **★ 字体替换槽（务必渲染核实）**：字体 = `FNT00SP`（BMFont 图集 4096²，`m_chars` 6954 项；在 AssetBundle 里，`m_textures[0]` = 图集 Texture2D）。`m_chars[i]{m_id,m_description,m_x,m_y,m_width,m_height,m_page,m_xAdvance}`，**`m_x/m_y` 为左上原点 → 直接 `img.crop((x,y,x+w,y+h))`**。本作 **U+333B「㌻」的格子被画成粉色花蕾/心形装饰符**（45×65px 实心，只出现在 レオナール 台词，59 处）→ 按 `♥` 输出。★ 注意 `m_description` 写的是**原字符名**（'Char: [㌻]; Code: [13115]'），**不能据此判定字形**，必须渲染。
  **排除**：`EVXXX_XXX`（排版被打乱的模板，二进制混入正文）、`DRESS_TST_01`（测试档，与 `MAP_DRESS_00` 重复）——判据 = 在 `Assembly-CSharp` 中 grep 引用数 = 0。工具 `verite_extract.py`。
  **★ 反编译链路（本机无 .NET SDK 时）**：`dotnet --list-runtimes` 只有 runtime 8.x（无 SDK，`dotnet tool install` 不可用）→ 从 **NuGet 直下 `ilspycmd` nupkg**（`https://api.nuget.org/v3-flatcontainer/ilspycmd/<ver>/ilspycmd.<ver>.nupkg`，会被重定向到 `nuget.azure.cn`，可下），解压后 `dotnet <解压目录>/tools/net8.0/any/ilspycmd.dll <dll> -o <outdir>`。

## HuneX「Ogre」系 —— allscr / MZX0（カレイドイヴ, PSV PCSG00520, éstciel/HuneX 2015）
- **平台/源**：PSV NoNpDrm ZIP（NPDRM + PFS 加密）。解密：`psvpfsparser -i <PCSG00520目录> -o <out> -z <zRIF> -f cma.henkaku.xyz`
  - **zRIF 未必在 NPS**（本作 `PCSG00520` = MISSING）→ 由 `sce_sys/package/work.bin`（NoNpDrm 假许可，512B，
    `0x10` 起 content id）经 `<psvdec>/util/rif2zrif.py` 现场还原。
  - ⚠️ **`psvpfsparser` 需联网访问 F00D 服务 `cma.henkaku.xyz`**（派生 `drv_key`）。网络被拦 → 403 → 报
    `parsing files.db... expected value`（boost property_tree json 错）。**免沙箱即通**。
  - eboot → ELF：`util/self2elf.py -i eboot.bin -o out.bin -k <zzzrif 生成的 work.bin>`（需 pycryptodome）。
- **`allscr.mrg`（脚本）**：
  - `0x0000`：**脚本名表** N 条 × 32B（30 字符 CP932 名 + `\r\n`）。本作 N=171（`CH00_A`…`CH07_SP06`、`CHxx_EVCG_nnn`）。
  - `0x1800` 起：内嵌 `mrgd00`（N 成员，与名表同序）。
  - 其后：N 个脚本本体，各自从 hed 给出的 offset 开始。
- **`allscr.hed`**：n × **8B 通用条目** `HHHH` = ofs_low, ofs_high, size_sect, size_low（小端）：
  `offset = 0x800 * ((ofs_high & 0xF000) << 4 | ofs_low)`；
  `size = size_low==0 ? 0x800*size_sect : ((0x800*(size_sect-1) & 0xFFFF0000) | size_low)`。
- **`mrgd00` 容器**（`allpac` 与其成员皆用）：`6B 'mrgd00' + u16 count(count*u16 @+6)` +
  `count × 8B` descriptor `(sector_offset, offset, ssize_upper, size)`；
  `real_size = (ssize_upper-1)//0x20*0x10000 + size`；`real_offset = 8 + count*8 + sector_offset*0x800 + offset`。
- **`MZX0` 压缩**（HuneX 标准）：`4B 'MZX0' + u32 解压长度 + LZ77 数据块`；**字面字节 XOR 0xFF**。
  128B 环形缓冲 + 4 类命令(`flags&3`：0=RLE / 1=backref / 2=ringbuf / 3=literal)，每 0x1000 重置。
  `allpac.src` 是 ASCII **MERGE FILE HEDDER**，逐条列出 `data.w h'...,h'...,h'...,h'...  ;NNNN 原始路径`（生成 allpac.hed 的源）。
- **脚本语法**：解压后为 CP932 文本，指令以 `;` 分隔，`_CMD(args)` 形式。**各指令右闭括号数不等**
  （ZM=1；MSAD/SELR/LVSV/STBG/FADS=2；偶有注释 `　日本語)` 追加）→ 稳妥取法：定位首个 `(`，
  其后全部 `rstrip(')')`。例：`_ZM99c02(「……」);`、`_MSAD(^ん……そういやここって……」));`
- **文本指令**：`_ZM<id>(text)`=一次点击=一个文本框；`_MSAD(text)`=续接同框；`_SELR(n,text)`=选项；
  `_LVSV(章节标题)`；`_MTLK(1,名前)`=说话人名（规范：不输出）。其余 `_STBG/_STCH/_STCN/_STFC/_VPLY/_WTVT/...` 忽略。
- **正文控制码**：`^`=框内软换行（合并）；**`@n`=框内换页/再点一次 → 应拆为新行**；`@w<n>`/`@h<n>`=窗口演出参数（删）；
  `@e`=结束标记（删）；`＊Ａ`=主角姓、`＊Ｂ`=主角名（inline 替换）。注音 `<基,読>` 仅见于开发残留 `TEST_SCRIPT`。
- **事件CG回放脚本**（`CHxx_EVCG_nnn`）与正章**逐字重复**，提取时应排除（本作 100 本仅 6 条独有句子）。
- **资源命名**：`allpac.nam` 每条 32B（大写文件名 + `\0` pad + `\r\n`），**nam[i] ↔ hed[i]**；
  `.MZP`/`.MRG` 均为 mrgd00 容器。DICTIONARY.MRG = **字体图像图集**（非用語集）。
- **系统文本**：不在资源里，而在 **eboot→ELF** 的 CP932 串表（`~0xA1100`；另有 UTF-8 串）。用需全角假名的过滤提取。

---

## 自研「テキスト方式 ADV」（プチレーヴ × Future Tech Lab）— クランク・イン
- 容器：PSV NoNpDrm **`.pkg`**（非 zip）→ `pkg2zip.exe <pkg> <zRIF>`（v1.8，产出 `… [TITLEID] [JPN].zip`，内含 `app/<TITLEID>/`）
  → `7z x` → `psvpfsparser.exe -i psvsrc/app/<TITLEID> -o dec/<TITLEID> -z <zRIF> -f cma.henkaku.xyz`（**必须联网访问 F00D**；网络被拦时报
  `Error: <unspecified file>(1): expected value`，**不是** zRIF 错误）。路径须 ASCII。
- 文件树：`eboot.bin`、`cmp.psarc`（**唯一文本容器**）、`cmpi.psarc`（立绘 `.gxt`）、`10…99.psarc`（语音 `.at9`）、`bgm/se/movie`、`sce_sys/manual/*.png`。
- **`cmp.psarc`**（标准 PSARC，`PSAR`+zlib 分块；`psarc_extract.py` 通用）内含：
  - `data/*.txt`（**UTF-16LE，逗号分隔指令表**）：
    `bg.txt`(背景 616) / `bgm.txt`(23) / `se.txt`(118) / `change.txt`(转场演出 56) / `chara.txt`(立绘差分 1416：`组,中_制夏_通常,kg02_ab,1,167,179`)
    / `chart.txt`(204：流程圖，20 字段，字段 14=章组 `Prologue/Act.N/Re-Act.N/END.`、15=标题、17+=解説，`,`=换行) / `flag.txt`(BE 存储)
  - **`script/scriptN.txt`** × 1622 = **行式剧本，1 行 = 1 步**（UTF-16LE，纯 `\n` 分隔，无隐藏标记）
  - `script/scriptN_l.txt` × 102 = label 表：`<global_step>:<LABEL>`（如 `646:ALBUM`）
  - `data/scrlst.txt` = `<label>,<scriptN>,<global_start>,<global_end>`（1622 条，**global 步号 = 全游戏文本框累计序号** 0…39,656）
- **行语义（3 类）**：
  1. **指令行**：行文本 == 任一指令表登记的标签（bg/bgm/se/change/chara 列），或 == `scrlst` 的 label，或形如 `NNN:LABEL`；
  2. **话者名行**：`姓<U+3000>名`（含全角空格、无句读、≤15 字）或**职务/端役词**（`係員/審査員/店員/園長/司会者/お母さん/先生/彼女/男性/女性/記者/スタッフ/団員/女優/アナウンサー/牧師/アナウンス/審査委員長/運転手/ドライバー/警官/救急隊員/ディレクター/助監督/ニュースキャスター/撮影スタッフ/売り子/司書/秘書/店長/招待客/時雨…` 及 `…員/…客/…スタッフ/…生徒/…学生/…店員/…記者/…観客/…通行人/…友人/…部員/…園児/…女優/…教師/…教諭/…たち/…Ａ-Ｇ/…１-３`）；
  3. **文本行**：其余 ⇒ **游戏内显示文本**（对话「」/ 地の文 / 选项）。
- **表外指令（须补排除）**：`場面転換中遠`、`スチルス中`、`ガイダンス`（SE 提示）、`タイトル画面へ`、chara 变体 `制春_困り・動揺目閉じ_マント無`、裸数字 `30`、`悲哀bgmout(bgmlong)`；
  通用判据：**含 `_` 且无标点** / **裸数字** / 含 `スチル|場面転換|フェード|bgmout|bgmin` 词干且无标点 / 末字为「音」的短行（`歩いて行く足音` 等 SE 提示）。
- **文本内标记**：`\`（反斜杠）= **框内软换行** → 合并（其后 `　` 保留）；`[橘]`/`[文月]` = 主人公姓名占位符 → inline 为 `橘`/`文月`；`『』` = 短信/台本；`　`(U+3000) = 缩进（保留）。
- **选项**：紧邻其后的**分支 label 组**（`xxx_da/_db`、`xxx_00a/b/c`）。形态涵盖和文（`聞いてみる`）、「」括注（`「ジェットコースターが……」`）、英文（`ｉｎｊｕｒｙ`/`Ｕｎｄｅｒｇｒｏｕｎｄ`）、`はい/いいえ`。
- **校验法（重要）**：`scrlst` 的 `end−start` = 该 label 的**文本框数**（≈ 本器文本行数）；对**末尾仅 1 个 label 的"叶子脚本"**核对最干净。
  本作 1035 本叶子脚本中 **869 本(84%) 精确相等**，其余 ±1（选项块计 1 步 vs. 逐项输出）。选项组使其 +N，含分支子脚本的父 label 其 range 会**累加子脚本步数**。
- **⚠ 引擎遗留数据**：`eboot → ELF` 的 UTF-16LE 串表含**同发行商他作《SA7 -SILENTABILITYSEVEN-》(Future Tech Lab, 2016) 的完整用語辞典**
  （`キャラクター/キーワード/組織/スポット/秘密道具/能力`，主角 `城あやか`、`ＡＲＫ` vs `ｕｎｋｎｏｗｎ`）——**与宿主作品无关**，提取时须核对（术语在本作剧本命中 0 即可判定）。ELF 另有本作**キャスト/スタッフ クレジット**（真数据）。

---

## KiriKiri（吉里吉里）XP3 + DropWave「OriginalTag」— クリムゾン・ロワイヤル
（QuinRose, PC 2009／前作 クリムゾン・エンパイア 的アペンドディスク）

- **源/解包**：PC 发行常为 **RAR5 自解压或加密包**。本作 `[PC-JP]クリムゾン・ロワイヤル.rar`
  **数据段加密**（`7z l` 头明文可列名；不加 `-p` 会**挂起等密码**）→ `7z x -potoame <rar> <files>`。
  ★ **Git-Bash 把含日文的路径传给 7z 会乱码**（`ϵͳ�Ҳ���ָ����·����`）→ 先用 Python `os.link()` 建 ASCII 名硬链接再解。
  归档：`appscenario.xp3`(剧本) / `appdata.xp3`(数据) / `respatch.xp3`(共享资源) / `data.xp3`(KAG系统+前作csv) /
  `appimage|appmovie|appsound.xp3` / `patchfont.xp3`(字体 tft)。
- **XP3 容器（**本作是带 ASCII 标签的索引变体，非标准 index**）**：
  - 头：`58 50 33 0d 0a 20 <X> 1a 8b`(8B, 第 7 字节各档不同，**不可作校验**) + 3B 填充 + **u64 索引绝对偏移 @0x0B**。
  - 索引：`u8 flag(0x01)` + `u64` + `u64 解压长` + **zlib 流**（zlib 起点本作固定在偏移 +0x11，
    稳妥做法：在索引块前 48B 内扫 `0x78` 且次字节 ∈ {01,5e,9c,da}）。
  - 解压后索引 = 连续 **`File` 记录**：`tag[4]="File"` + `u64 size` + 载荷；载荷内是子块序列，
    每子块 = `tag[4]` + `u64 size` + 载荷：
    - `info`：`20B 头` + `u16 名字长` + **名字 UTF-16LE**（名在 **+0x16**）
    - `segm`：N × **28B** 段记录 `{u32 flags; u64 offset; u64 size; u64 size}`（offset 为文件绝对偏移，段顺序连续）
    - `adlr`：4B Adler-32
- **文件编码**：`.ks`（KAG 剧本）与 `.tjs` = **zlib 压缩 + UTF-16LE(BOM)**（DropWave 定制加载）；
  **`.csv` = GBK(cp936)，内容却是日文**（汉化工具链遗留；cp932 会在 0xEC 等处 `illegal multibyte sequence`）；
  `scenarioindex.txt`/`ro_memoindex_*.txt` = zlib + CP932（ASCII 内容）。
- **DropWave OriginalTag**（`system/originalTag/mc*Tag.ks`，署名 Kenichi Tanga/DropWave 2008）：
  - **`[message window=… name=… face=… voice=…]` … `[/message]` = 一屏 = 一次点击**
    （`[/message]` 内做 `[backlay] [pb]` 改ページ＝等待点击）。
  - `[br]` = `[l cond="mp['click']"] [r]`：**全库 13,395 处均无属性** ⇒ 框内软换行 → **合并**。
    `[clearmessage]`=清窗（无文本）；`[next file=…]`=跳下一本；`[select word=… file=…]`=选项按钮（word 即按钮文本）。
  - 窗口容量宏注释写「25文字×4行＝100文字」，**实测成品最长行 101 字**，反证"一屏一块"成立；
    脚本内除宏定义外**不存在** `[p]/[l]/[waitclick]`，无需中途拆页。
  - **★ 坑：正文里行首 `;` 是 KAG 注释**（本作 461 行，含 228 行被注释掉的 `;　·····` 转场点线）→
    必须整行丢弃，否则输出成 `;····;` 伪文本。
  - 主人公名：`PlayDataManager.tjs` 默认 `f[F_FIRST_NAME]='シエラ'` / `f[F_FAMILY_NAME]='ロザン'`；
    `[firstname]`/`[familyname]` 宏 = `[emb exp="f[…]"]`（可改名）。另前作模板残留裸占位符 `【主人公の名前】`
    （**引擎不替换**，本作仅 1 处，按规范置为 シエラ）。说话人名走 `name="name_XX.png"` **图片名札** → 按规范不加前缀。
- **剧本播放顺序**：`system/appendClass/ScenarioNavigator.tjs` 的 `ALL_SCENARIOPLAY` 分支
  用 `new CSVArray(SCENARIOINDEX)` 顺序取下一本 ⇒ **`appscenario.xp3>scenarioindex.txt` 即游戏自身定义的线性播放序**
  （本作 615 条）。★ 索引内有全角 `bryoｎ` 笔误（5 处）→ 比对时做 **NFKC 归一化**。
- **归档归属陷阱（务必分辨）**：本 RAR 为「アペンドディスク本体 + 共享资源」的不完整副本（**无 exe、无前作 `scenario.xp3`**）。
  - `appscenario.xp3`(627 .ks) = **本作剧本**；`appdata.xp3`(csv) = **本作数据**（questdata 含 115–124＝`qeventdata` 引用的本作事件；
    shortscenariodata 有 `自室[RO強制OP2]`/`闘技場[ハルキア]`）。
  - **`data.xp3` 的 `.csv` = 前作《クリムゾン・エンパイア》**（`模擬戦闘[レクチャー]`/`御前試合`/quest 1–92）→ **排除**
    （同《クランク・イン》SA7 遗留之例）。
  - `respatch.xp3` = **两作共享资源**（`urawaza_check_1st.ks` 自注「エンパイアとロワイヤル共に使う」；
    `basictalkdata` 引用其 `basic_bryon2_repeat15.ks`）→ 收入为"追加区"。
  - `data.xp3>system/about.ks` 含**中文汉化组信息**（☆翼の梦☆推倒美男汉化组）→ 非原作文本，排除。
- **辞典/教程**：`system/**` 检索 `用語/辞典/図鑑/事典/豆知識` = **0**（无用語辞典）；回想/CG 图鉴条目是**图片**，
  `ro_memoindex_*.txt` 只是 `剧本名↔缩略图名` 映射。前作战斗教程在本作**已删除**，本作教程 =
  `messagedata.csv` 的道具屋/教会/フィールド/自室说明消息（106 条）。结局 `ro_endroll_{a,b,c}.ks` 只播 **`.mpg`**（演职员表在视频内）。
  `system/grammarGuide/*.ks` 是**开发者向 KAG 语法教程**，非玩家内容。
- 工具：`scripts/crimson_royale_extract.py`（内嵌 XP3 读取器 + 剧本/CSV 提取，纯 Python 可复跑）。
- 外部核对：vndb **c16530 シエラ=ロザン**（前作与ロワイヤル共用主角）；角色名与 getchu 官方介绍全吻合。
  本作 vndb **无词条**（PSV 移植因 QuinRose 倒闭中止）。


## Takuyo gss 引擎 —— LSDARC V.100 + `SCR 2.00`（ひめひび -Princess Days-, PSV PCSG01092）
- **平台/源**：PSV。源 zip 为 **pkg2zip 产物（PFS 未解，DATA/eboot 全高熵）**。
  解密：`work.bin`(512B) 经 `<psvdec>/rif2zrif.py` → zRIF
  （zRIF 由你自己的 dump 生成）
  → `psvpfsparser.exe -i PCSG01092 -o dec -z <zRIF> -f cma.henkaku.xyz`（**须联网 F00D**，成功标志 `keystone: matched retail hmac`）。
  eboot(SELF) 另：`util/self2elf.py -i eboot.bin -o eboot.elf -k work.bin`（需 pycryptodome → 建 venv 装 `pycryptodome six`）。
- **归档 `LSDARC V.100`**（`XXXDATA.BIN` 索引 + `XXXDATA.ARC` 数据）：
  `magic[12]="LSDARC V.100"`（0x4C53444152432056…）+ `u32 count` + count×
  `{u32 isPacked, u32 offset, u32 unpackedSize, u32 size, name\0}`（name=CP932，无固定对齐）。
  条目 offset 为**链式累加**（off[i+1]=off[i]+size[i]）可自校验。
  打包项（isPacked=1）= `"LSD\x1A" + u8 enc_method(B/W/S) + u8 pack_method(D/R/H/W) + u32 unpacked_size` + 自定义 LZ/LZSS；
  本作 **SCRDATA 531 条全部 isPacked=0**，未用到解包。SYSDATA=`VAGp`(PS2 VAG 音频)；FONTDATA 6 条、BMPDATA 1498 条为打包。
- **脚本 `SCR 2.00`**（`"SCR 2.00"` + u32 A + u32 B，A/B 与提取无关）：
  ```
  instruction:
    u16 opcode
    u8  size       # 整条指令字节长（含 3 字节头），自定界关键
    u16 id         # 源码行号/语句号（非地址，有跳跃）
    operand*:  <u8 type> <data>
       type 0x01 / 0x05 -> 4B（小端）
       type 0x02 / 0x04 / 0x06 -> 2B（0x04 用在 `0x22/0x23` 的 u16）
       type 0x03 -> NUL 结尾 CP932 字符串
  ```
  ★ **用 size 逐条前进，531/531 脚本（含全部无文本脚本）恰好铺满、零失步** —— 定表可靠。
- **操作码语义（本作实测）**：
  | op | 语义 | 备注 |
  |---|---|---|
  | `0x5a` | **消息框正文 = 一次点击一行** | 29,905 次，1 串操作数 |
  | `0xfc` | **带 `%s` 的消息** | 串后跟替换源操作数：`(6,slot)`/`(3,str)`，`(1,0xffffffff)` 为终止；`%s` 依次 ← 各 slot |
  | `0xf0` | **标题卡** | 章节/场景标题、地图选择状态标题「朝　マップ選択中」 |
  | `0x5c` | **选项** | `(u32 个数, "显示文本,FLAG", "…,FLAG2", …)`；显示文本 = 最后一个 ASCII 逗号之前 |
  | `0xfd` | 槽位/UI 赋值 | `(6,slot),(3,str)`；`0x2402`=名牌文本、`0x04e4`=背景图、`0x0224`=名字部件；**提取时剔** |
  | `0x3c`/`0x3d` | SE `/` BGM 文件名 | 剔 |
  | `0x3b`/`0x107` | 图片加载 `/ 串拼接 | 剔 |
  | `0x1e`/`0x1d` | 调脚本(file,label) `/ 尾调用 | 用于遍历调用图 |
  | `0x1a` | 标签定义 | |
  | `0x18` | 条件（flag）→ 紧跟 `0x1a label` 跳转 | 分支 |
  | `0x25`,`0x21`-`0x28`,`0x30`,`0x37`… | 变量/flag/算术/地图 | 非文本 |
- **控件与占位符（消息串内）**：字面 `\n`（0x5C 0x6E）= 框内换行 → **合并**；`\c`（0x5C 0x63）= 控制码 → 删；
  `@y`/`@w` = 演出/等待码 → 删；`%s` → 用操作数槽位替换。主人公名 slot：`0x0c02`=恋、`0x1802`=相崎
  （仅调试菜单 QUESTION 赋值，故事内取默认；合称=相崎　恋）。
- **顺序（点击序）**：入口 **`PRG_MAIN_0630.START`**（AUTOEXEC 的 START 分支）。
  线性链 `PRG_MAIN_0630 → 0701 → … → 0711 → 0712{HY,MN,SR} → … → 0717{…} →`
  6 条角色线 `PRG_MAIN_{HIK,MAS,NAO,RIN,SIN,YAM}`。每个 `PRG_MAIN_07xx` 依序 `0x1e` 调
  `COM07_xx_yy` 场景，末尾 `0x1d` 尾调用次日；分支场景（`_00`,`_01`…）在同一 PRG_MAIN 内按调用点并入。
  顺序 = 自 `PRG_MAIN_0630` 按 `0x1e/0x1d` 调用图 **DFS 前序、脚本去重**；末尾追加 `OMAKE_DRAMA`（おまけ）。
- **排除**：`CERO`（**CERO 分级用合辑**：944 条独有消息 942 条与主线重复）、`DEBUG_*`（9 个开发菜单）、
  `QUESTION`（起動条件调试菜单，含主人公名默认）、`SELECT`/`SELECT2`（选项 UI，无文本）、
  0 引用分支 `HY07_14_04_02..07`/`COM07_03_10_07`（仅 DEBUG 可达）。
- **辞典/教程**：本作**无用語辞典、无教程文本**；全脚本检索关键词仅命中台词；UI/教程为图片（BMPDATA）。
- **工具**：`scripts/himehibi_lsdarc.py`（LSDARC 读取）+ `himehibi_disasm.py`（SCR2.00 反汇编，含 size 表）
  + `himehibi_crawl.py`（调用图）+ `himehibi_extract.py`（文本提取）。
