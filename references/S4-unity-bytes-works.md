# KONAMI 自研 Unity `.bytes` —— 逐作差异 ＋ 工程注意

> **本册是主册的续篇，节号接着排**：§1〜§6（引擎核心：容器 / 解密 / 记录形状）在 `S4-unity-bytes.md`，
> 本册从 §7 起是本作实例与逐作核对手册。**不是缺了前六节** —— 按需跳读，别从头找第一节。

## 7. ★ 换作必核的「逐作差异点」（GS1 1st Love 实测，2026-10-15）

| # | 项 | GS2 | GS1 1st Love | 教训 |
|---|---|---|---|---|
| 1 | スキンシップ台词键 | `Params[].DlgText`（**list**） | `Params[].DialogueText`（**str**） | ★★ `for dt in par[key]` 对 **str 会按字符迭代** ⇒ 产出 5.6 万行单字垃圾。**正解：同时取两键并 `str` 包 `[str]`；新作先 `json` 打印一层结构再写 walker** |
| 2 | 角色名形式位 | `｛佐伯＊＊｝`（双星） | 另有**单 `＊`** 变体（`｛日比谷＊｝`） | 尾部 `＊`（1~2 个）一律剥，勿只判 `＊＊` |
| 3 | 历史遗留 `∋≡？`/`∈≡！` | 有（44 组同文变体） | **无**（全量 0） | 规则保留即幂等，别据此判「漏解」 |
| 4 | `01 04` 选项判据 | 成立 | **全量复核成立**（3 选项 925／2 选项 263／1 选项 4；抽样均真选项） | 判据稳；仍要**抽样目视**确认 |
| 5 | 其余（头魔数/骨架/池键式/`0x00→K`/`ExtraProfilePlayerName`） | — | **全同** | — |

★ **同族作品的「结构相同」只到「头魔数＋骨架」为止**；**数据表字段名与字段类型逐作可变** ⇒ 一律先 dump 一层 JSON。

## 8. 工程注意（两作共同）
- `hactool --pfs0dir` 对 **>1.7GB 成员写全零** ⇒ NSP→NCA **必须 Python 直拷**（通用件 `scripts/nsp_split.py`）。
- `--titlekey` 收**加密**值（＝`.tik[0x180:0x190]` 原值）。
- **`prod.keys` 可能因某键长度非法而中止**（`Key (…) must be 32 hex digits!`）⇒ 备一份 `prod_fixed.keys`。
- **BKTR 更新**：`--baseromfs` 需传**补齐到段大小**的本体 section1（否则 `Failed to read RomFS directory cache!`）；
  本机 hactool 的 BKTR `--romfsdir` 会把**所有输出写到同一路径**（路径 bug）⇒ 补丁**无法逐文件 diff**，
  改用 `nstool` 或手工解析 BKTR `PINF`（`num_fs_entries`／`file_data_table`）列「源＝patch data」的文件集。

## 9. ★ 第 3 作（GS3 3rd Story）：骨架同、判据不同

| # | 项 | GS1/GS2 | GS3 | 教训 |
|---|---|---|---|---|
| 1 | 头 | 28 B（7×u32），魔数 `(…,1,773,772)` | **16 B（4×u32）**，魔数不成立 | 只校验 `poolOff=u32@4` 与 `0x10≤poolOff<len` |
| 2 | 代码区起点 | `0x1C` | **`0x10`** | 起点取自「头长」；先 dump 首 0x40 字节定之 |
| 3 | 选项判据 | 块后 `0402` 再跟 **`0104`** | `0104` **只覆盖 1,094/1,189 个 3 选项块** | ★★ **改按 `0503` 个数 + `ops[0]` 是否名札分类**（细则见 `pitfalls/B-lines.md`） |
| 4 | 无说话人旁白 | 会被丢 | **`0503` 个数＝1 且为正文 ⇒ 收**（本作 1,346 行） | 判据要覆盖 `len(ops)==1` |
| 5 | 名札 | 裸名（`佐伯`）或 `｛X＊＊｝` 在正文 | 名札带**样式前缀 `？`**（`？琉夏`） | 判名札前剥前缀 |
| 6 | スキンシップ载体 | `lang/ja/initialize` 的 `skinship_dialogue_*` | **根** `initialize` 的 `ss/nss/wnss/sstuto_rct` 之 **`StrData`** | 换作必查「同功能的表换了哪个 asset」 |
| 7 | 行内换行标记 | `\n` | **`**LF**`**（另有 `**TAG**` 富文本） | 清洗统一 `TAG` 正则 |
| 8 | 池 XOR 键 / `0x00→K` / `0316…0317` / `∋≡？` | — | **全同** | 同族只保证「容器头+块骨架」层面 |
| 9 | cast 核对源 | `lbl_to_char_id` 可用 | **`lbl_to_char_id` 含 GS4 人名（系列共用表）⇒ 不可用**；改用 `AddressBookAddress_N` + vndb | 外部核对源逐作验，别沿用 |

