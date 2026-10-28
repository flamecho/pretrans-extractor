# HuneX「HESL / UNAS」系（HGTC / HPAC / HLZS / HFNT / HESL / HESE）

> 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。
> **与既有 HuneX「Ogre」系（mrg/hed/MZX0，见 `hunex-ogre.md`）不是一族**：本族是 2015 前后 PSV 新引擎，
> 魔数一律 `H` 开头、可无文本资源、文本用**自建码表**。

## 一、代表 / 源
- **BELIEVER!**（PSV `PCSG00539`，HuneX／D3 Publisher，2015-12-17）
- 源 NoNpDrm RAR → `psvpfsparser -i <app>/PCSG00539 -o dec -z <games.json 的 zRIF> -f cma.henkaku.xyz`
  （本作 zRIF **在 `games.json` 里有**；成功标志 `keystone: matched retail hmac`；需放行网络）
- eboot：`util/zzzrif.py` → work.bin → `util/self2elf.py` → ELF（内含 `hesl_*` 调试串，可确认引擎）

## 二、文件表（解密后 `data/`）

| 文件 | 格式 | 说明 |
|---|---|---|
| `script.heslnk` | HESL | **脚本包**：charset.csb + A01..E12/OP 等 64 项 |
| `common.hpac` | HPAC | **总索引**：内含各 `.hph`（对应 `.hpb` 的条目表）、`dialog.hgtc`、`dialog_common.hesexe`、system.phd/pbd |
| `adv.hpb` | 裸数据 | 由 `adv.hph` 索引；只有 bg/cg/stand/item/effect/transition 图片（**无文本**） |
| `data.hpb` | 裸数据 | 8×`HFNT` 字体图集 + 7×HPAC（字体/图片） |
| `voice.hpb` / `bgm.hpb` | 裸数据 | 语音 / BGM |

## 三、格式要点
- **`HLZS`**（压缩）：`'HLZS' + u32 ver(0x1000) + u32 encodeSize + u32 decodeSize + 0x10 pad`，载荷 @0x20。
  LZSS：dict 0x1000、maxlen 0x12、ring buffer；标志字节按位取（bit=1 字面量）。参考实现
  `<psvdec>/...` 外的 `YuriSizuku/GalgameReverse: project/hunex/src/hunex_hlzs.py`（本包内含 `scripts/hunex_hlzs.py`）。
- **`HPAC`**：头 0x20 `'HPAC'+ver+count+size+nameOffset+pad`；条目 0x20B
  `hash1,offset,size,unk,hash2,unk2,8B0`；名称表 @nameOffset（NUL 分隔）。
  ⚠ `common.hpac` 的 `size` 字段不可靠，**长度用「下一项 offset − 本项 offset」**。
- **`HGTC`**（图片容器）：`'HGTC'+ver+count`，条目 @0x20、0x20B `hash,u16w,u16h,dummy,off1,off2,8B0`；
  off1 起 0x400 头 + ≈w×h 的 8bit 灰度数据（对话框素材 1024×208 等）。
- **`HFNT`**（字体）：`'HFNT'+ver+count(3748)+(u16 w,h)×2+0x40` → HGTC(2) → 2 个 **1024×2048**
  图集，**横向 1/2 压缩**（放出后字格 37×46）；字形按 **code 序**（图集 index0 = `#`）。
- **`HESL`**：头 0x30 `'HESL'+ver+count+unk1+unk2+nameOff+dataOff`；条目 @0x30、0x10B
  `checksum,item_offset,item_size(=0 → 用下一项 offset 求长)`；名称 @nameOff。
- **`charset.csb`**（item 0）：`'CSB\0'+ver+count`，表 @**0x44**，**每项 6B**（UTF-8 字符 + 零填充），
  按码位序排列 → **index → 字符**。
