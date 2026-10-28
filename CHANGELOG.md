# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 与 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [1.4.0] - 2026-10-28

**手册按「阶段」重组为 44 本分册，工具链补齐到 19 个通用工具**。判型到收尾一阶段一册，册内编号统一，坑册按主题分组；每条判据都经过变异验证。

### 结构：44 本册，前缀＝阶段号

前缀不是分组习惯，而是**流水线上的位置**：

| 前缀 | 本数 | 收什么 |
|---|---|---|
| `00-` | 4 | **横切层**（不属任何单个阶段）：导航、输出规范、决策纪律、工作区约定 |
| `S0-` | 1 | 判型 |
| `S1-` | 1 | 取得（母本 / 镜像 / CHD） |
| `S2-` | 4 | 容器与解密（解密总纲 / PFS / EBOOT / NCA） |
| `S3-` | 4 | 解压归档（归档族 / 块增量 / opcode Δ / WSC） |
| `S4-` | 8 | 脚本（结构 / 记录形态库 / 反例 / STCM2L / Unity） |
| `S5-` | 4 | 解码（字符宽度 / 码表 / 字体 / 名字宏） |
| `S6-` | 10 | 成行（切行证明 / 双版 / 名札 / 选项 / 回声 / 定框 / 行完整性） |
| `S7-` | 6 | 交付（自检 / 外部核对 / 完整性 / 台账 / 名札剥离 / 交付层坑） |
| `S8-` | 1 | 收尾（一条命令跑完品检 / 对账 / 沉淀 / 落位） |

命名示例：`S2-decrypt.md` / `S4-structure.md` / `S6-lines-proof.md` / `S7-selfcheck.md`。

- **坑册 13 册**（`pitfalls/`）：`A-` 解码 / `B-` 提取 / `C-` 交付 / `E-` 专册，共 167 条；
  册内统一 `## N.` = 组、`### N.M` = 条目（条目少的册单层），13 册编号全部连续。
- **引擎 102 本**（`references/engines/`）：命名规则 `<厂商或引擎>-<平台或变体>.md` ——
  平台级通识用 `platform-`（`platform-psv-pfs` / `platform-switch-nca`），厂商族用 `hunex-` / `takuyo-` /
  `koei-` / `cri-` / `d3p-`，引擎名本身即唯一标识的不加前缀（`malie` / `siglus` / `lte`）。
  入口是四张路由表（`engines.md` ＋ `engines-2/3/solo.md`）。

### 编号：一种记号，只在一个地方用

| 用在哪 | 长什么样 |
|---|---|
| 文件名 | `S4-structure.md` · `pitfalls/B-lines.md`（前缀＝阶段号或层） |
| 册内小节 | `## 3.` 组、`### 3.2` 条目，一律从 1 起连续 |
| 跨册引用 | **一律带文件名**：`S6-lines-proof.md` §3 —— 裸 `§N` 只在本册内用 |

一批历史记号在本版清除：

- **批次前缀**（`W1_` / `P3_` / `UPD1_` / `D_`）—— 编号对读者零信息量；
- **旧条目号**（`A14` / `B22` 这套跨册共享的编号）—— 正文标注、册头提示、索引册、
  构建期生成器与对应 lint 检查项**全部移除**；以后要指某个坑，写「哪一册 §几」；
- **圈码 `①②③`** —— 不能当锚点（Markdown 只给 `#` 生成 id），也不能被 `§N` 引用。

### 判据与体检

`lint_docs.py` 现在查八项，每一项都配了**变异验证**（注入反例、确认报得出、再复原）：

| 项 | 查什么 |
|---|---|
| A 断链 | 文档里点名的 `.md` 是否真在包里（发行版连 `engines/` 一起严格校验） |
| B 路由缺 | 引擎册写了却没进路由表 —— 「有册子但没人知道去哪找」 |
| C 孤儿册 | 没有任何文件引用的册 —— 下次永远读不到 |
| D 空册 | < 200 B，多为写坏的占位 |
| F 编号连续 | `## N.` 从 1 连续、`### N.M` 组内连续且父组存在 |
| G 排版 | 围栏配对 / 表格列数 / 块前空行 / 行尾空格 / 编号标题 >100 字 |
| H §N 引用 | 带文件名的查目标册有没有该节；裸 `§N` 查本册；小数节号（`§1.5`）一并支持 |
| J 命令可跑 | `python scripts/X.py --flag` 里的脚本与参数是否真存在 |

构建期另有一组闸：`py` 语法、代码围栏配对、反引号奇偶、路径与密钥泄漏、行尾 LF、
死 `.py` 指针、死 `.md` 指针、多余文件（`--no-clean` 下写出过的临时物）。

