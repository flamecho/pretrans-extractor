# 脚本索引

从当前工作区调用技能脚本；参数以帮助或实现为准，不支持选项的旧脚本先查参数读取方式。
通用工具见下表；单作提取器查工作区 `scripts/` 和现有工作记录。

| 脚本 | 用途 |
|---|---|
| `identify.py` | 容器/引擎识别提示，须用魔数和结构复核。 |
| `probe.py` | 签名、熵、字符、局部字节和目录摘要，输出限量。 |
| `struct_probe.py` | A/B 失衡与 C/D 多段候选；不判断点击或页数。 |
| `dup_probe.py` | 行内重复候选；去重须有来源依据。 |
| `charset_audit.py` | 非日文字符、频次及上下文摘要。 |
| `check_text.py` | 编码、残留、字符台账和声明一致性；`--layout-map` 可选验证合并页。 |
| `selftest.py` | 品检回归；修改检查行为后运行。 |
| `test_workflow.py` | 来源页映射、收尾范围、验证复用与子进程 UTF-8 回归。 |
| `init_all_charset.py` | 在任务范围内批量生成字符台账；基线仍需核实。 |
| `recheck_all.py` | 在任务范围内批量复检文本。 |
| `wrapup.py` | 默认校验本作；`--checked-sha256` 复用通过记录，维护按显式选项执行。 |
| `distill.py` | 从本作报告生成沉淀草案，不直接修订技能。 |
| `archive_work.py` | 从报告生成记忆片段，`--apply` 执行落位；`--work` 是作品名。 |
| `memcheck.py` | 记忆入口体积信息，仅在维护需要时运行。 |
| `split_md.py` | 按语义拆文档，先用 `--dry-run` 核对输出及引用。 |
| `lint_docs.py` | 检查路径、路由及排版；默认包含工作记录，`--mem` 限定范围。 |
| `pending.py` | 显式批量维护时查待落位项目；仅清理时不运行。 |

`fix_wrap_pairs.py`、`fix_multi_brackets.py`、`merge_name_variants.py` 是历史启发式修补工具，
使用前由源码确定修复范围，统计结果仅定位候选。

清理与收尾见 [规则](../references/workspace.md#收尾与维护)，验收命令见 [自检](../references/verification.md#交付自检)。
