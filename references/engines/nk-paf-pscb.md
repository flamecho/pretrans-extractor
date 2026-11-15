# NK / PAF / PSCB

## NK / PAF

匹配头为 `NK + u16 count + u32 data_length + u32 header_offset`，成员表以 header_offset 为准。
成员 16 字节：compSize、uncompSize、nameOff、dataOff。名称区可有独立变换，正文与名字解码分开。
NK 可嵌套，按 PSCB、MIG、NC 等内层类型分类，不固化归档大小、成员数或名字池地址。

## PSCB

PSCB 头给出版本、size、codeOff 和 dataOff；代码及 CP932 NUL 池分别按范围读取。
匹配 op11 可打印页，op36 可显示无尾标记的叙述，按实际参数引用取文本。
`$k` 可提交等待，`$r` 可排版换行；无 $k 的串仍可能为正文、选择、名札或菜单。
斜线选择分隔须由选择消费者确认，不能按长句或含斜线直接判断用途。
池序仅在引用序列证明一致后复用，不默认编译序等于显示序。
