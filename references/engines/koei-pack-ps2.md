# Koei · PACK

## PACK 头

`PACK + u32 nameLen + name[nameLen]` 后为八个 u32：A、B、dataOff、dataSize、flag、count、recSize、reserved。
A 指向记录起点，B 为表长度；匹配布局满足 `A+B=dataOff`、`count×recSize=B` 和 `dataOff+dataSize=文件长`。
第一字段不是成员数；nameLen 可为零或有变换后的名字/签名区。

## 记录变体

64 字节项可为 `name[48] + off,stored,decomp,step`，也可仅存名称或经双字节码变换。
不能因头部相同就固定把记录尾四个字段解释为偏移和大小。
偏移型表核对成员范围及累积长度；纯名称表的数据定位和文本格式仍须从加载器确认。
