# TATC / RSON

## RSON / RZ / TATC

script.memfs 可为 RSON 索引，script.membody 存 RZ 包装的 zlib 块；按偏移/长度及路径表关联成员。
名称可用 UTF-16LE 与类型、长度字段编码，表位置从头和结构确定。
TATC 可含 `C0DEABC1`、KUV 签名、命令名表、字节码和 UTF-16LE 池；不能继承文本 TAT 的解析器。

## 指令与显示

GuideMess 可取旁白，NameMess 可含名字、正文、语音及立绘参数，SltRun 执行选择。
GAMESTR_DictWords 可关联词条及解释；_END 是块标签，不能当选项文本。
UTF-16 NUL 按两字节单元定位，但字段起点的绝对奇偶由记录布局决定。
CRLF、#R/#P/#T 等模板按实际处理器解析，姓名与版本条件保留分支关系，不固定一串一页或选第一支。
