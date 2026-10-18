# HuneX「Ogre」系（allscr / MZX0）

> 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。
> ★ **续作案例（円環のメモーリア / 赤い砂堕ちる月 / 罪喰い for V）见 `hunex-ogre-dramaticcreate.md`**。
> 本册＝家族总则 ＋ カレイドイヴ ＋ マジきゅん。

## 家族总则（容器 / 压缩 / 脚本语法）
- **`mrgd00` 容器**：`6B 'mrgd00' + u16 count` + `count×8B` descriptor `(sector_off, offset, ssize_upper, size)`；
  `real_size=(ssize_upper-1)//0x20*0x10000+size`；`real_offset=8+count*8+sector_off*0x800+offset`。
- **`allscr.hed`**（仅 カレイドイヴ 有）：n×**8B** `HHHH`（小端）= ofs_low, ofs_high, size_sect, size_low：
  `offset = 0x800*((ofs_high & 0xF000)<<4 | ofs_low)`；`size = size_low==0 ? 0x800*size_sect : ((0x800*(size_sect-1) & 0xFFFF0000) | size_low)`。
- **`MZX0`**（HuneX 标准）：`4B 'MZX0' + u32 解压长 + LZ77`；**字面字节 XOR 0xFF**；128B 环形缓冲 + 4 类命令(`flags&3`)，每 0x1000 重置。
- **脚本语法**：解压后 CP932，指令 `;` 分隔、`_CMD(args)`；**各指令右闭括号数不等**（ZM=1；MSAD/SELR/LVSV/STBG/FADS=2；偶有注释）⇒ 稳妥取法：定位首个 `(`，其后全部 `rstrip(')')`。
- **通用文本指令**：`_ZM<id>(text)`=一次点击=一框；`_MSAD(text)`=续接同框（语义**逐作不同**）；`_SELR(n,text)`=选项；`_MTLK(1,名前)`=名札（不输出）；其余 `_STBG/_STCH/_STCN/_STFC/_VPLY/_WTVT/…` 忽略。
- **资源** `allpac.nam` 每条 32B，**nam[i] ↔ hed[i]**；`.MZP`/`.MRG` 均为 mrgd00；系统文本在 **eboot→ELF** 的 CP932 串表。

## HuneX「Ogre」系 —— allscr / MZX0（カレイドイヴ, PSV PCSG00520, éstciel/HuneX 2015）
- **平台/源**：PSV NoNpDrm ZIP（NPDRM + PFS 加密）。解密：`psvpfsparser -i <PCSG00520目录> -o <out> -z <zRIF> -f cma.henkaku.xyz`
  - **zRIF 未必在 NPS**（本作 `PCSG00520` = MISSING）→ 由 `sce_sys/package/work.bin`（NoNpDrm 假许可，512B，
    `0x10` 起 content id）经 `<psvdec>/util/rif2zrif.py` 现场还原。
  - ⚠️ **`psvpfsparser` 需联网访问 F00D 服务 `cma.henkaku.xyz`**（派生 `drv_key`）。网络被拦 → 403 → 报
    `parsing files.db... expected value`（boost property_tree json 错）。**免沙箱即通**。
  - eboot → ELF：`util/self2elf.py -i eboot.bin -o out.bin -k <zzzrif 生成的 work.bin>`（需 pycryptodome）。
- **`allscr.mrg`（脚本）**：`0x0000` 脚本名表 N×32B（30 字符 CP932 + `\r\n`，本作 N=171）；`0x1800` 起内嵌 `mrgd00`（N 成员，与名表同序）；其后 N 个脚本本体。（**本作＝唯一带外部 `allscr.hed` 的一作**）
- **文本指令**：`_ZM<id>(text)`=一次点击=一框；`_MSAD(text)`=续接同框；`_SELR(n,text)`=选项；`_LVSV(章节标题)`（要收）；`_MTLK(1,名前)`=名札（不输出）。
- **控制码**：`^`=框内软换行（合并）；**`@n`=框内换页/再点一次 → 拆新行**；`@w<n>`/`@h<n>` 演出参数删；`@e` 结束删；`＊Ａ`=主角姓、`＊Ｂ`=主角名（inline）。
- **事件CG回放**（`CHxx_EVCG_nnn`）与正章逐字重复 ⇒ 排除。`DICTIONARY.MRG` = **字体图像图集**（非用語集）。系统文本在 **eboot→ELF** 的 CP932 串表（`~0xA1100`）。

