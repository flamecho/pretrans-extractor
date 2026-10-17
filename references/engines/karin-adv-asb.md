# 花梨エンターテイメント 自研 ADV（`.asb` 编译体 ＋ 同捆 SJIS `@命令` 源脚本 `.txt`）

> 单作专用自研引擎（见 `engines-solo.md`）。代表作：**新宿羅生門 ―Rashomon of Shinjuku―**
> （NS, `01005a401d766000`, 2024-08-08, 販売 Idea Factory / ブランド ALTERGEAR / 開発 花梨エンターテイメント, vndb v34021）。
> 首见于 2026-10-16。

## 1. 容器

- **Switch XCI**：`nstool -k <你的 prod.keys> --secure <o> <xci>` → secure HFS0（4 项：Program 3.36 GB ＋ Control ＋ Manual/Data ＋ cnmt）。
  Program NCA 为 **Game Card / 明文 key area**（Content Type=Program, Key Generation=17） ⇒ `--part1 <o> <nca>` 直接解 RomFS，**无需 titlekey**。
- XCI 的 `update/` 分区（235 NCA）＝**卡带同捆 SystemUpdate 固件**，非游戏补丁（无 BKTR）⇒ 忽略。
- RomFS：`script/  fixeddata/*.json  system/{bin,json,font}  battle/{qdata.json,kotodama/*.png,lwf,texpack}  ui/  lwf/  mask/  movie/  picture/  se/  sound/  voice/  shader/  mcfappframe.json`。
  中间件旁车：`mcfappframe.json`（框架）、`lwf/`（LightWave Flash 演出）、`battle/kotodama/a_txt_<hex>_n.png`（**按 Unicode 码位命名的逐字 PNG**＝战斗「コトダマ」字效，非文本源）。

## 2. 脚本：`.asb`（编译）＋ `.txt`（源）成对出货

```
s00.asb : "ASB\0" + u32BE payloadSize + u32BE payloadSize + u32BE stmtCount + u32BE hash
          → 之后为字节码（**不含 SJIS 原文**，全库无 raw 日文串 ⇒ 不必逆它）
s00.txt : SJIS / CRLF 纯文本
          // 注释
          @show_bg( 0, "bg/bg003" ); @update( _NORMAL );
          @label("line0002"); @play_music( 0, "50" ); @system( 47, 2 );
          @save_point(); @update( _FADE, 500 );
          @play_voice( 99, "story/001/s00/zz/v_zz00003" );
          @text("逃亡者", "っ……ようやく手に入れたぞ……"); @click(); @cls();
```

- ★★ **源是否过期＝零成本可验**：`.asb` 头第 3 个 `u32BE`（语句数）与 `.txt` 的语句数逐文件吻合（±0.5%）。
  实例：`001/s00` f3=4871 ↔ txt `;`=4861；`ExtraStory/s01` f3=48 ↔ txt 45。
  **吻合 ⇒ `.txt` 即编译源、以 `.txt` 为文本权威源，不必解 `.asb`**（遵守 skill ㉙「先看脚本是否直接可读，别默认上 VM/码表」）。
- `main`（ExeFS NSO）内含 `.asb` 字符串 ⇒ 运行时加载编译体；`.txt` 为随包源脚本，两者同源。
- 文法：`@命令( 参数… );` ／ 行注释 `//` ／ 赋值 `@svarNNN = 1;` ／ 条件 `@if( @varNN == k ) { @goto("tag_x"); }`。

## 3. 承载文本的命令（全库普查：205 种命令，**仅 2 条带日文串**）

| 命令 | 语义 | 条数（新宿羅生門） | 处理 |
|---|---|---|---|
| `@text("speaker","body")` | **一个文本框 = 一次点击**（后随 `@click(); @cls();`） | 32,140 | 取 body、**丢 speaker** |
| `@select_text(n,"opt")` | **选项**（后随 `@select()` 或 `@select_timer(sec,flag)`） | 283 | 一行一条、按序 |

- 其余命令参数**全为数值或 ID**：`@system(47,2)`＝演出/窗口、`@show_chara/@show_panel/@show_face/@play_voice/@play_music` 只带资源 ID。
- 串内语法：**软换行 `\n`（字面反斜杠 n）须合并**；**注音 `|基底語|よみ|` ⇒ 还原为基底语**（上屏显示基底语）；转义 `\"`。**无** `%s`/`Name[n]`/控制码/PUA。

## 4. 主角 / 改名

- `fixeddata/System.json`（UTF-8-BOM）→ `NAME_ENTRY` ＝（空）＝ **名前入力なし** ⇒ **主角固定名**（新宿羅生門＝**沖田洸**）。
  `NAME_DEFAULT`=「きなこもち」/`FamilyNAME_DEFAULT`=「小倉」为**引擎模板残留**（该引擎亦用于乙女系，UI 串 `str_ja.bin` 内含「ヒロイン名を入力してください」等他作口吻），**不可采用**。
- `NarrationName` = `【語り】` ＝ 预约名（名前欄非表示）⇒ 按旁白。

## 5. 排除（判据＝是否正文上屏）

- **开发 QA 脚本**：文件内含「拡張子確認用／3Dカメラ確認／カットイン確認／ステータステスト」等 ⇒ 整体剔（新宿羅生門＝`006/s11..s16`、`ExtraStory/s11..s19`）。
- **「テストシナリオ」占位脚本**：文件内含「テストシナリオ／テストを終わり／エクストラト?(ストーリー|シナリオ)」⇒ 整体剔（新宿羅生門＝SubStory/ExtraStory 共 59 文件）。★**出货基础卡带确实可能整块是占位**，`.asb` 尺寸同样极小 ⇒ 逐文件证伪，勿假定副线都是真内容。
- **战斗横幅**：`@text("", "【決闘】/【同志戦】… 対 …")` ⇒ 战斗模块 UI（对应 `ui/40_novel/05_battle_encount`）⇒ 剔。
- `battle/qdata.json`（741 条「斬れ！『悪鬼』」问答）、`fixeddata/*.json`（系统数据）、`system/bin/str_ja.bin`（569 条 UI 串）、`ui/80_manual/*`（**图片**手册）⇒ 系统/UI。

## 6. 工具

- `scripts/shinjuku_text.py` —— 自包含提取器（`python scripts/shinjuku_text.py [脚本目录] [输出txt]`）。
  收录顺序 `001…006 → SubStory/001…006 → ExtraStory`；顶部含 `EXCLUDE_FILES`／`STUB_MARK`／`BATTLE_BANNER`／`REPAIRS` 四张表。
- 用語辞典：`fixeddata/Word.json`（`Word`/`Ruby`/`Description`）→ `【見出し語】解説文`、一行一条、丢读音、条内换行合并、**并入成品末尾**。
- 品检：`python scripts/check_text.py <成品> --name 沖田洸`。
