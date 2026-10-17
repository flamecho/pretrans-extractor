# A1 · 解码层总纲（①〜⑮ 核心判据）

**解码层**：① 主循环**字符宽度感知**（否则静默丢 20% 文本）② 替换槽不能信 cp932；**PUA 槽＝大号标点/记号**、**单字节 kana 码位亦可改写**⇒以 **ELF code→Unicode 表**为准（A21）；**码表可分区错位**⇒低区用已知明文核（A22）
③ 变量表先锁人名映射 ④ eboot 串表有他作遗留串，整体排除 ⑤ **PSV 两层解密**：`pkg2zip` 只解容器，再跑 `psvpfsparser` 解 PFS（**前台联网**；`zRIF`≠可用看 signature）；⚠ `files.db…`＝取密钥**被拦**（非损坏）（01/`03-basics.md`）
⑥ **内联插入可能是「定长表引用」**：表基址靠「空槽字面」反推（勿假定 base=0）；逐文件验字节序、偏移须 **NUL 起点**、**键集合双向零差**自校验（A23）
⑦ `WSC` **全字节 `rotl_8(c,6)`** —— 易误判明文（A14）
⑧ 选项指令 `07 <名>`/`06 <5B>` **须按表分派**，勿硬跳 4B（A14）
⑨ **脚本 magic 之前的前缀区块可能另含正文** —— 别只扫代码段（A15）
⑩ **归档/多 zip 串联 512B 对齐**；**归档块单位非常量**（`max(offset)×UNIT≈大小`）→A16；**CRI CPK 两处静默错**→A19；**PSARC `size==0` 语义不唯一**⇒取「offset 命中最多」解→A20（`03-archive.md`）
　★**子文件「遍历终点」别信 FAT / 导出表**——记录流会**跨文件边界**：`sizeBytes` 会截尾 ⇒ 先用**簇对齐**，仍不够 ⇒ 终点放宽到 **「下一子文件起点 + 前缀区大小」**（STCM2L/CRI·UNI2 实证，丢 16%；267 文件里 266 个跨界）（`03-archive-delta.md`）
⑪ **同引擎 opcode 可能逐文件平移**（Δ 常为常数倍、builtin 不动）（A17）⇒「含日文串 opcode **平均长度**最大者」定 `text_op`；**或不平移（B/D/E/F 型）**，先判有无 Δ
⑫ **同族指令头布局随平台变**（STCM2L PS2/Switch vs PSV 不同）（A18）。★**同一平台也可能连「脚本版本号」本身都换**——Takuyo gss 同为 NS 版：`神さまと恋ゴコロ`＝`SCR 3.00`＋LSDARC 内层打包，`カエル畑DEつかまえて☆彡`＝**`SCR 2.00`＋未打包** ⇒ **一律读文件头的版本串定格式，别按平台或「同厂前作」推定**（2026-10-15）。
  　★**且节点「尾部签名相同、头长不同」的情况极常见**（STCM2L ニルアド：头长＝`28+12k`，`k=3` 才是选项）⇒ **扫描必须 k 泛化（k=1..6）**，否则**静默丢掉 k≥3 的整类文本**（实证选项 525／569 条全失）（2026-10-16）。
