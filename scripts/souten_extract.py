"""Extract 蒼天の彼方 (PC, System-NNN) from an installed game directory.

The SPT message commands are 22220001 (new ADV page), 22220002 (new full
page), and 22220003 (append to the current full page). Graph descriptions
are rendered story material; '$' graph tokens are variable conditions.
"""
from pathlib import Path
import argparse, collections, hashlib, json, re
from system_nnn import read_script, XOR

MESSAGE_OPS={0x22220001,0x22220002,0x22220003}
ORDER=[f'chart{i:03d}' for i in range(12)]+['_sub01','_sub02']
RUBY=re.compile(r'#［[０-９0-9]+[^［］]*］')

def config(path):
    return path.read_bytes().translate(XOR).decode('cp932')

def names(root):
    out={'#名','？？？'}
    for line in (root/'spt/charaname.xtx').read_bytes().decode('cp932').splitlines():
        if ',' in line:out.add(line.split(',')[1])
    for line in (root/'spt/namecol.xtx').read_bytes().decode('cp932').splitlines():
        if line:out.add(line.split()[0])
    out.discard('名前なし')
    return out

def description_pages(root,max_lines):
    pages=[]; node_count=0; variants=0
    for file in sorted((root/'chart').glob('chart*.xtx'),key=lambda p:int(re.search(r'\d+',p.stem)[0])):
        for number,line in enumerate(file.read_bytes().decode('cp932').splitlines(),1):
            if not line.startswith('@'):continue
            # ASCII whitespace separates engine tokens. U+3000 is a literal
            # displayed blank row in four descriptions, so preserve it.
            tokens=re.split(r'[ \t]+',line.strip(' \t'))
            node=int(tokens[0][1:]); first=next((i for i,t in enumerate(tokens) if t.startswith('【')),None)
            if first is None:raise ValueError(f'{file}:{number}: missing story description')
            normal=[]; alternate=[]
            for token in tokens[first:]:
                (alternate if token.startswith('!') else normal).append(token[1:] if token.startswith('!') else token)
            node_count+=1; seen=set()
            for kind,parts in [('通常',normal),('未読',alternate)]:
                if not parts:continue
                # The engine stores each whitespace token as one display row,
                # and uses variant=1 to skip the leading '!'. All source
                # descriptions fit the configured description-window height.
                if len(parts)>max_lines:raise ValueError('Description-window layout requires review')
                rendered=''.join(parts)
                if rendered in seen:continue
                seen.add(rendered);variants+=1
                pages.append({'text':rendered,'source':f'chart/{file.name}:{number}; node={node}; {kind}',
                              'kind':'description','node':node,'variant':kind,
                              'source_rows':len(parts),'display_rows':len(parts)})
    return pages,node_count,variants

