"""PCSG00611: extract narrative text from MalieVita scripts only.

Uses the existing CP932 Malie parser and stack model. The name-slot value is
provided explicitly; no configuration, executable or media text is read.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import unicodedata

import danzai_maria_psp_extract as malie
import mysteria_pc_text as vm

BUILD_SHA256 = '2e386ba95f6a355f5ff0e71465ae542e60203574ea21979c492674972e970ddb'
NOTICE_IDS = frozenset((
    707,708,709,1098,1569,2400,3211,4746,6075,6703,7149,7552,7553,8176,
    8833,9265,9419,9714,12078,12079,13968,16008,17729,19006,20073,21650,
    23607,24596,26835,27387,27975,
))
UNLOCK_ID = 27976


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(text, name_slot, name_field=False):
    out = []
    controls = collections.Counter()
    i = 0
    while i < len(text):
        c = ord(text[i]); i += 1
        if c == 7:
            assert i < len(text)
            sub = ord(text[i]); i += 1
            controls[sub] += 1
            if sub in (8, 12):
                end = text.find('\0', i)
                if end < 0:
                    assert name_field and sub == 12
                    end = len(text)
                payload = text[i:end]; i = end + 1
                if sub == 12:
                    assert payload == '1', repr(payload)
                    out.append(name_slot)
            else:
                assert sub in (4, 6, 9), (sub, repr(text))
        elif c == 10:
            controls['soft_lf'] += 1
        else:
            assert c >= 32, (c, repr(text))
            out.append(chr(c))
    return ''.join(out), controls


def extract(script, output, work, name_slot):
    assert name_slot.strip() and not any(ord(c) < 32 for c in name_slot)
    data, source = malie.load_script(script)
    assert source['sha256'] == BUILD_SHA256, 'Unverified script build.'
    p = malie.parse_exec(data)
    ins = list(malie.instructions(p['vm_code']))
    boundaries = {pc for pc, op, arg, size in ins} | {len(p['vm_code'])}
    funcs = {f[1] for f in p['functions']}
    assert sum(size for pc, op, arg, size in ins) == len(p['vm_code'])
    assert all(off in boundaries for label, off in p['labels'])
    assert all(off in boundaries for name, fid, result, off in p['functions'])
    assert all(arg in boundaries for pc, op, arg, size in ins if op in (0, 1, 2))
    assert all(arg in funcs for pc, op, arg, size in ins if op in (3, 4, 45))
    pool_pos = 0
    for off, size in p['indices']:
        assert off == pool_pos
        assert p['strings'][off + size:off + size + 1] == b'\0'
        pool_pos += size + 1
    assert pool_pos == len(p['strings'])
    es = list(malie.events(p))
    rows, sources, excluded, groups = [], [], [], []
    counts, controls = collections.Counter(), collections.Counter()
    seen, scope_counts = [], collections.defaultdict(collections.Counter)
    name = None
    visible, cleared = True, True
    scope, group = None, None

    def emit(text, origin):
        assert text.strip() and not any(ord(c) < 32 for c in text)
        assert not any(unicodedata.category(c) in ('Co', 'Cs') for c in text)
        rows.append(text)
        sources.append({'line': len(rows), **origin})

    for e in es:
        kind = e['kind']
        if kind in ('label', 'MALIE_LABLE'):
            labels = e['labels'] if kind == 'label' else [e['text']]
            for label in labels:
                if label and re.fullmatch(r'malie_s\d+', label):
                    scope = label
        elif kind == 'tag':
            tag = e['text']
            m = re.fullmatch(r"<msgframe visibility='(visible|hidden)'>", tag)
            if m:
                visible = m.group(1) == 'visible'
            m = re.fullmatch(r"<chapter name='([^']+)'>", tag)
            if m:
                emit(m.group(1), {'kind': 'chapter', 'pc': e['pc'], 'scope': scope})
                counts['script_chapters'] += 1
        elif kind == 'MALIE_NAME':
            assert name is None
            name = e['text']
            counts['name_calls'] += 1
        elif kind == '_ms_clear':
            name = None
            cleared = True
            counts['clear_calls'] += 1
        elif kind in ('_ms_page', '_ms_pause', '_ms_out', '_ms_overlap'):
            counts[kind] += 1
        elif kind == 'message':
            assert e['function'] == 'maliescenario' and cleared
            cleared = False
            seen.append(e['index'])
            text, ct = decode(e['text'], name_slot)
            controls.update(ct)
            assert ct[6] == 1 and e['text'].endswith('\x07\x06')
            assert e['text'].count('\x07\x06') == 1
            assert ct[8] == ct[9] and ct[8] in (0, 1)
            assert text.strip()
            scope_counts[scope]['source_messages'] += 1
            if e['index'] in NOTICE_IDS or e['index'] == UNLOCK_ID:
                assert name is None
                if e['index'] in NOTICE_IDS:
                    assert re.fullmatch('　アイテム図鑑に「[^\x07]+」が追加されました。\x07\x06', e['text'])
                    reason = 'item_unlock_notice'
                else:
                    assert e['text'] == '　夢の国の物語のページが読めるようになりました。\x07\x06'
                    reason = 'story_unlock_notice'
                excluded.append({'index': e['index'], 'pc': e['pc'], 'scope': scope, 'reason': reason})
                counts[reason] += 1
                scope_counts[scope]['excluded_messages'] += 1
                continue
            speaker = None
            name_macros = 0
            if name is not None:
                speaker_text, name_ct = decode(name, name_slot, name_field=True)
                name_macros = name_ct[12]
                counts['name_macros'] += name_macros
                if name == 'ナレーション':
                    counts['narrator_label_omitted'] += 1
                elif visible and speaker_text:
                    speaker = speaker_text
            if not visible:
                counts['hidden_frame_messages'] += 1
            if speaker:
                # Render the script's separate name field next to the utterance.
                # Existing thoughts and quotation marks retain source punctuation.
                trimmed = text.strip()
                if trimmed.startswith(('（', '(')):
                    counts['named_thoughts'] += 1
                elif trimmed.startswith('「') or trimmed.endswith('」'):
                    counts['source_quotes'] += 1
                else:
                    text = '「' + text + '」'
                    counts['dialogue_wrappers'] += 1
                text = speaker + text
                counts['named_messages'] += 1
            else:
                counts['unnamed_messages'] += 1
            counts['voiced_messages' if ct[8] else 'unvoiced_messages'] += 1
            counts['story_messages'] += 1
            scope_counts[scope]['story_messages'] += 1
            emit(text, {'kind': 'message', 'pc': e['pc'], 'index': e['index'], 'scope': scope,
                        'speaker_source': name, 'speaker': speaker, 'name_visible': visible,
                        'body_name_macros': ct[12], 'name_macros': name_macros,
                        'inline_pauses': ct[4]})
            name = None
        elif kind == 'FrameLayer_SendMessage' and e['function'] == 'maliescenario':
            assert len(e['args']) == 4 and e['args'][2][0] == 'int'
            cmd = e['args'][2][1]
            if cmd == 115:
                assert group is None
                group = {'pc': e['pc'], 'scope': scope, 'options': [], 'wait_pc': None}
            elif cmd == 116:
                assert group is not None and e['text'] is not None
                flag = e['args'][1]
                assert flag[0] == 'int' and flag[1] >> 16 == 1
                text, ct = decode(e['text'], name_slot)
                assert not ct
                emit(text, {'kind': 'choice', 'pc': e['pc'], 'scope': scope,
                            'group_pc': group['pc'], 'flags': flag[1]})
                group['options'].append({'pc': e['pc'], 'text': text, 'flags': flag[1]})
                counts['choice_fields'] += 1
                scope_counts[scope]['choice_fields'] += 1
                if text == '時間切れ':
                    # This field has the same enabled registration flag as
                    # manual options; preserve each script branch occurrence.
                    counts['timeout_choice_fields'] += 1
            elif cmd == 117:
                assert group is not None and group['wait_pc'] is None
                group['wait_pc'] = e['pc']
            else:
                assert cmd == 142
        elif kind == 'System_GetResult' and e['function'] == 'maliescenario':
            assert group is not None and group['wait_pc'] is not None
            group['result_pc'] = e['pc']
            assert group['options']
            groups.append(group)
            group = None
    assert group is None and cleared and name is None
    assert seen == list(range(len(p['indices'])))
    assert {e['index'] for e in excluded} == NOTICE_IDS | {UNLOCK_ID}
    assert counts['name_calls'] == 18370
    assert counts['name_macros'] == 2294 and controls[12] == 203
    assert len(groups) == 101 and counts['choice_fields'] == 345
    assert counts['script_chapters'] == 66 and len(scope_counts) == 66
    assert counts['hidden_frame_messages'] == 0
    assert len(rows) == counts['story_messages'] + counts['choice_fields'] + counts['script_chapters']
    work, output = Path(work), Path(output)
    work.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(rows) + '\n', encoding='utf-8-sig', newline='\n')
    (work / 'sources.jsonl').write_text(''.join(json.dumps(s, ensure_ascii=False) + '\n' for s in sources), encoding='utf-8', newline='\n')
    artifacts = {'excluded.json': excluded, 'choice_groups.json': groups}
    for filename, value in artifacts.items():
        (work / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    summary = {
        'rows': len(rows), 'bytes': output.stat().st_size, 'sha256': digest(output),
        'source': source, 'name_slot': name_slot, 'counts': dict(counts),
        'controls': dict(controls), 'instructions': len(ins), 'event_count': len(es),
        'sections': {k: len(p[k]) for k in ('variables','functions','labels','vm_data','vm_code','indices','strings')},
        'source_messages': len(seen), 'unique_indices': len(set(seen)),
        'choice_groups': len(groups), 'scopes': {k: dict(v) for k, v in scope_counts.items()},
        'multi_segment_pages': 0, 'unresolved': 0,
        'parser_sha256': {Path(path).name: digest(path) for path in (__file__, malie.__file__, vm.__file__)},
    }
    (work / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('scopes', 'parser_sha256')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('script', help='Verified exec.dat or decrypted data3.dat')
    ap.add_argument('output')
    ap.add_argument('--work', required=True)
    ap.add_argument('--name', required=True, help='Explicit value for script name slot 1')
    args = ap.parse_args()
    extract(args.script, args.output, args.work, args.name)
