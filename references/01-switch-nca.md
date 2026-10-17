# 解密 / 解码 · 补丁与 Switch NCA 专章

> 总览看 `pitfalls/A1-decode-core.md`；
> 本文件在「有官方补丁要合并」或「载体系 Switch NCA」这一阶段读。NCA 判型/纯文本脚本取值见 `02-unity.md`。

## 5. 官方修正补丁先解（★常被忽略）

- 同捆的 `Patch.rar` / `update.exe` / `patch.xp3` **先解开**。官方补丁常写「**一部の誤字脱字の修正**」。
- 内多为**与本体同方式的脚本文件** → 同一套解密即可解出 → 与本体 **diff 就拿到「作者认定的正确文本」**。
- 蝶の毒 v1.01 实证修正 6 处显示文：
  `斯波さま→斯波さん` / `噛察→観察` / 助詞脱落 / `*G用→雑用` / `済んだ→澄んだ` / `非常→非情`。
- **关键旁证**：`*G用→雑用` 说明**配布数据自身就带着化け文字** —— 不是解密方的错，官方只能靠补丁修。
  ⇒ 见到孤立化け时**两边都查**（自己的解码 + 原始数据缺陷）。
- 补丁**只覆盖部分文件**；未覆盖文件里的同类缺陷要自己判。
  （蝶の毒 `05_shiba_1.ks` 的闭引号 `」` 脱落＝官方漏修：XOR 保长度 ⇒ 物理上无该字节 ⇒ 数据缺陷，据「开 `「` 必合 `」`」补回。）

### 5.1 Switch 更新＝NCA「**BKTR 增量段**」—— **已解决**（2026-10-12 定案，魔女と亡霊のヴォロンテ）

1. `prod.keys` 里 17B 的 `mariko_master_kek_source_*` 先滤（否则 hactool 报 key 长度错）；
2. 带 Rights ID 的更新 NCA：ticket `tik[0x180:0x190]` 的**加密** titlekey 传 `--titlekey=<16B hex>`
   （hactool 会打印 `Titlekey (Decrypted) (From CLI)`；`key area @0x300` 全 0 ⇒ `Encryption Type: Titlekey crypto`）；
3. **先导出本体 RomFS 当 baseroot**：`-t nca --section1=base_sec1.romfs <本体NCA>`；
4. 更新 ExeFS：`--exefsdir=`；更新 RomFS：`--baseromfs=base_sec1.romfs --romfsdir=`
   ⇒ **成功判据＝能列出/解出 `rom:\…` 文件**（旧 hactool(2020) 也能成；`--listromfs` 先看清单）。

★ **XCI 内可同捆「全量替换型」更新**：secure 分区里**同一 Title ID 两个 Program NCA**（一个无 Rights ID＝本体，
一个带 Rights ID＋`Patch RomFS`(BKTR)＝更新）。**先比两者 RomFS 文件表**（文件名 hash 不同即被改）；
Unity 游戏更新常替换 `global-metadata.dat`/`resources.assets`/全部 asset bundle ⇒ **不比对就会用旧数据**。

### 5.2 ★ **全量压缩 NCA**（≠ 上面的「增量 BKTR」；2026-10-16 千銃士R）

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
