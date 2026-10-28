# Unity(IL2CPP) 与 Naninovel（含 Switch「同捆更新 / BKTR」）

> 首作：**魔女と亡霊のヴォロンテ**（NS/XCI，LocaGames 2025，Unity 2022.3.42f1 + IL2CPP + **Naninovel**）。
> 本文＝**通用技术/坑**；该作全量细节见 `engines/naninovel-unity.md`。

## 1. 认类型
- Unity 特征：RomFS/目录里 `Data/`、`Data/Managed/Metadata/global-metadata.dat`（**IL2CPP**；有 `Data/Managed/*.dll` 才是 Mono）、
  `Data/StreamingAssets/aa/`（Addressables）、`Data/resources.assets`。
- Unity 版本：`Data/globalgamemanagers`（或 `level0`）里正则 `20\d\d\.\d+\.\d+[a-z]\d+`。
- **Naninovel**（Elringus，VN 框架）判据：`aa/Switch/naninovel-{scripts,characters,backgrounds,choicehandlers,textprinters,ui,spawn,voice,movies}_*.bundle`。

## 2. ★ IL2CPP bundle 无 typetree ⇒ 不能直接 `obj.read()`
- 症状：`UnityPy` 对 MonoBehaviour 调 `obj.read()` **段错误**（进程被 SIGSEGV 杀掉，常常连 stdout 都吞掉 → 看起来「脚本没输出」）。
- 正解（UnityPy ≥1.25 + `TypeTreeGeneratorAPI`）：

  ```python
  from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
  gen = TypeTreeGenerator(unity_version)                       # 与游戏一致，如 "2022.3.42f1"
  gen.load_il2cpp(open('exefs/main','rb').read(),              # IL2CPP 可执行（NSO/ELF）
                  open('.../global-metadata.dat','rb').read())
  env = UnityPy.load(bundle); env.typetree_generator = gen
  d = obj.read_typetree()                                      # dict，不再段错误
  ```
- **兜底**：若「更新版」的 `main`/`global-metadata.dat` 让 LibCpp2IL 报
  `Fatal Exception initializing LibCpp2IL!` / `Arithmetic operation resulted in an overflow`，
  退回**本体版本**的 `main`+metadata 生成 typetree 再读**更新** bundle（同引擎类字段通常未变；用更新版
  `resources.assets` 的旁证文本来侧证）。
- TextAsset 有内建 typetree ⇒ `obj.read().m_Script` 直接给正文（别手写「4 字节长度+名字」的偏移猜法）。

## 3. ★ Switch：XCI 内可能同捆「全量替换型」更新（必须用更新版）
- 症状：`hactool -t xci --securedir=` 后 secure 分区里**同一 Title ID 出现两个 Program NCA**
  （一个无 Rights ID＝本体，一个带 **Rights ID + `Patch RomFS`(BKTR)**＝同捆更新）。
- 判据＋动作：**比对两者 RomFS 文件表**（文件名 hash 不同即更新改了文件）。Unity 游戏更新常替换
  `global-metadata.dat` / `resources.assets` / 全部 `naninovel-*` bundle ⇒ 用本体数据会漏/错内容。
- **BKTR 解法**（实测已成功；旧记录曾失败）：
  1. ticket `*.tik` 的 `tik[0x180:0x190]`＝**加密** titlekey ⇒ `hactool --titlekey=<16B hex>`；
     hactool 打印 `Titlekey (Decrypted) (From CLI)`；`key area @0x300` 全 0 ⇒ `Encryption Type: Titlekey crypto`。
  2. **先导出本体 RomFS 当 baseroot**：`-t nca --section1=base_sec1.romfs <本体NCA>`。
  3. 更新 ExeFS：`-t nca --titlekey=… --exefsdir=… <更新NCA>`。
  4. 更新 RomFS：`-t nca --titlekey=… --baseromfs=base_sec1.romfs --romfsdir=… <更新NCA>`
     ⇒ **成功判据＝能列出/解出 `rom:\…` 文件**；失败报 `Failed to read RomFS directory cache!`。
     `--listromfs` 可先只看清单。
  - 另：`prod.keys` 里 17B 的 `mariko_master_kek_source_*` 坏条目会让 hactool 报 key 长度错 ⇒ 先滤成 `prod_fixed.keys`。

