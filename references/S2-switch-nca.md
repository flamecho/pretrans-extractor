# Switch NCA（结构 + 卡点排查）

> 结构、魔数、解包链路与「卡住了怎么办」合为一册：**§1 更新档/压缩 NCA 先解**（最常被忽略），§2〜§7 是各类卡点的判据，报错时按节名找。

> 总览看 `pitfalls/A-decode.md`；
> 本文件在「有官方补丁要合并」或「载体系 Switch NCA」这一阶段读。NCA 判型/纯文本脚本取值见 `S4-unity.md`。

## 1. 官方修正补丁先解（★常被忽略）

- 同捆的 `Patch.rar` / `update.exe` / `patch.xp3` **先解开**。官方补丁常写「**一部の誤字脱字の修正**」。
- 内多为**与本体同方式的脚本文件** → 同一套解密即可解出 → 与本体 **diff 就拿到「作者认定的正确文本」**。
- 蝶の毒 v1.01 实证修正 6 处显示文：
  `斯波さま→斯波さん` / `噛察→観察` / 助詞脱落 / `*G用→雑用` / `済んだ→澄んだ` / `非常→非情`。
- **关键旁证**：`*G用→雑用` 说明**配布数据自身就带着化け文字** —— 不是解密方的错，官方只能靠补丁修。
  ⇒ 见到孤立化け时**两边都查**（自己的解码 + 原始数据缺陷）。
- 补丁**只覆盖部分文件**；未覆盖文件里的同类缺陷要自己判。
  （蝶の毒 `05_shiba_1.ks` 的闭引号 `」` 脱落＝官方漏修：XOR 保长度 ⇒ 物理上无该字节 ⇒ 数据缺陷，据「开 `「` 必合 `」`」补回。）

### Switch 更新＝NCA「**BKTR 增量段**」—— **已解决**（2026-10-12 定案，魔女と亡霊のヴォロンテ）

1. `prod.keys` 里 17B 的 `mariko_master_kek_source_*` 先滤（否则 hactool 报 key 长度错）；
2. 带 Rights ID 的更新 NCA：ticket `tik[0x180:0x190]` 的**加密** titlekey 传 `--titlekey=<16B hex>`
   （hactool 会打印 `Titlekey (Decrypted) (From CLI)`；`key area @0x300` 全 0 ⇒ `Encryption Type: Titlekey crypto`）；
3. **先导出本体 RomFS 当 baseroot**：`-t nca --section1=base_sec1.romfs <本体NCA>`；
4. 更新 ExeFS：`--exefsdir=`；更新 RomFS：`--baseromfs=base_sec1.romfs --romfsdir=`
   ⇒ **成功判据＝能列出/解出 `rom:\…` 文件**（旧 hactool(2020) 也能成；`--listromfs` 先看清单）。

★ **XCI 内可同捆「全量替换型」更新**：secure 分区里**同一 Title ID 两个 Program NCA**（一个无 Rights ID＝本体，
一个带 Rights ID＋`Patch RomFS`(BKTR)＝更新）。**先比两者 RomFS 文件表**（文件名 hash 不同即被改）；
Unity 游戏更新常替换 `global-metadata.dat`/`resources.assets`/全部 asset bundle ⇒ **不比对就会用旧数据**。

### ★ **全量压缩 NCA**（≠ 上面的「增量 BKTR」；2026-10-16 千銃士R）

同一字串 `BKTR` **两种用途**，**先看判据再谈工具**：

- **判据**：解密的段 FS 头 `0x400+secno*0x200` 的 **`CompressionInfo`(@+0x178) 非零**
  ⇒ section 数据**整段是 LZ4 分块压缩**（`SparseInfo`@+0x148 亦可能非零）。
- ⚠ **四款现成工具全部不支持**（2026-10-16 实测）：hactool(2020)／hactool 1.4.0／nstool 1.9.2／Kuriimu2 均失败
  （`Failed to read RomFS directory cache!` / `Hash layer 3 failed` / 报 corrupt）⇒ **别在工具上耗时间，直接自写**
  （范例 `scripts/senjyushi_extract.py`：`NcaReader` + `parse_buckets` + `Virt` + `parse_romfs`）。
- **表偏移相对「IVFC level5（数据层）起点」**，不是 section 起点（自洽判据：`offset+size == level5 尺寸`）。
- 桶树：`@0x00 u32 pad; @0x04 u32 bucket_count; @0x08 u64 total; @0x10 bucket_count×u64 base`，
  桶自 **`@0x4000`** 起每桶 0x4000：`{u32 idx,u32 entry_count,u64 end}` + `entry_count×0x18` 条目。
