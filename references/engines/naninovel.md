# Naninovel

## Script 与托管引用

Script.lines 的 rid 数组给出行序，references.RefIds 通过 rid、type 和 data 关联 ScriptLine 与命令对象。
textMap.idToText 是 keys/values 映射，按文本片段 ID 还原，不能按字典遍历顺序输出。
PrintText 的 playbackSpot、Text.raw.parts 和 AuthorId 参与正文定位，AddChoice 承载选项。
rid 起值及对象名偏移不固定；无 typetree 时用匹配序列化结构或 get_raw_data，不盲调用不兼容的对象读取器。

## 本地化与配置

同名 TextAsset 可为变量、词条、姓名或本地化 sidecar，按语言头、类型和引用区别。
原文及翻译工作稿通过片段 ID 或 hash 对账；注释中的原文不能混入再次输出。
CustomVariablesConfiguration 提供初值，姓名及标题变量按当前引用展开。

## 显示

按 PrintText 的等待、追加与清页参数维护段和页，选择按命令次序读取。
模板、宏脚本及未注册资源核对有效调用和独有内容，不能按文件名或同文率直接排除。
