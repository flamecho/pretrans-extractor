# VividColor · COM / CMP

## COM / CMP

COM可为PE附加区的裸成员、压缩索引和尾部PACK/u32 idx指针。
索引以u32原始长度加LZ流还原，项含offset、nlen_field、flag和UTF-16LE名字。
部分布局将长度与标志合在nlen_field，确认低位长度掩码后读取，不能固定字段总是纯字符数。
CMP可压缩成员并使用不同尾签名或索引变换。顺序解块仅在长度头、载荷消费与索引起点均验证后使用。

## LZ与脚本

匹配LZ中c<80h为c+1个字面量，c>=80h时v=(c<<8)|next，len=((v>>10)&1E)+2、dist=(v&7FF)+1。
SCR可为UTF-16指令文本，其他成员可为XML；分别按字段结构读取，不能从扩展名继承消息模型。
裸存、无长度头媒体与压缩块分派须由版本和成员类型确认，不固定PE附加起点。

## 工具

`scripts/pack_cmp.py`；复用前核对格式版本与参数。
