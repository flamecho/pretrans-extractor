# Unity · 资源与脚本格式

## 资源定位

Managed DLL 可为 Mono；global-metadata.dat 与匹配主程序用于 IL2CPP 类型恢复。
StreamingAssets、Addressables、resources.assets 和 AssetBundle 都可能承载文本。
按索引和对象类型定位；UnityPy 返回零对象或头异常不自动证明加密或无文本。
缺 typetree 时使用匹配 Unity 版本及程序集的 TypeTreeGenerator，确认类型布局后才借用其他版本模板。

## TextAsset 与 MonoBehaviour

TextAsset 优先读取 m_Script 或原始字节；MonoBehaviour 依类型布局读取，不扫描全部可解码串替代字段。
ScriptableObject、场景表、本地化键和运行时加载调用共同决定来源与顺序。
Utage 的 book/event/command 结构、Naninovel 的对象与本地化记录分别按对应格式解释，不能互套。
Naninovel 的独立规则见[naninovel.md](naninovel.md)。

## Bytes 与字段编码

bytes 可为记录表、引用池、偏移键变换或原生字节码；先确认头、表、字符串字段及调用。
偏移键按原始源位置消费，串内零字节和前置字段不能在变换前删去。
结构字段类型可能随序列化版本改变；字符串与字符串数组分别读取，不按字符迭代整句。
负描述符可冗余表示 UTF-8 字节长，如 `descriptor=-(byte_length+1)`；字符数和字节数独立核对，不把描述符当字段类型。

## UTXT

UTXT 头包含版本与 data_off，头部加载分块表不天然是消息页表。
已证字符码变体中，低位单字节 t 映射 T[t-1]；双字节映射由 lead、trail 计算，T 来自对应 chartable。
码表中的 CR/LF 可能占位，不能先去换行再平铺。
0x00 等文本换行与脚本的打印、等待和行尾命令分离，点击页界由消息调用确认。
词条壳、姓名槽、缩进和自定义字体按实际语法与字形解释；不复制固定 chartable 值。

## 自研记录与文本 DSL

| 格式 | 定位与消费 |
|---|---|
| CSR1.00 | 头及 label/offset 表定位代码，按 u16 opcode 读取对应操作数 |
| TKG | `int16 cmd,int16 size,params`，size 含四字节记录头 |
| SSCN | 沿 TextAsset 字节、Coder.Decode 和文本字段读取路径确认变换 |
| SET_TALK / CHOICE 型 | 正向解析引号、顶层逗号及关联 CSV；按参数名或位置取真实字段 |
| Message_CL 型 | 按消息块与字段语法读取，不将整个文本块视为一条显示 |
| @talk / @hitret 型 | 追踪消息起止、choice 参数及可见 name；后台 real 不覆盖匿名名札 |

JSON、CSV、宏和原生命令同样需要调用与字段依据。资源 hash、对象数量、TextAsset 数或物理行数不直接等于剧情顺序与点击数。
