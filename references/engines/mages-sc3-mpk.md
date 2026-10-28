# MAGES. 自家引擎 —— MPK 容器 ＋ SC3 脚本（5pb 系）

> 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。
> 首个样本：**花咲くまにまに（PSV, PCSG00366）**。Steins;Gate / Chaos;Child / Robotics;Notes 等同厂商 SciADV 作品
> 同用 SC3（.scx/.msb），但**码表/控制码可能不同**，换作必回查。

## 1. 容器 MPK（`MPK\0`）

- 资源包 = `MPK\0` + 头。**头与条目表**：

  | 偏移 | 类型 | 含义 |
  |---|---|---|
  | 0x00 | 4B | `MPK\0` |
  | 0x04 | u16 | file format minor |
  | 0x06 | u16 | file format major（本作 = 1）|
  | 0x08 | u64 | 文件数 N |
  | 0x10–0x40 | — | 保留（0）|
  | 0x40 | N×256B | 条目表 |

- 单条目（256 B）：

  | 偏移 | 类型 | 含义 |
  |---|---|---|
  | +0 | u32 | 1 = 该文件 zlib 压缩（实测恒 1）|
  | +4 | u32 | 数据偏移（绝对，对齐 0x800、基准 0x140）|
  | +8 | u32 | 存储长度（压缩后）|
  | +12 | u32 | 还原长度 |
  | +16 | 16B | 0 |
  | +32 | char[224] | 文件名（NUL 结尾）|

- 首条数据偏移 = `0x40 + N*256`（本作 N=209 → 0x D140）。
- 数据一律 zlib（`78 9C`）。同包还含 `.GXT`(PSV 8bpp 纹理)、`*_AT9`(ATRAC9 音频)、`.MP4`。
- 资源包与脚本包分离：`SCRIPT.MPK` / `SYSTEM.MPK` / `BG.MPK` / `CHARA.MPK` / `VOICE_AT9.MPK` …

## 2. 脚本 SC3

- magic `SC3\0`；**i32 OffsetStart @4**、**i32 OffsetEnd @8**；0x0C 起为字节码（本作不解析）。
- **偏移表** = `[OffsetStart, OffsetEnd)` 内的一串 u32（**绝对文件偏移**），条数 = `(End-Start)/4`。
- 第 i 条字符串 = `data[ off[i] : off[i+1] ]`，末条到文件尾；**无长度前缀、无终止符**。
- 一条字符串 = 一个文本框 = **一次点击 = 一行**；以 `0x03 0xFF` 收尾（少数同义替位 `0x08 FF`／`0x05 FF`）。
- 文本与字节码同文件；只取偏移表里的字符串即可，无需反汇编。

## 3. 文本编码（自定义 16 bit 码表）★ 本引擎最大的坑

- 码 = **大端 u16**。字符表内联在 **`eboot.bin`（self2elf → eboot.elf）**：一段连续 **Unicode 列表 T**，
  本作起于 ELF `0x751D0`。
- **关键：引擎码表 = 字体字形序列 E（`字形槽 = 码 - 0x8000`），而 E 与 T 只在低区同序、高区差 37**：

  | 码范围 | 取字 |
  |---|---|
  | `0x8000` | 框内换行（控制码）|
  | `0x8001`–`0x8058` | `T[码 - 0x8000]` |
  | `0x8059`–`0x807D` | 仅字体有的 37 个字形（本作脚本未使用）|
  | `0x807E`–`0x8F3E` | `T[码 - 0x8025]` |
  | `0x8F3F`–`0x8F42` | 字体尾部独有字形（本作 = 澤/跪/躱/巫）|

- **分区偏移的定法（两条腿走路）**：
  1. 高区（かな/漢字）：对唯一参数「基址」做**一次性拟合**（扫 `B∈[0x6000,0xA000]`，按假名/标点占比打分），
     本作 `B = 0x8025` 出现尖峰。
  2. 低区（ASCII/記号）：低码样本太少，占比法失效 ⇒ **改用已知明文**。本作的钥匙是
     剧本里 protagonist 写的英文名（`My name is Wasuke Tani.`）与 `_system.scr` 曲目信息
     （`歌：marina`／`編曲：Tak Miyazawa`）⇒ 得 `T[码 - 0x8000]`。
  - 两段差 37 = 字体比 T 多出的 37 个字形，恰落在槽 89..125。
- ⚠ **易错点**：只按高区拟合出的基址会把低区 ASCII 全部错译成 `_0-9A-Za-z` 字符（本作曾把
  `『My name is Wasuke Tani.』` 译成 `『NPC_B3P7HP_HJ93P_C7X』`）。**只要正文里出现 Latin/半角符号，
  就必须用已知明文单独校验低区。**
- `FONT.GXT` 结构：`GXT\0` + 0x40 头（`u16 w=2048 @0x38`、`u16 h=1984 @0x3A`）+ 灰度图集，
  **32×32 字形格、64 列**；`槽 = 码 - 0x8000`。字形渲染**只准人工目视个别字**（禁 OCR 批量建表）。
- ELF 内另有一张**排序 Unicode 表（Cmap）**，可用于校验某字形是否存在（本作据此区分 躱 U+8EB1 / 躲 U+8EB2）。

## 4. 控制码 / 宏码（本作实测）

| 码 | 含义 | 处理 |
|---|---|---|
| `0x01`…`0x02` | 名札（说话人）包裹；**内为姓+`0x803F`+名** | 丢弃整段（不加说话人前缀）|
| `0x03` / `0x08` / `0x05` | Present（显示该条）| 丢弃 |
| `0x04`+3B / `0x07`+1B | 文字色 / 等待 | 丢弃 |
| `0x0C` `0x11` `0x12` `0x13` `0x14` `0x16` `0x19` `0x1A`+2B | 字号/边距/取值/自动前进 | 丢弃 |
| `0x15`…`0x00` | 表达式 | 丢弃 |
| `0xFF` | 串终止 | 丢弃 |
| `0x8000` | **框内换行** | **合并** |
| `0x2000` / `0x2001` | 主人公**姓** / **名**（玩家名宏）| 内联（本作 望月 / 七緒）|
| `0x803F` | 名札内的姓/名分隔符（= 半角空格）| 随名札丢弃 |

- 本作**无 ruby**（0x09/0A/0B/1E 全库 0 次）、**无 0x00 换行**（框内换行只有 0x8000）。
- 玩家名默认值从 `macrosys2.scr` 前两条直接读出（望月／七緒），不必翻 eboot。

## 5. 端到端重跑（花咲くまにまに）

```bash
# rar → app 树 → PKG 层解密 → ELF → SCRIPT.MPK → .scr → 成品
7z x "<rar>" -o_src_manimani -y
psvpfsparser.exe -i ".../app/PCSG00366" -o _work_manimani/dec -z "<zRIF>" -f cma.henkaku.xyz
python self2elf.py -i _work_manimani/dec/eboot.bin -o _work_manimani/eboot.elf -k ".../sce_sys/package/work.bin"
python scripts/manimani_extract.py extract _work_manimani/dec/USRDIR/SCRIPT.MPK _work_manimani/scripts
python scripts/manimani_extract.py text _work_manimani/scripts _work_manimani/eboot.elf "提取结果/[PSV-JP]花咲くまにまに_全文本.txt"
```
详见 `提取结果/解析报告/[PSV-JP]花咲くまにまに_解析报告.md`。
