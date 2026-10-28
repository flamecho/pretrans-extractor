# Koei PS2 「HD/BIN + PACK」归档（アンジェリーク エトワール 系）

> 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。
> 首见作品：**アンジェリーク エトワール（PS2, SLPM_657.15, 2004-08, Ruby Party）**。
> 与 `engines/koei-cdar.md`（CDAR v2/v4）、`engines/koei-pasc.md`（pasc 节点流）**不同族**。

## 1. 盘面

```
ISO9660
├─ IOP/                    IRX 模块
├─ MOVIE/*.PSS
├─ SLPM_xxx.xx             主程序（MIPS ELF, stripped）
└─ DATA00..04.HD + .BIN    ← 本族归档（可能有多组，编号/组数不固定）
```

## 2. `.HD` / `.BIN`（已闭环）

- `.HD` = **u32 LE 尺寸表，逐条，无偏移字段**。
- `.BIN` = 条目顺序拼接，**每条按 2048（0x800）对齐**；对齐填充不参与尺寸。
- 自校验：`Σ ceil(size/2048)*2048 == len(.BIN)` —— 命中即证明表未被截断。
- **条目 #0 通常是 `FILENAME.LST`**（cp932、CRLF），行数 **== 条目数**，索引 i 即文件名。
  注意：**不是每组都有**（本作 DATA03 的 #0 是二进制，此时无名表）。
- 复用工具：`scripts/etoile_unpack.py`（`--manifest` 出清单，`--dump` 抽成员）。

## 3. `PACK` 容器

```
0x00 'PACK'
0x04 u32 nameLen
0x08 name[nameLen]        ← 变体①：常为 0；变体②：游戏自研 2 字节字符码（非 cp932）
8+nl u32 A                 = 头部长度
+4   u32 B                 = 表长度
+8   u32 dataOff           = A + B   （恒等式，全部样本成立）
+12  u32 dataSize
+16  u32 (0/1)
+20  u32 count             ← 成员数在这里（**第一字段不是 count**）
+24  u32 recSize = 0x40
+28  u32 0
+32  table[count × recSize]
dataOff.. 成员数据
```

- **成员记录（变体①，DATA00/01）**：`name[48]`(cp932,NUL 填充) + `u32 off` + `u32 stored` + `u32 decomp` + `u32 step`。
  自校验：逐条 `off_{i+1} == off_i + stored_i`，末条 `off+stored == dataSize`；`Σstored == dataSize`。
- **变体②（DATA02/03）**：同样的头部，但 64 字节记录**整块是自研 2 字节字符码**，取不出 off/size ⇒ 成员表未解。
- `step` ∈ {1,2}，与 `decomp ≈ stored × 2` 同期出现 ⇒ 疑为「位平面数」。

## 4. 内层成员数据

- **★ `step` 字段＝压缩开关（3rd 结论，已实证）**：`step=0` ⇒ **原样存储**（decomp 恒 == stored，
  数据直接以 `TIM2` / 嵌套 `PACK` 开头）；`step∈{1,2}` ⇒ 压缩（1 中位 1.69×、2 中位 2.86×，极端 141.6×）。
  本作 DATA00/01/04 共 6,590 成员：step0 = 3,627、step1 = 901、step2 = 2,062。
- 压缩成员**前 4 字节 = 有效字节数（== stored−4）**，流从 +4 起：`black.tm2` `7d 08 00 00`=2173 ✓、
  `E04_03.BIN` `bf 2b 00 00`=11199 ✓、`きらきら2.tm2` `df 0b 00 00`=3039 ✓。
- 流内可直见**字面量段**（`black.tm2` 里 `2c 00` 后紧跟 48 字节 TIM2 头），另有 `f7f7 f8f8 … ffff 0000`
  这种「递增 16 位表」⇒ 疑为长度/位宽表。
- 已排除：zlib / raw deflate / 标准 LZSS(4 变体) / LZ4 / LZP2(Koei DW5 系) / 64 B 头块循环 XOR /
  纯转置(step 2–32) / CDAR / `0x1F` 扩展长度 / 先转置再解码 / 整条目从 0/8/0x18/0x28 起整体解码 /
  **MTF-chunk 家族 216 组参数（双硬条件最好 1/60 命中，正式结案）**。
