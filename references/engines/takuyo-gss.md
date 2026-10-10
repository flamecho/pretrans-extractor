# Takuyo gss（LSDARC V.100 + SCR 2.00）

> 路由 / 一句话索引见 `../engines.md`。

## Takuyo gss 引擎 —— LSDARC V.100 + `SCR 2.00`（ひめひび -Princess Days-, PSV PCSG01092）
- **平台/源**：PSV。源 zip 为 **pkg2zip 产物（PFS 未解，DATA/eboot 全高熵）**。
  解密：`work.bin`(512B) 经 `<psvdec>/rif2zrif.py` → zRIF
  （本作 （你自备的 zRIF），同 `games.json`）
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
