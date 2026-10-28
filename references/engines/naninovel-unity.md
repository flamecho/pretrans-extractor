# Unity（IL2CPP）＋ Naninovel（Elringus）—— 剧本文本提取

> > 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。本文件自包含：容器→解密→脚本→成行→排除→工具。

## 0. 识别特征
- RomFS = Unity `Data/`（`Managed/Metadata/global-metadata.dat` ⇒ **IL2CPP**；`StreamingAssets/aa/` ⇒ **Addressables**；
  `Data/resources.assets`）。
- `StreamingAssets/aa/Switch/` 里出现 **`naninovel-*_assets_all_*.bundle`**（scripts / characters / backgrounds /
  choicehandlers / textprinters / ui / spawn / voice / movies）⇒ **Naninovel**（Elringus，Unity VN 框架）定案。
- 引擎版本从 `Data/globalgamemanagers`（或 `level0`）里正则 `20\d\d\.\d+\.\d+[a-z]\d+` 取（本作 `2022.3.42f1`）。

## 1. 容器链（NS XCI）

```bash
# prod.keys 里 17B 的 mariko_master_kek_source_* 坏条目会让 hactool 报错 → 先滤成 prod_fixed.keys
./_sw/hactool.exe --keyset=_sw/prod_fixed.keys -t xci --securedir=<o> <game>.xci
```
- secure 分区里**同一 Title ID 可能出现两个 Program NCA**：一个无 Rights ID（key area crypto，＝本体）
  ＋ 一个带 **Rights ID + `Patch RomFS`(BKTR)**（＝**同捆更新**）。
- `hactool -i` 判据：`Encryption Type: Titlekey crypto` / `Master Key Revision` / 段表 `Partition Type: Patch RomFS`。
- ★ **必须用更新版**：比对两者 RomFS 文件表可知更新替换了 `global-metadata.dat` / `resources.assets` / 全部
  `naninovel-*` bundle。文件名 hash 不同（例：基础 `naninovel-scripts_assets_all_c8378de5….bundle`
  → 更新 `…0448084b….bundle`）。
- **BKTR 解法（实测成功；OZMAFIA 这套做法失败）**：
  1. ticket `*.tik` 的 `tik[0x180:0x190]`（**加密** titlekey）⇒ `--titlekey=<16B hex>`；
     hactool 打印 `Titlekey (Decrypted) (From CLI)`；`key area @0x300` 全 0 即 titlekey crypto。
  2. **先导出本体 RomFS 作 baseroot**：`-t nca --section1=base_sec1.romfs <本体NCA>`。
  3. 更新 ExeFS：`-t nca --titlekey=… --exefsdir=… <更新NCA>`。
  4. 更新 RomFS：`-t nca --titlekey=… --baseromfs=base_sec1.romfs --romfsdir=… <更新NCA>`
     ⇒ 拿到 `rom:\…` 完整文件列表（**成功判据＝能列出并解出文件**；失败会报 `Failed to read RomFS directory cache!`）。
     `--listromfs` 可只看清单。

## 2. 脚本 bundle 结构（Naninovel `Script`，IL2CPP）
- 每个脚本 = **1 个 MonoBehaviour**（本作 70 个；`m_Name` = 脚本名，如 `s_e14` / `s_com0` / `Start` / `Title` /
  `macro` / `m_go` / `replay` / `title_music`）。
- ⚠ **IL2CPP release bundle 无 typetree** ⇒ `obj.read()` **段错误**；`obj.get_raw_data()` 可拿字节但需手解。
- ✅ **正解：TypeTreeGeneratorAPI 生成 typetree**：

  ```python
  from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator
  gen = TypeTreeGenerator(unity_version)          # "2022.3.42f1"
  gen.load_il2cpp(open('exefs/main','rb').read(), open('.../global-metadata.dat','rb').read())
  env = UnityPy.load(bundle); env.typetree_generator = gen
  d = obj.read_typetree()                          # 不再段错误
  ```
  ⚠ 更新版的 `main`/`global-metadata.dat` 可能让 **LibCpp2IL 初始化失败**（报 `Fatal Exception initializing LibCpp2IL!`
  ／`Arithmetic operation resulted in an overflow`）；此时用**本体** `main`+metadata 生成的 typetree 读**更新** bundle
  （同引擎类字段结构未变，实测可行），并用更新版 `resources.assets` 侧证。
