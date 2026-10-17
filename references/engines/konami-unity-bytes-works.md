# KONAMI 自研 Unity ADV（`.bytes`）—— 逐作差异（GS1 1st Love / GS3 3rd Story）

> 引擎核心见 `engines/konami-unity-bytes.md`（§1〜§7）。本册只放**换作差异点**。

## 8. ★ 第 2 作（GS1 1st Love）实测差异（2026-10-15）

1. **スキンシップ台词键**：GS1＝`Params[].DialogueText`（**字符串**）／GS2＝`DlgText`（**列表**）
   ⇒ `for dt in par['DialogueText']` 会**按字符迭代**（本次产出 56,748 行单字垃圾，已修）。
   正解：同时取两键，`str` 包成 `[str]`。**新增作品务必先 `json` 打印一层结构再写 walker。**
2. **角色名形式位**：GS1 有单 `＊` 变体（`｛日比谷＊｝`/`｛天之橋＊｝`）⇒ 尾部 `＊`（1~2 个）一律剥。
3. **无 `∋/∈`**：GS1 全量 0 处（GS2 有 44 组同文变体）⇒ 归一规则保留但幂等。
4. 其余全同：头魔数、`0316…0317` 骨架、`01 04` 判据（GS1 全量复核：3 选项块 925／2 选项 263／1 选项 4，
   抽样均为真选项）、池 XOR 键式、`0x00→K` 还原、`\n`/`@@`/`▼`、`ExtraProfilePlayerName="主人公"`。
5. GS1 规模：`scenario` **5,458** 本（另 92 本 44B 空壳）→ 正文 **41,314** ＋选项 **3,305**；
   スキンシップ `skinship_dialogue_01〜08`（**5,132**，含 4×Params 同文重复）；はばたきネット **533**。
6. GS1 名札表 **549 唯一值**（含资源 ID）；纯人名 17＋主人公共 18，与 vndb `v857` **零差**
   （葉月珪・守村桜弥・三原色・姫条まどか・鈴鹿和馬・日比谷渉・氷室零一・天之橋一鶴・蒼樹千晴・天童壬／
   有沢志穂・須藤瑞希・藤井奈津実・紺野珠美・花椿吾郎・尽＋`伊藤`(游戏内 charId16，vndb 无)）。
   游戏内 `lbl_to_char_id`(根 initialize) ＋ `AddressBookAddress_0..9`(string_table)＝**零成本 cast 核对源**。
7. 工具：`scripts/tokimemo_gs1_extract.py`（GS2 版 + 上列差异）；NSP 拆分通用件 `scripts/nsp_split.py`。
8. **更新 v1.0.4（未决）**：更新 NCA＝ExeFS(section0 `main/rtld/sdk/subsdk0`)＋**BKTR Patch RomFS**(section1, 46MB)。
   `hactool --baseromfs` 解补丁时**首个被写出的文件＝`Data/Managed/Metadata/global-metadata.dat`**（IL2CPP 元数据），
   其后 14,033 次写出**全落同一路径**（本机 hactool 的 BKTR `--romfsdir` 有路径 bug，末文件 0 字节）⇒ **未能逐文件 diff**。
   ⚠ `--baseromfs` 需传**补齐到段大小**的本体 section1（否则 `Failed to read RomFS directory cache!`）。
   结论：`StreamingAssets/*.assetbundle` 未被补丁列入 ⇒ 以本体为准；复核手段＝`nstool` 或手工解析 BKTR `PINF`。
9. `<你的 prod.keys>` 解析会因某键长度非法而**中止**（`Key (…) must be 32 hex digits!`）⇒ **用 `_sw/prod_fixed.keys`**。

## 9. ★ 第 3 作（GS3 3rd Story，2026-10-15）实测差异

TID `010091C01BD8A000`（v0 本体，**无更新**）；titlekey `.tik[0x180:0x190]`＝`a40043f5e81823c069b1f988ccbd0f85`；
Program NCA `3126fdcde787a8d8f3896c7dcd2b7e74.nca`；工具 `scripts/tokimemo_gs3_extract.py`；
成品 **72,703 行**（scenario 64,867＋skinship 7,107＋net 729），check_text PASS。

