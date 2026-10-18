# scripts · 索引（随 skill 发布的通用工具）

> 全部**纯标准库、无硬编码路径**，任何机器 `python scripts/xxx.py` 直接跑。
> 各作品的**专用提取器**：发行版随包附带 240+ 个 —— **按引擎查 `INDEX-BY-ENGINE.md`**
> （自动生成：引擎册 → 可改的脚本 → 一句话用途）。工作版在 `scripts/`，按引擎查 `TOOLS-works-<引擎族>.md`。

## 开工到收尾，一共 11 个

| 脚本 | 阶段 | 用途 | 用法 |
|---|---|---|---|
| `identify.py` | **S0** | 判型：容器/引擎/建议命令/该读哪份 `engines/*.md` | `python scripts/identify.py <文件或目录> [--deep]` |
| `probe.py` | **S2+** | 限量探查（默认 ≤80 行，绝不整表 dump）：`magic` `entropy` `strings` `jp` `hex` `u32` `find` `tree` | `python scripts/probe.py jp <file>` |
| `check_text.py` | **S7** | 成品品检：BOM/CR/`U+FFFD`/`〓`/控制符/半角假名/PUA/引号配对/说话人残留/主角名 | `python scripts/check_text.py <成品.txt> --name <主角名>` |
| `selftest.py` | **S7 前置** | **品检判据的回归测试**：21 个微型样本（半角假名 / 引号不配对 / PUA / BOM / CR / 名札 / 句号缺失 / 插入宏…），断言「该报的报了、不该报的没报」。**改 `check_text.py` 前后各跑一次** | `python scripts/selftest.py [-v]` |
| `wrapup.py` | **S8** | **一条命令跑完收尾**：品检 → **行数一致性** → 体积 → 沉淀草案 → 落位片段，输出待办清单 | `python scripts/wrapup.py --report R.md --text T.txt --name X` |
| `distill.py` | S8 | 报告 → **沉淀草案**：候选分「已覆盖 / 待沉淀 / 单作特例」＋建议落位册（**不改 skill**） | `python scripts/distill.py --report R.md [--log 日报.md]` |
| `archive_work.py` | S8 | 报告 → **四处落位片段**：WORKS 块 / TOOLS 节 / 日报小节 / 引擎提示（`--apply` 幂等追加）。读报告头的 `---` 块（作品/平台/引擎/主角/行数），无则正则兜底并标「请核对」；`infer()` 可 `import` 复用 | `python scripts/archive_work.py --report R.md [--apply]` |
| `memcheck.py` | S8 | 体积体检：memory / skill 各册是否超 10 KB（≥96% 提前预警） | `python scripts/memcheck.py` |
| `split_md.py` | 维护 | **按语义边界拆 md**：标题 / `**B22.` 条目 / 圈码；带零丢失校验与原子替换 | `python scripts/split_md.py <md> --dry-run` → `--names a.md,b.md` |
| `lint_docs.py` | 维护 | **手册对账**：断链 / 引擎册未进路由表 / 孤儿册 / 空册 / 超限 / 坑册编号重复 | `python scripts/lint_docs.py` |
| `pending.py` | 维护 | **未落位检测**：有成品无报告 / 有报告未进索引 / 未落位且无报告头 | `python scripts/pending.py` |

## 典型组合

```bash
# S0 判型（结论只当假设，用魔数复核）
python scripts/identify.py <母本目录> --deep

# S2 解包后：这条链路里到底有没有正文（0 命中 ⇒ 换载体，别硬找）
python scripts/probe.py jp <解包目录>

# 改过品检判据？先跑回归（退出码 0 = 21/21 通过）
python scripts/selftest.py

# S7+S8 交付收尾（一条命令；先不加 --apply 看片段，确认后再加）
python scripts/wrapup.py --report "提取结果/解析报告/XX_解析报告.md" \
                         --text "提取结果/XX_全文本.txt" --name 主角名
python scripts/archive_work.py --report "..." --apply        # 落到 WORKS / TOOLS 册

# 手册维护：先看切点，再语义命名落盘
python scripts/split_md.py references/04-lines.md --dry-run
python scripts/split_md.py references/04-lines.md --names "04-lines-a.md,04-lines-b.md"
```

## 三条安全约定（工具已内置，手工操作也要照做）

1. **不按字节切** —— `split_md.py` 只在语义边界下刀，并且**单条目过大时按空行切并标注「续 k/m」**。
2. **不「写完再 glob 删旧」** —— 一律「临时目录 → 校验（正文行守恒/边界守恒）→ 打印待删清单 →
   断言与输出名不相交 → 才删旧、搬入」。
3. **报告类工具只产草案** —— `distill.py` / `archive_work.py` **默认不写 skill**；
   落不落、落哪，由人按 `05-wrapup.md` 的分工决定。