### 工具链

- **19 个通用工具** `-h` 全通，`INDEX.md` 按阶段重排（`identify` / `probe` / `struct_probe` /
  `dup_probe` / `fix_wrap_pairs` / `fix_multi_brackets` / `merge_name_variants` / `charset_audit` /
  `check_text` / `init_all_charset` / `recheck_all` / `wrapup` / `distill` / `archive_work` /
  `memcheck` / `split_md` / `lint_docs` / `pending` / `selftest`）。
- `wrapup.py` 把收尾串成一条：品检 → 手册对账 → 沉淀草案 → 落位片段，最后只输出一张待办清单。
- **72 个「跑得出中间物、但产不出成品」的探针脚本归档**，不进发行包；`scripts/` 只留能复用的提取器
  （585 个 `*_extract.py` ＋ 通用容器工具）。
- 构建顺序修正：`skill/scripts` 为**权威源**，`tools/` 后写会静默覆盖修改（这一条曾让 dist 一直是旧版）。
- 清掉 `recheck_all.py` 的调试残留（硬编码 `makedirs('_recheck')` 并写文件，还会被打进发行包）。

### 文档门面

- `README.md` 重写：简介 → 用途与边界 → 快速开始 → 整理流程 → 输出规范 → 支持范围 → 目录结构 →
  环境变量 → 兼容性 → 隐私与安全 → 文档索引。
- `CHANGELOG.md` 只描述「这一版是什么」，不写「上一版怎么改的」。
- 手册里不再出现沿革：`〔原 X〕`、册头「本册独立编号（原为第 X 节…）」、「已下沉至 / 已移入」、
  「上一版…本版…」合计 **152 处**全部删除，改写成**陈述现状**或**反例**。

### 验收

```
dist 773 文件 ｜ build 校验 0（598 py 语法全通过）｜ 19 个工具 -h 全通
手册 164 文件 lint 全 0 ｜ selftest 28/28
pitfalls 13 册 167 条、编号全连续 ｜ 旧条目号 / 批次前缀 / 圈码：0 处残留
```

## [1.3.3] - 2026-10-18

**索引的可查性**。上一版做出了「引擎 → 脚本」表，但还有三个引擎册根本不在表里，
另有 21 个脚本在表里只显示一个「—」。

### 修正

- **`INDEX-BY-ENGINE.md` 的「按引擎」表覆盖全部 78 册**：没有现成脚本的册不再整行消失，
  改为明写「—（无现成脚本：按本册的容器链路 / 记录形状自己写）」。
  此前 `otomate-vm` / `psv-pfs` / `zerodiv-talks-variant` 三册查不到行，读者会以为索引漏了。
- **`zerodiv-talks-variant` 补「## 工具」节**：包里本就有 `vn_zerodiv_extract.py`，册里没写引用。
- **`corda_2fa_get.py` 的用法名写错**：docstring 里是 `corda2f_get.py`（少个下划线），
  这句会被抓进索引的「用途」列，照抄就报找不到文件。

### 变更

- **21 个脚本补模块 docstring**（`cdar` / `scan_jp` / `unity_scan` / `sjis_scan` / `pe_dis` /
  `vn_memdump` 等）：此前索引对它们只能显示「—」，读者得读代码猜用途。现索引 250 个脚本**全部有用途**。
- **README 正文跟上口径**：简介点明「239 个按作品提取器 + `INDEX-BY-ENGINE.md`」，
  并写出最快的三步（判型 → 引擎册看链路 → 索引挑脚本）；支持范围改为
  「78 本单引擎分册（约 30 个引擎族）」；文档表补索引一行。此前正文还停在 v1.3.0 的说法。
- `00-discipline.md` 增一条：**阶段册 ↔ 引擎册允许共享锚点事实，禁止单向改动**——
  同一技术句（NCA 块头、`hactool` 命令）两处各写一次是有意的（各自要能独立执行），
  实测最长连续重复仅 207 字，不必合并；但改一处须 `Grep` 另一处，否则两边会分叉。

## [1.3.2] - 2026-10-18

**发行版清理**。路径早已脱敏，但还有两类残留：一类让读者找不到东西，一类让页面渲染错位。

### 修正

- **脱敏正则吃掉行尾反引号（8 处）**：处理 `C:/Users/…` 与 `.workbuddy/memory/` 的两条规则，
  字符集没排除反引号，把紧跟在路径后的那个反引号一并吃掉 ⇒ 行内代码只剩开头没有收尾，
  未闭合的 code span 会把后文整段吞进代码块（`05-deliver-pitfalls`、`06-workspace` 等 8 处）。
