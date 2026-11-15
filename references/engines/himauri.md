# Himauri · HXP / HIM

## HXP

Him4：`magic + u32 count + u32 offset×count`。
Him5：`magic + u32 folder_count + (u32 size,u32 offset)×count`；每个 folder 内为变长记录。
记录为 `u8 nameLen + u32 BE fileOffset + name + NUL`，nameLen 含五字节头及 NUL，即名字字节数+6。
成员为 `u32 comp_size + u32 orig_size + data`；comp_size=0 可为原样，其余按引擎 LZ 还原。

## HIM 消息

匹配布局中 33 消息包带 `FF 02 0E + u16 BE` 消息序号。
序号用于引用与覆盖检查，页界仍须核对提交、追加和等待状态。
名札可能是正文首行，旁白也可含空首行；按显示窗口处理，不固定所有包为同一名称布局。

## 工具

`scripts/himpac.py`、`scripts/himscript.py`；复用前核对格式版本与参数。
