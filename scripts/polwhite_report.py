"""Package the verified provenance and write White EA's extraction report."""
from pathlib import Path
import json,hashlib,shutil,collections,argparse
ap=argparse.ArgumentParser();ap.add_argument('--checked',action='store_true');args=ap.parse_args()
ROOT=Path(__file__).resolve().parent.parent;W=ROOT/'_work_polwhite_ea'
X=json.loads((W/'extraction.json').read_text('utf-8'));I=json.loads((W/'inspection.json').read_text('utf-8'))
A=json.loads((W/'audit.json').read_text('utf-8'));V=json.loads((W/'inventory.json').read_text('utf-8'))
C=json.loads((W/'charset_sources.json').read_text('utf-8'));P=json.loads((W/'page_details.json').read_text('utf-8'))
TITLE=X['title'];allow=ROOT/'解析报告/allow';allow.mkdir(exist_ok=True)
assert X['sha256']==A['output_sha256'] and not A['unexpected_overflows']
if args.checked:
    data=(W/'check.log').read_bytes()
    check_log=data.decode('utf-16') if data.startswith(b'\xff\xfe') else data.decode('utf-8-sig')
    assert 'RESULT: PASS' in check_log and TITLE in check_log
    assert hashlib.sha256(Path(X['output']).read_bytes()).hexdigest()==X['sha256']
    shutil.copyfile(W/'check.log',allow/(TITLE+'.check.log'))
quality='PASS（技能 check_text.py 退出码 0；916 个来源映射页全部一致）' if args.checked else '待运行最终技能检查'
for filename,ext in [('line_origins.json','sources.json'),('layout_map.json','layout.json'),('audit.json','audit.json'),('inventory.json','inventory.json'),('charset_sources.json','charset.json'),('ascii_audit.json','ascii.json'),('structure_audit.json','structure.json'),('page_details.json','pages.json'),('rar_manifest.json','rar.json'),('iso_manifest.json','iso.json'),('disc_manifest.json','disc.json')]:
    shutil.copyfile(W/filename,allow/(TITLE+'.'+ext))
runtime=allow/(TITLE+'.runtime');runtime.mkdir(exist_ok=True)
for name in ['native_case1_step01.png','native_case1_step05.png','native_case1_step06.png','native_case1_step07.png','native_case2_step04.png','native_case2_step05.png']:
    shutil.copyfile(W/name,runtime/name)
