# ASGARD 自研「TAT」文本脚本（PSV）

> 代表作：**5人の恋プリンス ~ヒミツの契約結婚~（PSV `PCSG00590`／2015-06-25／KADOKAWA・ASGARD）**
> 关键：**脚本是 UTF-8 明文文本 DSL**（不是字节码），难点全在「解密」与「成行」，不在解码。

## 1. 入口与解密
- 源常为 `[PSV-JP]xxx.zip`（≈943 MiB）解开是 `PCSG00590/` 文件树（2471 文件）。**整棵树是「未解密的 PKG 内容」**：
  连 `png` / `dirlist.txt` / `eboot.bin` 都熵≈8.0、无魔数。判据：`sce_sys/param.sfo`=`\0PSF` 明文、
  `sce_sys/package/head.bin` 头 = `7f 50 4b 47`（`\x7fPKG`，0x30 起 content id）、有 `sce_pfs/{files.db,unicv.db}`、`work.bin` 512B 明文。
- 解：

  ```bash
  ZRIF=$(python -c "import json;print(json.load(open('games.json'))['PCSG00590'])")   # psvdec-main/games.json
  bin/win64/psvpfsparser.exe -i "<app0 目录>" -o "<out>" -z "$ZRIF" -f http://cma.henkaku.xyz
  #   成功判据＝末行 "keystone: matched retail hmac"
  python util/self2elf.py -i eboot.bin -o eboot_elf.bin -k sce_sys/package/work.bin   # 需 pycryptodome（envs/default）
  ```
- 解密后：`script_tat/**/*.TAT` = **UTF-8-BOM 明文**；资源索引 `rdix.rson`（`RSON`＋ASCII 路径表，登记 330 个脚本）。

## 2. 脚本语法

```
[LABEL]                         ← label（行尾 //《$:LABEL》 是工具自动注释）
<WinFrame ON2,OFF>              ← 指令；行尾 //《*:…》 是工具自动注释
<Extend CHARA_LIPSYNC,hibiki>   ← 设定说话人立绘
【ヒビキ】                       ← 独立名札行（丢弃）
「とりあえずキミの家まで送るよ」<KW><WinClear>   ← 一次点击
```
- **点击边界 = `<KW><WinClear>`**；**软换行**＝一个框由多条物理行组成，仅末行带 `<KW>` ⇒ 必须「积攒到 KW 再成行」。
- 选项：`<SltDel>` → `<SltAdd idx,ID,text>`（idx 0/1/2，ID=分支 label）→ `<SltRun>`；**显示文本取第 3 字段**。
  `CERO_select.tat` 等 dev 菜单是 4 字段（`idx,文件名,label,标题`）——4 字段即非玩家选项。
- 非显示控制码：`#S5`/`#SC`（文字送り速度）、`#Ss`/`#Se`（慢速起止）、`#C0-9`（色）⇒ 剔除（本作 4,543 处）。
- 主角宏：`{firstname}` / `{familyname}`。**本作两名输入无默认值**（eboot `0x180244` 有「あなたの苗字／下の名前を入力してください」，
  `graph/name_entry/*.png` 只是标签图）⇒ 交付须自带占位名（本作取 ひなた／小野寺，避开 147 个既有名札）并写进报告。
- 其它指令：`<Extend MEMORIAL,角色,N>`（解锁纪念画廊）、`<Extend End>`（回标题）、`<Extend SEND_VMAIL,…>`（测试用）、
  `<CHARA …name=父>`（非 LIVE2D 的立绘角色）、`<Jump label>`、`<SltAdd>` 之外无文本。

## 3. 文件分组与取舍（本作实测）

| 组 | 处理 | 判据 |
|---|---|---|
| `00_PRO/SCR_PRO_A,B` ・ `<路线>/SCR_XX_01..29` ・ `end_a..d` | 收 | 正文/结局 |
| `SCR_XX_NN_h`（每线 5 个） | 收，紧跟 NN 话 | 「彼目線」追加篇；与其它文件文本框重合率 ≈0 |
| `SCR_XX_m01..m16`（共 90） | **不收**（回想） | 对「非 m 全库」覆盖率 **=1.00**（90/90），首行注释「ヒビキの回想その１。」 |
| `CERO/`（11） | 不收 | CERO 審査用替換稿＋dev 选择菜单 |
| `000_test/`（18）・`misc.tat` | 不收 | dev harness／占位 |
| `eboot.bin` UTF-16LE 文本 | 不收 | `special/メモリアル`（角色告白＋手紙）＋UI 文案＋引擎报错串 |

## 4. 源文破损（本作）
- 2 行被截断的指令（`<LIVE2D …` 缺 `>`；残片 `*:FADE_OUT(color={(255,255,255)》},time=700)`、`*:VOICE(filename=MAK_0308>`）
  ⇒ 判据「文本候选行含 `//《` 或 `*:` 或 `》`」整行剔除（全库仅此 2 行，未丢正文）。
- 半角 `｢｣`（SYOU 线 6 处）、半角 `()`（4 处）、缺 `」`（NOZUMU_end_a 1 处）、`」』`（1 处）⇒ 归一/定值修。

## 5. 工具
`scripts/prince5_extract.py`（`--src` 解密后 `script_tat`，`--out` 成品；内含 `NAME_FIRST/NAME_FAMILY`、`FIX_LINES`）。