- `Script` 字段：

| 字段 | 内容 |
|---|---|
| `m_Name` | 脚本名 |
| `lines` | `[{'rid': N}…]`，**数组序 = lineIndex 序 = 显示序** |
| `references` | `{'version','RefIds':[{'rid','type':{'class','ns','asm'},'data'}]}`；rid 1000+ = ScriptLine，1000+N.. = 命令对象 |
| `textMap.idToText` | `{'keys':[…],'values':[…]}`＝Dictionary\<string,string\>：行文本片段 id→日文 |

- **ScriptLine 类别**（`references[i].type.class`）：
  - `GenericTextScriptLine`：`data={lineIndex,lineHash,inlinedCommands:[{rid}]}`；`inlinedCommands` → 命令对象 `PrintText`。
  - `CommandScriptLine`：`data={lineIndex,lineHash,command:{rid}}`；命令对象 class 见下。
  - `LabelScriptLine`（`labelText`）/ `EmptyScriptLine` / `CommentScriptLine` ⇒ 不产出。
- **`PrintText`（正文唯一来源）**：`data.playbackSpot{scriptName,lineIndex}`、`Text.raw.parts[]`、`AuthorId.value`、
  `Wait.value`。每个 part＝`{id,text,expression}`：
  - `id` 非空 → 取 `textMap.idToText[id]`；
  - `expression` 非空 → **运行时变量**（本作只有 `g_name`＝主角名 + 结局/章节题 `t_*`）；
  - `text` 非空 → 直接用它。
  ★ **一句台词常被变量切成多个 part**（`「` ｜ `{g_name}` ｜ `、貴様は…」`）⇒ **必须按 parts 顺序拼接**，否则丢内容/引号不配对。
- **选项**：`AddChoice`，`ChoiceSummary.value.parts`（同 parts 机制）＋ `GotoPath`。
- **`Wait`**：本作全部 =1（一 part 一句 = 一次点击）。若出现 `Wait=0` 需按「同框累积」处理。

## 3. `resources.assets` 里的 sidecar（★ 成行必需）
`Data/resources.assets` 是普通 Unity 序列化文件（`UnityPy.load()` 直接可读，**TextAsset 有内建 typetree ⇒ `obj.read().m_Script`**）。
同名 TextAsset 常**成对**存在，判据＝**正文是否以 `; Japanese <ja> to English <en> localization document for …` 开头**：

| TextAsset | 格式 | 用途 |
|---|---|---|
| **`Script`（不带头的日文份）** | `t_c0: プロローグ` 一行一条 | **`{t_*}` 变量解析**：章节题 / 編題 / 结局名 / bad-end 名 / `t_name`(主角默认名) |
| `Script`（带头的英译份） | `; プロローグ` ＋ `t_c0: Prologue` | 英译工作稿，**不用** |
| **`Tips`（不带头的日文份）** | `key: 見出し語 \| カテゴリ \| 解説` | **用語辞典** ⇒ `【見出し語】解説文` 一行一条、去读音、并入末尾 |
| `CharacterNames`（不带头的日文份） | `key: 日文名` | 说话人 `AuthorId` → 显示名（**交付不加前缀**，仅用于外部核对） |
| `<脚本名>`（带头的英译份） | `# 6f` ＋ `; 日文` ＋ 英文 | 逐行 hash→译文，**与 bundle 的 `idToText` 同源**，可用于比对/侧证 |

> managed text 条目的分隔符**随 Naninovel 版本变**（基础版 `^`、更新版 `|`）⇒ 解析按「split 后取首尾」写。
> `CustomVariablesConfiguration`（`resources.assets` MonoBehaviour，名字在第 28 字节）里可直接读变量初值（本作 `g_name="フィエナ"`）。

