#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Paradise (PS2 / D3P Daisy2 / DDP3) 全文本提取。
复用 scripts/sgs_kai_ddp.py（同族 三国恋戦記 魁 / ディストピアの王 / Paradise 結-MUSUBI- 的容器/LZSS/密钥）。
文本命令：03 0d 36 ff 01 80 <UTF-16LE> 00 00 = STORY MESSAGE（一次点击＝一框）
          03 0d 32 ff 02 0d 0c ff 01 80 <UTF-16LE> = CHOICE
"""
import sys, os, re, struct, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import sgs_kai_ddp as K

MSG    = b'\x03\x0d\x36\xff\x01\x80'
CHOICE = b'\x03\x0d\x32\xff\x02\x0d\x0c\xff\x01\x80'
SEP    = '\\n'
RUBY   = re.compile(r'\|([^<>|]+)<[^<>]*>')

def read_utf16z(data, p):
    buf = bytearray(); q = p
    while q + 1 < len(data) and not (data[q] == 0 and data[q+1] == 0):
        buf += data[q:q+2]; q += 2
    return buf.decode('utf-16le', 'replace'), q + 2

def split_name(s):
    if SEP not in s:
        return '', s
    first, rest = s.split(SEP, 1)
    if first == '':
        return '', rest
    if first[:1] in '「（『':
        return '', s
    if set(first) <= set('？?…・'):
        return first, rest
    if len(first) <= 12 and rest[:1] in '「（『' and first[-1:] not in '、。！？…':
        return first, rest
    return '', s

def clean_msg(s):
    s = s.replace('\u8001', '')
    s = RUBY.sub(r'\1', s)
    name, s = split_name(s)
    s = re.sub(r'\\s\[[^\]]*\]', '', s)
    s = re.sub(r'\\[a-zA-Z]{1,3}\[[^\]]*\]', '', s)
    s = s.replace(SEP, '')
    s = s.replace('\u3000', ' ').strip()
    return s

def order_key(name):
    m = re.match(r'^main_sec(\d+)$', name)
    if m: return (0, 0, int(m.group(1)), name)
    m = re.match(r'^rt_(.+?)_ch(\d+)_sec(\d+)([a-z]?)$', name)
    if m: return (1, m.group(1), int(m.group(2))*1000 + int(m.group(3)), name)
    m = re.match(r'^rt_(.+?)_chend_(\w+)$', name)
    if m: return (1, m.group(1), 999999, name)
    if name == 'subroutine': return (9, 0, 0, name)
    return (5, 0, 0, name)

def extract_file(path, lines, stat):
    d, entries, typ = K.parse_ddp(path)
    if typ == 'DDP3':
        src = [(e[0], e[1], e[2], e[3]) for e in entries if e[0] and e[2] is not None]
        src.sort(key=lambda e: order_key(e[0]))
    elif typ == 'DDP2':
        cnt, doff = struct.unpack_from('<II', d, 4)
        src = []
        for i in range(cnt):
            off, full, stored, _ = struct.unpack_from('<IIII', d, 0x20 + i*16)
            src.append((None, off, full, stored))
    else:
        raise SystemExit('unknown type %s' % typ)
    for nm, off, osz, st in src:
        try:
            plain, _ = K.get_block(d, off, osz, st)
        except Exception as e:
            print('  skip block', nm, 'err', e); continue
        events = []
        for m in re.finditer(re.escape(MSG), plain):
            events.append((m.start(), 'msg'))
        for m in re.finditer(re.escape(CHOICE), plain):
            events.append((m.start(), 'choice'))
        events.sort()
        for start, kind in events:
            plen = len(MSG) if kind == 'msg' else len(CHOICE)
            s, _ = read_utf16z(plain, start + plen)
            c = clean_msg(s)
            if not c:
                continue
            lines.append(c)
            stat[kind] += 1

def main():
    files = sys.argv[1:] or [os.path.join(VNTRANS_HOME, '_work_jp_paradise/extracted/pfm_text.dat')]
    out = os.path.join(VNTRANS_HOME, '提取结果/[JP]Paradise.txt')
    lines, stat = [], collections.Counter()
    for f in files:
        if not os.path.exists(f):
            print('skip missing', f); continue
        print('==', f, '==')
        extract_file(f, lines, stat)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('story lines: %d   choices: %d   total: %d' % (stat['msg'], stat['choice'], len(lines)))
    print('bytes:', os.path.getsize(out))

if __name__ == '__main__':
    main()
