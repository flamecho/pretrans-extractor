#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""NScripter (nscript.dat) 文本提取器。
用法: python ns_rip.py <游戏目录或nscript.dat> [-o 输出目录]
输出: <name>_全文本.txt + <name>_选项.txt + <name>_诊断.json
"""
import os, re, sys, json, argparse

TERM = ('\\', '@')
CMD_HEAD = re.compile(r'^[A-Za-z_!]')
PLATE_CH = '◆■□★☆▼▲●○◇※◎▽△'
HAS_JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\uff66-\uff9f]')

def decode_dat(path):
    b = open(path, 'rb').read()
    if b'*define' in b or b'caption' in b or b'*start' in b:
        return b.decode('cp932', 'replace'), 'plain'
    x = bytes(c ^ 0x84 for c in b)
    if b'*define' in x or b'*start' in x or b'caption' in x:
        return x.decode('cp932', 'replace'), 'xor84'
    return None, 'fail'

def find_script(root):
    cands = [root, os.path.join(root, '本編'), os.path.join(root, 'game'),
             os.path.join(root, 'グロ有ver')]
    for c in cands:
        f = os.path.join(c, 'nscript.dat')
        if os.path.isfile(f):
            return f
    # ns2/nscripter 有时脚本在 arc.nsa 里，暂不处理
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.lower() == 'nscript.dat':
                return os.path.join(dirpath, f)
    return None

def is_cmd(s):
    if not s:
        return True
    c = s[0]
    if c in ';#*@\\?!%':          # 注释 / label / 旧式命令 / 颜色码
        return True
    if CMD_HEAD.match(s):          # ASCII 命令名
        return True
    if c in '"\'':                 # 命令参数续行（菜单按钮定义）
        return True
    return False

def plate_of(line):
    """返回 (是否名札, 名字)"""
    s = line.strip()
    if not s:
        return False, None
    if s[0] in PLATE_CH and s[-1] in PLATE_CH and len(s) <= 24:
        # ◆　名前　◆ / ■私■ / ▼　群青路　▼
        inner = s.strip(PLATE_CH).strip().strip('\u3000').strip()
        return True, inner
    return False, None

def looks_like_bare_name(s, nxt):
    if not s or len(s) > 12:
        return False
    if s[0] in '「『（(【':
        return False
    if re.search(r'[。、！？…」』）)]', s):
        return False
    if not nxt:
        return False
    if nxt.lstrip()[:1] not in '「『（(':
        return False
    return True

def split_quote_safe(segs):
    """把 @ 切开的段按引号配对合并；能平衡则保留切分。"""
    out = []
    buf = ''
    for g in segs:
        buf += g
        if balanced(buf):
            if buf.strip():
                out.append(buf)
            buf = ''
    if buf.strip():
        if out:
            out[-1] += buf
        else:
            out.append(buf)
    return out

def balanced(t):
    return t.count('「') == t.count('」') and t.count('『') == t.count('』')

def parse(text, log):
    lines = [l.rstrip('\r') for l in text.split('\n')]
    msgs = []
    opts = []
    cur = []          # 当前 chunk 的各 click 段
    seg = ''
    run = False       # 是否在文本行内
    plate = ''
    last_plate = ''
    pending_name = ''  # 裸名待确认

    def flush():
        nonlocal cur, seg, plate, last_plate
        if seg:
            cur.append(seg)
        if cur:
            pieces = split_quote_safe(cur)
            for p in pieces:
                p = clean(p)
                if p:
                    msgs.append((plate, p))
        cur = []
        seg = ''
        plate = ''
        last_plate = ''

    for idx, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        if s.startswith(';') or s.startswith('*'):
            run = False
            continue
        # 名札（带框字符）
        ok, nm = plate_of(raw)
        if ok and not (raw.strip().endswith('\\') or raw.strip().endswith('@')):
            flush()
            plate = nm
            continue
        term = None
        body = raw
        if raw.rstrip().endswith('\\'):
            term = '\\'
            body = raw.rstrip()[:-1]
        elif raw.rstrip().endswith('@'):
            term = '@'
            body = raw.rstrip()[:-1]
        if term is None and not run:
            # 可能是裸名 / 也可能是漏网的命令 / 也可能是无终止符的正文首行
            nxt = lines[idx + 1] if idx + 1 < len(lines) else ''
            if is_cmd(s) or not HAS_JP.search(s):
                continue
            if looks_like_bare_name(s, nxt):
                flush()
                pending_name = s
                plate = s
                continue
            log['orphan'].append(s[:60])
        if term is None and run:
            seg += body          # 软续行：同一条显示行继续
            continue
        # 正式文本行
        seg += body
        run = (term is None)
        if term == '@':
            cur.append(seg)
            seg = ''
        elif term == '\\':
            cur.append(seg)
            seg = ''
            flush()
    flush()
    return msgs

def clean(t):
    t = t.replace('\\u3000', '\u3000')
    t = t.strip().strip('\u3000').strip()
    return t

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('--name', default=None)
    a = ap.parse_args()
    gdir = a.target
    if os.path.isfile(gdir):
        script = gdir
        name = a.name or os.path.splitext(os.path.basename(os.path.dirname(gdir)))[0]
    else:
        script = find_script(gdir)
        name = a.name or os.path.basename(os.path.abspath(gdir))
    text, how = decode_dat(script)
    if text is None:
        print('DECODE FAIL', script); sys.exit(2)
    log = {'orphan': []}
    msgs = parse(text, log)
    out = a.out or os.path.dirname(os.path.abspath(script))
    with open(os.path.join(out, 'dbg_msgs.txt'), 'w', encoding='utf-8') as f:
        for pl, t in msgs:
            f.write(f'[{pl}] {t}\n')
    print(f'{name}: {how} msgs={len(msgs)} orphan={len(log["orphan"])}')
    for o in log['orphan'][:10]:
        print('  orphan:', o)

if __name__ == '__main__':
    main()
