#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三国恋戦記 魁 —— 全文本提取（对话/选项/结局/教程）
依赖：sgs_kai_ddp.py（同目录）
"""
import sys, os, re
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sgs_kai_ddp as K

SRC = os.path.join(VNTRANS_HOME, '_src_sgs_kai')
OUT = os.path.join(VNTRANS_HOME, '提取结果')
MSG_PFX = b'\x03\x0d\x36\xff\x01\x80'   # 剧情消息命令
CHOICE_PFX = b'\x03\x0d\x32\xff\x02\x0d\x0c\xff\x01\x80'  # 选项/心声命令
STR_OP  = b'\xff\x01\x80'                # 字符串参数
SEP = '\\n'                              # 脚本内换行 = 字面反斜杠+n

def read_utf16z(data, p):
    buf = bytearray(); q = p
    while q + 1 < len(data) and not (data[q] == 0 and data[q+1] == 0):
        buf += data[q:q+2]; q += 2
    return buf.decode('utf-16le', 'replace'), q + 2

_MARKER = re.compile(r'^(?:\\s\[[^\]]*\])+$')   # 纯语音/音效标记

def clean(s):
    s = s.replace('\u8001', '')
    if SEP in s:
        first, rest = s.split(SEP, 1)
        is_name = (_MARKER.match(first) is not None) or (
            len(first) <= 10 and rest[:1] in '「（『' and first[-1:] not in '、。！？…')
        if is_name:                 # 首段=说话人名（或纯语音标记）→ 剥除
            s = rest
        # 否则首段是正文的第 1 个软换行 → 整串保留
    s = re.sub(r'\\s\[[^\]]*\]', '', s)
    s = re.sub(r'\\[a-zA-Z]{1,3}\[[^\]]*\]', '', s)
    s = s.replace(SEP, '')
    return s.strip()

def order_key(name):
    g = 9; ch = 0; sec = 0
    m = re.match(r'^(.+?)_ch(\d+)_sec(\d+)$', name)
    if name == 'プロローグ':
        g = 0
    elif m:
        ch = int(m.group(2)); sec = int(m.group(3))
        g = {'hakuhu': 1, 'kada': 2, 'honsyo': 3, 'rt_chuei': 4, 'rt_housen': 5}.get(m.group(1), 6)
    elif 'end' in name or 'badend' in name or 'good' in name:
        g = 7
        mm = re.search(r'end_bad(\d+)', name); ch = 100 + (int(mm.group(1)) if mm else 0)
    elif name == 'subroutine':
        g = 99
    else:
        g = 8
    return (g, ch, sec, name)

def extract(plain, mode):
    """mode='msg'：03 0d 36 剧情；mode='nl'：任意含字面\\n 的字符串（结局）；
       mode='choice'：03 0d 32 选项/心声"""
    out = []
    if mode == 'msg':
        for m in re.finditer(re.escape(MSG_PFX), plain):
            s, _ = read_utf16z(plain, m.start() + len(MSG_PFX))
            c = clean(s)
            if c: out.append(c)
    elif mode == 'choice':
        for m in re.finditer(re.escape(CHOICE_PFX), plain):
            s, _ = read_utf16z(plain, m.start() + len(CHOICE_PFX))
            c = clean(s)
            if c: out.append(c)
    else:
        for m in re.finditer(re.escape(STR_OP), plain):
            s, _ = read_utf16z(plain, m.start() + len(STR_OP))
            if SEP in s:
                c = clean(s)
                if c: out.append(c)
    return out

def main():
    os.makedirs(OUT, exist_ok=True)
    # 1) 剧情
    d, entries, _ = K.parse_ddp(os.path.join(SRC, 'sgs_text.dat'))
    named = sorted([e for e in entries if e[2] is not None], key=lambda e: order_key(e[0]))
    lines = []; choices = []
    for nm, off, osz, st in named:
        plain, _ = K.get_block(d, off, osz, st)
        lines += extract(plain, 'msg')
        choices += extract(plain, 'choice')
    with open(os.path.join(OUT, '三国恋戦記 魁_全文本.txt'), 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    if choices:
        with open(os.path.join(OUT, '三国恋戦記 魁_选项.txt'), 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(choices) + '\n')
    print('剧情行', len(lines), '选项行', len(choices))

    # 2) 结局（sgs_endd.dat）
    ed = os.path.join(SRC, 'sgs_endd.dat')
    if os.path.exists(ed):
        de, eent, _ = K.parse_ddp(ed)
        out = []
        for nm, off, osz, st in eent:
            if osz is None: continue
            try: plain, _ = K.get_block(de, off, osz, st)
            except Exception: continue
            ms = extract(plain, 'nl')
            if ms:
                out.append('========== %s ==========' % nm); out += ms
        if out:
            with open(os.path.join(OUT, '三国恋戦記 魁_结局文本.txt'), 'w', encoding='utf-8-sig', newline='\n') as f:
                f.write('\n'.join(out) + '\n')
            print('结局行', len(out))

    # 3) 教程（Help HTML）
    hdir = os.path.join(SRC, 'Help')
    if os.path.isdir(hdir):
        tut = []
        for fn in sorted(os.listdir(hdir)):
            if fn.lower().endswith(('.htm', '.html')):
                raw = open(os.path.join(hdir, fn), 'rb').read()
                txt = raw.decode('cp932', 'replace')
                txt = re.sub(r'(?is)<script.*?</script>', '', txt)
                txt = re.sub(r'(?is)<style.*?</style>', '', txt)
                txt = re.sub(r'(?is)<br\s*/?>', '\n', txt)
                txt = re.sub(r'(?is)</(p|div|tr|h\d|li|td)>', '\n', txt)
                txt = re.sub(r'(?s)<[^>]+>', '', txt)
                txt = txt.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                body = '\n'.join(l.strip() for l in txt.split('\n') if l.strip())
                if body:
                    tut.append('===== %s =====' % fn); tut.append(body)
        if tut:
            with open(os.path.join(OUT, '三国恋戦記 魁_教程.txt'), 'w', encoding='utf-8-sig', newline='\n') as f:
                f.write('\n'.join(tut) + '\n')
            print('教程段', len(tut))

if __name__ == '__main__':
    main()
