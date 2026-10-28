#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]DistortedCode ―生者の残り香― text extract (TAKUYO gss / SCR 3.00).

Chain: XCI -> (hand-carved NCAs) -> Program NCA -> RomFS
       SCRDATA.BIN (LSDARC V.100 index) + SCRDATA.ARC (277 x "SCR 3.00", all unpacked)

Line model (L0, bytecode):
  0x5a  message fragment        | 0xfc  same + %s (slot 0c02 = 澪)
  tail code \\d  = click wait    | tail \\u (=before \\d) = the *same display line* continues
  head code \\n  = display-line start marker (no blank line)
  => one display line == the run of fragments joined by \\u ; 單一推進指令(\\d) => 单版
  0xf0 = chapter title card (扉文) | 0x5c = choices ("text ,flag")
  0xfd/0x107 = image / name-plate (【名】) draws -> not text
"""
import os
import re
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gss_scr3 as D
import himehibi_lsdarc as L

ROM = '_work_dcode/romfs'
OUT = '提取结果/[NS-JP]DistortedCode ―生者の残り香―.txt'

# 主人公（vndb / rekowiki：伴星 澪）. 0xfc 的 %s 取 slot 0c02（INIT 0x15d9 FullName 定义）
SLOT = {'0c02': '澪'}
SYSTEM = {'AUTOEXEC', 'INIT', 'PRG_ROUTE', 'PRG_BG', 'PRG_EFFECT', 'PRG_EFFECTSTOP',
          'PRG_NAME', 'PRG_PLATE', 'PRG_STAND', 'PRG_TEXT', 'RELOAD', 'SELECT',
          'SELECT2', 'YURASHI', 'NAZOTOKI', 'PSY007X'}
MSG = {0x5a, 0xfc}
TITLE = 0xf0
OPT = 0x5c

RE_RUBY = re.compile(r'#r([^|#]*)\|([^#]*)#')
CHAP = {'PSY': 0, 'KAS': 1, 'OCC': 2, 'TRU': 3}


def decode_ruby(s):
    return RE_RUBY.sub(lambda m: m.group(1), s)


def subst(s, ops):
    """%s <- slot operands (type 6) of the same instruction"""
    if '%s' not in s:
        return s, False
    it = iter([SLOT.get(v, '') for t, v in ops if t == 6])
    return re.sub('%s', lambda m: next(it, ''), s), True


def fragments(raw, ops):
    """split one instruction string into click fragments.
    returns list of (text, cont) where cont=True -> next fragment is on the same display line"""
    out = []
    cur = []
    conn = False
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if c == '\\' and i + 1 < n:
            k = raw[i + 1]
            if k == 'd':
                out.append((''.join(cur), conn))
                cur = []
                conn = False
                i += 2
                continue
            if k == 'u':
                conn = True
                i += 2
                continue
            if k == 'n':
                i += 2          # display-line start marker -> dropped
                continue
            cur.append(k if k != 'u' else '')
            i += 2
            continue
        cur.append(c)
        i += 1
    if cur:
        out.append((''.join(cur), False))
    return out


def clean(s):
    s = decode_ruby(s)
    s = re.sub(r'@[a-zA-Z]', '', s)          # 残留的 @r 等引擎命令（全库 3 处）
    s = re.sub(r'[\x00-\x08\x0b-\x1f]', '', s)
    return s.strip().strip('\u3000').strip()


def emit_page(page, lines, stats):
    """一页（一个文本框）＝ 若干显示行，整页同时上屏。
    双版对照：先列各行，再列合并行（A,B,C,ABC）；单行页不重复。
    ★互斥对（0xfc 的 %s 版 / 0x5a 的实名版）必须在**段级**先去重，
      否则两版都会被拼进合并行，出现同句重复。"""
    if not page:
        return
    ded = []
    for t, hv in page:
        if ded and ded[-1][0] == t and ded[-1][1] != hv:
            stats['drop_dup'] += 1
            continue
        ded.append((t, hv))
    page = ded
    # 双版对照：一次点击一行（段行；段内 \u 行内软换行已在 fragments() 合并，不拆）＋ 一页一行
    if len(page) > 1:
        for t, hv in page:
            lines.append(('msg', t, hv))
        lines.append(('msg', ''.join(t for t, _ in page), any(h for _, h in page)))
        stats['dual_page'] += 1
    else:
        lines.append(('msg', page[0][0], page[0][1]))


def build():
    ents, _ = L.read_index(os.path.join(ROM, 'SCRDATA.BIN'))
    arc = open(os.path.join(ROM, 'SCRDATA.ARC'), 'rb').read()
    scripts = {}
    for e in ents:
        scripts[e['name'].upper()] = arc[e['off']:e['off'] + e['usz']]

    # ---- dispatch order (L0: PRG_ROUTE 0x1e calls) ----
    route, err = D.disasm(scripts['PRG_ROUTE'])
    assert not err, err
    route_order = []
    for off, op, size, ident, o in route:
        if op == 0x1e:
            ss = [v for t, v in o if t == 3]
            if len(ss) >= 2 and ss[0].lower().endswith('.scr'):
                nm = ss[0][:-4].upper()
                if nm not in route_order:
                    route_order.append(nm)
    idx = {nm: i for i, nm in enumerate(route_order)}

    def key(nm):
        m = re.match(r'([A-Z]{3})(\d+)', nm)
        if not m:
            return (9, 0, 0)
        return (CHAP.get(m.group(1), 5), int(m.group(2)), idx.get(nm, 999))

    todo = [nm for nm in scripts if nm not in SYSTEM and nm in idx]
    todo.sort(key=key)

    lines = []
    stats = collections.Counter()
    for nm in todo:
        res, err = D.disasm(scripts[nm])
        assert not err, (nm, err)
        buf = []          # pending fragments of the current display line
        page = []         # display lines accumulated in the current page (text box)
        for off, op, size, ident, o in res:
            ss = [v for t, v in o if t == 3]
            if op in MSG and ss:
                stats['op_%#x' % op] += 1
                txt, hasvar = subst(ss[0], o)
                if hasvar:
                    stats['var'] += 1
                stats['ruby'] += len(RE_RUBY.findall(txt))
                frs = fragments(txt, o)
                stats['frag'] += len(frs)
                if len(frs) > 1:
                    stats['multi_frag_op'] += 1
                for txt2, conn in frs:
                    t = clean(txt2)
                    if t:
                        buf.append((t, hasvar))
                    else:
                        stats['empty_frag'] += 1
                    if not conn:
                        if buf:
                            join = ''.join(x[0] for x in buf)
                            stats['merge'] += len(buf) - 1
                            page.append((join, any(x[1] for x in buf)))
                            buf = []
                            # page end: op tail is neither \d (line end) nor \u (same line continues)
                            if not txt.rstrip().endswith(('\\d', '\\u')):
                                emit_page(page, lines, stats)
                                page = []
            elif op == TITLE and ss:
                t = clean(ss[0])
                if t:
                    stats['title'] += 1
                    lines.append(('title', t, False))
            elif op == OPT:
                for s in ss:
                    body = s.rsplit(',', 1)[0]
                    t = clean(body)
                    if t:
                        stats['opt'] += 1
                        lines.append(('opt', t, False))
        if buf:
            stats['merge'] += len(buf) - 1
            page.append((''.join(x[0] for x in buf), any(x[1] for x in buf)))
            buf = []
        emit_page(page, lines, stats)

    # ---- 互斥对去重：0xfc(%s) 版与紧随其后的 0x5a(实名) 版逐字相同 -> 取一 ----
    dedup = []
    stats['drop_dup'] = 0
    for it in lines:
        if dedup and it[0] == 'msg' and dedup[-1][0] == 'msg' \
                and it[1] == dedup[-1][1] and (it[2] != dedup[-1][2]):
            stats['drop_dup'] += 1
            continue
        dedup.append(it)
    lines = dedup
    return lines, stats


def main():
    lines, stats = build()
    os.makedirs('提取结果', exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        for _, t, _ in lines:
            f.write(t + '\n')
    body = sum(1 for x in lines if x[0] == 'msg')
    print('total %d  msg %d  title %d  opt %d  drop_dup %d'
          % (len(lines), body, stats['title'], stats['opt'], stats['drop_dup']))
    print('stats', dict(stats))
    print('closure: ops %d = frag %d = lines(%d) + merge(%d) + empty(%d)'
          % (stats['op_0x5a'] + stats['op_0xfc'], stats['frag'],
             len(lines) - stats['title'] - stats['opt'], stats['merge'],
             stats['empty_frag']))
    L2 = [len(t) for _, t, _ in lines]
    L2.sort()
    print('len max %d p95 %d median %d' % (L2[-1], L2[int(len(L2) * .95)], L2[len(L2) // 2]))
    print('bytes', os.path.getsize(OUT))


main()
