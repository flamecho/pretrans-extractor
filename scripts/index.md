# 通用脚本

保留通用工具及共通解析库。参数以帮助或实现为准。
作品专用入口见 [works.md](works.md)，按格式选择见 [by-engine.md](by-engine.md)，必要解析依赖见 [_lib/index.md](_lib/index.md)。

| 脚本 | 适用范围 | 用途 | 关联格式 |
|---|---|---|---|
| [advhd.py](advhd.py) | 通用 | WillPlus / AdvHD (.wsc bytecode) shared engine. | — |
| [air_abc.py](air_abc.py) | 通用 | Adobe AIR / SWF 的 ABC(ActionScript 3 字节码) 解析器 + 反汇编器。 | — |
| [air_body.py](air_body.py) | 通用 | ABC 方法体（method_body_info）定位器。 | — |
| [air_body2.py](air_body2.py) | 通用 | 更宽松的方法体定位：不限定 d0 30 序言，改用「6 个 u30 精确落在 code 起点 + 尾部结构自洽」。 | — |
| [air_kvs_dat.py](air_kvs_dat.py) | 通用 | Adobe AIR / Flash 「*.kvs + *.dat」资源归档解包器 | — |
| [air_scan.py](air_scan.py) | 通用 | 批量反汇编所有方法，按「字节运算 + ByteArray 读写」特征筛解密候选。 | — |
| [air_win.py](air_win.py) | 通用 | 打印某个 ABC 偏移附近的反汇编窗口。 | — |
| [archive_work.py](archive_work.py) | 通用 | 从解析报告生成作品、工具、日志片段及引擎文档建议。 | — |
| [bktr_merge.py](bktr_merge.py) | 通用 | 官方更新档（BKTR Patch RomFS）→ 本体 romfs 合并读取（hactool 对这类重打包件报 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) |
| [bktr_romfs.py](bktr_romfs.py) | 通用 | NS 更新档「Patch RomFS / BKTR」读取器（不依赖 hactool，可直接读 .nsp/.nca）。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) |
| [cd_bin2iso.py](cd_bin2iso.py) | 通用 | MODE1/2352 · MODE2/2352 裸镜像 -> 2048 用户数据 ISO | [koei-embins-ps2](../references/engines/koei-embins-ps2.md) · [koei-pack-ps2](../references/engines/koei-pack-ps2.md) |
| [cdar.py](cdar.py) | 通用 | CDAR 容器读取库（被 cdar_extract.py import）：索引表 + 条目解压。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [cdar_extract.py](cdar_extract.py) | 通用 | 递归解包 CDAR 容器（可下钻嵌套），逐条目落成原始字节。 | [koei-cdar](../references/engines/koei-cdar.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [charset_audit.py](charset_audit.py) | 通用 | 非日文字符台账审计：把每部成品里「kana/汉字/CJK标点/全角符号」以外的字符全部列出， | — |
| [check_text.py](check_text.py) | 通用 | 交付前自检（品检）—— 日文游戏剧本文本提取产物的通用检查器。 | — |
| [corda_2fa_get.py](corda_2fa_get.py) | 通用 | 按路径取出 CDAR v4 里某个叶子文件: corda_2fa_get.py <DATA.BIN> <base> <path> <out> | — |
| [cpk.py](cpk.py) | 通用 | CRI CPK unpacker (纯 Python, 无依赖). | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [cpk_v1.py](cpk_v1.py) | 通用 | CRI CPK unpacker (v1 ITOC-style + v2/v3 @UTF), 纯 Python. | [cri-archives](../references/engines/cri-archives.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [distill.py](distill.py) | 通用 | 从报告生成文档修订草案。 | — |
| [dup_probe.py](dup_probe.py) | 通用 | 双版拼接探针：找「同一行内同一句出现两次」的行。 | — |
| [emu.py](emu.py) | 通用 | 模拟器辅助：截屏 + 发键（Windows，PIL + ctypes，无第三方 GUI 依赖）。 | — |
| [emu_bring.py](emu_bring.py) | 通用 | 把模拟器（PCSX2/PPSSPP）窗口置前并截图。标题匹配在脚本内完成，免 CJK 参数传递。 | — |
| [eroto_unxp3.py](eroto_unxp3.py) | 通用 | XP3 脚本层解包（LiveMaker/KiriKiri 通用）：解出 .ks/.tjs/.txt/.sli/.asd 并列出全部成员分类。 | [kirikiri](../references/engines/kirikiri.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [fix_multi_brackets.py](fix_multi_brackets.py) | 通用 | 一行多个框的拆行（独白 （A）（B） / 台词 「A」「B」）。 | — |
| [fix_wrap_pairs.py](fix_wrap_pairs.py) | 通用 | 框内软换行被切成两行的修复（跨行续行收拢 / 缺引号补齐）。 | — |
| [fullscan.py](fullscan.py) | 通用 | 逐个归档条目试解压，按「含日文字数」排序 —— 先定位正文在哪一层容器。 | — |
| [glyph_pick.py](glyph_pick.py) | 通用 | 在「语境候选字」之间做字形比对（仅用于验证假设，勿当 OCR 用）。 | — |
| [happygift_inspect.py](happygift_inspect.py) | 通用 | 通用工具 | [reallive](../references/engines/reallive.md) |
| [himpac.py](himpac.py) | 通用 | Himauri (SH System) HXP 容器解包 —— Him4 / Him5 | [himauri](../references/engines/himauri.md) |
| [himscript.py](himscript.py) | 通用 | Himauri Script Engine (.him) → 文本 | [himauri](../references/engines/himauri.md) |
| [hunex_hlzs.py](hunex_hlzs.py) | 通用 | HuneX HLZS（LZSS）解码器：dict 0x1000 / maxlen 0x12，解 script_dialog_xx.hdlg 等 HLZS 载荷。 | — |
| [identify.py](identify.py) | 通用 | 识别容器或引擎，输出依据、文档路径和建议命令。 | [artemis](../references/engines/artemis.md) · [cri-archives](../references/engines/cri-archives.md) · [kirikiri](../references/engines/kirikiri.md) · [koei-cdar](../references/engines/koei-cdar.md) · [malie](../references/engines/malie.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [nis-nml](../references/engines/nis-nml.md) · [nitroplus](../references/engines/nitroplus.md) · [rom2](../references/engines/rom2.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [il2cpp_fields.py](il2cpp_fields.py) | 通用 | 纯 Python 读 IL2CPP global-metadata.dat 的类型定义/字段表（不反编译、零依赖）。 | — |
| [init_all_charset.py](init_all_charset.py) | 通用 | 批量生成字符台账：对 提取结果/ 下全部成品跑 check_text --init-charset。 | — |
| [iowatch.py](iowatch.py) | 通用 | 按秒采样进程 I/O 计数与文本槽变化，定位"一次点击读了多少字节、出现哪些新文本"。 | — |
| [iso_cut_cpk.py](iso_cut_cpk.py) | 通用 | ISO9660 内指定 LBA 的 CPK 切出并解包 —— PSP（Zerodiv / CRI CPK 系）通用驱动 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [libp_malievita.py](libp_malievita.py) | 通用 | Malie（Vita）Libp 归档读取库：入口表 / 文件名 / 数据切片。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [lint_docs.py](lint_docs.py) | 通用 | 检查技能文档的文件、章节链接、导航可达性和 Markdown 排版。 | — |
| [livemaker_extract.py](livemaker_extract.py) | 通用 | LiveMaker 3 通用文本提取（VF 归档 ＋ LMScript .lsb ＋ LiveNovel TpWord）。 | [livemaker](../references/engines/livemaker.md) |
| [lua51.py](lua51.py) | 通用 | Lua 5.1 bytecode 解析（Vita/PSV 乙女作常见：脚本编译为 luac 5.1）。 | — |
| [malie_extract.py](malie_extract.py) | 通用 | Malie System (GreenWood) 通用提取工具 —— OmegaVampire repack / 断罪のマリア 实证. | [malie](../references/engines/malie.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [mem_scan.py](mem_scan.py) | 通用 | 读取运行中进程的内存，按编码搜日文串（用于「格式解不开时，直接从运行时抓明文」）。 | [unity](../references/engines/unity.md) |
| [memcheck.py](memcheck.py) | 通用 | 检查记忆入口大小，并列出技能文档体积。 | — |
| [memcollect.py](memcollect.py) | 通用 | 运行中进程的日文文本高频采样器（PC 游戯 运行时提取） | — |
| [memdump.py](memdump.py) | 通用 | 从进程内存 dump 一段区间到文件。用法: python scripts/memdump.py <pid> <hex_addr> <size> <out> | — |
| [memdump_win32.py](memdump_win32.py) | 通用 | 从**正在运行**的 32 位游戏进程里按绝对地址读内存并 dump（不启动游戏）。 | — |
| [memscan.py](memscan.py) | 通用 | 扫描另一个进程的内存，按多种编码查找关键词（用于判断某段文本在运行时是否以明文存在）。 | — |
| [memscan_jp.py](memscan_jp.py) | 通用 | 从运行中的进程内存里捞 CP932 日文（PC 游戯 文本提取的「运行时」路线） | — |
| [memtext.py](memtext.py) | 通用 | 遍历进程内指定 guest 地址区间的已提交区域，就地提取 cp932 日文段落。 | — |
| [merge_name_variants.py](merge_name_variants.py) | 通用 | 双版拼接合并工具（名字宏双版 / 点名版↔泛称版）。 | — |
| [mips_xref.py](mips_xref.py) | 通用 | 线性扫描 + lui/addiu 地址恢复（PS2 R5900）。 | — |
| [ml2_unpack.py](ml2_unpack.py) | 通用 | [DEPRECATED] 已被 ml2_tkl.py 取代（本文件的 flags=1 LZSS / flags=2 实现均不正确）。 | — |
| [nca_romfs.py](nca_romfs.py) | 通用 | 通用：NSP/NCA 就地读 romfs（不落副本）。 | — |
| [nca_stream_romfs.py](nca_stream_romfs.py) | 通用 | Switch 容器流式取 romfs 文件（不落 NCA/NSP 副本，省盘）。 | [otomate-sscn](../references/engines/otomate-sscn.md) |
| [noa_unpack.py](noa_unpack.py) | 通用 | Entis GLS / ERISA 'noa' archive unpacker. | — |
| [npa_nrbf.py](npa_nrbf.py) | 通用 | Nitroplus NPA 内 NRBF（.NET BinaryFormatter）序列化数据的解析器。 | — |
| [npk3.py](npk3.py) | 通用 | NPK3 (Nitroplus Diesel Engine) unpacker. | — |
| [ns_dual.py](ns_dual.py) | 通用 | NScripter（nscript.dat，整文件 XOR <key>）-> 「双版对照」全文本 | — |
| [ns_extract.py](ns_extract.py) | 通用 | NScripter (nscript.dat) 全文本提取器 —— 「双版对照」口径。 | — |
| [ns_open.py](ns_open.py) | 通用 | NS 统一入口 —— 一条命令走完 XCI/NSP/NCA 的判定与解包，并**打印为什么选这条路**。 | [artemis](../references/engines/artemis.md) · [cri-archives](../references/engines/cri-archives.md) · [kirikiri](../references/engines/kirikiri.md) · [koei-cdar](../references/engines/koei-cdar.md) · [malie](../references/engines/malie.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [nis-nml](../references/engines/nis-nml.md) · [nitroplus](../references/engines/nitroplus.md) · [rom2](../references/engines/rom2.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [ns_rip.py](ns_rip.py) | 通用 | NScripter (nscript.dat) 文本提取器。 | — |
| [nsac.py](nsac.py) | 通用 | NSAC (v2) 容器解析/解包 —— eXtend 系 PSVita 作品《逢魔が刻 ～かくりよの縁～》(PCSG00769) | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [nis-nml](../references/engines/nis-nml.md) |
| [nsp_list.py](nsp_list.py) | 通用 | 列/取 NSP(XCI 内 PFS0) 的条目 —— 只读 PFS0 头，不涉及解密。 | — |
| [nsp_nca_romfs.py](nsp_nca_romfs.py) | 通用 | ワンド オブ フォーチュン Ｒ２（Switch）—— NSP → Program NCA → RomFS 枚举／导出 | [selfpak-utf16-vm](../references/engines/selfpak-utf16-vm.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) · [vridge](../references/engines/vridge.md) |
| [nsp_plainromfs.py](nsp_plainromfs.py) | 通用 | 通用：NSP/PFS0（或裸 NCA）内**未压缩** RomFS 的就地列出/提取。 | — |
| [nsp_romfs_bulk.py](nsp_romfs_bulk.py) | 通用 | NSP 内 romfs 批量就地提取（按正则/大小筛选），一次开 NCA 多次落盘。 | — |
| [nsp_split.py](nsp_split.py) | 通用 | PFS0(NSP) 逐块直拷拆分器 —— 规避 hactool --pfs0dir 对 >1.7GB 成员写全零的问题。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [pack_cmp.py](pack_cmp.py) | 通用 | VividColor «GameSystem» *.cmp PACK 容器工具（PC）。 | [vividcolor](../references/engines/vividcolor.md) |
| [pe_dis.py](pe_dis.py) | 通用 | PE 反汇编辅助（capstone）：按 RVA/VA 定位并打印附近指令。 | — |
| [pending.py](pending.py) | 通用 | **未落位检测**：哪些作品提完了却还没进索引。 | — |
| [probe.py](probe.py) | 通用 | 低 token 探查器（所有输出**默认限量**，绝不整表 dump）。 | — |
| [procboth.py](procboth.py) | 通用 | 联合监视：游戏文件读取位置变化 + guest 堆中新出现的 cp932 日文串。 | — |
| [procfpos.py](procfpos.py) | 通用 | 列出指定进程打开的游戏文件及其当前读写位置（GetFilePointer）。 | — |
| [prochandles.py](prochandles.py) | 通用 | 列出指定进程当前打开的文件路径。 | — |
| [procwatch.py](procwatch.py) | 通用 | 实时监视进程内游戏文件的读取位置变化，定位"引擎刚刚读了哪一段"。 | — |
| [psarc_extract.py](psarc_extract.py) | 通用 | PSARC (Sony) extractor — big-endian classic PSARC. | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [psvskip_patch.py](psvskip_patch.py) | 通用 | 让 psvpfsparser 在单文件解密失败时继续（跳过），不整进程退出。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [ramsnap.py](ramsnap.py) | 通用 | 把 guest 内存整段 dump 到文件（分块读，支持 100MB 级区域）。 | — |
| [rar5_list.py](rar5_list.py) | 通用 | RAR5 文件头遍历器：不解压、只读块头，快速列出文件名（大固实包用）。 | — |
| [recheck_all.py](recheck_all.py) | 通用 | 批量复检 提取结果/：按双版清单逐个跑 check_text，汇总 PASS/FAIL 并列出 E/W。 | — |
| [renderfont.py](renderfont.py) | 通用 | 把字库图集渲染成 PNG（逐码位预览，供人工目视确认字形）。 | — |
| [rl_decomp.py](rl_decomp.py) | 通用 | 通用工具 | [reallive](../references/engines/reallive.md) |
| [rl_parse.py](rl_parse.py) | 通用 | 通用工具 | [reallive](../references/engines/reallive.md) |
| [rxdata_scripts_dump.py](rxdata_scripts_dump.py) | 通用 | RPG Maker XP/VX Scripts.rxdata 解压到 .rb（zlib 逐本解压）。 | — |
| [scan_jp.py](scan_jp.py) | 通用 | 目录级扫描：找「连续假名 run 多」的文件并排序 —— 先圈候选，再细看。 | — |
| [scan_nested.py](scan_nested.py) | 通用 | 在归档的嵌套条目里扫日文，报 magic / 大小 / 样例。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [scanjp.py](scanjp.py) | 通用 | 单文件内定位连续假名 run（按偏移列出），用于确认哪一段是正文。 | — |
| [selftest.py](selftest.py) | 通用 | check_text.py 判据的回归测试（改判据前后各跑一次）。 | — |
| [split_adjacent_quotes.py](split_adjacent_quotes.py) | 通用 | 句中 」「 相邻的筛查／拆分工具（skill references/layout.md §「句中引号只作探针」的落地）。 | — |
| [split_md.py](split_md.py) | 通用 | **按语义边界**拆分 md（标题 / 编号条目），带零丢失校验与原子替换。 | — |
| [struct_probe.py](struct_probe.py) | 通用 | 引号/括号结构探针：把「一行里塞了几个框」量化。 | — |
| [switch_nca.py](switch_nca.py) | 通用 | Switch NCA 解密器（不依赖 hactool）—— 处理 Titlekey crypto / Standard crypto 的 Program NCA。 | — |
| [termdict_extract.py](termdict_extract.py) | 通用 | 用語辞典（termItem.dat）→ 【見出し語】解説文 一行一条，并入成品末尾 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) |
| [test_workflow.py](test_workflow.py) | 通用 | Regression fixtures for source layout checks and task-scoped wrapup. | — |
| [tik_key.py](tik_key.py) | 通用 | 由 ticket 推 NCA 内容密钥（Titlekey crypto），并用 section 0 的 PFS0/IVFC 魔数自证。 | — |
| [upd_merge.py](upd_merge.py) | 通用 | 通用「NS 官方更新（BKTR 差分）＋ 本体 NCA」→ 最新 romfs 文件 合并器。 | [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) |
| [utapri_debut_check.py](utapri_debut_check.py) | 通用 | 交付前自检（品检）—— 日文游戏剧本文本提取产物的通用检查器。 | — |
| [vridge_psp_run.py](vridge_psp_run.py) | 通用 | Vridge/D3P 系 PSP 作品（sc.cpk + lt.bin 自建字符集）通用提取器。 | [cri-archives](../references/engines/cri-archives.md) · [mz-cmdstream](../references/engines/mz-cmdstream.md) · [nis-cpk-snbin](../references/engines/nis-cpk-snbin.md) · [stcm2l](../references/engines/stcm2l.md) · [unity](../references/engines/unity.md) |
| [win_memdump.py](win_memdump.py) | 通用 | Windows 进程内存导出（只读，用于从运行中的游戏抓明文）。 | — |
| [wrapup.py](wrapup.py) | 通用 | Task-local validation; maintenance steps run only when explicitly selected. | — |
| [xci_romfs.py](xci_romfs.py) | 通用 | XCI -> (内存中)NCA -> RomFS 单文件抽取（不落 NCA/整 romfs，省磁盘）。 | — |
| [xp3dec_index.py](xp3dec_index.py) | 通用 | XP3 索引解析（通用）：Kirikiri XP3 的 File/info/segm/adlr 块逐个消费，导出 JSON + 成员名清单。 | — |
| [xp3dec_inproc.py](xp3dec_inproc.py) | 通用 | XP3 逐文件加密的通用解法：在真实游戏进程内 in-process 调用注册的 filter 回调。 | — |
