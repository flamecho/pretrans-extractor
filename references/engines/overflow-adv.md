# OverFlow ADV

## SCRIPT.DAT 变体

StackSoftwareADV / OverFlowADV 标识可辅助识别，格式选择以尾部、目录和脚本结构为准。

| 布局 | 容器与 OBJ |
|---|---|
| xor12 | 尾 3×u32 XOR F0F0F0F0；OBJ 可含 u32 dirOff、u16 count、u32 off/u16 len 表 |
| not8 | 尾 2×u32 取反；OBJ 可含 u16 codeOff、u16 count、u16 off/len 表 |

解码尾字段后核对目录压缩/原始长度及范围，不能由文件大小或作品名选分派。

## LZSS

匹配 DecodeLz 为 4096 零环、写位置 FEE，MSB-first，0 为字面量、1 为 u16 LE 匹配。
匹配 len=(v&F)+3、off=(v>>4)&FFF，为环绝对位置。
核对输入消费和输出长度，不能强截到 dsize 掩盖偏移错误。

## 参数与显示

80/11 等压串、00/09 页分隔和20/11 分派依版本解释。
池可分正文、语音、空槽及姓名区，按实际参数引用确认，不固定 3g / 3G+g 索引公式。
控制 P数字 按读取器处理；槽位异常逐处核对，不自动用旁边非资源串补正文。
原文编码按资源与加载器确定，不用一串多编码回退掩盖损坏记录。
