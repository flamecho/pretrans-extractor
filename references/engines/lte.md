# LTE

## 资源与 PacK

LTE 脚本可为 Unity TextAsset 中 UTF-16LE BOM 文本，也可位于 PacK 的 gzip 成员中。
PacK 与全大写 PACK 不同；匹配 PacK 数据按 400h 对齐，先验证成员头、gzip 消费和目录关系。
Unity 的资源对象定位见[Unity](unity.md)，不能固定 TextAsset 数量或对象名称偏移。

## 标签 DSL

扫描 `<tag 属性>`、引号、嵌套标签和标签外注释；属性内的 > 不能结束标签。
pb 可翻页，wait key=true 等待点击，wait time 是定时停顿；等待不天然清页。
select/case 或专用选择容器取 value 文案，分支目标不输出。
ruby 取基底，tips 取内联词，place 等上屏字幕单独分类；颜色与样式保留其正文内容。
名札、mobilephone、monologue 等图层按实现区分，不因标签名相同跨版本继承语义。

## 词条与变量

词条及初值可能位于 TextAsset、配置或 Assembly-CSharp 的 #US 堆。
#US 为压缩长度前缀、UTF-16 数据及末尾 flag；ldstr token 指向条目长度前缀。
按调用和字段关系配对 ID、标题与解释，不能用相邻三串或固定词条前缀泛取。
