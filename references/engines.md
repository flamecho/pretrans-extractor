# 项目 _trans —— 引擎路由（索引）

> 引擎**细节已按家族拆到同目录 `engines/*.md`**（2026-10-10，单文件最大 9.6 KB）。
> **用法：先在本表定位引擎，再只读对应的那一个 `engines/*.md`** —— 不要整目录读。
> 工具索引见 `../scripts/INDEX.md`；作业规范与坑索引见 `../SKILL.md`。

## 引擎一句话索引 ＋ 详见文件

| 引擎 | 代表作 | 一句话要点 | 详见 |
|---|---|---|---|
| NoNpDrm / PSV PFS | PSV 通用 | pkg2zip → `psvpfsparser -z <zRIF>`；`zRIF` 与 `work.bin` 一致 ≠ 可用，看 `header signature is valid` | `engines/psv-pfs.md` |
| Switch XCI / NCA / NSP | Paradigm Paradox・滄海天記・悪役令嬢 | PFS0→NCA3(明文头@0x200)→RomFS；`--keyset/--titlekey` 传**加密**值 | `engines/switch-nca.md` |
| **ROM2 / SNR（Kalmia8·ACTGS）** | **鳥籠のマリアージュ ～初恋の翼～** | 容器 `ROM2`：0x20 头 ＋ 顺序目录块 `[u32 count][count×12B: nameOff(bit31=dir)/off(单位0x200)/size][NUL 名]`，名字偏移**相对块起点**；脚本 `main.snr`：`87 <A><F> 01 <C><LEN><content>`，content=`[人名]@r[@v语音]正文`；**选项内联 `07 選択肢\0 <u8 len> <opt>\0…`** | `engines/rom2-snr.md` |
| Koei CDAR v2/v4 | コルダ・遥か・下天の華 | 文本 `04 <u16 len> <cp932> 00`；框边界 BOUND/C7/M91；v4 两套定长插值表；FD 改内联记录插入 | `engines/koei-cdar.md` |
| Otomate VM | BAW・フォルティッシモ | JIS X0208；块 `…0xff68…`；**字体槽禁跨作** | `engines/otomate-vm.md` |
| STCM2L（Idea Factory） | 猛獣(Switch/UTF-8)・PANDORA(PS2/CP932)・Norn9(PSV/UTF-8) | 链 `[u32 size][payload]`；文本记录 `[addr][c1][c2]…[0][len/4][1][len][text]`；PS2 容器＝CRI UNI2；PSV 指令 `[is_call][opcode][nparams][length]`，**opcode 逐文件平移 Δ** | `engines/idea-factory-stcm2l.md` |
| CRI CPK ／ CRI AFS | 通用 ／ 花宵ロマネスク | `cpk.py`(>>8) / `cpk_v1.py`(&0xFF)，判据 `@UTF`；AFS＝自研「SJIS 索引码」（`FFF0`=框、`FFE6/7`=姓/名宏，数字·全角拉丁整体错位 −1 槽） | `engines/cri-cpk-afs.md` |
| KiriKiri XP3（3 态） | クリムゾン・ロワイヤル・蝶の毒 初回版/幻想夜話 | 标准／DropWave OTag（`.ks/.tjs`=zlib+UTF-16LE）／**区间 1 字节 XOR**（孤立字节另键→逐位置定值复元表） | `engines/kirikiri-xp3.md` |
| Malie System（Camellia LIBP / MalieVita） | OmegaVampire・英国探偵ミステリア | PC：LIBP=Camellia；Vita：LIBP **明文** ＋ **offset 块单位 2048**、exec.dat 名=ASCII、STRT=CP932；AlphaROM 壳须运行时 dump | `engines/malie.md` |
| WillPlus / AdvHD（`.wsc`） | Butterfly Lip / Gloss / Rouge | arc＝ext 组容器（21B/条）；**WSC 每字节 `rotl_8(c,6)`**；文本 `op41`旁白/`op42`名+台词/`op02`选项，目标指令须按表分派 | `engines/willplus-advhd.md` |
| Unity ＋ 自研 ADV | ハイリゲンシュタット・ヴェリテ・悪役令嬢 | PSARC→`resources.assets`(TextAsset)／TKG `0x10 MSG_PARAM`=点击／CSR1.00 `06 01`·`06 03`=文本框 | `engines/unity-adv.md` |
| HuneX Ogre（allscr / MZX0） | カレイドイヴ | `MZX0`(字面 XOR 0xFF)→CP932 `_CMD()`；`@n`=下一页须**拆行**；UI 在 eboot→ELF | `engines/hunex-ogre.md` |
| **HuneX HESL/UNAS（HGTC/HPAC/HLZS/HFNT/CSB/HESL/HESE）** | **BELIEVER!** | 与 Ogre 不同族；`script.heslnk`→`charset.csb`(**字符表**)＋`HESE`；文本码＝**`csb[code-0x8000-6]`**；`0x8000`=框内换行(合并)、`0x2C`=软换行 | `engines/hunex-hesl.md` |
| Takuyo gss | ひめひび 1・続！二学期 | `LSDARC V.100` ＋ `SCR 2.00`；文本 op `0x5a/0xfc/0xf0/0x5c`；`0x10c` 动态调用须展开 | `engines/takuyo-gss.md` |
| Nitroplus NPA / NSS | Lamento -BEYOND THE VOID- | `.npa` 索引名＋内容双层加密、25 套预置方案（zlib 流认定）；`.nss`＝cp932/CRLF 派生脚本 | `engines/nitroplus.md` |
| SiglusEngine | 罪ナル螺旋ノ檻 | 单 exe = PE + RAR5 SFX；`.pck`+`Gameexe.dat`+资源 key | `engines/siglus.md` |
| 自研「テキスト方式 ADV」 | クランク・イン | 文本在 `cmp.psarc`：UTF-16LE 行式剧本×1622 + `scrlst.txt`（`end−start`=文本框数＝校验法） | `engines/text-mode-adv.md` |
| 其它自研 / 小众 | PP・滄海天記・ブラザーズ・あさき、ゆめみし・Tiny×MACHINEGUN・時函・KoiGIG・逢魔が刻 | Regista advGame／Artemis `pf8`／BGI/Ethornell／System-NNN `.spt`／LTEngine／NScripter（＋`.nsa` 变体・MNP）／NIS-NML | `engines/misc-engines.md` |

## 维护约定
- **新增引擎 ⇒ 新建 `engines/<slug>.md`，然后只在本表加一行**（含一句话要点 ＋ 详见文件）。**不要往本文件里堆细节。**
- 已有引擎的新发现 ⇒ 直接追加到对应 `engines/*.md`。
- 每个引擎文件自包含（容器 → 解密 → 脚本结构 → 成行 → 排除 → 工具），方便「一次只读一个」。
