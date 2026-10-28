# VSC · vl_file（PAC/MemPack + vlLZSS + TML 字节码）

> 实例：召しませ浪漫茶房 ＝ SIMPLE2000 Vol.98 THE 浪漫茶房（`SLPM_657.37`, PS2, 2004-10 / 廉価 2006-03,
> D3PUBLISHER 发行・**ヴァンテアンシステムズ（VSC）** 开发）。
> 同社后作 `ラスト・エスコート2` 已换 `VDP + LSB`，见 `vsc-vdp-lsb.md`；两者**不通用**。

## 1. 识别特征

| 看什么 | 值 |
|---|---|
| ISO 根 | `SYSTEM.CNF` + `SLPM_657.37` + `DATA/{ACTION,ETC,TML,SHOP,PICK,GALLERY,EVGP}/` + `MOVIE/VSC_S.PSS` |
| 归档 | `*.PAC`；**无魔数**，头 = `u32 ver`（1=vlLZSS 压缩 / 0=无压缩）+ `u32 解长` |
| 脚本 | `DATA/TML/TMLPACK.PAC`（ver=0）内 306 个 `.TML` |
| 文本 | 载荷字节全在 `0x21–0x7E`，`+0x80` 即 EUC-JP（JIS 7bit） |
| ELF 旁证 | 源码路径串 `D:\Proj33\SOURCE\system\vl_file\vlCompress.c`、`tag_vlLZSS`、`TmlDecode_Load/GetCommand` |

## 2. 容器
```
vlLZSS 型 PAC：u32 ver=1 | u32 解压长 | 流
  解压后 = MemPack：u32 count | count×32B{name[16] | u32 size@+0x10 | 8B 0} | 数据（按 size 累加，无对齐）
无压缩 PAC（TMLPACK）：u32 0 | u32 总长 | u32 count | 12B 0 | count×32B（同上） | 数据
```
`vlLZSS`（`vlCompressDecode@0x185DF0`）：ring 4096、写指针初 0xFEE、flag 每 8 项 LSB 先行（1=字面量）、
token 2B：`off = b0|((b1&0xF0)<<4)`、`len = (b1&0x0F)+3`、**拷贝源 = ring[(off+k)&0xFFF]（绝对位址，不是回退距离）**。

## 3. TML 命令流
`u32 op = 0xFF000000|opcode`（字节 `lo hi 00 FF`），参数紧随；77 项表在 ELF `0x1C2F90`（`[u32 cmd][u32 fn]` 二分）。

| op | 语义 | 参数 |
|---|---|---|
| `0x1F4` | 正文一行 | `u8 len`+len（len>0x40 截断） |
| `0x1F5` | 中央消息（扉文/全屏旁白） | 同上 |
| `0x012C/0x012E` | 名札（主/副窗） | `u8 color`+`u8 len`+len |
| `0x0130/0x0131` | 插入主角**姓**/**名** | — |
| `0x01F6` | 枠内改行（不点击） | — |
| `0x01F7` | 枠末 = **一次点击** | — |
| `0x0192/0x0191` | 选项（首/续） | `u8`+`u32 id`+`u8 len`+len |
| `0x0190` | 跳转 | u32 绝对偏移 |
| `0x0002` | 空指令（`GetNextCmd` 特判跳 5B） | 1 |

## 4. 成行
- 一次点击 = 一枠（`0x1F7`）；`0x1F6` 与连续 `0x1F4` 直接拼接。
- 窗口 3 行 × 18 全角（`EvMsgWin_LineFeed` 行号上限 3 `slti 4`；成品行宽断崖 54）。
- 判「下一指令是否续文」的白名单 `_IsNextCommandMsgCheck@0x197910`：`{0x1F4,0x1F5,0x1F6,0x130,0x131}`。
- **无「换页/框内等待」并列点击指令 ⇒ 单版**。

## 5. 易错
1. **`.TML` 不是独立场景，是一条流的任意切块**（切点会落在指令/字符串中间）⇒ 必须按包内顺序**拼接后整体解析**；
   逐文件解析每个切点丢 1 条正文。
2. 别按 cp932 解（是 JIS 7bit）。
3. `0x1F6`（改行）不是点击；`0x1F7` 才是。
4. 主角名走 `0x130/0x131` 宏，字面「甘味/千歳」也可能出现在文本里（本作 0 处误伤）。
5. 商店/料理/栽培/名入力/回想标题等系统串在 **ELF**（cp932，219 条），不在 TML；`c_data.dat` 是道具名表。
6. 包内 00 填充块要跳过（否则走查失步）。

## 6. 工具
`scripts/roman_vl.py`（vlLZSS+MemPack）、`scripts/roman_extract.py`（TML→成品）、`scripts/check_text.py`。
