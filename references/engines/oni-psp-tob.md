# Idea Factory/Otomate 自研 PSP「oni」引擎（PSPFS_V1 ＋ DSARC ＋ **STS.DAT/.tob**）

> 2026-10-17 立（**O＊G＊A 鬼ごっこロワイアル ハンターは孤島で恋をする** / `ULJM06299` / vndb v11960）。
> 同引擎同容器形态亦见 **学園ヘタリア（Gakuen Hetalia）** 等 Otomate 2012–2013 PSP 作（社区报告 STS.DAT 内同款 `.tob` 脚本）。
> 工程内部代号 = **`oni`**（EBOOT 断言串 `d:/projects/oni/prog/src/…`）。

## 1. 文件层

```
PSP_GAME/USRDIR/
  DATA.DAT         PSPFS_V1，19,171 条（本作）＝ 素材全部
  DATA2.DAT        INSDIR 里的 `\0PGD` 加密同构包（安装用副本，子集；scripts/pgdecrypt.exe 可解）
  STS.DAT          ★剧本文本（271 个 tob 脚本）
  STS_DEF.TOB      脚本用定义表（无正文）
  STS.MAO          小块定义（tob 头 + 0x7F 填充数据，无正文）
  #LAYOUT__.PSP    构建清单（小写名，CRLF）——与 PSPFS 条目 1:1，可当白名单
```

- `BOOT.BIN`＝**3.1 MB 全零**（非明文 ELF）；`EBOOT.BIN`＝`~PSP`，`scripts/pspdecrypt/pspdecrypt.exe` 一次通过
  （`tag D91613F0 type 2`）。EBOOT 里有用的只有**字面量表**（名字默认值、文件名模板），剧本不在里面。
- ⚠ `identify.py` 会把本 `.chd` 误判成「KiriKiri XP3」（0x9ddd 处的巧合魔数）——**先看 `MComprHD` 头**。

## 2. PSPFS_V1（本作变体）

| off | 宽 | 内容 |
|---|---|---|
| 0x00 | 8 | `PSPFS_V1` |
| 0x08 | 4 | 条目数 |
| 0x0C | 4 | 0 |
| 0x10 | 32×n | `name[24]` ＋ `u32 size` ＋ `u32 offset` |

- 数据 0x800 对齐；**条目按构建顺序排列，offset 无序**（不能当顺序表）。
- 注意与「Disgaea 型」52 B 条目不同：本作是 **32 B**。

## 3. DSARC（.DAT 包内层）

- `DSARC FL` + `u32 count` + `u32 0`，随后条目 **`name[N]` + u32 size + u32 offset**，`N` 逐容器不同（本作见 40 / 48）。
- ★**条目步长要自证**：用「名字全为可见 ASCII 且 size>0、offset ≥ 表尾」四条件遍历候选步长（40/48/56/64…），
  否则会静默取到 size=0/offset=0 的假解（本次首轮就踩了）。
- 外层 `.DAT` 常见形态：`[u32 1][u32 0][u32 0x0C]` + **gzip**（FNAME 恒为 `_gz_div.tmp`）；多成员 ARC（INITARC/STAYARC 等）
  是**连续 gzip 流**，须用 `decompressobj().unused_data` 循环，别只解第一个。

## 4. STS.DAT / tob（**正文**）

```
STS.DAT = [0x1540 B 头部 blob（0x7F 填充的绘图数据）] + 271 × tob
tob     = [u32 'tob\0'][u32 size][u32 ver=1][u32 n]
          [u32 strOff][u32 0x28|0x2c][u32 0x20][u32 strEnd]
          + 代码区(0x20..strOff) + 字符串表(strOff..strEnd)
```

- **字符串表**：4 字节对齐的 NUL 结尾串，**全字节 XOR 0xDA**，内容 cp932。
  - ★**假名一律半角片假名**（0xA1-0xDF，`｡｢｣､･` 也是半角）；汉字/`……`/`【】`/`――` 全角。
  - 半角→全角必须**合并浊点**：`ｶ`+`ﾞ`→`ガ`，`ﾊ`+`ﾟ`→`パ`（漏了就满篇 `カ゛`）。
  - 表首 4 B 是残留（`ﾈe`/`ｰ)`…）——**丢弃首条 ≤4 B 记录**。
- **表内三类条目**：① `*.vag` = 该文本框语音（**排在框文本之后**）② `./../tob/x.tob`、`x.sts` = 脚本名/标签命名空间
  ③ 正文（可带 1 字节样式码 `s`/`i`/`b`/`.`）。
- `<switch_err> ○○ニ分岐シテキタ` = **选项组的分岐标记**：其前的连续短串＝选项，逐条成行。
- **顺序**：STS.DAT 内的 tob 排列即流程序（`d00` → `prologue00/01` → `st_01`…`st_08` → `st0900/1000<角色>` → `st_omake_01..10`）。
- 代码区是变长指令流（`03 01 07 00 <u16>` 一族，`04/02 xx` 为其它），**本次未逆 VM**——成行靠「语音 + 引号」启发式。

## 5. 成行 / 交付要点

1. 一次点击＝一行：同一框内的折行串**直接拼接**（`「OGA･女子中学選手権､第3試合!` + `賀茂泉中対､…` + `…参ﾘﾏｼﾀ!｣`）。
2. 框界：`.vag` 且引号已闭合 ／ 引号深度归零且以 `」` 收尾 ／ 叙述句 `。！？` 后紧接 `「`。
3. **引号跨框**是常态（源侧还会漏写 `」`，全书净差 3 个）⇒ 后处理 `rebalance()`：先按上限（4 段/300 字）合并，
   仍不平衡再补 `」`/`「`；本次 68 行（0.34%）被补。
4. 名字：`白雲` + `＠`（可变名）⇒ 默认名取 **EBOOT `InputName.cpp` 区的 `【白雲%s】`** 旁字面量（本作＝`美咲`）；
   行内替换后**去掉名前的空格**（源里写成 `白雲 @`）。
5. 排除：`d00`（启动路由）、`sts_deb`（调试菜单）、`sts_omake`/`scene_play`/`sts_cmn`（系统菜单）、`r1_t1_01`（α版测试场景）。
6. `.SP2`＝UI 版面（`*.tga` 引用 + 0xFFFF 分隔属性，**无正文**）；`.MPB`＝`MAP\0` 地图；`.MTN/.MOC/.GIM`＝Live2D/贴图。
   本作**无用語辞典**。

## 6. 工具

`scripts/oga_sts_extract.py`（STS.DAT → 全文本，一条命令；含半角假名转换、表头残留剔除、选项组、引号补齐）。
