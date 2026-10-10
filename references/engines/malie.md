# Malie System（Camellia LIBP / MalieVita / AlphaROM）

> 路由 / 一句话索引见 `../engines.md`。

## Malie System —— GreenWood（OmegaVampire repack 实证；Camellia 系）

- **识别**：游戏根 `malie.ini` + `as.ini` + `maliesetup.dll`；exe manifest 含 `GreenWood.Light.malie.exe`。
- **外层容器**：本作以 **WinRAR SFX**（WinRAR SFX module）封装，内嵌 **RAR5**（签名 `Rar!\x1a\x07\x01\x00` @ `0x48E00`，无加密、Solid）。
  7z 可直接 `x` SFX，或按偏移切出 `.rar` 再解。资源：`data/{game,cg,voice,sound,movie}.dat`、`system/exec.dat`。
- **资源归档 = LIBP（Camellia 加密）**：
  - 头 `LIBP` + `u32 entry1_count` + `u32 entry2_count` + `u32 unk`（整体加密，熵 8.0）。
  - 之后依次（**全部同样加密**）：`entry1[count1]`（32B/条：`char name[20]` + `u32 flags` + `u32 offset_index` + `u32 length`）、
    `entry2[count2]`（`u32 offset`，单位 1024B）；数据区基址 = 表后 **1024 对齐**（v2；v1 为 4096）。
  - `flags & 0x10000` = 文件，否则为目录（目录的 `offset_index`=entry1 起始下标、`length`=条数，递归）。
    文件真实偏移 = `base + entry2[offset_index] * UNIT`。
    ⚠️ **UNIT 不固定**：PC 版多为 1024，**PSV 版 MalieVita = 2048**（exdieslib 亦注明「Maybe a bug」）。
    判据（秒级）＝`max(entry2) × UNIT ≈ 文件大小`；取错会**整体错位**成「隔一块明文、隔一块化け」的假象。
    自适应 1024/2048/4096 已补进 `scripts/malie_extract.py::read_libp`。
  - 解密 = **按 16B 块整块解密**，`DecryptBlock(block_offset)` 依赖绝对偏移（块内位移参与轮数），故支持随机访问。
- **Camellia 解密（asmodean exdieslib 版）**：20 组**预计算密钥调度** `KEYS[20][56]`（非 raw key），
  自实现 Camellia-128 轮函数 + 4 张 S 盒，外加每块「按偏移旋转 + 半字节交换(mutate)」。密钥靠**试用**匹配：
  解密首 16B 得 `LIBP`/`LIBU` 即命中。
  - **OmegaVampire repack 命中 index 11**（该槽在 exdieslib 中以《オメルタ～沈黙の掟～》命名；表 20 组覆盖 OmegaVampire/Omerta/Dies irae/神咒神威神楽 等 Camellia-Malie 家族）。
- **剧本 = `system/exec.dat`（明文，非归档）** —— 编译后的 Malie VM 脚本：
  ```
  u32 全局变量数 → N×{ u32 名长(hi bit=flag) | UTF-16 名 | 递归类型链(u32 flag;≠0→跳4再递归) | 4×u32 }
  u32 跳过1 | u32 函数数 → N×{ u32 名长 | UTF-16 名 | u32 id | u32 res | u32 codeOffset }
  u32 标签数 → N×{ u32 名长 | UTF-16 名 | u32 codeOffset }
  u32 VM_DATA大小 | VM_DATA        （内联 tag/标签字符串，UTF-16）
  u32 VM_CODE大小 | VM_CODE        （字节码）
  u32 字符串数cnt | STRING_INFO[cnt]{u32 off,u32 len} | u32 表大小 | 字符串表
  ```
  （另有「压缩/加密字符串表」分支：`unk*8 > 剩余文件` 时 unk=压缩长度；本作走普通分支。）
- **VM 指令**（1B opcode）：`0x00/01/02` jmp/jnz/jz(+4B)、`0x03` call(4B id+1B argc)、`0x04` call(1B id+1B argc)、
  `0x08/0x0D` push imm32、`0x09/0x0A/0x0C` pushStr(VM_DATA 偏移 1/2/4B)、`0x11` push imm8、`0x12` push[sp]、
  `0x2D` vCall(4B id)、`0x31` initStack、`0x32/0x33` jmp-short/ret。
- **文本提取**：从 `maliescenario`(函数名，本作 id 0x5D) 的 codeOffset 起线性解析至首条 `0x33`。
  **一次点击 = 一条 `_ms_message`(id 0x2D) 调用**，其栈顶参数 = **字符串表下标**；正文 = `字符串表[vIdx[idx].off : +len]`（UTF-16LE）。
  `MALIE_NAME`(0x48)=说话人名、`tag`(0x23)=`<layer>/<cg>/<chapter …>`、`MALIE_LABLE`(0x31) 等忽略。
- **消息字符串内控制码（2026-10-07 修正）**：**`0x0007 0x0006` = 文本框分隔符（= 一次玩家点击）→ 必须切分成多行** ⚠️
  （首版误当「句尾」直接丢弃，会把同一条 `_ms_message` 里的多个文本框并成一行 —— OmegaVampire 序章曾被并到 309 字）、
  `0x0007 0x0008 <语音名NUL>`=LoadVoice、`0x0007 0x0009`=LoadVoice 结束、`0x0007 0x0001 <本体>0x0A<读音>00`=**注音**（留本体丢读音）、
  **`0x0007 0x000C <id> 0x0000` = 主人公名宏**、`0x0000`=语音名终止/段分隔、`0x000A`=框内软换行（合并）、`0x0007 0x0004`=句内停顿（丢）、`0x0001..0x0006`=内联（跳 4/1/2/1/2/2 字符）。