## 4. Naninovel 脚本结构（要点；全量见引擎分册）
- 每脚本 1 个 MonoBehaviour；字段 `lines[{rid}]`（**数组序＝显示序**）/ `references.RefIds`（rid1000+＝ScriptLine）/
  `textMap.idToText`（Dictionary\<string,string\>：文本片段 id→日文）。
- **正文只在 `PrintText.Text.raw.parts`**：part＝`{id,text,expression}`；`id`→`textMap`，`expression`→运行时变量。
  ★ **一句台词常被内联变量切成多个 part**（`「` ｜ `{name}` ｜ `、…」`）⇒ **必须按 parts 顺序拼接**，否则丢文本、
  且会制造「行首 `「` 未收尾」的引号不配对假象。
- 选项＝`AddChoice.ChoiceSummary`（同 parts 机制）＋ `GotoPath`；说话人＝`PrintText.AuthorId`（**不前缀**）。
- `{t_*}` / 主角默认名在 **`resources.assets` 的 TextAsset「Script」managed text**（`key: 值` 一行一条）；
  **用語辞典**＝TextAsset「Tips」；角色名＝「CharacterNames」。
  ⚠ **同名 TextAsset 常成对**：以 `; Japanese <ja> to English <en> localization document for …` 开头的是**英译稿**，
  不带头、值直接是日文的那份才是**默认日语**。（managed text 分隔符随版本变：`^` 或 `|`。）
- **顺序**按 `@goto`/`@gosub` 链实测（例：共通 `s_com0→s_com1..8` → 四条角色线各自 `n→n+1` → 番外）。
  **别按 bundle 对象序**（hash 序，与剧情无关）。

## 5. 互斥分支去重（Naninovel「可变主角名」套路）
- 形态：`@if g_name=="默认名"||g_name=="罗马字"` → 字面名台词 ／ `@else` → `{g_name}` 台词 ⇒ 两支渲染**同文** ⇒ **取一支**。
- 判据写死为：「**紧邻上一条是 `@else`/`@elseif`** 且**（行内标记清理后的）文本全同**」。
  - ⚠ 别用「行号差 2」——普通相邻两行也常差 2（中间夹一条命令）。
  - ⚠ **必须在标记清理后的文本层比较**——否则 `…<tip="x">WORD</tip>…` 的行漏去重（本作 `s_com4` 实例）。
  - ⚠ 同为「相邻同文」但**说话人不同**者（`p` 说完 `ish` 说「……」）是**真两句**，**不可去重**。
- 行内标记：去 `<space=1em>`（纯排版）、`<br>`；`<tip="x">WORD</tip>` ⇒ **`WORD`**。

## 6. 外部核对
- vndb：`POST api.vndb.org/kana/vn {"filters":["search","=","<标题>"],"fields":"id,title,alttitle,developers.name,platforms"}` 取 v 号。
  ⚠ 实测 `/character` 端点 `filters` 返 **400**、`/vn` 的 `characters{}` 字段**不存在** ⇒ 直接
  `WebFetch https://vndb.org/v<id>/chars` 取 cast（含 `original` 日文名）。
- ★ **author id ≠ 角色字面名**（本作 `vivi` → オリヴィエ、`mel` → メロディー）⇒ 以 `CharacterNames` 为准再比 vndb。

## 7. ★ 变体：Unity 自研 ADV「**纯文本脚本**」（`.h` + `Setting/*.csv`）
- **实例**：CRAZY CHA!N -エルピスの鎖-（NS，2026-07-09，Otomate）。→ 不入 `.assets`，无 IL2CPP 字节码解析。
- **判型**：`Data/StreamingAssets/Script/EV###-###.h`（UTF-8 BOM / CRLF 的**纯文本**，SET_TALK 一行一次点击）
  ＋ `Data/StreamingAssets/Setting/*.csv`（`CHOICE=选项` `EV_TITLE=扉文` `STORYFLOW=剧本文流顺序` `DICT=用語辞典`）。
