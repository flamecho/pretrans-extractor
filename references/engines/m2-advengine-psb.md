# M2「ADVENGINE」（Squirrel/Sqrat ＋ PSB）— PSP/PSV/NS 通用

> 首作：**[PSP-JP] Beyond The Future -Fix The Time Arrows-**（MAGES. × Rejet, 2011, `ULJM05988`）。
> 同族＝任何 `*_info.psb.m` ＋ `*_body.bin` 成对的数据盘（M2 的 Kaleido/ADV Workshop 系）。
> 工具：`scripts/btf_pgd.py`（PGD）・`btf_mdf.py`（MDF 壳）・`btf_carve.py`・`btf_extract.py`；PSB→JSON 用 `scripts/freemote/PsbDecompile.exe`。

## 1. 认引擎（3 个锚，命中任一即是）

| 锚 | 证据 |
|---|---|
| 文件 | `PSP_GAME/USRDIR/fileinfo.psb.m` ＋ `INSDIR/INSTALL.BIN`（PSP）；或 `*/{scenario,image,sound,voice,motion,font,script,config}_info.psb.m` |
| ELF 串 | `ADVENGINE`／`script/main.nut`／`Sqrat` 导出类：`SQPSBFile` `SQFileData` `SQTextRender` `SQLayerView` `MInstallUtility` |
| 数据头 | 成员头 `mdf\0`＋u32 原始长度＋`78 9C/DA`（zlib）；PSB 本体 `PSB\0` |

## 2. 容器链（PSP）

```
ISO9660
 ├ USRDIR/fileinfo.psb.m        ← MDF 壳的「根索引」PSB（1 KB 级）
 ├ USRDIR/movie/*.pmf
 ├ SYSDIR/EBOOT.BIN             ~PSP；BOOT.BIN 可能**全 0**（本作 1.63 MB 全 0）
 └ INSDIR/INSTALL.BIN           ← ★ PGD 加密的「全部数据」（本作 744 MB）
```

**`fileinfo.psb.m` → JSON 的 `umd_root`**：`名字 → [?, size, offset]`（3 元素＝INSTALL.BIN 内字节偏移，2048 对齐；
2 元素 `[LBA,size]` ＝ UMD 直读，如 movie）。**游戏运行期不读 UMD 上别的文件**，所以正文只在 INSTALL.BIN 里。

**PSB 键**：13 字符、紧跟在 `PARAM.SFO` 的 `DISC_ID` 串后面（本作 `ULJM05988` 后即 `V4fSjadn4mnAn` @0x17407c）。
MDF 的 seed ＝ **键 ＋ 文件名**（`scenario_info.psb.m` 就带扩展名；body 成员用「条目名 ＋ `expire_suffix_list`」，本作 `.scn.m`）。

## 3. INSTALL.BIN ＝ PGD（\0PGD）

头：`00 'PGD' | u32 key_index=1 | u32 drm_type=1 | 0`；`0x10` 起全随机 ⇒ 是 PGD 而非裸包（误判表现：
按 umd_root 偏移直接切出来 `79 47 9a b3…`，四条 MDF 试解全败）。

- **先查 `scripts/pgdecrypt.exe`**（tpu's，`pgdecrypt.exe INSTALL.BIN` → `INSTALL.BIN.decrypt`，同族 PSP 作通用）。
- 无 exe 时用 `scripts/btf_pgd.py`（**可随机访问**，只解需要的区段；本作 `scenario_body`+`script`+`config` ≈ 11 MB）：
  `drm_type=1 ⇒ mac_type=1 / cipher_type=1 / 固定键 dnas_key1A90`；
  BBMac ＝ AES-CMAC(`kirk7_key38`) `^ loc_1CD4`（有 vkey 再 `AES_enc` 一次）⇒ 用 `MAC_80`（`pgd[0:0x80]` vs `pgd[0x80:0x90]`）一验即知对错；
  `vkey = MAC(pgd[0:0x70]) ^ AES_dec_k38(pgd[0x70:0x80])`；
  内容 = CTR 变体：`nonce = AES_dec_k39(key ^ loc_1CF4) ^ loc_1CE4`，`ks_i = AES_dec_k63(N||LE(1+i)) ^ (N||LE(i))`；
  DESCRIPTOR 在 `0x30`（`file_size@0x44 / block_size@0x48 / data_offset@0x4c`）、数据在 `0x90`。
  只用 kirk 公开表 3 把键（0x38/0x39/0x63），**不碰 KIRK 硬件密钥**。算法逐行对应 `tpunix/kirk_engine` 的
  `npdrm/dnas.c` + `kirk/amctrl.c`。

