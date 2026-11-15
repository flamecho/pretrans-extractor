# Swallowtail · FPK / SPT / ACT

## FPK / RLE0

FPK为u32 count后32字节成员：u32 offset、size、name[24]；匹配offset为文件绝对偏移。
RLE0头为magic及24、stored、decoded、method、reserved；method区分原样与RLE。
控制c高两位为操作，低六位为n，零可表示40h；字面量、单字节及双/三字节模式重复的次数按对应分派确认。
核对成员范围及还原长度，不能只因出现Ogg或PNG头就推定整个包用途。

## SPT / ACT

SPT为count后八个u32的记录，可含opcode、话者/语音、ACT行号、行数及参数。
ACT的CP932行池通过记录引用取范围，标签或注释可辅助关联SC正文与SL选择。
匹配op1可显示一页，名札行是否包含在行数中、旁白是否省略名札由handler确认。
框内物理行合并，点击与清屏按显示状态处理，不保存固定人物ID、行宽和主程序地址。