- **本作结论（OmegaVampire repack）**：34,940 条消息 ↔ 字符串表 34,940 条**一一对应**；
  控制码归零后 30,397 行正文；主人公名宏默认 **マリア**。
  ⚠️ **该 repack 的 `system/exec.dat` 正文实为《断罪のマリア THE EXORCISM OF MARIA》**，而其余资源为 OmegaVampire（混装包）。
- **工具**：`scripts/malie_extract.py` —— 自带 S 盒 + 20 组密钥；`--list/--extract`（LIBP）、`--text`（exec.dat→txt）。

### MalieVita（PSV 版 Malie）—— 英国探偵ミステリア The Crown 实证
- **识别**：PSV pkg → PFS 解密后 `data/dataN.dat` 头为 **明文 `LIBP`**（本作**无 Camellia**，Camellia 只出现在 AlphaROM 加壳的 PC repack）。
  eboot 内含 `malievita` / `MALIESYSTEM` 串；`data/system/{exec.dat, malie.ini}`。
- **LIBP 明文**：`flags & 0x10000` 文件 / 否则目录；**offset 块单位 = 2048**、基址 2048 对齐（见上）。
  数据区**先顺序放明文文本（csv），再放 png/at9**；条带化误解会得到「隔块明文·隔块化け」。
- **exec.dat 与 PC 版差异**：① 函数名/标签名 = **窄字节 ASCII**；② 字符串表 `STRT` = **CP932**。
  结构：`全局变量(386) → 函数(106) → 标签(2733) → VM_DATA → VM_CODE → vIdx[34643] → STRT`。
- **走查判据**：`_ms_message`(vCall `0x2D`,id 45) 调用数 **= 字符串表条目数**（本作 34,643），相等即走全。
- **主人公名宏**：`07 0C <n> 00`（`n` ↔ `malie.ini` `NAME<nn>`）；本作 `InputName=true`＋`NAME01=エミリー`，姓名 = `エミリー・ホワイトリー`。
- **另据本作总结**：`voice.csv`(角色码↔名) 可直接当人名核对表；`malie_t_<章>_<场景>` 是场景标签体系。
- **工具**：`scripts/mysteria_extract.py`＋`mysteria_text.py`＋`libp_malievita.py`。

### Malie 自保护（AlphaROM）＋内嵌剧本资源（OmegaVampire 官方版实证）
- **引擎可把剧本内嵌进主 exe**（不落地 exec.dat）：资源 **类型 `EXEC` / 名 `MalieScenario`**。
  `maliesetup.dll` / `KarinCfg.exe` 里同一「Install 命令」= **按名找资源(13B `repe cmpsb` "MalieScenario") → 建 z_stream → `inflateInit_`（版本串 `"1.1.4"`，zlib 1.1.4）→ 解压写出 `exec.dat`**。
  ⇒ **该资源(解壳后)就是 zlib 流＝真 exec.dat**。辅助串：`ZLibIn_Full %s`、`LIBU`、`getLibSector %s : %d %d`、16B 串 `2JEV~fC],)kv-L]Z`。
- **主 exe 常被 AlphaROM 加壳**（本作包内自带 `AlphaROMdiE-Build20140214` 破解器即证据）。
  识别特征：导入表被洗成「**每 DLL 仅 1 个**」且含指纹 **`GetKeyboardType`**；`.text` 熵≈8.0、无 `55 8B EC`；段名被改坏（`.data\x009\t`）；大块原数据搬进 `.data9` 类段；有 `.detour` 段藏**原 PE 头副本**。
  `AlphaROMdiE.exe` 用 `CreateProcessW`+`WriteProcessMemory`（**运行时内存改写**），**不能静态脱壳**。
- **⚠️ 取证铁律：exe 内的资源目录可能是「诱饵」**——多个资源的 rva/size 区间互相重叠即证（被壳虚拟化）。
  加壳后**不可按 rva 直读资源**；且 FIXED：`\x89PNG/IHDR/OggS/g_index/MALIE_NAME` 全 0，`78 xx` 位置 zlib 全败，raw-deflate/XOR/ADD/SUB/Camellia(20 键) 全不通 ⇒ **资源数据确被加密，纯静态拿不到**（只有 Windows 标准资源 MANIFEST/VERSION/ICON 明文可读）。
- **正规取法（本次已成功）——运行时内存转储**：
  1. 启动游戏（**必须在交互式桌面**；沙箱/无桌面环境启动会 exit 0、无窗口、无子进程）。
  2. `OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ)` + `VirtualQueryEx`/`ReadProcessMemory` 全量转储（本作 769 区域 / **338 MB**）——**不结束用户进程**。
  3. **定位脚本缓冲区**：找变量表特征 `u32 0x80000012 + UTF-16 名`（如 `g_index1`）或已知角色名；本作脚本在 **VA `0x74e000`, size `0x4d1000`**（另有同内容副本 @ VA `0x6680000`），**脚本起始 = 该区域偏移 `+0xc58`**（其前 0xc58 字节是引擎另一段数据）。
  4. 用 `parse_exec` 从该偏移解析（格式自带严格校验 → 可**逐偏移试探**自动定位起点）。
  5. **完整性验证**：`walk_script` 取到的消息数应 == 字符串表条数、下标互异且无未引用；再对**全部函数**分别反汇编取并集比对（本作 21,568 == 21,568，0 未引用）。
  - ⚠️ 引擎内建函数名字符串（`MALIE_NAME`/`_ms_message`/`maliescenario`/`tag`）**位于 exe 的 `.text` 区（本作 VA 0x401000）**，别误当剧本；剧本靠 `g_index` 变量表/角色名定位。
  - 工具：`_work_omega/dump_pid.py`（按 PID 转储）、`carve.py`（定位+解析）、`final_extract.py`（出成品）、`verify.py`（完整性）。