- ELF 侧：MIPS32 **小端 R5900**（`sd`=0x3F、`sq`=0x1F，须用 `CS_MODE_MIPS64` 反汇编）；
  全段仅 **1 条 `srl …,5`**（`0x15eb14`，base-6 运算）⇒ 解压器不是「`>>5`+`&0x1F`」族。
  链路已走出：`0x177200`（拼 `"DATA00"`）→ `0x155050`（`malloc(0x68c)`＋读 HD/BIN）→ `0x154cb0`（真干活）。
  ✅ 字符串引用点（gap 3–4 的 `lui+addiu`）：`0x14b114`/`0x177204`/`0x177258`/`0x1848fc`/`0x1aa4cc`/`0x1aa504`。
- **续做入口**：Ghidra 导入 → 在 `0x155050`/`0x154cb0` 建函数反编译 → 从 `0x154cb0` 的 8 个被调
  （`0x14af00`/`0x14a910`/`0x12dd50`/`0x14a930`/`0x14a2f0`/`0x12eb50`/`0x12dfd8`/`0x154750`）里找
  「读 u32 长度 → 循环 lbu/sb」的解压器；用 `black.tm2`(2177→308288) 与 `index.lst`(44→50) 双端校验。

## 5. 本作靶子

- 剧本在 **DATA02**：`s01jul_*`…`s18vic_*`（18 守护圣线，各 145–153 条）、`s99sys_*`(176)、`sysM_*`(213)、
  `A_EVENT_*`、另有 `resident_script.PAK` / `scriptlist.PAK` / `sptPlaceMessage.PAK` / `sysM_SysMes.PAK`。
- DATA00 = 系统类（`backlog.PAK` / `command.PAK` / `font_00.FAC` / `kutipaku.PAK` / `PS2_MesWin.PAK`）；
  DATA01 = 事件与贴图（`AE*_*.PAK`、`*.tm2`、`namesNNN`）；DATA03 = 无名的 13,463 条（6,642 PACK）；
  DATA04 = 贴图（TIM2 明文）。全 5 组 **SJIS 平假名连续段命中 0** ⇒ 正文一律在内层，不在明文处。

## 6. ★ 解压算法（已破解，2026-10-18 第四轮）

**PACK 成员取用器 = `FUN_00150640`**（ELF `SLPM` 里唯一引 `0x4B434150`="PACK" 小端常量的地方）：
`nameLen = hdr+4`；`count = hdr+nameLen+0x1c`；`table = param_1[2]`（V1 = `hdr+nameLen+0x28`）；
记录 `name[48] + off@0x30 + stored@0x34 + decomp@0x38 + type@0x3c(&0xf)`。

- `type 0` → `memcpy(dst, src, decomp)`（原样）
- `type 1` → `FUN_00142c80`（LZSS）：
  `[u32 maskBits][mask (maskBits+7)>>3][字面量 1B / 匹配 2B 交错]`；
  mask 字节内 LSB 先，**bit=1 字面量 / bit=0 匹配**；token u16 LE `dist=tok>>4`（0=结束）、`len=(tok&0xF)+2`；
  4096 环形缓冲、写指针从 1 起（位置 p ↔ out[p-1]）。
- `type 2` → `FUN_00142a20`（Huffman 类，先建 256 项码表）：**用 unicorn 模拟执行**最省事。
- ⚠ unicorn 必须 `UC_MODE_MIPS64`（`sd` 在 MIPS32 模式异常）；置 `$gp=0x1e40f0`、`a0..a3=(src,len,dst,cap)`。
- 工具：`scripts/koei_dec.py`（type1 纯 Python）、`scripts/emu_dec.py`（types 1/2 模拟）；
  整包解出并扫文本的那步没留脚本 —— 用 `identify.py` 定位后按 `G1T`/`tm2` 魔数批量切即可。
- 校验：`index.lst` 解出 `<CG>\r\nyuki.tm2\r\n</CG>…<ANM>\r\nyuki.BIN…`（逐字节命中）；
  `きらきら2.tm2` → `TIM2`；`E04_03.BIN` → `ANMB`；DATA00 3,563 成员 **0 失败**。
