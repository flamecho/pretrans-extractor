# VSC · VDP / LSB

## VDP

匹配目录自800h起，每项34h：name[16]、保留区、flags、size、字段、indexOff、dataOff。
flags低位可表示条目数；子目录项28h字节，包含offset、size及name。
数据对齐和偏移基准以索引及成员范围确认，不保存固定脚本数量。

## LSB

头给出size、cmdCount、cmdTableOff、bodyOff及场景名，代码和CP932 NUL参数分别读取。
记录头随opcode变化，不能用固定8/16字节头或短串相邻关系判定正文。
选择可带FFFF/CCCC及分支字段和连续串，名/文与旁白按命令引用解释。
反斜线/#排版、&/%姓名槽由当前宏表确认；PAC/TML为[另一格式](vsc-vl-file-tml.md)。

## 工具

`scripts/vdp.py`；复用前核对格式版本与参数。
