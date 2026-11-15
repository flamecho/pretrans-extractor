# 编码与还原案例

## 解码案例

仅在相应问题出现时读取，通用解码见 [基础](decode.md#字段与编码)。

### 加密与包装

SQLite 可直接读取，文本列为 CP932 时用 bytes text_factory 保留原字节。
压缩流包含明文字面量，不证明未压缩；按压缩标志、声明大小及真实解码器确认。
WSC 旋转解码见 [专册](archives.md#wsc-操作)。

### 码表

自定义 kana、PUA 和符号槽不能直接套 CP932 或按上下文猜标点。
查 [ELF 表](decode.md#elf-码表) 与 [字体](decode.md#自定义字体)。
槽序单调只在已证排序规则中限定候选，字体和上下文冲突继续查证，不据文脉改字。
KONAMI 池内偏移键与零字节还原见 [字节码](engines/unity.md#自研记录与文本-dsl)。

### 表与资料

定长插入表以已知槽及地址核对基址，宏和姓名见 [专册](names-and-macros.md#宏与动态文本)。
.NET #US 字符串堆也可含辞典，按实际引用及显示用途取舍。
未在正文搜索到词条不证明他作遗留，元数据表与脚本表可能含不同范围。

### 归档

文件边界、块对齐、字段独立混淆及前缀区均按变体确认，见 [归档](archives.md#容器与读取)、
[同族差异](archives.md#归档族与变体)、[偏移变体](archives.md#基址与记录范围)。
子文件越界先查布局与独立连续流证据，不默认放宽终点。
压缩长度、消费及已知内容共同验证；小文件通过不证明大型压缩流正确。
尾部长度可能按位取反，零长度也可能是合法空成员。Switch 解包见 [平台](platforms/switch-nca.md)。

### 脚本

定义区可能含文本形态和命令码，不从首个日文候选直接认定代码起点。
按真实区段、指令头及引用消费，opcode Δ 只定位候选，不按平均串长分类。
源码与编译体同捆时核对有效版本及实际调用，语句数近似不证明源码未过期。
gss SCR2 已证变体的 108 为槽赋值、106 为清槽、3a 为 OR；仍按本作表核对。

### Unity

优先已支持对象及 schema，无 typetree 时才核对原始对象布局。
TextAsset、MonoBehaviour、StreamingAssets 和程序集均可能存文本，见 [Unity](engines/unity.md)。
序列化头、明文版本串及零对象结果只提示包装异常，不证明未加密或不存在正文。

### Director

[格式资料](engines/director.md)。

### NScripter 位图台词

[格式资料](engines/nscripter.md)。

### DDEngine 原生实现

[格式资料](engines/ddengine.md)。

### Unity 头异常

[格式资料](engines/unity.md#自研记录与文本-dsl)。

## 编码与成行案例

按 [解码](decode.md#字段与编码) 选择方法；下列参数限对应作品和变体。

### 文本载体定位

| 格式或作品 | 定位 |
|---|---|
| O＊G＊A 鬼ごっこロワイアル | `MComprHD` 为 CHD 外壳；`identify.py` 输出须由魔数和解出结构复核 |
| PSPFS_V1 / TOB | `DATA.DAT` 可为媒体，`STS.DAT` 的 TOB 字符串表含正文 |
| Lucian Bees | 同容器可有多个独立 `u32 n + 偏移表` 块，逐块分类覆盖 |

没有假名命中不能证明无文本。先按索引、魔数、引用及已知变换定位，
不为确认媒体组而解压全部成员。XOR 键由已知明文、源码或已证同作参数确定。

本册所述 `0xDA` XOR 变体用半角片假名存平假名、全角片假名存原片假名。
仅在确认该编码后转换半角区并合并浊点、半浊点；不跨作统一转换。

### Lucian Bees 标签与串覆盖

[格式资料](engines/hunex-ika.md)。

### LOVE＆PEACE 字节移位

[格式资料](engines/lovepeace-adv.md)。

### ラブレボ HuneX Ogre 字形码

[格式资料](engines/hunex-ogre.md#字形码变体)。

### Solomon's Ring PCT 变体

[格式资料](engines/planpeace-pct.md)。

### PSCB 字符串池与 NK/PAF

ラストエスコート PSP 的 `PSCB` 为指令区加 NUL 串池；
`11 00 30 10` 与 `$k` 结束串、`36 00 20 10` 与无 `$k` 独白分别形成计数对应。
计数一致只能验证覆盖，池序是否为显示序仍需确认读取方式与调用；
已证顺序消费的实现可复用，不必重复逆向。

无 `$k` 串也含回想标题、摘要及独白，按对应命令分类。
姓、名可分两槽存储，不能与正文里的字面默认名重复冠名。

NK 头字段为 `u16 count@0x02`、`u32 hdr@0x08`，
条目 16 字节 `[compSize][uncompSize][nameOff][dataOff]`，数据对齐 `0x800`。
由 hdr 定表起点；本作首个 `nameOff=0x14+count*16`。错读字段可能仍解出部分偏移，
须核对索引、名称及内容。7z 无法读取正常 ISO 时复用 ISO9660 walker，
PVD root 字段位于 `0x8000+158/+166`。

### KID 页尾与名字宏

[格式资料](engines/kid-cp932.md#文本与控制)。

### PCT 多串、填充与重复候选

[格式资料](engines/planpeace-pct.md)。

### XTX 名札覆盖

あさき、ゆめみし的 `spt/charaname.xtx` 仅覆盖具名角色；
脚本另有泛用身份、`―――`、平假名集体名及 `・` 连接的合署名。
按名札字段和显示调用补全类别，可见标签关联对应正文。
`短前缀＋引号` 词频仅作候选定位，不按汉字、假名或出现次数决定名札。

### TOB VM 与 EVB 前向解析

[格式资料](engines/tob-dsarc.md)。
