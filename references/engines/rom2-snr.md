# ROM2 / SNR（Kalmia8 · ACTGS）

> 路由/一句话索引见 `../engines.md`；主索引见 `../00-index.md`。

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
- 本作 10 块 / 2936 文件 / 460.8 MB。顶层：`adv.txa codes.txt config.txa default.msk effects.txa logview.txa main.snr matisse.fnt msgtex.txa name.txa rodin.fnt saveload.txa seura.fnt splash.txa sysmenu.txa sysse.bin systex.txa title.txa trial.txa voice.txa` ＋目录 `bgm bastup mask movie picture se voice voicen`。
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

## 同族第 2 作：参千世界遊戯 ～Re Multi Universe Myself～（PSV PCSG01194 / Dramatic Create・girls★dynamics）

链路：NoNpDrm `.zip`（`PCSG01194/data.rom` 1.23 GB，**无 pkg**）→ `psvpfsparser -z <zRIF>` → `rom2_extract.py`
→ 文本只在 `main.snr`（3,087,248 B）；顶层另有 `adv/appendix/config/gallery/logview/replay/saveload/sysmenu/systex/title/trial/voice.txa`（TXA4 纹理）、`*.fnt`（**FNT4** 可变长轮廓字体，未解）、`default.msk`、`sysse.bin`。

**★ 与 鳥籠 的两处变体（换作必回查）**：
1. **记录头 = `87 <A:u16> <F:u8> <T:u8> <C:u16> <LEN:u16>`，`T ∈ {0x00,0x01}`**（鳥籠只有 0x01）。本作 47 条 `T=0x00`
   是正文，若不收会漏。`A` 严格递增且 **1..22672 完全连续**（可当自洽判据）。
2. **★ 单字节 kana/记号 = 引擎自定义码表，不是 cp932 半角假名**！权威来源 = **eboot(ELF) 的「代码→Unicode」表**
   （本作 @`0xadc5a-0x10`，代码索引 `0xA1 ↔ index 8`）：

   ```
   0xA0=U+3000(全角空格) 0xA1=。 0xA2=「 0xA3=」 0xA4=、 0xA5=… 0xA6=を
   0xA7-0xB0=ぁぃぅぇぉゃゅょっー   0xB1-0xDD=あ…ん(平假名)   0xDE=！(U+FF01)  0xDF=？(U+FF1F)
   ```
   即「半角假名码位 → 全角平假名」，且 **0xDE/0xDF 两个 JIS X0201 浊点/半浊点位被改指 ！/？**。2 字节（lead
   `0x81-0x9F`/`0xE0-0xFC`）= cp932。**`0xDE/0xDF` 直接按 cp932 读成 ﾞ/ﾟ 会造成整篇无 ！？** —— 这是最容易踩的坑。
   验证法（照抄）：① 找 マニュアル `sce_sys/manual/*.png` 里的对话框截图当**已知明文**；② 在 main.snr 里按
   混合编码搜出该句原字节，逐位对齐即锁定全部语义（本作由 p018/p011 的
   「まあ、この程度の修羅場だったら…かしら、っと！」与 p021「…行きますよ！／…してください！」双锚定）。

**body 结构**：`[名札] @r [@p<名>. ] [@v<语音名>. ] 正文`
- `@r`(40 72)=框内换行⇒合并（一记录=一文本框=一次点击，p011 截图回证）。
- `@p`(40 70)=立绘/位置 ID（`10.` `160.` `30.`…）；`@v`(40 76)=语音名（**含 SJIS 假名/汉字**，如 `A_トモエ_014.`
  `B_フェリクス_09.`）；`@y`(40 79)/`@|`(40 7c) 无参控制（各 51 次）。三者**参数都是「到 `.` 为止的名字」**，
  按 ASCII 截断会把语音名漏进正文（鳥籠语音名纯 ASCII，故旧写法在此失效）。
- 名札 = 第一个 `@r` 之前的全部字节 ⇒ 丢弃。**无注音**（`@b` 0 次）、**无 `%0` 宏**（主角固定名）。

**选项**：`01 80 xx xx 07 <選択肢\0> <u8 blocklen> <opt>\0…\0\0`，本作 **34 组 / 71 条**（原文含「」）。

**排除**（未覆盖区扫描确认）：`NCSELECT` 内联菜单串、章节/路由标签（`プロローグ`/`共通ルート`）、
资源名表（`トモエ登場`/`トモエ顔`/`ロゴ左`/`タイトル画面`/`ライコウ戦`/`移転装置通常`…）、角色 ID 表、BGM 曲名表；
**无用語辞典**（main.snr/ELF 均无）；`movie/*.mp4` **无字幕轨**（歌词烧录画面，不可提）。

**成品**：22,743 行（正文 22,672 ＋ 选项 71），`check_text --name トモエ` PASS（トモエ 出现 2,971 行；主角名固定）。
工具：`scripts/sanzen_extract.py`（自包含，内嵌 ELF 导出的单字节码表，无需 eboot.elf 即可复现）。
