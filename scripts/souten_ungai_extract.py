"""Extract the standalone Japanese 雲外蒼天 short story using System-NNN.

Reuses the verified SPT reader and the original Souten's name/ruby grammar.
All text records are checked against their source commands before delivery.
"""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import json
import re
import zlib

from _lib.system_nnn import read_script
from souten_extract import config, names, RUBY


def jp_character(ch):
    return any(lo <= ord(ch) <= hi for lo, hi in (
        (0x3000, 0x30ff), (0x4e00, 0x9fff), (0xff01, 0xff60), (0xffe0, 0xffee)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--report', required=True, type=Path)
    ap.add_argument('--evidence', required=True, type=Path)
    args = ap.parse_args()
    root = args.source.resolve()
    args.evidence.mkdir(parents=True, exist_ok=True)
    game = config(root / 'init2/game.fxf')
    default = re.search(r'^meiInitData\s+(\S+)', game, re.M)[1]
    printconfig = config(root / 'init2/printmessage.fxf')
    adv_capacity = int(re.search(r'^windowMessageNumber\s+(\d+)', printconfig, re.M)[1])
    for setting in ('nameFlag', 'autoNameWindowFlag'):
        assert re.search(r'^' + setting + r'\s+1\s*$', printconfig, re.M)
    assert re.search(r'^nameWindowFlag\s+1\s*$', config(root / 'init2/messageWindow.fxf'), re.M)
    assert re.search(r'^seiFlag\s+0\s*$', config(root / 'init2/nameinput.fxf'), re.M)
    project = (root / 'spt/project.xtx').read_text('cp932').splitlines()
    scripts = {p.stem: read_script(p) for p in sorted((root / 'spt').glob('*.spt'))}
    assert set(scripts) == set(project) == {'sys', 'sot_backscript', 'sot_ungai001'}
    assert not scripts['sys'].messages and not scripts['sot_backscript'].messages
    plate_names = names(root)
    rows, mapping, stats = [], [], []
    macros = ruby = max_rows = max_row_bytes = 0
    speakers = collections.Counter()
    for key, script in scripts.items():
        message_ops = [c for c in script.commands if len(c.words) > 2 and c.words[1] == 0x66660006]
        assert all(c.words[2] in {0x22220001, 0x22220004, 0x22220005} for c in message_ops)
        display = [c for c in message_ops if c.words[2] == 0x22220001]
        assert [c.words[3] for c in display] == list(range(len(script.messages)))
        for command in display:
            assert len(command.words) == 6 and command.words[5] == 0
            record = script.messages[command.words[3]]
            raw = record.text
            lines = raw.split('\r\n')
            assert len(lines) <= adv_capacity
            assert all('\r' not in s and '\n' not in s for s in lines)
            assert all(len(s.encode('cp932')) <= 254 for s in lines)
            max_rows = max(max_rows, len(lines))
            max_row_bytes = max(max_row_bytes, *(len(s.encode('cp932')) for s in lines))
            head, sep, body = raw.partition('\r\n')
            plate = head if sep and head in plate_names else ''
            if plate:
                assert body.startswith('「'), 'Unreviewed unquoted dialogue'
                speakers[plate.replace('#名', default)] += 1
            macros += raw.count('#名')
            ruby += len(RUBY.findall(raw))
            rendered = RUBY.sub('', raw).replace('#名', default).replace('\r\n', '')
            assert rendered and '#' not in rendered and '\ufffd' not in rendered
            assert not any(ord(ch) < 0x20 or 0xe000 <= ord(ch) <= 0xf8ff for ch in rendered)
            # Cross-check the result against the original decoded payload and
            # separately recorded annotation spans, before writing any output.
            fragments, cursor = [], 0
            for annotation in RUBY.finditer(raw):
                fragments.append(raw[cursor:annotation.start()])
                cursor = annotation.end()
            fragments.append(raw[cursor:])
            assert rendered == ''.join(fragments).replace('#名', default).replace('\r\n', '')
            rows.append(rendered)
            mapping.append({'line': len(rows), 'script': script.path.name,
                            'command_rva': hex(command.offset), 'message_index': record.index,
                            'text_offset': hex(record.offset), 'opcode': hex(command.words[2]),
                            'speaker': plate.replace('#名', default), 'raw': raw})
        stats.append({'script': script.path.name, 'messages': len(script.messages),
                      'display_commands': len(display), 'misc_strings': len(script.strings),
                      'commands': len(script.commands), 'code_end': hex(script.header[9] * 4 - 16),
                      'sha256': hashlib.sha256(script.path.read_bytes()).hexdigest(),
                      'message_group': dict(collections.Counter(hex(c.words[2]) for c in message_ops))})
    assert len(rows) == 119 and sum(s['display_commands'] for s in stats) == 119
    coverage = json.loads((args.evidence / 'archive-coverage.json').read_text('utf-8'))
    assert not coverage['missing'] and not coverage['added'] and not coverage['different_sizes']
    verified = []
    for filename, meta in coverage['members'].items():
        file = root / filename
        if file.suffix in {'.spt', '.fxf', '.xtx', '.dat', '.txt'} or file.name == 'souten_sp.exe':
            assert f'{zlib.crc32(file.read_bytes()) & 0xffffffff:08X}' == meta['CRC'], filename
            verified.append(filename)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(rows) + '\n', encoding='utf-8-sig', newline='\n')
    data = args.output.read_bytes()
    assert data.decode('utf-8-sig').splitlines() == rows
    assert data.startswith(b'\xef\xbb\xbf') and b'\r' not in data
    digest = hashlib.sha256(data).hexdigest()
    charset = collections.Counter(ch for row in rows for ch in row if not jp_character(ch))
    ledger = ['# 每个字符核对到本行原始 SPT 载荷；来源见 sources.json。']
    for ch, count in charset.most_common():
        first = next(item for row, item in zip(rows, mapping) if ch in row)
        raw = first['raw'].replace('#名', default)
        assert ch in raw
        ledger.append(f"{ch}\t{count}\tL{first['line']}\t{first['script']}:message={first['message_index']}")
    ledgerpath = args.report.parent / 'allow' / (args.output.stem + '.charset')
    ledgerpath.parent.mkdir(parents=True, exist_ok=True)
    ledgerpath.write_text('\n'.join(ledger) + '\n', encoding='utf-8', newline='\n')
    review = {'ascii_lines': [], 'unbalanced': [], 'multiple_speeches': [], 'adjacent_duplicates': []}
    for n, row in enumerate(rows, 1):
        if any(0x20 <= ord(ch) < 0x7f for ch in row):
            review['ascii_lines'].append(n)
        if any(row.count(a) != row.count(b) for a, b in [('「', '」'), ('『', '』'), ('（', '）')]):
            review['unbalanced'].append(n)
        if row.count('「') > 1:
            review['multiple_speeches'].append(n)
        if n > 1 and row == rows[n - 2]:
            review['adjacent_duplicates'].append([n - 1, n])
    summary = {'lines': len(rows), 'bytes': len(data), 'sha256': digest, 'default_name': default,
               'message_segments': len(rows), 'merged_pages': 0, 'name_macro_occurrences': macros,
               'ruby_annotations': ruby, 'speakers': dict(speakers), 'raw_row_max': max_rows,
               'raw_row_bytes_max': max_row_bytes, 'adv_capacity': adv_capacity,
               'scripts': stats, 'source_crc_verified': verified,
               'source_verified_lines': len(mapping), 'charset_kinds': len(charset), 'review': review}
    (args.evidence / 'sources.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2),
                                               encoding='utf-8', newline='\n')
    (args.evidence / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                                               encoding='utf-8', newline='\n')
    title = args.output.stem
    table = '\n'.join(f"| {s['script']} | {s['messages']} | {s['display_commands']} | {s['misc_strings']} |"
                      for s in stats)
    report = f'''---
作品: "{title}"
平台: PC
引擎: System-NNN / NNNLib（MIO，2009）
主角: {default}
行数: {len(rows)}
日期: {datetime.date.today().isoformat()}
---

# {title} 解析报告

- **版式**：单版（每条 ADV 消息一次点击一页；段行 {len(rows)}，多段合并页 0）。
- 成品：`提取结果/{args.output.name}`，UTF-8 BOM、纯 LF、无空行，{len(rows)} 行，{len(data):,} 字节。
- SHA256：`{digest}`。

## 来源与范围

游戏目录：`{root}`。源文件已解开；说明书称本作是《蒼天の彼方》的非卖品追加短篇。
原始 `souten_ungai.exe` 为 RAR 自解压文件，归档偏移 90624，含 129 个文件和 10 个目录，均未加密；无需密码。
归档成员与现有游戏目录逐名、逐大小一致，无缺失或新增文件。
正文相关剧本、配置、名字表、说明、场景数据及主程序共 {len(verified)} 个文件的 CRC 与原始归档一致，未发现另行补丁。
上层另有自解压文件和起动说明，完整源清单合计 131 个文件。

`spt/project.xtx` 登记三本脚本，与实有清单完全一致。`sys.spt` 的脚本切换命令调用 `sot_ungai001`；
后者独占 119 条正文。`sot_backscript.spt` 是背景演出与本篇遗留的图鉴/年表图像控制，没有消息池正文。
图鉴、年表、回想和流程图入口在 `init2/game.fxf` 中禁用，说明书亦明确本作没有画廊功能；未发现追加文字剧本、文字选项或辞典。

| 脚本 | 消息池条数 | 正文显示命令 | 杂项字符串 |
|---|---:|---:|---:|
{table}

三组 GPK/GTB 为背景、立绘和系统图片；65 个 VAW 为系统/效果音，6 个 WGQ 和 2 个 MML 为 BGM 及循环控制。
17 个 XTX 为项目、姓名、资源/变量和系统音表，24 个 FXF 为显示与变量配置；`scene.dat` 是 12 字节场景数据，
`sav/sysfile.org` 是初始系统存档，`oggvorbis/COPYING.txt` 是音频软件许可证。
媒体按已知类型分组处置，未全量解包或做图像 OCR。排除菜单、姓名输入字库、配置注释、资源名、日志副本与程序内部标签。

## 解析、点击与姓名依据

复用 `scripts/system_nnn.py` 的 SPT 解析器：整文件 XOR FF，`SPTHEADER0` 头，word 为单位的地址表，
cp932 严格解码 NUL 结尾消息；NUL 后对齐填充不解码。指令以 `word_count` 推进，三本代码区均在标签表头准确闭合。
显示命令实际引用消息索引恰为 `0..118`；无跳过、字节扫描猜池或重同步。

本作 `souten_sp.exe` 的 L0 证据保存在 `证据/{title}/engine-proof.txt`，位置均为 RVA。
已只读取正在运行的进程 `.text`（1,413,995 字节），与按加载基址重定位的磁盘代码逐字节一致，差异 0；未推进游戏、写内存或改存档。
与本篇已证实现核对后确认语义一致，但本作 handler 地址和对象布局有变化，使用本作地址：

- F35A7–F36C5：`66660006 / 22220001..03` 读取消息表，提交显示对象并推进指令，返回消息状态。
- 10916B–1092DD：新 ADV 消息清除之前的缓冲与行数；`22220003` 才保留并追加。本作全部 119 条为 `22220001`，没有全屏或追加消息。
- 109313–10937B：CRLF 被同次消息解析消费，属于排版换行，无等待；因此页内换行合并。
- 1094DA 限制每行 254 字节，109880–109990 按窗口容量裁切或滚动。
  本作最大原始排版行数 {max_rows}、最大单行 {max_row_bytes} 字节，低于 `windowMessageNumber {adv_capacity}` 和缓冲上限，不触发容量截断或额外翻页。
- `22220004`（等待）及 `22220005`（窗口效果）传数值参数，不读取正文消息；文字选项命令 `22220006` 在三本脚本中均未出现。
- `messageWindow.fxf` 的 `nameWindowFlag 1`，`printmessage.fxf` 的 `nameFlag 1`、`autoNameWindowFlag 1` 启用名札。
  名字表及名字颜色表标记消息首行；{sum(speakers.values())} 条带名消息按可见姓名冠原对白，旁白不冠名。
- `game.fxf` 明确 `meiInitData {default}`，`nameinput.fxf` 为 `seiFlag 0`；只替换 {macros} 处 `#名` 宏，不全局替换字面姓名。
  {ruby} 处 `#［N读音］` 注音按同系列已证语法剥除，保留前面的基底字。
  全部带名台词已有原始引号，无人工补引号、配平、改标点或删语义空格。

最终行数闭合：119 条正文消息 + 0 多段合并页 + 0 额外文字条目 = 119 行。
119 行均逐条核对原始命令偏移、消息索引、文本地址、姓名宏和注音；非日文字符台账按本行源载荷核实。
ASCII 行数 {len(review['ascii_lines'])}，引号/括号失衡 {len(review['unbalanced'])}，多对白候选 {len(review['multiple_speeches'])}，相邻同文 {len(review['adjacent_duplicates'])}。
没有未解变量、控制码、解码占位、PUA 或关键未决边界。最终技能品检结果见下方。

## 复现

Python 3.13.12；Capstone 5.0.7、pefile 2024.8.26 仅用于只读代码取证，正文提取仅用 Python 标准库。
原始归档清单 `sfx-members.txt`、清单核对 `archive-coverage.json`、源文件清单 `inventory.json`、正文来源 `sources.json` 与统计 `summary.json` 各保存一份。

```powershell
& '<本地路径>' -B -X utf8 scripts/souten_ungai_extract.py '{root}' '提取结果/{args.output.name}' --report '解析报告/{args.report.name}' --evidence '解析报告/证据/{title}'
& '<本地路径>' -B -X utf8 '<本地路径>' '提取结果/{args.output.name}' --report '解析报告/{args.report.name}' --name '{default}'
```
'''
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding='utf-8-sig', newline='\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in {'scripts', 'source_crc_verified'}},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