- **引擎册抬头 26 本**写着「主索引见 `../MEMORY.md`」——包里没有这个文件，改指 `../00-index.md`。
- **`00-workspace.md` §5** 整节讲的是记忆层（MEMORY.md / CONVENTIONS.md / WORKS.md / TOOLS.md），
  这些文件不随包发布 ⇒ 该段不进发行版；收尾命令、`.py` 写入注意、环境坑等仍保留。
- **正文反引号不配对 20 处**（源文件本就如此，与脱敏无关）：跨行的 inline code 合并为一行；
  表格里多余的孤立反引号、`0x5C` 转义后残留的反引号一并修正。

### 新增（构建期校验，防回退）

- `build_dist.py` 校验新增两项：**正文行反引号奇偶**（不配对即视为失败）、
  **`MEMORY.md` 残留扫描**（发行版必须为 0）。
- `--no-clean`：目标目录被占用（预览面板 / 资源管理器持有句柄）时 `rmtree` 与 `rename` 都会被拒，
  可跳过清空就地覆盖（仅在文件集不变时使用，事后核对文件数）。

## [1.3.1] - 2026-10-18

**让「命中已知引擎」这条快速路径真的走得通**。上一版把 240+ 个按作品提取器随包附带，
却没有告诉使用者「这个引擎该改哪个脚本」——`INDEX.md` 只有 10 个通用工具，
而其抬头还写着「专用提取器不随 skill 发布」（与事实相反）。

### 新增

- **`scripts/INDEX-BY-ENGINE.md`** —— **引擎 → 可复用脚本**索引，构建时自动生成、不手改：
  - **一、按引擎**：75 个引擎册 → 各自可直接改的 174 个脚本（命中引擎后从这一行开始）；
  - **二、按脚本**：脚本 → 一句话用途（取模块 docstring）→ 出自哪本引擎册；
  - **三、未被任何引擎册引用**的 65 个（薄壳 / 一次性脚本 / 漏记），附用途，避免凭文件名猜。
- **`scripts/selftest.py`** —— 品检判据的**回归测试**：21 个微型样本，覆盖
  BOM / CR / 半角假名 / 半角标点 / PUA / `U+FFFD` / `〓` / 控制符 / 引号配对 / 行首孤立标点 /
  颜文字单侧括号 / 名札三形态 / 字段标签放行 / 句号缺失 / 插入宏 / 主角名出现性。
  **改动 `check_text.py` 前后各跑一次**（退出码 0 = 21/21）。

### 变更

- `S0-triage.md` / `00-index.md` 的「按引擎查脚本」改指 `INDEX-BY-ENGINE.md`
  （原文指向的 `INDEX.md` 里并没有按引擎分类的内容）。
- `scripts/INDEX.md`：更正过期声明，补入 `selftest.py`（10 → 11 个通用工具）。
- `lint_docs.py`：`engines/` 与 `engines-N.md` 属**构建期注入**（仅发行版存在），
  工作版不再把它们计入断链，输出增加「注入跳过」计数。
  此前工作版常驻 30+ 条噪声，真断链会被淹掉。
- `S8-wrapup.md`：维护命令一节补「改了品检判据先跑回归」及正确顺序（先加样本、再改判据）。

## [1.3.0] - 2026-10-18

**知识库按流程阶段重构 + 收尾工具链**。把「按体积硬切的坑索引／引擎文件」改成**按阶段、按引擎**的语义分册，
并把提取后的整理工作（品检 / 沉淀 / 落位 / 拆分）做成**可校验的工具**。

### 新增

- **4 个工具**（`scripts/`）：
  - `wrapup.py` —— **一条命令跑完收尾**：品检 → 行数一致性 → 体积 → 沉淀草案 → 落位片段，只输出一张待办清单；
  - `distill.py` —— 报告 → **沉淀草案**：按 4-gram 包含度查重，分「已覆盖 / 待沉淀 / 单作特例」并给建议落位；
  - `archive_work.py` —— 报告 → **四处落位片段**（作品索引 / 工具索引 / 日志小节 / 引擎提示），`--apply` 幂等追加；
  - `split_md.py` —— **按语义边界拆 md**（标题 / 编号条目），带正文行守恒校验与原子替换。
  - `lint_docs.py` —— **手册对账**：断链 / 引擎册未进路由表 / 孤儿册 / 空册 / 超限 / 坑册编号重复。
  - `pending.py` —— **未落位检测**：有成品无报告 / 有报告未进索引 / 未落位且无报告头。
