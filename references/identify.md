# 源范围与格式识别

## 源范围

先确定文本来源范围，再按指定语言和版本确认配置、脚本清单、补丁及追加剧情。已有安装或解包目录匹配所需版本时直接复用，
无需重解光盘或媒体；局部版本存疑只核对相关配置和模块。运行验证使用的模块路径须与静态分析一致。

先列归档结构，再按需要提取；所需密码优先使用已提供值。范围内未知载体查签名和代表内容，
完整解包仅用于实际依赖或覆盖缺口。归档有可靠类型索引时按类型归类并读取相关成员；索引不足再扩查未知组，不为判型导出全部载荷。
提取器复用前核对格式、版本和参数；格式知识查 [引擎索引](engines/index.md)，本作状态查已有工作记录。

## 平台入口

| 信号 | 路径 |
|---|---|
| PSV app 树、work.bin、NoNpDrm 包 | [PSV PFS](platforms/psv-pfs.md) |
| PSP_GAME、ISO、EBOOT.BIN | 先按资源签名定位脚本；实现或原生正文未决时再读 [PSP EBOOT](decode.md#psp-eboot) |
| PS2 SYSTEM.CNF、SLPM/SLPS ELF | 先查启动程序及模块；正文可编译进[原生显示调用](script-structure.md#原生显示调用) |
| XCI、NSP、NCA、NSZ、XCZ | [Switch](platforms/switch-nca.md)，核对段与有效更新 |
| MComprHD / CHD | [镜像](engines/images.md) |
| PC exe 加数据目录 | 查真实 PE、CLR、overlay 和资源签名 |
| 普通压缩包或安装器 | 先列结构，按需要提取；Inno 使用支持的安装包工具 |

文件名、后缀、厂商和工具识勿只缩小候选。
语言和编码由格式、配置及可解析文本确认；日文零命中可能来自压缩、加密、字形表或错误载体。

## 格式索引

| 签名或结构 | 定位与参考 |
|---|---|
| CPK、@UTF；AFS、AFS2 | CRI 目录与压缩，[归档](archives.md#容器与读取)、[格式族](archives.md#归档族与变体) |
| `.spt` 中 `#SYS.ID`、`#MES.OUT` / `#MESEX.OUT`，引号内为大端双字节单元 | [混合编码 SPT](engines/spt.md)；已证构建直接从 ISO/CPK 读取脚本，不能仅凭 `.spt` 后缀套用 System-NNN |
| XP3；YPF | 索引、BASE、成员加密，[解码](decode.md#字段与编码) |
| PFS / PSPFS_V1 | 先区分 PSV PFS 与 PSP 自研，再读平台或 TOB 记录 |
| NCA 加密头、PFS0、HFS0 | [Switch](platforms/switch-nca.md)，NCA3 仅在解密头中可见 |
| PSARC | [格式族](archives.md#归档族与变体)，再按成员类型定位 |
| Marvelous MZ 命令流 | 工作区 mz-cmdstream；tag/wc、正文62、选择51为本作候选 |
| HFU2、UFFA | HuneX IKA，[脚本结构](script-cases.md#脚本构建) |
| mrgd00、MZX0、allscr | HuneX Ogre；工作区 hunex-ogre |
| STCM2、STCM2L、GLOBAL_DATA | [结构](engines/stcm2l.md#记录布局)、[变体](engines/stcm2l.md)、[导入编号](archives.md#基址与记录范围) |
| LSDARC V.100、SCR x.xx、LSD1A | Takuyo gss，[脚本结构](script-cases.md#脚本构建) |
| PSB、MDF、PGD | M2 索引、场景表及加密，[专册](engines/m2-psb.md) |
| LIBP、exec.dat | [Malie 格式与显示](engines/malie.md)，按成员读取，区分 PC/PSP/PSV 编码与块单位 |
| SQLite scene.db、ATL.DLL | Aromarie，[序列化文本](script-structure.md#序列化字段) |
| data.dat、pct_mess.dat、script*.dat | PCT，[编码及池](decode-cases.md#编码与成行案例) |
| ROM2、SNR | [格式族](archives.md#归档族与变体)，记录与语音参数逐作不同 |
| FPK、VML | D3P PS2，工作区 d3p-ps2-fpk-vml；68/64/F601为文本类候选 |
| Boys3.exe、B3.IDX、FPK、SPT | Swallowtail，工作区 swallowtail-boys3 |
| EMBINS.VVV | Koei PS2 模块及串池，工作区 koei-embins-ps2；按显示引用读取 |
| EVB、MARC | Otomate 字形码，[记录模式](script-structure.md#记录模式) |
| YDP1、SCRIPT_LSB | Idea Factory，工作区 idea-factory-ydp-lsb |
| VF、PE overlay | LiveMaker，[归档](archives.md#容器与读取)；字段独立混淆 |
| WSC、Rio.arc | [WillPlus 操作](archives.md#wsc-操作) |
| KAG、KS、TJS | [宏、扫描及显示状态](engines/kirikiri.md) |
| NScript.dat、NSA | [NScripter](engines/nscripter.md) |
| YuukiNovel WorkFile、YNE、PackageFile20 | 工作区 yuuki-novel；核对目录、LCG、点击及选择语法 |
| SCD、串联 ZIP | 学園K，[格式族](archives.md#归档族与变体) |
| SPTHEADER0、XOR FF 的 SPT | [System-NNN](engines/system-nnn.md) |
| `BE AD BC A8`、GCore/CGAya、aya.ini | [Kogado ARCW 与命令脚本](engines/kogado-gcore.md) |
| UnityFS、assets、assetbundle | [Unity](engines/unity.md)，按对象与实际字段定位 |
| KONAMI bytes、0503 引用 | [bytes](engines/unity.md#自研记录与文本-dsl) |
| HDLG、HESL、HLZS | [记录模式](script-structure.md#记录模式) |
| MDB、Standard Jet DB | [Access 与 DSL](archives.md#容器与读取) |
| XFIR/RIFX、CXT/DXR、STXT | [Director](archives.md#容器与读取) |
| FWS/CWS/ZWS | [SWF](archives.md#容器与读取)，对象不直接等于点击 |
| PACK、CMP、ENGINE.INI | [FORIS/Koei PACK](archives.md#容器与读取)、[格式族](archives.md#归档族与变体) |
| DDP0/DDP1 | [DDEngine](decode-cases.md#解码案例) |
| BSF1 | [记录模式](script-structure.md#记录模式) |

表内 opcode、偏移和变换只提示对应构建，不在识别阶段套用点击或过滤规则。

## 魔数核对

签名可能出现在代码、资源字符串、索引或压缩流中。
结合头字段、索引范围、已知成员和真实解包结构确认容器起点；
同一签名出现多次不证明有多套正文。

普通 PE 的 `4D 5A 50 00` 不另立 MZP 格式。
大文件需要签名扫描时使用 mmap 或适合当前 I/O 的分块读取，
不设唯一实现；先查已知索引和局部范围。
扁平补丁按 basename 匹配须确认唯一性，不覆盖不同目录同名资源。

## 未知格式与输出

先查已有工具或引擎读取实现，再确认包装、编码、字符串区和引用。
若 ELF/PE 中已有叙事串及显示引用，先检查[原生调用链](script-structure.md#原生显示调用)，无需假定另有脚本文件或 VM 分发器。
按已证区段解析长度、指令及终止，记录未消费部分和未决项。
文本命令、数组顺序、计数一致和连续地址不单独证明点击；
必要边界按 [取证](layout.md#边界取证) 补齐。

新发现保存到对应格式参考或已有作品记录，不重复生成路由、日报及草案。
