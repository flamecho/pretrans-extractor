# MNP · ARC! / MMA

## ARC! / MMA

ARC! 头提供 index_off、entry_size、版本和 count；常见二十字节条目为 `{offset,usize,csize,HeaderSize,Flags}`。
无文件名索引的变体通过专门成员保存 CP932 名称表，先确认该成员用途。
Flags 决定过滤及压缩，不能按媒体后缀选择。

## 变换

已证 MMA 过滤可为循环键 XOR、ROR8 或 ROL8 与 LZSS 组合。
LZSS 控制位为 MSB-first；双字节匹配字段可用 `len=(o&0x1F)+3`、`dist=(o>>5)+1`。
密钥、过滤范围和 HeaderSize 来自对应方案及条目字段，验证消费与还原长度。

## 文本

脚本可为 CP932 行式命令。标签与 put/site/item/select 等调用分别解析，不能把标签前缀作为正文。
变量按初始化配置与控制流求值；排版、等待及页结束标记分别解释。
