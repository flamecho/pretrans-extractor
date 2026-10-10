# HuneX「HESL / UNAS」系（HGTC / HPAC / HLZS / HFNT / HESL / HESE）

> 路由 / 一句话索引见 `../engines.md`。
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
  `<psvdec>/...` 外的 `YuriSizuku/GalgameReverse: project/hunex/src/hunex_hlzs.py`（本作自写解码器已归档 `scripts/_archive/believer/hlzs.py`）。
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
> ⚠ 当时走弯路的做法已被禁（skill §0「禁穷举/禁 OCR」）：扫 `k∈[−1200,1200]`、试 CP932 各偏移、
> 渲染字形图集做 OCR —— 全部无效。**正确做法＝一条已知明文锚定基址常量**（如上 `見`→1064）。
> 判据要用**含汉字**的串（平假名段会被 `+0x200` 假象带偏）。

## 五、成行 / 排除
- 一次点击 = 一行（每个 `op 0x1b` TEXT）＝一行；`0x2C`、`0x8000` 都**合并**。
- `op 0x1a` NAME 串丢弃（不加说话人前缀）。章选择表（序章…ＢＡＤ/ＨＡＰＰＹ）为**共通导入块**，61 脚本逐一重复 → 只留一次。
- `adv.hpb`/`data.hpb`/`dialog.hgtc` 均为图片或字体，**无剧本文本**；系统 UI 串不在资源里。

## 六、工具
- `scripts/believer_extract.py` —— BELIEVER! 定稿提取器（HESL→HESE→成行，含 csb 解码与共通块去重）
- 探查辅助：`scripts/_archive/believer/hlzs.py`（HLZS 解码，清理时归档）＋ `hunex_hlzs_reference.py`（参考实现）
- ~~OCR / 字体图集探查脚本~~ —— 随中间数据一并删除，**且已被禁令**（skill §0「禁 OCR」），勿再走此路。
- ⚠ **参考实现 `w_hese_dasm.py`（wlt233/hunex_script）不是同一变体**：它用 `0xA0<op>` 框架 + 外部
  `script_dialog_ja.hdlg.txt`（文本按 param 索引）；本作 `A0 1b` **0** 次、`1b 00 00 80` **14,840** 次、
  文本**内联** ⇒ 别指望它给码表。可借鉴的只有**指令语义/名札/选项分派**。
