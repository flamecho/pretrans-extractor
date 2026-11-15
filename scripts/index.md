# 脚本索引

从当前工作区调用技能脚本；参数以帮助或实现为准，不支持选项的旧脚本先查参数读取方式。
通用工具见下表；作品专用脚本见 [works.md](works.md)，按格式选工具见 [by-engine.md](by-engine.md)。

| 脚本 | 适用范围 | 用途 |
|---|---|---|
| `identify.py` | 通用 | 容器/引擎识别提示，须用魔数和结构复核。 |
| `probe.py` | 通用 | 签名、熵、字符、局部字节和目录摘要，输出限量。 |
| `struct_probe.py` | 通用 | A/B 失衡与 C/D 多段候选；不判断点击或页数。 |
| `dup_probe.py` | 通用 | 行内重复候选；去重须有来源依据。 |
| `charset_audit.py` | 通用 | 非日文字符、频次及上下文摘要。 |
| `check_text.py` | 通用 | 编码、残留、字符台账和声明一致性；`--layout-map` 可选验证合并页。 |
| `selftest.py` | 通用 | 品检回归；修改检查行为后运行。 |
| `test_workflow.py` | 通用 | 来源页映射、收尾范围、验证复用与子进程 UTF-8 回归。 |
| `init_all_charset.py` | 通用 | 在任务范围内批量生成字符台账；基线仍需核实。 |
| `recheck_all.py` | 通用 | 在任务范围内批量复检文本。 |
| `wrapup.py` | 通用 | 默认校验本作；`--checked-sha256` 复用通过记录，维护按显式选项执行。 |
| `distill.py` | 通用 | 从本作报告生成沉淀草案，不直接修订技能。 |
| `archive_work.py` | 通用 | 从报告生成记忆片段，`--apply` 执行落位；`--work` 是作品名。 |
| `memcheck.py` | 通用 | 记忆入口体积信息，仅在维护需要时运行。 |
| `split_md.py` | 通用 | 按语义拆文档，先用 `--dry-run` 核对输出及引用。 |
| `lint_docs.py` | 通用 | 检查路径、路由及排版；默认包含工作记录，`--mem` 限定范围。 |
| `pending.py` | 通用 | 显式批量维护时查待落位项目；仅清理时不运行。 |
| `fix_wrap_pairs.py` | 通用 | 历史启发式修补：成对包装。 |
| `fix_multi_brackets.py` | 通用 | 历史启发式修补：多段括号。 |
| `merge_name_variants.py` | 通用 | 历史启发式修补：姓名变体。 |

修补工具使用前由源码确定修复范围，统计结果仅定位候选。