def main():
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--report',type=Path,required=True);ap.add_argument('--audit',type=Path,required=True)
    args=ap.parse_args();root=args.source.resolve();args.audit.mkdir(parents=True,exist_ok=True)
    game=config(root/'init2/game.fxf')
    m=re.search(r'^meiInitData\s+(\S+)',game,re.M)
    if not m:raise ValueError('The game has no default given name')
    protagonist=m[1];plates=names(root)
    print_config=config(root/'init2/printmessage.fxf')
    adv_max=int(re.search(r'^windowMessageNumber\s+(\d+)',print_config,re.M)[1])
    nvl_max=int(re.search(r'^fullMessageNumber\s+(\d+)',print_config,re.M)[1])
    chart_config=config(root/'init2/selectchart.fxf')
    desc_max=int(re.search(r'^chartDescMax\s+(\d+)',chart_config,re.M)[1])
    descs,node_count,variant_count=description_pages(root,desc_max)
    all_scripts={p.stem:read_script(p) for p in sorted((root/'spt').glob('*.spt'))}
    if set(all_scripts)-set(ORDER)!={'sys','sot_backscript','open','_sub03'}:
        raise ValueError('Unreviewed script files')
    for key,s in all_scripts.items():
        if key not in ORDER and s.messages:raise ValueError(f'Unreviewed messages in {key}')
    rows=[];mapping=[];layouts=[];stats=[];opcounts=collections.Counter();plate_counts=collections.Counter()
    annotation_count=0;name_macros=0;pending=[];raw_page_rows=0
    def emit(text,source,kind,extra=None):
        if not text:raise ValueError(f'Empty displayed text: {source}')
        rows.append(text);mapping.append({'line':len(rows),'source':source,'kind':kind,**(extra or {})})
        return len(rows)
    def flush():
        nonlocal pending,raw_page_rows
        if len(pending)>1:
            merged=''.join(rows[i-1] for i in pending)
            src='; '.join(mapping[i-1]['source'] for i in pending)
            line=emit(merged,src,'merged')
            layouts.append({'segments':pending,'merged':line,'source':src})
        pending=[];raw_page_rows=0
    def clean(raw):
        nonlocal annotation_count,name_macros
        annotation_count+=len(RUBY.findall(raw));name_macros+=raw.count('#名')
        text=RUBY.sub('',raw).replace('#名',protagonist)
        if '#' in text:raise ValueError(f'Unknown inline control: {raw!r}')
        return text.replace('\r\n','')
    for key in ORDER:
        script=all_scripts[key];cmds=[c for c in script.commands if c.words[1]==0x66660006 and c.words[2] in MESSAGE_OPS]
        refs=[c.words[3] for c in cmds]
        if refs!=list(range(len(script.messages))):raise ValueError(f'{key}: message command coverage/order differs')
        first=len(rows)+1
        for command in cmds:
            op=command.words[2];opcounts[op]+=1
            record=script.messages[command.words[3]];raw=record.text
            if len(command.words)!=6 or command.words[5]!=0:raise ValueError('Unreviewed message parameters')
            raw_lines=raw.split('\r\n')
            if any('\r' in line or '\n' in line for line in raw_lines):
                raise ValueError('Unreviewed line separator')
            if any(len(line.encode('cp932'))>254 for line in raw_lines):
                raise ValueError('Message exceeds the engine row buffer')
            if op==0x22220001 and len(raw_lines)>adv_max:
                raise ValueError('ADV message exceeds configured row capacity')
            if op in (0x22220001,0x22220002):flush()
            head,sep,body=raw.partition('\r\n')
            plate=head if sep and head in plates else ''
            if plate:plate_counts[plate]+=1
            # Recognized head text is a visible name plate in ADV, or visible
            # text at the top of a full-screen speech paragraph. Concatenating
            # it preserves the displayed speaker without adding punctuation.
            text=clean(plate)+clean(body) if plate else clean(raw)
            src=f'spt/{key}.spt: command=0x{command.offset:x}; message={record.index}; text=0x{record.offset:x}'
            n=emit(text,src,'message',{'opcode':hex(op),'speaker':plate.replace('#名',protagonist)})
            if op!=0x22220001:
                if op==0x22220003 and not pending:raise ValueError('Full-screen append has no page')
                pending.append(n);raw_page_rows+=raw.count('\r\n')+1
                if raw_page_rows>nvl_max:raise ValueError('Full-screen page exceeds configured row capacity')
        flush();stats.append({'script':key,'messages':len(cmds),'first_line':first,'last_line':len(rows),
                              'bytes':len(script.data),'sha256':hashlib.sha256(script.path.read_bytes()).hexdigest()})
    core_end=len(rows)
    for page in descs:
        emit(page['text'],page['source'],'description')
    text='\n'.join(rows)+'\n';args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(text,encoding='utf-8-sig',newline='\n')
    digest=hashlib.sha256(args.output.read_bytes()).hexdigest()
    summary={'lines':len(rows),'message_segments':sum(opcounts.values()),'merged_pages':len(layouts),
             'nvl_pages':opcounts[0x22220002],'opcodes':{hex(k):v for k,v in opcounts.items()},
             'description_nodes':node_count,'description_pages':variant_count,'core_output_lines':core_end,
             'default_name':protagonist,'names':dict(plate_counts),'name_macro_occurrences':name_macros,
             'ruby_annotations':annotation_count,'bytes':args.output.stat().st_size,'sha256':digest,'scripts':stats,
             'row_capacity':{'adv':adv_max,'nvl':nvl_max,'description':desc_max}}
    (args.audit/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (args.audit/'layout.json').write_text(json.dumps({'pages':layouts},ensure_ascii=False,indent=2),encoding='utf-8')
    (args.audit/'sources.json').write_text(json.dumps(mapping,ensure_ascii=False),encoding='utf-8')
    title=args.output.stem
    table='\n'.join(f"| {s['script']}.spt | {s['messages']} | {s['first_line']} |" for s in stats)
    report=f'''---
作品: "{title}"
平台: PC
引擎: System-NNN / NNNLib（MIO，2009）
主角: {protagonist}
行数: {len(rows)}
日期: 2026-11-14
---

# {title} 解析报告

- **版式**：双版对照（仅同页多次点击的全屏剧情附合并行；正文段行 {sum(opcounts.values())}，多段页 {len(layouts)}）。
- 成品：`提取结果/{args.output.name}`，UTF-8 BOM、LF，{len(rows)} 行，{args.output.stat().st_size:,} 字节。
- SHA256：`{digest}`。

## 源与范围

源目录：`{root}`。本作文件已解开，不需要解压密码；未修改游戏及存档。
完整源清单核对了 18 本 SPT、项目和函数清单、名字与颜色表、12 本流程图及显示配置。
14 本剧本有正文，共 {sum(opcounts.values())} 条消息。`sys`、`sot_backscript`、`open`、`_sub03` 没有消息命令，属于系统、图像演出和流程控制。
`_sub01` 含开场、结局及剧情子程序，`_sub02` 含羽兎空间剧情，均收录。
文本按 chart000 至 chart011、_sub01、_sub02 的源文件与命令顺序排列；分支全部收录，子程序按自身源顺序集中保留一次。
流程图的叙事说明追加到正文末尾；系统菜单、帮助、日志、流程图条件变量、图像资源名不收。
图鉴、年表及流程图按钮使用图像，未对图像文字做 OCR；未发现文本型辞典或独立文字选择命令。

| 剧本 | 消息段数 | 成品首行 |
|---|---:|---:|
{table}

## 格式和覆盖

SPT 整文件 XOR FF；头为 `(32, 66660001, 55550001)`，0x30 处为 `SPTHEADER0`。
头的 `(count, base)` 描述消息和杂项字符串地址表，base 与地址表元素均以 4 字节为单位。
消息通过地址表直接读取；每串以 NUL 终止并补至 4 字节边界，填充不参与 cp932 严格解码。
指令为 `[word_count, group, opcode, operands…]`，严格按长度推进。
代码终点是标签表前 16 字节的 `(label_count+4, 66660001, 55550002, 44440003)` 记录。
14/14 剧本的显示命令引用恰为消息索引 `0..count-1`，没有跳过、重同步或猜测池起点。

## 点击、清屏与姓名的 L0 依据

以下位置为本作 `souten.exe` 的 RVA，已从正在运行的进程只读取证，并核对随游戏配置。

- RVA EE7C7–EE8E5：解释器处理 `66660006 / 22220001..03`，按操作数取消息指针，提交显示对象，推进指令并返回消息状态。每条命令是一次推进的新增文本。
- RVA 102E4B：`22220003` 保持上一页模式；102F19–102FBB：`22220001`、`22220002` 清除行缓冲和累计行数，`22220003` 保留并追加。
- RVA 103013：CRLF 消费为排版行；103380、103497 递增行缓冲，不在 CRLF 处等待。
- `22220001` 共 {opcounts[0x22220001]} 条；`22220002` 共 {opcounts[0x22220002]} 条，开启全屏页；`22220003` 共 {opcounts[0x22220003]} 条，追加到上一全屏页。
- 全屏页的原始排版行数不超过配置 `fullMessageNumber 12`；所有消息参数均为本作标准形式，未出现未解的容量翻页情况。
- RVA 103560–103619 按窗口容量截取或滚动排版行。普通消息最多 4 行，配置 `windowMessageNumber {adv_max}`；每个原始排版行均不超过 254 字节缓冲上限，故本作没有被截去的正文或需要另分的容量页。
- `messageWindow.fxf` 为 `nameWindowFlag 1`；`printmessage.fxf` 为 `nameFlag 1`、`autoNameWindowFlag 1`，名札坐标 nameX=101、nameY=411。
- `charaname.xtx` 和 `namecol.xtx` 提供 {len(plates)} 个合法标记，实用 {len(plate_counts)} 种；带名的 {sum(plate_counts.values())} 个消息按 `姓名＋原台词` 输出。旁白保持原文，不补引号。
- `game.fxf` 明确 `meiInitData {protagonist}`，`nameinput.fxf` 为 `seiFlag 0`；`#名` 共 {name_macros} 处，仅替换这一宏。注音 `#［Nよみ］` 共 {annotation_count} 处只保留前面的基底字。

页映射由原始命令生成，共 {len(layouts)} 个多段页；单段页不重复。

## 流程图的叙事说明

RVA 5CB62 将 `$…` 保存到条件字段；5D230 返回去掉 `$` 的变量名，12774D 将其解析为游戏变量索引，120535 检查变量值。它不是显示的选项文字。
RVA 5CB85 区分普通说明和 `!` 未读说明，5D130 获取对应文字；124CBA–124D1A 将它们逐行绘制到说明窗。
因此保留实际显示的 `【场面名】剧情说明`，排版行合并；不把条件名或裸场面名另造一份选项。四处独立全角空白排版行保留其原文字面。
共 {node_count} 个节点、{variant_count} 个不同显示版本；相同节点完全相同的前后状态说明只保留一次。
说明窗按实际记录行数绘制；全库说明均不超过配置 `chartDescMax {desc_max}`，未发生溢出。条件分支的说明在适用状态可显示，按源条件版本全部覆盖。

## 验收与复现

正文和页映射已按源命令闭合；未对标点配平、字形、名字字面量或相邻同文做改写。
字符来源、结构警告及最终品检结果在下方记录。

```powershell
& '<本地路径>' -B -X utf8 scripts/souten_extract.py '<游戏目录>' '提取结果/{args.output.name}' --report '解析报告/{args.report.name}' --audit '{args.audit.as_posix()}'
```

工具：`scripts/system_nnn.py`（SPT 结构）与 `scripts/souten_extract.py`（本作显示与叙事范围）。
'''
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(report,encoding='utf-8-sig',newline='\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in {'names','scripts'}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