- **`references/S8-wrapup.md`** —— 收尾流程与**三条拆分硬规矩**（禁按字节切 / 禁「写完再 glob 删旧」/ 拆完立刻改引用）。
- **报告头 front-matter 规范**（`S7-external-report.md` §4.1）：`作品 / 平台 / 引擎 / 主角 / 行数 / 日期`。
  有它索引字段零歧义；没有则正则兜底并标注「请核对」。

### 变更

- **`references/` 按流程阶段重排**：`00-triage`（判型）→ `01-*`（取得/容器）→ `02-*`（脚本/记录形状/反例）→
  `03-*`（解码）→ `04-*`（成行）→ `05-*`（交付）→ `06-*`（流程）；坑索引归入 `pitfalls/` 15 册（A 解码 / B 提取 / C 交付 / E 专册）。
- 新增 `S0-triage.md`（平台 → 容器 → 脚本 → 厂商 → 四步攻坚）与 `S4-record-patterns.md`（文本记录形态 P1–P8）、
  `S4-false-signals.md`（24 条「看着像判据其实会骗」的反例）。
- `memcheck.py`：超限时直接给出 `split_md.py` 命令，并对 ≥96% 上限的册**提前预警**；`--fix` 直接试算切点（不落盘）。
- `distill.py` 的落位建议增加**并行坑册**（阶段册讲怎么做、坑册讲别踩什么）。
- 引擎知识改为在 `references/engines/` 一引擎一文件（原 `references/engines.md` 保留为路由表）。

### 本版不含 / 已修正

- **移除随包的第三方 C# 源码**（`scripts/koei/`）：那是 Kuriimu2 的 `plugin_ruby_party` 插件代码，
  与本仓库许可证不同，不应随包分发；CDAR 结构参考改由 [`references/third-party.md`](references/third-party.md) 指向上游。
- **移除随包的第三方 HuneX 工具**（`scripts/hunex/`）：其源码标注 *FOR INTERNAL USE ONLY* 且版权属他人，
  不宜随 MIT 分发；MZX0 等解包改由 [`references/third-party.md`](references/third-party.md) 指向原项目。
- **正文不收录授权串**：引擎册中的 zRIF 一律以 `<zRIF>` 占位，需自备。
- **清除机器相关路径**：解释器路径、venv 路径、游戏开发机路径统一改为 `<你的 Python 3.10+>` / `<venv>` / `<開発機>` 等占位；
  `提取结果/`、`_work_*` 等属**工作区约定**，保留但在 `00-workspace.md` 顶部注明「一种可选布局」。
- **工具不依赖安装目录名**：`distill.py` / `lint_docs.py` / `memcheck.py` 默认取
  「脚本所在目录的上一级」，装成任何名字、放在任何路径都能跑。
- **路由续册一并发布**：`engines-2.md` / `engines-3.md` / `engines-solo.md`；
  在干净目录解压后 `lint_docs.py` 为 0 断链 / 0 路由缺失 / 0 孤儿册。
- **文档改成面向使用者**：删去内部的拆分/搬迁沿革（「XX 拆出」「本册超 10 KB」）与旧编号（`03h`/`04a` 等），
  交叉引用一律写成文件名；目录树、报告模板、脚本索引都按「你拿到这个包怎么用」重写。
- **补齐按作品编写的提取器**：`scripts/` 现含 239 个（原只随包 116 个），引擎册里提到的脚本不再指向空文件。
- **修正大小写与失效指针**：`ENGINES.md`（实际文件名 `engines.md`）等 83 处大小写在 Linux/macOS 上会失败；
  指向「记忆层内部文件」（不随包发布）的 34 处引用改为指向包内文件。

### 已知限制

- 报告的**主角字段**若未写 front-matter，正则抽取约 71%（会标注「请核对」）；写头则 100%。
- `distill.py` 的落位建议目前只覆盖 `references/` 阶段册，尚未覆盖 `pitfalls/*`。

## [1.2.0] - 2026-10-10

**知识库分层 + 决策纪律版**。把「一个巨型坑文件 + 一个巨型引擎文件」改成**按阶段 / 按引擎拆分**，
并新增三条最高优先级的作业纪律与两个流程步。

### 新增

- **三条最高优先级纪律**（`SKILL.md` §0）：① 禁止穷举 ② 禁止 OCR ③ 禁止无规划试错
  （动手前先立假设 + 证伪条件；同一假设 2 次探查无新信息即换路；单点 >3 次未收敛即汇报）。
- **流程新增两步**：**S0 识别**（`scripts/identify.py`：一次调用给出「引擎 + 建议命令 + 该读哪份引擎分册」）
  与 **S8 收尾**（每作交付后自动跑 `memcheck.py` + 落记忆，不等用户提醒）。
