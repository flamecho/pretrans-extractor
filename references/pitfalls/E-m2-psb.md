# E · M2 ADVENGINE／PSB·PGD 专册

> 分三组：**容器解密与键获取** → **场景表、选项与收文范围** → **成行、标签与品检**。
> 两作：**Beyond The Future**（UMD/PSP，`INSTALL.BIN` 全量）、**いざ、出陣！恋戦 第二幕 ～甲斐編～**（同族第 2 作）。

## 1. 容器解密与键获取

### 1.1 ★PSB 三层壳要一层层剥：MDF(MT19937) → zlib → PSB；seed ＝ 键 ＋ 文件名（含扩展名/后缀）
（2026-10-18，**Beyond The Future**，M2「ADVENGINE」＋PSB）：`envelope` 每个成员独立加壳；seed 用 **`键`＋`名字`**，名字要按索引 PSB 的 `expire_suffix_list` 补后缀
（本作剧本 `0-main-1.txt` 实际 seed 名是 `0-main-1.txt.scn.m`）。keylen 默认 **131**（`78 9C/DA` 校验）。
⚠ **`voice_body.bin`/`sound_body.bin` 是裸 PSB**（无 MDF 壳），`savedata/*.png` 是裸 PNG —— 别对它们试 MDF。

### 1.2 ★「索引 PSB 指向的 body」可能是 PGD 加密容器——切出来全是噪声时，先看头 4 字节再怀疑键
（同上作）：`fileinfo.psb.m` 是明文 MDF 壳 PSB，
但它的 `umd_root` 表指向的 `INSDIR/INSTALL.BIN` 头是 `00 50 47 44`（`\0PGD`）＋`u32@4=1`(key_index)＋`u32@8=1`(drm_type)。
按偏移直接切，得到 `79 47 9a b3…`，试遍 4 个 MDF seed 名变体全败 —— 极易误判「PSB 键不对」。
**判据**：`00 'PGD'` 四字节；`drm_type=1 + key_index≤1` ⇒ mac_type/cipher_type 皆 1、固定键 `dnas_key1A90`。
**先查 `scripts/pgdecrypt.exe`**（tpu's，同族 PSP 作通用）；要随机访问（只解 10 MB 剧本）再用 `scripts/btf_pgd.py`。
（本作 `INSTALL.BIN` 744,694,224 B → 解出 733,237,248 B，**全部数据只在这里**，UMD 上没有第二份。）

### 1.3 ★`pgd_decrypt` 的 CMAC 尾块：数据长度是 16 的整数倍时，最后 16 字节仍留在 pad（`pad_size=16`）
（同上作，自写实现连错两轮）：`amctrl.c` 里 `pad_size &= 0x0f; if(pad_size==0) pad_size = 16;` —— 若照
「`pad_size = len % 16`」写，整块对齐时会把全部数据喂进 CBC-MAC、尾部用空 pad，结果 MAC 全错。
**自检办法**：本实现的「无 vkey MAC」应恒等于 `标准 AES-CMAC(kirk38, data) ^ loc_1CD4`（用 pycryptodome 的 CMAC 一比即知）。
**再自检**：`MAC_80`（`pgd[0:0x80]` 算出的 MAC 与 `pgd[0x80:0x90]` 16 字节全等）通过 ⇒ 键与算法都对，
此时 DESCRIPTOR 才可能解出合理值（`file_size/block_size=1024/data_offset=0x90`）。

### 1.4 ★MDF seed 名＝「成员名 ＋ 后缀」，无扩展名的成员别再补 `.txt`
（2026-10-18，**いざ、出陣！恋戦 第二幕 ～甲斐編～** ULJM06346，同族第 2 作）：`scenario_info.psb.m` 的
`file_info` 键是 `00_com01.txt`／`scenelist`／`test.ks`，`expire_suffix_list=[".scn.m"]`；
seed 正确写法＝**键名直接接后缀** ⇒ `00_com01.txt.scn.m` ✓、**`scenelist.scn.m` ✓（不是 `scenelist.txt.scn.m`）**。
写错只报 `incorrect header check`，极易误判「键不对」。**判据：先拿 1 个成员试 2 种名字，再批量。**

