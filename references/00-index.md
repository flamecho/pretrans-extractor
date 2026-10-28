# 导航

> **别按册名找，按症状找**：先看 §1 的「症状 → 去哪」，命中就直接读那一册；没命中的再按 §3 的阶段表走。

## 1. 症状 → 去哪（最快入口）

| 你遇到的现象 | 读这一册 |
|---|---|
| 解出来是乱码 / 半角假名 / 片平混排 | `S2-decrypt.md` → `pitfalls/B-encoding-lines.md`（半角假名语义方向） |
| 汉字少了、字数比预期低两三成 | `pitfalls/A-decode.md` ①（主循环字符宽度） |
| 文本找到了，但断行碎成一片 | **`S6-lines-proof.md`**（先定档 L0/L1/L2）→ `pitfalls/B-lines.md` |
| 一页该出两版（段行＋合并行）吗 | **`S6-lines-dual.md`**（三步判定；禁统计判据） |
| 一行里塞了两个框 / 引号括号失衡 | **`S6-line-integrity.md`**（四探针→A·B·C·D）→ 修补见 `S6-line-repair.md` |
| 说话人、名札、作者注记混进正文 | **`S7-name-plate.md`**（形态判据）→ `S6-lines-names.md`（留还是剥）→ `pitfalls/B-name-tag-edges.md` → `pitfalls/B-name-note.md`（这段到底算备注还是正文） |
| 主角名 / 变量 / 占位没解出来 | **`S7-charset-ledger.md`**（改名槽形态表＋四步取证） |
| 品检报「字符未备案」 | `S7-charset-ledger.md` §1（台账 whitelist）＋ `scripts/charset_audit.py` |
| 选项少了 / 重复 / 判成名札 | `S6-lines-options.md` → `pitfalls/B-lines.md` |
| 脚本记录认不出形状 | **`S4-record-patterns.md`**（P1〜P8）→ `pitfalls/B-script-structure.md` |
| 同族续作照搬前作就错 | `S4-false-signals.md`（27 条反例）＋ `pitfalls/B-script-structure.md` |
| 解包报错 / 卡在某一步 | `S2-switch-nca.md`（后半册＝卡点排查）· `S2-psv-pfs.md` · `S2-psp-eboot.md` |
| 归档块错位、解压长度不对 | `S3-archive.md` · `S3-archive-family.md` · `S3-archive-delta.md` |
| 交付格式 / 文件名 / 收哪些 | **`SKILL.md` §0** ＋ `S7-deliver-pitfalls.md` |
| 报告要写什么 | `S7-external-report.md`（front-matter ＋ 三行判据） |
| 收尾（品检 / 沉淀 / 落位） | **`S8-wrapup.md`**（一条命令） |

## 2. 开工速查：最易翻车的 14 条

> ⚠ **下判据前先扫 `S4-false-signals.md`**（汉字尾字节撞指令码 / 「读得通」≠字对 / 图集顺序≠码序 …27 条反例）。

**解码层**（`references/pitfalls/A-decode.md`）
1. 主循环**字符宽度感知** —— 否则汉字尾字节撞指令码，静默丢 20%+ 文本
2. **半角假名转全角前先判语义方向**：该作是「平假名语义」还是「片假名语义」——
   判据＝找一条同句里已是全角平假名的假名（如 `が`），若与半角部分并存 ⇒ 平假名语义。
   映射反了会出「片平混排」（うみねこ 98% 行受影响）；`･`/`､`/`｡` 这类半角标点要单独实测，
   不能按 cp932 字面映射（`･`→`・` 可能应为 `…`）。详见 `pitfalls/B-encoding-lines.md`
3. 替换槽 / gaiji **不能信 cp932**；PUA 槽＝被改画的标点；以 ELF `code→Unicode` 表为准
4. 变量表要**先锁定人名映射**
5. eboot 串表常含**同发行商他作遗留串** → 核对后整体排除
6. PSV 是**两层**：`pkg2zip` 只解容器，再 `psvpfsparser` 解 PFS；`zRIF` ≠ 可用，看 `header signature is valid`
7. 归档**块单位不是常量** —— 用 `max(offset)×UNIT ≈ 文件大小` 反推
8. 同引擎 opcode 可能**逐文件平移**（STCM2L：Δ=0x10 倍数，builtin 不动）
9. 自建码表：**用一条已知明文锚定基址**（禁穷举、禁 OCR，见 SKILL.md §0 ①②）

**提取层**（`references/pitfalls/B-lines.md` 起）
10. **一次点击 = 一行**；**断框必须代码级**（L0 字节码/标记/引擎配置、L1 记录自定界＋交叉验证）——
   **空行/字数/句末标点/引号配对/相似度/语感禁止当主判据**（L2 只能当探针）；续写形态覆盖全集；
   安全写法＝「默认新框，只在看到追加码才合并」；**换作必回查**（`S6-lines-proof.md`）
