"""Package checked FE provenance and write the extraction report."""
from pathlib import Path
import json,hashlib,shutil,argparse,collections
ap=argparse.ArgumentParser();ap.add_argument('--checked',action='store_true');args=ap.parse_args()
ROOT=Path(__file__).resolve().parent.parent;W=ROOT/'_work_polwhite_fe'
def read(name):return json.loads((W/(name+'.json')).read_text('utf-8'))
X=read('extraction');I=read('inspection');A=read('audit');V=read('inventory')
C=read('charset_sources');P=read('page_details');F=read('flow');O=read('line_origins')
TITLE=X['title'];allow=ROOT/'解析报告/allow';allow.mkdir(exist_ok=True)
assert A['output_sha256']==X['sha256'] and not A['unexpected_overflows']
assert X['stats']['records']==6771 and len(F['excluded_text'])==1
quality='待运行最终技能品检'
if args.checked:
    log=(W/'check.log').read_text('utf-8-sig')
    assert 'RESULT: PASS' in log and TITLE in log
    assert hashlib.sha256(Path(X['output']).read_bytes()).hexdigest()==X['sha256']
    shutil.copyfile(W/'check.log',allow/(TITLE+'.check.log'))
    quality='PASS（技能 check_text.py 退出码 0；1375 个来源映射页全部一致）'
for filename,ext in [('line_origins','sources'),('layout_map','layout'),('audit','audit'),('inventory','inventory'),('charset_sources','charset'),('ascii_audit','ascii'),('structure_audit','structure'),('page_details','pages'),('rar_manifest','rar'),('iso_manifest','iso'),('disc_manifest','disc')]:
    shutil.copyfile(W/(filename+'.json'),allow/(TITLE+'.'+ext+'.json'))
runtime=allow/(TITLE+'.runtime');runtime.mkdir(exist_ok=True)
for name in ('native_case1_step02.png','native_case1_step03.png','native_case1_step04.png','native_case1_step05.png','native_case2_step00.png','native_case2_step01.png'):
    shutil.copyfile(W/name,runtime/name)
# Each character and all ASCII sources have been read with script provenance.
assert {x['char'] for x in C}==set('―…“”1796Z')
(allow/(TITLE+'.charset')).write_text('# 非日文字符已逐种回源核实，保留原字形\n'+'\n'.join(f"{x['char']}\t{x['count']}\t{x['codepoint']}" for x in C)+'\n','utf-8',newline='\n')
(allow/(TITLE+'.allow')).write_text('# 不需要字形或宏豁免。\n#@no-final-period: 原始 Textout 的闭引号与 pause 定义台词终点；全部段行与源文一致，保留原标点。\n','utf-8',newline='\n')
tools=['polwhite_extract.py','polwhite_audit.py','polwhite_inventory.py','polwhite_native_validate.py','polwhite_capture.py','polwhite_finish_native.py','polwhite_fe_report.py','happygift_inspect.py','happygift_flow.py','rl_decomp.py','rl_parse.py','kare_dx_extract.py']
versions='\n'.join(f"- `{n}`：`{hashlib.sha256((ROOT/'tools'/n).read_bytes()).hexdigest()}`。" for n in tools)
autos='\n'.join(f"- SEEN{p['scene']:04d} @0x{p['end']:X}：窗口 {p['window']}，前页段行 {','.join(map(str,p['segments']))}，整页行 {p['merged'] or '无（单段页）'}。" for p in P if p['reason']=='auto')
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
- **编码**：UTF-8 BOM、纯 LF、无空行；保留日文原文、原字形、空格和标点。
- **总计**：{X['lines']} 行、{X['chars']} 字符（不含 BOM/LF）、{X['bytes']} 字节。
- **SHA256**：`{X['sha256']}`。
- **品检**：{quality}。

## 来源和范围

按用户指定技能 `<本地路径>` 提取。源 RAR 为 `{V['archive']}`，{V['archive_size']} 字节；使用给定密码 otoame 列清单，成员标记未加密。RAR 2 项：一个目录、一个初回特典版 ISO，无同捆补丁。

用户已解出并挂载 ISO 为 D:/。ISO 为 {V['iso_size']} 字节，完整成员清单 {V['iso_entries']} 项（1528 文件、13 目录）。游戏 PID 22072，安装于 C:/OCELOT/WHITE_F；Setup.ini 与 #REGNAME=OCELOT\\WHITE_F 对应。安装目录的 SEEN.TXT、GAMEEXE.INI、REALLIVE.EXE 与挂载盘逐文件 SHA256 相同。原游戏、原脚本和用户存档未改写。

