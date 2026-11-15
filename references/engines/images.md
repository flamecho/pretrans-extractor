# CHD 与原始光盘镜像

优先使用 `chdman`；自有解码器仅用于已支持的压缩器和映射类型。
以下字段用于实现或排错，已有可靠导出结果时不重复解码。

## 判据与前置

- 签名为 `MComprHD`，本册布局适用于 `version=5`；多字节字段采用大端序。
- `compressors[0..3]` 为四字节压缩器标识，按标识选择支持的实现。
- 工作区工具：`scripts/chd_to_iso.js <chd> <out.iso>`，仅复用其已支持的 zstd 与映射类型。

## CHD v5 头部（文件偏移，大端）

| off | 宽 | 字段 |
|---|---|---|
| 0x00 | 8 | `"MComprHD"` |
| 0x08 | 4 | header length（=124） |
| 0x0C | 4 | version（=5） |
| 0x10 | 16 | compressors[4] |
| 0x20 | 8 | logicalbytes |
| 0x28 | 8 | mapoffset |
| 0x30 | 8 | metaoffset |
| 0x38 | 4 | hunkbytes |
| 0x3C | 4 | unitbytes |
| 0x40/0x54/0x68 | 20×3 | rawsha1 / sha1 / parentsha1 |

`hunkcount = ceil(logicalbytes / hunkbytes)`；`rawsha1` 对应 CHD 逻辑数据。

## map 头（`mapoffset` 起 16 B，大端）

| off | 宽 | 字段 |
|---|---|---|
| 0 | 4 | mapbytes（后续压缩 map 流的字节数） |
| 4 | 6 | firstoffs（首个 hunk 数据偏移） |
| 10 | 2 | mapcrc（CRC16 over 解出的 12 B×hunkcount） |
| 12 | 1 | lengthbits |
| 13 | 1 | selfbits |
| 14 | 1 | parentbits |
| 15 | 1 | — |

map 流在 `mapoffset+16`，长 `mapbytes`，由 Huffman 类型流和位流参数构成。

## map 解码（两遍）

第一遍解码类型，`create_huffman_decoder(16, 8)` 的参数为 numcodes=16、maxbits=8，码长占 4 bit。

- 导树：`v=read(4)`；v≠1 时码长为 v。v=1 时再读值，值为 1 则码长为 1，否则重复该值 `read(4)+3` 次。
- 生成 canonical 码及 `1<<8` 查表；解码时 `peek(8)` 查表，再消费实际码长。
- 解出 hunkcount 个类型：`7=RLE_SMALL` 重复前类型 `2+n` 次；`8=RLE_LARGE` 重复 `2+16+(hi<<4)+lo` 次。
- `9/10=SELF_0/1`、`11=PARENT_SELF`、`12/13=PARENT_0/1` 在第二遍归一化。

第二遍读取 length/offset/crc，位流为 MSB-first：

| 类型 | 读法 |
|---|---|
| `0..3`（压缩器 n） | `len=read(lengthbits)`；`curoffset+=len`；`crc=read(16)` |
| `4`（NONE） | `len=hunkbytes`；`curoffset+=len`；`crc=read(16)` |
| `5`（SELF） | `offset=read(selfbits)`（SELF 引用 hunk 编号） |
| `6`（PARENT） | `offset=read(parentbits)` |
| `9/10` | `offset=last_self`(+1)，归化为 5、不读位 |
| `11/12/13` | `last_parent` 递推，归化为 6、不读位 |

`curoffset` 初值为 `firstoffs`，跨 hunk 累积。

## hunk 还原

- `0..3`：按 map 的 `[offset, offset+len)` 及 `compressors[n]` 解压，结果长度为 hunkbytes。
- `4`：读取原始 len 字节。
- `5`：引用逻辑偏移 `offset*hunkbytes` 的数据；顺序写出实现须支持该引用方向。
- `6`：需要父镜像及相应引用实现，不按普通 hunk 处理。

压缩长度由 map 提供，不另扫描 zstd 帧猜长度。输出逻辑长度须等于 logicalbytes。

## 完整性校验

自有解码器在还原过程中检查 map CRC16、数据 hunk CRC16 及逻辑长度。
SELF/PARENT 引用项不携带独立数据 CRC，不将其零值作为校验失败。
有完整逻辑数据时可核对 `rawsha1`；已改变扇区布局的 ISO 不直接与该摘要比较。
可靠工具已有通过记录时复用，不为文本提取追加整盘哈希。

## 字段注意事项

- hunkbytes 从头字段读取，不套用 DVD 默认值。
- compressors 按四字节大端转 ASCII，不按整数值选择压缩器。
- metaoffset 指向元数据，首个数据 hunk 由 firstoffs 定位。

## 数据扇区位移

extent 读取结果不符预期时，先核对扇区模式和用户区起点；高熵不证明整盘加密。
确有插入扇区时，用多个独立文件的已知明文计算 `实际扇区 − 表内 extent`，
一致差值结合文件结构确认位移，单个短魔数不足以定值。

位移仅应用于受影响区域；目录位于插入点之前时保持原地址。修正后核对相关文件结构。
工具 `ccdimg.py extract --shift <已确认扇区数>`；不按文件偏移是否为 2048 倍数判断位移。

### CloneCD 用户区

| 写法 | 用户区起点 | 判据 |
|---|---|---|
| `TRACK 1 MODE1/2352` | 扇区 +16 | `.cue` 或 `.ccd` 里的 `[TRACK] MODEDATA` |
| `TRACK 1 MODE2/2352` | 扇区 +24（Form1，含 8 B 子头） | 同上，并核对扇区子头 |

MODE2 Form1 按 +16 读取会偏差 8 字节；先核对模式再判断位移。
`scripts/ccdimg.py` 按 CCD track mode 选择用户区起点。
