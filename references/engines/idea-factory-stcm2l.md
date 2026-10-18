# STCM2L（Idea Factory 系）

> 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。

- **STCM2L（Idea Factory 系；猛獣＝Switch/UTF-8，PANDORA＝PS2/CP932）**：
  - 脚本头：`generator 32B("STCM2L Jul 12 2010 …")` ＋ `exports_offset(u32)` ＋ `exports_count` ＋ … ＋ `"GLOBAL_DATA\0"` ＋ globals(u32 数组) ＋ `"CODE_START_\0" 12B`；
    **代码段起点 = 该串偏移 + 24**；⚠ **但 `exports_offset` ≠ 代码链终点**：实测 118 文件在它之后**仍连续是合法 opcode**
    （含真台词，如 PANDORA file100 `「……走れるか？」` / file101 `「……いつまでも腐っているよりは」`），共 **244 条文本记录被它截掉**
    ⇒ 遍历应走到**子文件末尾**（`fstart + sizeBytes`），按「opcode 链合法性」自停，不要用 `exports_offset` 当界。
  - 代码段 = opcode 链 `[u32 size][payload(size-4)]`。
  - **文本记录 = `[addr][c1][c2]…[0][len/4][1][len][text][pad]`**，`len=align4(bytelen+1)` 且 `len/4` 复写前一字段（＝该记录的可靠签名）。
    `"0"` 字段在 payload 偏移 **12**（2 个颜色字段）＝正文/台词；偏移 **24**（5 段样式）＝菜单项候选（选项）。
  - **换行/新框标记 = 12B opcode `[0][cmd][flag]`**（cmd ∈ {0xd2,0xd3,0xd4,0xf5,0x7a,0x34,0x35,0x9a,…} 一票命令号）
    → 标记处切行、无标记的连续片段合并 ＝「一次点击＝一行」。
  - **★ PS2 侧容器 = CRI「UNI2」**（PANDORA，SLPM-55269）：`0x00 "UNI2"` / `0x04 0x00010000(数据区起点)` / `0x08 子文件数` / `0x0c 1(FAT 起始簇)` / `0x10 3`；
    FAT 自 `0x810`，每条 16B `[FileID][startCluster][sizeClusters][sizeBytes]`；**子文件绝对偏移 = startCluster × 0x800**。
    每个子文件 = `[0x1800 前缀区块][STCM2L 脚本]`，**脚本 magic 固定 +0x1800**（130 文件 129 命中，id=10 脚本被裁短例外）。
  - **★ 子文件 0x1800 前缀区块另有正文 —— 只走代码段会整段丢失**，且**逐文件有两种记录框架，勿一刀切**：
    - **A) 场景脚本**（PANDORA 61/129 文件）：记录框 = **`[u32 cmd][u32 arg][u32 size][payload]`**；
      `0xd2`=正文/台词、**`0xd3`=换箱分隔**（size=0x10 空 payload）、`0xd4`=说话人名(丢)、其余(`0x7a`/`0x34 switch`/`0x13 evNNNN`/bg/立绘)=资源控制。
      ★★ **连续的多个 `0xd2` 属于同一文本框**（框内软换行）⇒ 相邻片段**必须合并**；**`0xd3` 才是「新箱」**。
      否则整段被拆成碎片行（旧版踩过：一次修正合并 ≈270 行）。**结局/尾声整段剧情就在此前缀区**
      （PANDORA 文件 **961/981** 的ジョーカー ED，**不在**代码段内）。
    - **B) 平坦记录表**（68 文件）：`[0][n][1][L][text]` 逐条、无 cmd/arg/size 框；内容＝**小测问答库（豆知識）**
      ＋资源串（`b-ronn_b`/`thread_cnt`/`処理開始`）＋系统表（STATUS 画面说明、人名表 `カンナ…その他`）⇒ 只留小测，其余丢。
    - ⚠ **前缀区首条记录的头可能在 `fstart` 之前**（实测 -0x10，payload 落在区块内）⇒ 扫描必须容忍**跨界记录**，否则丢首条（PANDORA `「だが忘れるな。`）。
    - ⚠ **代码段 ↔ 前缀区之间必须补边界**，否则交界处两行粘连（实证 `「ああ……。寝ていたのか」` 与 `「だが忘れるな。…」` 粘成一行）。
    - ⚠ **说话人名判定别用「频次 ≥2」**：集合名+番号名札（`救急隊員１`/`軍人４`/`通行人１`）常只出现在单一文件 ⇒ freq==1 漏判、与台词并成 `名「…」`。改「**紧邻引号起头即认定**」。名札字符集须含**形近破折号**（`ロニ―` 用 U+2015 而非 `ー` U+30FC）⇒ 纳入 `\u2010-\u2015`。
    - ⚠ **口径**：PANDORA 定稿取**严格「一次点击＝一行」**（跨框不合并、允许单侧引号）——原作会把一句/心声拆到两框，
      强制合并会造字；`scripts/pandora_extract.py` 有 `STRICT_CLICK` 开关（`--merge` 出续写合并版）。
    - ⚠ `opt/mopt`（同一 opcode 含「人名＋正文」）里的人名要过滤，否则吐出裸名行。
    - ⚠ 引号修复：缺开括号要**行首补**（勿行尾追加，否则产出 `）（` 怪串）；全/半角混用（原作实测 5 处 `（…… )`）与全角同现时归一。
    - 另：外层 `SCRIPT.UNI` 自身也带一份 STCM2L（magic 同在 `0x1800`），含军用术语小测＋曲目表(丢)＋符号表(丢)。
  - 行内 `#n` ＝软换行标记（删除合并）；`#Name[n]` ＝主角名插入宏（PANDORA `#Name[1]`→**カンナ**，默认名取自子文件内「名字输入初始值表」`[2][1][8]"カンナ"`）。
  - **★ PSV 侧（两作布局互不相同：Norn9 Act Tune / RE:VICE[D]）⇒ 见 `idea-factory-stcm2l-psv.md`**。
  - 工具：`stcm2l_extract.py`（猛獣 Switch）／`pandora_extract.py`＋`pandora_dbg.py`（PANDORA PS2）／`norn9_extract.py`・`revice_extract.py`（PSV）。
- **★ PSP 侧（CRI CPK 两样本：`SNOW BOUND LAND`／`アーメン・ノワール ポータブル`）⇒ 见 `engines/idea-factory-stcm2l-psp-cpk.md`**（本册超 10 KB，2026-10-16 拆出）。
- **★ Switch 侧（猛獣／BLACK WOLVES SAGA）⇒ 见 `engines/idea-factory-stcm2l-switch.md`**（本册超 10 KB，2026-10-12 拆出）。
- **★ PS2「UNI2」第 2 样本（`L2 Love×Loop`）⇒ 见 `engines/idea-factory-stcm2l-ps2-uni2.md`**（本册超 10 KB，2026-10-16 拆出；★ 前缀区 0x2000／末条跨入下一文件前缀区）。
