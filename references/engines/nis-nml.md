# NIS · NSAC / NML

## NSAC / NML

NSAC v2 包装与数据库成员共同定位 NML 资料，先识别容器版本与真实成员类型。
数据库、脚本文案和系统字段通过引用及显示用途区分；不能把所有 database.dat 字符串按池序输出。
容器读取可复用 `scripts/nsac.py`，文本字段仍由对应 NML 读取和调用核对。

## 工具

`scripts/nsac.py`；复用前核对格式版本与参数。
