# ROM2 / SNR（Kalmia8 · ACTGS）

> 路由 / 一句话索引见 `../engines.md`。

## ROM2 / SNR（Kalmia8 · ACTGS 引擎）—— 鳥籠のマリアージュ ～初恋の翼～（PSV PCSG90230）

链路：官方 pkg ＋ `work.bin` → `rif2zrif.py` 得 zRIF → `pkg2zip -x`（**pkg 必须先硬链接到 ASCII 路径**，
pkg2zip 是窄字符程序，日文路径直接 `cannot open`）→ `psvpfsparser -i app/PCSG90230 -o dec -z <zRIF> -f cma.henkaku.xyz`
（`keystone: matched retail hmac` 为准）→ `dec/data.rom`（483 MB）。
eboot 为 SCE SELF，`self2elf.py -k work.bin`（**需 pycryptodome，用 venv python**）；ELF 内含引擎串 `kalmia8`、
`dramatic create`、角色 id `kanako/yuuto/shota/tsukasa/souichi/makoto`、名字输入表。

### 容器 `ROM2`（data.rom）
```
0x00 "ROM2"
0x04 u32 version=1
0x08 u32 ?            (metadata 结束)
0x0c u32 unit = 0x200  # 文件偏移单位
0x10 16B digest
0x20 起 = 目录块序列（块起点间 16 字节对齐）：
   u32 count                        # 含 "." 与 ".."
   count × 12B entry:
       u32 f0 : 名字偏移（**相对本块起点**；bit31 = 目录项）
       u32 f1 : 数据偏移（单位 unit，仅文件）
       u32 f2 : 数据大小（字节，仅文件）
   count 个 NUL 结尾名字（位置 = 块起点 + (f0 & 0x7fffffff)）
```
- 目录树按「块出现顺序 = 根 → 各子目录（进入队列）」展开；块 0 = 根（33 项）。
- 本作 10 块 / 2936 文件 / 460.8 MB。顶层：`adv.txa codes.txt config.txa default.msk effects.txa logview.txa
  main.snr matisse.fnt msgtex.txa name.txa rodin.fnt saveload.txa seura.fnt splash.txa sysmenu.txa sysse.bin
  systex.txa title.txa trial.txa voice.txa` ＋目录 `bgm bastup mask movie picture se voice voicen`。
- `*.txa`(magic `TXA4`) 内是带名的图像条目（adv/panel/quicksave/skip…）＝**纹理图集**；`*.bup`(magic `BUP4`)＝立绘
  （kana1_1/mako1l00… 前缀＝角色）;`*.msk`/`*.pic`＝图像；`codes.txt`＝字体用字符码表（单字+CRLF）；`*.fnt`＝字体；
  `*.at9`＝ATRAC9；`*.mp4`＝视频。**文本只在 `main.snr`。**
- 工具：`scripts/rom2_extract.py`。

### 脚本 `main.snr`（magic `"SNR "`，1.44 MB）
- 头：`"SNR "` + u32 filesize + 若干 u32 + 分区偏移表（@0x50 资源名表、@0x12024 起 BGM 曲名/菜单/场景名表）；
  **指令流自 0x12bb0 起**。
- **消息记录**（本作 14,450 条；`A`=记录序号 1…14460 连续）：
  ```
  87 <A:u16> <F:u8> 01 <C:u16> <LEN:u16> <LEN 字节 content>
  ```
  `C`=0xffff（10143 条）或小整数（场景/组 id）；**不影响成行**。
  `content` = `[说话人名] @r [@v<语音名>] 正文`：
  - `@r`(0x40 0x72) = **框内换行**；实测一记录最多 3 行（`@r` 计数 0/1/2/3 ⇒ 1~4 段，首段为名札）
    ⇒ **一个记录 = 一个文本框 = 一次点击**，行内 `@r` 全部合并。
  - `@v`(0x40 0x76) + ASCII 语音名（如 `kan_00001.`）⇒ 丢弃。
  - `@b 读音. @< 基底 @>`（0x40 0x62 / 0x40 0x3c / 0x40 0x3e）= **注音** ⇒ 只留基底（如 `藤井　雅紀。`）。
  - `%0`(0x25 0x30) = **主人公名宏** ⇒ 替换为默认名。默认名取自 eboot 名字输入表三槽
    （`佳加香可夏かカ` / `奈夏南那名なナ` / `子こコ`）+ 固定姓 `藤井` ⇒ **藤井 佳奈子**；`%0` 只含名（`%0ちゃん`→`佳奈子ちゃん`）。
- **选项**（本作 45 组 / 91 选项，**内联于指令流**）：
  ```
  … 01 80 xx xx 07 <選択肢\0> <u8 blocklen> <opt1>\0<opt2>\0 … \0\0
      4a 01 80 <n> 00 <target:u32> × n     # 各选项分支目标（= 文件偏移）
  ```
  `blocklen` = Σ(选项字节数+1) + 1（含末尾终止 NUL）。
- **排除**（判据＝是否直接上屏）：0x12bd8–0x12e49 的菜单串（`シーン回想`/`シナリオ選択`/`体験版ルート選択`/
  `プロローグ`/`睦ルート`/`おまけ…`）、`F8F0 <grp> 00 <len> <name> 00` 的 **route/chapter 元数据**
  （`共通ルート`/`協力ルート`/`空っぽの鳥籠`/`うたかたの恋`/`初めてのキス`…，作为选项旁的路由/章节标记出现，
  **实测不以消息记录上屏**）、BGM 曲名表（サウンドテスト）。
- 工具：`scripts/torimari_extract.py`（记录/选项/注音/人名宏/清洗）。
- 本作产物 14,541 行（正文 14,450 + 选项 91），`check_text.py --name 佳奈子` PASS。
