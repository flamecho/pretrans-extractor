# VSC · PAC / TML

## PAC / MemPack

vlLZSS型PAC可为u32 version=1、u32解压长、压缩流，解出MemPack的count及32字节名称/大小项。
原样型可为version=0、总长、count、保留区及同类项。成员按声明大小累积。
匹配vlLZSS用4096环、写位置FEE、LSB-first，1为字面量；
off=b0|((b1&F0)<<4)、len=(b1&0F)+3，off为环绝对位置，初始化按实现确认。

## TML消息

匹配1F4/1F6可追加显示文本，1F7可完成消息；1F5/130/131也可能参与续文检测。
按IsNextCommandMsgCheck及等待处理确定同段和页，不将所有白名单命令作正文。
姓名、语音与选择参数按字段用途读取，不固定为单击或单版。
