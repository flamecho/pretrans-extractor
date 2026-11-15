# Switch NCA、更新与解包故障

按实际容器、NCA 类型、加密方式、FS 段及工具版本选择路径。
优先复用已解资源和当前支持实现，错误文本只提示原因。

## 入口与版本范围

工作区工具 `scripts/ns_open.py` 可按容器列分区、切 NCA、导 RomFS；
参数见本机帮助。本作适配器含固定路径、偏移或密钥时，先核对输入版本。
通用部件包括 xci_hfs0、nsp_split、switch_nca、bktr_romfs。

核对本体、更新及 DLC 的 CNMT、TitleID 和覆盖关系。
卡带 update 分区可为系统更新，不能按分区名、NCA 数量或高熵直接分类。
官方文本修正采用补丁覆盖；补丁未修的原文异常登记保留，不自动补引号。

## NCA 密钥与 FS

| 情况 | 处理 |
|---|---|
| 标准 crypto | 按 key generation 与 key area 获取内容密钥 |
| Rights ID/titlekey crypto | 使用解密 titlekey，不再次走 key area 解密 |
| ticket | 常见加密 titlekey 位于 `180:190`，结合 ticket 格式确认 |
| 工具 titlekey 参数 | 核对该版本接收加密还是明文值，不跨工具套约定 |

key revision 按 NCA 与 ticket 的真实字段映射，不把某个字节直接作通用索引。
CTR 按 FS header 的 counter 和绝对 section offset 生成；
用 PFS0、IVFC、RomFS 头及已有工具结果核对。
工具能解而自写不能解时先比对密钥、counter、偏移和实现，
不能据此断言源被重新加密或只能换源。

密钥长度或格式异常在本作临时配置中处理，保留原始 keyset。
缺默认 prod.keys 警告须核对显式 -k 是否生效，不据警告反复复制多套配置。

## BKTR 与压缩段

BKTR 更新读取匹配本体虚拟视图；按 FS 表确定 base section，
不硬编码 Program 的 RomFS 必在 section1。
可用支持工具的 baseromfs/exefsdir/romfsdir 导出有效更新文件。

NCA CompressionInfo 与 BKTR 是不同层；查对应段的 CompressionInfo、SparseInfo 和 IVFC。
千銃士R 的压缩表相对数据层，bucket 为 `4000` 字节，
条目 `{virtual:u64,physical:u64,type:u32,storedBytes:u32}`；
本作 type0 为 raw、type3 为 LZ4 block。
按 storedBytes 截取，不能把物理对齐填充交给 LZ4。

首块、bucket 和虚拟长度核对本作表，不能仅凭 `offset+size` 等式确定基准。
参考 `scripts/senjyushi_extract.py` 与 `scripts/switch_nca.py`；
已有支持实现优先，不因旧 hactool 报目录错就重写解包器。

## NSP、XCI 与 RomFS

PFS0 标准 entry 为 24 字节：
`offset:u64,size:u64,nameOffset:u32,reserved:u32`。
字符串表始于 `10+count*18(hex)`，
数据基址再加 stringTableBytes；不能按 16 字节读，也不把 24 字节视为特殊变体。

XCI HFS0 条目为 64 字节，offset 相对头、条目和字符串表之后的数据区。
hash 校验失败先检查 header、密钥及实际布局；有充分结构证据时可用已证 HFS0 提取器，
不把 corrupt 报错单独当布局损坏或可以跳过校验的依据。

RomFS 目录和文件名内联、按四字节对齐：
`dirAdvance=18(hex)+align4(nameBytes)`，
`fileAdvance=20(hex)+align4(nameBytes)`。
大型 NCA/NSP 采用就地 seek 和按需解密，避免为文本复制整个媒体镜像。

DLC Data/PublicData 的 RomFS 可在 section0，按段表定位。
DLC 可能仅为解锁标记，实际剧情在更新或本体资源；按引用与覆盖确认，
不能由包大小或文本差集独立判断缺失。

## NSO0