- **`HESE`**（脚本）：头 0x30 `'HESE'+ver+code_offset+string_count+text_op_count`；
  `string_count>0` 时 @0x40 有 string_count×u32 串偏移（相对 code_offset）；
  指令小端 `[u16 opcode][u16 flags][u32 param]`，`flags==0` → 4B 裸指令。
  - `op 0x1a` **NAME**：+4B 后接内联串（说话人名／主角名 → 按规定**丢弃**）
  - `op 0x1b` **TEXT**：变体 A（param==0）→ +8B 后串；变体 B → +4B 后串；
    **空 TEXT = 同一文本框的续接**（跨 op 续句，需与前一行拼接）
  - 少数串**无 0x0000 终止符**，直接以「下一条指令」为界

## 四、★文本编码（本族核心）
串 = **u16 码流**（小端）：

| 码 | 处理 |
|---|---|
| `0x0001-0x001F` / `0x0023` | 标记/控制，丢弃，**并使本串结束** |
| `0x0021-0x0024` | 标记，丢弃 |
| `0x002C` | **框内软换行 → 合并** |
| `0x8000` | **框内显式换行 → 合并**（**不是**点击分框！） |
| `0xFFFC`/`0xFFFF` | 丢弃 |
| `< 0x80` | ASCII |
| `≥ 0x8000` | `charset.csb[(code - 0x8000) **- 6**]` |

**推导路径（勿再走弯路）**：hi 字节 0x80-0x87 → 先疑「SJIS−0x200」，平假名条成立（读出 `しています`）、
汉字条失败 ⇒ 是自建码表；用 `dialog_common.hesexe` 系统消息上下文反推（`…が見つかりませんでした`
的 `見`），命中 `charset.csb[1064]=='見'` ⇒ 常量 **−6**（＝字体图集比 csb 多的 6 个字形）。
**k=0 / +0x200 都会给出「看似通顺」的错文，必须走 csb 且带 −6。**
> ⚠ 当时走弯路的做法已被禁（skill SKILL.md §0「禁穷举/禁 OCR」）：扫 `k∈[−1200,1200]`、试 CP932 各偏移、
> 渲染字形图集做 OCR —— 全部无效。**正确做法＝一条已知明文锚定基址常量**（如上 `見`→1064）。
> 判据要用**含汉字**的串（平假名段会被 `+0x200` 假象带偏）。

## 五、成行 / 排除
- 一次点击 = 一行（每个 `op 0x1b` TEXT）＝一行；`0x2C`、`0x8000` 都**合并**。
- `op 0x1a` NAME = **说话人名牌**（语义已确认：`園崎みあ` 后紧跟 `「……うっ……！」`）。按「不加说话人前缀」整条丢弃。
  章选择表（序章…ＢＡＤ/ＨＡＰＰＹ）为**共通导入块**，61 脚本逐一重复 → 只留一次。
- `adv.hpb`/`data.hpb`/`dialog.hgtc` 均为图片或字体，**无剧本文本**；系统 UI 串不在资源里。

## 五之二、★主角名去向（2026-10-12 复核，更正旧结论）
- **女主＝園崎 みあ（vndb c40222，女性·主角；其余角色全男）** —— 标准乙女游戏女主。
- **她的名字只出现在 NAME 名牌里：4,476 次**（全角色最多；对比 神代/海 1545、勅使河原/錬 1244、伊波/遊 1241、
  舞川/臣 1232、高梨/響 1126）。名牌串形如 `園崎〈0x8000〉みあ`（姓/名之间是换行码）。
- **对白正文（TEXT，13,632 段）里：特殊码（≥0x9000 宏）＝ 0 个；`園崎`/`みあ`/`崎みあ` ＝ 0 次**
  （正文里 3 个「園」全是 **公園/学園**）。⇒ **本作不存在「名字插入宏」，名字根本不在正文里。**
- ⇒ 成品没有女主名，**不是「宏被当空码丢弃」的缺陷**，而是「名牌一律丢弃」口径的必然结果。
- ⚠ **更正**：旧报告写「主角名只经 `op 0x1a` 设置（**可改名**）」——**不成立**。eboot（1.03 MB）里
  按 UTF-16/SJIS/gamecode 都找不到 `園崎みあ` 默认名表；NAME 串是**定字面名**（非变量）⇒ 疑为**固定名**（改名机制未证实）。

