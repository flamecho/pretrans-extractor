# orfre-dcvm 探查史（失败路线 / 锚点 / 标尺 / 推导）—— 仅排障时读

主档：`orfre-dcvm.md`（容器 → 解密 → 脚本结构 → 成行 → 工具）。本文件记录**结论之外的推导过程**，防止重复走弯路。

## H1. 行序：全部失败路线（勿重试）
根因（最终查明）：`STR` 池**按类型分组存放**（`6..39` 旁白 / `42..52` 心声 / `53..88` 对白 / 其后资源名 / 符号名 / 语音 / 裸章题 / 选项），
所以任何「按池序遍历」的静态序都不是显示序。以下路线均已实测无效：

| 路线 | 实测结果 |
|---|---|
| `<id>;STR` 首现序 | 递增比 0.993 = 按池序遍历（注册），非显示序 |
| CFG 访问序（`scripts/orfleur_trace.py`） | 同样呈池序 |
| 按 funcid 分组取序列 | sorted-ratio 0.55–0.88，均无序 |
| 8 字节步长链 | 少数真链（chunk377 `0x2e14` 起 `71,8,52,46,90,88,91`）存在，但不可靠分离 |
| `STOR` 分段 | 95 个递增检查点地址（多落 `PUSHIB`），分段取文本仍乱序 |
| 线性走链 `scripts/orfleur_vm.py` | 408 语句 / 68 去重 / 最长不重复窗口仅 9 行 ⇒ 多分支共享行块 |
| 语音 id 定序 | 语音引用序与 PC 语音序不符（ad1092 反复出现） |

⇒ **正解是 `STBL`（见主档 §6）**，不需要 VM 解释器。

## H2. 调用约定推导（2026-10-11）
- 约定 = `<args…>; PUSH <nargs>; PUSH <funcid>; CALL|PCALL`（`SYSCALL` 同构）。`nargs` 位置值多为 1/2/3 小整数，末位才是函数号。
- **funcid = 本块 FTBL 索引** ⇒ 同一数值在不同块＝不同函数（此前「函数名对不上」的困惑由此解开）。
  例（chunk377）：`FTBL[1]=orfre_text_open`、`[5]=orfre_text_set_name`、`[7]=orfre_text_start`、`[21]=puppet_universal_transition`、`[23]=puppet_voice_play_all`、`[35]=setCurrentScene`、`[39]=setSummary`。
- 场景主例程形态 = `PUSHIB n; STR; PUSHIB 1; PUSHIB 21; PCALL; PUSHRET; PUSHIW <下一行>; JMPF`，n 递增 ⇒ **按池序枚举注册**，不是显示序。
- 易错点：funcid 的小整数也落在池索引范围内，会被误当文本参数 ⇒ 取参必须用「紧邻 PUSH 序列」。

## H3. PC 版汉化补丁 = 完整剧情序标尺（2026-10-11）
> 定序已由 `STBL` 解决，本标尺**转作交叉验证**用（PSV/PC 行数比 1.00）。

- 来源：用户博客 `flamecho.top/posts/118` → GitHub `flamecho/flamecho-translation-patch` → `乙女向/补丁/[PC-JP]オルフレール[20250302].zip`（1 MB）。
  **下载通道**：`raw.githubusercontent.com` 被墙 ⇒ 走 `api.github.com/repos/<owner>/<repo>/contents/<urlencoded path>`，响应带 `content`(base64)（<1 MB 可直接取）。
- zip 内 = `additional.xp3`。**XP3 结构**（本包变体）：magic 11 B `58 50 33 0d 0a 20 0a 1a 8b 67 01` → u64 index_off（0x0F73B7）；
  **index 区与所有段均为 zlib**；index 解压后 = `File`(4)+u64 size + {`info`(4)+u64 size+`[u32 flags][u64 orig][u64 comp][u16 namelen][name UTF-16LE]`，`segm`(4)+u64 size+n×`[u32 flags][u64 off][u64 usize][u64 csize]`，`adlr`}。本包 254 文件（252 `*.snr` + 2 ini）。
- **`.snr` = UTF-16LE KiriKiri 脚本**（不是 ROM2/SNR！）：指令行（`インフォメーション("章題")`/`音楽再生`/`背景`/`トランジション`/`前景`/`f.CC08="sa1_"`，行尾 `;`，`//` 注释）＋ 文本行。
  文本行形态：旁白 `　正文`；对白/心声 `【名札】(语音id)「正文」`，`\1`＝主人公名宏，`//話者名:アデル→？？？`＝隐藏名注记。
- **语音 id 跨版本同名**：PC `(AD1092)` ↔ PSV `ad/ad1092`；`OW_SA0190` ↔ `ow/ow_sa0190`（集合实测全等）。
- 工具/产物：`scripts/pc_snr_order.py` → `_work_orfleur/pc_order.json`（252 场景 / 33,293 行 / 8,300 行带语音）；PC 脚本在 `_work_orfleur/pc_snr/`。

## H4. 归一化实证
- 池内 `<a>(X)…`：`<a>` 是属性标签，**括号里的 X 就是要绘制的开括号** ⇒ `<a>(「)…」`→`「…」`、`<a>(（)…）`→`（…）`。**不能只删标签**（否则残留 `(「)`）。
- 实测输出：`（フィル様……いったいあなたの心はどこにあるのでしょうか……）`、`「クレア? どうしたの?」`。
- `<name>(0)`＝主角名宏 ⇒ 替换为 `クレア`（铁律 13 主角名出现性自检）。
