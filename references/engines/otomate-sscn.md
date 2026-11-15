# Otomate · SSCN

## SSCN JSON

Buff 是 base64 命令流，Positions 给出指令起点；相邻偏移差可用于核对长度。
TextData 是混合池，包含正文、选项及条件、资源等操作数；Labels / Tags 定义跳转与命令标签。
先检查 Positions 单调性、终点和代码范围，再按 opcode 参数取池索引。

## 显示与变量

结合实际消息函数确认正文参数、名札、追加/清页及等待，不能将 TextData 全池导出。
选择的文案与分支目标分开，动态变量以初始化及显示调用解析。
平台容器取出见[Switch](../platforms/switch-nca.md)，不在格式册保存固定 HFS0 基址或分区数量。
