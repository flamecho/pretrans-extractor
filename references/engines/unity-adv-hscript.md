# Unity (IL2CPP) + 自研 ADV · **纯文本脚本变体**（`.h`）

> 首作：**CRAZY CHA!N -エルピスの鎖-**（NS/XCI，オトメイト 2026-07-09，vndb `v54934`）。
> 与同族 `unity-adv.md`（PSARC/TKG/CSR1.00 二进制脚本）**不同**：本变体剧本是**纯文本 `.h`**，提取几乎是纯文本解析。
> 全量细节见工作区 `提取结果/解析报告/[NS-JP]CRAZY CHA!N -エルピスの鎖-_解析报告.md`。

## 1. 认类型
- RomFS = `Data/Managed/Metadata/global-metadata.dat`（IL2CPP）+ `Data/StreamingAssets/`。
- **本变体判据**：`Data/StreamingAssets/Script/EV###-###.h`（502 个，UTF-8 BOM + CRLF）+ `Data/StreamingAssets/Setting/*.csv`。
  `.h` 不是 C 头文件，是**自研脚本**：`SET_TALK(...)` / `@REWORD(...)` / `CHOICE_JUMP(...)` / `SET_CH` / `FADE_*` / `NEXT_PAGE` / `:DIVxxxx` 标签。
- IL2CPP 元数据可当「**引擎类名实证源**」：`grep` 类名可判定行为（本作靠 `CmdSetTalk/CmdNextPage`（脚本命令集）
  与 `GetEvTitle/SetTitleText/AdvChapShow`（标题显示）**互补**，证出「扉文由引擎自动上屏、脚本内无 title 命令」）。

## 2. ★ 脚本格式与成行

```
SET_TALK( <ch>, <win>, "<話者名>", <voice>, "<正文>" )     ← 一次点击 = 一个文本框（收）
@REWORD( ... )                                            ← 「名前差分」版：玩家改过主角名时才显示（默认名口径 ⇒ 不收）
CHOICE_JUMP( <key>, DIVxxxx, DIVyyyy, … )                 ← 选项正文在 Setting/CHOICE.csv（按 key 取）
// 行注释、/* … */ 块注释                                    ← 制作注记（选择支说明/SE 名）⇒ 不收
SET_CH / SET_BG / WAIT / SE_PLAY / FADE_* / NEXT_PAGE …    ← 演出, 无正文
```
- **改名差分**：每条含名台词成对写 —— `//名前差分なし` + `SET_TALK` ／ `//名前差分` + `@REWORD`。
  **两个版本正文不同**（前者更自然）。默认名 ⇒ 取 `SET_TALK`、**跳 `@REWORD`**（可用 `--with-reword` 换口径）。
- **正文内标记**：`\` 框内软换行（删/合并）、`\　` 换行+全角缩进（连空格删）、`$語$` 用語强调（去 `$`）、
  `#字#[よみ]` ルビ（去读音留基底）、`&` 主角名占位（→默认名）、`\"` 个别脚本开头引号前多一 `\`（容错剥）。
- **选项条数校验**：`CHOICE_JUMP` 实参个数（去 `NULL`）必须 == `CHOICE.csv` 同 key 的行数 ⇒ 本作 108/108 全中（可当自检）。
- **`CHOICE.csv` 的 `問` 列别收**：它是选项前的提问，且**同文已作为 `SET_TALK` 在脚本里**（108/108 均能找到）⇒ 收 CSV 会重复。
- **排序**：`Setting/STORYFLOW.csv` 的 `ファイル名` 列 = 游戏自身剧本流（**≠ 文件名字典序**；含无脚本的 `CHAP*` 跳过）。
- **`Setting/EV_TITLE.csv`** 第 5 列 = 每剧本一句**扉文**（直接上屏标题；按 SKILL.md §0「直接上屏特效・扉文」收，可用 `--no-title` 关）。

## 3. ★ XCI 侧：`hactool -t xci` 报 `XCI partition is corrupt!` 的对策
- 读 hactool `xci.c`：该报错**不是 HFS0 解析失败**，而是 `check_memory_hash_table_with_suffix()`
  用 header@`0x140` 的 `hfs0_header_hash` 校验 `0xF000` 处 0x200B HFS0 头（后缀 = compat type 1B）。
  源码只试 `COMPAT_GLOBAL(0)`/`COMPAT_CHINA(1)`；**实测后缀 0..255 全不中** ⇒ 需 `xci_header_key`（本机 keyset 无）。
- ⇒ **文件其实完全标准**，按 HFS0 布局手工切 NCA 即可（`scripts/crazychain_xci.py`）：
  `hfs0_file_entry_t{u64 offset, u64 size, u32 string_table_offset, u32 hashed_size, u64 reserved, hash[0x20]}`（0x40/条），
  **offset 相对「HFS0 头+条目表+字符串表」之后**；root HFS0 @`0xF000` → `update`/`logo`/`normal`/`secure`（`secure` 含全部 NCA）。
- ★★ **NCA 头是 `header_key`(AES-XTS/0x200) 加密的，不是 plaintext `NCA3`**（hactool `nca_decrypt_header`）。
  ⇒ **「整文件扫不到 `NCA3` 就断定是密文」是错误推理**（本作一开始走了这条弯路）。判「是否要 titlekey」看 hactool 打印的
  `Distribution type` / `Encryption Type`：`Gamecard` + `Standard crypto` ⇒ **不需要 titlekey**，直接 `-t nca --romfsdir=` 即可。

## 4. 工具
- `scripts/crazychain_xci.py`：XCI → secure 分区 NCA 切出（`--list` 只看结构）。
- `scripts/crazychain_extract.py`：`.h` + `Setting/*.csv` → 全文本（`--no-title` / `--with-reword`）。
