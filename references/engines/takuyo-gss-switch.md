# Takuyo gss —— Switch 变体（`SCR 3.00` + LSDARC 内层压缩）

> 本家（PSV `SCR 2.00`）见 `../engines/takuyo-gss.md`；
> 路由见 `../engines.md`；主索引见 `../00-index.md`。
> ★ **脚本版本按文件头判，不可按平台推定**：同为 NS 版，`神さまと恋ゴコロ`＝`SCR 3.00`＋内层打包（**本册**），
> **`カエル畑DEつかまえて☆彡`＝`SCR 2.00`＋未打包**（⇒ 见 **`takuyo-gss-switch-scr2.md`**）。

## 第 3 作：神さまと恋ゴコロ（NS-JP, TAKUYO, TitleID `0100612019f12000`, vndb v10045）
- **源**：`<游戏 dump 目录>/[NS-JP]神さまと恋ゴコロ.nsp`（PFS0, 2.58 GB）。
  `hactool -t pfs0 --outdir=` → `.tik` + `f560bc…nca`(本体) ＋ 2 小 NCA。
  ticket `masterkey rev=0x10`；NCA `Encryption Type: Titlekey crypto`，head MasterKeyRev `0xF`。
  解：`hactool --keyset=_sw/prod_fixed.keys --titlekey=43b1a7f0f8da115461c3e315337ffdfa -t nca --exefsdir= --romfsdir=`。
  （tik[0x180:0x190] 的原值即 `--titlekey=`，hactool 会再解一遍。）
- **RomFS 特征**：`SCRDATA.BIN/.ARC`（脚本）、`SCRDATA.DAT/.H/.LST`（**旧 PC/PS2 遗留表，尺寸与索引不符，不可信**）、
  `BMPDATA/FONTDATA/WAVDATA/STAND.ARC`、`KAMI_OP*.MP4`、`o_*.csv`、`lsd.exe`(565 KB MZP)、`gss.exe`(0 B)。

### ① 容器同 LSDARC，但**内层打包**

```c
// 脚本容器结构，343 条；未打包 18 / 打包 325
magic[12]="LSDARC V.100" | u32 count | count×{u32 isPacked,u32 off,u32 unpackedSize,u32 size,name\0}
// off[i]+size[i]==off[i+1]（链累加，零差）；未打包项直接是 "SCR 3.00" 文本
// 打包项 = "LSD\x1a" + u8 enc + u8 pack + u32 unpacked_size + payload（payload 从 off+12 起）
```

| pack | enc | 条数 | 算法 |
|---|---|---|---|
| `H` | `N` | 266 | Huffman（头 256 项建码表，再按位流查表） |
| `D` | `W`×55 `N`×3 | 58 | 16bit 增量样本（5bit/样本：4bit 步长 idx + 1bit 符号） |
| `R` | `S` | 1 | RLE（GARbro 原版） |
- **参考实现**：`CialloAlone`/`Airahc` 的 `GalgameReverse` → `src/gss/gss_arc.cs`（morkt 骨架 + devseed 补全；
  GARbro 本家 `ArcFormats/Gss/ArcARC.cs` 的 `UnpackD/H/W` 全为 `NotImplementedException`）。
  已移植 `scripts/gss_codec.py`（含引擎常量表）。
- **★坑：`decrypt`(enc) 是**就地前向差分** —— 「前一值」取**已解密**值（引擎 in-place），
  用「原始前值」会出现前 2 字节对、其余全崩的假象（本作 `SC`+乱码）。`B`=字节/`W`=LE双字节/`S`=BE双字节，首元素取负。
- **验证锚**：解出必须 `"SCR 3.00"` 开头 ⇒ 343/343 命中。

### ② `SCR 3.00` 指令（与 `SCR 2.00` 只差头宽）

```c
"SCR 3.00"(8) + u32 A + u32 B
u16 opcode | u16 size（**总长，含 6B 头**）| u16 id | operand*<u8 type><data>
// type 0x00→1B 0x01→4B 0x02→2B 0x03→NUL结尾CP932 0x04→2B 0x05→4B 0x06→2B
```
（PSV 版是 `u16 op|u8 size|u16 id`＝3B 头；**size 由 1B→2B** 是唯一差别。）
按 size 前进，343/343 零失步。

### ③ 文本 opcode（本作）
- 收：`0x5a` 正文 25,925 / `0xfc` `%s` 正文 1,140 / `0xf0` 扉文 313 / `0x5c` 选项 853（`文本,FLAG`，取最后 ASCII 逗号前）。
- `0xfc` 的 `%s` 源＝其后 type6 槽位，**本作仅 `1802`(姓) / `0c02`(名)**；其余槽（`a403/00c0/8c80/5003/3803/04c0`）
  只在 `0x10c`（sprintf→槽，`PRG_NAME` 组名札、`PRG_BG` 组文件名）当**目标** ⇒ `0x10c` 不收。
- 串内：`\n`=框内换行（合并）、`\c`=控制码（删）。**以 `☆` 开头 = 制作备忘/SE 注记，引擎跳过不上屏 ⇒ 剔**。
- 名札：`0xfd(3803)`＋`PRG_NAME.SCR/NAME` 显示 `【名】` ⇒ 不加前缀、丢弃。

### ④ 顺序 / 排除
- 入口 `AUTOEXEC` → `Init.SCR/START` → `PRG_ROUTE.scr/START`；
  顺序＝按 `0x1e/0x1d/0x102` 调用图 **DFS 前序去重**（覆盖 326/343）。
  结构：`00_PROLOGUE → 09_25～09_27 → 各角色 _01 → L_00_* 共通 → L_0x_* → 10_03～12_19 → ED_* ／ *_23_END… → EVENT01-06 → 各角色本篇 → Z_* → COM_*`。
