# 3Daisy · SCRVITA / TBL / PAK

## PAK / TBL

PAK 可为 0x800 字节头及按 0x800 对齐的脚本序列。TBL 保存版本、头长和条目数，数量从索引读取。
脚本头 16 字节：`u32 LE magic=0x00011804 | u32 checksum | u32 BE stream_off | u32 BE ?`。
命令起点为脚本起点加 stream_off；魔数候选还须通过脚本范围与指令消费校验。

## 命令与文本

token 为 `00 <u8 len> <payload>` 或单字节 opcode。带参载荷首字节 `01` 后为 BE u32；
`02` 后为 `u16 BE len + CP932 文本 + NUL`。逐 token 前进，不能在载荷中扫描 opcode。
所列布局中 `F0` 可设内容或以空串清页，`B0` 可追加，`01` 可显示标题；结合调用参数核对具体用途。
函数、资源和跳转字符串按消费者排除。显示起点不由引号、空格或非 ASCII 字符决定。
姓名可能与正文内联，先核对名札显示方式，再按[姓名策略](../names-and-macros.md#名札与关联)处理。
