# YKC / YKS

## YKC001

24字节头给出idx_off与idx_len，20字节索引含name_off/name_len/data_off/size/reserved。
名称池可在数据末尾，name_off为绝对偏移；按索引读取CP932 NUL名称，核对数据及名称范围。

## YKS001

40字节头给出多个块的offset/count/len。匹配布局只对块4逐字节XOR AA，其他块不变。
块4可为命令名NUL及u32或CP932参数，不能把40字节头后所有数据都取反。
13、Case、WindowNameSet、StrOut等标记的参数类型须结合前后命令解释。
相邻串可为姓名、正文、语音或资源，不能只凭字符串长度与13计数切页。
按选择和显示调用维护顺序、段与页；表内数值中的0A/0D不是文本换行。
