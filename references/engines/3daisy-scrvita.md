# 3Daisy 自研（SCRVITA / .tbl+.pak / .psb）

> 从 `engines.md` 拆出。路由/一句话索引见 `../engines.md`；主索引见 `../MEMORY.md`。
> 定案作：**ヴァルプルガの詩（PSV PCSG00768，3Daisy／发行 PROTOTYPE）**。工具 `scripts/valpurga_extract.py`。

## 容器
- 资源前缀按平台：`SCRVITA/` `CGVITA/` `SYSCGVITA/` `PCMVITA/` `EVENTVITA/` `BGMVITA/`（PC/PSP 版应为 `SCRPC`/`SCRPSP` 等）。
- 数据 = **`.tbl`（索引）＋ `NN.pak`（数据）** 成对：`psvscr00.pak`(剧本) / `psvsys00.pak`(系统) /
  `psvcg00.pak` / `psvpcm00.pak` / `psvvoice00.pak`；命名模板 `%s%02d.pak`、`%s00.pak`、`%s.tbl`、`%s%d.fnt`、`%s%d.pro`。
- 字体 `minp32/mdnp32/gothp32/mgothp32` ＋ `.pro`；另有 `merged.pro`、`*.psb`（E-mote 风）、`*.pt2`（图像）。
- **`.pak` 内容为明文 cp932**（`psvpfsparser` 解 PFS 层后）。`.pak` = **0x800 字节头** ＋ 脚本序列。
- `.tbl` 头 `u16 ver 0x0150 | u16 hdr 0x20 | u32 count | u32 0x00010800 | u32 0xff | u32 id`；
  体熵 ~7.1 → **疑压缩/位打包，未解析**（无碍：见下「脚本定位」）。
- `.pak` 里 **90 个脚本**（本作），按 **0x800 对齐**，以脚本头 magic 定位。

## 脚本头 / 命令流
- 脚本头 **16 字节**：`u32 LE magic 0x00011804 | u32 checksum | u32 BE stream_off | u32 BE ?`
  - 命令流起点 = 脚本起点 ＋ `stream_off`；**脚本用 magic `04 18 01 00`（0x800 对齐）定位，无需 `.tbl`**。
- 命令流 = token 序列：
  - token = `00 <u8 len> <len 字节 payload>`（带参） ｜ `<单字节 opcode>`
  - payload[0]=`0x01` → `u32 BE` 整数（`f0 <int> f0` 形式可作「slot 选择」）
  - payload[0]=`0x02` → 字符串 `02 <u16 BE len> <len 字节 cp932> 00`
  - payload = `04` → **主人公名插入宏**（配合前面的 `f0 <slot> f0`；slot 6=姓 / 7=名）
- **字节全部按 token 解析到脚本末即严丝合缝**（自身即校验）。

## 成行（一次点击 = 一行）

| opcode | 语义 | 处理 |
|---|---|---|
| `0xf0`＋非空串 | 设文本框内容 | 串以 `「`/空格开头 → **新文本框**；否则续接当前框 |
| `0xb0`＋串 | 续接当前文本框（框内分段/换行） | 追加 |
| `0xf0`＋空串 | 清框（文本框结束） | **输出**当前框 |
| `0x01`＋串 | 标题 / 扉文 | 独立成行 |
| 串后 `09` | 调用函数（`_function`、`z_catsystem`） | 丢弃 |
| 串后 `30`/`0e`/`44`/`b8`/`b1`/`b7`/`ba` | BGM / 切场景 / 影片 / 跳转 | 丢弃 |

- **资源/函数名是纯 ASCII**（`_function` `bg00040` `bgm16` `se_138` `w_sio21823` `v/fin_00008` `z_catsystem` `prologue` …）
  → 用「串含非 ASCII 字符」一步过滤，稳健。
- 说话人 **inline**：名札与正文**同一串**（无独立 token），形如 `名前 「…」`／`名前 『…』`（邮件）／
  `名前 （…）`（心声·独白）／`mob名　そのN 「…」`（名札自带全角空格，如 `人狼一族の男　その一`）。
  分隔符半角 0x20 或全角 U+3000 → **去「名札＋空格」**，只留括号内容。
  判据＝`^([^「『（]{1,26}?)[ \u3000](?=[「『（])`（非贪婪取最早的「空格＋起始括号」；全身检 37 种/269 行）。
- 选项 = 以 `「` 开头、无说话人名的独立文本框（本作 83 条）。
- **不做「相邻重复行」去重**：实测相邻同文行全部来自**不同脚本位置**（= 两次点击 / 两个说话人，
  如 `金の犬 「……」` 与 `銀の犬 「……」`），去重即删真文本。判据＝每行记来源 token 偏移，SAME_OFF 才可去。
- 行内控制：`\n` `\N`（框内换行→合并）、`\c`（颜色→剔）、`\f`（翻页→剔）、`\<字母>`（剔）。
- 主人公名宏：`f0 <slot> f0` + `04 b0` = 行内插入名字；`04 f0` = 置名札并**开启新框**（清框）。
  默认名取自 eboot 名字输入表（`泉\0詩生\0`）；引擎通用宏（eboot 残留串「主人公の名前を『岡崎朋也』へ戻す」可证）。

## 排除
- `psvsys`/`psvcg`/`psvpcm`/`psvvoice` 不取（系统/UI/图/音）。
- eboot（SELF→ELF）串表含**他作遗留串**（如 CLANNAD 的「岡崎朋也」）→ 不作正文来源。
- 少量系统提示（如「クリア情報（システムデータ）をセーブしました」）随脚本输出，按需再剔。
- 德文诗节数据内为 cp932 西里尔 `в`/`о`（应为德文 `ß`/`ö`）→ 按**实际码位保留**（字体槽不可信 cp932）。

## 工具
- `scripts/valpurga_extract.py <dec 目录> <out.txt>`。
- 解密链（PSV）：`zzzrif.py`(work.bin→zRIF) → `pkg2zip -x`(容器层) → `psvpfsparser -i -o -z`(**PFS 层**)
  → `self2elf.py -k work.bin`(eboot)。详见 `../MEMORY.md` 铁律 11 与 `engines/psv-pfs.md`。
