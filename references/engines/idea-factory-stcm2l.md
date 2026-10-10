# STCM2L（Idea Factory 系）

> 路由 / 一句话索引见 `../engines.md`。

- **STCM2L（Idea Factory 系；猛獣＝Switch/UTF-8，PANDORA＝PS2/CP932）**：
  - 脚本头：`generator 32B("STCM2L Jul 12 2010 …")` ＋ `exports_offset(u32)` ＋ `exports_count` ＋ … ＋ `"GLOBAL_DATA\0"` ＋ globals(u32 数组) ＋ `"CODE_START_\0" 12B`；
    **代码段起点 = 该串偏移 + 24**；**终点 = 子文件起点 ＋ exports_offset**（⚠ `exports_offset` 相对**子文件起点**，不是 magic 处）。
  - 代码段 = opcode 链 `[u32 size][payload(size-4)]`。
  - **文本记录 = `[addr][c1][c2]…[0][len/4][1][len][text][pad]`**，`len=align4(bytelen+1)` 且 `len/4` 复写前一字段（＝该记录的可靠签名）。
    `"0"` 字段在 payload 偏移 **12**（2 个颜色字段）＝正文/台词；偏移 **24**（5 段样式）＝菜单项候选（选项）。
  - **换行/新框标记 = 12B opcode `[0][cmd][flag]`**（cmd ∈ {0xd2,0xd3,0xd4,0xf5,0x7a,0x34,0x35,0x9a,…} 一票命令号）
    → 标记处切行、无标记的连续片段合并 ＝「一次点击＝一行」。
  - **★ PS2 侧容器 = CRI「UNI2」**（PANDORA，SLPM-55269）：`0x00 "UNI2"` / `0x04 0x00010000(数据区起点)` / `0x08 子文件数` / `0x0c 1(FAT 起始簇)` / `0x10 3`；
    FAT 自 `0x810`，每条 16B `[FileID][startCluster][sizeClusters][sizeBytes]`；**子文件绝对偏移 = startCluster × 0x800**。
    每个子文件 = `[0x1800 前缀区块][STCM2L 脚本]`，**脚本 magic 固定 +0x1800**（130 文件 129 命中，id=10 脚本被裁短例外）。
  - **★ 子文件 0x1800 前缀区块另有正文 —— 只走代码段会整段丢失**：
    ① 每章「ミッション小测（豆知識クイズ，一问＋两答）」② **结局场景整段**（PANDORA 文件 **961/981** 的ジョーカー ED 就在此前缀区，**不在**代码段内）③ 人名初始值表/玩法说明（判系统，丢）。
    另：外层 `SCRIPT.UNI` 自身也带一份 STCM2L（magic 同在 `0x1800`），含军用术语小测＋曲目表(丢)＋符号表(丢)。
  - 行内 `#n` ＝软换行标记（删除合并）；`#Name[n]` ＝主角名插入宏（PANDORA `#Name[1]`→**カンナ**，默认名取自子文件内「名字输入初始值表」`[2][1][8]"カンナ"`）。
  - **★ PSV 侧（Norn9 Act Tune，PCSG00833）—— 与 PS2/Switch 版差异大，别照搬**：
    - 指令 = `[u32 is_call][u32 opcode][u32 nparams][u32 length]` ＋ nparams×`[p0,p1,p2]` ＋ data；
      **字符串参数＝p0 局部指针指向指令内数据区 `[0][L/4][1][L][utf8 text][pad]`**（注意是 **12 B/参数**、且 length 已含头）。
    - **★★ 每文件 opcode 有常量平移 Δ（本作最大的坑）**：导入函数 ID 整块平移（Δ = 0x10 的整数倍；
      本作 Δ ∈ {0, ±0x10, 0x30, 0x40, 0xe0, 0x120, 0x150}），**但 builtin（`0x1f4` 等换框 / `0x6` goto / `0x3` Mif / `0` / `0x11` / `0x12`）不动**。
      **Δ 检测法＝取「含日文串且平均长度最大（去噪）的 opcode」为 text_op，Δ = text_op − 0xcf9c**
      （用平均长度而非计数：5001 类文件正文极少、flag 串反而更多，计数会选错）。
    - 归一化（Δ=0 基准）：`0xcf9c`=push 文本 / `0xd698`=push 人名 / `0xe090`=选项（p0=文本,p1=目标标签）/
      `0x236c`=章题标识 / `0x5414`·`0x4b24`·`0x4cfc`·`0x4ed4`…=flag。
    - **换框 = builtin `0x1f4`**（连续 `0xcf9c` 合并成一行）。
    - **互斥分支同点击多版本**：`if/else` 两版相邻排放、以 `goto`(0x6) 分隔；「then 版」的 `0x1f4` **紧跟 `goto`**。
      ⇒ 规则：`goto` 断「段」；`0x1f4` 若下一条是 `goto` 也只断段，否则断「点击」；同点击多段取一（优先无 `#Name[`，再取最长）。
    - 变量：`#Name[1]`→**こはる** / `#Name[2]`→**深琴** / `#Name[3]`→**七海**（三名可改名女主；脚本内占位符版与直写版并存可互为印证）；`#Scale[…]` 丢。
    - **每文件开头 5 行共通导入**（`プロローグに新たな選択肢が追加されました`＋4 行世界观）逐文件重复 88 次 ⇒ 只留一次置于全文最前。
    - SYSTEM.cpk `dbDictionary.gbin` = **薄桜鬼遗留术语表**（无本作词条）⇒ 整体排除（无 用語辞典 可并入）；
      `script/init/*.DAT` ×7 仅 flag ⇒ 排除；GAME.cpk 全为图像。
    - 工具：`norn9_extract.py`（自包含；自动检测 Δ/text/name/opt）。
  - 工具：`stcm2l_extract.py`（猛獣 Switch）／`pandora_extract.py`＋`pandora_dbg.py`（PANDORA PS2）／`norn9_extract.py`（Norn9 PSV）。
