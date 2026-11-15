# 归档、容器与参数

## 容器与读取

格式族见 [归档族](archives.md#归档族与变体)，偏移异常见 [归档变体](archives.md#基址与记录范围)。
以下参数限对应资源；复用已有解包源和通过记录。

### 遥か：表引用与内联

[格式资料](engines/koei-cdar.md#文本与表引用)。

### Zerodiv：压缩与变体

[格式资料](engines/zerodiv.md)。

### CRI CPK ITOC

`EnableFileName=0`、TOC 为空而 ITOC 存在时，
合并 `CpkItocL/CpkItocH`，按 ID 和已证存储顺序，
从 ContentOffset 按 Align 累加 FileSize。
FileSize 是磁盘长度，ExtractSize 是解压长度；不能用 ExtractSize 切压缩成员。
压缩算法按成员头及实现确认，不仅比较两种长度。
总长度闭合检查漏项和对齐，不独立证明顺序正确。

### LiveMaker VF 与 RAR SFX

[格式资料](engines/livemaker.md#vf-归档)。

### VividColor 与 FORIS PACK

[格式资料](engines/vividcolor.md)。

### Director

[格式资料](engines/director.md)。

### SWF 与 DefineFont2

[格式资料](engines/air-woga.md)。

### Access 数据库与日文 DSL

`Standard Jet DB` 头及 VB/Jet 运行库可定位 MDB。
`access_parser` 返回按列字典；若库把原 CP932 字节按 latin1 暴露，
确认后用 `latin1 encode→CP932 decode` 恢复。
BOY×BOY 的 `ScenData.mScena` 为 DSL，`sSceID` 提供场景 ID，`sTitle` 可为作者注记。

`台詞/文字/名前/選択/献立` 按命令分类；
`待つ:0000` 为点击等待，WAVE 或数值参数可为语音或时间等待。
不能将所有“待つ”都作点击。
名字按显示状态关联，掲示板或邮件的 MENU/DATA 字段按显示结构读取，保留叙事资料。

## 归档族与变体

通用归档见 [主册](archives.md#容器与读取)。以下为已知格式定位，参数限对应作品。

### CPK 与 CRILAYLA

PsychicEmotion6 的 TOC FileOffset 解析曾整体偏移 1000(hex)。
先核对 ContentOffset、TocOffset、Align 和参考实现采用的基址；
只有确认本作连续存储后才按条目顺序累加，不能普遍忽略目录 offset。

CRILAYLA 从尾部反向解码，100(hex) 字面块放输出头部；
长度含 2/3/5/8 位扩展。复用完整实现并核对声明长度、真实消费及脚本魔数，
不将旧简化实现的失败解释为加密或数据损坏。

### PSARC

爽海バッカニアーズ的块表 size0 对应零字节而非默认整块。
通过 entry 的 offset、firstBlockIndex、成员范围及内容核对解释，
`scripts/psarc_extract.py` 可复用本作判定。
匹配次数只定位候选，不能以最多命中直接确认全部条目。
解压异常记录失败成员和影响范围，不静默跳过后宣称完整。

### ROM2/SNR

[格式资料](engines/rom2.md)。

### 学園K：串联 ZIP 与 SCD

[格式资料](engines/dat-pak-scd.md#容器)。

### MARGINAL#4 表字节序

dbXlsSelect 为 LE，dbXlsIPSelect/dbXlsSkitterSelect 为 BE。
由脚本引用、键、字段和串起点确认，不按目录统一字节序。
NUL 前界及双向引用集合用于覆盖核对，首键可能位于头部；
解释未引用和重复引用，按表用途确定覆盖要求。

### ハイカラ LZS

[格式资料](engines/lzs-scd.md)。

### Koei PS2 HD/BIN 与 PACK H2

[格式资料](engines/koei-pack-ps2.md#pack-头)。

## 基址与记录范围

WSC 旋转见 [专册](archives.md#wsc-操作)，结构见 [AdvHD](engines/advhd-wsc.md#指令变体)。

### LIBP 基址与块单位

[格式资料](engines/malie.md)。

### STCM2L 导入编号平移

[格式资料](engines/stcm2l.md#调用与文本分类)。

### 指令布局与链检查

PSV 可为 `isCall/opcode/nparams/length＋nparams×三字段＋data`；
其他 STCM2 变体有 `size＋payload`。以头字段和导出区确认代码边界，
不能仅因 size 异常就判平台布局不同。
PSV 局部指针可指向 `0,L/4,1,L,text`，固定 payload 偏移限对应变体。

Koei pasc 的记录流可从20(hex)开始。
从头部、索引或参考实现取得起点，按节点长度消费并验证范围、对齐和终止；
“恰好到 EOF”不能独立证明布局，也不枚举所有起点后择唯一命中。

### UNI2 前缀与跨成员数据

[格式资料](engines/stcm2l.md)。

## WSC 操作

### WillPlus 归档

扩展名组表为 `u32 extGroupCount`，各组 `ext[4], count, tableOffset`。
WSC 条目 `name[13], size, offset` 为 21 字节；ANM 等组可能不同，按扩展名组布局解析。

WSC 逐字节 `rotl_8(c,6) = (c<<6 | c>>2)&0xFF`。
解密前的规则字节不证明明文，核对签名、结构及完整解码。

### 指令与选项

已证变体 `op41` 为旁白、`op42` 为姓名与台词、`op02` 为选项。
版本间指令长度不同，核对 opcode 表及真实终止；完整消费不代替语义验证。
工作区可复用 `scripts/advhd.py`，本作驱动按版本配置。

选项为 `2B + text\0 + 3B头(01 XX 03) + 目标指令`。
目标可能为 `07 script\0` 或 `06 <5B>`，须按目标 opcode 消费，不能固定跳四字节后读字符串。

### 输出

核对实际 `%K%P` 等等待、翻页和排版标记。字面 `\n` 为排版转义；演出空项不生成正文。
电话、邮件的名札按可见性关联，不直接删除。原文括号笔误保留并记录，不能按作者意图猜改。
姓名输入菜单存在不证明正文使用姓名宏，外部 Nameable 标记不证明槽位存在。

### 前缀区与范围

子文件可为 `前缀区 + 脚本`，前缀可能有小测、结局、姓名表及 UI。
主代码外的候选按记录、调用及显示用途分类，不整块收取或排除。
外层容器也可能有同格式脚本，核对来源避免漏收或重复。
前缀大小和记录流边界见 [变体](archives.md#基址与记录范围)。

## CRI 与 KAG 块流

### 块与文件

CPK 数据可为逻辑串接流再切块，文件边界不必与压缩块一致。
CRILAYLA 头、声明长度及内容共同验证，TOC 等式成立不单独证明条目一一对应。
已证变体按 ContentOffset 解压或读取 2048 字节块，再按独立文件标记切分逻辑流。
文件首行注释可能前有换行/NUL 填充或附注，不能只锚定行首完整文件名。

### CRILAYLA

u32@8 的 usize 不含 0x100 原样前缀。
变长计数阶梯为 2、3、5、8 bit，末级 FF 继续；固定八位读法可造成中途越界。
参考实现须支持 ReverseStream、长度阶梯及原样前缀，验证完整消费、输出长度和已知内容。

### TOC 变体

偏移可能与条目错位，但长度匹配或整体平移只定位候选。
以块内身份、资源引用及完整结构确认，不盲取下一行偏移。

### KAG 输出

共用扫描、宏与页状态见 [KAG](engines/kirikiri.md)。
已证自定义 message 块经实际等待/清屏确认显示单元，块内 br 为排版。
selectb 的 word 参数按剧情位置输出，姓名宏先求值再剥样式。
next 链可能碎片化，顺序以入口、调用及独立场景信息核对，不默认文件名排序。
原文姓名异称不能因名札表无此名而改字。
