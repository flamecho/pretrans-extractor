# 引擎：5pb/otome 自研 `.evb` ＋ `MARC` ＋ `CPK`（マスケティア PSP）

**一句话**：ISO → `~PSP` EBOOT(type 9) 解出 ELF；`ca000_0000.cpk` → 自研 bytecode `.evb`（1078 个），
正文只在 **`FE 00`/`FE 02`**（＋`FE 30/31/32` 带样式的参数字节）之后，`0A 00` 结束一个文本框。

## 容器
- **CPK**（CRI）：`scripts/cpk.py` 直接解 → `ca000/*.evb` + `ar999_0000.bin`。
- **MARC**（自定义）：`uint32 count` + `(offset,end)` 记录。子档 e0=字体图集（512×872 **8bpp alpha 直通**，
  前 64B 是 alpha 渐变调色板**不是索引表**；swizzle 32×8），e1=同码域系统串（存档提示等＝罗塞塔之一）。

## `~PSP` EBOOT.BIN（Encrypt Type 9）
- 头 `0x7C`=9、tag `D91613F0`(code `0x5D`) → PPSSPP `PrxDecrypter` 静态 KIRK 密钥。
- 坑① `PRXType9::decrypt()` 跨块 AES 覆盖 struct 内 `sha1` ⇒ 自检比**解密后** sha1；
- 坑② `decryptKirkHeader` 输入是**已解过**的 kirkHeader。
- 脚本 `scripts/psp_prx_type9_decode.py`。产出 ELF（MIPS）。

## ★ 字符表（凭 corpus 锚点 + cast 反证）

```
hira : code ∈ [0x8181,0x81D3]              -> SJIS = code + 0x011E
kata : code = 0x81E1 + index                （序列见下，跨 0x8200 回绕 0x8100）
       序列 = ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅ
              テデトドナニヌネノハバパヒビピフブプヘベペホボポマミ
       tail : ユ=815B ョ=815C ヨ=815D ラ=815E リ=815F ル=817B レ=817C ロ=817D ワ=817F
              ン=81D7 ヴ=81D8 ヶ=81D9/81DA ー=825F
kanji: code = 0x8201 + (JIS行-0x30)*96 + (JIS列-0x21)   # 行跨距 96（一级 0x30-0x4F, 二级 0x50-0x74）
digit: 0x8130..0x8139 = 0..9
latin: A-Z = 0x8141..0x815A ; a-z = 0x8161..0x817A
punct: 8121=！ 8124=… 8127=々 **8128=（ 8129=）**（全库唯一括号对＝独白用；非「」）812C=、 812E=。 8160=？ 8180=・ 8200=〜 / 8E13=―(破折号)
kanji_fix (euc_jp 不覆盖的 JIS 末尾格，据上下文): 8DDD=嗅 8DE1=媚 8DE3=諍 8DE7=璧 8DE9=疼 8DEA=眷 8DEF=贅
```
- 控制码（丢弃）：`8DD7/8DD8`(人名包裹) `9C00-9FFF`(演出) 及汉字表每行末 2 填充槽 `(code-0x8201)%96>=94`。
- 锚点（cast 反证全中）：アンヌ王妃 / コンスタンティン / コンスタンス / ロマンチックだね / トレヴィル /
  プランシェ / ロシュフォール / バッキンガム塔 / シュバリエ学園 / サファイア / ダイヤ /
  **ジャンヌ・ダルク・レ・ミゼラブル・ヴィクトル・ユーゴー**(⇒ 8180=・, 815B=ユ) /
  **2年C組・帰りのHR・これでOK・Bonne année**(⇒ 拉丁区间) / 三ヶ月・数ヶ月。

## `.evb` 脚本（关键）
- **文本框 = `FE <print-op> [若干非文本参数字节] <正文> 0A 00`**。
- **★`print` 操作码是一整族（48 个）**：判据＝**所有 FE 操作码中以 `0A 00` 结尾者** ——
  `00 02 13 15 1D 1E 24 25 27 29 2B 30 34 36–3B 3D–3F 45 48 4B–53 55 57–5A 5F 80 81 82 84 87 88 8B 8C C0`。
  参数个数不必区分——读取器遇到非文本字节直接跳过（`FE 24 00 <text>` 等）。
  ⚠ **只认 `FE 00/02` 会漏整段旁白**（ev000_0002 由 7 行 → 24 行）；改用「任意 0x81–0x9F 对全流扫描」
  则混入**参数块字节**（多 ~3400 行垃圾，行首「罪」「總」）。**正解＝print 族白名单 ＋ `0A 00` 定界**。
- `FE` = 2 字节操作码前缀，须整体跳过（否则 `81 28`=「 被读成 `82 81`）。
- `0A` = 框内换行（成行时合并）；**`0A 00` = 文本框结束（一次点击=一行）**。

## 工具

| 脚本 | 作用 |
|---|---|
| `scripts/psp_prx_type9_decode.py` | `~PSP` Encrypt Type 9 EBOOT → ELF |
| `scripts/musketeer_charset.py` | 字符表 + `decode_char` / `decode_stream` |
| `scripts/musketeer_extract.py` | `.evb` → 全文本（FE 正文、`0A 00` 成行、去重、UTF-8 BOM/LF） |
| `scripts/cpk.py` | CRI CPK 解包（通用） |
| `scripts/marc_font.py` / `musketeer_ar999_font.bin` | MARC 字体图集复原 |

## 重跑

```
python scripts/musketeer_extract.py <解包出的 ca000 目录> 提取结果/マスケティア_全文本.txt
python scripts/check_text.py 提取结果/マスケティア_全文本.txt --name ダルタニアン
```

## 结果
1078 evb → **20,416 行 / 419,214 字**；未解析 **16 (0.004%)**（JIS 末尾孤字）。
唯一品检遗留：1 行开「未闭合（源数据本身无 `」`）。

- **宏码**：`1D 00` = 主角名插入（813 框）；默认名 `ダルタニアン`。`1A/1B/1C/1E/20 00` = 章节/场景标题衔接符（不分框）。

- **换页命令**（文本框终止符，除 `0A 00` 外）：`FB FF <u16> <u32 B> <u32×B>` ／ `FE FF <u16> <u32> <u32> <u8> FE 00 <正文>`。长旁白・选项列表＝多页。
- **名字宏 `1D 00` 可落在打印命令参数区末尾**（`<print-op> <params> 1D 00 <正文>`）⇒ 起点须并入该宏，否则产出 `、私だ。`（行首顿号）。
- 数据表伪框：`<u16> 0A 00` 形态，过滤「≤3 字且全汉字」。
