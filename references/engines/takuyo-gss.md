# Takuyo gss（LSDARC V.100 + SCR 2.00）

> 路由/一句话索引见 `../engines.md`；主索引见 `../MEMORY.md`。
> ★ **平台分册**：PSP（étude prologue）＝`takuyo-gss-psp.md`；NS（神さまと恋ゴコロ/ソラユメ等）＝`takuyo-gss-switch.md`（SCR 3.00 打包）／`takuyo-gss-switch-scr2.md`（SCR 2.00 未打包）。本册＝PSV（ひめひび・Cafe Cuillere）。

## Takuyo gss 引擎 —— LSDARC V.100 + `SCR 2.00`（ひめひび -Princess Days-, PSV PCSG01092）
- **平台/源**：PSV。源 zip 为 **pkg2zip 产物（PFS 未解，DATA/eboot 全高熵）**。
  解密：`work.bin`(512B) 经 `<psvdec>/rif2zrif.py` → zRIF
  （本作 <zRIF>，同 `games.json`）
  → `psvpfsparser.exe -i PCSG01092 -o dec -z <zRIF> -f cma.henkaku.xyz`（**须联网 F00D**，成功标志 `keystone: matched retail hmac`）。
  eboot(SELF) 另：`util/self2elf.py -i eboot.bin -o eboot.elf -k work.bin`（需 pycryptodome → 建 venv 装 `pycryptodome six`）。
- **归档 `LSDARC V.100`**（`XXXDATA.BIN` 索引 + `XXXDATA.ARC` 数据）：
  `magic[12]="LSDARC V.100"`（0x4C53444152432056…）+ `u32 count` + count×
  `{u32 isPacked, u32 offset, u32 unpackedSize, u32 size, name\0}`（name=CP932，无固定对齐）。
  条目 offset 为**链式累加**（off[i+1]=off[i]+size[i]）可自校验。
  打包项（isPacked=1）= `"LSD\x1A" + u8 enc_method(B/W/S) + u8 pack_method(D/R/H/W) + u32 unpacked_size` + 自定义 LZ/LZSS；
  本作 **SCRDATA 531 条全部 isPacked=0**，未用到解包。SYSDATA=`VAGp`(PS2 VAG 音频)；FONTDATA 6 条、BMPDATA 1498 条为打包。
- **脚本 `SCR 2.00`**（`"SCR 2.00"` + u32 A + u32 B，A/B 与提取无关）：

  ```
  instruction:
    u16 opcode
    u8  size       # 整条指令字节长（含 3 字节头），自定界关键
    u16 id         # 源码行号/语句号（非地址，有跳跃）
    operand*:  <u8 type> <data>
       type 0x01 / 0x05 -> 4B（小端）
       type 0x02 / 0x04 / 0x06 -> 2B（0x04 用在 `0x22/0x23` 的 u16）
       type 0x03 -> NUL 结尾 CP932 字符串
  ```
  ★ **用 size 逐条前进，531/531 脚本（含全部无文本脚本）恰好铺满、零失步** —— 定表可靠。
- **操作码语义（本作实测）**：

  | op | 语义 | 备注 |
  |---|---|---|
  | `0x5a` | **消息框正文 = 一次点击一行** | 29,905 次，1 串操作数 |
  | `0xfc` | **带 `%s` 的消息** | 串后跟替换源操作数：`(6,slot)`/`(3,str)`，`(1,0xffffffff)` 为终止；`%s` 依次 ← 各 slot |
  | `0xf0` | **标题卡** | 章节/场景标题、地图选择状态标题「朝　マップ選択中」 |
  | `0x5c` | **选项** | `(u32 个数, "显示文本,FLAG", "…,FLAG2", …)`；显示文本 = 最后一个 ASCII 逗号之前 |
  | `0xfd` | 槽位/UI 赋值 | `(6,slot),(3,str)`；`0x2402`=名牌文本、`0x04e4`=背景图、`0x0224`=名字部件；**提取时剔** |
  | `0x3c`/`0x3d` | SE `/` BGM 文件名 | 剔 |
  | `0x3b`/`0x107` | 图片加载 `/ 串拼接 | 剔 |
  | `0x1e`/`0x1d` | 调脚本(file,label) `/ 尾调用 | 用于遍历调用图 |
  | `0x1a` | 标签定义 | |
  | `0x18` | 条件（flag）→ 紧跟 `0x1a label` 跳转 | 分支 |
  | `0x25`,`0x21`-`0x28`,`0x30`,`0x37`… | 变量/flag/算术/地图 | 非文本 |
- **控件与占位符（消息串内）**：字面 `\n`（0x5C 0x6E）= 框内换行 → **合并**；`\c`（0x5C 0x63）= 控制码 → 删；
  `@y`/`@w` = 演出/等待码 → 删；`%s` → 用操作数槽位替换。主人公名 slot：`0x0c02`=恋、`0x1802`=相崎
  （仅调试菜单 QUESTION 赋值，故事内取默认；合称=相崎　恋）。