- **上下文卫生纪律**（`SKILL.md` §2 / `references/05` §6）：探查限量 ≤80 行、只读「这一步」需要的、不预读、大文件主动拆。
- **新脚本**：`identify.py`（容器→引擎识别）、`probe.py`（限量探查）、`memcheck.py`（体积体检）。
- **新增提取器**：`believer_extract.py`（HuneX HESL/HESE）、`advhd.py` + `blip/bgloss/brouge_extract.py`
  （WillPlus AdvHD `.wsc`）、`libp_malievita.py` / `mysteria_extract.py` / `mysteria_text.py`（Malie Vita）、
  `rom2_extract.py` / `torimari_extract.py`（ROM2·SNR）、`norn9_extract.py` / `pandora_extract.py`（STCM2L 平台变体）、
  `gensou_decode.py` / `gensou_extract.py` / `gensou_scan.py`、`haruka5_extract.py` / `kazahanaki_extract.py`、
  `shinoda_botan_extract.py`、`vn_memdump.py` 等。
- **新增坑条目**：A14（WSC `rotl_8` / 选项目标指令须按表分派）、A15（脚本 magic 之前的前缀区块另含正文）、
  A16（归档块单位需反推，取错＝整体错位）、A17（opcode 逐文件平移）、A18（同族指令头布局随平台变）、
  A9（自建码表用一条已知明文锚定基址）、B7（互斥分支＝同一点击多版本正文）、B8（共通导入块去重）、
  C8（辞典载体可能是同发行商他作遗留串）。

### 变更

- `SKILL.md` 重写：明确「开工只读本文件；§3 索引已覆盖全部坑，细节按阶段读」。
- `references/03-pitfalls.md` → 拆为 **`03a-decode-basics` / `03b-decode-archive` / `03c-decode-wsc-ops` /
  `03d-extract-lines` / `03e-deliver-flow`** 五个按阶段分册。
- `references/engines.md` → 改为**路由表**（一句话索引 + 「详见」列），引擎细节拆到
  **`references/engines/<slug>.md`**（一引擎一文件，18 册，各 ≤10 KB）。

## [1.1.0] - 2026-10-07

**结构重构版**：主文件改为「必守规则 + 流程骨架 + 坑索引」，细节下沉到 `references/` 分册，避免加载时被截断。

### 新增

- `references/01-decrypt-decode.md` —— 解密 / 解压 / 化け（乱码）分类与修复 / 官方修正补丁。
- `references/02-script-reverse.md` —— 脚本结构逆向：字符宽度感知、消息格式、字符层、宏、分支回填、点击语义。
- `references/03-pitfalls.md` —— **全量坑 + 真实返工案例**（解码层 / 提取层 / 交付层 / 流程）。
- `references/04-verify-and-report.md` —— 自检、外部核对、验收清单、报告结构。
- `references/05-workspace-and-tools.md` —— 工作区布局、脚本形态、S1–S7 流程、环境要求。
- `scripts/check_text.py` —— 交付前通用品检：BOM / LF / `U+FFFD` / `〓` / 控制符、
  **半角假名**、**私用区 PUA**、**引号配对**、**说话人残留**、主角名出现性、空行 / 超长行 / 相邻重复行。
- 新增提取器：`xp3.py` / `chou_decrypt.py` / `chou_extract.py` / `chou_fix.py`（KiriKiri XP3 系）、
  `npa_nrbf.py`（Nitroplus NPA）、`lamento_extract.py`、`malie_extract.py`、
  `hanayoi_afs.py` / `hanayoi_extract.py` / `hanayoi_run.py`、`shinoda_botan_extract.py`、`vn_memdump.py`。
- `CHANGELOG.md`。

### 变更

- `SKILL.md` 精简为「输出规范 + 自检 + 流程骨架 + 坑索引 + 导航」；原细则移入 `references/`。
- 输出规范独立成 §0，明确「只收直接上屏的文本」「一次点击 = 一行」「不加说话人前缀」。
- `description` 收敛为 3 行。

### 移除

- `references/output-spec.md`、`references/workflow-checklist.md`
  —— 内容分别并入 `SKILL.md` §0 与 `references/04-verify-and-report.md`。

## [1.0.0] - 2026-10-06

首个公开版本：容器解包工具 + 各引擎提取器 + 输出规范 + 30+ 引擎复用要点。

- `SKILL.md` / `README.md` / `LICENSE`(MIT) / `.gitignore`
- `references/`：`engines.md`、`output-spec.md`、`workflow-checklist.md`、`third-party.md`
- `scripts/`：81 个提取/容器/探查脚本 + `INDEX.md` + `koei/` + `hunex/`
