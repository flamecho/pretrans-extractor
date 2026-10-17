# 自研「テキスト方式 ADV」（クランク・イン）

> 路由/一句话索引见 `../engines.md`；主索引见 `../MEMORY.md`。

## 自研「テキスト方式 ADV」（プチレーヴ × Future Tech Lab）— クランク・イン
- 容器：PSV NoNpDrm **`.pkg`**（非 zip）→ `scripts/pkg2zip.exe <pkg> <zRIF>`（v1.8，产出 `… [TITLEID] [JPN].zip`，内含 `app/<TITLEID>/`）
  → `7z x` → `psvpfsparser.exe -i psvsrc/app/<TITLEID> -o dec/<TITLEID> -z <zRIF> -f cma.henkaku.xyz`（**必须联网访问 F00D**；网络被拦时报
  `Error: <unspecified file>(1): expected value`，**不是** zRIF 错误）。路径须 ASCII。
- 文件树：`eboot.bin`、`cmp.psarc`（**唯一文本容器**）、`cmpi.psarc`（立绘 `.gxt`）、`10…99.psarc`（语音 `.at9`）、`bgm/se/movie`、`sce_sys/manual/*.png`。
- **`cmp.psarc`**（标准 PSARC，`PSAR`+zlib 分块；`psarc_extract.py` 通用）内含：
  - `data/*.txt`（**UTF-16LE，逗号分隔指令表**）：
    `bg.txt`(背景 616) / `bgm.txt`(23) / `se.txt`(118) / `change.txt`(转场演出 56) / `chara.txt`(立绘差分 1416：`组,中_制夏_通常,kg02_ab,1,167,179`)
    / `chart.txt`(204：流程圖，20 字段，字段 14=章组 `Prologue/Act.N/Re-Act.N/END.`、15=标题、17+=解説，`,`=换行) / `flag.txt`(BE 存储)
  - **`script/scriptN.txt`** × 1622 = **行式剧本，1 行 = 1 步**（UTF-16LE，纯 `\n` 分隔，无隐藏标记）
  - `script/scriptN_l.txt` × 102 = label 表：`<global_step>:<LABEL>`（如 `646:ALBUM`）
  - `data/scrlst.txt` = `<label>,<scriptN>,<global_start>,<global_end>`（1622 条，**global 步号 = 全游戏文本框累计序号** 0…39,656）
- **行语义（3 类）**：
  1. **指令行**：行文本 == 任一指令表登记的标签（bg/bgm/se/change/chara 列），或 == `scrlst` 的 label，或形如 `NNN:LABEL`；
  2. **话者名行**：`姓<U+3000>名`（含全角空格、无句读、≤15 字）或**职务/端役词**（`係員/審査員/店員/園長/司会者/お母さん/先生/彼女/男性/女性/記者/スタッフ/団員/女優/アナウンサー/牧師/アナウンス/審査委員長/運転手/ドライバー/警官/救急隊員/ディレクター/助監督/ニュースキャスター/撮影スタッフ/売り子/司書/秘書/店長/招待客/時雨…` 及 `…員/…客/…スタッフ/…生徒/…学生/…店員/…記者/…観客/…通行人/…友人/…部員/…園児/…女優/…教師/…教諭/…たち/…Ａ-Ｇ/…１-３`）；
  3. **文本行**：其余 ⇒ **游戏内显示文本**（对话「」/ 地の文 / 选项）。
- **表外指令（须补排除）**：`場面転換中遠`、`スチルス中`、`ガイダンス`（SE 提示）、`タイトル画面へ`、chara 变体 `制春_困り・動揺目閉じ_マント無`、裸数字 `30`、`悲哀bgmout(bgmlong)`；
  通用判据：**含 `_` 且无标点** / **裸数字** / 含 `スチル|場面転換|フェード|bgmout|bgmin` 词干且无标点 / 末字为「音」的短行（`歩いて行く足音` 等 SE 提示）。
