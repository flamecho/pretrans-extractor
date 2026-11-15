"""Verify Souten output against source records and write sourced exceptions.

Run after souten_extract.py, then run the skill's check_text.py with the
generated charset, exact allow file, and layout map. No output text is edited.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re

from system_nnn import read_script
from souten_extract import config, names, description_pages, RUBY


def cjk(ch):
    # Match check_text.py's charset gate (its is_jp() has a wider range).
    return any(a <= ord(ch) <= b for a, b in (
        (0x3000, 0x30ff), (0x4e00, 0x9fff),
        (0xff01, 0xff60), (0xffe0, 0xffee)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=Path)
    ap.add_argument('text', type=Path)
    ap.add_argument('--audit', required=True, type=Path)
    ap.add_argument('--allow', required=True, type=Path)
    args = ap.parse_args()
    data = args.text.read_bytes()
    assert data.startswith(b'\xef\xbb\xbf') and b'\r' not in data
    rows = data.decode('utf-8-sig').splitlines()
    mapping = json.loads((args.audit / 'sources.json').read_text('utf-8'))
    layout = json.loads((args.audit / 'layout.json').read_text('utf-8'))['pages']
    summary_path = args.audit / 'summary.json'
    summary = json.loads(summary_path.read_text('utf-8'))
    assert len(mapping) == len(rows) == summary['lines']
    assert hashlib.sha256(data).hexdigest() == summary['sha256']
    game = config(args.source / 'init2/game.fxf')
    default = re.search(r'^meiInitData\s+(\S+)', game, re.M)[1]
    plates = names(args.source)
    scripts = {p.name: read_script(p) for p in (args.source / 'spt').glob('*.spt')}
    commands = {name: {c.offset: c for c in script.commands} for name, script in scripts.items()}
    descriptions = {p['source']: p['text'] for p in description_pages(
        args.source, summary['row_capacity']['description'])[0]}
    merged = {p['merged']: p['segments'] for p in layout}
    counts = collections.Counter()
    first_source = {}
    review = {'adjacent_duplicates': [], 'structure_candidates': [], 'ascii_lines': []}
    exceptions = []
    for line, (text, source) in enumerate(zip(rows, mapping), 1):
        assert text and source['line'] == line
        if source['kind'] == 'message':
            match = re.fullmatch(r'spt/(.+\.spt): command=0x([0-9a-f]+); '
                                 r'message=(\d+); text=0x([0-9a-f]+)', source['source'])
            assert match, source
            script = scripts[match[1]]
            index = int(match[3])
            record = script.messages[index]
            assert record.offset == int(match[4], 16)
            command = commands[match[1]][int(match[2], 16)]
            assert command.words[3] == index and hex(command.words[2]) == source['opcode']
            raw = record.text
            head, sep, body = raw.partition('\r\n')
            plate = head if sep and head in plates else ''
            expected = RUBY.sub('', raw).replace('#名', default).replace('\r\n', '')
            assert source['speaker'] == plate.replace('#名', default)
            assert text == expected, (line, source)
            literal = RUBY.sub('', raw.replace('#名', default))
        elif source['kind'] == 'description':
            literal = descriptions[source['source']]
            assert text == literal, (line, source)
            # A scene heading followed by quoted narration is not a name plate.
            if text.startswith('【第二太子】「'):
                assert source['source'] == 'chart/chart4.xtx:21; node=3020; 未読'
                exceptions.append(text)
        elif source['kind'] == 'merged':
            segments = merged[line]
            assert segments == list(range(segments[0], line))
            assert text == ''.join(rows[n - 1] for n in segments)
            literal = text
        else:
            raise ValueError(source)
        for ch in text:
            if not cjk(ch):
                assert ch in literal, (line, ch, source)
                counts[ch] += 1
                first_source.setdefault(ch, (line, source['source']))
        flags = [left + right for left, right in [('「', '」'), ('『', '』'), ('（', '）')]
                 if text.count(left) != text.count(right)]
        if text.count('「') > 1:
            flags.append('multiple_speeches')
        if flags:
            review['structure_candidates'].append({'line': line, 'flags': flags})
        if line > 1 and text == rows[line - 2]:
            assert source['source'] != mapping[line - 2]['source']
            review['adjacent_duplicates'].append([line - 1, line])
        if any(0x20 <= ord(ch) < 0x7f for ch in text):
            review['ascii_lines'].append(line)
        assert '\ufffd' not in text and not any(0xe000 <= ord(ch) <= 0xf8ff for ch in text)
        assert not any(ord(ch) < 0x20 for ch in text) and '#' not in text
    assert len(exceptions) == 1
    args.allow.parent.mkdir(parents=True, exist_ok=True)
    args.allow.write_text(
        '#@story-description: chart/chart4.xtx:21 的未读说明；【第二太子】为场面标题，'
        '其后引号为叙事原文；RVA 5CB85/5D130/124CBA 证明说明窗直接显示。\n'
        + '\n'.join(exceptions) + '\n', encoding='utf-8', newline='\n')
    charset = args.allow.with_suffix('.charset')
    ledger = ['# 字符均核对本行源载荷；首字符为品检基线，后列为次数与首现来源。']
    for ch, count in counts.most_common():
        line, source = first_source[ch]
        ledger.append(f'{ch}\t{count}\tL{line}\t{source}')
    charset.write_text('\n'.join(ledger) + '\n', encoding='utf-8', newline='\n')
    (args.audit / 'review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2),
                                           encoding='utf-8', newline='\n')
    summary['source_audit'] = {
        'verified_lines': len(rows), 'charset_kinds': len(counts),
        'ascii_lines': len(review['ascii_lines']),
        'structure_candidates': len(review['structure_candidates']),
        'structure_by_flag': dict(collections.Counter(
            flag for item in review['structure_candidates'] for flag in item['flags'])),
        'adjacent_duplicate_pairs': len(review['adjacent_duplicates']),
        'exact_exceptions': len(exceptions), 'sha256': summary['sha256']}
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary['source_audit'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
