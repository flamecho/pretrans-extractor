# Director · Afterburner

## RIFX / Afterburner

RIFX 类型 FGDM 为电影、FGDC 为外置 cast；MV93 可为未保护电影的 imap/mmap 布局。
Fver 由 varint 长度和版本字段组成。Fcdr 解出压缩器 MoaID 与描述，按类型选择实现。
ABMP 的 varint 表包含资源 ID、偏移、压缩/原始大小、类型与 FourCC；FGEI 后为 ILS 载荷基址。
ILS 中的资源按 `resId + 声明长度` 读取，外置块按相对基址定位；ziplib 与 SWA 等类型分别处理。

## 文本使用

KEY*、CASt、CAS*、Score 与 Lingo 引用决定文本成员如何显示。
文本池、字段成员和注释不等于有效剧情；按实际脚本与帧引用读取显示序列。
