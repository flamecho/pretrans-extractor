#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Goes! (PCSG00367) 文本提取
链路：pkg -> psvpfsparser -> PSARC(cmp.psarc) -> script/script_N.bin + script_N.txt
脚本记录：8 字节 = [u32 op][u32 arg]
  op=0x202            : 取字符串表 script_N.txt 第 arg 行
  op=0x10004 arg=1    : 该串 = 正文（一次点击一行）
  op=0x10004 arg=11   : 该串 = 名札（丢弃）
  op=0x10004 arg=13/14: 该串 = 选项
  op=0x10004 arg=2    : 一次点击的推进（其计数 == scrlst.csv 场景区间，全 491 场景吻合）
  其余 op             : 资源/演出（0x2=立绘,0x302=脸,0x20004..=语音/SE,0x101/0x100/0x0=跳转）
"""
import os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, '_work_goes', 'x', 'cmp')
SCRIPT = os.path.join(BASE, 'script')
SYS = os.path.join(BASE, 'system')

HERO_SURNAME = '百瀬'
HERO_GIVEN = '志緒'


def load_pool(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\xff\xfe':
        raw = raw[2:]
    return raw.decode('utf-16-le', 'replace').split('\n')


def load_ops(path):
    with open(path, 'rb') as f:
        raw = f.read()
    return [struct.unpack_from('<II', raw, i * 8) for i in range(len(raw) // 8)]


NAME_RE = re.compile(r'<(\d+)>')


def expand_names(s):
    def rep(m):
        n = int(m.group(1))
        if n == 14:
            return HERO_SURNAME
        return HERO_GIVEN
    return NAME_RE.sub(rep, s)


def join_breaks(s):
    # 框内软换行：\  + 可选的缩进全角空格，合并时直接去掉
    s = s.replace('\\\\', '')
    s = re.sub(r'\\[　\s]?', '', s)
    return s


SKIP_PREFIX = ('★', '→＜', '流用番号', '引用○', 'フラグ分岐')


def is_dev_body(s):
    if s.startswith(SKIP_PREFIX):
        return True
    if re.fullmatch(r'[　\s]*[a-z_]+\([a-z]*\)', s):   # seloopout(seshort) 型函数调用
        return True
    return False


def extract_file(bin_path, txt_path):
    ops = load_ops(bin_path)
    pool = load_pool(txt_path)
    out = []
    n = len(ops)
    # 按一次点击切段：以 (0x10004,2) 结尾
    segs, cur = [], []
    for a, b in ops:
        if (a, b) == (0x10004, 2):
            segs.append(cur)
            cur = []
        else:
            cur.append((a, b))
    tail = cur

    def handle(seg):
        for i, (a, b) in enumerate(seg):
            if a != 0x202 or b >= len(pool):
                continue
            nxt = seg[i + 1] if i + 1 < len(seg) else (0, 0)
            if nxt[0] != 0x10004:
                continue
            v = nxt[1]
            s = pool[b]
            if v == 1:
                if is_dev_body(s):
                    continue
                out.append(join_breaks(expand_names(s)))
            elif v in (13, 14):
                if s.strip():
                    out.append(join_breaks(expand_names(s)))

    for sg in segs:
        handle(sg)
    handle(tail)
    return out


def main(out_path):
    rows = [r.split(',') for r in
            open(os.path.join(SYS, 'scrlst.csv'), 'rb').read().decode('utf-16-le')
            .replace('\r\n', '\n').split('\n') if r.strip()]
    order = []
    for r in rows[2:]:
        order.append((r[0], r[1]))

    lines, seen, dup = [], set(), 0
    for title, scr in order:
        b = os.path.join(SCRIPT, scr + '.bin')
        t = os.path.join(SCRIPT, scr + '.txt')
        if not (os.path.exists(b) and os.path.exists(t)):
            print('MISSING', scr)
            continue
        for s in extract_file(b, t):
            if not s.strip():
                continue
            lines.append(s)

    dedup = lines

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write('\n'.join(dedup).encode('utf-8'))
        f.write(b'\n')
    print('scenes', len(order), 'lines', len(lines), 'dup_removed', dup, 'final', len(dedup))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '提取结果/[PSV-JP]Goes!.txt')
