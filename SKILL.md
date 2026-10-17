---
name: pretrans-extractor
description: >
  从日文 VN / AVG 游戏（PS2 / PSP / PSV / Switch / PC）封包资源中提取全部剧本文本，
  按「一次点击 = 一行」规范化输出，覆盖 CPK / CDAR / PFS / NCA / XP3 / Unity / BGI 等 30 余种引擎。
  触发：游戏文本提取、剧本 rip、容器解包、字形/码表逆向。输出用于制作 LunaTranslator 预翻译文件。
---

# 日文游戏剧本文本提取 —— 作业规范

> **本文件＝必守规则＋流程骨架＋导航**。**开工读：本文件（§0〜§2）＋ `references/00-triage.md`（判型）＋ `references/pitfalls/A1-decode-core.md`（解码/提取坑）＋ `references/pitfalls/C1-deliver.md`（交付/流程坑）**；其余按需，勿预读。

## 0. 输出规范（强制；用户口径，不得改）

**形态**：UTF-8 **with BOM** / **纯 LF**（0 CR）/ 0 `U+FFFD` / 0 控制符 / 0 `〓`。
只出**正文＋选项**，**不产出**「说话人表」「系统・UI テキスト」之类的附属文件。

**要收**：① 正文（旁白/独白/台词）② 选项（一行一条、按序；**图片式无字选项跳过**）③ 直接上屏特效（鏡文字/扉文/歌詞）④ 用語辞典/豆知識（`【見出し語】解説文` 一行一条、不带读音、换行合并、**并入末尾**）。
**不收**（判据＝**是否直接渲染到画面**）：① 日志/回想载体（backlog/log/replay；显示稿副本、改稿不同步）② 系统/UI（config/help/save・`sysscn`）③ 调试串、`error :`、名字字库、他作遗留串

**行粒度**：**一次点击 = 一行**；同一文本框内的软换行**合并**。两个方向都会错——用**引号配对**当验收探针。
**说话人**：**不加前缀**（独立名札行 `【秀雄】` 丢弃；行首 `【名】`+正文、`名前：` 去前缀）。
**人名与变量**：行内替换，不留 `%s`/`Name[n]`/`〓`。主角可改名 ⇒ 必然存在插入宏，**不可当空控制码丢掉**；⚠ **字面姓氏多为他人，先证身份再改名**（`04` §2.7）。
**不改写**：保留原文、不翻译、不润色。**禁止猜测**——不可解码位用 **`〔未解析〕`**（**禁 `〓`**，§1 判 E）＋报告单列；专有名词先外部核对。

**① 禁止穷举 ＋ ② 禁止 OCR（最高优先级）** —— 破码表/猜键/修化け一律**先结构化推理**（魔数、**已知明文反解**、上下文、确定表、**参考实现**）。
- **① 禁穷举**：扫偏移/试变换/全码表匹配——仅当**无其他方案且用户已确认**才可（规模须先报）。
- **② 禁 OCR**：不得用「渲染字形＋OCR/模板匹配」解码（变宽/打包字体必崩）；字形渲染**只准人工目视单字**，不得批量建表
- 正解：**逐位置定值复元表**；码表基址用**一条已知明文**锚定（BELIEVER! 秒级）。

**③ 禁无规划试错**——先立**假设＋证伪条件**；同假设**2 次无新信息⇒换路**、单点 **>3 次未收敛⇒汇报**。

## 1. 交付前自检（必跑）

脚本位置：装了 skill 用 `scripts/`（工作区同名在 `scripts/`，同名同版）。
跑 `python <skill>/scripts/check_text.py "提取结果/XX_全文本.txt" --name 主角名`（**退出码 0=PASS**）。

- **判据**：`[E]` BOM/CR/`U+FFFD`/`〓`/控制符/ **半角假名**/ **PUA**/ **引号不配对**/ **说话人残留**（4 形态）；
  `[W]` 主角名未出现 / 空行 / 超长行 / 相邻重复行 / 非日文字符。
- **人工必做**：① 抽读 6 处（各 10 行）；② **名札表整表导出 → 逐个比 vndb**（`04` §2.6-7）；
  ③ **名札前缀词频复扫** —— 对成品跑 `^([^\s「」（）]{1,12})「`，只剩叙述句即干净；出现 `？？？`/`ＭＣ`/纯名字 ⇒ 名札表漏项（`references/pitfalls/B2-tags-resume.md`）

