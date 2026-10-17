# Takuyo gss —— Switch 变体 · `SCR 2.00`（未打包）

> **同一引擎的 Switch 版有两套脚本版本**：
> `神さまと恋ゴコロ`＝`SCR 3.00`＋LSDARC 内层打包（见 `takuyo-gss-switch.md`）；
> **本册＝`SCR 2.00`＋未打包**。本家（PSV `SCR 2.00`）见 `takuyo-gss.md`；路由见 `../engines.md`。
> ★★ **脚本版本按文件头判，不可按平台推定**。

## カエル畑DEつかまえて☆彡（NS-JP, TAKUYO, TitleID `0100e5200d1a2000`, vndb v3106）
- **源**：`<游戏 dump 目录>/[NS-JP]カエル畑DEつかまえて☆彡.xci`（2.99 GB）。
  ★`hactool -t xci` 报 `XCI partition is corrupt!`（缺 `xci_header_key`，hfs0_header_hash 校验不过）
  ⇒ **`scripts/crazychain_xci.py` 手切 secure 分区**（root HFS0 @0xF000，分区 `update/logo/normal/secure`）。
  NCA：`Distribution type: Gamecard` / `Content Type: Program` / **`Encryption Type: Standard crypto`**
  ⇒ key area 明文给出内容密钥（`Key 2`），`hactool --romfsdir=` **直接解，不需要 titlekey**。
  ※ XCI 的 `update` 分区（385 MB・~180 NCA）＝**卡带同捆 SystemUpdate**（cnmt 高熵），**不是游戏补丁**。
- **RomFS**：`SCRDATA1.BIN/.ARC`（脚本）、`BMPDATA0/1`、`FONTDATA`、`WAVDATA0/1`、`movie/KAERU_OP|ED.mp4`。
  **无 csv / 无 exefs 名表**（`main`(NSO0) 内检索 `菅野`/`風羽` 均 0 命中）。
- **容器同 LSDARC V.100，但本作 495 条全部 `isPacked=0`**（未用到 pack `H/D/R`）。
- ★★ **脚本是 `SCR 2.00`（不是 3.00）**——即使同为 NS 版也不能按平台套 `神さまと恋ゴコロ` 的 3.00 头。
  `SCR 2.00` 指令头 `u16 op|u8 size|u16 id`（3B）；**495/495 零失步**。
- ★★ **opcode 表与 ひめひび（PSV）完全一致、未发生平移**（`0x5a`正文 / `0xfc` `%s` / `0xf0`扉文 / `0x5c`选项 /
  `0xfd`槽赋值 / `0x3c`WAV / `0x1e`call / `0xf5`效果 / `0x10c`sprintf→槽 / `0x132`槽←串 / `0x1c`命令 / `0x3b`图像）。
  文本 op **只有这 4 个**（其余含串 op 全是文件名/slot/命令）。串内 `\n`=框内换行(合并，1267)、`\c`=控制码(删，12)；
  **本作无 `☆` 制作备忘串**。
- **顺序**：`AUTOEXEC`→`Init.SCR/START`＋`PRG_ROUTE.scr/START`；`PRG_ROUTE` 内有**线性派发表**（585 个 `0x1e`）
  ⇒ 顺序＝`0x1e` 调用图 **DFS 前序去重**（471/495 可达）。
  结构：`COM001–077BAD`（共通，内嵌 `06_xx` 日期事件＋`MINI_*`）→ `HAKU/HINO/MATO`（三组**两人组七不思議**章节，
  与 `06_22〜06_25` 交错）→ 六条个別线 `HAM`(葉村)`KUG`(空閑)`YUU`(広瀬)`MAI`(米原)`TOG`(戸神)`NOR`(法月)。
  **路线字母靠名札统计认定**（HAKU=葉村+空閑 / HINO=法月+広瀬 / MATO=米原+戸神）。