- **成行**：`SET_TALK( ch, win, "話者名", voice, "正文" )` 第 5 参；`@REWORD` 是**改名差分版**（`//名前差分なし` 孪生行）⇒ 默认不收。
- **取值口径**：`unquote`＝取到**首个未转义 `"`**（见坑索引 ㉑）；`\`=框内软换行合并（`\　` 连全角空格一并去）、
  `$語$`→去 `$`、`#字#[よみ]`→去读音、`&`→主角名。
- **选项**：`CHOICE_JUMP` 处按 `CHOICE.csv` 落位，**条数须 == 实参数**（本作 108/108）；`CHOICE.csv` 的**问句列不收**
  （脚本里已有同名 `SET_TALK`，否则重复）。**排序用 `STORYFLOW.csv` 的文件名列**（≠ 文件名字典序）。
- 工具：`scripts/crazychain_extract.py`（`--no-title` / `--with-reword` 可调）、`scripts/crazychain_xci.py`（见下）。

## ★ XCI / NCA 判型 ＋ 纯文本脚本取值（2026-10-14，CRAZY CHA!N 立）

⑲ ★★ **`hactool -t xci` 报 `XCI partition is corrupt!` ≠ HFS0 布局坏**：读 `xci.c` 可知该报错来自
  `check_memory_hash_table_with_suffix()` —— 用 header@`0x140` 的 `hfs0_header_hash` 校验 `hfs0_offset` 处
  `hfs0_header_size` 字节（后缀 1B = compat type）。源码只试 `COMPAT_GLOBAL(0)`/`COMPAT_CHINA(1)`；
  **本机无 `xci_header_key` 时后缀 0..255 可能全不中** ⇒ 直接失败。**文件其实标准** ⇒ 按
  `hfs0_file_entry_t{u64 offset,u64 size,u32 string_table_offset,u32 hashed_size,u64 reserved,hash[0x20]}`
  （0x40/条，offset 相对「头+条目表+字符串表」之后）手工切 NCA，再 `hactool -t nca`。工具 `scripts/crazychain_xci.py`。
⑳ ★★ **NCA 头是 `header_key`(AES-XTS/0x200) 加密的，不是 plaintext `NCA3`**（`nca_decrypt_header`）
  ⇒ **「整文件扫不到 `NCA3`/`HFS0` 就断定是密文」是错误推理**（曾据此走弯路）。判「要不要 titlekey」看 hactool 打印的
  `Distribution type` / `Encryption Type`：`Gamecard` + `Standard crypto` ⇒ 直接 `-t nca --romfsdir=`。
㉑ ★ **纯文本脚本取「引号内文本」要取到「第一个未转义的 `"`」，不是「首尾各去一个引号」**
  （2026-10-14，CRAZY CHA!N）：源数据偶有笔误在字符串末尾多写一个 `"`（`"…」""`）；
  用 `a[1:-1]` 会取「首个↔**末个**引号」之间的内容 ⇒ **多余引号被吃进正文**（成品行尾多一个半角 `"`）。
  修法＝正向扫描到首个未转义 `"` 即停（`\"` 视为字面引号），无闭合引号才取到行尾；
  拆分参数（顶层逗号）也要同步加 `\"` 感知。**孪生行**（同句 `@REWORD` / `//名前差分` 版）是零成本判据。

㉒ ★ **XCI 的 `update` 分区未必是「游戏补丁」**（2026-10-15，カエル畑DEつかまえて☆彡）：卡带 dumps 里常见的是
  **同捆 SystemUpdate**（本作 385 MB・约 180 个 NCA，**其 `.cnmt.nca` 头为高熵＝系统密钥加密，读不出 title id**）
  ⇒ **与游戏文本无关，别去里面找 patch**。判据＝**一堆 NCA ＋ 每个都配 `.cnmt.nca` 且头部非明文**；
  真正的游戏更新＝**指向同 TitleID 的单个 Program NCA**（带 BKTR／Patch RomFS，见 ⑰）。本作文本只在本体 `secure` 分区。
