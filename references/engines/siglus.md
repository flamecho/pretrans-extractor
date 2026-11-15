# Siglus

## Scene / Gameexe

载荷可为固定256字节表和可执行16字节键的XOR组合；Scene与Gameexe使用不同固定表。
Gameexe头的needKey决定是否施加EXE键，再按长度头解压为UTF-16LE配置。
场景头为33个i32，给出代码、字符串、标签、属性、命令及姓名等列表的ofs/count。
验证所有区段及单位；字符串索引的offset/len可为字符单位。
匹配串i的u16单元XOR `(28807*i)%65536`，不能将其按字节XOR。

## 字节码与显示

指令包含PUSH(form,val)、运算、属性、跳转、调用、COMMAND、TEXT、NAME与SEL_BLOCK。
FM_STR=20、FM_INT=10的匹配布局须与参数表对应；完整解析栈与调用，不能只看push后的一个opcode。
TEXT的read_flag用于记录引用，NAME用于姓名；字符串加法也可构造普通文本，不自动判为选择。
选择、资源和正文按消费者分类；页界由命令和显示层确认，不固定每个TEXT为一页。
