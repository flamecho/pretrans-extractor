#!/usr/bin/env python3
"""Extract only SPT script text from unENDing Bloody Call (PSP-JP).

Run with -B -X utf8. Dependencies: sibling iso9660.py and cpk.py.
Only ISO/CPK directory metadata and .spt payloads are read. Other game
payloads, including name-input tables, fonts, pictures and movies, are not read.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import re

from cpk import CPK, UTF
from iso9660 import ISO

VERSION = 1
TOKENS = {0x254B: '%K', 0x2550: '%P', 0x257B: '%{',
          0x253A: '%:', 0x257D: '%}', 0x5C6E: '\\n'}
COMMAND = re.compile(rb'^\s*#([A-Z0-9_.]+)(?:\s+|(?=;)|$)(.*)$', re.S)
RUBY = re.compile(r'%\{([^%]*)%:([^%]*)%\}')


class Slice:
    def __init__(self, f, base, size):
        self.f, self.base, self.size, self.pos = f, base, size, 0

    def seek(self, offset):
        assert 0 <= offset <= self.size, (offset, self.size)
        self.pos = offset

    def read(self, size):
        size = min(size, self.size - self.pos)
        self.f.seek(self.base + self.pos)
        result = self.f.read(size)
        assert len(result) == size
        self.pos += len(result)
        return result


class EmbeddedCPK(CPK):
    def __init__(self, iso, entry):
        self.f = Slice(iso.f, entry['lba'] * 2048, entry['size'])
        self.hdr = UTF(self._read(0x10, 0x400)).rows[0]
        self._build()
        assert len(self.entries) == self.hdr['Files']
        for e in self.entries:
            assert 0 <= e['offset'] < entry['size']
            assert e['offset'] + e['FileSize'] <= entry['size']


def read_text_arg(raw, pos):
    """SPT Unicode argument: opening ASCII quote, BE units, %quote sentinel.

    Native parser 0x12ce8 reads two bytes per unit. 0x2522 terminates,
    0x5c6e is a layout newline, and 0x25xx units are message controls.
    A U+000A low byte is ordinary text data, so regex '.' is unsuitable.
    """
    assert raw[pos] == 0x22
    start = pos
    pos += 1
    chars = []
    while pos + 1 < len(raw):
        unit = int.from_bytes(raw[pos:pos + 2], 'big')
        if unit == 0x2522:
            return ''.join(chars), pos + 2, raw[start:pos + 2]
        assert not 0xD800 <= unit <= 0xDFFF, ('unexpected surrogate', hex(unit))
        chars.append(TOKENS.get(unit, chr(unit)))
        pos += 2
    raise ValueError('Unterminated Unicode SPT argument')


def visible(text, message=False):
    ruby = len(RUBY.findall(text))
    text = RUBY.sub(lambda m: m[1], text)
    if message:
        assert text.endswith('%K%P'), text
        assert text.count('%K') == text.count('%P') == 1, text
        text = text[:-4]
    layout_breaks = text.count('\\n')
    text = text.replace('\\n', '')
    assert not re.search(r'%[KP{:}]', text), text
    assert not any(ord(c) < 0x20 or 0xE000 <= ord(c) <= 0xF8FF
                   or c == '\ufffd' for c in text), text
    return text, ruby, layout_breaks


def parse_script(data, source):
    rows = []
    commands = collections.Counter()
    labels = []
    calls = []
    condition_stack = []
    condition_issues = []
    select = None
    offset = 0
    lines = data.split(b'\r\n')
    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        location = {'script': source, 'record': line_no, 'offset': offset}
        offset += len(line) + (2 if line_no < len(lines) else 0)
        if not stripped or stripped.startswith(b';'):
            continue
        if stripped.startswith(b':'):
            labels.append(stripped.decode('cp932'))
            continue
        match = COMMAND.match(line)
        if match:
            cmd = match[1].decode('ascii')
            arg = match[2].strip()
            commands[cmd] += 1
            if cmd == 'IF':
                condition_stack.append(line_no)
            elif cmd == 'ENDIF':
                if condition_stack:
                    condition_stack.pop()
                else:
                    condition_issues.append({'kind': 'unmatched_ENDIF', **location})
            if cmd in {'GO', 'SUB.CALL', 'JUMP'}:
                calls.append({'command': cmd, 'argument': arg.decode('cp932'), **location})
            if cmd == 'SELECT':
                assert select is None, location
                select = {'source': location, 'options': 0}
            elif cmd == 'ENDSELECT':
                assert select is not None and select['options'] > 0, location
                select = None
            elif cmd in {'MES.OUT', 'MESEX.OUT'}:
                count = 3 if cmd == 'MESEX.OUT' else 2
                prefix = arg.split(b',', count)
                assert len(prefix) == count + 1, location
                numbers = [int(x) for x in prefix[:count]]
                payload = prefix[count]
                name = ''
                if cmd == 'MESEX.OUT':
                    raw_name, pos, _ = read_text_arg(payload, 0)
                    assert payload[pos:pos + 1] == b',', location
                    name, name_ruby, name_breaks = visible(raw_name)
                    assert not name_breaks and not name_ruby, location
                    pos += 1
                else:
                    pos = 0
                raw_body, end, raw_literal = read_text_arg(payload, pos)
                assert not payload[end:].strip() or payload[end:].lstrip().startswith(b';'), location
                body, ruby, breaks = visible(raw_body, message=True)
                assert body, location
                rows.append({'kind': 'dialogue' if name else 'narration',
                             'command': cmd, 'arguments': numbers, 'name': name,
                             'raw_text': raw_body, 'text': name + body,
                             'ruby': ruby, 'layout_breaks': breaks,
                             'literal_bytes': len(raw_literal), **location})
            continue
        if select is not None and stripped.startswith(b'"'):
            raw_option, end, literal = read_text_arg(stripped, 0)
            tail = stripped[end:]
            assert re.fullmatch(rb',@\d+,GO\s+"[A-Za-z0-9_]+"\s*(?:;.*)?', tail), location
            text, ruby, breaks = visible(raw_option)
            assert text, location
            select['options'] += 1
            rows.append({'kind': 'choice', 'name': '', 'raw_text': raw_option,
                         'text': text, 'ruby': ruby, 'layout_breaks': breaks,
                         'literal_bytes': len(literal), 'select': select['source'],
                         'branch': tail.decode('ascii'), **location})
            continue
        raise ValueError(('Unclassified active SPT record', location, line.hex()))
    assert offset == len(data)
    assert select is None
    condition_issues.extend({'kind': 'unclosed_IF', 'script': source, 'record': n}
                            for n in condition_stack)
    return rows, commands, labels, calls, condition_issues


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('iso', type=pathlib.Path)
    ap.add_argument('--work', type=pathlib.Path, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    iso = ISO(args.iso)
    directory = list(iso.walk())
    types = collections.Counter()
    commands = collections.Counter()
    all_rows, scripts, issues = [], [], []
    cpks = sorted((p, e) for p, e in directory if p.lower().endswith('.cpk'))
    for archive, entry in cpks:
        c = EmbeddedCPK(iso, entry)
        for member in c.entries:
            suffix = pathlib.Path(member['name']).suffix.lower()
            types[suffix] += 1
            if suffix != '.spt':
                continue
            data = c.raw(member)
            assert len(data) == member['ExtractSize'], member
            source = archive + '/' + member['name']
            target = args.work / 'scripts' / pathlib.Path(archive).stem / member['name']
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or target.read_bytes() != data:
                target.write_bytes(data)
            rows, counts, labels, calls, condition_issues = parse_script(data, source)
            commands.update(counts)
            issues.extend(condition_issues)
            scripts.append({'source': source, 'bytes': len(data),
                            'sha256': hashlib.sha256(data).hexdigest(),
                            'rows': len(rows), 'commands': dict(counts),
                            'labels': labels, 'calls': calls})
            all_rows.extend(rows)
    for n, row in enumerate(all_rows, 1):
        row['output_line'] = n
    assert len(all_rows) == commands['MES.OUT'] + commands['MESEX.OUT'] + sum(r['kind'] == 'choice' for r in all_rows)
    assert commands['SELECT'] == commands['ENDSELECT']
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', encoding='utf-8-sig', newline='\n') as f:
        for row in all_rows:
            f.write(row['text'] + '\n')
    with (args.work / 'rows.jsonl').open('w', encoding='utf-8', newline='\n') as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    kinds = collections.Counter(r['kind'] for r in all_rows)
    summary = {'parser_version': VERSION, 'source_iso': str(args.iso.resolve()),
               'cpks': len(cpks), 'member_types': dict(types), 'script_count': len(scripts),
               'script_bytes': sum(s['bytes'] for s in scripts), 'scripts': scripts,
               'commands': dict(commands), 'kinds': dict(kinds), 'rows': len(all_rows),
               'ruby': sum(r['ruby'] for r in all_rows),
               'layout_breaks': sum(r['layout_breaks'] for r in all_rows),
               'names': dict(collections.Counter(r['name'] for r in all_rows if r['name'])),
               'extra_script_rows': sum(s['rows'] for s in scripts if pathlib.Path(s['source']).name.startswith('P')),
               'condition_issues': issues, 'unclassified_records': 0,
               'sha256': hashlib.sha256(args.out.read_bytes()).hexdigest()}
    (args.work / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k not in {'scripts', 'commands', 'names'}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
