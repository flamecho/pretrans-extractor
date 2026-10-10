## pretrans-extractor v1.2.0

**知识库分层 + 决策纪律版**。把「一个巨型坑文件 + 一个巨型引擎文件」改成按阶段 / 按引擎拆分，
并新增三条最高优先级的作业纪律与两个流程步。

### 新增

**三条最高优先级纪律**（`SKILL.md` §0）

- **禁止穷举** —— 破码表 / 猜键 / 修化け一律先结构化推理（魔数、已知明文反解、上下文、确定性表、参考实现）；
  仅在确认无其他方案时可枚举。
- **禁止 OCR** —— 不得用「渲染字形 + OCR / 模板匹配」解码；字形渲染只准人工目视单个字。
- **禁止无规划试错** —— 动手前先立假设 + 证伪条件；同一假设连续 2 次探查无新信息即换路；单点 >3 次未收敛即汇报。

**流程新增两步**

- **S0 识别** —— `python scripts/identify.py <文件或目录> [--deep]`：一次调用给出「引擎 + 建议命令 + 该读哪份引擎分册」。
- **S8 收尾** —— 每作交付后自动跑 `memcheck.py` + 落记忆，不等用户提醒。

**新脚本**

| 脚本 | 作用 |
|---|---|
| `scripts/identify.py` | 容器 → 引擎识别（输出建议命令与该读的引擎分册） |
| `scripts/probe.py` | 限量探查（≤80 行），替代 `xxd` 整文件 dump |
| `scripts/memcheck.py` | 体积体检（`.md > 10 KB` 提醒拆文件） |

**新增提取器（节选）**

- HuneX HESL/HESE —— `believer_extract.py`
- WillPlus / AdvHD `.wsc` —— `advhd.py`、`blip_extract.py`、`bgloss_extract.py`、`brouge_extract.py`
- Malie System (Vita) —— `libp_malievita.py`、`mysteria_extract.py`、`mysteria_text.py`
- ROM2 / SNR —— `rom2_extract.py`、`torimari_extract.py`
- STCM2L 平台变体 —— `norn9_extract.py`（PSV）、`pandora_extract.py`（PS2）
- 其他 —— `gensou_decode/extract/scan.py`、`haruka5_extract.py`、`kazahanaki_extract.py`、
  `shinoda_botan_extract.py`、`vn_memdump.py`

**新增坑条目**

- 解码层：WSC 全字节 `rotl_8(c,6)`；选项目标指令须按表分派；脚本 magic 之前的前缀区块另含正文；
  归档块单位需反推（取错＝整体错位）；opcode 逐文件平移；自建码表用一条已知明文锚定基址。
- 提取层：互斥分支＝同一点击多版本正文；共通导入块逐文件重复需去重。
- 交付层：辞典载体可能是同发行商他作遗留串（抽 3–5 条验证后整体排除）。

### 变更

- `SKILL.md` 重写：明确「开工只读本文件；§3 坑索引已覆盖全部坑，细节按阶段读」。
- `references/03-pitfalls.md` → 拆为 **`03a-decode-basics` / `03b-decode-archive` / `03c-decode-wsc-ops` /
  `03d-extract-lines` / `03e-deliver-flow`** 五个按阶段分册。
- `references/engines.md` → 改为**路由表**（一句话索引 + 「详见」列）；引擎细节拆到
  **`references/engines/<slug>.md`**（一引擎一文件，共 18 册，各 ≤10 KB），查引擎时**只读命中的那一册**。

---

**安装**：把整个仓库放进 Agent 的 skills 目录（如 `~/.workbuddy/skills/pretrans-extractor/`），
或直接当工具箱用（纯 Python）。详见 [README](https://github.com/flamecho/pretrans-extractor#readme)。

**依赖**：第三方工具与密钥不自带，见 [`references/third-party.md`](https://github.com/flamecho/pretrans-extractor/blob/main/references/third-party.md)。

> 本仓库不含任何解密密钥、授权串或游戏资源；请仅对**合法拥有**的游戏副本使用。
