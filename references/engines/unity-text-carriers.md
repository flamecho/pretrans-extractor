# Unity（IL2CPP / Mono）文本载体速查 —— 2026-10-25/26 批实测 6 型

> **触发**：romfs 顶层是 `Data/`（含 `Managed`、`globalgamemanagers`、`level*`、`boot.config`）＝ Unity。
> **别急着找 "TextAsset 里的日文"** —— 本轮 12 部 Unity 作用了 **6 种完全不同的载体**，先查本表命中哪一型。

## 0. 先做三件定位（每件一分钟）

1. `ls Data/StreamingAssets/` —— 有 `Script/`、`Setting/`、`aa/`、`scenario/` 就直接看名字。
2. `ls Data/StreamingAssets/aa/` —— 有 Addressables（`catalog.json` + `*.bundle`）⇒ 剧本大概率在 bundle 里，见 §5/§6。
3. `find Data -maxdepth 2 -type f | head` —— 有 `sharedassets*.assets` ⇒ 文本可能被剥进静态资产（`§4` 的 `.book` 就在这）。

## 1. `Data/StreamingAssets/Script/*.h` —— 纯文本命令 DSL（最省事）

**代表**：Honey Vibes、My9Swallows TOPSTARS LEAGUE。
UTF-8 纯文本，`SET_TALK( 角色ID, WIN, "显示名", 语音ID, "正文" )` ＝ **一次点击一行**（L1 命令自定界）。
`\` ＝框内软换行（后跟全角空格＝缩进）⇒ 删掉合并；`SET_TALK_CLR` 关窗；48 种命令里**只有 SET_TALK 带正文**。
选项在 `Setting/CHOICE.csv` 的「選択肢」列（「問」与剧本里的 SET_TALK 重复，**不要重复收**）；辞典在 `Setting/DICT.csv`；
顺序按 `Setting/STORYFLOW.csv` 的「ファイル名」列（`CHAP###` 是章题、磁盘无脚本）。
工具：`scripts/honeyvibes_extract.py`。

## 2. `.kaiso` —— TextAsset 但内容是 **UTF-16LE + BOM**

**代表**：もし、この世界に神様がいるとするならば。（Rejet 行首命令 DSL，`Data/resources.assets` 里 74 个）
⚠ **UnityPy 直接 `str` 读会得到整片 `\udcXX`**：必须
`m_Script.encode('utf-8','surrogateescape')` 还原原始字节，**再按 BOM 判编码**（UTF-8 / UTF-16LE / UTF-16BE 都可能，另一作 `08_01_15` 就是 UTF-16BE+BOM）。
成行：`＠話者` 行 + 到 `<pb>` 为止 = 一次点击；块内全角缩进续行合并。

## 3. `.qui` —— **Lisp DSL** 纯文本

**代表**：白と黒のアリス for Nintendo Switch（UTF-8 BOM）
形如 `(message 話者 nil "本文")`；`(name-w)`/`(name-b)` 是双主角名宏。
ADV 单段页一行；`novel-mode 1` 的 NVL 同框追加页出「段行＋合并行」⇒ **双版对照**（本批唯一双版的 Unity 作之一）。

## 4. `.book` —— Utage（宴）MonoBehaviour

**代表**：ハンサムロンダリング（`Data/sharedassets1.assets` 里 251 个 `.book`；`aa/` 里 1,348 个 bundle 全是语音/立绘）
记录格式按 `storycraft/unity-utage-book` 逆，工具 `scripts/utage_extract.py`（复用 `scripts/dd_utage.py`）。
- 自证：251/251 全部 `end == len` 闭合。
- 剧情顺序取 `Boot.chapter` 的 PPtr 列表（不是文件名排序）。
- 成行：**一个 Text 命令行 = 一次点击**；行内 `\n` 是框内换行 ⇒ 合并。
- 自证（可复用）：单格硬顶 76 字 / 最多 3 段、续段 `　` 缩进与句末标点强相关、首段行首 `　` 为 0 处；
  `PageCtrl` 行空、`Next` 行全是章节标题、`BrPage` 行全无文本。

## 5. `UTXT` —— 自研二进制文本容器（Otomate「UMA」系）

