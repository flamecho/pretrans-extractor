# Monoceros

## GLNK

匹配头为 `GLNK + u16 version + u32 count + u32 entry_start + u32 data_start`。
成员为 `u8 nameLen + name + u32 off,size,reserved`；按头地址与成员范围确认偏移基准。
媒体包不一定含脚本，消息池也可能在主程序或独立区段。

## 消息与选择

匹配 opcode 8000 以 u32 消息号取池串，XOR FF 后交给 SetText，并注册点击对象。
SetText 的整页替换与日志窗累计绘制须分开；回想队列不能作为剧情页界依据。
选择可有 `28 00 01 + u16 字节长 + CP932` 载荷，按命令组及分支解释，不固化窗口尺寸、地址或选项数量。
