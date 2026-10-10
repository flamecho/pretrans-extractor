# KiriKiri XP3（标准 / DropWave OTag / 区间 1 字节 XOR）

> 路由 / 一句话索引见 `../engines.md`。

## KiriKiri（吉里吉里）XP3 + DropWave「OriginalTag」— クリムゾン・ロワイヤル
（QuinRose, PC 2009／前作 クリムゾン・エンパイア 的アペンドディスク）

- **源/解包**：PC 发行常为 **RAR5 自解压或加密包**。本作 `[PC-JP]クリムゾン・ロワイヤル.rar`
  **数据段加密**（`7z l` 头明文可列名；不加 `-p` 会**挂起等密码**）→ `7z x -potoame <rar> <files>`。
  ★ **Git-Bash 把含日文的路径传给 7z 会乱码**（`ϵͳ�Ҳ���ָ����·����`）→ 先用 Python `os.link()` 建 ASCII 名硬链接再解。
  归档：`appscenario.xp3`(剧本) / `appdata.xp3`(数据) / `respatch.xp3`(共享资源) / `data.xp3`(KAG系统+前作csv) /
  `appimage|appmovie|appsound.xp3` / `patchfont.xp3`(字体 tft)。
- **XP3 容器（**本作是带 ASCII 标签的索引变体，非标准 index**）**：
  - 头：`58 50 33 0d 0a 20 <X> 1a 8b`(8B, 第 7 字节各档不同，**不可作校验**) + 3B 填充 + **u64 索引绝对偏移 @0x0B**。
  - 索引：`u8 flag(0x01)` + `u64` + `u64 解压长` + **zlib 流**（zlib 起点本作固定在偏移 +0x11，
    稳妥做法：在索引块前 48B 内扫 `0x78` 且次字节 ∈ {01,5e,9c,da}）。
  - 解压后索引 = 连续 **`File` 记录**：`tag[4]="File"` + `u64 size` + 载荷；载荷内是子块序列，
    每子块 = `tag[4]` + `u64 size` + 载荷：
    - `info`：`20B 头` + `u16 名字长` + **名字 UTF-16LE**（名在 **+0x16**）
    - `segm`：N × **28B** 段记录 `{u32 flags; u64 offset; u64 size; u64 size}`（offset 为文件绝对偏移，段顺序连续）
    - `adlr`：4B Adler-32
- **文件编码**：`.ks`（KAG 剧本）与 `.tjs` = **zlib 压缩 + UTF-16LE(BOM)**（DropWave 定制加载）；
  **`.csv` = GBK(cp936)，内容却是日文**（汉化工具链遗留；cp932 会在 0xEC 等处 `illegal multibyte sequence`）；
  `scenarioindex.txt`/`ro_memoindex_*.txt` = zlib + CP932（ASCII 内容）。
- **DropWave OriginalTag**（`system/originalTag/mc*Tag.ks`，署名 Kenichi Tanga/DropWave 2008）：
  - **`[message window=… name=… face=… voice=…]` … `[/message]` = 一屏 = 一次点击**
    （`[/message]` 内做 `[backlay] [pb]` 改ページ＝等待点击）。
  - `[br]` = `[l cond="mp['click']"] [r]`：**全库 13,395 处均无属性** ⇒ 框内软换行 → **合并**。
    `[clearmessage]`=清窗（无文本）；`[next file=…]`=跳下一本；`[select word=… file=…]`=选项按钮（word 即按钮文本）。
  - 窗口容量宏注释写「25文字×4行＝100文字」，**实测成品最长行 101 字**，反证"一屏一块"成立；
    脚本内除宏定义外**不存在** `[p]/[l]/[waitclick]`，无需中途拆页。
  - **★ 坑：正文里行首 `;` 是 KAG 注释**（本作 461 行，含 228 行被注释掉的 `;　·····` 转场点线）→
    必须整行丢弃，否则输出成 `;····;` 伪文本。
  - 主人公名：`PlayDataManager.tjs` 默认 `f[F_FIRST_NAME]='シエラ'` / `f[F_FAMILY_NAME]='ロザン'`；
    `[firstname]`/`[familyname]` 宏 = `[emb exp="f[…]"]`（可改名）。另前作模板残留裸占位符 `【主人公の名前】`
    （**引擎不替换**，本作仅 1 处，按规范置为 シエラ）。说话人名走 `name="name_XX.png"` **图片名札** → 按规范不加前缀。
- **剧本播放顺序**：`system/appendClass/ScenarioNavigator.tjs` 的 `ALL_SCENARIOPLAY` 分支
  用 `new CSVArray(SCENARIOINDEX)` 顺序取下一本 ⇒ **`appscenario.xp3>scenarioindex.txt` 即游戏自身定义的线性播放序**
  （本作 615 条）。★ 索引内有全角 `bryoｎ` 笔误（5 处）→ 比对时做 **NFKC 归一化**。