- **排除 14 个**：系统/演出 `AUTOEXEC INIT PRG_BG PRG_EFFECT PRG_NAME PRG_PLATE PRG_ROUTE PRG_STAND PRG_THREAD`、
  UI `RELOAD SELECT2`、**迷你游戏 `MINI_HOU MINI_GOMI MINI_KINOKO`**（「相方選んで下さい」「ミニゲームをスキップ…」）。
- **收录 extras（0 引用、原生菜单启动）**：`KAKEAI_*`12 段（掛け合い短編，各以 `0x5a` 打「标题＋`-終-`」收尾）
  ＋ `SP_DORAMA01–10`（スペシャルドラマ）⇒ 追加于末尾。
- **主人公名（可改名）**：slot `1802`=**菅野**（`0x132` 显式写死）/ `0c02`=**風羽**（`PRG_ROUTE@0x36` `0xfd`
  `0c02←6081`，6081 仅读不写＝引擎写入）/ `f405`=**スガ**（`0xfd` 写死）。`0xfc` 的 `%s` 只用这 3 槽。
  ★默认名**外部核对**：官方站 `takuyo.co.jp/products/kaerusummer/character.html` ＝「菅野風羽（すがのふう）/名前変更可能」；
  ★**出现性实证**：`NOR007@0x512` 有**字面** `葉村＆空閑＆広瀬＆法月＆風羽\n「「「「「………………」」」」」`。
  ★★**第二种插入宏 `@GameLast`（仅 2 处，全在 `0xf0` 标题卡里；用户 2026-10-15 指出初版漏还原）**：
  `0xf0` 只有 1 个字符串操作数、**无槽位可替换** ⇒ 作者在标题里改用**文本宏**。
  `COM013@0x10` `おはようございます、@GameLastです` → 菅野です（紧接正文本人报名 `「菅野です」`）；
  `MATO003@0x10` `@GameLast愛護週間で優先です` → 菅野愛護週間（全篇 5 处同义句）。
  ⇒ **`@GameLast` ＝ 姓 slot `1802`**，驱动加 `NAME_MACROS={"@GameLast": 菅野}`。教训见 skill `pitfalls/B1-lines.md` ㉘。
- **用語解説（妖怪図鑑）inline 9 条**：`PRG_NAME.SCR NAME_NON` 清名札后紧随 `0x5a`，体例 `【見出し語】：解説`
  （`COM001`【謎の小さいオッサン】/`COM001`+`COM045`【チョコレートマン】/`COM002`【ナナフシ】/
  `HINO007_HIR`【トリコロール】/`KUG007`【尋ね人：…】）。**`NOR020@0xdc7` 唯一漏 `【】`** ⇒ 整行定值修。
  这些卡**留在原位**（每张都是一次点击的 inline 上屏事件），不搬末尾。
- **工具**：`scripts/kaeru_extract.py`（DFS 排序＋成行＋`NAME_SLOTS`/`NAME_MACROS`/`TEXT_PATCH`/排除表/extras）；复用
  `gss_lsdarc.py` ＋ `himehibi_disasm.py`（SCR 2.00 反汇编）。成品 30,121 行【PASS】；
  报告 `提取结果/解析报告/カエル畑DEつかまえて☆彡_解析报告.md`。

## 第 2 作（SCR 2.00 同型）：ソラ*ユメ（NS-JP, TAKUYO, TitleID `0100e6a027760000`, vndb v1341）
- **源**：`<游戏 dump 目录>/[NS-JP]ソラユメ.xci`（3.99 GB）。`hactool -t xci --securedir` **正常**（无 corrupt）⇒
  4 NCA；Program `acd922…nca`（**Standard crypto**，key area 明文 ⇒ `--romfsdir=` 直解，无需 titlekey）。
  ExeFS `main`(NSO0, 构建串 `g*switch_gss`)／RomFS `*DATA.ARC/.BIN` ＋ `movie/` ＋ **`omake/NNst.dat`×8**。
