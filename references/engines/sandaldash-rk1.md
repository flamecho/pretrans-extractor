# SandalDash · RK1

## RK1

script.dat 尾16字节包含保留字段、RK1 NUL、u32 count和u32 table_off。
目录项28字节：name[12]、reserved、compSize、rawSize、offset；不用扫描ASCII名字代替尾指针。
匹配LZSS为4096零环、写位置FEE、LSB-first，1为字面量；
off=b0|((b1&F0)<<4)、len=(b1&0F)+3，按环绝对下标逐字节复制。

## 144字节记录

解压体为code:u8、field1[64]、field2[64]、tail[15]，核对rawSize是否为144的倍数。
64为正文，6A可为名札，6E/6F可收尾；旁白可直接进入正文，不要求前有6A。
同段连续64是排版行，等待与清屏分别按处理器确认，空尾组不输出正文。
CD的field2可为选项，CE收组、C8分派；不能因其他field2含引号就收作选项。
D2可引用无扩展名脚本，按目录名称规则和跳转参数恢复顺序。