- **条目 = `{u64 virtual, u64 physical(相对 level5), u32 comp_type, u32 comp_size}`**；
  `comp_type 0=raw / 3=LZ4(块格式)`；块 0x10000（首块 0x200 raw）。
- ⚠★ **physical 按 0x10 对齐 ⇒ 必须按 `comp_size` 精确截取**（多截到填充字节即 LZ4 corrupt —— 本作最大一坑）。
- 实例：136 桶 × 682 条 = 92,228 条，解压总长 13,128,882,432 B = RomFS 镜像大小 → 9,936 文件。
- **同作 NCA 头 XTS 的 tweak 是「字节反序」**（非标准）：`T0 = AES_enc(k2, 扇区号 大端)`，
  扇区内每 16B 块 `T ← rev(α_be(rev(T)))`（`rev` = 128 位字节反序）。已落入 `scripts/switch_nca.py`，与 hactool 逐字节一致。
- ⚠ **titlekey 走 `master_key_<rev>` + `titlekek_source` 现推**：keyset 若缺该 source，hactool 会**静默用错 key**
  （症状＝段解出乱码、RomFS 表读不出），须自行派生后核对。

## 2. ★ Titlekey crypto 的内容密钥＝**titlekey 本身**（Starry☆Sky ~Spring Memories~, 2026-10-19）

- 症状：段表/IVFC/`superblock hash` 全部解得出（头 XTS 正确），但**段数据全是乱码**，四个 key_area slot 都不对。
- 正解：**Titlekey crypto 的 NCA，内容密钥直接用「解密后的 titlekey」**，不是 `key_area[i]` 再用 `key_area_key_application_*` 解一次。
  `titlekey = AES_ECB_dec(titlekek[NCA Master Key Rev], tik[0x180:0x190])`；
  ⚠ **索引是 NCA 头 0x21C 的 Master Key Revision（本例 0x14），不是 ticket 0x285（0x15＝+1）**。
  用 `hactool --titlekey=<tik[0x180:0x190]>` 打印的 `Titlekey (Decrypted)` 逐字节核对最省事。
- 段 CTR：高位 8B 在 **fs header `@0x400+secno*0x200+0x141`**（不是 0x140），低位 8B ＝ **绝对文件偏移/16 大端**。
  自检锚点：ExeFS 段首 `PFS0`、RomFS 段 IVFC level5 首 `50 00 00 00 …`（RomFS 头 `header_size=0x50`）。
- **RomFS 元数据条目名字「内联 + 4 字节对齐」**：`advance = 0x18(dir)/0x20(file) + align4(namelen)`。
  不对齐会从第 4 个目录开始跑飞（症状：只解出 5 个目录/1 个文件，名字里混进 `MetadataResources…`）。
- 大档（3 GB NCA + 2.9 GB RomFS）在只剩 6 GB 的盘上：**用「NSP 内就地 seek 读 + 按需解密」**，
  别整档拷贝；只做 info 校验时用 `hactool -i` 读小 NCA 即可验 keyset。

## 3. ★ NSO0 段解包：**头字段序别凭印象**（2026-10-19 うたプリ All Star）

```
0x00 "NSO0" | 0x04 ver | 0x08 reserved | 0x0C flags
0x10 text.file / 0x14 text.mem / 0x18 text.size / 0x1C ModuleNameOffset(=0x100)
0x20 ro.file   / 0x24 ro.mem   / 0x28 ro.size   / 0x2C ModuleNameSize
0x30 data.file / 0x34 data.mem / 0x38 data.size / 0x3C BssSize
0x60 text.comp / 0x64 ro.comp  / 0x68 data.comp
flags bit0/1/2 = text/ro/data 用 **LZ4 block** 压缩（bit3-5=hash 校验）
```
- **判据（解对了的样子）**：text 段首出现 ARM64 指令且 `+0x0C` 处有 `MOD0`；rodata 解出后能扫到成批 ASCII／UTF-8 串。
- **症状（读错了的样子）**：LZ4 在**第一个 token** 就 `offset > 已输出长度`（`start<0`）⇒ 别怀疑数据、先回头核头字段。
  本作曾把 `0x18` 当「file offset」、`0x20` 当「压缩长度」，结果 `main` 与 4 个 `subsdk` **全部**解压失败。
- 一次解全：`scripts/nso_x.py`（按 `0x0C` flags 逐段 LZ4，按 mem offset 平铺，缺页补 0）。

## 4. ★ 剧本藏在 exe 里时的通用取法：**ADRP+ADD 定位 → 相邻函数＝解压器**

