# 引擎：dramatic create 自研「Orfre」/ DCVM（PSV オルフレール ～幸福の花束～）

一句话：PSV `PCSG00919`；容器＝自研 ROFS（`map/<n>.map` 索引 ＋ `rom/<n>.rom` 数据）；脚本＝`DCVM` 自定义 VM；
文本在 `STR` 池（按类型分组存放，池序 ≠ 显示序），**顺序取 `STBL` 段（＝编译发射序＝显示序）**。

> 探查史（失败路线 / 截图锚点 / PC 补丁标尺 / 调用约定推导）见 **`orfre-dcvm-history.md`**。

## 0. 作品
- 《オルフレール ～幸福の花束～》(PSV 日文, PCSG00919)。**非** HuneX。主角名 **クレア**。

## 1. 容器链（PSV）
`pkg`(1.87 GB)＋`work.bin` → `rif2zrif.py work.bin` → `pkg2zip.exe -x <pkg> <zRIF>` → `app/PCSG00919/`
→ `psvpfsparser.exe -i app/PCSG00919 -o dec -z <zRIF> -f cma.henkaku.xyz`（**keystone: matched retail hmac** → 成功）
→ `dec/eboot.bin`（`SCE` 头）＋ `dec/map/*.map` ＋ `dec/rom/*.rom`
- eboot → ELF：`self2elf.py -i dec/eboot.bin -o eboot.elf -k work.bin`（**ARM32/Thumb**, vaddr=0x81000000, PH0 off 0xe0）

## 2. ROFS（自研容器）

| 文件 | 作用 |
|---|---|
| `map/<n>.map` | 索引（**仍是加密/高熵**，magic `2a272b69`，未破解——非必需） |
| `rom/<n>.rom` | 数据；**1024 B 分页**，pg0 = 加密头（各 rom `[4:]` 相同），pg≥1 起有效 |

`.rom` 页格式（pg≥1）：

```
[u16 0x19A6][u16 type][u32 comp][u32 raw][blob]
 type=1 → blob = 单条 zlib
 type=2 → blob = "ZPZP" 多流容器: [magic ZPZP][u32 n][u32 f][u32 hdrsize][n×u32 off]
           → concat(zlib(member_i)) 得原始块
非 0x19A6 页 → 原始块（`DCVM` 明文开头）
```
- 所有脚本都在 `rom/script.rom`（562 个 DCVM 子块）；其余 17 个 `rom/*.rom`（bg/bgm/bu/ev/other/rodata/se/thumb/voice_*）**无 DCVM**。

## 3. 脚本容器 DCVM
段序（`[tag][u32 size][data]`，size 含 8 B 头，从 off 0x10 起链式）：
`DCVM` → `STOR` → `PTBL` → `PSTR` → [`VTBL`] → `FTBL` → `CODE` → `STR ` → `STBL`

| 段 | 语义 |
|---|---|
| `STR ` | **NUL 分隔字符串池**（全部文本在此）。**按类型分组存放**（旁白 / 心声 / 对白 / 资源名 / 符号名 / 语音 / 裸章题 / 选项）⇒ **池序 ≠ 显示序** |
| `FTBL` | **符号表** `{u32 addr\|0xffffff(外部), u32 名字池id, u32 flags}`，**按名排序**；索引 = 调用时的 funcid（每块自带 ⇒ 同名数值跨块含义不同）。局部符号 `addr` = CODE 内偏移，入口 = `code[addr+0x14]` |
| `CODE` | 头 20 B + 导出桩表（`ENTRY;PUSHIB n;[PUSHIB n;CALL];RET;END`）+ 函数体 |
| **`STBL`** | `u32[size] + u32[count] + count×u32[offset]`；**offset 以 STR 段 tag 起点为基准**，字符串 = `data[STR_off+16+offset]`（＝ `strd[offset+8]`，`strd = data[STR_off+8:STR_off+size]`）。⚠️ 差 8 会 5/236 命中。**顺序 = 编译发射序 = 显示序** |

- `LINE`/`FILE` op 在游戏中**不出现**（不能靠它排序）。

## 4. VM 指令集（自研 Orfre）
- opcode 表在 `eboot.elf` file `0x1cd4e0`，80 × 12 B `{name*, u32 指令长度, handler*}`，index=opcode。
- 名称序：`ABORT NOP TYPE TYPE_POP INIT TERM LOOP ENTRY END IS_NULL_TYPE SYSCALL CALL RET ADD… GEQ JMP JMPT JMPF PUSHIW PUSHIH PUSHIB PUSHNIH PUSHNIB PUSH_NULL PUSHR STR PUSHRET VAR_AUTO VAR_LOCAL VAR_ARG VAR_GLOBAL LD ST SP POP SWAP DUP RTOI ITOR ENTRY_INFO PSETUP PCALL CHECK_STACK_BEGIN CHECK_STACK_END CHECK_INDEX LINE FILE LDRET VAR_PERSISTENT VAR_INITIALIZE`（80 个）
- 长度表（index 0..79）：`1,1,2,2,1,1,9,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,5,3,2,3,2,1,5,1,1,1,1,1,1,1,1,5,1,1,1,1,1,5,1,1,1,1,5,5,5,1,1,1`
  （PUSHIW=5(u32) / PUSHIH=3(u16) / PUSHIB=2(u8) / PUSHNIH・PUSHNIB 同宽 / PUSHR=5 / LOOP=9）