11. 互斥分支＝同一点击的多版本正文 ⇒ 同段取一；共通导入块逐文件重复 ⇒ 只留一次
12. 大字号演出会把话者名写进正文流 ⇒ 裸名札行（`^【…】$`）剔除

**交付层**（`references/pitfalls/C-deliver.md`）
13. 主角名宏被当空码丢 · 选项被当标签丢 · 说话人残留 4 形态 · 系统/UI 混入
14. **同框第二段文本可能挂别的 op**（`FF8F` 型）⇒ 只认 2 个文本 op 会静默截断整句，**探针＝引号配对数**；选项装饰分两层（首字形图标＋单独成框的框线）（`pitfalls/B-multi-text-op.md`）

> 每条只给判据；完整条目在 `pitfalls/`。先按 §1 查症状，再回这里对号。

## 3. 两条路径

| 情形 | 做法 | 目标 |
|---|---|---|
| **命中已知引擎** | `S0-triage.md` 的表 → 只读命中的 `engines/<slug>.md` → 复用 `../scripts/INDEX-BY-ENGINE.md` 里该引擎的脚本 | 同族续作快速出文本 |
| **未命中** | `S0-triage.md` §E 四步攻坚 → `S4-record-patterns.md` 认形状 → `S6-*` 成行 → `S7-*` 自检 | 慢但可收敛 |

## 3.5 文件名前缀＝阶段号

`references/` 下每本册子的前缀**就是**下一节的 S 号：**`S6-` 一定是成行阶段才用的判据**，`S0-`〜`S8-` 依次是判型→取得→容器→归档→脚本→解码→成行→交付→收尾；**`00-`** 是横切层（导航 / 输出规范 / 决策纪律 / 工作区约定），随时可查。
同一阶段内有多本时按主题挑（见下一节），**不按字母序从头读**。

## 4. 阶段 → 文件

| 阶段 | 做什么 | 读这些 |
|---|---|---|
| **S0 判型** | 平台 / 容器 / 引擎 | **`S0-triage.md`** |
| **S1 取得** | 母本、压缩包、镜像、**DLC 全扫** | `S1-image-chd.md`（CHD/NSZ）· **DLC 全扫见 `SKILL.md` §0** |
| **S2 容器** | PSV / PSP / Switch / 解密总纲 | `S2-psv-pfs.md` · `S2-psp-eboot.md` · **`S2-switch-nca.md`** · `S2-decrypt.md` |
| **S3 解压 / 归档** | 归档结构、块单位、Δ、自校验 | `S3-archive.md` · `S3-archive-family.md` · `S3-archive-delta.md` · `S3-wsc-ops.md` |
| **S4 脚本** | 脚本结构、记录形状、反例、STCM2L | `S4-structure.md` · **`S4-record-patterns.md`** · **`S4-false-signals.md`** · `S4-stcm2l.md`（形态）· `S4-stcm2l-cases.md`（案例） |
| **S4' Unity** | IL2CPP / Naninovel / `.bytes` | `S4-unity.md` · `S4-unity-bytes.md` · `S4-unity-bytes-works.md` |
| **S5 解码** | 宽度、码表、字体槽、名字宏 | `S5-basics.md` · `S5-codetable-elf.md` · `S5-selffont.md` · `S5-names-macro.md` |
| **S6 成行** | 一次点击＝一行、定框、双版、名札、选项 | **`S6-lines-proof.md`（先定档）** ＋ **`S6-lines-dual.md`（双版）** · `S6-lines.md` · `S6-typing.md` · `S6-lines-names.md` · `S6-lines-options.md` · `S6-lines-echo.md` · `S6-lines-cases.md` |
| **S6 之后 · 行完整性** | 一行塞了几个框、怎么修 | **`S6-line-integrity.md`**（判定）→ **`S6-line-repair.md`**（修补案例） |
| **S7 交付** | 自检、字符台账、外部核对、完整性、报告 | **`00-rules.md`（交付形态与判据档次全文）** · **`S7-charset-ledger.md`** · **`S7-name-plate.md`** · `S7-selfcheck.md` · `S7-external-report.md` · `S7-completeness.md` · `S7-deliver-pitfalls.md` |
| **S8 收尾** | 一条命令跑完品检 / 对账 / 沉淀 / 落位 | **`S8-wrapup.md`** · `00-workspace.md` · `00-discipline.md` |

## 5. 坑册（按层：A 解码 / B 提取 / C 交付 / E 专册）