适用：romfs 里只见媒体（cpk/xtx/hca）＋一个可疑 `.bin`，且该 `.bin` 里能读到**成片但被切碎**的 cp932。
1. 解 exefs（NSO→平铺）；`Grep` 资源名（如 `sn.bin`）与 `rom:/…` 路径串 → 确认**引擎只开这几个包**。
2. 手写 ADRP 解码扫 text 段：`(w & 0x9F000000)==0x90000000`，`imm=immhi:immlo` 符号扩展后 `<<12`，
   `target=(pc & ~0xFFF)+imm`；命中字符串所在页后，在其后 4 条内找 `ADD Xd,Xn,#lo12`（`(w&0xFF800000)==0x91000000`）。
3. 引用点前一条 `bl` 通常是 **loader**（本作 `0x2F50`：拼 `rom:/`+名 → `criFsLoader`），
   **紧跟其后那次 `bl` 就是「取到数据后的处理函数」**——本作 `0x4FD80` 即 LZSS 解压器。
4. 抄指令不要猜：`tbnz w9,#0` 定 literal 极性、`bfi w10,w13,#8,#4` 定 12-bit 拼法、
   `add w12,w12,#2` 要和下一句 `add w10,w10,#1` 合起来算 → **实际长度 = 低半字节 + 3**（单独读 `#2` 会差 1，输出全零）。
5. 首 4 B `ldrsw` 就是**解压尺寸**；把该值当参数喂解码器，跑完长度对上即闭包。

## 5. ★ 旧 hactool 读不了 **Key Generation ≥ 0x0D** 的 NCA（うたプリ All Star After Secret, 2026-10-19）

- 症状：`hactool -t nsp -i` 直接报 **`Invalid NCA header! Are keys correct?`**（连 `NCA3` 魔数都读不出），
  `prod.keys` / `keys.txt` / `merged.keys` 全一样 —— **不是 keyset 缺 header_key，是工具太旧**（2020 版只认到 keygen 0x0C 左右）。
- 正解：`nstool 1.9.2 -k merged.keys -t nca --tik <tik>`，头能读出 `Key Generation: 14`；
  但若再报 **`NCA Partition 0/1 not readable (AES-CTR Key was not determined)`** ⇒ keyset 缺 `key_area_key_application_0e`，
  改传 **`--titlekey <tik[0x180:0x190] 的 16B hex>`**（加密 titlekey，nstool 用 `titlekek_0e` 解）即可；随后 `--part0/--part1 <dir>` 落地。
- ⚠ **Git-Bash 下 `nstool -x /` 会被路径转换毁掉**（`Failed to extract virtual path: "C:/Program Files/…PortableGit"`）
  ⇒ 解 `.nsp` 别用 nstool，直接按 PFS0 头拆（`scripts/nsp_split.py`）；必须用 nstool 时加 `MSYS2_ARG_CONV_EXCL="*"` 且**给 Windows 绝对路径**。
- 交叉验证：`nstool --fstree` 能列出 RomFS 树（6 个 CPK）＝ 段密钥已正确。

## 6. ★ 解包被卡住时（失败信息的真伪判别 · 统一入口）

见 **`S2-switch-nca.md`**：`prod.keys does not exist`／`partition is corrupt`／`Invalid NCA header`／
`RomFS directory cache`／NSP 成员全零 等 8 类失败信息，分别「不是」什么、「是」什么、该走哪条路线；
含统一入口 `scripts/ns_open.py`（判类型 → 选路线 → 失败自动回退，并打印决策链）。

---

## 7. ★★ NS 解包「路线决策表」＋统一入口（2026-10-26 复盘：为什么每次都绕弯）

**结论：不是某个工具坏了，是「4 类场景 × 5 份 keys × 27 个每作脚本」没有统一入口。**
hactool 2020-06-01 版的能力边界是硬的（只认到 keygen 0x0C 左右），新作必然失败；失败信息又长得像密钥错。

### 失败信息 → 真实原因 → 正确路线

| 你看到的 | 不是 | 是 | 走哪条 |
|---|---|---|---|
| `[WARN] prod.keys does not exist` / `Failed to load "prod.keys"` | 缺 keyset | hactool/nstool **总在当前目录**找 `prod.keys`，即使已 `-k` 指定别的 | `cd _sw` 或让工具把 `cwd=_sw` |
| `Failed to match key "bis_key_00"` ×N | 密钥错 | keyset 里塞了本机不需要的键（只是 WARN） | 忽略；别被刷屏骗 |
| `XCI partition is corrupt` | 数据坏 | **hfs0_header_hash 校验**失败（需 `xci_header_key`），布局没坏 | `scripts/xci_hfs0.py --extract`（手工切 secure） |
| `Invalid NCA header! Are keys correct?`（连 `NCA3` 都读不出） | keyset 缺 header_key | **hactool 太旧**（keygen ≥ 0x0D） | `nstool 1.9.2 -t nca --tik <tik>` / `scripts/switch_nca.py` |
| `NCA Partition 0/1 not readable (AES-CTR Key was not determined)` | header 错 | keyset 缺 `key_area_key_application_0e` | 传 **`--titlekey <tik[0x180:0x190] 16B hex>`** |
| `Failed to read RomFS directory cache` / `Hash layer 3 failed` | 密钥错 | **patch NCA（crypt_type=4, BKTR）或压缩 NCA** | `scripts/bktr_romfs.py --changed` / nsz 先解压 |
| NSP 大成员解出来是全零 | 解密失败 | hactool `--pfs0dir` 对 >1.7 GB 成员的 bug | `scripts/nsp_split.py`（逐块直拷） |
| `Failed to extract virtual path: "C:/Program Files/…PortableGit"` | 路径不存在 | **Git-Bash 把 `-x /` 的 `/` 转成 Windows 根** | `MSYS2_ARG_CONV_EXCL="*"` + Windows 绝对路径，或干脆别用 nstool 解 NSP |