## 2. 标准流程（骨架 S0〜S8）＋ 上下文卫生

| 步 | 做什么 | 关键判据 |
|---|---|---|
| **S0 识别** | **先读 `references/00-triage.md`**（平台→容器→脚本→厂商，四张对照表）＋ `python scripts/identify.py <文件或目录> [--deep]` ＋ **写「做题卡」** | 一次拿到「引擎＋命令＋该读哪份 `engines/*.md`」；**表里没有 ⇒ 走 triage §E 四步攻坚**。⚠ `identify.py` 会误判（曾把 CHD 壳判成 KiriKiri）⇒ **结论只当假设，用魔数复核一次**。**同族先查历史**：`Grep <厂商\|引擎> references/engines.md` → 命中就往 `engines/<slug>.md` ，看同族各作的差异 |
| **S1 源** | 定位母本，`7z l` 看结构 | 头部加密？密码常在同目录小 txt；**同捆更新程序先解** |
| **S2 容器** | 解外层，拿脚本资源 | 先跑 `identify.py`；魔数 `XP3`/`CPK`/`PFS`/`NCA`/`PSARC`/`NSAC`/`AFS`/`ROM2`…；Will `Rio.arc`＝ext 组容器。**解包后立刻 `probe.py jp`**：假名/汉字 0 命中 ⇒ 这层没有正文，换载体（别在条目结构里硬找） |
| **S3 解密** | 还原文件内容 | ① 已知魔数反推键 → ② 字符似然模型 → ③ 定值复元表 |
| **S4 结构** | 认脚本容器与记录格式 | **先认记录形状（`02-record-patterns.md` P1〜P8）**；「记录驱动扫描」自定界 ⇒ 永不失步 |
| **S5 解码** | 码表 / 替换槽 / 宏 | 假名块先定；**替换槽不信 cp932** |
| **S6 成行** | 按 §0 落地 | 续写形态**全集**都要覆盖 |
| **S7 自检+报告** | §1 自检 ＋ **闭合校验** ＋ 写报告 | 报告必须含**重跑步骤**；**串数/字节闭合**（`05-completeness`）对不上 ⇒ 先查漏，不写「已全部提取」 |
| **S8 收尾** | **§5 固定动作（自动，不等用户说）** | `memcheck.py` ＋ 落记忆 |

> **★ 上下文卫生**：完整 7 条见 `references/05` §6。① 探查一律 `scripts/probe.py`（**≤80 行**），**永不**整文件 xxd／整表 dump；② 只读「这一步」需要的；③ 长会话卸到 `_work_<game>/NOTES.md`；④ `Grep`＋抽样；⑤ **`.md >10 KB` 主动拆**。

## 3. 动手前先查的坑

> 完整坑列表在 `references/pitfalls/`（按层分册，编号 ①〜ⓨ / A1–A19 / B1–B31 原样保留）；**导航见 `references/00-index.md`**。
> 本节只留最容易翻车的 12 条，**开工必看**；其余按阶段读对应分册。
> ⚠ **下判据前先扫 `02-false-signals.md`**（汉字尾字节撞指令码 / 「读得通」≠字对 / 图集顺序≠码序 …24 条反例）。

**解码层**（`references/pitfalls/A1-decode-core.md`、`A2-decode-late.md`）
1. 主循环**字符宽度感知** —— 否则汉字尾字节撞指令码，静默丢 20%+ 文本
2. 替换槽 / gaiji **不能信 cp932**；PUA 槽＝被改画的标点；以 ELF `code→Unicode` 表为准
3. 变量表要**先锁定人名映射**
4. eboot 串表常含**同发行商他作遗留串** → 核对后整体排除
5. PSV 是**两层**：`pkg2zip` 只解容器，再 `psvpfsparser` 解 PFS；`zRIF` ≠ 可用，看 `header signature is valid`
6. 归档**块单位不是常量** —— 用 `max(offset)×UNIT ≈ 文件大小` 反推
7. 同引擎 opcode 可能**逐文件平移**（STCM2L：Δ=0x10 倍数，builtin 不动）
8. 自建码表：**用一条已知明文锚定基址**（禁穷举、禁 OCR，见 §0 ①②）

**提取层**（`references/pitfalls/B1-lines.md` 起）
9. **一次点击 = 一行**；续写形态要覆盖全集；安全写法＝「默认新框，只在看到追加码才合并」
10. 互斥分支＝同一点击的多版本正文 ⇒ 同段取一；共通导入块逐文件重复 ⇒ 只留一次
11. 大字号演出会把话者名写进正文流 ⇒ 裸名札行（`^【…】$`）剔除

