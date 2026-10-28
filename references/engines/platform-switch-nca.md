# Switch XCI / NCA / NSP

> 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。

- **Switch XCI/NCA/NSP**（Paradigm Paradox 定案）：XCI 卡带分区可**明文**，root HFS0 偏移在 XCI 头 0x130；NSP(PFS0) 条目 `{u64 off,u64 size,u32 nameoff,u32 pad}`（0x18/条，表在 0x10，数据基址=0x10+N*0x18+strsize）。**NCA3 明文头在 0x200**（0x00 Fixed-Key / 0x100 NPDM 签名）；keygen=`max(hdr[0x206],hdr[0x220])-1`；段头 `@0x400+i*0x200`。**头 XTS 用大端 sector tweak**（`AES(k2, sector.to_bytes(16,'big'))`）。段数据 CTR：key=解密后 key area **slot2**；计数器=`rev(section_ctr)`‖`BE(pos>>4)`，须 16B 对齐起解；key_area 用 `key_area_key_application_XX`(XX=max(crypto,crypto2)-1)；RomFS 在 IVFC 末级。**Titlekey** `=AES_ECB_dec(titlekek_keygen, tik[0x180:0x190])`；★ hactool `--titlekey=` 传**加密 titlekey**。`prod.keys` 里 17B 的 `mariko_master_kek_source_*` 坏条目会让 hactool 报错 → 先过滤。参考 `scripts/kuriimu2_src/src/lib/Kryptography/Encryption/Nintendo/Switch/*`。
  - ★★ **NSP 实测补充（悪役令嬢，2026-10-05）**：① **hactool 选项须写 `--keyset=<path>`，`-k <path>` 这份 build 不生效**（会回落到默认 prod.keys）。② **`hactool --titlekey=` 收的是 `.tik[0x180:0x190]` 里那段「加密」titlekey**，hactool 会自己再解一遍并打印 `Titlekey (Decrypted) (From CLI)`；真正生效的 titlekey = `AES_ECB_dec(titlekek_N, tik[0x180:0x190])`。③ **titlekek 索引 = NCA 的 Master Key Revision（`max(hdr[0x206],hdr[0x220])-1`），不是 ticket 的 0x285**（两者可差 1：本体 NCA 0x10 / ticket 0x11；更新 NCA 0x11 / ticket 0x12）。④ ticket 布局：sig(0x140)+Issuer(0x40)+TitleKeyBlock(0x100 @0x180)+…，`0x280` 版本、`0x281` titlekey type、`0x285` master key rev、`0x2A0` rights id。⑤ **旧 hactool(2020) 本体（titlekey crypto）能整段解 RomFS**；但遇 **BKTR 增量更新段会 segfault**，`--baseromfs`(用 `--romfs=`/`--section1=` 的产物) 亦报 `Failed to read RomFS directory cache!` ⇒ 增量更新落不了地；此时可**直接解更新段的 section1 并读其中 RomFS 文件表**（文件名明文可辨）来判断更新是否动了文本。⑥ `--exefsdir=`/`--romfsdir=` 可一次解出。⑦ 判定更新只加语言的实例：更新段文件表里同时出现 `adv101.CSR` 与 `adv101_en.CSR` → 仅补英文化。

## ★ NCA 头 XTS / 段表 / BKTR 增量补丁（OZMAFIA!! -vivace- 1.0.1，2026-10-12）
- **NCA 头 XTS 解密**（自写 `scripts/ozmafia_nca.py`，结果与 hactool 打印**逐字节一致**）：
  `magic 'NCA3'` 在 **0x200**（0x000–0x1FF 是 RSA/固定键签名，别拿 0x0 当 magic）；
  sector tweak = `AES_enc(header_key[16:], sector_idx 大端 16B)`，同一 sector 内每 16B 块 tweak **递进 alpha**（GF(2^128)×x，回约 0x87）。