# These six source characters were read with provenance before registration:
# em dash, ellipsis, musical notes, source curly quotes, and one ASCII space.
(allow/(TITLE+'.charset')).write_text('# 非日文字符台账：已逐种回源核实，字形及空格均保留\n'+'\n'.join(f"{x['char']}\t{x['count']}\t{x['codepoint']}" for x in C)+'\n','utf-8',newline='\n')
(allow/(TITLE+'.allow')).write_text('# 无需字形替换或半角假名豁免。\n#@no-final-period: 原始 Textout 的台词多数以闭引号接 pause，末句没有句点；如 SEEN2000 @0x101B 的ブランカ台词。全部段行逐条回源一致，保留原标点。\n','utf-8',newline='\n')
script_names=['polwhite_extract.py','polwhite_audit.py','polwhite_inventory.py','polwhite_native_validate.py','polwhite_report.py','happygift_inspect.py','happygift_flow.py','rl_decomp.py','rl_parse.py','kare_dx_extract.py']
versions='\n'.join(f"- `{name}`：`{hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest()}`。" for name in script_names)
auto_rows=[p for p in P if p['reason']=='auto']
auto_sources='\n'.join(f"- SEEN{p['scene']:04d} `@0x{p['end']:X}`，窗口 {p['window']}：此前页段行 {','.join(map(str,p['segments']))}，整页行 {p['merged']}。" for p in auto_rows)
PY='C:\\Users\\(略)\\.workbuddy\\binaries\\python\\envs\\default\\Scripts\\python.exe'
SK='C:\\Users\\(略)\\.workbuddy\\skills\\vn-custom-bytecode-text'
report=f'''---
作品: "{TITLE}"
平台: PC-JP
引擎: RealLive 1.4.7.3 / bytecode 10002
行数: {X['lines']}
日期: 2026-11-14
---

- **版式**：双版对照（按实际显示页；段行 {X['stats']['segments']}，多段合并页 {X['stats']['merged_pages']}；单段页不重复）。
- **输出**：`提取结果/{TITLE}.txt`。
- **编码**：UTF-8 BOM、纯 LF，无空行；保留日文、原字形、空格和标点，不翻译、不润色。
- **总计**：{X['lines']} 行、{X['chars']} 字符（不含 BOM 和 LF）、{X['bytes']} 字节。
- **SHA256**：`{X['sha256']}`。
- **品检**：{quality}。

## 来源和范围

用户指定技能：`<本地路径>`。源 RAR 为 `{V['archive']}`，{V['archive_size']} 字节；使用用户给定密码 `otoame` 列清单，归档和成员均标记为未加密。RAR 有 2 项：一个目录和一个 ISO，没有同捆补丁或额外脚本。

ISO 已由用户解出并挂载为 `D:/`，大小 {V['iso_size']} 字节；完整 ISO 清单 {V['iso_entries']} 项，对应 {V['disc_files']} 个文件、13 个目录。运行窗口 PID 22220 指向 `C:/OCELOT/WHITE_E/REALLIVE.EXE`。Setup.ini 的安装配置和 HKCU/Software/OCELOT/WHITE_E 的资源路径均明确：安装位置为 `C:/OCELOT/WHITE_E`，媒体在 `D:/`。安装根的 4 个文件是 REALLIVE.EXE、GAMEEXE.INI、SEEN.TXT、WHITE_E.ico；没有改写原始游戏、脚本或用户存档。

安装版与挂载盘的 SEEN.TXT、GAMEEXE.INI、REALLIVE.EXE 分别逐文件 SHA256 一致。脚本是唯一的 SEEN.TXT，{I['seen_size']} 字节，摘要 `{I['seen_sha256']}`。GAMEEXE.INI 的摘要 `{V['verified']['GAMEEXE.INI']['installed_sha256']}`；原可执行文件摘要 `{V['verified']['REALLIVE.EXE']['installed_sha256']}`。

资源及非正文按用途处置：946 个 G00 为图像，55 个 OGG 为声音，6 个 OVK 为语音容器，28 个 HIK 为图像动画，mode.cgm 的 CGTABLE 签名为回想图像解锁表。_omake 的三段视频为其他系列宣传及本系列 DEMO，没有独立文本脚本；未转录宣传视频的画面或音频。html/review.html 是客服投稿表单。WHITE_E.env 是光盘标识，Autorun.inf 和 Setup.ini 属启动/安装配置。directx/ 与 test/ 是 DirectX 组件、驱动和媒体检测工具，未知 DAT 小文件的 PC-9821 签名与所在驱动目录相符。未发现追加叙事脚本、辞典或文字选项；不从图片猜写菜单文字。

## 容器、字节码及调用覆盖

10,000 项 TOC 中有 7 个非空索引场景：9、200、201、202、203、2000、9999。各场景均为 464 字节头、编译版本 10002；标准 256 字节 XOR 和 LZSS 解压通过，消费长度等于压缩块长度，字节码消费及所有目标入口闭合。无二级 XOR。索引成员范围终止于 {I['indexed_end']}，源文件的其余 {I['seen_size']-I['indexed_end']} 字节没有 TOC 引用，不当作可载入正文，也不声称已解码这些字节。

按 #SEEN_START=0200 建立指令图，处理本地 goto、条件、表跳转、gosub、跨场景 jump/farcall 和返回。全部 7 个场景均有实际入边；正文集中在 SEEN2000，5056 条真实 Textout 全部收录，涵盖本篇完整叙事及结尾。其余场景承载标题/CG/系统流程及雪花粒子特效子程序。没有未解动态跳转、缺失入口或遗漏选项。

7 个 `ＳｅｅｎＥｎｄ` 记录是 RLMachine::PerformTextout 的 Halt 哨兵，尾随 U+F8F3 是终止填充，未作为正文。正文非 ASCII 参数候选中，14 个是 __doruby_on 的读音、1 个是 Sys:title 的「本編」，5 个是语音整数参数被 cp932 探针误识别；SEEN201 的「苗字」「名前」是输入界面参数。没有遗漏可显示的正文字符串命令。引用的 SEEN9 仅创建 SNOW 图形对象及设定数字运动参数，不承载文字。

## 点击、翻页和姓名证据

复用 `scripts/rlvm-source/` 的 libreallive 和消息处理实现作结构说明，再以本作配置、原始字节码和本作原引擎显示核对。处理依据为 module_msg.cc::Msg_pause、spause、par、msgHide、Msg_TextWindow，textout_long_operation.cc::DisplayName、text_window.cc::SetName/SetNameWithoutDisplay/MustLineBreak/HardBrake，以及 rlmachine.cc::PerformTextout。

- 窗口 000、001 的 R_COMMAND_MOD=0；`0:3:17/0`（`23 00 03 11 00 00 00 00`）的 pause 翻页，共 3212 个有效页结束。
- `0:3:205/0`（`23 00 03 CD 00 00 00 00`）为同页等待，共 1712 次；每次新增的文字成为段行，同页多段再输出完整拼接行。原引擎 case1 的 step00→step01 清楚显示新台词在原页下方追加。
- `0:3:3/0` 的 par 与 `0:3:201/0` 的 br 是排版换行，共 2540 次；同次点击内文本合并。原文的开头全角空格和内部半角空格保留。
- 47 次 TextWindow 102 只切换活动窗口，不作为页界。所有切窗都发生在待输出文本已结束后；窗口 000 为 30×5 字符，001 为 18×15 字符，字号 23、横间距 -1。6 个演出页结束于实际 msgHide 151。
- 全库排版模型纳入 NAME_MOD=2 的括号缩进、par 的缩进重置、br、全/半角宽度和禁则悬挂。查出两处容量重置，原引擎分别验证了其实际页界。最终共 3220 个显示页：3212 个 pause 页、6 个 msgHide 页、2 个自动页；窗口 000 为 2909 页，001 为 311 页，无未解释的溢出。

自动页来源：

{auto_sources}

`@0x29400`（168960）之前的六个新增段在前一竖窗页，随后「彼女は、険しい顔をしていた。」回到新页顶部。`@0x7B7B0`（505776）之前的五段在前页，随后「お嬢さま！？」单独出现在新页，后面的 pause 不重复此单段页。Native case1 steps05/06、case2 steps04/05 的截图保存在 allow 的本作 runtime 目录；旧页淡化的演出不当作再次新增文字。

窗 000 和 001 的 NAME_MOD=2，SetName 仅在模式 0 输出姓名、SetNameWithoutDisplay 仅在模式 1 绘制名字窗，因此本作姓名不显示。原引擎 case1 step01 的源记录为 `【パリア】「リシュリー、待て。行くな！　――って、スノウ……！？」`，屏幕仅显示台词；case2 的スノウ和プリムローズ标签也不显示。消费 1925 个隐藏姓名标签（含括弧共 11841 字符），不冠名、不补引号；心声的原括号保留。NAME.A/B 虽为空，但全文没有引用姓名宏或 PRINT 表达式，无须猜填。

14 对 ruby 命令只改变读音绘制，保留对应基底文字，读音参数不进入正文。

原引擎验证副本位于 `_work_polwhite_ea/native_case1`、`native_case2`。为了隔离实例，仅改副本的窗口类标识、配置和脚本入口跳转；显示、字符宽度、消息及翻页处理机器代码原样保留。使用单独注册表与存档位置、原场景字节码和 D:/ 资源。测试推进仅发送给自建进程，测试进程已停止，用户 PID 22220 未被发送推进输入。

## 字符和产物校验

4923 条段行逐条从源 Textout 重建，所有 5056 个记录各消费一次，无缺失或重复来源；916 个合并页按来源段拼接。字符闭合：153354 原始文字减 11841 隐藏标签 = 141513 个实际新增字符；整页合并行另有 73501 字符，合计 215014 字符。

非日文字符台账共 6 种：`―`、`…`、`♪`、`“`、`”` 和半角空格，均已按行号与脚本偏移核实。唯一 ASCII 命中是旁白「―― 一瞬、なにが起こったのか、リシュリーは理解できないでいた。」内的原始半角空格；无拉丁字母、半角假名、PUA、未映射字形或未还原变量。172 条多括号候选均是源命令所定义的完整段或整页；段行和合并行的开闭数量异常均为 0，不以此代替页界证据。

allow 保存本作 .charset/.allow、逐行来源、精确 layout map、字符/ASCII/结构审计、页表、归档和光盘清单及运行截图。最终技能品检结果：{quality}。通过时文本 SHA256 为 `{X['sha256']}`，与来源审计及交付文件一致；来源及显示规则的未决项为 0。

品检的三条长度警告是窗口 001 的整页合并行 L887/L1238/L2799，显示宽度分别 200.5/221.5/206，均经字号、缩进、排版换行和原引擎页容量核对。相邻同文 L3563/L3564「　知っている。」分别来自 SEEN2000 @0x50184（328068）和 @0x501A8（328104），各接独立 pause；按两个实际点击保留，未按文字去重。没有机器错误。

## 复现

```powershell
& '{PY}' -B -X utf8 'C:\\game\\_Trans\\tools\\polwhite_extract.py' --source 'C:\\OCELOT\\WHITE_E' --prepare --publish
& '{PY}' -B -X utf8 'C:\\game\\_Trans\\tools\\polwhite_audit.py'
& '{PY}' -B -X utf8 '{SK}\\scripts\\check_text.py' 'C:\\game\\_Trans\\提取结果\\{TITLE}.txt' --dual --expect-dual --report 'C:\\game\\_Trans\\解析报告\\{TITLE}_解析报告.md' --allow 'C:\\game\\_Trans\\解析报告\\allow\\{TITLE}.allow' --layout-map 'C:\\game\\_Trans\\解析报告\\allow\\{TITLE}.layout.json'
```

本次工具 SHA256：

{versions}

## 清理状态

本次先核实上一作的 `<工作区>`，其结论与复现工具已记录。删除被自动审批拒绝，仅返回 `blocked by policy`，所以该目录仍在；没有更换工具或分批绕过。清理记录为 `清理记录/2026-11-14_誰にでも裏がある临时产物.md`。本作 `_work_polwhite_ea` 保留提取和原引擎验证中间文件，非交付成品。测试子目录有指向 D:/ 媒体的目录联接，不能递归遍历联接删除媒体。
'''
dest=ROOT/'解析报告'/(TITLE+'_解析报告.md')
dest.write_text(report,encoding='utf-8-sig',newline='\n')
print('REPORT',dest,'ROWS',X['lines'])