| 偏移 | 字段 |
|---|---|
| 00/04/08/0C | NSO0、version、reserved、flags |
| 10/14/18/1C | text fileOffset、memoryOffset、size、moduleNameOffset |
| 20/24/28/2C | ro fileOffset、memoryOffset、size、moduleNameSize |
| 30/34/38/3C | data fileOffset、memoryOffset、size、bssSize |
| 60/64/68 | text/ro/data 压缩长度 |
| A0/C0/E0 | 三段 SHA-256 |

flags bit0–2 为对应段 LZ4 block，bit3–5 指示 hash 校验。
按 fileOffset 和压缩长度读取，不把 size 当文件偏移。
解压后按 memoryOffset 落位，保留段间空洞；启用 hash 时核对摘要。
ModuleName 的长度不能用来猜 text 数据起点。
工具 `scripts/nso_x.py`，IL2CPP 读取见 [Unity](../engines/unity.md)。

## ARM64 资源加载定位

ADRP 掩码 `(w&9F000000)==90000000`，
页目标为 `(pc&~FFF)+(signExtend(immhi:immlo)<<12)`；
结合相邻 ADD 和真实数据流追踪资源名。
loader 后的调用是处理函数候选，须核对参数及被调方，不能按“紧邻函数”直接认定解压器。
LZSS 的 literal 极性、位域和长度增量按完整调用解释，验证消费、长度及结构。

## 常见故障

| 信号 | 优先核对 |
|---|---|
| Invalid NCA header | header key、工具支持版本、源头结构 |
| AES-CTR key 未确定 | key generation、Rights ID、titlekey 约定 |
| RomFS cache/hash 层失败 | key/counter、base、BKTR、压缩或 sparse 支持 |
| 大成员全零、工具崩溃 | 实际输出范围、工具大文件支持，改用流式实现 |
| Git-Bash 的根路径被改写 | PowerShell 或 `MSYS2_ARG_CONV_EXCL=*` 加 Windows 路径 |
| 返回 0 但没有文件 | 分区类型、选择范围及实际输出，不仅看退出码 |

只处理已确认原因，不按错误字符串自动切换所有路线或更换原版源。

## 构建记录：platform-switch-nca

- Switch XCI/NCA/NSP（Paradigm Paradox 定案）：XCI 卡带分区可明文，root HFS0 偏移在 XCI 头 0x130；NSP(PFS0) 条目 `{u64 off,u64 size,u32 nameoff,u32 pad}`（0x18/条，表在 0x10，数据基址=0x10+N*0x18+strsize）。NCA3 明文头在 0x200（0x00 Fixed-Key / 0x100 NPDM 签名）；keygen=`max(hdr[0x206],hdr[0x220])-1`；段头 `@0x400+i*0x200`。头 XTS 用大端 sector tweak（`AES(k2, sector.to_bytes(16,'big'))`）。段数据 CTR：key=解密后 key area slot2；计数器=`rev(section_ctr)`‖`BE(pos>>4)`，须 16B 对齐起解；key_area 用 `key_area_key_application_XX`(XX=max(crypto,crypto2)-1)；RomFS 在 IVFC 末级。Titlekey `=AES_ECB_dec(titlekek_keygen, tik[0x180:0x190])`；hactool `--titlekey=` 传加密 titlekey。`prod.keys` 里 17B 的 `mariko_master_kek_source_*` 坏条目会让 hactool 报错 → 先过滤。参考 `scripts/kuriimu2_src/src/lib/Kryptography/Encryption/Nintendo/Switch/*`。
  - NSP 实测补充（悪役令嬢，2026-10-05）：① hactool 选项须写 `--keyset=<path>`，`-k <path>` 这份 build 不生效（会回落到默认 prod.keys）。② `hactool --titlekey=` 收的是 `.tik[0x180:0x190]` 里那段「加密」titlekey，hactool 会自己再解一遍并打印 `Titlekey (Decrypted) (From CLI)`；真正生效的 titlekey = `AES_ECB_dec(titlekek_N, tik[0x180:0x190])`。③ titlekek 索引 = NCA 的 Master Key Revision（`max(hdr[0x206],hdr[0x220])-1`），不是 ticket 的 0x285（两者可差 1：本体 NCA 0x10 / ticket 0x11；更新 NCA 0x11 / ticket 0x12）。④ ticket 布局：sig(0x140)+Issuer(0x40)+TitleKeyBlock(0x100 @0x180)+…，`0x280` 版本、`0x281` titlekey type、`0x285` master key rev、`0x2A0` rights id。⑤ 旧 hactool(2020) 本体（titlekey crypto）能整段解 RomFS；但遇 BKTR 增量更新段会 segfault，`--baseromfs`(用 `--romfs=`/`--section1=` 的产物) 亦报 `Failed to read RomFS directory cache!` ⇒ 增量更新落不了地；此时可直接解更新段的 section1 并读其中 RomFS 文件表（文件名明文可辨）来判断更新是否动了文本。⑥ `--exefsdir=`/`--romfsdir=` 可一次解出。⑦ 判定更新只加语言的实例：更新段文件表里同时出现 `adv101.CSR` 与 `adv101_en.CSR` → 仅补英文化。

