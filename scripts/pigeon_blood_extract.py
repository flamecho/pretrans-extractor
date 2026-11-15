#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Pigeon Blood (PC / PIL-SLASH / D3P Daisy2 DDP3) 全文本提取。

容器链：PE32 + RAR5 SFX@0x48E00 → ISO9660 → Files\\data\\pjb_text.dat (DDP3)
记录表变体：本作 inner magic 在 off+1（同族旧作 off+2），故 parse_ddp 的
            magic-2 反查全 miss；正解是以 magic-1 反查记录区。
文本命令（L0）：03 0d 36 ff 01 80 <UTF-16LE> 00 00 = MSG（一次点击＝一框＝一行）
                03 0d 32 ff 02 0d 0c ff 01 80 <UTF-16LE> = CHOICE（每个签名一个选项）
★ 不 strip U+8001：本作 7 处均为真汉字「老」（老朽化 / 年老いた / 老齢 / 老若男女）。
"""
import sys, os, re, struct, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import sgs_kai_ddp as K

MAG    = K.MAG
MSG    = b'\x03\x0d\x36\xff\x01\x80'
CHOICE = b'\x03\x0d\x32\xff\x02\x0d\x0c\xff\x01\x80'
SEP    = '\\n'
RUBY   = re.compile(r'\|([^<>|]+)<[^<>]*>')


def parse_pjb(path):
    """DDP3 记录表变体：以 DDWuHXB 位置 m 反查 off=m-1 的记录头。"""
    d = open(path, 'rb').read()
    assert d[:4] == b'DDP3', 'not DDP3'
    data_off = struct.unpack_from('<I', d, 8)[0]
    magics = [m.start() for m in re.finditer(re.escape(MAG), d)]
    idx = {}
    for q in range(0x20, data_off - 0x13):
        off = struct.unpack_from('<I', d, q + 1)[0]
        if data_off <= off < len(d) and d[q] >= 0x13 and q + d[q] <= data_off + 8:
            nm = d[q+0x11:q+0x11+d[q]-0x13].decode('utf-16le', 'replace')
            idx[off] = (struct.unpack_from('<I', d, q+5)[0],
                        struct.unpack_from('<I', d, q+9)[0], nm)
    entries = []
    for m in magics:
        off = m - 1
        if off not in idx:
            raise SystemExit('record miss: magic=%#x off=%#x' % (m, off))
        osz, st, nm = idx[off]
        entries.append((nm, off, osz, st))
    return d, entries


def read_utf16z(data, p):
    buf = bytearray(); q = p
    while q + 1 < len(data) and not (data[q] == 0 and data[q+1] == 0):
        buf += data[q:q+2]; q += 2
    return buf.decode('utf-16le', 'replace'), q + 2


def split_name(s):
    """独立名字窗：'名字\\n台词' 剔名；'\\n旁白' 保留整行。"""
    if SEP not in s:
        return '', s
    first, rest = s.split(SEP, 1)
    if first == '':
        return '', rest
    if first[:1] in '「｢（『':
        return '', s
    if set(first) <= set('？?…・'):
        return first, rest
    if len(first) <= 12 and rest[:1] in '「｢（『' and first[-1:] not in '、。！？…':
        return first, rest
    return '', s


def clean_msg(s):
    s = RUBY.sub(r'\1', s)
    name, s = split_name(s)
    s = re.sub(r'\\[a-zA-Z]{1,3}\[[^\]]*\]', '', s)
    s = s.replace(SEP, '')            # 框内软换行合并，不拆
    s = s.rstrip('\\')                # 孤立反斜杠＝源码截断的软换行残片，非正文
    s = s.replace('\u3000', ' ').strip()
    return s


def order_key(name):
    """块名 [前缀][数字][后缀]；同前缀内数字递增＝剧本顺序（128/149 块内
    有 num+1 跳转引用佐证）；前缀间无脚本跳转表，采用确定性字母序。"""
    m = re.match(r'^([a-z]+)(\d+)(.*)$', name)
    if m:
        return (m.group(1), int(m.group(2)), m.group(3))
    return ('\uffff', 0, name)


def main():
    src = (sys.argv[1] if len(sys.argv) > 1 else
           os.path.join(VNTRANS_HOME, '_work_pigeon_blood/extracted/pjb_text.dat'))
    out = os.path.join(VNTRANS_HOME, '提取结果/[JP]Pigeon Blood.txt')
    d, entries = parse_pjb(src)
    entries.sort(key=lambda e: order_key(e[0]))
    print('blocks=%d (magic-1 reverse lookup)' % len(entries))
    lines, stat = [], collections.Counter()
    ruby_n, ctrl_n, skipped = 0, 0, 0
    for nm, off, osz, st in entries:
        plain, _ = K.get_block(d, off, osz, st)
        events = []
        for m in re.finditer(re.escape(MSG), plain):
            events.append((m.start(), 'msg'))
        for m in re.finditer(re.escape(CHOICE), plain):
            events.append((m.start(), 'choice'))
        events.sort()
        for start, kind in events:
            plen = len(MSG) if kind == 'msg' else len(CHOICE)
            raw, _ = read_utf16z(plain, start + plen)
            ruby_n += len(RUBY.findall(raw))
            ctrl_n += len(re.findall(r'\\[a-zA-Z]{1,3}\[[^\]]*\]', raw))
            c = clean_msg(raw)
            if not c:
                skipped += 1
                continue
            lines.append(c); stat[kind] += 1
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('story=%d  choices=%d  total=%d' % (stat['msg'], stat['choice'], len(lines)))
    print('ruby=%d  ctrl_stripped=%d  empty_skipped=%d' % (ruby_n, ctrl_n, skipped))
    print('bytes=%d  ->  %s' % (os.path.getsize(out), out))


if __name__ == '__main__':
    main()