唯一脚本容器为 SEEN.TXT，{I['seen_size']} 字节，摘要 `{I['seen_sha256']}`。配置摘要 `{V['verified']['GAMEEXE.INI']['installed_sha256']}`，引擎摘要 `{V['verified']['REALLIVE.EXE']['installed_sha256']}`。引擎文件与上一作已验证的 1.4.7.3 原引擎完全一致；本作配置、字节码和运行画面分别核对，没有沿用另一作的自动翻页偏移。

831 个 G00 为图像，53 个 OGG 和 6 个 OVK 为音频/语音，27 个 HIK 为图像动画；mode.cgm 是 CGTABLE 解锁表。_omake 的 polyphonica_34op.mpg、白 DEMO 和 THE_BLACK 特报是宣传视频，没有独立文本脚本，不转录宣传片。html/review.html 是客服投稿表。WHITE_F.env、Autorun.inf、Setup.ini 属光盘/安装配置；directx/、test/ 的驱动、示例音视频与带 PC-9821 签名的 DAT 小文件属于组件/测试工具。已列完整清单并按用途处置，未发现补丁、额外剧情脚本、辞典或文字选项。

## 字节码、调用与过滤

10,000 项 TOC 有 8 个非空场景：9、100、101、102、103、1000、1100、9999。头长 464、版本 10002；标准 256 字节 XOR 与 LZSS 解压均闭合，各场景消费长度等于压缩长度，没有二级 XOR。全部字节码解析完成，跳转目标均落在合法记录。索引结束于 {I['indexed_end']}，尾部 {I['seen_size']-I['indexed_end']} 字节无 TOC 引用，不作为可载入正文，也不声称已解码。

#SEEN_START=0100、#SEEN_MENU=0101；根据本地 goto/条件/表跳转、gosub、跨场景 jump/farcall/return 和 MenuReturn 建立可达图。全部 8 个场景有入边。正文收 SEEN1100「プロローグ」和 SEEN1000「本編」，按序章→本篇排列。标题入口可分别启动这两段；没有额外文字分支或未解动态跳转。序章 1349 个、本篇 5422 个有效 Textout 共 6771 个，均各消费一次。

