# CHD v5（zstd）→ ISO 裸镜像（自写解码，无需 chdman）

> 起因 Jewelic Nightmare PSP：**PSP/PS2/PS3 的 `.chd` 源近年普遍改用 CHD v5 ＋ zstd**，
> 而本机/无网环境常拿不到 `chdman` ⇒ 这条自写路径已实证位级无损，直接复用。

## 0. 判据与前置

- 头部 8 B ＝ `MComprHD`；**其后所有多字节字段一律大端**（`MAME chd.h` 约定），
  `version==5`；`compressors[0..3]` 形如 `zstd`/`lzma`/`cdzl`/`cdfl`/`huff`（ASCII 四字符）。
- 依赖：**Node 22.15+（`zlib.zstdDecompressSync`）** —— 比 Python 省事（本机无 zstandard/lzma-chd 库）。
  ⚠ Node 的 `createZstdDecompress` **不接续多帧**（读完第一帧就 end）⇒ **必须自己算帧长**、逐帧解。
- 工具：`scripts/chd_to_iso.js <chd> <out.iso>`。

## 1. CHD v5 头部（文件偏移，大端）

| off | 宽 | 字段 |
|---|---|---|
| 0x00 | 8 | `"MComprHD"` |
| 0x08 | 4 | header length（=124） |
| 0x0C | 4 | version（=5） |
| 0x10 | 16 | compressors[4] |
| 0x20 | 8 | logicalbytes |
| 0x28 | 8 | mapoffset |
| 0x30 | 8 | metaoffset |
| 0x38 | 4 | **hunkbytes** |
| 0x3C | 4 | unitbytes |
| 0x40/0x54/0x68 | 20×3 | rawsha1 / sha1 / parentsha1 |

`hunkcount = logicalbytes / hunkbytes`；`rawsha1` ＝**整盘裸镜像的 SHA1**（见 §5 自检）。

## 2. map 头（`mapoffset` 起 16 B，大端）

| off | 宽 | 字段 |
|---|---|---|
| 0 | 4 | mapbytes（后续压缩 map 流的字节数） |
| 4 | 6 | firstoffs（首个 hunk 数据偏移） |
| 10 | 2 | mapcrc（**CRC16 over 解出的 12 B×hunkcount**） |
| 12 | 1 | lengthbits |
| 13 | 1 | selfbits |
| 14 | 1 | parentbits |
| 15 | 1 | — |

map 流在 `mapoffset+16`，长 `mapbytes`，**不是 zlib**，而是「Huffman 编码的类型流 + 位流参数」。

## 3. map 解码（两遍）

**Pass 1 — 类型字节**：`create_huffman_decoder(16, 8)`
⇒ ★**参数是（numcodes=16, maxbits=8），码长位宽 = 4 bit**。
（按「maxbits=16/位宽 5」读会得到 Kraft 和 ≈3.2、码长 21 的非法树——这就是本作第一次失败的原因；
**自检判据：码长直方图的 Kraft 和必须恰为 1.000000**。）

- 导树（`huffman_import_tree_rle`）：`v=read(4)`；`v!=1` ⇒ 码长 v；`v==1` 再读一个 ⇒ 若又是 1 则码长 1，
  否则 `rep = read(4)+3` 连铺 `rep` 个「上一步读到的值」。
- 规范化码（canonical）后建 `1<<8` 查表；`huffman_decode_one` = `peek(8)` 查表、`remove(len)`。
- 解码 hunkcount 个类型：`7=RLE_SMALL`（再解 1 符号 n ⇒ 重复 `2+n`）、
  `8=RLE_LARGE`（解 hi、lo ⇒ 重复 `2+16+(hi<<4)+lo`）、`9=SELF_0`、`10=SELF_1`、`11=PARENT_SELF`、`12/13=PARENT_0/1`。

**Pass 2 — length/offset/crc**（位流 MSB-first，32 bit 缓冲）：

| 类型 | 读法 |
|---|---|
| `0..3`（压缩器 n） | `len=read(lengthbits)`；`curoffset+=len`；`crc=read(16)` |
| `4`（NONE） | `len=hunkbytes`；`curoffset+=len`；`crc=read(16)` |
| `5`（SELF） | `offset=read(selfbits)`（**单位＝unitbytes**，不是字节） |
| `6`（PARENT） | `offset=read(parentbits)` |
| `9/10` | `offset=last_self`(+1)，归化为 5、**不读位** |
| `11/12/13` | `last_parent` 递推，归化为 6、不读位 |

`curoffset` 初值＝`firstoffs`，跨 hunk 累积（**不能每 hunk 重置**）。

## 4. hunk 还原

- `0..3` ⇒ 取 `[offset, offset+len)` 按 `compressors[n]` 解（本作 zstd：**标准帧，FCS=2048**）；长度须 == hunkbytes。
- `4` ⇒ 原样 `len` 字节。
- `5` ⇒ 从**已写出的逻辑偏移** `offset*unitbytes` 复制 hunkbytes（顺序写盘时可直接 `readSync` 回读）。
- zstd 帧长自算：`magic(4) + FHD(1) [+win] [+dictID] [+FCS] + blocks(3B 头: last/type/size，RLE 块数据仅 1B) [+checksum]`。

## 5. 自检（**必做，零成本**）

1. `CRC16(map 解出结果)` == map 头 `mapcrc`（本作 `0xef11`）；
2. 逐 hunk `crc16(data)` == map 里的 crc16（SELF 项不读 crc，恒为 0 ⇒ **不可算作失败**：
   本作 71710 个「crcbad」恰等于 SELF 数，反证其余全过）；
3. **整盘 SHA1 == 头部 `rawsha1`** ⇒ 位级无损，可放心进入容器层。

## 6. 踩过的坑

- `hunkbytes` 可能只有 **2048**（DVD 型 CHD 从 2048 B 扇区 ISO 压制）⇒ hunkcount 高达 72 万，别按「DVD 默认 8 MB」推定。
- `compressors[0]` 读出来像 `0x7a737464`，**按大端解 4 字节才是 ASCII `zstd`**——先用 `to_bytes(4,'big')` 看一眼。
- `metaoffset=124` ⇒ 头部之后常跟一条 16 B metadata 记录（`"DVD "` 等），真正的首个 hunk 在 `firstoffs`（≠124）。
- 裸镜像 SHA1 对上就说明**不必再纠结 hunk 类型统计**（本作 168,162 zstd ＋ 480,832 NONE ＋ 71,710 SELF）。
