# LiveMaker · VF / LSB / TpWord

## VF 归档

VF 位于独立文件或 PE overlay，头为 `vf + u32 version + u32 count`。
目录依次保存长度前缀文件名、count+1 个 offset、压缩类型、附加字段、校验值和加密标志；尾部可为 `u32 archive_offset + lv`。
文件名、offset_low 和 offset_high 使用独立混淆流；共享流会使后续字段错位。

```text
key = (key * 5 + 0x75D6EE39) & 0xFFFFFFFF
字节变换消费 key 低字节；整数变换按四个字节消费同一 key。
compress_type: 0=ZLIB, 1=NONE, 2=ENCRYPTED, 3=ENCRYPTED_ZLIB
```

结合目录末、offset 单调性、末成员和 trailer 校验。分离目录/数据文件时，offset 基准改为数据文件，不沿用 overlay 闭合式。
加密标志非零时须使用对应方案；目录闭合不能替代逐成员解压校验。

## LMScript

LSB 头包含版本、标志、命令种类数及参数标志流长度。按版本读取命令字段，不硬编码命令数或标志流宽度。
命令公共字段包括 type、Indent、Mute、NotUpdate 和 LineNo；TextIns 嵌入 TpWord，Call/Jump 提供文件与标签目标。
入口与正文范围由调用和 TextIns 用途确定，脚本名称、目录位置和 TextIns 数量不能独立排除载体。

## TpWord

块头为 `TpWord + 三字节 ASCII 版本`，随后为 decorators、conditions、links 和 glyph 数组。
conditions 自版本 104 引入，links 自版本 105 引入；glyph 字段宽度按版本读取。

| glyph | 载荷用途 |
|---|---|
| Char | link、速度、字符码及 decorator；字符通常为大端 CP932 双字节码 |
| Return | break_type |
| Event | 事件名与参数 |
| Var / HistChar | 变量与装饰引用 |
| Img | 图片来源、状态与对齐 |

块长与消费终点闭合，变量、图片、链接和事件分别跟踪，不能只收 Char 后忽略潜在显示来源。

## 点击、页界与选择

BreakType 枚举为 LINE=0、PAGE=1、PAUSE=2、CLEAR=3。LINE 是排版换行；PAGE 是否翻页以及事件是否等待，结合消息页状态机确认。
`{PAUSE}` 可在同页继续；区分等待旗标与当前页索引，保留同页新增段。
TextIns 的 Wait、StopEvent、目标控件及点击分支决定提交，不把一块 TpWord 固定当成一次点击。
选择可能由 To 临时变量、AddArray、ArrayToString 和选择执行 Call 组装；沿操作数绑定取字面值，以实际调用点分组。
外框图片、NAMELABEL 或内嵌标签都可能提供名札，按可见位置关联正文。

## 工具

`scripts/livemaker_extract.py`；复用前核对格式版本与参数。
