# TOB / PSPFS / DSARC

## PSPFS / DSARC

PSPFS_V1 可为 `8B magic + u32 count + u32 reserved + count×(name[24],size,offset)`；存在其他项宽版本。
DSARC FL 成员为 name[N]、size、offset，N 按容器布局确定。
外层 gzip 可串联多段，按 eof/unused_data 逐段解；成员范围、条目宽度及对齐共同验证。

## TOB

tob 头含 size、version、strOff、strEnd 等字段；代码起点由头表及区段消费确认。
指令为 `u8 n,u8 opcode,(n-1)×u16 args`，n=1 无参数。
字符串可 XOR DA 后按 CP932 读取，地址和 padding 以四字节单位处理。
半角假名槽的实际字形由字体或读取器确认，不能直接全转平假名或全角。

## 消息

匹配 3E 以 wordOff 引用串起点，3F 为等待，41 为等待及清屏，3C 可重置状态。
01(7,N) 可为源码行号；03/04 可相对跳转，05/31 可为延时或等待参数，按操作数类型区分。
先解析指令再取显示引用，选择与正文分派按消费者确认；不能扫描 02 3E、语音或净引号差拼页。
