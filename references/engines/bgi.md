# BGI · ARC 与脚本

## PackFile / DSC

PackFile v2：12 字节头 `PackFile + u32 count`，成员 32 字节为 `name[16],off,size,u32,u32`。
DSC FORMAT 1.00 含 key、out_size、dec_count，0x20 起为 512 字节变换后的 Huffman 深度表，0x220 起为 Huffman/LZ 流。
表变换由匹配 PRNG 实现确定；压缩码 >=256 可为回引，长度与距离须按版本解释。

## 字节码版本

| 版本 | 结构与消息 |
|---|---|
| v0 | u16 opcode；0010 PrintMessage(win,mode,str)、0014 SetName、00B0 Select |
| v1 | u32 opcode；0003 压串、0140 等消息调用、0160 选择、00F0 加载脚本 |

v0 的 mode=0 不等待，正文向后累计到结束当前段的 mode=1。
v1 消息参数有两参数及五参数等布局；按函数签名和栈行为取正文，不固定最近五次 push 或名/文栈顺序。
串池偏移与内联 NUL 分别读取；未知指令须核对操作数，不以四字节强推进。
调用图、归档覆盖层与分支条件用于恢复顺序及替代版本，不能按游戏名、后缀或同文率直接排除。
