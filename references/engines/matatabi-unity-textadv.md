# Matatabi 自研「纯文本 @命令 ADV」（Unity IL2CPP 宿主）

> 单作专用自研引擎，路由见 `engines-solo.md`；主索引 `../00-index.md`。
> 代表：**神凪ノ杜 五月雨綴り（NS-JP, `TID 0100B5801D7CE000`）**（2026-10-16）

## 容器（NS）
NSP(PFS0) → `nstool -x` → 4×NCA ＋ `.tik`。Program NCA 带 **RightsId ⇒ titlekey crypto**，
须 `nstool -k <keys> --tik <同目录 .tik>` 才能解 RomFS（否则 `AES-CTR Key was not determined`）。
RomFS = `1/Data/`：`Managed/Metadata/global-metadata.dat`（IL2CPP）＋ `data.unity3d`（框架，无正文）
＋ `StreamingAssets/ab_switch/`。

★ **`ab_switch` 下各成员都是 UnityFS AssetBundle**（带 TypeTree，直接 `UnityPy obj.read()`）：

| 成员 | 内容 |
|---|---|
| **`script`（1.6 MB）** | **624 个 TextAsset ＝ 全部剧本**（正文源） |
| `data`（35 KB） | 58 个 MonoBehaviour ＝ UI/系统/章节/画廊表（见「排除」） |
| `ov` | 34 个 TextAsset ＝ 立绘部件 **XML**（`OV001_body_a.png` 坐标），**无文本** |
| `advcg` / `sound` / `voice*` / `*.mp4` | 图/音/视频 |

★ 与既有 `unity-adv-hscript.md`（CRAZY CHA!N，`SET_TALK` 型 `.h`）**同属「Unity ＋ 自研 ADV ＋ 纯文本脚本」大类，但文法不同**，勿套用。

## 脚本格式（**纯文本**，UTF-8-BOM ＋ CRLF）

```
;一行注释                     ← 不上屏（文件头：ファイル名/場所/時間/登場人物 ＋ 制作备忘「※ＳＥ：」等）
@命令 [arg=val ...]           ← 引擎指令（@bg/@se/@bgm/@ov/@faceov/@setDraw/@fadein/@wait/@ctrl/@if…）
*L12|                         ← 标签
@talk [voice=… name=… real=…]    ← 一个文本框开始
正文行…                          ← 框内软换行（1〜3 行，**直接拼接**）
@hitret                          ← 文本框结束（= 一次玩家点击）
@choice text=选项文字 file=分支   ← 选项（一组若干条，`@choiceEnd` 收尾）
```

- **成行：一次点击 = 一行**（`@talk`…`@hitret` 之间所有正文行直接拼接；日文无需空格）。
- **名札**仅在 `@talk name=`（`姓　名` 全角空格分隔）⇒ **输出不加说话人前缀**，名札丢弃。
- `name=？？？ real=旭` ＝ 未揭示真名的说话人（`real=` 给真名，**用于 cast 核对**）。
- 选项 `text=` 含 `「」`（原文如此，保留）。
- 源内**笔误**（要容忍）：`@hitre`＝`@hitret`（框闭合，4 处）；`@fadei/@wai/@fram` 等＝命令笔误（无文本）；
  `km_t12_05` 有一处**漏写 `@hitret`** ⇒ 解析须「框内见 `@` 命令即先闭合当前框」。

## 宏 / 主角名
- 唯一宏 **`<pf>` ＝ 主角的名**（姓「木南」**字面固定**，不出现在宏里）。
- ★★**默认名出处 = `ab_switch/data` 的 `DataGlobalValue`**（可改名的**旁车默认值金矿**）：
  `ADV・主人公苗字 = 木南`、**`ADV・主人公デフォルトネーム = 瑞希`**；
  同表还有 `ダイアログ・名前入力 = 主人公の名前は[n]木南　<pf>でよろしいですか？`（印证 <pf> 位置）。
  ⇒ 无需从 eboot／代码反推，**Unity 系先去 `DataGlobalValue` 类表找 `デフォルトネーム`**。

## 排除（判据＝是否作剧本正文上屏）
`data` 的 `DataChapter1..6`/`DataChapterMain`（章选择：章名＋梗概）、`DataGlobalValue` 的 `ダイアログ・*`（系统确认文）、
`DataSpecialCg/Bgm/Movie/Omake`・`DataMiniGameInfo`・`DataAdvChara`（画廊/迷你游戏/人物名表）、
`data.unity3d` 的 `Start`/`Recollection`/`macro_*flash`/`立ち絵確認用スクリプト`/`test1`（框架/测试）、
`script` 的 `test_vitaOV`（≈`sp_10_02` 副本）与 `km_t_end*`（结局 flag 处理，无文本）。
**本作无「用語辞典/図鑑」文本**（全 romfs 检索 `辞典/用語/図鑑` 无命中）。

## 成品种类分布
`km_t00`(妖狐共通,76) → `km_t01/02/03`(妖狐 3 线) → `km_t10`(龍神共通) → `km_t11/12/13`(龍神 3 线)
→ `sp_01..06`(ご褒美) → `sp_10`(高耶編等おまけ)。分支文件（`km_t00_07a/b/c`）紧随主文件 ⇒ **按文件名自然序即推进序**。

## 工具
`scripts/kannagi_extract.py <script_txt目录> <out.txt> [--name 瑞希]`（含 `OVERRIDES` 整行定值表修原文笔误）。
配套：`scripts/unity_list.py`（列 bundle 对象）、`scripts/unity_textasset_dump.py`（导 TextAsset）。