### 统一入口（首选，别再一作一个脚本）

```bash
python scripts/ns_open.py <xci|nsp|nca>            # 判类型 + 列分区/NCA（秒级）
python scripts/ns_open.py <file> --nca  <dir>      # 只切 NCA
python scripts/ns_open.py <file> --romfs <dir>     # 切 NCA 并导 romfs
```
它做三件事：① `cwd=_sw` + 默认 `merged.keys`（消灭假警告）；② XCI 失败自动回退 `xci_hfs0.py`、NSP 走 `nsp_split.py`；
③ NCA 导 romfs 失败时按日志判定「patch/压缩」并转 `bktr_romfs.py`，同时打印**走了哪条路线、为什么**。

### 每作脚本的定位（别再把它们当通用件）

`nca_romfs.py` / `nca_stream_romfs.py` / `ukronia_*.py` / `handsome_*.py` 这类是**某作的薄驱动**（含该作的路径/偏移/titlekey 硬编码），
只能复现、不能复用。真正通用的只有 4 个：`xci_hfs0.py`｜`nsp_split.py`｜`switch_nca.py`｜`bktr_romfs.py`。
**判据：脚本里出现具体作品名/硬编码偏移 ⇒ 它是驱动，不是工具。**

### DLC（追加内容）的 NCA 是 **Data 型**，RomFS 在 **Section 0**

- 现象：`nsp_split` 正常拆出 NCA，`hactool -t nca --romfsdir` 返回 rc 0 但**一个文件都没导出**。
- 原因：DLC 的 NCA `Content Type: PublicData`，`Section 0` 就是 RomFS（而 Program NCA 的 romfs 在 `Section 1`）。
- 正解：`nstool -k merged.keys --tik <tik> --part0 <outdir> <nca>`；或 `switch_nca.py`（自研，按段表直取）。
- 识别：`hactool -t nca -i` 看 `Content Type` 与 `Section 0: Partition Type: RomFS`。
- 提醒：**DLC 正文不在本体成品里**，交付前若源目录有 `*DLC*.nsp` 必须单独提，并写进报告。

### ★★ DLC 的真伪：**DLC nsp 常常只是解锁标记，正文在「更新档」里**

2026-10-26 实测（ハンサムロンダリング / NS）：

| 层 | 观察 | 说明 |
|---|---|---|
| DLC nsp | 各 **121 KB**，解开只有 1 个 21 字节 txt（`After Story case.CATS`） | **AOC 解锁标记**，不是剧情 |
| 更新档 UPD 1.3.0 | **244 MB**，`sharedassets1.assets` 从本体 **11 KB → 34 MB** | 真正的 DLC 资源在这里 |
| 该 assets | Utage `book` 251 个，8 个含文本共 **1,832 行** | ⇒ 8 个追加短篇 |

**判定流程（别再只看 DLC nsp）**：
1. DLC nsp **< 1 MB** ⇒ 先怀疑是解锁标记；
2. 找**同作品的 UPD（更新档）最新版**，比对 `sharedassets*.assets` / `resources.assets` 体积是否暴涨（可用 `scripts/handsome_updraw.py --diff` 这类工具做文件级 diff）；
3. 用**该引擎的剧本提取器**扫「更新后的 assets」（Unity 作常用 UnityPy；Utage 用 `utage_extract.py`）；
4. 与已交付成品做差集 ⇒ 差集才是漏收的 DLC 正文。

**反例**：泡沫のユークロニア 的 DLC1/2 带 `scenario_aoc01`(43 KB) / `scenario_aoc02`(59 KB)，提出来 1,130 行**全部已在成品**——说明该作把 DLC 内容也放进了本体 romfs。**所以必须做差集，不能假定「DLC 文件里有 ⇒ 成品没有」。**