- ❌ 未通：**DATA02/DATA03 变体**（记录为 64 字节纯 2 字节字符码、无 off/size 字段），剧本仍在里面。

## 7. ★★ DATA02/03「PACK H2」—— 已完全破解（2026-10-18 第五轮）

> 前面 §4–§6 关于「DATA02 变体未通」的结论**作废**。真正原因是把 `name` 区当成了「文件名」，
> 实际上 **它是密钥**。

### 7.1 布局

```
+0x00 'PACK'
+0x04 u32 nameLen
+0x08 byte[nameLen]  KEY（同时也是"名字/签名区"，每文件不同）
+0x08+nameLen  u32 A(=记录起点), B(=count*64), doff(=A+B), dsize, 1, count, 64, 0
+A    记录表 count × 64（纯名字，**没有** off/stored/decomp/type 字段）
+doff 数据区 dsize 字节
```
全量 4170 个 PACK：`A+B==doff && doff+dsize==条目size && count*64==B` **零误差**。

### 7.2 解码（三步）

1. **XOR**：`plain[i] = seg[i] ^ key[i % len(key)]`（key 每段从 0 重新计）
2. **首 u32 = v**
   - `v == segLen-4` → **type2**（MTF+RLE，`FUN_00142a20`）
   - 否则 `v` 是 **maskBits** → **type1**（LZSS，`FUN_00142c80`）
3. 输出必须以 `SCPT` 开头（否则换另一种再试）

数据区可含**多段**，每段 `[u32 v][stream]`，逐段推进。

### 7.3 校验

| 条目 | key | v | 类型 | 输出 |
|---|---|---|---|---|
| A_EVENT_ENDING / HAKKEN / SONOTA | 24 | 503/249/756 = ds-4 | 2 | `SCPT` |
| s99sys_1a_02 | 24 | 3796（maskBits） | 1 | `SCPT` 22,384 B，含 197 段假名 |

### 7.4 SCPT 文本块

```
(names029|nameh000|B156_0_0|A_HIZASI|...)\x00\x00\x00\x00<SJIS 文本，\n 分行>\x00
```
- `namesNNN` / `namehNNN` = 说话人 ID（**名字表不在 SCPT 内**）
- 取文本 → `\n` 合并为一行 = 一个 message box

### 7.5 工具

- `scripts/etoile_script.py`：整包 → SCPT（`unpack_entry`）
- `scripts/etoile_text.py`：SCPT 目录 → 纯文本
- 依赖 `scripts/emu_dec.py`（unicorn 模拟 type1/type2）、`scripts/etoile_unpack.py`（load_pair）

### 7.6 全量结果（2026-10-18）

- 4,170 个 PACK → **4,167 成功**；文本 **10,908 行 / 848 KB**；`check_text.py` **PASS**
- 3 个未解：`illegal_name.PAK`（解出名字样例非 SCPT）、`scriptlist.PAK`（ASCII 清单）、
  `resident_script.PAK`（87 成员系统脚本，key 40 字节时首 u32 非法 —— 未攻克，属系统文本，交付不需要）
- **35 个 ≥3 KB 的 0 行文件全是 `sysM_*`（系统菜单/UI）** ⇒ 交付口径不收，正常
- 清洗：`▼∋⊆∈`(0x81A5/B9/BA/B8)=框分隔拆行；**`#t1`/`#t2`(ASCII)=分页，也拆行**；
  **`#c0`/`#c9`=换色码，删码；`#c9名前#c0` 整行=带色说话人名，剔**；
  `\n` 合并；行首 `[主人公]` 删；内联 `[主人公]`→`エンジュ`
  （官方公式名，本作是系列首部不默认叫 アンジェリーク 的）；`システムメッセージ`/`ﾎﾞﾘｭｰﾑ`/`本編用アイテム` 三行剔除
- ★ 教训：**控制码不只有 SJIS 高位符**，还有 `#t1` 这种 ASCII 形式；「含日文即台词」的过滤器拦不住，
  必须单独扫 `#[a-z]\d` 与 `#c\d`。