## 4. PSB / MDF 壳

- 成员内层＝MDF：`mdf\0`＋u32 原始长度＋zlib。`btf_mdf.py <file> <key> <out> [keylen=131]`。
  keylen 通常是 **131**；不对时表现为 `incorrect header check`（换 97/64 或让 PsbDecompile 自推）。
- `voice_body.bin` / `sound_body.bin` 是**裸 PSB**（不带 MDF 壳）；`savedata/*.png` 是裸 PNG。
- PSB→JSON：`PsbDecompile.exe <x.psb>`；索引类用 `PsbDecompile info-psb <x_info.psb.m> -k <key> -l 131`
  （⚠ 本作 `info-psb` 在 **body 未解 PGD** 时会抛 `NullReferenceException`——先把 body 解出来再跑）。

## 5. 剧本（PSB `Scn`）

```json
{"scenes":[{"label":"*start","title":"兆し","texts":[[spk,null,text,null,flag,state],…],
   "lines":[…],"selects":[{"text":…,"target":…,"exp":…,"eval":…}],"selectInfo":{…},
   "nexts":[{"storage":"0-main-2.txt","target":null,"type":0}]}]}
```

- **一次点击＝一行**：`texts[]` 每项一框；`scenelist.json` 的 `textCount` 与 `len(texts)` 逐场相等（闭合校验用）。
  `*select` 场景 `textCount=1` 但 `texts=0`（选项另计）⇒ 核对行数时要减掉「有 selects 的场景数」。
- 框内 `\n` ＝软换行（≤3 行）⇒ **合并**。
- `texts[i][0]` ＝说话人（`""`＝叙述、`null`＝神之声）⇒ 名札**不进正文**。
- 选项：`selects[].text`；`selectInfo.type ∈ {map,chara,town}` 时同一文本会按 `eval` 分支**重复两条**
  （`f.ing_1>0` / `==0`，target 不同）⇒ **同场同文折叠成一条**（本作折叠 281/1,087）。普通选项无重复。
- 内联标签：`%C`、`%<n>#<hex>;`、`%<n>`、`\w`（停顿）⇒ 全剥；剥后必须复扫 `%`/`\\` 残留＝0。
- 主角宏：本作只有 `$f.name;`（1,519 次）⇒ inline 默认名 **リリス**（vndb v7770：Lilith / Nameable）。
- **顺序＝`scenelist.json`**（`list[]`：`storage / target / title / textCount / selects`），覆盖全部场景，零遗漏；
  **不要**用文件名序或文件内 label 序（分支 label 如 `*0-main-5_1` 会乱）。

## 6. 收 / 不收

| 收 | 不收 |
|---|---|
| `scenario/*.scn.m` 的 `texts` ＋ `selects` | `config/text.psb.m`（存档/安装系统提示） |
| （本作无用语辞典） | `script/*.nut.m`（Squirrel 字节码 `FA FA RIQS`，UI/系统逻辑） |
| | `scenelist` 的 `title`（回想菜单用场景名，非上屏正文） |
| | `charvoice.psb`（角色语音配置）・`classlist.psb`（图层类定义） |
| | `testsozai.txt`（`素材展開用`＝开发测试，场景只有 1 行） |

## 7. 逐作注意

- **键必须从 EBOOT 现取**（跟在 `DISC_ID` 后面 13 字符），**不要跨作复用**。
- `BOOT.BIN` 可能是全 0（本作）⇒ 别指望「明文 ELF 金矿」，要引擎信息就解 `EBOOT.BIN`。
- PSB 里 `scenes[]` 可能多于一（本作 1 场景/文件最普遍，但同族有多场景文件）。
- `selects` 条目字段分两类：**改旗标**（`exp`）与**条件显示**（`eval`）——`eval` 只用于互斥分支，不参与文本去重以外的判断。