## 4. 成行/排除（本作口径）
- **收**：`PrintText`（正文）＋ `AddChoice`（选项，一行一条按序）＋ `{t_*}` 上屏扉文（章节题/編題/结局名/bad-end 名，就地解析）
  ＋ `Tips` 用語辞典（并入末尾）。
- **不收**：`Start`（＝**调试跳转菜单**，`debug==true` 默认关，32 条选项）、`Title`/`title_music`/`replay`（系统·UI，0 文本）、
  `macro`（死代码 helper，唯一 `{t_bad1}` 与正文重复）、`m_go`/`m_endroll`（0 文本）。
- **顺序＝`@goto` 链实测**：共通 `s_com0`→`s_com1..8` → 四条角色线（`s_e*`/`s_i*`/`s_m*`/`s_v*`，各自 `n → n+1` 逐环相接）
  → `s_n1` → 番外 `ss_1`。**别按 bundle 内对象序**（那是 hash 序，与剧情无关）。
- **互斥分支去重**：Naninovel 的「可变主角名」套路是
  `@if g_name=="默认名"||g_name=="罗马字"` → 字面名台词 ／ `@else` → `{g_name}` 台词 ⇒ 两支渲染同文 ⇒ **取一支**。
  判据必须写「**紧邻上一条是 `@else`/`@elseif` 且（标记清理后的）文本全同**」。
  ⚠ **别用「行号差 2」判**（普通相邻行也差 2）；⚠ **必须在标记清理后的文本层比较**（带 `<tip>` 的行否则漏去重）。
  ⚠ 同为「相邻同文」但**说话人不同**的（`p` 说完 `ish` 说）是**真两句**，**不可去重**。
- **行内标记**：去 `<space=1em>`（纯排版缩进）、`<br>`；`<tip="x">WORD</tip>` ⇒ **`WORD`**（保留可见文字、去 tooltip 标记）。
- **变量**：`{g_name}` ⇒ 主角默认名（`t_name` / `CustomVariablesConfiguration`，本作 `フィエナ`）；`{t_*}` ⇒ `Script` managed text。
- **不加说话人前缀**；行内不换行；UTF-8 BOM / 纯 LF。

## 5. 外部核对
vndb：`POST api.vndb.org/kana/vn {"filters":["search","=","<标题>"],"fields":"id,title,alttitle,developers.name,platforms"}` 取 v 号。
⚠ **实测 `/character` 端点 `filters` 返回 400、`/vn` 的 `characters{}` 字段不存在** ⇒ 直接
`WebFetch https://vndb.org/v<id>/chars` 取 cast（含 `original` 日文名）。本作 `v50653`：主角 フィエナ（**Nameable**）、
エマニュエル・ド・ボーモン / イスマイール / メロディー / オリヴィエ・パケ（四条线）＋副角色，全部对上。
★ **author id 与角色字面名可能不同**（本作 `vivi` → **オリヴィエ**、`mel` → メロディー）⇒ 必查 `CharacterNames`。

## 6. 工具
- `scripts/naninovel_extract.py` —— bundle → `_scripts.json`（typetree 生成、parts 拼接、`after_else` 标记、name 替换）。
- `scripts/naninovel_assemble.py` —— `_scripts.json` ＋ managed text ＋ Tips → §0 成品（顺序表、互斥去重、标记清理、`{t_*}` 解析、辞典并入）。
- 侧车导出：`python scripts/unity_textasset_dump.py <resources.assets> <out_dir>`（`obj.read().m_Script`）。
- `scripts/ozmafia_nca.py info <nca>` —— 看 NCA 头 / 段表 / key area（判 titlekey crypto 与 BKTR 用）。

> 通用技术/坑（IL2CPP typetree 生成、同捆更新/BKTR 解法、互斥去重判据）另见 skill
> `references/S4-unity.md`；本文只留本作实证数据。
