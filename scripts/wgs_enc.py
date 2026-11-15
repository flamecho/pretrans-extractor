# -*- coding: utf-8 -*-
"""冬園 UTXT：验证 script 里是否含正文（用已知文本反向编码去搜）"""
import re, sys, collections
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

T = open(os.path.join(VNTRANS_HOME, '_w_wgs/chartable.bin'), 'rb').read().decode('utf-8')
TA = r'<本地路径>'
TALK = TA + 'uma_talk_2.bytes'
SCRIPT = TA + 'uma_script_2.bytes'


def dec(d, st):
    out = []
    i = st
    while i < len(d):
        b = d[i]
        if b == 0:
            out.append('\x00'); i += 1
        elif b < 0x80:
            out.append(T[b - 1]); i += 1
        else:
            k = d[i + 1] + 128 * (b - 0x81)
            out.append(T[k + 127] if k + 127 < len(T) else '?'); i += 2
    return ''.join(out)


def enc(s):
    """把文本编码回字节（逆映射；字符不在表里则跳过该字符）"""
    idx = {}
    for i, ch in enumerate(T):
        idx.setdefault(ch, i)
    out = bytearray()
    for ch in s:
        i = idx.get(ch)
        if i is None:
            continue
        if i < 127:                      # 1 字节：t = i+1 (1..127)
            out.append(i + 1)
        else:                            # 2 字节：code = i-127 = trail + 128*(lead-0x81)
            code = i - 127
            lead = 0x81 + code // 128
            trail = code % 128
            out += bytes([lead, trail])
    return bytes(out)


if __name__ == '__main__':
    talk = open(TALK, 'rb').read()
    body = talk[0x4B6B:]
    s = dec(body, 0)
    segs = [x for x in s.split('\x00') if len(x) >= 8]
    print('talk 段数(>=8)', len(segs))
    script = open(SCRIPT, 'rb').read()
    print('script size', len(script))
    hit = 0
    for seg in segs[:400]:
        e = enc(seg)
        if not e:
            continue
        if e in script:
            hit += 1
            if hit <= 5:
                print('  命中 %r  @%#x' % (seg[:24], script.find(e)))
    print('前 400 段中在 script 命中：', hit)
