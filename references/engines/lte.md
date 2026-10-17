# LTE 引擎（自研・纯文本标签脚本）

> 路由/一句话索引见 `../engines.md`；主索引见 `../MEMORY.md`。
> 首见作：**TOKYOヤマノテBOYS for V MAIN DISC（PSV / Rejet / 2017）**。
> 宿主＝ **Unity 5.4.4p2（Mono）**；脚本引擎本体＝ `Media/Plugins/LteVitaNativePlugin.suprx` ＋
> `Assembly-CSharp.dll`（类名 `ScenarioParser` / `*Command`）。

## 1. 判型（一次性确认「这就是 LTE」）
- 目录出现 `Media/StreamingAssets/LTE/`（`Movie/` `Texture/` 等）＋ `LteVitaNativePlugin.suprx`。
- `archive.psarc`（标准 Sony PSARC）里 `Media/resources.assets` 含 **4340 TextAsset**，其中剧本头为 `FF FE`（UTF-16LE BOM）。
- 剧本首行 `/////////////////////// TYB　シナリオ////`、含 `//●イベント名`、命令形如 `<pb>` `<set …>` `＠名前`。

## 2. 容器 / 链路

```text
PKG ＋ work.bin ──zzzrif.py──▶ zRIF ──pkg2zip -x──▶ app/PCSGxxxxx（PFS 密文）
   ──psvpfsparser（前台・联网；判据 keystone: matched retail hmac）──▶ dec/
   ├ archive.psarc  (PSAR 0001 0004 zlib；条目0＝名字表)  ── scripts/psarc_extract.py ──▶ Media/resources.assets
   │     └ UnityPy: TextAsset 4340 → 1229 剧本（UTF-16LE）＋ 3111 二进制 UI 布局
   └ Media/Managed/Assembly-CSharp.dll  ← ★用語辞典在这里（见 §5）
```
⚠ `pkg2zip` 等 Win32 exe 的**命令行参数**过不了日文路径（bash→ANSI 变 `¥ä¥Þ¥Î¥Æ`）⇒ cd 进源目录用**相对名**，或硬链接到 ASCII 路径。

## 3. 脚本语法（纯文本，非字节码）

```text
//注释（仅在 <> 之外切；<se name="…">//走り去る音 也对）
<jump file="TYB_A00_020_0">
<effect name="ゆっくり暗転" position="全体">
＠鈴木                      ← 说话人名札（行首 ＠，丢整行）
坊ちゃま、カップを          ← 正文（行内软换行合并）
<pb>                       ← ★一次点击边界
```

| 命令 | 处置 |
|---|---|
| `<pb>` / `<wait key="true">` | **一击边界**（两处都要切；只切 `<pb>` 会留下 888 个 >4 行的「页」） |
| `<select>` ＋ `<case value="X">` | **选项**（一行一条、按序；实测全部 `<case>` 都在 `<select>` 内） |
| `<ruby value="読">基底</ruby>` | 取**基底语** |
| `<tips name="X辞書NNN">見出し語</tips>` | 取見出し語（行内）；X 见 §5 |
| `<place name="…">` | **場所テロップ**（上屏字幕）→ 独立一行 |
| `<mobilephone title from>` | 头部略、**正文保留** |
| `<moshistart>`…`<moshititle>` | 「もしも」前提句＝标题；在 `<moshititle>` 处**切分** |
| `<monologue>` `<textbox>` `<textboxtype>` `<color>` | 样式/演出，忽略标签、保留文字 |
| `<voice>` `<set>` `<clear>` `<facechange>` `<move>` `<effect>` `<se>` `<bgm>` `<animation>` `<map>` `<eventgraphic>` `<movie>` `<skinship>` `<value>` `<if>` `<else>` `<jump>` `<block>` `<ending>` `<click>` `<picture>` `<allclear>` `<scenarioend>` `<moshiend>` | 无上屏文字，忽略 |
| `%name%` | **主角名宏**（inline） |

★**标签正则必须容忍属性值里的 `>`**：`<if condition="A && B >= C">` —— 用 `[^>]*>` 会在 `>=` 处截断，
把 `= 8">` 泄漏进正文（本作实测 33 行）。正解 `</?name(?:"[^"]*"|[^>"])*?>`。
★源脚本另存**标签残片**（`<effect …>` 后多余 `>` / `" position="全体">`，33 处）⇒ 按「属性片段 / 孤立 `>`」模式丢弃。

## 4. 文件命名（本作）

| 前缀 | 含义 |
|---|---|
| `TYB_A##` / `TYB_B##` / `TYB_C##` | HONEY MILK / SUPER MINT / DARK CHERRY **本編**（各 8 章） |
| `TYB_<盘>_<角色头>_BACK` / `_SUB` | 角色别 BACK/SUB シナリオ（角色头：Y 悠斗 / K 虎太郎 / A 歩夢 / I 伊織 / L ルーシー / T 拓海 / J ジェシー / TET テツ / SHI） |
| `TYB_[ABC]E_*` | ENDING（真/通常/恋愛） |
| `TYB_Z_*` | **前夜祭DISC**（`//●イベント番号：ＴＹＢ前夜祭`，a–g） |
| `TYBV_*` / `TYBPSP_*` | Vita / PSP 追加シナリオ |
| `book_*` | 「アナザーフェアリーテイル」SP イラスト短編 |
| `ifdata_*` | 「もしも」ミニシナリオ（`<moshistart>`） |
| **排除**：`JumpSkip_*`（`<jumpskip>`＋`<jump>` 纯跳转）、`cero_*`、`day` `ScriptTop` `ScriptBottom` `LTStart` `BTStart` `BTStart2` `ED_flag` `test_Title` | 系统/回想 |

## 5. ★用語辞典 ＝ 藏在 `Assembly-CSharp.dll` 的 .NET `#US` 字符串堆
- 堆内记录形如 **`[読み] [見出し語] [解説]` 三元组连续排布**（解説含 `<br>`），
  ID 串 `HM辞書NNN` / `SM辞書NNN` / `DC辞書NNN`（＝各碟）与 `Z辞書NNN`（＝Vita追加）另置于堆中。
- **锚定法**：拿脚本里 `<tips name="X">見出し語</tips>` 的見出し語去堆里找三元组 ⇒ **329/329 命中**。
  无脚本引用的 `Z辞書` 用「ID 紧邻三元组」回收 **131/147**（余 16 条与既存条目逐字相同 ⇒ 被堆**去重**，不可单独定位）。
- ⚠ **同一堆混有他作遗留**（本作里另有 `辞書001–219`＝江戸/天下五剣系别作辞典、`回想NNN`＝别作回想一覧；
  判据＝其词在本作脚本 **0 命中**）⇒ 整体排除（对齐铁律 12）。
- 输出 `【見出し語】解説文`（一行一条、去读音、`<br>` 合并）。源里 1 处半角 `｢` 归一为全角。
- 读法与工具：`scripts/us_walk.py` 的 `parse_pe/parse_metadata/walk_us`（`#US` 堆 = `[compressed len][UTF-16][1 flag]`；
  `ldstr` token 指向**长度前缀**，即 `token = dataoffset-1`）。

## 6. 工具
- `scripts/yamanote_extract.py` —— **自包含一键复现**（PSARC 解包 ＋ TextAsset 导出 ＋ 辞典回收 ＋ 成行）。
  `python scripts/yamanote_extract.py --dec <解密后目录> --out <成品.txt>`
- 依赖 `scripts/psarc_extract.py`、`UnityPy`。
