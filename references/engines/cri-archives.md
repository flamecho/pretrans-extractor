# CRI · CPK / AFS

## CPK

CPK 元数据采用 @UTF，TOC / ITOC 决定名称、ID、长度和定位方式。
按表类型与字段标志读取常量列、逐行列及字符串/数据区，偏移基准由字段及头声明确定。
无 TOC 或名称时，通过 ITOC 的 ID 顺序、Align 和 ContentOffset 定位成员，核对 ContentSize。
CRILAYLA 等成员压缩与 CPK 包本身区分；FileSize 与 ExtractSize 分别保留。

## AFS

AFS 头为 `AFS NUL + u32 count + count×(u32 offset,u32 size)`，名称表可为附属区段。
首个成员偏移不是独立数据区字段；核对索引末、对齐和成员范围。
CPK/AFS 只定义归档，脚本编码、姓名槽和点击模型由内层格式决定。
通用偏移与压缩检查见[归档](../archives.md)。

## 工具

`scripts/cpk.py`、`scripts/cpk_v1.py`；复用前核对格式版本与参数。
