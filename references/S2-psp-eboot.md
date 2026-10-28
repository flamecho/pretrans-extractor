# PSP `~PSP`（EBOOT.BIN / PRX）解密 ＋ ELF 反汇编入口

> 解密总览见 `S2-decrypt.md`。

## 1. ★ PSP `~PSP`（EBOOT.BIN / PRX）解密 —— 标准路径，别自己造（2026-10-14，裏語 薄桜鬼 两作）

PSP 的 `EBOOT.BIN` 多为 **`~PSP` 加密 PRX**（magic `7e 50 53 50`，`mod_name` 如 `URA`），
**VM/脚本解释器就在里面** ⇒ 不解它就永远读不出 opcode 语义（只能靠猜）。
- 工具 **`pspdecrypt`**（John-K/pspdecrypt，代码源自 PPSSPP＋libkirk）：
  `scripts/pspdecrypt/pspdecrypt.exe EBOOT.BIN` → 打印 `tag D91613F0 with type 2`，产出 `EBOOT.BIN.dec` = **MIPS32 LE ELF**。
  **免密钥**（KIRK command 1 的 IPL 密钥是公开的）。
  ⚠ 直连 `github.com/.../releases/download/...` 常被墙 ⇒ 走 `api.github.com/repos/<o>/<r>/releases/assets/<id>`
  （header `Accept: application/octet-stream`）。
- **定位**：ISO9660 列 `PSP_GAME/SYSDIR/EBOOT.BIN`（偏移 = LBA×2048）。头长可由
  `EBOOT.BIN 大小 − BOOT.BIN 大小` 反推（实测 `0x157`／`0x158`）；`0x2C` 字段 = 文件总大小。
- **拿到 ELF 后**：capstone（`CS_ARCH_MIPS`+`CS_MODE_MIPS32`+`CS_MODE_LITTLE_ENDIAN`）或 rizin。定锚顺序：
  ① 字符串交叉引用（`lui`+`addiu/ori` 装配地址）→ ② 「结构相同的极小函数串」多半只是 sprintf 包装
  ③ 找文件 I/O 层 → ④ **由「读条目」函数的 `bit31` 分派找到解压器**（本例 LZO1X）。
  ⚠ 别用「switch 分派表」盲扫 —— C++ 虚调用与 `jr $ra` 会淹没候选（本会话在这种扫描上耗了数轮）。

## 2. ★★ 先看 `SYSDIR/BOOT.BIN` —— 它常常是**明文 ELF**，省掉整条解密链（2026-10-16，étude prologue PSP）
`PSP_GAME/SYSDIR/` 里通常有**两个**启动文件：`EBOOT.BIN`（`~PSP` 加密）与 **`BOOT.BIN`**。
**本作 `BOOT.BIN` 的 `head -c4` ＝ `\x7fELF`（明文 MIPS32 ELF，比 EBOOT 小 ~300 B＝少了 `~PSP` 壳头）**
⇒ **根本不需跑 `pspdecrypt`**。开工第一步就该 `file`/`head -c4` 两个都试，别默认必须解密。
- ⚠ 并非所有 PSP 作都如此（裏語 薄桜鬼 两作的 `EBOOT.BIN`/`BOOT.BIN` 皆 `~PSP`）⇒ **逐作实判，不按厂牌推定**。
- ★**第三种情形：`BOOT.BIN` 是「全零的假文件」**（ラブレボ!! Portable 3,926,912 B 全 `00`，`strings` 0 条）⇒
  这种占位文件**不含任何代码/串表**，必须回头解 `EBOOT.BIN`（`pspdecrypt.exe` 免密钥，仍可拿到 ELF 的
  `res/...` 资源名表与**名字表**：本作 `0x1e35d0` = `ヒトミ/桜川/＊Ｂ/一ノ瀬　蓮/…`）。
  判据：`BOOT.BIN` 尺寸与 `EBOOT.BIN` 只差壳头（300~400 B）但内容全零 ⇒ 直接走 EBOOT。
- **明文 ELF 的廉价金矿（照优先级查，全在 `.rodata` 串区）**：
  ① **引擎的脚本/事件名表** —— 成片的 NUL 结尾名，**4 字节对齐、字段 `(len+1+3)//4*4` 步进**；
     表尾常转成**另一类**（如 `*.BMP` 名表）。**判据＝表的起始名紧邻一个「原生函数名字符串」**
     （étude prologue：`… EVENT_CHECK / NOW_LOAD_OFF / data/bmp/AFF/MASKLR.msk / M_HTM_01 …`，起点 `0x6edf8`，
     紧跟在 `GET_SCRIPT_NAME` 之后）。⚠ **表内可能有小写变体**（`S_MDR_01_a` vs 包内 `S_MDR_01_A`）⇒ **匹配大小写不敏感**。
  ② 名表/槽表/默认名/码表；③ 主循环与 I/O 层。
- **对「非线形（日历/模拟）作」，这张表就是唯一的顺序依据**：`0x1e/0x1d` 调用图往往只覆盖
  开篇/结局/日常系统，剧情事件由原生 `GET_SCRIPT_NAME` 依该表动态派发 ⇒ 见 `pitfalls/B-lines.md`。