### NCA 头 XTS / 段表 / BKTR 增量补丁（OZMAFIA!! -vivace- 1.0.1，2026-10-12）
- NCA 头 XTS 解密（自写 `scripts/ozmafia_nca.py`，结果与 hactool 打印逐字节一致）：
  `magic 'NCA3'` 在 0x200（0x000–0x1FF 是 RSA/固定键签名，勿拿 0x0 当 magic）；
  sector tweak = `AES_enc(header_key[16:], sector_idx 大端 16B)`，同一 sector 内每 16B 块 tweak 递进 alpha（GF(2^128)×x，回约 0x87）。
- 头字段：段表 @0x240（4×0x10，`media_start/media_end` = u32 小端，单位 0x200）；rights_id @0x230（16B）；
  key_generation @0x206 / key_generation_2 @0x220 ⇒ `keygen = max−1`。段 FS 头 @`0x400+secno*0x200`。
- 段数据 AES-CTR：counter 初值 = 段 FS 头的 section_ctr（`bytes[0:4]`=段号+1，`bytes[8:16]`=段文件偏移/16，大端 16B）。
- BKTR 增量补丁本机解不了：`hactool`(2020-06-01) `--romfsdir` ⇒ `cannot save BKTR section without base romfs`；
  `--baseromfs=<本体 section1>` ⇒ `Failed to read RomFS directory cache!`（与既有坑一致；本体 section1 须 `hactool --section1=` 先导出）。
  本机无 hactoolnet/nstool。OZMAFIA 补丁：段0=ExeFS、段1=Patch RomFS（BKTR，0x9cc400）；
  key area(@0x300) 全 0（titlekey crypto），但 hactool 打印的 `Titlekey (Decrypted)` 作内容密钥 + section_ctr
  解不出 RomFS 头明文（`50 00 00 00…`）⇒ 内容密钥/计数器未闭合，按纪律停手。要补丁级保真须换较新工具。
- 另：`prod.keys` 含 17 字节的 `mariko_master_kek_source_*` 会让 hactool 报 `Key (...) must be 32 hex digits!` ⇒ 先滤成 prod_fixed.keys。

### 另一种 BKTR：全量压缩 NCA（fs header `CompressionInfo`；≠ 上面的「增量补丁段」）

判据：解密的段 FS 头 @`0x400+secno*0x200` 里 `CompressionInfo`(@+0x178, {u64 offset, u64 size}) 非零
（`SparseInfo`@+0x148 亦可能非零）。此时 section 数据本身是 LZ4 分块压缩，不是增量补丁。

- 现成工具全不支持（2026-10-16 实测）：`hactool`(2020) ⇒ `Failed to read RomFS directory cache!`；
  `hactool` 1.4.0 / `nstool` 1.9.2 / `Kuriimu2` ⇒ 同样失败（`Hash layer 3 failed` / 报 corrupt）。
  只能自写：`scripts/senjyushi_extract.py`（`NcaReader` + `parse_buckets` + `Virt` + `parse_romfs`）。
- `CompressionInfo.offset` 相对「section 的 DATA 层(IVFC level5)起点」，不是 section 起点
  （自洽判据：`offset + size == level5 尺寸`）。