- 调用约定：**`<args…>; PUSH <nargs>; PUSH <funcid>; CALL\|PCALL`**（`SYSCALL` 同构：`<args>; PUSH <syscall#>; SYSCALL`）。
- **跳转 = `PUSHIW <target>; JMP\|JMPT\|JMPF`**，target 走栈，目标 = `code[imm+0x14]`。
- 文本引用 = `<strid>; STR`（STR 弹栈取 `池[id]`）。内置模块 19 个（`OrfreText/OrfreSystem/OrfreConfig/OrfreBacklog/OrfreVoice/Puppet*/Font…`）。
- 脚本级 API（FTBL 名）：`orfre_text_open/_append/_start/_end/_set_name/_clear/_close/_page_break/_page_pre_break/_set_enable_auto_lf/_set_voice_collection`；`orfre_select/_append/_init`；`puppet_universal_transition/_voice_play_all/_voice_load/_bgm_play/_image_delete/_chapter_end/_scenario_begin`；`replay_<n>/setCurrentScene/setSummary/setJumpLabel/setBranchAttribute/reset`。

## 5. 脚本 / 场景结构（已解）
- **`script.rom` 第 8 号块** = 全部剧本名有序清单，共 **260** 条：
  `{ad01-01v..ad07-10v(87, 含 ad03-15_5v), no01-01v..no05-10v(45), op01v..op08v(8), ru01-01v..ru08-11v(56), za01-01v..za05-13v(63)}.s`
  （路由字符：ad=アデル / no=ノア / ru=ルイス / za=ザック / op=开场；另 `*_breath`、`fi/ka/al/om/ow` 语音前缀）
- **子块 21–287（各 888 B）= 逐剧本「流程桩」**：每块池内恰含 1 条 `game/script/scenario/<名>.s`，**顺序即脚本流程序**（含 `*_breath`、`test`）。
- **子块 295–561 = 逐剧本「正文块」，与桩索引一一对应**（`body[295+k] ↔ stub[21+k]`）。正文块池内含**下一条**剧本名（流程指针）。剧本名去尾部 `v` 即 PC `.snr` 名。
- **子块 16/17/18 = 全文本「重复库」**（池已排序、量巨大：dial≈1113/21435/15256）⇒ **交付时整体排除**，否则三重重复。
- 空正文条目（正常）：6 个 `*_breath`（语音/息遣い专用）＋ `no05-01v`（**路由节点**，仅含 `no04-01v.s`/`no05-02v.s` 跳转）。

## 6. ★成行（最终，一次点击 = 一行）
**顺序 = `STBL` 顺序**（实测 562 块 / 122,212 条偏移 **100% 命中**字符串起点，0 失配）。

| 保留 | 规则 |
|---|---|
| 旁白/对白/心声 | 行首 ∈ {` `,`　`,`「`,`（`} |
| 扉文（章题卡） | `― 章題 ―` |
| 信件/引用 | 行首 `『` |
| 选项 | 含 `\n` 的连接串 → 逐条成行（紧随 `選択肢` 的同名副本丢弃） |

| 丢弃 | 例 |
|---|---|
| 名字札 | `アデル`/`サマル`/`街の人Ａ`（不加说话人前缀） |
| 资源路径・语音・BGM/SE | `game/image/...`、`ad/ad1092`、`bgm01`、`se/mj_se36` |
| API・符号名 | `orfre_text_open`、`puppet_universal_transition` |
| 系统串 | `タイトルに戻りますか？`、`次のチャプターへ…` |
| 回想专用 | `回想:XXX`（不收日志/回想载体） |
| 裸章题（元数据） | `メイドとしてのめまぐるしい日々`（PC 侧为 `インフォメーション(...)`，非上屏） |

**归一化**：`<a>(X)`→`X`（X＝要绘制的开括号，如 `<a>(「)…」`→`「…」`，**不能只删标签**）；`<w>…</w>`→删标签留内容；
`<name>(n)`→`クレア`（主角名宏）；半角假名（＝平假名表示）→平假名（含浊点/半浊点合成）；片假名本为全角；行内换行合并。
输出 UTF-8(BOM) + 纯 LF、无空行。

- 工具：**`scripts/orfleur_stbl_extract.py`**（`<dec_dir> <out.txt> [--chunk-txt dir]`）；基础库 `scripts/orfleur_extract.py`（`strip_tags`/`hankaku_to_hiragana`/`parse_rom`/`secs`/`vm_ops`）。
- 交叉验证：与 PC 汉化补丁逐句对应；PSV 22,250 行 / PC 正文 22,142 行 = **1.00**（中位 1.04，p10–p90 0.96–1.14）；品检 PASS。

## 7. 截图锚点（VNDB v15563，存 `_work_orfleur/shots/`）
- 取名画面：`主人公の名前を入力してください`，默认 **クレア**＋姓 アイシア。⇒ 主角名取自此处。
- 对话窗：上行名字窗 + 下行正文 `「…」`（**`「」` 属正文**）；旁白无名字窗；选项为平铺多行纯文本。
- 存档画面说明字＝`setSummary` 实参 ⇒ `setSummary` 不是显示调用。
- 截图直链 `https://t.vndb.org/sf/<xx>/<id>.jpg`（API：`POST api.vndb.org/kana/vn {"filters":["id","=","v15563"],"fields":"screenshots{url}"}`）。
