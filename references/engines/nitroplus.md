# Nitroplus · NPA / NSS / NPK3

## NPA

NPA 头为签名、版本、键字段、压缩/加密状态、条目数与目录长度。
常见索引自偏移 41 起，条目为 `nameLen,name,type,folderId,offset,size,unpacked`，步长为 `4+nameLen+17`；数据位置为 `41+dir_size+offset`。
名称变换、键组合、内容过滤长度及置换表由具体 EncryptionScheme 选择，不能按作品名猜方案。
方案匹配通过独立成员的解压、语法和长度验证；方案值及密钥属于输入参数，不复制到格式册。

## NSS

NSS 可包含 include、scene/chapter/cut、函数、PRE 文本对象、ruby、voice、字体和点击标签。
显示文本与 SetBacklog 日志字段分别处理；不同稿的近似同文不自动合并。
选择、扉文、歌词与菜单按钮可能来自独立 CreateText / SetChoice / Palette 调用。
按标签大小写、注释、文本对象及实际打印逻辑维护段页，不能简单按物理空行或一条 Print 切分。

## NPK3 / Squirrel

NPK3 头含 minor、16 字节 IV、count 和 tableSize。表与段可使用 AES-256-CBC/PKCS7，段长度决定是否还有 zstd。
目录保存 mode、UTF-8 路径、文件长度、SHA-256 与段数组；按表校验逐成员还原。
密钥由对应实现或输入提供，不能使用其他作品的固定值。
Squirrel 的函数树、独立字面量池及寄存器传参共同确定调用，不能仅搜索字面量文本。
跟踪 LOAD/MOVE/PREPCALLK/CALL 等操作，在条件分支中保存可能的值，不静默丢弃未知参数。
TypeBegin、Print 和 CommitText 的提交与 wait_key 门控决定段与页；<K>、ruby、palette 等按相应 handler 核对。