**代表**：テミラーナ国の強運姫と悲運騎士団、ミストニアの翅望（两部同族，后者是 BKTR 全量压缩 NCA）
- 正文：`uma_talk_2.bytes`（纯消息表）；`uma_text_2.bytes` 是混合表（用語＋资源名），**别当正文用**。
- ★**字符表不是 metadata literal，而是 `Data/sharedassets0.assets` 里 TextAsset `chartable`（4413 字），
  且行尾 `\r\n` 也参与编号**（实测 max index 4410 ↔ 4413 上界；把 `\r\n` 删掉反而全乱）。
- `$$R` 注音标记要剥；`\n` + 行首缩进合并。
- 主角名：テミラーナ 是 `%`（主名）/`&&`（昵称）、ミストニア 是单个 `%`，两作都**无默认名 ⇒ 保留占位**。

## 6. Naninovel（定制）—— ★最容易「以为没有文本」

**代表**：ネオンクラッシュ、レッドベルの慟哭（两作同构，共 39,642 条 CMsg）
- 剧本 = `Assets/NaninovelData/Scripts/*.nani` 的 `Naninovel.Script` ScriptableObject，在 Addressable bundle 里
  （**bundle 自带 typetree，`read_typetree()` 可直接读，不需要 IL2CPP metadata**）。
- ★★**`CMsg.Text.value` 不是文本 key**：形如 `18,@18_0036,@18_0036z` = `(作者号, 语音资源名, 语音变体名)`。
  旁证：`@18_0036` ↔ `Assets/Sounds/Voice/18_0036.wav`，且 catalog 里 108 个 `z.wav` 与 `X`/`Xz` 两两成对。
- ★★**真正文 = 每条 `CMsg` 之前连续的若干条 `CommentScriptLine.commentText`**，按顺序拼接 = 一行台词。
- ★**为什么容易漏**：`Script.lines[]` 里只有 `{rid}`，真数据在 `references.RefIds[rid].data`
  （Unity `[SerializeReference]` 多态表），`CommandScriptLine` 还要再跳一层 `command:{rid}` 才到 `CMsg`。
  **只看 `lines[]` 字段名会得出「一条日文都没有」的错误结论**（本批两个代理先后栽在这）。
- 排除项已穷尽验证：`Data/` 下 93 个非 bundle 文件（`resources.assets`/`sharedassets*`/`level*`/`globalgamemanagers*`）
  无剧本正文（`global-metadata.dat` 的日文命中全是 UI 文案）；16,033 个 bundle 全量 LZ4 解压按日文密度排行，
  除脚本 bundle 外最高 1,808 ⇒ **不存在独立文本表**，`Assets/Static/DialogText.asset` 的 44 B MonoBehaviour 是空存根。
- 工具：`scripts/neon_dialog.py`（吃 bundle + il2cpp）、`scripts/redbell_dialog.py`（纯字节，吃 nani blob 目录）。
- 剔除：`話者名：`/`演技：`/`◆◇＝` 舞台指示/`BGM`/`SE`；开发注（`話者ID表`/`合成ボイス`/`ID変更` 等）按
  「前导型剥前缀、尾随型截到最后一个收尾引号、整行注记整行丢」处理。

## 7. 通用坑（与本批所有 Unity 作相关）

1. **`nsz -D` 写盘期间文件尾还是 0** —— 必须等 `[DONE]` 再读头判型，否则误判「坏件」。
2. **`hactool` 读不了含 CJK 的路径**（`Invalid argument`）⇒ 先复制成纯 ASCII 名再处理。
3. **HFS0 条目 `size` 是 u64**（`+0x08` 取 8 字节），只取低 32 位会把 >4 GB 的 NCA 截断
   （实测 10.3 GB→1.7 GB、7.2 GB→2.9 GB 两次）。
4. **不要用「含假名/汉字」过滤正文**（会丢纯标点台词与全角英文标题）；该判据只能用来标定剧本区起点。
5. 主角名占位（`%`、`%+&`、`&&`、`＆＆＆＆＆`、`{GivenName}`、`${FirstName}`、`<firstname>`）**找不到默认名就原样保留，禁猜**。