**交付层**（`references/pitfalls/C1-deliver.md`、`C2-deliver-2.md`）
12. 主角名宏被当空码丢 · 选项被当标签丢 · 说话人残留 4 形态 · 系统/UI 混入

## 4. 深入资料导航

> **只需按「当前在做哪一步」查一行**；未用到的不要打开。

| 当前在做 | 读这些（均在 `references/`） |
|---|---|
| **开工：这是什么东西** | **`00-triage.md`（判型四表＋四步攻坚）** |
| **开工：全部坑一览** | `00-index.md`（总导航）→ `references/pitfalls/A1-decode-core.md` |
| 解密 / 解压 / 化け / 官方补丁 | `01-decrypt.md` |
| PSV PFS 两类失败 / PUA 字形槽 | `01-psv-pfs.md` |
| PSP `~PSP` EBOOT / `BOOT.BIN` / ELF 反汇编 | `01-psp-eboot.md` |
| Switch NCA（BKTR 增量 / 全量压缩） | `01-switch-nca.md` |
| CHD v5 → ISO | `01-image-chd.md` |
| 认脚本结构（消息 / 宏 / 分支 / 点击语义） | `02-structure.md` |
| STCM2L 专项 / 定序 | `02-stcm2l.md` |
| **认文本记录形状（未知字节码）** | `02-record-patterns.md`（P1〜P8） |
| **判据可信度（反例清单）** | `02-false-signals.md` |
| 解码 · 通用（宽度 / 替换槽 / 名字判别） | `03-basics.md` |
| ELF `code→Unicode` 码表 / 分区错位 | `03-codetable-elf.md` |
| 归档 / 定长表 案例 | `03-archive.md` ＋ `03-archive-family.md` |
| WSC `rotl_8` / 脚本前缀区 | `03-wsc-ops.md` |
| 归档块单位 / opcode Δ / 链式自校验 | `03-archive-delta.md` |
| 判型 · 定框（记录类型 / 一次点击边界） | `04-typing.md` |
| 成行 · 通用规则 | `04-lines.md` |
| 成行 · 各引擎案例 | `04-lines-cases.md` |
| 名札边界 / 记录框语义 | `04-lines-names.md` |
| 话者名自举 / 槽拆分与回声 | `04-lines-echo.md` |
| 互斥备选 / 整段折叠 / 选项数据区 | `04-lines-options.md` |
| 自建位图字体 / 名字宏 / 交付改名 | `03-selffont.md` ＋ `03-names-macro.md` |
| Unity(IL2CPP) / Naninovel / Switch 同捆更新 | `02-unity.md` |
| Unity 自研 `.bytes`（KONAMI ADV） | `02-unity-bytes.md` ＋ `02-unity-bytes-works.md` |
| 交付层 / 流程层的坑（C1〜C8、D1〜D10） | `05-deliver-pitfalls.md` |
| 自检 / 外部核对 / 完整性审计 | `05-selfcheck.md` ＋ `05-external-report.md` ＋ `05-completeness.md` |
| 工作区 / 记忆 / 上下文卫生 / 决策纪律 | `06-workspace.md` ＋ `06-discipline.md` |
| **某引擎细则** | `engines.md`（路由表）→ 只读命中的 `engines/<slug>.md` |

自检脚本：`scripts/check_text.py`（项目内同版 `scripts/check_text.py`）。

## 5. 收尾（每作交付后自动跑，不等用户提醒）

```bash
python scripts/wrapup.py --report "提取结果/解析报告/XX_解析报告.md" \
                         --text "提取结果/XX_全文本.txt" --name <主角名>
```

一条命令跑完 **品检 → 体积 → 沉淀草案 → 落位片段**，只输出一张待办清单；`--apply` 幂等追加 WORKS/TOOLS。
**拆分纪律（硬）**：只按语义边界切、禁「写完再 glob 删旧」、拆完立刻改引用 —— 详见 `references/05-wrapup.md`。

> 各引擎格式细则见`references/`：`engines.md`（**路由表**）→ 只读命中的 `engines/<slug>.md`。

> **后期条目（ⓒ〜ⓩ 等）已按层归入 `references/pitfalls/B4`〜`B9`、`E1`、`E2`**；不再在本文件追加变更记录。