## 六、工具
- `scripts/believer_extract.py` —— BELIEVER! 定稿提取器（HESL→HESE→成行，含 csb 解码与共通块去重）
- `scripts/hunex_hlzs.py` —— HLZS（LZSS）解码：`HLZS` 头 + dict 0x1000 / maxlen 0x12。
- 第三方参考实现 `hunex_hlzs_reference.py`（`devseed` 开发，另有 `wlt233/hunex_script`）**不随包**，
  需要时按上面的头结构自写即可（`hunex_hlzs.py` 已是完整可用的版本）。
- ~~OCR / 字体图集探查脚本~~ —— 随中间数据一并删除，**且已被禁令**（skill SKILL.md §0「禁 OCR」），勿再走此路。
- ⚠ **参考实现 `w_hese_dasm.py`（wlt233/hunex_script）不是同一变体**：它用 `0xA0<op>` 框架 + 外部
  `script_dialog_ja.hdlg.txt`（文本按 param 索引）；本作 `A0 1b` **0** 次、`1b 00 00 80` **14,840** 次、
  文本**内联** ⇒ 别指望它给码表。可借鉴的只有**指令语义/名札/选项分派**。

## 七、第 2 作：VitaminX Destination（PSV PCSG01115，2018-02-22，vndb v22022）

> 与 BELIEVER! 同族，**容器/码表完全一致**（HESL→CSB 6B/项、`code−0x8000−**6**`、HESE 头 0x40 起）。
> 差异只在**指令语义**与**名札形态**，本册只记差异；共性见 §三〜§五。

| 项 | BELIEVER! | **本作** |
|---|---|---|
| 正文 | `1b` param 0 | 同（`1b 00 00 80`+u32 0+**u32 index**+串，共 12B 后接串） |
| 选项 | 未记录 | **`19 00 00 80`+u32 target+串**（target＝跳转目标）——`test_script` 内作者自测串 `選択肢１/２/３` 直接指认 |
| 名札 | `1a`＋日文名（丢弃） | `1a`＋**和名**与**全角罗马字 id** 各一条（`南悠里` / `Ｈｅｒｏｉｎｅ`、`風門寺悟郎` / `ＧｏｒｏＦｕｍｏｎｊｉ`） |
| 章題 | 无 | **`1b` param `0x26`**＋串（`専属★敏腕★美人秘書` 等，每脚本 1 条＝扉文） |
| 主角名宏 | 无（名字不在正文） | ★**`0x0b`＝姓（南）／`0x0a`＝名（悠里）**，见下 |

**★主角名宏（本族新见形态）**：同一文本框有两种写法并存——
字面版 `それじゃ、協力してくれた南悠里センセに拍手～！`；
分段版 `TEXT『それじゃ、協力してくれた』+ 0x0b『』+ 0x0a『センセに拍手～！』`。
判据＝分段版去掉插入的姓/名后与字面版逐字相同，且 **0x0b 恒在 0x0a 之前**（姓→名）。
处理＝**字面版优先**，字面版缺失才用分段版拼回（名字 inline）。共 524 段，拼回后引号全配对。

**其它**：串多**无 0x0000 终止符**，以下一条指令的 op 字节（`<0x20` 或 `0x23`）为界；
`text_op_count`（HESE 头 +0x10）＝TEXT 指令数，可作**完整性闭合判据**（129 脚本 27,369＝27,369）；
`action_through`/`action_tsukkomi`/`use_asset` 无文本；`test_script`/`test_script2` 为开发自测，剔。
无 用語辞典 载体。工具：`scripts/vxdst_extract.py`。

> ★ **Switch 变体（文本外置 `.hdlg`，HESE 内无日文）见 `hunex-hesl-switch.md`**。