- 6 名攻略角色：IKUTO(如月征都)/KUON(高梨久遠)/KENGA(辻宮兼我)/SEIJI(笠原誠司)/SUBARU(東條昴)/SORA(日渡奏良)。
- **排除**：系统/演出（`AUTOEXEC INIT RELOAD PRG_* YURASHI TIME_PASS`）、UI（`SELECT SELECT2`）、
  无文本（`CERO EVENT01-06`）、**测试**（`SUNDAY`＝`あいうえお…`＋`手巣テスト…`）、开发菜单 `DEBUG`、
  回想/鑑賞（`01GALLERY 01SYSTEM 02SECRET_VOICE`）、迷你游戏 `02MINI_GAME`。
- **收录 extras**：`03OMAKE`(おまけ短編) / `CASE_1..6`(ＳＥＣＲＥＴ　ＲＯＯＭ) / `04WEB`(Web 短編)。
- **主角默认名**＝**水無川 愛梨**：`romfs/sjistext.csv` 首两行 `水無川,ShiftJISBinary[1],gss_emulate.cpp` /
  `愛梨,ShiftJISBinary[2],gss_emulate.cpp`（＝エミュ既定名表）。
- 笔误 1 处：`SORA_14` 全角 `（` 开 + **半角 `)`** 收（源字节尾 `0x29`）⇒ 整行定值修。

### ⑤ 工具
`scripts/gss_codec.py`（H/D/R + decrypt N/B/W/S）｜`scripts/gss_lsdarc.py`（索引＋逐条解包）｜
`scripts/gss_scr3.py`（SCR 3.00 反汇编）｜`scripts/kamikoi_extract.py`（驱动：DFS 排序＋成行＋`NAME_SLOTS`/`TEXT_PATCH`/`☆` 过滤/排除表）。
成品 28,231 行【PASS】；报告 `提取结果/解析报告/[NS-JP]神さまと恋ゴコロ_解析报告.md`。

## 第 4 作：SWEET CLOWN ~午前三時のオカシな道化師~（NS-JP, TAKUYO, `010028D0148E6000`）
- **源**：`甜小丑.xci`（6.14 GB）＋ 同捆 `甜小丑 补丁.nsp`（v196608）。
  ★ **XCI 为紧密打包、非 0x200 对齐**（secure 起于 0x17022，update/normal 各 17 B 空壳）⇒ `hactool -t xci` 报
  `XCI partition is corrupt!`（hfs0 头 hash）≠ 布局坏：**按 hfs0 表手切**，数据起点 = `base+0x10+n*0x40+strtab`，offset 相对该起点。
  本体 Standard crypto（keygen=2）hactool 直解；更新 Titlekey crypto（keygen=11）。
- **更新**：旧 hactool 对 BKTR 报 `BKTR section seems to be corrupted` ⇒ 用 **`nstool 1.9.2 --basenca <本体nca> --tik <tik>`**
  叠加（`-x /1/<file>` 可选择性取文件，免解 6 GB 全树）。卡带内 v65536 与 NSP v196608 的 `SCRDATA.ARC` **逐字节相同**
  （md5 `334512d1…`），两版均全量替换本体脚本（`48c0234d…`）＋附带原样副本 `100SCRDATA.*`；22 个脚本 32 处**误字修正**。
- **容器**：同 LSDARC V.100，但 **386 条全 `isPacked=0`**（本作未用 H/D/R 压缩，`gss_codec.py` 不必调用）。
- **脚本 `SCR 3.00`** 同格式，386/386 零失步。文本 op：`0x5a` 43,068 / `0xfc` 619（槽仅 `1802`姓+`0c02`名）/ `0xf0` 369 / `0x5c` 205。
- ★★ **换行 vs 换页（本族首个定案）**：串内只有两种控制码——`\n`＝**框内软换行（不点击，合并）** 1,102；
  `\c`＝**清框换页（等点击，断行）** 457。**无 B 类（不清框的框内等待）⇒ 单版**，不要出「双版对照」。
  铁证：`KOB_SWEET054` `でも毎日\c毎日\c私は\c…`＝逐词一屏；按同框续写会变 8–11 行，而全库单段最多 3 行。
- ★ **`0x5a` 固定名 / `0xfc` `%s` 互斥成对 371 处**：同句两版由 `0x22/0x21/0x23` 分隔，槽位替换后**逐字相同**且
  必为 `(0x5a,0xfc)` 相邻 ⇒ **按 op 型别去重**（禁用字符串相似度）；`(0x5a,0x5a)` 的 375 处重复是 `「…………」` 连续静默，**保留**。
- 名札＝`0x1e PRG_NAME.SCR <label>` 独立名字窗（`PLAYER`/`NAME`/`NAME_NON`）⇒ 整行丢、不加前缀。
- 文本内 **`@GameLast`＝玩家姓**（非 `%s` 槽，仅 `SIN011` 1 处）⇒ 替换默认姓；`≪…≫`＝强调引题号（原文用字）。
- 主角默认名 **橿野 柘榴**（`sjistext.csv` [1]/[2]）。无 用語辞典（`用語/辞典/豆知識` 0 命中）。
- **工具**：`scripts/sweetclown_extract.py`。成品 44,528 行【PASS】；报告 `解析报告/[NS-JP]SWEET CLOWN ~午前三時のオカシな道化師~_解析报告.md`。