SEEN1100 @0x2404B 的「プロローグです。」位于 @0x24025 的 Sys:MenuReturn 1201 之后。module_sys.cc::Sys_MenuReturn::AdvanceInstructionPointer 返回 false，处理函数 LocalReset 后 Jump(#SEEN_MENU,0)，不会继续尾随字节码；因此这条调试文本和随后的主篇跳转不可达，排除。其余 8 个 ＳｅｅｎＥｎｄ 与 U+F8F3 是 Halt 哨兵/填充，不输出。

SEEN9 只创建/调整 SNOW 图形对象，没有消息命令或正文；本篇 @550248、@554533 在同页文本尚存时 farcall 此场景，返回后继续同页，不额外切页。非 ASCII 参数普查共 502 个候选：55 个 ruby 读音、2 个章标题、2 个姓名输入 UI 参数、443 个整数语音参数被 cp932 探针误识别；无遗漏的正文字符串命令。55 对 ruby 仅收基底，不重复收读音。原文没有姓名宏或 PRINT 表达式，NAME.A/B 为空不影响文本。

## 点击、页界与名札

结构依据 scripts/rlvm-source/ 的 module_msg.cc、textout_long_operation.cc、text_window.cc 与 rlmachine.cc；本作原引擎隔离副本交叉验证。窗口 000/001 的 R_COMMAND_MOD=0、NAME_MOD=2、字号 23、横间距 -1，容量分别 30×5 和 18×15。

- pause 0:3:17/0 翻页；原字节 `23 00 03 11 00 00 00 00`。有文本的有效页结束 2932 次。
- spause 0:3:205/0 同页等待，3549 次；按每次新增文字生成段行，多段页额外输出整页合并行。
- par 0:3:3/0 和 br 0:3:201/0 仅排版换行，共 6187 次；同次点击内合并。par 重置缩进，br 保留缩进。
- 窗口切换 102 共 140 次；都发生于待输出页结束后，不以切窗命令充当页界。msgHide 151 共 8 个有文字页结束，空页隐藏不生成空行。
- 全库排版模型纳入半角宽度、隐藏姓名后的引号缩进、排版换行与禁则悬挂。共 2942 页：2932 pause、8 msgHide、2 自动页；窗口 000 为 2057 页、001 为 885 页，无未解释的容量溢出。

自动页来源：

{autos}

序章 @46002 的プリムローズ台词在新竖窗页顶部出现。native case1 step03 显示前页四段，step04 显示新页的「まあ、手を繋ぐことさえ許してもらえたことのない犬が、ほざきますこと」。本篇 @304286 的ミス・プリズム台词在新横窗页出现；case2 step00/01 对照为此前四行台词与新页的「たしかに、あなたならよくご存じでしょうね」。两处都是消费隐藏姓名之后、首个可见字符之前翻页，可按 Textout 起点切页；旧页淡化背景不当作再次新增文字。

NAME_MOD=2：SetName 不绘制正文姓名，SetNameWithoutDisplay 仅模式 1 才绘制名字窗。两个本作运行样例均仅显示台词，没有プリムローズ/ミス・プリズム名札。共消费 2737 个隐藏姓名标签（含括弧 16449 字符），不冠名、不补引号；旁白/心声与原标点保留。未使用窗口 002 的可见名字窗模式。

原引擎验证仅改测试副本的窗口类标识、配置与入口跳转，显示/换行/消息处理机器代码不变；采用独立注册表和存档位置以及原场景字节码，测试输入只发送给自建进程。两个测试进程均已停止，测试注册表项已删除，用户游戏恢复前台。

## 来源与字符验收

6481 段行和 1375 合并页共 7856 行。序章为 1251 段行+290 合并页，本篇为 5230 段行+1085 合并页。6771 个 Textout 与全部段行逐条重建一致，没有重复或缺失来源；1375 个合并页与段行拼接一致。字符闭合：195347 原始字符-16449 隐藏标签=178898 新增显示字符；合并行另有 136569 字符，共 315467 字符。

非日文字符 9 种：―、…、“、”、1、7、9、6、Z，已逐种回源。4 条 ASCII 命中只来自 SEEN1000 @5220 的「1796年」与 @184248 的「ZZZZZZ…」，各有段行及合并行；数字为音乐史年份，Z 是原文睡眠拟声，保留。没有未解宏、控制码、替换字符、半角假名或 PUA。533 条多括号探针均是源定义的段行或合并页，段行/合并行括号失衡均为 0；统计不代替页界证明。

allow 保存来源、页映射、字符/ASCII/结构审计、完整成员清单和关键运行截图。最终品检：{quality}。通过时 SHA256 与上面的交付摘要相同，未决来源/姓名/页界问题为 0。

机器警告已回源：2 条拉丁字母行是上述 Z 拟声的段行/整页；超长的 L1352、L5319 都是窗口 1 整页合并行，各由 4 个段行组成，排版模型确认页容量足够；相邻同文 L173/L174「ブランカ」分别来自 SEEN1100 @12359、@12465，各有独立 pause，保留两个实际点击。没有机器错误，完整检查日志保存在本作 check.log。

## 复现

```powershell
& '{PY}' -B -X utf8 'C:\\game\\_Trans\\tools\\polwhite_extract.py' --variant fe --prepare --publish
& '{PY}' -B -X utf8 'C:\\game\\_Trans\\tools\\polwhite_audit.py' --work 'C:\\game\\_Trans\\_work_polwhite_fe'
& '{PY}' -B -X utf8 'C:\\game\\_Trans\\tools\\polwhite_fe_report.py'
& '{PY}' -B -X utf8 '{SK}\\scripts\\check_text.py' 'C:\\game\\_Trans\\提取结果\\{TITLE}.txt' --dual --expect-dual --report 'C:\\game\\_Trans\\解析报告\\{TITLE}_解析报告.md' --allow 'C:\\game\\_Trans\\解析报告\\allow\\{TITLE}.allow' --layout-map 'C:\\game\\_Trans\\解析报告\\allow\\{TITLE}.layout.json'
```

本次工具 SHA256：

{versions}

新增上游证据为 https://github.com/eglaysher/rlvm/blob/master/src/modules/module_sys.cc ，本地保存于 scripts/rlvm-source/module_sys.cc；不把上游实现替代本作配置/字节码/运行验证。

## 清理状态

上一作复现结论已补入 references/engines/reallive.md。删除 <工作区> 被自动审批拒绝，只返回 blocked by policy；目录仍在，未更换工具或分批绕过。清理记录见 清理记录/2026-11-14_エンドレスアリア临时产物.md。本作 _work_polwhite_fe 为中间文件与隔离运行副本，非交付成品，验证子目录含指向 D:/ 媒体的目录联接。
'''
dest=ROOT/'解析报告'/(TITLE+'_解析报告.md')
dest.write_text(report,'utf-8-sig',newline='\n')
print('REPORT',dest,'ROWS',X['lines'],'QUALITY',quality)