1. ★★ **头只有 16 B（4×u32）⇒ 代码区自 `0x10` 起**（GS1/GS2 为 28 B／`0x1C`）；
   头魔数 `(…,1,773,772)` **不成立** ⇒ 只校验 `poolOff=u32@4`。
2. ★★ **选项判据必须改**：`0104` 只覆盖 3 选项块的 1,094/1,189；2 选项块大量落在
   `0007`/`0200`/`0102`/`0404`/`0108`… ⇒ 改「**按 `0503` 个数分类 ＋ `ops[0]` 是否名札**」：
   1 个＝旁白（**收**，GS1/GS2 会丢）、≥3＝选项、2 个中 `ops[0]` 是名札＝名札+正文、否则＝选项。
   另加 `is_option_pair()`（两项皆名札形且 `ops[1]` 无对话标记 ⇒ 选项对，如 `鐘を鳴らす／鐘を鳴らさない`）
   与 `OPTION_ONLY={大学を受験する,就職試験を受ける}`（`ops[1]` 含「、」故上式不触发，z63 進路選択 68 块）。
3. ★ **名札带样式前缀 `？`**（`？琉夏`/`？コウ`；同名另有裸形）⇒ 剥前缀后判名札；名札本身不入正文。
4. ★★ **スキンシップ 台词换载体**：GS1/GS2 在 `lang/ja/initialize` 的 `skinship_dialogue_*`；
   本作在**根** `initialize.assetbundle` 的 `ss_rct_1..6`/`nss_rct_1..6`/`wnss_rct_1..6`/`sstuto_rct` 之 **`StrData`**，
   行内换行标记 **`**LF**`**（非 `\n`）。`skinship_table_1..8` 只有资源名，无文本。
5. **剔除项**：整本 `scenario/v/v00_00_000|001`（命令テスト菜单）；行级——`デバッグキャラIDに不正な値が入っています！！！`、
   `…バイト実績イベント`／`アルバイト実績イベント成功|失敗`、采话人 ∈`{ダミー,デバッグ,テスト}` 的整块（台词实为脚本注释）、
   含脚本 ID `[A-Za-z]{1,2}\d{2}_\d{2}_\d{3}` 的行、纯 `　`/`・` 装饰行（653，与 GS1/GS2 口径一致）。
6. **cast 核对**：vndb `v2956`（须带 `Cookie: vndb_view=2-/v2956/chars` 才显示 4 名剧透角色）。
   名札表 157 唯一值 / 22 名 **21 命中**；唯一缺项 `若王子 貴文` ⇒ 全量扫描仅存于 `string_table`(UI)，Switch 版无其台词。
   **`lbl_to_char_id` 不是本作 cast 表**（233 词含 GS4 人名 ⇒ 系列共用 label 表，勿用）。
   主角 = `バンビ`(Nameable) ⇒ 默认名 **`主人公`**（唯经 `｛主人公｝` 宏出现）。
7. 其他全同 GS1/GS2：池 XOR 键式、`0x00→K` 还原、`0316…0317` 骨架、`∋≡？`/`∈≡！`、`\n`/`@@`/`▼`、
   `AddressBookAddress_0..7`＝主 cast 全名。


## 10. ★ 第 4 作（GS4 4th Heart，2026-10-15）实测差异

TID `0100B0100E26C000`；源＝**XCI（gamecard）**而非 NSP；工具 `scripts/tokimemo_gs4_extract.py`
（＋切片器 `scripts/crazychain_xci.py`）；成品 **72,207 行**（scenario 71,161＋chat 393＋net 653），PASS。

1. ★★ **头字段语义与 GS3 不同**：本作 `hdr[3]`（u32@12）＝ **字符串池起点**，`hdr[1]`（u32@4）＝**代码区终点**；
   **2,525/11,754 本文件 hdr[1] != hdr[3]**（GS1/GS2/GS3 全量 hdr[1]==hdr[3]）⇒ 照搬 GS3 的 `poolOff=u32@4`
   会**从二进制区读池**（解不出字串）。**判据**：对差分文件试 hdr[3] 能否解出日文（实测 2,437/2,525 命中）。
