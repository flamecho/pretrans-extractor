# KID 自研 `mlk/ADV`（ARC0 归档 ＋ 文本 DSL `.cpp`）

> 作品：**水の旋律 ～協奏曲～ / After Story -Sweet Concerto-**（PC 2006，KID，CD-ROM）
> 工具：`scripts/mizumelody_arc.py`（解包）、`scripts/mizumelody_text.py`（成行）
> 报告：`提取结果/解析报告/水の旋律 ～協奏曲～_解析报告.md`

## 1. 母本
CloneCD（`.ccd/.img/.sub`）→ 2352 B/扇区，剥 16 B 同步头取 2048 B ⇒ ISO。
光盘内每个程序各带一份归档：`ADV/SRC/ARCHIVE.BIN`（本篇 969 条）、`INU/`、`CALENDAR/`、根 `ARCHIVE.BIN`（MENU.EXE）。

## 2. ARC0 容器

```
0x00 "ARC0"
0x04 u32 count
0x08 保留块 0x10000 B（三份归档此块逐字节相同；首 0x100 也参与 XOR）
0x10008 索引 × count，每条 268 B
        记录： name[256] + u32 size + u32 offset + u32 flag(0x201)
数据区起点 = 0x10008 + count*268，条目首尾相接（offset 链自洽）
```

条目类型：`.tga`（纹理）/`.cpp`（脚本）/`.txt`（config）/`archiver2.exe`（打包器本体）。

## 3. 双重混淆（都可完全还原）

| 层 | 规则 | 代码依据（`ADV.EXE` VA） |
|---|---|---|
| 字节混淆 | **每段的前 0x100 字节 `^= i`**（i = 段内位序 0..0xFF），其后原样 | `0x45EE10`：`xor byte [esp+eax+0x158],al / inc eax / cmp eax,0x100 / jb` |
| 压缩 | **zlib（deflate）**，`78 01` | 静态链接 zlib 1.2.2；`uncompress` 路径 `0x49B2B0` |

- 索引记录同样先按位序 XOR 再解析（否则名字全是化け）。
- **无 per-file 密钥、无链式依赖** ⇒ 任意条目可独立解密（随机访问）。
- 判定口径：`78 01` 头 + 首 0x100 字节 XOR 后能整段 inflate 无残留。

## 4. 脚本 DSL（`.cpp`，cp932）

命令表在 `.rdata` `0x24055C` 起（NUL 分隔）：
`exit l p lock pop dump scene thumb title_load clear_log uncheck print push wait fade call movie bgmplay bgmstop sestop layout mes snow mode erase set_save load create insert set_camera draw priority select parent point line seplay path set_buffer translate rotate scale button rect bind`。

| 命令 | 语义 | 成行 |
|---|---|---|
| `mes(名, 文[, 声])` | 一段文字入文本框 | 一行（名札丢：独立 `name_window` sprite） |
| `p()` | キー入力待ち **＋改頁** | 框边界 |
| `l()` | キー入力待ち **改頁なし** | 同框下一段（**双指令 ⇒ 双版对照**） |
| `select("文","标签",…)` | 选项菜单 | 一行一条按序 |
| `scene(TITLE_*)` | 存档槽标题串（`strcpy` 进结构 +0x1284；仅调试打印） | **不上屏，不收** |
| `print()` | 调试打印 | 不收 |

- 段内 `\n`＝同击内排版换行 ⇒ 合并。
- 本作无名字宏（主角固定 白石陽菜）、无用语辞典、无文本型扉文（场景卡是 TGA 图）。

## 5. 结果
53 个剧情脚本 → 3,107 行（正文 3,017 ＋ 同框分段 43 ＋ 合并 7 ＋ 选项 40）；`check_text` PASS。
