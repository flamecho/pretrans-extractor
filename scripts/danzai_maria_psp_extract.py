"""断罪のマリア ラ･カンパネラ PSP: script-only LIBP/Malie extraction.

Does not read game configuration, CSVs, images, movies or other text assets.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import struct

import mysteria_pc_text as vm

BUILD_SHA256 = 'e4cae371eab2518a2c26aced53f65d3b8ddcece9c93774543ed3a578e5418d81'
NOTICE_IDS = frozenset((
    953,955,1650,1677,2084,2097,3898,3902,4665,5228,5229,5230,5920,5930,
    9899,10358,10883,10887,13821,13825,14547,14623,14627,15121,15125,17591,
    19309,20645,22322,22565,22977,23228,23734,28249,28971,28979,28983,29382,
    29805,29809,29811,29815,30052,30330,30536,30540,30767,31416,31417,31461,
    31468,31472,31795,31923,32210,32360,32367,33217,33219,33389,33705,33922,
    33924,33925,34197,34199,34340,34342,34558,34560,34707,34709,35887,36726,36792
))
DELETED_PLACEHOLDER_IDS = frozenset((170,171,172,173,174,175,176,14036,14037,16392,16394,16840,16841))
QUIZ_NOTICE_ID = 10054


def instructions(code):
    pc = 0
    while pc < len(code):
        op = code[pc]
        assert op <= 0x33, (pc, op)
        # In this PSP build, 08 is a single-byte instruction; the PC helper's
        # assumed four-byte operand would swallow the following fontsize call.
        size = {0:5, 1:5, 2:5, 3:6, 4:3, 9:2, 10:3, 12:5,
                13:5, 17:2, 45:5, 49:5, 51:2}.get(op, 1)
        assert pc+size <= len(code)
        arg = None
        if size >= 5:
            arg = struct.unpack_from('<I', code, pc+1)[0]
        elif size in (2, 3):
            arg = struct.unpack_from('<H', code, pc+1)[0] if op == 10 else code[pc+1]
        yield pc, op, arg, size
        pc += size
    assert pc == len(code)


def parse_exec(data):
    pos = 0
    def read(size):
        nonlocal pos
        assert 0 <= size <= len(data) - pos, (pos, size, len(data))
        part = data[pos:pos+size]
        pos += size
        return part
    def u32():
        return struct.unpack('<I', read(4))[0]
    def text():
        size = u32() & 0x7fffffff
        return read(size).decode('cp932').rstrip('\0')
    p = {}
    variables = []
    for _ in range(u32()):
        name = text()
        types = []
        kind = u32()
        while kind:
            types.append((kind, u32()))
            kind = u32()
        variables.append({'name': name, 'types': types, 'values': struct.unpack('<4I', read(16))})
    p['variables'] = variables
    p['unknown'] = u32()
    p['functions'] = [(text(), u32(), u32(), u32()) for _ in range(u32())]
    p['labels'] = [(text(), u32()) for _ in range(u32())]
    for key in ('vm_data', 'vm_code'):
        size = u32()
        p[key+'_offset'] = pos
        p[key] = read(size)
    count = u32()
    assert count * 8 <= len(data) - pos
    p['indices'] = [struct.unpack('<II', read(8)) for _ in range(count)]
    size = u32()
    p['strings_offset'] = pos
    p['strings'] = read(size)
    assert pos == len(data), (pos, len(data))
    for off, size in p['indices']:
        assert off + size <= len(p['strings'])
    return p


def vm_string(p, off):
    data = p['vm_data']
    assert 0 <= off < len(data)
    end = data.find(b'\0', off)
    assert end >= off
    return data[off:end].decode('cp932')


def events(p):
    # Reuse the verified Malie opcode schema and argument/stack model;
    # this PSP build stores both data strings and message strings in CP932.
    original = vm.vm_string
    original_instructions = vm.instructions
    vm.vm_string = vm_string
    vm.instructions = instructions
    original_strings = p['strings']
    original_indices = p['indices']
    converted = []
    indices = []
    offset = 0
    for start, size in original_indices:
        part = original_strings[start:start+size].decode('cp932').encode('utf-16-le')
        indices.append((offset, len(part)))
        converted.append(part)
        offset += len(part)
    p = {**p, 'strings': b''.join(converted), 'indices': indices}
    try:
        yield from vm.events(p)
    finally:
        vm.vm_string = original
        vm.instructions = original_instructions


def load_script(path):
    path = Path(path)
    with path.open('rb') as f:
        header = f.read(16)
        if header[:4] != b'LIBP':
            data = header + f.read()
            return data, {'script_bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        _, n1, n2, zero = struct.unpack('<4sIII', header)
        assert zero == 0 and 0 < n1 < 1000000 and 0 < n2 < 1000000
        raw = f.read(n1*32)
        entries = []
        for i in range(n1):
            record = raw[i*32:(i+1)*32]
            name = record[:20].split(b'\0')[0].decode('cp932')
            entries.append((name, *struct.unpack('<III', record[20:])))
        sectors = struct.unpack('<%dI' % n2, f.read(n2*4))
        base = (16+n1*32+n2*4+2047)&~2047
        seen = set()
        scripts = []
        filecount = 0
        def walk(prefix, first, count):
            nonlocal filecount
            assert 0 <= first and first+count <= n1
            for i in range(first, first+count):
                assert i not in seen
                seen.add(i)
                name, flags, ref, length = entries[i]
                full = '/'.join(filter(None, (prefix, name)))
                if flags:
                    filecount += 1
                    copies = flags >> 16
                    assert flags == copies << 16 and ref+copies <= n2
                    if full.endswith('/exec.dat'):
                        scripts.append((full, ref, length, copies))
                else:
                    walk(full, ref, length)
        walk('', 0, 1)
        assert len(seen) == n1 and len(scripts) == 1
        name, ref, length, copies = scripts[0]
        hashes = []
        offsets = []
        data = None
        for sector in sectors[ref:ref+copies]:
            off = base+sector*2048
            f.seek(off)
            part = f.read(length)
            assert len(part) == length
            hashes.append(hashlib.sha256(part).hexdigest())
            offsets.append(off)
            if data is None:
                data = part
        assert len(set(hashes)) == 1
        return data, {'archive_entry': name, 'script_bytes': length, 'sha256': hashes[0],
                      'copies': copies, 'offsets': offsets, 'entries': n1, 'files': filecount,
                      'sector_bytes': 2048, 'data_base': base}


def decode(s, default, name_field=False):
    segments = [[]]
    counts = collections.Counter()
    i = 0
    while i < len(s):
        c = ord(s[i])
        i += 1
        if c == 7:
            assert i < len(s)
            sub = ord(s[i])
            i += 1
            counts[sub] += 1
            if sub in (8, 12):
                end = s.find('\0', i)
                if end < 0:
                    assert name_field and sub == 12
                    end = len(s)
                payload = s[i:end]
                i = end+1
                if sub == 12:
                    assert payload == '1', repr(payload)
                    segments[-1].append(default)
            elif sub == 6:
                segments.append([])
            else:
                assert sub == 9, (sub, repr(s))
        elif c == 10:
            counts['soft_lf'] += 1
        else:
            assert c >= 32, (c, repr(s))
            segments[-1].append(chr(c))
    return [''.join(x) for x in segments if ''.join(x).strip()], counts


def extract(p, es, output, work, source):
    # This build's protagonist name is a literal script nameplate, including
    # the messages whose body uses the name-slot macro. No INI is consulted.
    default = 'マリア'
    assert sum(e['kind']=='MALIE_NAME' and e['text']==default for e in es) == 6617
    rows = []
    sources = []
    counts = collections.Counter()
    controls = collections.Counter()
    name = None
    visible = True
    clear = True
    seen = []
    scope = None
    group = None
    groups = []
    chapters = []
    layout = []
    excluded = []
    def emit(text, provenance):
        assert text.strip() and '\n' not in text and '\r' not in text
        assert not any(ord(c)<32 for c in text)
        rows.append(text)
        sources.append({'line': len(rows), **provenance})
    def named_text(text, speaker):
        if not speaker:
            return text
        trimmed = text.strip()
        if trimmed.startswith(('（', '(')):
            counts['source_thoughts'] += 1
        elif trimmed.startswith('「') and trimmed.endswith('」'):
            counts['source_quoted'] += 1
        else:
            text = '「'+text+'」'
            counts['supplemented_quotes'] += 1
        return speaker+text
    for e in es:
        k = e['kind']
        if k == 'label':
            for label in e['labels']:
                m = re.fullmatch(r'malie_s(\d+)', label)
                if m:
                    scope = int(m.group(1))
        elif k == 'tag':
            tag = e['text']
            m = re.fullmatch(r"<msgframe visibility='([^']+)'>", tag)
            if m:
                assert m.group(1) in ('visible', 'hidden')
                visible = m.group(1) == 'visible'
            m = re.fullmatch(r"<chapter name='([^']+)'>", tag)
            if m:
                # Literal narrative chapter names from the script. Image title
                # cards are not opened or transcribed in this script-only task.
                emit(m.group(1), {'kind': 'script_chapter', 'pc': e['pc'], 'scope': scope})
                chapters.append({'pc': e['pc'], 'text': m.group(1), 'scope': scope})
                counts['script_chapters'] += 1
        elif k == 'MALIE_NAME':
            assert name is None
            name = e['text']
            counts['name_calls'] += 1
        elif k == '_ms_clear':
            name = None
            clear = True
            counts['clear_calls'] += 1
        elif k == '_ms_page':
            counts['page_wait_calls'] += 1
        elif k == '_ms_out':
            counts['out_calls'] += 1
        elif k == 'message':
            assert e['function'] == 'maliescenario'
            assert clear, ('message without preceding clear', e['index'])
            clear = False
            seen.append(e['index'])
            parts, ct = decode(e['text'], default)
            assert len(parts) <= 1, (e['index'], len(parts))
            assert ct[6] in (1, 2)
            controls.update(ct)
            if e['index'] in DELETED_PLACEHOLDER_IDS or e['index'] == QUIZ_NOTICE_ID:
                assert name is None
                if e['index'] in DELETED_PLACEHOLDER_IDS:
                    assert e['text'] == '削除\x07\x06'
                    category = 'deleted_script_placeholder'
                else:
                    assert e['text'] == '図書館問題：全問正解\x07\x06'
                    category = 'quiz_result_ui_notice'
                counts[category] += 1
                excluded.append({'index': e['index'], 'pc': e['pc'], 'reason': category})
                counts['empty_terminal_segments'] += ct[6]
                name = None
                continue
            if e['index'] in NOTICE_IDS:
                assert name is None
                item_notice = re.fullmatch(r'[ \u3000]*★アイテムリストに新項目(?:を追加しました|が追加されました)。?\n\u3000.+\x07\x06', e['text'])
                extra_notice = re.fullmatch(r'\u3000★「[^」]+」への扉が開きました。\n\u3000{3}ＥＸＴＲＡモードからプレイすることができます。\x07\x06', e['text'])
                assert item_notice or extra_notice
                category = 'item_ui_notice' if item_notice else 'extra_unlock_ui_notice'
                counts[category] += 1
                excluded.append({'index': e['index'], 'pc': e['pc'], 'reason': category})
                counts['empty_terminal_segments'] += ct[6]
                name = None
                continue
            if not parts:
                counts['empty_messages'] += 1
                counts['empty_terminal_segments'] += ct[6]
                name = None
                continue
            speaker = None
            if name is not None:
                name_parts, name_ct = decode(name, default, True)
                assert len(name_parts) <= 1
                counts['name_macros'] += name_ct[12]
                if visible and name_parts:
                    speaker = name_parts[0]
                if not name_parts:
                    counts['empty_name_calls'] += 1
            if speaker:
                assert '\x07' not in speaker
                counts['named_messages'] += 1
            assert ct[8] == ct[9] and ct[8] in (0, 1)
            if ct[8] == 0:
                counts['narration_messages'] += 1
            else:
                counts['voiced_messages'] += 1
            if not visible:
                counts['hidden_frame_script_messages'] += 1
            text = named_text(parts[0], speaker)
            emit(text, {'kind': 'message', 'pc': e['pc'], 'index': e['index'], 'scope': scope,
                        'speaker_source': name, 'name_visible': visible})
            counts['story_messages'] += 1
            counts['empty_terminal_segments'] += ct[6]
            name = None
        elif k == 'FrameLayer_SendMessage' and e['function'] == 'maliescenario':
            assert len(e['args']) == 4
            cmd = e['args'][2]
            assert cmd[0] == 'int'
            if cmd[1] == 115:
                assert group is None
                group = {'pc': e['pc'], 'scope': scope, 'options': [], 'wait_pc': None}
            elif cmd[1] == 116:
                assert group is not None and e['text'] is not None
                flag = e['args'][1]
                assert flag[0] == 'int' and flag[1] >> 16 == 1
                parts, ct = decode(e['text'], default)
                assert len(parts) == 1 and not ct
                emit(parts[0], {'kind': 'choice', 'pc': e['pc'], 'scope': scope,
                                'group_pc': group['pc'], 'flags': flag[1]})
                group['options'].append({'pc': e['pc'], 'text': parts[0], 'flags': flag[1]})
                counts['choice_fields'] += 1
                # Retain the script's timeout branch labels. They enter the
                # same enabled option registration call as all other fields.
                if parts[0] == '時間切れ':
                    counts['timeout_choice_fields'] += 1
            elif cmd[1] == 117:
                assert group is not None
                group['wait_pc'] = e['pc']
            else:
                assert cmd[1] == 142
        elif k == 'System_GetResult' and e['function'] == 'maliescenario':
            assert group is not None and group['wait_pc'] is not None
            groups.append(group)
            group = None
    assert group is None and clear and name is None
    assert seen == list(range(len(p['indices'])))
    assert {e['index'] for e in excluded} == NOTICE_IDS | DELETED_PLACEHOLDER_IDS | {QUIZ_NOTICE_ID}
    parsed_instructions = list(instructions(p['vm_code']))
    boundaries = {pc for pc, op, arg, size in parsed_instructions}
    assert sum(size for pc, op, arg, size in parsed_instructions) == len(p['vm_code'])
    for pc, op, arg, size in parsed_instructions:
        if op in (0, 1, 2):
            assert arg in boundaries, (pc, arg)
    assert all(off in boundaries for label, off in p['labels'])
    for fn, fid, res, off in p['functions']:
        assert off == 0 or off in boundaries
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(rows)+'\n', encoding='utf-8-sig', newline='\n')
    (work/'sources.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in sources), encoding='utf-8', newline='\n')
    summary = {'rows': len(rows), 'bytes': output.stat().st_size,
               'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'source': source,
               'counts': dict(counts), 'controls': dict(controls), 'choice_groups': len(groups),
               'sections': {k: len(p[k]) for k in ('variables','functions','labels','vm_data','vm_code','indices','strings')},
               'instructions': len(parsed_instructions), 'source_messages': len(seen),
               'unique_indices': len(set(seen)), 'unresolved': 0, 'multi_segment_pages': 0}
    (work/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    (work/'choice_groups.json').write_text(json.dumps(groups, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    (work/'excluded.json').write_text(json.dumps(excluded, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('script')
    ap.add_argument('output')
    ap.add_argument('--work', required=True)
    args = ap.parse_args()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    data, source = load_script(args.script)
    assert source['sha256'] == BUILD_SHA256, 'This extractor is verified for a different script build.'
    p = parse_exec(data)
    es = list(events(p))
    (work / 'events.jsonl').write_text(''.join(json.dumps(e, ensure_ascii=False)+'\n' for e in es), encoding='utf-8', newline='\n')
    extract(p, es, args.output, work, source)