清理与收尾见 [规则](../references/workspace.md#收尾与维护)，验收命令见 [自检](../references/verification.md#交付自检)。

<!-- generated:script-catalog:start -->

## 通用格式工具

| 脚本 | 适用范围 | 用途 |
|---|---|---|
| [advhd.py](advhd.py) | 通用 | WillPlus / AdvHD (.wsc bytecode) shared engine. |
| [air_abc.py](air_abc.py) | 通用 | Adobe AIR / SWF 的 ABC(ActionScript 3 字节码) 解析器 + 反汇编器。 |
| [air_body.py](air_body.py) | 通用 | ABC 方法体（method_body_info）定位器。 |
| [air_body2.py](air_body2.py) | 通用 | 更宽松的方法体定位：不限定 d0 30 序言，改用「6 个 u30 精确落在 code 起点 + 尾部结构自洽」。 |
| [air_kvs_dat.py](air_kvs_dat.py) | 通用 | Adobe AIR / Flash 「*.kvs + *.dat」资源归档解包器 |
| [air_scan.py](air_scan.py) | 通用 | 批量反汇编所有方法，按「字节运算 + ByteArray 读写」特征筛解密候选。 |
| [air_win.py](air_win.py) | 通用 | 打印某个 ABC 偏移附近的反汇编窗口。 |
| [bktr_merge.py](bktr_merge.py) | 通用 | 官方更新档（BKTR Patch RomFS）→ 本体 romfs 合并读取（hactool 对这类重打包件报 |
| [bktr_romfs.py](bktr_romfs.py) | 通用 | NS 更新档「Patch RomFS / BKTR」读取器（不依赖 hactool，可直接读 .nsp/.nca）。 |
| [cd_bin2iso.py](cd_bin2iso.py) | 通用 | MODE1/2352 · MODE2/2352 裸镜像 -> 2048 用户数据 ISO |
| [cdar.py](cdar.py) | 通用 | CDAR 容器读取库（被 cdar_extract.py import）：索引表 + 条目解压。 |
| [cdar_extract.py](cdar_extract.py) | 通用 | 递归解包 CDAR 容器（可下钻嵌套），逐条目落成原始字节。 |
| [corda_2fa_get.py](corda_2fa_get.py) | 通用 | 按路径取出 CDAR v4 里某个叶子文件: corda_2fa_get.py <DATA.BIN> <base> <path> <out> |
| [cpk.py](cpk.py) | 通用 | CRI CPK unpacker (纯 Python, 无依赖). |
| [cpk_v1.py](cpk_v1.py) | 通用 | CRI CPK unpacker (v1 ITOC-style + v2/v3 @UTF), 纯 Python. |
| [emu.py](emu.py) | 通用 | 模拟器辅助：截屏 + 发键（Windows，PIL + ctypes，无第三方 GUI 依赖）。 |
| [emu_bring.py](emu_bring.py) | 通用 | 把模拟器（PCSX2/PPSSPP）窗口置前并截图。标题匹配在脚本内完成，免 CJK 参数传递。 |
| [eroto_unxp3.py](eroto_unxp3.py) | 通用 | XP3 脚本层解包（LiveMaker/KiriKiri 通用）：解出 .ks/.tjs/.txt/.sli/.asd 并列出全部成员分类。 |
| [fullscan.py](fullscan.py) | 通用 | 逐个归档条目试解压，按「含日文字数」排序 —— 先定位正文在哪一层容器。 |
| [glyph_pick.py](glyph_pick.py) | 通用 | 在「语境候选字」之间做字形比对（仅用于验证假设，勿当 OCR 用）。 |
| [happygift_inspect.py](happygift_inspect.py) | 通用 | — |
| [himpac.py](himpac.py) | 通用 | Himauri (SH System) HXP 容器解包 —— Him4 / Him5 |
| [himscript.py](himscript.py) | 通用 | Himauri Script Engine (.him) → 文本 |
| [hunex_hlzs.py](hunex_hlzs.py) | 通用 | HuneX HLZS（LZSS）解码器：dict 0x1000 / maxlen 0x12，解 script_dialog_xx.hdlg 等 HLZS 载荷。 |
| [il2cpp_fields.py](il2cpp_fields.py) | 通用 | 纯 Python 读 IL2CPP global-metadata.dat 的类型定义/字段表（不反编译、零依赖）。 |
| [iowatch.py](iowatch.py) | 通用 | 按秒采样进程 I/O 计数与文本槽变化，定位"一次点击读了多少字节、出现哪些新文本"。 |
| [iso_cut_cpk.py](iso_cut_cpk.py) | 通用 | ISO9660 内指定 LBA 的 CPK 切出并解包 —— PSP（Zerodiv / CRI CPK 系）通用驱动 |
| [libp_malievita.py](libp_malievita.py) | 通用 | Malie（Vita）Libp 归档读取库：入口表 / 文件名 / 数据切片。 |
| [livemaker_extract.py](livemaker_extract.py) | 通用 | LiveMaker 3 通用文本提取（VF 归档 ＋ LMScript .lsb ＋ LiveNovel TpWord）。 |
| [lua51.py](lua51.py) | 通用 | Lua 5.1 bytecode 解析（Vita/PSV 乙女作常见：脚本编译为 luac 5.1）。 |
| [malie_extract.py](malie_extract.py) | 通用 | Malie System (GreenWood) 通用提取工具 —— OmegaVampire repack / 断罪のマリア 实证. |
| [mem_scan.py](mem_scan.py) | 通用 | 读取运行中进程的内存，按编码搜日文串（用于「格式解不开时，直接从运行时抓明文」）。 |
| [memcollect.py](memcollect.py) | 通用 | 运行中进程的日文文本高频采样器（PC 游戯 运行时提取） |
| [memdump.py](memdump.py) | 通用 | 从进程内存 dump 一段区间到文件。用法: python scripts/memdump.py <pid> <hex_addr> <size> <out> |
| [memdump_win32.py](memdump_win32.py) | 通用 | 从**正在运行**的 32 位游戏进程里按绝对地址读内存并 dump（不启动游戏）。 |
| [memscan.py](memscan.py) | 通用 | 扫描另一个进程的内存，按多种编码查找关键词（用于判断某段文本在运行时是否以明文存在）。 |
| [memscan_jp.py](memscan_jp.py) | 通用 | 从运行中的进程内存里捞 CP932 日文（PC 游戯 文本提取的「运行时」路线） |
| [memtext.py](memtext.py) | 通用 | 遍历进程内指定 guest 地址区间的已提交区域，就地提取 cp932 日文段落。 |
| [mips_xref.py](mips_xref.py) | 通用 | 线性扫描 + lui/addiu 地址恢复（PS2 R5900）。 |
| [ml2_unpack.py](ml2_unpack.py) | 通用 | [DEPRECATED] 已被 ml2_tkl.py 取代（本文件的 flags=1 LZSS / flags=2 实现均不正确）。 |
| [nca_romfs.py](nca_romfs.py) | 通用 | 通用：NSP/NCA 就地读 romfs（不落副本）。 |
| [nca_stream_romfs.py](nca_stream_romfs.py) | 通用 | Switch 容器流式取 romfs 文件（不落 NCA/NSP 副本，省盘）。 |
| [noa_unpack.py](noa_unpack.py) | 通用 | Entis GLS / ERISA 'noa' archive unpacker. |
| [npa_nrbf.py](npa_nrbf.py) | 通用 | Nitroplus NPA 内 NRBF（.NET BinaryFormatter）序列化数据的解析器。 |
| [npk3.py](npk3.py) | 通用 | NPK3 (Nitroplus Diesel Engine) unpacker. |
| [ns_dual.py](ns_dual.py) | 通用 | NScripter（nscript.dat，整文件 XOR <key>）-> 「双版对照」全文本 |
| [ns_extract.py](ns_extract.py) | 通用 | NScripter (nscript.dat) 全文本提取器 —— 「双版对照」口径。 |
| [ns_open.py](ns_open.py) | 通用 | NS 统一入口 —— 一条命令走完 XCI/NSP/NCA 的判定与解包，并**打印为什么选这条路**。 |
| [ns_rip.py](ns_rip.py) | 通用 | NScripter (nscript.dat) 文本提取器。 |
| [nsac.py](nsac.py) | 通用 | NSAC (v2) 容器解析/解包 —— eXtend 系 PSVita 作品《逢魔が刻 ～かくりよの縁～》(PCSG00769) |
| [nsp_list.py](nsp_list.py) | 通用 | 列/取 NSP(XCI 内 PFS0) 的条目 —— 只读 PFS0 头，不涉及解密。 |
| [nsp_nca_romfs.py](nsp_nca_romfs.py) | 通用 | ワンド オブ フォーチュン Ｒ２（Switch）—— NSP → Program NCA → RomFS 枚举／导出 |
| [nsp_plainromfs.py](nsp_plainromfs.py) | 通用 | 通用：NSP/PFS0（或裸 NCA）内**未压缩** RomFS 的就地列出/提取。 |
| [nsp_romfs_bulk.py](nsp_romfs_bulk.py) | 通用 | NSP 内 romfs 批量就地提取（按正则/大小筛选），一次开 NCA 多次落盘。 |
| [nsp_split.py](nsp_split.py) | 通用 | PFS0(NSP) 逐块直拷拆分器 —— 规避 hactool --pfs0dir 对 >1.7GB 成员写全零的问题。 |
| [pack_cmp.py](pack_cmp.py) | 通用 | VividColor «GameSystem» *.cmp PACK 容器工具（PC）。 |
| [pe_dis.py](pe_dis.py) | 通用 | PE 反汇编辅助（capstone）：按 RVA/VA 定位并打印附近指令。 |
| [procboth.py](procboth.py) | 通用 | 联合监视：游戏文件读取位置变化 + guest 堆中新出现的 cp932 日文串。 |
| [procfpos.py](procfpos.py) | 通用 | 列出指定进程打开的游戏文件及其当前读写位置（GetFilePointer）。 |
| [prochandles.py](prochandles.py) | 通用 | 列出指定进程当前打开的文件路径。 |
| [procwatch.py](procwatch.py) | 通用 | 实时监视进程内游戏文件的读取位置变化，定位"引擎刚刚读了哪一段"。 |
| [psarc_extract.py](psarc_extract.py) | 通用 | PSARC (Sony) extractor — big-endian classic PSARC. |
| [psvskip_patch.py](psvskip_patch.py) | 通用 | 让 psvpfsparser 在单文件解密失败时继续（跳过），不整进程退出。 |
| [ramsnap.py](ramsnap.py) | 通用 | 把 guest 内存整段 dump 到文件（分块读，支持 100MB 级区域）。 |
| [rar5_list.py](rar5_list.py) | 通用 | RAR5 文件头遍历器：不解压、只读块头，快速列出文件名（大固实包用）。 |
| [renderfont.py](renderfont.py) | 通用 | 把字库图集渲染成 PNG（逐码位预览，供人工目视确认字形）。 |
| [rl_decomp.py](rl_decomp.py) | 通用 | — |
| [rl_parse.py](rl_parse.py) | 通用 | — |
| [rxdata_scripts_dump.py](rxdata_scripts_dump.py) | 通用 | RPG Maker XP/VX Scripts.rxdata 解压到 .rb（zlib 逐本解压）。 |
| [scan_jp.py](scan_jp.py) | 通用 | 目录级扫描：找「连续假名 run 多」的文件并排序 —— 先圈候选，再细看。 |
| [scan_nested.py](scan_nested.py) | 通用 | 在归档的嵌套条目里扫日文，报 magic / 大小 / 样例。 |
| [scanjp.py](scanjp.py) | 通用 | 单文件内定位连续假名 run（按偏移列出），用于确认哪一段是正文。 |
| [split_adjacent_quotes.py](split_adjacent_quotes.py) | 通用 | 句中 」「 相邻的筛查／拆分工具（skill references/layout.md §「句中引号只作探针」的落地）。 |
| [switch_nca.py](switch_nca.py) | 通用 | Switch NCA 解密器（不依赖 hactool）—— 处理 Titlekey crypto / Standard crypto 的 Program NCA。 |
| [termdict_extract.py](termdict_extract.py) | 通用 | 用語辞典（termItem.dat）→ 【見出し語】解説文 一行一条，并入成品末尾 |
| [tik_key.py](tik_key.py) | 通用 | 由 ticket 推 NCA 内容密钥（Titlekey crypto），并用 section 0 的 PFS0/IVFC 魔数自证。 |
| [upd_merge.py](upd_merge.py) | 通用 | 通用「NS 官方更新（BKTR 差分）＋ 本体 NCA」→ 最新 romfs 文件 合并器。 |
| [utapri_debut_check.py](utapri_debut_check.py) | 通用 | 交付前自检（品检）—— 日文游戏剧本文本提取产物的通用检查器。 |
| [vridge_psp_run.py](vridge_psp_run.py) | 通用 | Vridge/D3P 系 PSP 作品（sc.cpk + lt.bin 自建字符集）通用提取器。 |
| [win_memdump.py](win_memdump.py) | 通用 | Windows 进程内存导出（只读，用于从运行中的游戏抓明文）。 |
| [xci_romfs.py](xci_romfs.py) | 通用 | XCI -> (内存中)NCA -> RomFS 单文件抽取（不落 NCA/整 romfs，省磁盘）。 |
| [xp3dec_index.py](xp3dec_index.py) | 通用 | XP3 索引解析（通用）：Kirikiri XP3 的 File/info/segm/adlr 块逐个消费，导出 JSON + 成员名清单。 |
| [xp3dec_inproc.py](xp3dec_inproc.py) | 通用 | XP3 逐文件加密的通用解法：在真实游戏进程内 in-process 调用注册的 filter 回调。 |
