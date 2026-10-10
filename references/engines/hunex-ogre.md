# HuneX「Ogre」系（allscr / MZX0）

> 路由 / 一句话索引见 `../engines.md`。

## HuneX「Ogre」系 —— allscr / MZX0（カレイドイヴ, PSV PCSG00520, éstciel/HuneX 2015）
- **平台/源**：PSV NoNpDrm ZIP（NPDRM + PFS 加密）。解密：`psvpfsparser -i <PCSG00520目录> -o <out> -z <zRIF> -f cma.henkaku.xyz`
  - **zRIF 未必在 NPS**（本作 `PCSG00520` = MISSING）→ 由 `sce_sys/package/work.bin`（NoNpDrm 假许可，512B，
    `0x10` 起 content id）经 `<psvdec>/util/rif2zrif.py` 现场还原。
  - ⚠️ **`psvpfsparser` 需联网访问 F00D 服务 `cma.henkaku.xyz`**（派生 `drv_key`）。网络被拦 → 403 → 报
    `parsing files.db... expected value`（boost property_tree json 错）。**免沙箱即通**。
  - eboot → ELF：`util/self2elf.py -i eboot.bin -o out.bin -k <zzzrif 生成的 work.bin>`（需 pycryptodome）。
- **`allscr.mrg`（脚本）**：
  - `0x0000`：**脚本名表** N 条 × 32B（30 字符 CP932 名 + `\r\n`）。本作 N=171（`CH00_A`…`CH07_SP06`、`CHxx_EVCG_nnn`）。
  - `0x1800` 起：内嵌 `mrgd00`（N 成员，与名表同序）。
  - 其后：N 个脚本本体，各自从 hed 给出的 offset 开始。
- **`allscr.hed`**：n × **8B 通用条目** `HHHH` = ofs_low, ofs_high, size_sect, size_low（小端）：
  `offset = 0x800 * ((ofs_high & 0xF000) << 4 | ofs_low)`；
  `size = size_low==0 ? 0x800*size_sect : ((0x800*(size_sect-1) & 0xFFFF0000) | size_low)`。
- **`mrgd00` 容器**（`allpac` 与其成员皆用）：`6B 'mrgd00' + u16 count(count*u16 @+6)` +
  `count × 8B` descriptor `(sector_offset, offset, ssize_upper, size)`；
  `real_size = (ssize_upper-1)//0x20*0x10000 + size`；`real_offset = 8 + count*8 + sector_offset*0x800 + offset`。
- **`MZX0` 压缩**（HuneX 标准）：`4B 'MZX0' + u32 解压长度 + LZ77 数据块`；**字面字节 XOR 0xFF**。
  128B 环形缓冲 + 4 类命令(`flags&3`：0=RLE / 1=backref / 2=ringbuf / 3=literal)，每 0x1000 重置。
  `allpac.src` 是 ASCII **MERGE FILE HEDDER**，逐条列出 `data.w h'...,h'...,h'...,h'...  ;NNNN 原始路径`（生成 allpac.hed 的源）。
- **脚本语法**：解压后为 CP932 文本，指令以 `;` 分隔，`_CMD(args)` 形式。**各指令右闭括号数不等**
  （ZM=1；MSAD/SELR/LVSV/STBG/FADS=2；偶有注释 `　日本語)` 追加）→ 稳妥取法：定位首个 `(`，
  其后全部 `rstrip(')')`。例：`_ZM99c02(「……」);`、`_MSAD(^ん……そういやここって……」));`
- **文本指令**：`_ZM<id>(text)`=一次点击=一个文本框；`_MSAD(text)`=续接同框；`_SELR(n,text)`=选项；
  `_LVSV(章节标题)`；`_MTLK(1,名前)`=说话人名（规范：不输出）。其余 `_STBG/_STCH/_STCN/_STFC/_VPLY/_WTVT/...` 忽略。
- **正文控制码**：`^`=框内软换行（合并）；**`@n`=框内换页/再点一次 → 应拆为新行**；`@w<n>`/`@h<n>`=窗口演出参数（删）；
  `@e`=结束标记（删）；`＊Ａ`=主角姓、`＊Ｂ`=主角名（inline 替换）。注音 `<基,読>` 仅见于开发残留 `TEST_SCRIPT`。
- **事件CG回放脚本**（`CHxx_EVCG_nnn`）与正章**逐字重复**，提取时应排除（本作 100 本仅 6 条独有句子）。
- **资源命名**：`allpac.nam` 每条 32B（大写文件名 + `\0` pad + `\r\n`），**nam[i] ↔ hed[i]**；
  `.MZP`/`.MRG` 均为 mrgd00 容器。DICTIONARY.MRG = **字体图像图集**（非用語集）。
- **系统文本**：不在资源里，而在 **eboot→ELF** 的 CP932 串表（`~0xA1100`；另有 UTF-8 串）。用需全角假名的过滤提取。

---