⑬ **自建码表**：用一条已知明文锚定基址；先查参考实现是否**同变体**（A9）
⑭ **同引擎跨作 opcode 语义可变** ⇒ 换作必回查；**eboot→ELF＝元数据金矿**（名表/总表/**码表**）（A10/A11/A21）
⑮ ★**自建字符集（高码区读不通）⇒ 找「自带字形图集」**（判据见 `03-selffont.md`）。★**同族续作槽序逐作独立、字体可重绘、高码槽或为语义标记/绘文字**（按文脉改写）；**36px 辨字必错⇒台词仲裁**；★★**先自检「槽序==cp932 序」是否严格单调**：成立⇒当**候选窗口压缩器**（未定槽夹在相邻已知槽间，实例 57 槽秒级定完／零枚举零 OCR）、不成立⇒仅纠错提示（`03-selffont.md`）

⑯ ★**Unity IL2CPP 的 bundle 无 typetree** ⇒ `obj.read()` **段错误**（常连 stdout 一起吞）；用
`TypeTreeGenerator(UnityPy) + load_il2cpp(exefs/main, global-metadata.dat)` 生成再 `read_typetree()`；
更新版 main/metadata 可能让 LibCpp2IL 挂 ⇒ 退回本体版本读更新 bundle（`02-unity.md`）。
⑰ ★**Switch XCI 内可同捆「全量替换型」更新**（同 Title ID 两个 Program NCA；带 Rights ID ＋ `Patch RomFS`(BKTR)）
⇒ **先比 RomFS 文件表**；BKTR 用 `--titlekey=<tik[0x180:0x190]>` ＋ `--baseromfs=<本体 section1>` 可解（`02-unity.md`）。
  　★**且 NCA 可整段压缩**（fs header `CompressionInfo`@+0x178 非零 ⇒ section 数据是 **LZ4 桶树**；表偏移相对 **IVFC level5 起点**，
  physical 按 0x10 对齐 ⇒ **须按 comp_size 截取**）：**四款现成工具 hactool(2020)/hactool1.4.0/nstool1.9.2/Kuriimu2 全不支持**，
  **别在工具上耗时间，直接自写**（千銃士R `scripts/senjyushi_extract.py`）（`01-switch-nca.md` §5.2）。
⑱ ★**容器内层可能再套自定义压缩**（别以为同引擎＝同链路）：Takuyo gss 的 `LSDARC V.100`，
PSV=`SCR 2.00` 未打包，**NS=`SCR 3.00`＋`LSD\x1a` 打包**（pack `H`=Huffman/`D`=16bit增量/`R`=RLE）。
★**enc 层是「就地前向差分」——「前一值」取已解密值**（用原始前值会「前 2 字节对、其余全崩」的假象）；
★**验证锚＝解出必须 `"SCR 3.00"` 开头**；参考实现 `GalgameReverse/src/gss/gss_arc.cs`（GARbro 同名文件 `UnpackD/H/W` 全空）（01）
⑲ ★**条目尾部可能有「哈希/校验/对齐」字节 ⇒ 解析前按尾部签名切掉**：症状＝末个文本 op 的 run 掺入随机字节
  → 凭空多出**含 `PUA`** 的文本/选项（Vamwolf：147 个假选项）。★**PUA＝「二进制被误读成文本」的强信号**（02）。
⑳ ★**脚本前可能有一段「样式/字符定义表」区，且内含真命令码**（`FFFF`/宏 `FFE6`…）⇒ 解析须**从首个正文类命令起**
  （如名牌 `FFF0`），否则插错名/产假选项（02）。

**提取层（成行/断框/命名/选项）⇒ 已移入 `pitfalls/B1-lines.md`**。
　★ 另有两条「无标签序列化」专项：**A27**（`04-typing.md`：**`[i32 X][u32 L][L 字节]` 里 `-X-1` 恒等于字节数 ⇒ X 是长度、不是字段号**，
　　⚠ 值域恰 255 个/步长 3 极像字段号 ⇒ **先拿长度自证再判型**）＋ **B31**（`04-lines-names.md`：名札与正文同编码时，
　　**「后随同类串」＝名札位**；须做「长串是否被误当名札」的证伪）。

㉘ ★**Unity(IL2CPP) 系：可改名主角的「默认名」常直接写在 AssetBundle 内的旁车表里** —— 先去找
  `Data/StreamingAssets/<ab>/data`（或 `resources.assets`）里的 **`DataGlobalValue`／`DataSystemFlag` 一类 MonoBehaviour**，
  读 `ADV・主人公デフォルトネーム`（实例：神凪ノ杜＝`ADV・主人公苗字=木南`＋`ADV・主人公デフォルトネーム=瑞希`），
  **不必反推 eboot／IL2CPP 代码**。同表常附 `名前入力` 提示文（`主人公の名前は[n]木南　<pf>で…`）⇒ **可反证宏的位置与语义**。
㉙ ★**Unity 自研 ADV 的又一变体：AssetBundle（如 `ab_switch/script`）里装「纯文本 @命令脚本」**——
  文法 `;注释` ／ `@命令 [arg=val]` ／ `*标签|`；**`@talk … @hitret` ＝ 一个文本框**（框内行**直接拼接**、一次点击＝一行）、
  **`@choice text=… file=…` ＝ 选项**。**完全不是字节码 ⇒ 先看脚本是否直接可读，别默认上 VM/码表**。
  ⚠ 解析须容忍源内笔误：闭合命令变体（`@hitre`）＋**漏写闭合**（框内遇任何 `@` 命令即**先闭合当前框**再执行该命令）。
  同 bundle 里其它 TextAsset 可能是**立绘部件 XML**（`OV001_body_a.png` 坐标表，非文本）；UI/画廊/章节表另存于 `data` bundle ⇒ 判「是否上屏」再定弃取。

**★ XCI / NCA 判型 ＋ 纯文本脚本取值（⑲⑳㉑）⇒ 已移入 `02-unity.md`**（hfs0_header_hash / NCA 头加密 / 引号取到首个未转义 `"`）。
**★ 解码层の后期条目 ㉒〜㉗（未圧縮判定の罠／opcode 跨作品平移／明文 SQLite 剧本库／.NET `#US` 堆の用語辞典／LZSS 変種の同定）
⇒ 已移入 `pitfalls/A2-decode-late.md`**。
**★ 解码层＝提取层の后期条目 ㉝〜㉟（`SCR 1.10≡2.00` 指令编码同构＋`LSDARC` enc/pack 逐作独立／**扉文标题卡可由文本槽拼接生成**／选项行首数值前缀＝写入值）
⇒ 已移入 `pitfalls/B4-late-1.md`**（2026-10-16；`pitfalls/B3-lines-cont.md`/`pitfalls/A2-decode-late.md` 亦达 10 KB 故另起续册）。

**★ 解码/提取层 后期条目 ㊶〜㊽（PSP STCM2L「CPK 布局」的**收尾三元组 `[0][cmd][flag]` 判型**／**选项组锚在 `select` 上向前收**／**公共前导块用资源名整体滤除**／**样式标签先剥再 strip**／**同族跨作「压缩化」／命令集／名字宏逐作变**／★**字符串记录两大陷阱：命令白名单 + 串可在参数列表末尾（非 +4）**）
⇒ 已移入 `pitfalls/B5-late-2.md`**（2026-10-16，`pitfalls/B4-late-1.md` 超 10 KB 故再拆）。

**★ 源为 `.chd`（MAME **CHD v5**，压缩器 `zstd`）⇒ `01-image-chd.md`**（2026-10-17）：无 chdman 时自写解码，
判据链＝`MComprHD`＋**头部全大端**／`hunkbytes` 可能仅 2048／map＝Huffman(**numcodes=16,maxbits=8**,码长位宽 4)
＋位流(`lengthbits/selfbits`)／Node 22.15+ `zlib.zstdDecompressSync` **须自算帧长逐帧解**（`createZstdDecompress` 不接续多帧）；
**收尾必验「整盘 SHA1 == 头部 `rawsha1`」**。
