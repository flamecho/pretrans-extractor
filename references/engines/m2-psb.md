# M2 · PSB / MDF

## PGD / MDF / PSB

PGD 头 `00 50 47 44`，+4 为 key_index、+8 为 drm_type；先解 body 再按索引切成员。
MDF 包装可需 MT19937 变换后 zlib，PSB 则读取索引、字符串、场景和属性树；先查签名，不能统一套 MDF。
fileinfo.psb 的索引可分别用字节偏移或 LBA/size，单位由记录形状与消费者确定。

## 键与校验

PGD 的 MAC_80 比较对头 0..80h 的 MAC 与 80h..90h 字段。
CMAC 的完整末块仍须留在末块处理，不能因模 16 为零就跳过。
MDF seed、PSB 键及 PGD 材料取自匹配配置或加载器，不保存作品键、固定长度或主程序定位地址。
文本按 PSB 的实际显示引用读取，资源树中存在字符串不等于剧情。
