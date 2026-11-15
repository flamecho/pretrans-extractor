"""冬園サクリフィス UTXT 文本流 -> 文本框（按代码级结构切分）
- 容器: UTXT 头 16B, u32@0x0C = 字符流绝对偏移
- 字符流: 1B token(0x01-0x7F)->chartable[token-1]; 2B token lead>=0x81 -> chartable[trail+128*(lead-0x81)+127]
- 0x00 = 换行。换行后接 U+3000 = 框内软换行(缩进续行)；不接 U+3000 = 新文本框
"""
import sys, re, collections
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

CHART = os.path.join(VNTRANS_HOME, '_w_wgs/chartable.bin')
ROOT = r'<本地路径>'

T = open(CHART, 'rb').read().decode('utf-8')
HEROINE = 'レティシア'


def load(fn):
    d = open(ROOT + fn, 'rb').read()
    assert d[:4] == b'UTXT', d[:4]
    off = int.from_bytes(d[12:16], 'little')
    chars, i = [], off
    while i < len(d):
        b = d[i]
        if b == 0:
            chars.append('\x00'); i += 1
        elif b < 0x80:
            chars.append(T[b - 1]); i += 1
        else:
            code = d[i + 1] + 128 * (b - 0x81)
            chars.append(T[code + 127]); i += 2
    return ''.join(chars)


def clean(s):
    s = s.replace('$', '')          # 辞書語の囲み
    s = s.replace('%', HEROINE)     # 主人公名プレースホルダ
    return s


def boxes(talk):
    segs = talk.split('\x00')
    out, cur = [], None
    for seg in segs:
        if not seg:
            continue
        if cur is not None and seg.startswith('\u3000'):
            cur += seg[1:]          # 续行：去掉缩进后直接拼接
        else:
            if cur is not None:
                out.append(cur)
            cur = seg
    if cur is not None:
        out.append(cur)
    return [clean(x) for x in out if x.strip()]


if __name__ == '__main__':
    talk = load('uma_talk_2.bytes')
    text = load('uma_text_2.bytes')
    print('talk chars', len(talk), 'text chars', len(text), file=sys.stderr)
    bx = boxes(talk)
    print('boxes', len(bx), file=sys.stderr)
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        st = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        for k, b in enumerate(bx[st:st + int(sys.argv[3]) if len(sys.argv) > 3 else 12], st):
            print(k, len(b), '|', b)
    else:
        with open(os.path.join(VNTRANS_HOME, '_w_wgs/boxes.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(bx) + '\n')