- **头字段**：段表 @**0x240**（4×0x10，`media_start/media_end` = **u32 小端**，单位 0x200）；rights_id @0x230（16B）；
  key_generation @0x206 / key_generation_2 @0x220 ⇒ `keygen = max−1`。段 FS 头 @`0x400+secno*0x200`。
- **段数据 AES-CTR**：counter 初值 = 段 FS 头的 section_ctr（`bytes[0:4]`=段号+1，`bytes[8:16]`=**段文件偏移/16**，大端 16B）。
- **⚠ BKTR 增量补丁本机解不了**：`hactool`(2020-06-01) `--romfsdir` ⇒ `cannot save BKTR section without base romfs`；
  `--baseromfs=<本体 section1>` ⇒ `Failed to read RomFS directory cache!`（与既有坑一致；本体 section1 须 `hactool --section1=` 先导出）。
  **本机无 hactoolnet/nstool**。OZMAFIA 补丁：段0=ExeFS、段1=**Patch RomFS（BKTR，0x9cc400）**；
  key area(@0x300) **全 0**（titlekey crypto），但 hactool 打印的 `Titlekey (Decrypted)` 作内容密钥 + section_ctr
  解不出 RomFS 头明文（`50 00 00 00…`）⇒ **内容密钥/计数器未闭合，按纪律停手**。要补丁级保真须换较新工具。
- 另：`prod.keys` 含 17 字节的 `mariko_master_kek_source_*` 会让 hactool 报 `Key (...) must be 32 hex digits!` ⇒ **先滤成 prod_fixed.keys**。

## ★ 另一种 BKTR：**全量压缩 NCA**（fs header `CompressionInfo`；≠ 上面的「增量补丁段」）

**判据**：解密的段 FS 头 @`0x400+secno*0x200` 里 **`CompressionInfo`(@+0x178, {u64 offset, u64 size}) 非零**
（`SparseInfo`@+0x148 亦可能非零）。此时 **section 数据本身是 LZ4 分块压缩**，不是增量补丁。

- ⚠ **现成工具全不支持**（2026-10-16 实测）：`hactool`(2020) ⇒ `Failed to read RomFS directory cache!`；
  `hactool` 1.4.0 / `nstool` 1.9.2 / `Kuriimu2` ⇒ 同样失败（`Hash layer 3 failed` / 报 corrupt）。
  **只能自写**：`scripts/senjyushi_extract.py`（`NcaReader` + `parse_buckets` + `Virt` + `parse_romfs`）。
- **`CompressionInfo.offset` 相对「section 的 DATA 层(IVFC level5)起点」**，不是 section 起点
  （自洽判据：`offset + size == level5 尺寸`）。
- 桶树布局：`@0x00 u32 pad; @0x04 u32 bucket_count; @0x08 u64 total; @0x10 bucket_count×u64 base_offsets`；
  桶自 **`@0x4000`** 起、每桶 0x4000：`{u32 idx, u32 entry_count, u64 end}` + `entry_count×0x18` 条目。
- **条目 = `{u64 virtual_off, u64 physical_off(相对 level5 起点), u32 comp_type, u32 comp_size}`**；
  `comp_type 0=raw / 3=LZ4(块格式)`；块 0x10000（首块 0x200 raw）。
- ⚠★ **physical 按 0x10 对齐 ⇒ 必须按 `comp_size` 精确截取**，多截到填充字节会令 LZ4 报 corrupt（本作最大一坑）。
- 实例（千銃士R）：136 桶 × 682 条 = **92,228** 条，解压总长 **13,128,882,432 B** = RomFS 镜像大小 → 9,936 文件。
- **NCA 头 AES-XTS 的 tweak 是「字节反序」**（非标准 XTS）：`T0 = AES_enc(k2, 扇区号 大端)`，
  扇区内每 16B 块 `T ← rev(α_be(rev(T)))`（`rev` = 128 位字节反序）。已落入 `scripts/switch_nca.py`，与 hactool 逐字节一致。
- ⚠ titlekey 走 `master_key_<rev>` + `titlekek_source` 现推（keyset 缺该 source 时 hactool 会**静默用错 key**）。