| 册 | 层 | 收什么 |
|---|---|---|
| `pitfalls/A-decode.md` | 解码 | **六组**：先判要不要解密 / 编码与码表 / 变量与元数据 / 容器与归档 / 脚本结构 / Unity 特例 |
| `pitfalls/B-lines.md` | 提取 | **成行主册**，五组：断框与拼装 / 去重与折叠 / 名札·宏·注记 / 选项 / 过滤与清洗 |
| `pitfalls/B-tags-resume.md` | 提取 | 标签脚本解析（正则须容忍属性值里的 `>`）、续行硬边界、「点击 vs 段」两个层级、`.TAT`/`<TAG>` DSL 引擎的点击探针＋闭合审计 |
| `pitfalls/B-script-structure.md` | 结构 | **脚本判型与记录结构**，五组：判哪个引擎 / 记录怎么切（含尾随标记 `k×cmd`、非线形作取序）/ 文本槽与拼装 / 选项 / 排除与清洗 |
| `pitfalls/B-encoding-lines.md` | 编码/成行 | **编码与成行细节**，四组：文本在哪 / 编码与化け / 串与池 / 成行与定框 |
| `pitfalls/B-name-note.md` | 提取 | **名札与备注的边界**：「长得像备注」≠ 备注（判据是标记不是形态）、长句注记、单框两名札＝改稿残留 |
| `pitfalls/B-name-tag-edges.md` | 提取 | 名札剥离边界，**三组**：名札形态（后接符 / 带句号 / PUA 填充 / 地の文内联）/ 判定实现与验收（空串陷阱、验收探针）/ 选项侧（禁过裸名过滤、定长选择肢表） |
| `pitfalls/B-tag-scanner.md` | 结构 | 标签扫描三个静默漏洞（`L==len+1` / off-by-one / 剧本·系统分装） |
| `pitfalls/B-multi-text-op.md` | 提取 | 同框第二段挂别的 op、选项装饰两层、「基础码必属基础区」不成立 |
| `pitfalls/B-halfwidth-ruby-dual.md` | 交付 | 半角假名≠化け、ruby 剥除、局部双版 `--dual` 优先 |
| `pitfalls/C-deliver.md` | 交付 | **交付与自检**，四组：排除 / 版式与标点 / 多版本·定长表 / 交付前自检动作 |
| `pitfalls/E-m2-psb.md` | 专册 | M2 ADVENGINE / PSB·PGD，**三组**：容器解密与键获取（MDF 壳 / PGD 容器 / CMAC pad / seed 名 / EBOOT）/ 场景表·选项·收文范围 / 成行·标签·品检 |
| `pitfalls/E-cri-kag.md` | 专册 | CRI CPK 块流 / CRILAYLA / KAG `.ks` |

> **`★` 是什么**：册内条目按踩坑代价标了星 —— `★` 值得先读，`★★` 最容易踩（踩了要返工）。
> 它是**册内相对**标记，跨册不可比。
>
> 找不到对应条目时：`Grep "<症状关键词>" pitfalls/`，别从头读。

## 6. 引擎知识

| 入口 | 用法 |
|---|---|
| 工作区 `engines.md` | **路由表**：一句话索引 ＋「详见」列（`ENGINES-2` / `ENGINES-3` / `ENGINES-solo` 为续册） |
| `engines/<slug>.md`（工作区） | 单引擎全量（一引擎一文件）；**只读命中的那一个** |

## 7. 脚本

`../scripts/INDEX.md`（通用工具：判型 / 探查 / 品检 / 收尾 / 维护）。
按引擎找**可改的按作品提取器**：发行版看 `../scripts/INDEX-BY-ENGINE.md`（自动生成），工作版看 `TOOLS-works-<引擎族>.md`。
**反查**「这个 py 干什么 / 这个作品做过吗」⇒ `../scripts/INDEX-BY-SCRIPT.md`（585 个，字母序，`出自引擎册` 为 `—` 即该册没记它）。

| 阶段 | 脚本 |
|---|---|
| S0 判型 | `identify.py` |
| S2 探正文 | `probe.py` |
| **S6 之后 · 行完整性** | `struct_probe.py`（引号/括号 A·B·C·D）· `fix_wrap_pairs.py` · `fix_multi_brackets.py` · `merge_name_variants.py` · `dup_probe.py` |
| S7 品检 | `check_text.py`（台账 whitelist ＋ 版式自判）· `charset_audit.py` · `selftest.py`（改判据前后跑） |
| S8 收尾 | **`wrapup.py`**（编排）→ `distill.py` / `archive_work.py` / `memcheck.py`（只报 00-index.md 超 8 KB） |
| 手册维护 | `split_md.py`（按语义边界拆）· `lint_docs.py`（断链 / 孤儿 / 排版对账）· `pending.py` |