- 桶树布局：`@0x00 u32 pad; @0x04 u32 bucket_count; @0x08 u64 total; @0x10 bucket_count×u64 base_offsets`；
  桶自 `@0x4000` 起、每桶 0x4000：`{u32 idx, u32 entry_count, u64 end}` + `entry_count×0x18` 条目。
- 条目 = `{u64 virtual_off, u64 physical_off(相对 level5 起点), u32 comp_type, u32 comp_size}`；
  `comp_type 0=raw / 3=LZ4(块格式)`；块 0x10000（首块 0x200 raw）。
- physical 按 0x10 对齐 ⇒ 必须按 `comp_size` 精确截取，多截到填充字节会令 LZ4 报 corrupt（本作最大一坑）。
- 实例（千銃士R）：136 桶 × 682 条 = 92,228 条，解压总长 13,128,882,432 B = RomFS 镜像大小 → 9,936 文件。
- NCA 头 AES-XTS 的 tweak 是「字节反序」（非标准 XTS）：`T0 = AES_enc(k2, 扇区号 大端)`，
  扇区内每 16B 块 `T ← rev(α_be(rev(T)))`（`rev` = 128 位字节反序）。已落入 `scripts/switch_nca.py`，与 hactool 逐字节一致。
- titlekey 走 `master_key_<rev>` + `titlekek_source` 现推（keyset 缺该 source 时 hactool 会静默用错 key）。

### NSP 头部被清零后仍能打开

- 症状：`hactool -t nsp` 报 `Invalid NCA header`、`nstool` 报 `Input file type was undetermined`。
  原因不是 keys：文件 0x0–0x8000 被整段清零（原本的 `PFS0` 头没了），但 0x8000 之后完好
  （`tik` @0x8000（issuer `Root-CA00000003-XS00000020` @+0x140）、第二张 tik @0x86C0、cnmt NCA @0x89C0、Program NCA @0x97C0）。
- 定位 NCA 起点的通用手法（不靠 PFS0）：NCA 头是 header_key AES-XTS；`NCA3` 魔数在解密后 0x200，
  且该处属 sector 1 的 block 0 ⇒ tweak 恒为 `T = AES_enc(k2, BE(1))`（同文件所有候选点相同）。
  ⇒ 把文件按 `d[0x200:]` 切 16B 块批量 ECB 解密（一次 C 调用），逐块 `C^T` 比对 `4E 43 41 33`
  （必须先 `C^T` 再解密、解密后再 `^T`，漏任一次全灭）。步长 0x10，不能用 0x200
  （NSP 里 NCA 常紧贴 PFS0 头，如 `0x120`）。
- titlekek 索引 = keygen − 1（同 key_area_key）：本作 NCA `Key Generation: 16(0x10)`，
  `titlekey = AES_dec(titlekek_0f, tik[0x180])`；用 `titlekek_10` 会得到「看着像随机」的错键
  （hactool `--titlekey` 会打印 `Titlekey (Decrypted)`，可直接对账）。
- romfs 段 CTR：`high8 = fs_header[0x741:0x749]`，`low = NCA 内绝对偏移/16`（含段起点 `0x1C000`）。
  nstool `--showlayout` 会直接打印 `AesCtr Counter`（本作 `00000002000000000000000000001C00`）——先问它，勿猜。
- 判 key 对不对的唯一硬判据：把 data layer 第 0 块（0x4000）解密后 SHA256，与 IVFC `Hash Layer 4[0]` 比；
  相等即闭包（本作 `b9ae9da4eb17fca3…`），不必等整段。
- 本作 romfs 是「元数据在尾部」的变体：header 在 0，`dir_hash@0x145aac270 / dir_meta@0x145aac344`，
  `file_hash@0x145aaca88 / file_meta@0x145adabe4`（逐项 `off+size` 恰好衔接到 `data_size=0x145d1c21c`）。
  ⇒ 截断的 dump 连文件名都列不出（元数据在 5.46 GB 处），勿再试「先列表再抽文件」。
- 文件截断的判据链：`u64@0x208`(NCA size) vs 实际文件长度；nstool 报
  `SubStream length is greater than base stream length`；`--fstree` 只列得出 Partition 2（logo，明文）。