### 1.5 ★`SYSDIR/BOOT.BIN` 全 0 也常见（1.63 MB 全零）——「明文 ELF 金矿」不是每个 PSP 作都有
（**Beyond The Future**）：`EBOOT.BIN`（`~PSP`，tag D91613F0 type 2）解出来才是 ELF；引擎串/键都在 `.rodata`：
本作 PSB 键是**紧跟 `PARAM.SFO` 的 `DISC_ID` 串后面那 13 个字符**（`ULJM05988` → `V4fSjadn4mnAn`），
比「在 ELF 里找像键的串」稳得多。ELF 里还有 `ADVENGINE`/`script/main.nut`/Sqrat 类名表，可一步认引擎。

## 2. 场景表、选项与收文范围

### 2.1 ★顺序表就在包里：`scenelist.json`（`list[]`）＝唯一 master 顺序，别用文件名序／文件内 label 序
（**Beyond The Future**）：1,540 条 `{storage,target,title,textCount,selects}`，**覆盖全部场景（零遗漏，实测 0 条不在表内）**；
文件内 label 是 `*start` / `*select` / `*0-main-5_1` / `*conf` 这种分支名，按它排必乱。
**行数闭合**：`Σ textCount`（28,022）− **有 selects 的场景数**（247，这些 `*select` 场景 `textCount=1` 而 `texts=0`）
＝ 正文行数（27,775），能对上才说明没漏场。

### 2.2 ★map/chara/town 型选项按 `eval` 双写：同一文本两条（`f.x>0` / `f.x==0`，target 不同）⇒ 同场同文折叠
（同上作）：1,087 条选项里 281 条是这种互斥备选；折叠后 806 条。**普通选项（`selectInfo` 为空）实测 0 例重复**
⇒ 只对本场相邻同文折叠，别全局去重（同名目的地会在不同地图各出现一次，那是真的）。

### 2.3 ★同族第 2 作的「收/不收」清单会多出 sys 素材档与自动分支选项
（**いざ、出陣！恋戦 第二幕 ～甲斐編～**）：`00_com_sys.txt`＝**立ち絵ビューア**（正文全是 `真田幸村 白襦袢 頬赤 奥` 这类表情/衣装素材名）、
`00_com_sys_kai.txt`＝**音声テスト**（151 条 `１`）、`test.ks`＝開発テスト ⇒ 都整块剔除。
选项侧：`selects` 整组**同文**（`章間`＋`eval="f.game_route==20/21"`，或只有 1 条）＝**自动分支，不上屏** ⇒ 剔除
（本作 select 条目 625 条 → 可见 516 条 / 152 组）。`selectInfo.message` 与**前一框正文重复**（提问显示在上一框）⇒ 不发射。
行数闭合：`Σ scenelist.textCount − 有 selects 的条目数 = texts 条数`（本作 25,257−261=24,996，0 差）。

## 3. 成行、标签与品检

### 3.1 ★内联排版标签必须剥干净再品检：`%C` / `%<n>#<hex>;` / `%<n>` / `\w`
（**Beyond The Future**）：`%C`＝神之声/变色标记、`%50#00ff0000;`＝速度＋颜色、`\w`＝停顿。剥完必须**复扫 `%`、`\\` 残留＝0**
（漏 `%\d+` 会留 1 行 `「――堕ちろ。%45――堕ちろ…」`）。⚠`\w` 是停顿不是点击 ⇒ 同框合并，不拆行。

### 3.2 交付前「原文手误」要有字节级证据再放行
（同上作）：本作 `check_text` 唯一 2 处 `[E] 引号不配对`，两处都在 PSB 串里就已如此
（`…ナユタさま……！` 原文无 `」`；`…変わったのだ]` 原文用 ASCII `]`）⇒ **按「不改写」保留**，
报告里连「文件+场景+texts 下标」一起写明，别私自补 `」`。