2. **XCI 链路**：`hactool -t xci` 本 XCI 正常解析；NCA 用 `crazychain_xci.py` 手工切出；
   **本 XCI 无 `.tik`/`.cert`**（Gamecard）⇒ `hactool -t nca … -k prod_fixed.keys --romfsdir=…`
   **无需 `--titlekey`** 即出完整 RomFS（key area Key0/1/3=00…、Key2 有值）。
3. **附加文本源换了名字**：`lang/ja/initialize` 的 **`chat_message`**（はばたきチャット，`message`，393 行）与
   **`habaw`**（はばたきネット：`MovieTable`/`EventTable`/`NewsTable`/`ColumnTable` 的
   `Title`/`HeaderTitle`/`Description`/`Notice`/`Piriod` ←注意表里拼写是 `Piriod`，653 行）。
   スキンシップ台词在 **`scenario/ss/*`（4,940 本）**，随剧本收；`nss_table_*`/`skinship_table_*` 只有资源名。
4. **主角名 = `マリィ`**（vndb `v26002`，别名 Protagonist/主人公）。
5. **cast 核对**：`AdvNameCh1..8` ＝ 風真/颯砂/本多/七ツ森/柊/氷室/御影/大地（**本作即 8 攻略対象**，最可靠）；
   名札 134 唯一值（具名 36）。**`大成 功`／`巴 征道` 是 DLC 追加攻略キャラ**（官方 DLC 2/3，独立 NSP）⇒
   本体无台词；`大迫 力` 本体 0 处、`花椿 吾郎` 仅作はばたきネット 文本内容（12 处）。
6. 保留原字：`Å`、西里尔 `о`（チャット のハンドル `７ｃо（ななこ）`）、`✕`（求人票）—— 均源数据。
7. **统一修订（四作同步，2026-10-15）**：① 主角名按 vndb 填（GS1 `主人公`／GS2 `デイジー`／GS3 `バンビ`／GS4 `マリィ`），
   相邻「苗字＋名前」合并；② 块分类＝`0503` 个数 ＋ 名札判据（名表∨不以假名收尾∨非 0104 块）；
   ③ 半角 `()`→全角、纯装饰行（`・`＋全角空格）剔除；④ `check_text` 收窄「行首【名】＋正文」（括号含 `・`/`＠` 不算）。

## 11. GS4 追加コンテンツ（DLC 9 本，2026-10-15）

- ★ **本体是 XCI（无 `.tik`）而 DLC 是 NSP（有 `.tik`）⇒ DLC 必须带 `--titlekey`**（`nsp_split` 出的 `.tik[0x180:0x190]`）。
- ★ **DLC romfs 无 `Data/StreamingAssets` 层级**（直接 `romfs/scenario/…`）⇒ 先重排成
  `<dlc>/compat/Data/StreamingAssets/scenario/…` 再喂同一提取器（`--no-chat --no-net`；DLC 无 chat_message/habaw）。
- `.bytes` 格式与本体同（头 4×u32，本 DLC `hdr[3]`＝池起点）。
- 规模：DLC1 入学式 37／**DLC2 巴征道 741**／**DLC3 大成功 731**／DLC4 春 166／DLC5 夏 225／DLC6 秋 483／DLC7 冬 414
  ＝ **2,797 行**（7 包含文本）；**DLC「Fashion item」×2 无文本**（Sprite/Texture2D＋`index` 清单）。
- TID：`0100B0100E26D003`(1)／`…D001`(2 巴)／`…D002`(3 大成)／`…D00B`(4 春)／`…D00C`(5 夏)／`…D00D`(6 秋)／`…D00E`(7 冬)／
  `…D004`/`…D008`(服装)。官方名（外部核对）＝巴征道(2021-12-01,¥1,980,柔道部)／大成功／春〜冬のときめきドラマセット。
- 源数据：`xx02_01_001_00`（冬）一 op 内「台词＋旁白」两段，属源脚本同一文本框 ⇒ 按行内换行合并成一行。