---

## マジきゅんっ！ルネッサンス（PSV PCSG00852, HuneX/BROCCOLI 2016）—— **同族但布局/语义不同**
- **解密**：同 PSV 常规（`work.bin`→`rif2zrif`→`pkg2zip -x`→`psvpfsparser`，看 `keystone: matched retail hmac`）。
  eboot 名字输入初始值表：ELF `0xCD508`=`愛ヶ咲` / `0xCD510`=`小花`（主角**愛ヶ咲 小花**，`Nameable`）。
- **★ `allscr.mrg` = 自包含 `mrgd00`（count=87），本作无 `allscr.hed`**：
  `[0]scr.nam`（84 名 ×32B）＋`[1]scr_adr.mrg`＋`[2]颜色小表`＋`[3..86]`84 个脚本（names[i]↔member[3+i]）。
  descriptor＝`so,of,su,sz`(u16×4)：`off=8+count*8+so*0x800+of`，`size=(su-1)//0x20*0x10000+sz`。
- **★ `@n` 语义与 カレイドイヴ 相反**：本作 `@n`(41) 与 `_MSAD`(41) **1:1 配对**（`_ZM(…@n)` 与 `_MSAD` 间仅隔
  `_WTVT/_STCN/_FADS`）；`_MSAD`=续接同框 ⇒ **`@n` 是框内暂停，须与 `_MSAD` 合并成一行**。按旧口径拆行 →
  **35 行引号不配对**。判据：**引号配对**当验收探针。
- **★ 0xEC4C = 姓/名分隔符**（CP932 未映射；19,217 实例全在「姓|名」间）→ 空格（正文自身亦用 `0x20`）。
  名札 `_MTLK1(,＊Ａ\xEC4CM＊Ｂ)`；`＊Ａ`=姓 / `＊Ｂ`=名（正文里姓常写字面、名才用 `＊Ｂ`）。
- **额外文本载体**：`_PSSM(idx,text)`=**MINISCENARIO**（ミニシナリオ 31 段，*MS_<route>_<nn>*，独有文本）；
  `_PRAM(idx,charid,text)`=**DEVMAIL**（剧情内メール，charid=发送者）。二者**非日志/回想**（与主线 `_ZM` 重合 0〜1%）。
- **排除**：`TEST_SCRIPT`(开发菜单)、`TEMPLATE`、`PROFILE`(无文本指令)、`_MTLK1` 名札、`_LVSV`(标题为 CG `ec_title0n`)。
- **`allpac.mrg`**（373 MRG＋5,849 MZP）＝ 图片/UI，无 `.mzx` 脚本、无辞典载体。
- **成品**：41,274 行（ZM 38,039＋PSSM 2,292＋PRAM 573＋选项 396；−25 空框 −1 跨框续句）。工具 `scripts/majikyun_extract.py`。

---

> **续作三例**（円環のメモーリア 第三种布局 / 赤い砂堕ちる月 第四种`_IF__`守卫块 / 罪喰い for V 第五种`_MSAD`续接＋空守卫块）见 → **`hunex-ogre-dramaticcreate.md`**

> ★**PSP 变体（字形码制）**：乙女的恋革命★ラブレボ!! Portable＝`scradr.mrg`/`scrbin.mrg`（`mrgd00`×36＋MZX0＋**再全字节 XOR 0xFF**）、
> 文本 `_ZM` 内是 **2 字节字形码**（`idx=(b0-0xA0)*60+(b1-0x3F)`，页 60 格；0..134 记号、136..218 平假名、219..304 片假名、≥305 汉字 JIS 区 0x30 行内 94 进）
> ⇒ 详见 **`hunex-ogre-loverevo.md`**