- **归档归属陷阱（务必分辨）**：本 RAR 为「アペンドディスク本体 + 共享资源」的不完整副本（**无 exe、无前作 `scenario.xp3`**）。
  - `appscenario.xp3`(627 .ks) = **本作剧本**；`appdata.xp3`(csv) = **本作数据**（questdata 含 115–124＝`qeventdata` 引用的本作事件；
    shortscenariodata 有 `自室[RO強制OP2]`/`闘技場[ハルキア]`）。
  - **`data.xp3` 的 `.csv` = 前作《クリムゾン・エンパイア》**（`模擬戦闘[レクチャー]`/`御前試合`/quest 1–92）→ **排除**
    （同《クランク・イン》SA7 遗留之例）。
  - `respatch.xp3` = **两作共享资源**（`urawaza_check_1st.ks` 自注「エンパイアとロワイヤル共に使う」；
    `basictalkdata` 引用其 `basic_bryon2_repeat15.ks`）→ 收入为"追加区"。
  - `data.xp3>system/about.ks` 含**中文汉化组信息**（☆翼の梦☆推倒美男汉化组）→ 非原作文本，排除。
- **辞典/教程**：`system/**` 检索 `用語/辞典/図鑑/事典/豆知識` = **0**（无用語辞典）；回想/CG 图鉴条目是**图片**，
  `ro_memoindex_*.txt` 只是 `剧本名↔缩略图名` 映射。前作战斗教程在本作**已删除**，本作教程 =
  `messagedata.csv` 的道具屋/教会/フィールド/自室说明消息（106 条）。结局 `ro_endroll_{a,b,c}.ks` 只播 **`.mpg`**（演职员表在视频内）。
  `system/grammarGuide/*.ks` 是**开发者向 KAG 语法教程**，非玩家内容。
- 工具：`scripts/crimson_royale_extract.py`（内嵌 XP3 读取器 + 剧本/CSV 提取，纯 Python 可复跑）。
- 外部核对：vndb **c16530 シエラ=ロザン**（前作与ロワイヤル共用主角）；角色名与 getchu 官方介绍全吻合。
  本作 vndb **无词条**（PSV 移植因 QuinRose 倒闭中止）。

## KiriKiri XP3「区间 1 字节 XOR」（Aromarie）— 蝶の毒 華の鎖 初回版 / ～幻想夜話～

- **容器**：标准 KiriKiri XP3，索引**明文**（20B 头后 **0x20 处 u64 = index_offset**）。
  解析即 `scripts/xp3.py`：索引 zlib 展开 → `File` 记录序列（`info` 名字 UTF-16LE / `segm` 28B 段 `{u32 flags; u64 offset; u64 size; u64 size}`）。
- **内容保护**：cp932 平文做 **每文件 1 字节 XOR**。键**基本恒定**，但 **极少数孤立字节另键**（→ 1~3 字化け）。
  完整键规则未解（`plugin/poisonchain*.tpm` = RSA 公钥 + 加密 `.decc` 节，解析コスト过大）。
  完整性靠 **cp932 文字尤度モデルで区間鍵・境界を推定 + 逐位置定值复元表** 保证。
- **两作差异（重要）**：
  | | 初回生産版（2011） | ～幻想夜話～（FD, 2012） |
  |---|---|---|
  | 压缩 | **有 zlib**（`78da` level9；`stored < original`） | **无 zlib**（`stored` = 磁盘长；索引 `original` 字段不可信） |
  | 键分段 | 多数单键，`sysscn/first.ks` 真 2 段 `[0,574)=0x93/[574,700)=0x18` | **每文件 [头部区][正文区] 两段键**（境界 318〜643B，例 hideo_bad `0x7E→0xDC`） |
  | 官方补丁 | 同捆 `Patch.rar`→NSIS→`patch.xp3`（KiriKiri 覆盖包，同方式可解，修 6 处显示文） | 无 |
  | 化け | 45 处（20 `〓` + 25 半角假名化） | 24 处（见下） |
- **★ 孤立化けの规律（幻想夜話で確定）＝「2 バイト字の首バイト 1 個」が別値に置換**。
  置換後は (a) ASCII（`B','7','p','b','y','C','\r'→'p' 等。文字種走査で検出可）
  か (b) 別の合法前導バイト（→ 誤った漢字。文字種では検出不可）。
  ⇒ **尾バイト＋前後文＋同作内の平行語**から一意に確定し、**逐位置定值复元表**（`FIXES`: バイト位置→正値）に固定。
  **総当り・全探索はしない**（用户鉄律）。検出補助は bigram 意外度（`gensou_scan.py`）＋ASCII/`【`/`[` 混入走査。
  実例：`激秒屋→呉服屋`(8CE0 959E) / `ﾏﾘ財→借財`(借=8ED8) / `b髏O→る唇`(82E9 904F) / `竡→月` / `ﾋendif→@endif`
  （※`@endif` を直さないと `@if/@else` 分支整合が崩れ、hideo_happy が 408→560 行に化ける）
- **KAG3 記法**（両作共通）：`[名前置換]/[名字置換]/[愛称置換]`＝野宮/百合子/ユリ（＝主人公 野宮百合子）、
  `[漢字'よみ]` ルビ、`【X/Y】→【Y】`、`【名】` 独立行＝話者札（破棄）、選択肢 `[seladd text=…]`。
  `@if exp="f.sys_name==0"`＝既定名ルート。
- **工具**：`scripts/xp3.py`｜初回版 `chou_decrypt.py`(区间XOR复号)+`chou_fix.py`(OVERRIDES/REKEY/`TEXT_PATCH`)+`chou_extract.py`｜
  幻想夜話 `gensou_decode.py`(区間XOR+`FIXES`)+`gensou_extract.py`+`gensou_scan.py`。
- **環境の坑**：**日本語パスを 7-Zip に bash から渡すと化ける** → PowerShell 経由で `7z x`（または ASCII 名 hard link）。
