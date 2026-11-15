# Karin ADV · ASB

## ASB 与源脚本

ASB 头为 `ASB NUL + u32 BE payloadSize×2 + u32 BE stmtCount + u32 BE hash`，随后为编译体。
同名 TXT 可为 CP932 文本源，包含 `@label`、`@text`、`@click`、`@cls` 等命令。
先核对名称、语句及调用是否与编译体对应，可靠源脚本可直接解析，不因包中存在 ASB 就默认反编译。

## 显示

按引号和转义读取 text 的名札、正文与参数。click 是等待、cls 是清屏，二者分别更新状态。
选择、标题与资源按显示调用分类；源稿与运行时版本不同则以实际加载版本为准。