- 全量细节：`engines/konami-unity-bytes.md`（引擎核心）＋ `engines/konami-unity-bytes-works.md`（§8 GS1／§9 GS3）。
- 工具：`scripts/tokimemo_gs3_extract.py`。成品 72,703 行，check_text PASS。

## 10. ★ 第 4 作（GS4 4th Heart）：只差「池起点」一个字段

| # | 项 | GS1〜GS3 | GS4 |
|---|---|---|---|
| 1 | **池起点 / 代码区终点** | `poolOff = u32@4`（hdr[1]，且 hdr[1]==hdr[3] 全量） | **`poolOff = u32@12`（hdr[3]）、代码区终点 = `u32@4`（hdr[1]）**；本作 **2,525/11,754** 本 hdr[1]≠hdr[3] ⇒ 用 hdr[1] 会从**二进制区**读池 |
| 2 | 容器 | NSP(PFS0) → NCA | **XCI(gamecard)**：`hactool -t xci` 可解析 → 手工切 NCA → `hactool -t nca` **无需 `--titlekey`**（无 `.tik`，key area Key0/1/3=00…） |
| 3 | 附加源 | `skinship_dialogue_*` / `ss_rct…StrData` / `habatakinet_*` | **`chat_message`**（はばたきチャット `message`）＋ **`habaw`**（はばたきネット，字段拼写 `Piriod`）；スキンシップ 在 `scenario/ss/*` |
| 4 | 主角名 | `主人公`／`デイジー`／`バンビ` | **`マリィ`**（vndb `v26002`） |
| 5 | 名札表 | `AdvNameCh*`（GS3 仅 9 项） | **`AdvNameCh1..8` = 8 攻略対象**，最可靠 |
| 6 | 池 XOR 键 / `0316…0317` / 块分类 | — | **全同**（判据见 `pitfalls/B-lines.md`） |

★ 教训：**「头 16 B」不足以判定字段语义** —— 同为 16 B 头，GS3 的池起点在 u32@4、GS4 在 u32@12。
定法＝**对 hdr[1] 与 hdr[3] 各解一次池，看哪个出合法日文**（本作 2,437/2,525 命中 hdr[3]）。

## 11. GS4 追加コンテンツ（DLC）—— 两条易踩的连接层差异

| # | 项 | 本体 | DLC |
|---|---|---|---|
| 1 | 容器与 `.tik` | **XCI（gamecard）**：**无 `.tik`/`.cert`** ⇒ `hactool -t nca` **不需要** `--titlekey` | **NSP（PFS0）**：含 `.tik`/`.cert` ⇒ **必须** `--titlekey=$(<.tik>[0x180:0x190] 的 hex)` |
| 2 | romfs 布局 | `romfs/Data/StreamingAssets/…` | ★ **无 `Data/StreamingAssets` 层级**：直接 `romfs/scenario/…`（另有 `romfs/bg`・`character`・`still` 等） |

- ⇒ 复用同一提取器时，先建兼容布局：`<dlc>/compat/Data/StreamingAssets/scenario` ← 复制 `romfs/scenario`，
  再 `tokimemo_gs4_extract.py <dlc>/compat --no-chat --no-net`（**DLC 无 `chat_message`/`habaw` 等附加表**）。
- DLC 的 `.bytes` 头/池键/块骨架与本体一致（池起点同样取 `hdr[3]`）。
- 内容判据：**只用 `romfs/scenario/**` 判断有无文本** —— 服装类 DLC 只有 `fashion/`・`fashion_icon/`（Sprite/Texture2D）
  ＋ `index`（文件清单 TextAsset）⇒ **无文本**，直接跳过，别硬找。
- 追加キャラ DLC 的名札（如 `巴`／`大成`）可能**已存在于本体 `string_table` 名表** ⇒ 白名单无需扩充；
  实测名札泄漏 0（判据见 `pitfalls/B-lines.md`）。
