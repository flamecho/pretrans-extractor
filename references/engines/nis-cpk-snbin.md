# BROCCOLI×NIS Switch 移植（CRI CPK 6 件 ＋ `sn.bin` LZSS 剧本）

**识别 → 容器 → sn.bin 解压 → 记录格式 → 成行 → 坑**

## 识别
- Switch NSP；RomFS 根**平铺 6 个 CRI CPK**：`bg` / `bgs` / `bgm` / `se` / `vo` / `sys`
- 另加 `font48.xtx`＋`font48b.xtx`（各带 `_eng` 变体）、`movie/`、**`sn.bin`**
- **没有 `novel.cpk`** ⇒ 见到这 6 件套就按本册走（剧本在 `sn.bin`）
- 实例：うたの☆プリンスさまっ♪ All Star（`0100B3E0149FC000`）

## 容器
1. `nsp_split.py` 拆 PFS0；Program NCA 本作 **Key Generation 13**（`merged.keys` 可用）
2. `nstool -x <dir> <nca>` → `0/` exefs、`1/` romfs、`2/` logo
3. **CPK 特例**：`EnableFileName=0` ＋ `TocOffset=0`
   - 无文件名、无 per-file 偏移；只有 ITOC 的 `CpkItocL/H`（`ID/FileSize/ExtractSize`）
   - 偏移＝**ID 升序 + Align(2048) 累积**；**唯一硬校验：累积和 == `header.ContentSize`**
4. 成员性质：`bg`=CRILAYLA（`10 00 00 00`=单层 xtx／`50 00 00 00`=多层图层表）；`bgs`=**全部同尺寸 xtx**；`bgm/se/vo`=HCA；`sys`=UI

## NSO 解包（关键：别再误读头）
```
0x0C flags ｜ 0x10/0x14/0x18 text.file/mem/size ｜ 0x20/0x24/0x28 ro.* ｜ 0x30/0x34/0x38 data.*
0x60 text.comp / 0x64 ro.comp / 0x68 data.comp   （flags bit0/1/2 = 段压缩，LZ4 block）
```
`scripts/nso_x.py` 一条命令出平铺镜像。**早前把 `0x18` 当 file offset 导致 LZ4 全失败**。

## `sn.bin` 解压（逆向自 `main:0x4FD80`）
```
[0x00] u32 解压尺寸   [0x04] LZSS 流
ring=0x1000，pos 初值 0xFEE；每 8 token 一个 flag 字节（LSB 优先，1=literal，0=match）
literal: 1B 原样
match  : 2B → idx = b0 | ((b1 & 0xF0) << 4)     # 12bit 环下标（不是距离！）
               len = (b1 & 0x0F) + 3            # ★+3，读成 +2 会全崩
         从 ring[idx..] 顺次取，边取边写 ring[pos]
```
本作 2,305,613 B → **6,020,768 B**（`sn.dec` 平铺）。

## 平铺内容 / 记录格式

| 区域 | 内容 |
|---|---|
| 0x0000–0x1800 | 头表（offset 对 + 场景条目指针） |
| 0x1800–0x2800 | 场景选择菜单表（33 条）＋debug 项 ⇒ **UI，不收** |
| 0x2800– | 剧本流 |

| 记录 | 字节 | 说明 |
|---|---|---|
| 开框 | `4F 0D 00 <flag u16>` | flag=1 表示后面有名札 |
| 名札 | `46 0D 00 <name> NUL` | 丢弃；可整表导出做 cast 核对（本作 112 种） |
| 正文 | `… FF FF <u16> <cp932> NUL` | 前导变长 ⇒ 用 `FF FF`+u16 当锚点 |
| **收框** | `4A FF FF 6A FF FF FF FF 49 FF FF FF FF` | **一次点击＝一行**（`9F FF FF …` 变体极少数） |
| 框内改行 | `%N` | **换行≠换页** ⇒ 删掉合并，单版本交付 |
| 选项 | `01 00 <idx u16> 00 00 <u32> <文本> NUL` | 一行一条 |
| 章题扉文 | `4F 03 00 00 <文本> NUL` | 直接上屏 |
| 主角名 | `●●●○○○`／`●●●`／`○○○` | 占位符 ⇒ inline 替换 |

## 坑
1. NSO 头字段序错 ⇒ 解压全失败（先按 switchbrew 对齐再动手）
2. match 是**环下标**不是距离；长度 `+3`；环起点 `0xFEE`
3. `%N` 是**框内改行**，当主角名替换会变成「春歌デビューおめでとう」这类病句
4. 引号会跨点击失衡（邮件把 `『…』` 拆到 2〜3 次点击）⇒ 属源数据，**不要为配对去合并记录**
5. `bgs.cpk` 1849×130,592 B 全是 xtx、`sys.cpk` 106 成员零日文 —— 都不是剧本

## 复用工具
`scripts/nsp_split.py`、`scripts/cpk.py`、`scripts/nso_x.py`、`scripts/utapri_as_extract.py`（LZSS＋记录解析＋占位替换）
