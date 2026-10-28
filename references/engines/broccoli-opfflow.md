# Broccoli 自研指令流（Switch / うたプリ 系）

**识别特征 → 容器链路 → 脚本记录 → 成行 → 易错**

## 识别
- Switch NSP，RomFS 根为 `1/*.cpk`（CRI CPK）：`anm/bg/ci/data/novel/lesson/rhythm/start/title.cpk`
- `novel.cpk` 内为 `DATA01..DATA13/xx_Story.dat`，本体无容器、无压缩
- 文件内**大量 `0xFF`**，且文本区字节呈 `7C–7F` 开头的两字节对（其实是 SJIS 取反）
- 厂商旁证：BROCCOLI（うたの☆プリンスさまっ♪ 系列）

## 容器链路
1. `nsp_split.py`（PFS0 直拆；nstool 的 `-x /` 在 Git-Bash 有路径转换坑）
2. Program NCA：**Key Generation 14** ⇒ 旧 hactool(2020)、hactool 1.4、`keys.txt` 全部 `Invalid NCA header`
   ⇒ `nstool -k merged.keys -t nca --titlekey <tik[0x180:0x190]> --part1 <out>`；
   keyset 常缺 `key_area_key_application_0e`，只能走 Titlekey crypto
3. `cpk.py` 解 `novel.cpk` / `data.cpk`

## 脚本记录
```
ff <op> <u16 id LE> <u16 b> <u16 c> [载荷]
0x0A  头 12B，文本样式 id：0x00CC 续行 / 0x07DE 段首 / 0x00D5 主角名槽
0x00  头 4B，无样式文本
0x0E  id 0x0074、头 16B ⇒ 选项（前置 0e/0003，后置 0e/0072 收束）
id 0x07DD（任意 op，头 12B）⇒ ruby 文本：[基底][00 00 或 ㌻][基底+正文]，取后半
```

## 文本编码
**逐字节 XOR 0xFF**，再 cp932：
`raw 7e8a → 0x8175 「`、`raw 7ebd → 0x8142 。`、`raw 7d4e → 0x82B1 こ`
- 尾部填充 raw `00`（取反即 NUL）
- 正文中 raw `0x01` 等控制字节 ⇒ 解码时一律跳过（否则产出 `〔FE〕` 伪影）

## 成行（L0）
- **框结束 = `op0A + id 0x00CC + 空载荷`**（随后固定 `op08/0400` wait）→ 一次点击一行
- 选项 `op0E/0x0074` 单独成行（先冲掉当前框）
- `0x876E`=㌻＝框内**改行**（换行≠换页，合并）；`0x32A4–A6`=㊤㊥㊦＝演出标记，剔除

## 主角名
`op0A/0x00D5`：**每个框内第一次出现**才插名字，其载荷是「名字之后的文本」；
同框后续 0x00D5 只出载荷（否则「春歌春歌」）。默认名在 `main` 的 cp932 串表（本作 0x179d67）。

## 易错
1. 旧 hactool 不支持 KeyGen14，别在工具上耗时间
2. 把 XOR-SJIS 误判成「自定义码表」而去建表（`0xFF` 取反即可，一条 `「」` 明文即可锚定）
3. ruby 记录（0x07DD）会**重复基底**，不去重会出「良きライバル良きライバル」
4. 把 `data.cpk` 的 `memorial*.dat`（回想）当正文收进来