- **文本内标记**：`\`（反斜杠）= **框内软换行** → 合并（其后 `　` 保留）；`[橘]`/`[文月]` = 主人公姓名占位符 → inline 为 `橘`/`文月`；`『』` = 短信/台本；`　`(U+3000) = 缩进（保留）。
- **选项**：紧邻其后的**分支 label 组**（`xxx_da/_db`、`xxx_00a/b/c`）。形态涵盖和文（`聞いてみる`）、「」括注（`「ジェットコースターが……」`）、英文（`ｉｎｊｕｒｙ`/`Ｕｎｄｅｒｇｒｏｕｎｄ`）、`はい/いいえ`。
- **校验法（重要）**：`scrlst` 的 `end−start` = 该 label 的**文本框数**（≈ 本器文本行数）；对**末尾仅 1 个 label 的"叶子脚本"**核对最干净。
  本作 1035 本叶子脚本中 **869 本(84%) 精确相等**，其余 ±1（选项块计 1 步 vs. 逐项输出）。选项组使其 +N，含分支子脚本的父 label 其 range 会**累加子脚本步数**。
- **⚠ 引擎遗留数据**：`eboot → ELF` 的 UTF-16LE 串表含**同发行商他作《SA7 -SILENTABILITYSEVEN-》(Future Tech Lab, 2016) 的完整用語辞典**
  （`キャラクター/キーワード/組織/スポット/秘密道具/能力`，主角 `城あやか`、`ＡＲＫ` vs `ｕｎｋｎｏｗｎ`）——**与宿主作品无关**，提取时须核对（术语在本作剧本命中 0 即可判定）。ELF 另有本作**キャスト/スタッフ クレジット**（真数据）。

---

## 同族第 2 作：爽海バッカニアーズ!（PSV / PCSG00296 / 2014）
- **源**：NoNpDrm `.zip`（`Soukai Buccaneers NoNpDrm/PCSG00296/`）。⚠️ **`zip` 仍是 PFS 加密**（`eboot/psarc` 熵≈7.997；`param.sfo` 明文但 `pic0.png` 无 PNG 魔数）。
  → `psvpfsparser.exe -i <PCSG00296> -o dec -z <zRIF> -f cma.henkaku.xyz`（zRIF 见 `<psvdec>/games.json`）。
  **输入目录必须含完整文件树**（缺 `movie/` 会 `Directory ... does not exist` 中止）→ 先解 movie；路径须 ASCII。
- **容器**：文本**只在 `cmp.psarc`**（标准 PSARC v1.4，zlib 分块）；`a〜k/z/se/bgm/system` 全为 `.at9` 音频。
  ⚠️ **PSARC 块表零块语义**：本作 `size==0` = **真空块(0 字节)**，非 Kuriimu2 默认的 `blockSize`。判据＝使条目自带 offset 命中最多的解释（`za=0` 时 4500/4500）。`scripts/psarc_extract.py` 已自动判定。
- **脚本**：`script/<name>.txt`（UTF-16LE，1 行 1 步，共 1062）＝正本；`.bin` = 编译字节码（**无文本**）；`_l.txt` = 标签表 `<步号>:<LABEL>`（如 `504:SELECT_A`）。顺序取 `system/scrlst.csv`（1061）。
- **行语义**：① 指令＝`system/{image,bgm,se,effect,chara}.csv` 的标签 ＋ 全大写命令（`ALL/START/SEL_START/RE_SELECT/SELECT_A〜C/CHECK_COUNT/LOVER/NORMAL2/BG/PG/RETURN_POINT` 等）＋ 脚本名模式 `NN_xx_NNN(_N)` ＋ 裸数字；
  ② 话者名＝短行且**下一非表现类行以 `「/『/（` 开头**（或下一行已是话者名 → 覆盖「内部 ID＋显示名」双行，如 `ドレイク`＋`リアンの父`）→ 丢弃；
  ③ 其余＝上屏文本。**探测话者名时不可跨过分支持令**，否则地点选择项（`教会/大通り/裏通り`）会被误链。
- **标记**：`\`＝框内软换行(合并，后随 `　` 保留)；`<dicNNN>…</dic>`＝辞典链接(剥标签留词)；`『』`／`　`(U+3000) 保留。无 `Name[n]`/`%s`/`[…]` 占位符 → **主角固定名 リアン**。
- **选项**：chart（`system/chart_set.csv` 357 节点）＋ 脚本内联分支。选项文本＝紧邻分支脚本名之前的文本行（`支持する`→`00_kg_004_2/_1`）；`SEL_START` 是 flag 自动路由非玩家选择；chart 节点标题属 UI 未收。
- **用語辞典**：`system/dic.csv` 51 条，f6＝詳細解説（采此），f5 为「分类＋读音」式短注（按「不带读音」不取）→ `【見出し語】解説`。
- **杂项排除**：`縦揺れ/横揺れ/縦横`(震动)、`移動モード`、`ビンタ1`、`フレデリック自信21`、`洞窟内での足音1`。
- **半角中点**：`02_cr_042.txt` 原文 `･･･`(U+FF65×6，全作唯一) → 定值改全角 `・`。
- 成品 32,678 行【PASS】；工具 `scripts/baccan_extract.py`。
- **`\` 语义已实证**（说明书实拍＋统计）：**框内换行**，非翻页。判据＝段数上限 **3**、去 `<dic>` 后段长上限 **28 字** ⇒ **文本框固定 3 行 ×28 字，1 步 = 1 框 = 1 次点击**。`\　` 的 `　` 为次行缩进（保留）。
