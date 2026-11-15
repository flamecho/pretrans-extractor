---
name: pretrans-extractor
description: >
  从 PC、PS2、PSP、PSV、Switch 日文 VN / AVG 资源提取正文、选项和叙事资料，
  解析字节码、编码及显示边界，生成 LunaTranslator 预翻译原文与解析报告。
---

# 游戏文本提取

1. 查已有提取器、报告和作品记录，沿用已确认的[范围](references/output.md)、姓名值与参数，接续未完成步骤。
2. 按签名、容器、头布局和命令语法查[引擎与格式索引](references/engines/index.md)，复用匹配的解析与显示策略；未知格式再[判型](references/identify.md)，变化处核对读取实现与显示调用。
3. 按[交付自检](references/verification.md#交付自检)核对输出并保存报告；输入与处理未变的通过记录直接复用。

共通流程见[文档导航](references/index.md)。引擎册只存格式知识；单作参数、结果和状态留在已有报告与工作记录。

| 当前需要 | 入口 |
|---|---|
| 引擎或格式 | [引擎与格式索引](references/engines/index.md) |
| 姓名槽与动态模板 | [动态策略](references/names-and-macros.md#动态策略) |
| 记录或 ELF / PE 编译剧情 | [脚本结构](references/script-structure.md) |
| 未决点击与页界 | [边界取证](references/layout.md#边界取证) |
| 清理或技能修订 | [工作区](references/workspace.md#收尾与维护) |
| 工具参数 | [脚本索引](scripts/index.md) |

发行版工具：[格式与脚本](scripts/by-engine.md)、[脚本用途](scripts/by-script.md)、[第三方依赖](references/third-party.md)。
