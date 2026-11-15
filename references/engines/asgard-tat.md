# ASGARD · TAT 脚本

## 识别

script_tat 下 TAT 可为 UTF-8 BOM 文本，rdix.rson 登记资源路径；PFS 解密见[PSV](../platforms/psv-pfs.md)。
TAT 后缀也用于其他格式，先确认文本语法。

## 点击与清屏

标签 `[label]`、`<命令 …>`、行与块注释先按语法读取。物理正文行累积到 KW。
`<KW>` 为等待，`<WinClear>` 为清屏；成对出现时形成单击页，裸 KW 须保留同页新增段。
Voice 变化用于定位疑点，不能直接补出缺失点击。
速度 `#S…`、颜色 `#C…` 按完整控制语法消费；损坏指令逐处核对，不按残片字符整行过滤。

## 选择与姓名

SltDel / SltAdd / SltRun 组成选择；三字段 `idx,label,text` 取显示字段。
多文件或多 label 的组结合入口确认是否开发菜单，不凭字段数直接排除。