- **容器**：`LSDARC V.100`，SCRDATA **407 条全 `isPacked=0`**；链式连续 407/407、末条 `off+size==ARC 尺寸` 自校验通过。
- **脚本恒 `SCR 2.00`**（407/407 零失步）。★**文件头第 9 字节 `B` 是 u32 A=0x42，不是版本后缀**。
- ★★**新增 op（カエル畑未记）**：`0x108`＝**槽←串**（本作唯一用处：`PRG_ROUTE@0x51` 写默认名 `皐月`）；
  `0x106`＝**清槽**；`0x10c`＝**sprintf→槽**（组装名札 `FullName`，剔）；`0x3a`＝**OR**（链式折叠 ⇒「多旗任一」）；
  `0x22`＝**条件为假则跳**（`0x30`/`0x36`/`0x3a` 建条件，`0x23 T` 为标号，**`0x22`..`0x23` 之间＝条件为真时执行**）。
- ★★**调试开关＝flag `c808`**：`INIT` 里 `0x25(c808)←0`，**全部脚本无处置 1**（仅 396 次比较）
  ⇒ **落在 `0x36(0400,c808,1)`→`0x22`→`0x23` 块内部的 `0x5c` 一律是开发用 flag 设定菜单，剔**（本作 52 个：
  「好感度が高い／ルートか？／〜した・してない」）。⚠**反例**：`0x36(c808==1)→0x18 goto *_end` 形态（如 AMAKYO007@0x21aa）
  是「调试时跳过正常选项」⇒ 选项在块**外**，**保留**。★**别用「前 N 条含 c808 比较」当判据**（窗口不稳，会误剔）。
- ★**选项两形态**：① 行内 `(count,"文本,FLAG",…)`（文本＝最后 ASCII 逗号前）；② **槽型** `(count,2006,4806,7006,9806,c006)`
  ——文本先由 `0xfd(slot)←"文本:FLAG"` 写入（先全部置 `''` 清空）⇒ 取 `:` 前。
- **串内码**：`\n`合并／`\c`删／`@r`…`@0`（样式成对开关）删／`@uXXXXXX`（色）删／`@y`删；
  ★**`@GameFirst`＝姓的「文本宏」**（`0xf0` 章题里，如 `【妄想家　@GameFirst】`）⇒ 同 カエル畑 `@GameLast` 之理。
- **主角 守永 皐月**（官方站＋vndb c42461 双向核）。槽：`1802`＝姓 **守永**（引擎写 `8c80`，脚本只读）／`0c02`＝名 **皐月**／`7c04`＝ニックネーム **さっ**。
- **顺序**：`AUTOEXEC→INIT→PRG_ROUTE`（380 条线性派发表）⇒ `0x1e` DFS 前序去重，405/407 可达。
  3 组路线 `ASA(朝峰)×RUU(ルーエン)`／`YAM(山瀬)×MIS(水窪)`／`AMA(餘部)×KYO(御剣)`＋各 BAD END。
  **排除 10 系统脚本**（`AUTOEXEC INIT PRG_* RELOAD SELECT2`）。
- **おまけ SS**：`romfs/omake/NNst.dat`×8（CP932＋CRLF 纯文本短编；`AUTOEXEC` 有 `OMAKE_START` 标签但无脚本跳 ⇒
  **引擎菜单进入**）。★**占位符**：`@`＝名（皐月）／`*`＝姓（守永），三式自证 `*さん`/`*悠月`/`*@は今日も元気に`。
  成行＝**连续非空行合并**（源是硬折行显示文本）、空行分段 ⇒ 1,768 行，追加末尾。
- **工具**：`scripts/sorayume_extract.py`（复用 `himehibi_lsdarc.py`＋`himehibi_disasm.py`）。
  成品 **42,155 行**（正文 37,554＋`%s` 2,094＋扉文 399＋选项 340＋おまけ 1,768；剔 52 DEBUG）
  —— 品检余 2 类 [E] 均**已核实为工具误报**（原文半角标点 `･`×6/`､`×1；书信 `注意：`/`追伸：`）；
  报告 `提取结果/解析报告/[NS-JP]ソラユメ_解析报告.md`。
