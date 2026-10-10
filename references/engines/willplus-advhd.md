# WillPlus / AdvHD（.wsc）

> 路由 / 一句话索引见 `../engines.md`。

- **WillPlus / AdvHD（`.wsc`）（Butterfly Lip ＋ Gloss ＋ Rouge 实证，2026-10-10）**：PC；exe manifest 残留 `will.willadv.exe`。
  - **同系列三作＝同一引擎、零改动复用**：Lip（`DKLDISC1.iso`/`DKLAPPEND.iso`，脚本 `BL_/OMAKE`，Vol.1）、
    Gloss（`DKGDISC1.iso`/`DKGAPPEND.iso`，脚本 `BG_/BGA_/BGC_/OMK_`，Vol.2）、
    Rouge（`DKRDISC1.ISO` 单盘，脚本 `BR_*`，Vol.3）。三作用**同一 opcode 表**均走到末尾收尾；
    Lip 201＋5 脚本中 200/201 ＋ 全 5 通过（唯一失步＝系统脚本 `MAINMENU` 的 `0xAB`，属系统/UI，整体不收）。
    共用引擎模块 `scripts/advhd.py`（`parse_arc`/`decrypt`/`walk`/`clean`/`extract_arc`），各作只写薄驱动。
  - **Arc**：`u32 extGroupCount` → 每组 `[ext 4B][count u32][tableOffset u32]`；条目表 `[name 13B][size u32][offset u32]`＝**21 B/条**。
    `Rio.arc`＝ext `WSC`（脚本）；`CHIP.arc`＝ext `ANM`（子表 MSK/PNG/TBL/WIP＝立绘贴图）；`Bgm/Se/Voice.arc`＝ext `OGG`。
  - **★ 解密**：WSC 数据**每字节 `rotl_8(c, 6)`**（`(c<<6|c>>2)&0xFF`）＝解密；即在 arc 里存的是 rotl_8(c,2) 过的。
    （未解密时也能看到貌似 opcode 的字节，**极易误判为明文**——务必先用 `rotl_8(c,6)` 过一遍。）
  - **反汇编**：wareya/will 的 `wsc.cpp` opcode 表（8bit opcode＋定长参数）可用，但本作多/异：`0x61` 取**1 参数**（影片名，非 0）、`0xE6`＝2 字节、`0x0D`＝7 字节。
  - **文本 opcode**：`op41`(GOODSTRING,4)＝旁白；`op42`(DOUBLESTRING,5)＝**说话人名\0＋台词\0**；`op02`＝选项。其余 STRING op 多为资源名（BGM_xx/ST11C07S/chi01/EFMSK_*/ED02.DAT）。
  - **★ 选项项的目标指令要「按表分派」，不能「硬跳 4 字节」**：每项＝`2B ＋ 选项\0 ＋ 3B 头(01 XX 03) ＋ 1 条目标指令`。
    该指令**通常**是 `07 <脚本名>\0`（直接跳转），但 **Lip `BL_10B` 用 `06 <5 字节>`（间接跳转）**。
    旧写法「跳 4 字节 ＋ 读原始串」只对 `07` 成立（4＝`01 XX 03`＋`07`），对 `06` 失步（第 2 个选项被读成 `･`）。
    修法（已入 `advhd.py`）：**跳 3 字节头后按标准 opcode 表分派一条指令**（`0x07` 读串 / `0x06` 跳 5B）。
    对 Gloss/Rouge 的 `0x07` 情形**结果完全等价**（不改变既有产物）。
  - **成行**：串尾 `%K%P`＝一次点击；串内换行是**字面 `\n`(0x5C 0x6E) 转义**（非 0x0A）→ 合并；`%O` 与 `\n\n\n` 为空演出丢弃。
  - **电话/邮件样式**：`【名】\n『文』`（op41）→ 去 `【名】`、保留 `『文』`。
  - **容器**：`DKGAPPEND.iso`＝官方 `After Love パッチ`（追加 RIO+.arc 续后日谈「OMK」）；`data1.cab/data2.cab`＝InstallShield 安装器＋MSI（仅 VC++ 运行库，**无游戏文本**，用 unshield 取）。
  - **原语**：`scripts/bgloss_extract.py`（Gloss 自包含旧版）｜`scripts/advhd.py`＋`brouge_extract.py`（Rouge）／`blip_extract.py`（Lip，共用引擎薄驱动）。
  - **原文笔误**：Rouge 有 3 处引号不配对（`BR_03G`/`BR_05R` 尾 `」」`；`BR_24END01` 缺起始 `（`），
    经原始字节核对确认是**作者笔误**、用户口径＝按作者意图修正并报告单列（固化在 `brouge_extract.py` 的 `POSTFIX`）。
