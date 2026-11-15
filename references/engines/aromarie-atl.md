# Aromarie ATL · SQLite 剧本

## SQLite 表

以 scene.db 及运行时 SQL 确认格式，资源 AXRe 与文本库分别处理。

| 表 | 用途 |
|---|---|
| line | sceneId、lineNo、type、param 指令序列 |
| talk / talkText | talkId 关联、话者与按 phrase 排序的正文片段 |
| choice | choiceId、no、text、eval 与分支目标 |
| scene / next | 场景信息与跳转 |
| talkCode / talkVoice / AtomTable | 演出、语音、编辑器池，不直接作为正文 |

## 执行与显示

匹配枚举中 type=1 引用 talk，type=6 引用 choice；其余类型按调用解释。
同一 talk 的 phrase 先按序拼接；choice 按 no 读取，并保留显示条件。
同 lineNo 可有多条指令，按运行时 ORDER BY type,param 执行。只有已证明中间状态不显示且后写替换时才折叠；不能一律取最大 param。
未引用 talkText 与场景菜单标题分别核对，不为补池覆盖加入正文。

## 姓名与条件

talk.name 是名框模板，可回退到 target。正文 `%NAxx%` 的槽位、初值及空值取自 NameEditOnStart 与 VariableTable。
不保存固定姓名值。互斥同文选项仅在条件证明为替代版本后折叠，跨事件重复仍保留。
