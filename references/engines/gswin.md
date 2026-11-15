# GsWin · DataPack5 / SCW

## DataPack5 / SCW

DataPack5 为归档签名，GsSYMBOL5BINDATA 为符号库；Scw5.x 为脚本。
SCW 头中 14h 为 i32 compressed，18h/1Ch 为原始/存储长度，24h 起为指令、字符串、标签的 count 与 len。
匹配布局数据自 1C8h 起，先按位置 i&FF XOR；compressed=-1 时再 LZSS。
解出的体为三张 `(u32 off,u32 len)` 表及三个数据区。
校验 `raw_len=8×Σcount+Σlen`、各表范围及指令引用，不能只检查解码出日文。

## 分类

按指令消费者区分正文、选择、名称、标签和资源。归档名称可辅助核对语音与图像引用。
纯 ASCII、符号开头、小节号或 Sys/TEST 文件名只作筛查线索，不能直接排除显示文字或整本脚本。
