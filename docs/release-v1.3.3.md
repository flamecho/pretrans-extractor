## v1.3.3 —— 索引要能查得到

v1.3.1 做出了「引擎 → 可改的脚本」表。用起来发现两个洞：**有的引擎册根本不在表里**，
**有的脚本在表里只有一个「—」**。

### 修正

| 问题 | 影响 |
|---|---|
| `otomate-vm` / `psv-pfs` / `zerodiv-talks-variant` 三册在「按引擎」表里**整行消失** | 命中这三个引擎的人会以为索引漏了 |
| `zerodiv-talks-variant` 没写工具引用 | 包里本就有 `vn_zerodiv_extract.py`，却查不到 |
| `corda_2fa_get.py` 的用法写错名字 | docstring 里是 `corda2f_get.py`（少个下划线），照抄即报「找不到文件」 |

现在「按引擎」表**覆盖全部 78 册**：有脚本的列脚本，没脚本的明写

> —（无现成脚本：按本册的容器链路 / 记录形状自己写）

空着和不存在是两件事，前者能让人继续往下走。

### 21 个脚本补了用途说明

`cdar` / `scan_jp` / `scan_nested` / `scanjp` / `sjis_scan` / `unity_scan` / `unity_scan2` /
`pe_dis` / `period55` / `fullscan` / `lztest` / `renderfont` / `vn_memdump` / `libp_malievita` /
`npa_nrbf` / `pandora_dbg` / `rear_extract` / `himehibi_scan` / `hanayoi_afs` / `hanayoi_run` /
`cdar_extract`

它们此前没有模块 docstring，索引第二栏只能显示「—」。现在 **250 个脚本全部有用途**，扫一眼就知道该不该用。

其中几个其实挺常用，只是名字看不出来：

- `scan_jp.py` —— 目录级扫描，按「连续假名 run 多」排序，先圈定正文在哪个文件
- `unity_scan.py` / `unity_scan2.py` —— Unity 资产里的日文检测（前者试三种编码，后者直接按 UTF-8 字节匹配）
- `fullscan.py` —— 逐个归档条目试解压，按含日文字数排序，找正文在哪一层容器
- `renderfont.py` —— 字库图集渲染成 PNG，人工目视确认字形

### 一条维护规则（写进 `06-discipline.md`）

阶段册与引擎册允许共享「锚点事实」（NCA 块头字段、`hactool` 命令行、Unity 解包步骤）——
两处各写一次是为了让每一册都能**独立读懂 / 独立执行**。

实测重复量其实很小：最长连续重复 207 字，其余多是共享术语，不必强行合并。
真正的风险只有**改一边忘另一边**，所以改这类句子前先 `Grep` 关键词确认另一处。

### 升级方式

替换整个目录。本次不改任何提取逻辑，索引与说明更完整而已。
