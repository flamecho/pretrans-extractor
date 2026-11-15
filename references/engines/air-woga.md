# Adobe AIR / woga · DAT 与 WAS

## DAT 分段

SWF/ABC 中的 `jp.co.woga.util:PackageLoader`、`packageStream` 可辅助识别。
DAT 为四字节头后串联 raw deflate 流；从偏移 4 使用 `decompressobj(-15)`，每段边界由 eof 和 unused_data 确定。
分块喂入，避免每段复制整个剩余文件。解出的 JSON 清单、脚本与媒体分别分类，不能用 PNG 内的偶然模式猜分段。

## WAS 文本 DSL

UTF-8 脚本含 `__` 标签、`@@命令{JSON}` 和正文；按命令、引号、JSON 及注释语法扫描。
`@@message` 的正文可跨物理行；是否提交并等待由 WASmessage.run 及 target 图层确认。
裸行也可能显示文字，不能只取 TAB 行。邮件、聊天与主文本层分别追踪，昵称是否内联按实际显示确定。
CSV 题库按字段读取题干和选项，槽数从数据与读取器确定，不固化路线号、题数或输出分隔符。

## ABC 取证

DoABC 头为 u32 flags 和 NUL name，不能将 flags 当 u30。
`coerce_b/a/i/d/s/u/o` 无操作数；只有 `coerce(80)`、`astype(86)` 带 multiname。
方法体、命令分发表及显示目标用于核对页界和裸行语义；常量池中是否存在一个词不能单独决定它是否为命令。
