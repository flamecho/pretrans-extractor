# AVG32

## PACL / PACK

SEEN.TXT 可为 PACL 剧本归档；SEEN.MAC 是相关宏或折行资料，是否同源须核对。
PACK 成员为 `PACK + u32 0 + u32 unpacked + u32 packed`，载荷自 0x10 起。
匹配压缩为 MSB-first LZ：1 为字面量，0 为两字节 token；
`count=(token&0x0F)+2`、`distance=(token>>4)+1`。未压缩条件按读取器解释。

## 版本与参数

可参考 avg32 crate 的 archive、scenario、meswin、system 实现。
版本至少影响 FE/FF 文本前缀和 67 子命令的 val 参数；按可执行版本和匹配表读取，不用程序大小推定版本。
未知指令数与区段闭合用于检查参数宽度，不能单靠 unknown=0 证明正确。

## 显示状态

| 指令 | 匹配实现的语义 |
|---|---|
| 01 / 03 | 点击等待，line_feed 分别为 true / false；清屏须另查 |
| 02 | CR 排版换行 |
| 04 子命令 | mes_clear / mes_hide 或等待后清理 |
| FE / FF | 文本包，按版本处理扩展前缀 |
| FD、40 @n、10 子命令 | 字符串或数值插入 |
| 58 子 1/2/3 | 22 列表至 23 的选择项 |

＊Ａ至＊Ｚ 为字符变量槽，取配置与运行时值。draw_buffer_string、窗口标题及名字输入标题按显示用途分类。