- **顺序（点击序）**：入口 **`PRG_MAIN_0630.START`**（AUTOEXEC 的 START 分支）。
  线性链 `PRG_MAIN_0630 → 0701 → … → 0711 → 0712{HY,MN,SR} → … → 0717{…} →`
  6 条角色线 `PRG_MAIN_{HIK,MAS,NAO,RIN,SIN,YAM}`。每个 `PRG_MAIN_07xx` 依序 `0x1e` 调
  `COM07_xx_yy` 场景，末尾 `0x1d` 尾调用次日；分支场景（`_00`,`_01`…）在同一 PRG_MAIN 内按调用点并入。
  顺序 = 自 `PRG_MAIN_0630` 按 `0x1e/0x1d` 调用图 **DFS 前序、脚本去重**；末尾追加 `OMAKE_DRAMA`（おまけ）。
- **排除**：`CERO`（**CERO 分级用合辑**：944 条独有消息 942 条与主线重复）、`DEBUG_*`（9 个开发菜单）、
  `QUESTION`（起動条件调试菜单，含主人公名默认）、`SELECT`/`SELECT2`（选项 UI，无文本）、
  0 引用分支 `HY07_14_04_02..07`/`COM07_03_10_07`（仅 DEBUG 可达）。
- **辞典/教程**：本作**无用語辞典、无教程文本**；全脚本检索关键词仅命中台词；UI/教程为图片（BMPDATA）。
- **工具**：`scripts/himehibi_lsdarc.py`（LSDARC 读取）+ `himehibi_disasm.py`（SCR2.00 反汇编，含 size 表）
  + `himehibi_crawl.py`（调用图）+ `himehibi_extract.py`（文本提取）。

## 第 2 作：Cafe Cuillere ~カフェ キュイエール~（PSV PCSG01197, DWANGO·Takuyo）
- **源**：`[PSV-JP]Cafe Cuillere.zip`（pkg2zip 产物，PFS 未解）。zRIF 已在 `games.json`：
  <zRIF>
  → `psvpfsparser.exe -i PCSG01197 -o dec -z <zRIF> -f cma.henkaku.xyz`（`keystone: matched retail hmac`）。
  容器结构与 ひめひび **完全一致**（`LSDARC V.100`，SCRDATA 109 条全 isPacked=0，109/109 零失步）。
- **与 ひめひび 的差异点（本作新增结论）**：
  1. **`0x10c`＝语音＋字幕**（ひめひび 记为「动态调用」）：`(6,dest)(3,"%.1d %.1d FILE.WAV 正文")(args…)`，
     **`.WAV ` 之后即上屏正文**（留守電/メール），须收录；替换源＝**字符串之后**的操作数（勿把字符串本身当 arg）。
  2. **注音 `#r基底|读音#`**（Ruby，19 处）：取基底去读音。
  3. **`0x5c` 选项前缀＝1 个全角 `０/１/２`**（＝写入的 flag 值，非显示）；显示文本须**剥前缀**。
     同一文本以 ０/１ 两值出现可证其为值而非正文。`戻/Ｋ/Ｒ/Ａ/Ｍ/Ｉ/Ｈ` 等标记**仅 DEBUG 用**。
  4. **主人公名槽 3 个**：`6402`＝真緒(名) / `7002`＝藤白(姓) / `8402`＝まお(名かな)；
     默认值直接取 eboot 名表 `藤白\0\0真緒\0\0まお\0\0`（`self2elf` 后搜 UTF-8）。
  5. **「固定名 / `%s`」成对互斥**：同句写两遍，以 `0x36/0x22/0x21/0x23` 条件跳转分隔；
     **槽位替换后两版文本全同** ⇒ **相邻去重**即自动归并（1058 行；标题/选项 0 误伤）。
  6. **剧本顺序＝SCRDATA 索引序＝eboot 脚本总表序**（`PRG_ROUTE` 线性派发；eboot 0x5cf78 起为脚本名表）。
     `_008`＝各角色 **スイートエンド**；`009_*`＝**おまけ** 15 篇；`010_*`＝**スイートハーレム**（需 Sweet End 解锁）
     —— 三者仅 DEBUG 引用，但 eboot **EXTRA 菜单表**（含标题＋解锁条件，0x5e600 起）证明其为发行内容 ⇒ 收录。
  7. **排除 15 个系统脚本**；`PRG_ROUTE` 另有 26 条「おまけ…閲覧可能になりました」解锁通知（系统文本）与
     `PRG_EFFECT` 20 条 `『演出未実装』` 开发占位 → 均剔。
  8. **原文笔误 1 行**（`007_ROG_002`：全角 `（` 开、半角 `)` 收，源字节 `…8169…29`）→ 显式整行定值修。
- **工具**：`scripts/cafe_extract.py`（复用 `himehibi_lsdarc.py` ＋ `himehibi_disasm.py`；自带 name-slot / ruby / 选项前缀 / 0x10c / 相邻去重 / TEXT_PATCH）。
- 成品 32,114 行（正文 31,576＋标题 258＋选项 280）【PASS】；报告 `提取结果/解析报告/Cafe Cuillere_解析报告.md`。
  9. **`\n`＝框内换行（非翻点击）**：全稿仅 3 处 `\n` 后紧跟 `「`，皆为**「两人同时开口」双行文本框**，
     每处**仅 1 个语音 + 1 条 `0x5a`**（＝一点击）⇒ 合并后同句两遍属**原文演出**（如
     `009_010_A_M id=327 「あ、そうなんだ。じゃあいいや」\n「あ、そうなんだ。じゃあいいや」`），
     **不是重复行、不该被去重吃掉**（去重只比 `out[-1]` 整行，不碰行内子串）。
