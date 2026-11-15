# Artemis · PF 与标签脚本

## PFS 版本

pf6 与 pf8 共享长度前缀目录的总体结构，但索引范围与成员过滤不同。
按签名读取 index_size、file_count 和 `{nameLen,name,separator,offset,size}`，校验表尾及成员范围。
pf6 的已证变体可为原始成员；pf8 可使用索引 SHA-1 作为循环 XOR 键，过滤范围与视频例外由匹配实现确认。
不能给所有版本套同一 XOR 或只变换前二十字节。

## 脚本

标签式文本和 Lua 风 AST 两类格式分别处理。
标签文本按命令属性取 text，感知注释、块注释、缩进与内联 tips；不能将所有 [ 起头片段视为命令行。
AST 按 text/name/select 等字段取文案，ruby 保留基底，排版 token 与等待分开解释。
语法块、物理行和字符串条数不直接等于点击，最终按文本打印及窗口调用确认。

## 工具

`scripts/artemis_pfs_extract.py`；复用前核对格式版本与参数。
