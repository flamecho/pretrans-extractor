"""Source-aware KAG lexer for Otomedou Kochouran (KAG 3.30)."""
from pathlib import Path
import argparse
import collections
import json
import re


def lex(path):
    """Keep line/column provenance; skip comments, script blocks and macro bodies."""
    in_script = False
    in_macro = False
    for lineno, raw in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        line = raw.lstrip(' \t')
        if not line or line.startswith(';'):
            continue
        if in_script and line not in ('@endscript', '[endscript]'):
            continue
        if line.startswith('*'):
            yield dict(kind='label', value=line[1:], line=lineno, col=1)
            continue
        if line.startswith('@'):
            tokens = [(True, line[1:], 1)]
        else:
            tokens = []
            i = 0
            while i < len(line):
                if line[i:i+2] == '[[':
                    tokens.append((False, '[', i+1))
                    i += 2
                elif line[i] == '[':
                    start = i
                    i += 1
                    quote = ''
                    while i < len(line):
                        ch = line[i]
                        if quote:
                            if ch == quote:
                                quote = ''
                        elif ch in ('"', "'"):
                            quote = ch
                        elif ch == ']':
                            break
                        i += 1
                    if i >= len(line):
                        raise ValueError(f'{path}:{lineno}: unterminated tag {line[start:]}')
                    tokens.append((True, line[start+1:i], start+1))
                    i += 1
                else:
                    start = i
                    while i < len(line) and line[i] != '[':
                        i += 1
                    tokens.append((False, line[start:i], start+1))
        for is_tag, value, col in tokens:
            if is_tag:
                m = re.match(r'([^\s=]+)', value)
                if not m:
                    raise ValueError(f'{path}:{lineno}: invalid tag {value}')
                tag = m[1].lower()
                if tag == 'endscript':
                    in_script = False
                    continue
                if tag == 'endmacro':
                    in_macro = False
                    continue
                if in_script:
                    continue
                if tag == 'iscript':
                    in_script = True
                    continue
                if tag == 'macro':
                    in_macro = True
                    continue
                if in_macro:
                    continue
                attrs = {}
                for a in re.finditer(r'(\w+)\s*=\s*(?:"([^"]*)"|\x27([^\x27]*)\x27|([^\s]+))', value[len(m[1]):]):
                    attrs[a[1]] = next(v for v in a.groups()[1:] if v is not None)
                yield dict(kind='tag', value=value, tag=tag, attrs=attrs, line=lineno, col=col)
            elif not in_script and not in_macro:
                yield dict(kind='text', value=value, line=lineno, col=col)


def inspect(root, output):
    result = {}
    alltags = collections.Counter()
    for path in sorted(root.rglob('*.ks')):
        tokens = list(lex(path))
        tags = collections.Counter(t['tag'] for t in tokens if t['kind'] == 'tag')
        texts = [t for t in tokens if t['kind'] == 'text']
        name = str(path.relative_to(root)).replace('\\', '/')
        result[name] = dict(tags=dict(tags), text_chars=sum(len(t['value']) for t in texts),
                            text_records=texts, tokens=tokens)
        alltags.update(tags)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('FILES',len(result), 'TAGS',dict(alltags))
    print('TEXT',[(k,v['text_chars']) for k,v in result.items()])
    for k,v in result.items():
        if k.startswith('scenario/') and v['text_chars'] and k not in ('scenario/first.ks','scenario/macro.ks','scenario/snow.ks','scenario/gvolume.ks'):
            interesting = [t for t in v['tokens'] if t['kind']=='tag' and t['tag'] in
                           ('if','else','elsif','endif','jump','call','l','emb','input','ch','i','graph','button')]
            print('FLOW',k,interesting)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--inspect', type=Path, required=True)
    a = p.parse_args()
    inspect(a.root,a.inspect)
