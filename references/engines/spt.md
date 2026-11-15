# 混合编码 SPT

## 混合编码SPT

命令可含#SYS.ID、#MES.OUT、#MESEX.OUT，语法为ASCII，标签可用CP932，引号参数使用大端双字节单元。
与XOR FF后SPTHEADER0的System-NNN及其他SPT不同，先核对实际头与语法。
从命令参数起点按双字节单元读取；匹配参数以22开始、2522单元终止，不能逐字节找引号。

## 参数与显示

MES.OUT可有无名正文，MESEX.OUT可有姓名与正文；SELECT/ENDSELECT给出选择组。
5C6E可为字面排版换行，`%{基底%:读音%}`为ruby，末尾%K%P可为等待及清页。
按命令的类型、字段数量及显示实现读取，不固定所有参数索引。
