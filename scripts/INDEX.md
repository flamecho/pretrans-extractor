# scripts · 索引（随 skill 发布的通用工具）

> 全部**纯标准库、无硬编码路径**，任何机器 `python scripts/xxx.py` 直接跑（在**包根目录**执行）。
> ⚠ 本表 19 个工具都支持 `-h`；**585 个专用提取器不支持**——它们按单作写死 SRC/OUTDIR，直接 `python scripts/xxx.py` 就跑，加 `-h` 会被当成参数。
> 各作品的**专用提取器**：发行版随包附带 585 个 —— **按引擎查 `INDEX-BY-ENGINE.md`**；
> **反查某个 py 干什么 / 某作品做过没有** → `INDEX-BY-SCRIPT.md`（585 行，字母序，可 grep）
> （自动生成：引擎册 → 可改的脚本）。工作版在 `scripts/`，按引擎查 `TOOLS-works-<引擎族>.md`。

## 开工到收尾，一共 19 个

| 脚本 | 阶段 | 用途 | 用法 |
|---|---|---|---|
| `identify.py` | **S0** | 判型：容器/引擎/建议命令/该读哪份 `engines/*.md` | `python scripts/identify.py <文件或目录> [--deep]` |
| `probe.py` | **S2+** | 限量探查（默认 ≤80 行，绝不整表 dump）：`magic` `entropy` `strings` `jp` `hex` `u32` `find` `tree` | `python scripts/probe.py jp <file>` |
| `struct_probe.py` | **S6 之后** | **一行塞了几个框**：按配对结构判「合法内联引用」vs「多框粘连」，输出 A/B/C/D 四类 | `python scripts/struct_probe.py <成品.txt>` |
| `dup_probe.py` | **S6 之后** | **双版拼接探针**：找「同一行内同一句出现两次」（引号平衡时也能抓） | `python scripts/dup_probe.py <成品.txt> [--alias 名1,名2]` |
| `fix_wrap_pairs.py` | **S6 之后** | 框内软换行被切成两行 ⇒ 跨行续行收拢 / 缺引号补齐 | `python scripts/fix_wrap_pairs.py <成品.txt> [--ch 引号] [--repair]` |
| `fix_multi_brackets.py` | **S6 之后** | 一行多个框 ⇒ 拆行（独白 `（A）（B）` / 台词 `「A」「B」`） | `python scripts/fix_multi_brackets.py <成品.txt> [--dry]` |
| `merge_name_variants.py` | **S6 之后** | 双版拼接**合并**（名字宏双版 / 点名↔泛称），三种外观都覆盖 | `python scripts/merge_name_variants.py <成品.txt> --macro FF08` |
| `charset_audit.py` | **S6 之后** | **字符台账审计**：列出非日文字符＋次数＋首现行＋上下文，供人工逐字判定 | `python scripts/charset_audit.py <成品.txt> [--sus]` |
| `check_text.py` | **S7** | 成品品检：BOM/CR/`U+FFFD`/`〓`/控制符/半角假名/PUA/引号配对/说话人残留/主角名 | `python scripts/check_text.py <成品.txt> --name <主角名>` |
| `selftest.py` | **S7 前置** | **品检判据的回归测试**：28 个微型样本（半角假名 / 引号不配对 / PUA / BOM / CR / 名札 / 句号缺失 / 插入宏 / 双版版式 3 条 / 字符台账 4 条）。**改 `check_text.py` 前后各跑一次** | `python scripts/selftest.py [-v]` |
| `init_all_charset.py` | **S7 批量** | **一次生成全部字符台账**：对 `提取结果/` 下每个成品跑 `check_text --init-charset`（须在成品根目录跑） | `python scripts/init_all_charset.py` |
| `recheck_all.py` | **S7 批量** | **一次复检全部成品**：按双版清单逐个跑 `check_text`，汇总 PASS/FAIL 并列出 E/W（结果只打印，不落盘） | `python scripts/recheck_all.py` |
| `wrapup.py` | **S8** | **一条命令跑完收尾**：品检 → **行数一致性** → **切行判据三行** → 体积 → 沉淀草案 → 落位片段，输出待办清单 | `python scripts/wrapup.py --report R.md --text T.txt --name X` |
| `distill.py` | S8 | 报告 → **沉淀草案**：候选分「已覆盖 / 待沉淀 / 单作特例」＋建议落位册（**不改 skill**） | `python scripts/distill.py --report R.md [--log 日报.md]` |
| `archive_work.py` | S8 | 报告 → **四处落位片段**：WORKS 块 / TOOLS 节 / 日报小节 / 引擎提示（`--apply` 幂等追加） | `python scripts/archive_work.py --report R.md [--apply]` |
| `memcheck.py` | S8 | 目录体检：只报 `references/00-index.md` 超 8 KB（自动注入会截断）；其余册**仅列大小**，不作达标线 | `python scripts/memcheck.py` |
| `split_md.py` | 维护 | **按语义边界拆 md**：标题 / 编号条目 / 圈码；带零丢失校验与原子替换 | `python scripts/split_md.py <md> --dry-run` → `--names a.md,b.md` |
| `lint_docs.py` | 维护 | **手册对账**：断链 / 路由缺失 / 孤儿册 / 空册 / 编号连续 / 排版 / §N 引用 / 命令可跑 | `python scripts/lint_docs.py` |
| `pending.py` | 维护 | **未落位检测**：有成品无报告 / 有报告未进索引 / 未落位且无报告头 | `python scripts/pending.py` |

## 典型组合

```bash
# S0 判型（结论只当假设，用魔数复核）
python scripts/identify.py <母本目录> --deep

# S2 解包后：这条链路里到底有没有正文（0 命中 ⇒ 换载体，别硬找）
python scripts/probe.py jp <解包目录>

# 改过品检判据？先跑回归（退出码 0 = 28/28 通过）
python scripts/selftest.py

# S7+S8 交付收尾（一条命令；先不加 --apply 看片段，确认后再加）
python scripts/wrapup.py --report "解析报告/XX_解析报告.md" \
                         --text "提取结果/<压缩包名>.txt" --name 主角名
python scripts/archive_work.py --report "..." --apply        # 落到 WORKS / TOOLS 册

# 手册维护：先看切点，再语义命名落盘
python scripts/split_md.py references/S6-lines.md --dry-run
python scripts/split_md.py references/S6-lines.md --names "S6-lines-a.md,S6-lines-b.md"
```

## 三条安全约定（工具已内置，手工操作也要照做）

1. **不按字节切** —— `split_md.py` 只在语义边界下刀，并且**单条目过大时按空行切并标注「续 k/m」**。
2. **不「写完再 glob 删旧」** —— 一律「临时目录 → 校验（正文行守恒/边界守恒）→ 打印待删清单 →
   断言与输出名不相交 → 才删旧、搬入」。
3. **报告类工具只产草案** —— `distill.py` / `archive_work.py` **默认不写 skill**；
   落不落、落哪，由人按 `S8-wrapup.md` 的分工决定。
