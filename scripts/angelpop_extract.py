#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[JP]Angel ★ Pop  正文提取（KiriKiri KAG3 / cp932 .ks）

断框判据（L0，代码级）来自 system/MainWindow.tjs 的 tag handler 表：
  l  (4324) -> showLineBreak(3736) -> conductor.wait(%[click:...])   ⇒ 行クリック待ち（一次点击）
  p  (4330) -> showPageBreak(3781) -> conductor.wait(%[click:...])   ⇒ ページクリック待ち（一次点击）
  r  (4203) -> processReturn                                        ⇒ 改行（框内换行，合并）
  ct (4351) -> clearMessageLayers(true)   / cm (4360) -> clearMessageLayers(false)
  er (4369) -> current.clear()                                      ⇒ 清屏，不等点击
  s  (4463) -> inSleep（選択肢待ち）
说明：
  * .ks 里的物理换行**不进显示**（正文由 KAGParser 逐字生成 [ch]，换行不产生字符），
    所以一段文本可以跨多个物理行，必须按 [l]/[p] 聚合。
  * 人名不可解宏（[emb exp=sf.琥珀] / sf.ルキエル）用游戏内字面默认值定值，
    出处见报告（[eval exp="sf.琥珀='琥珀'"]、说话人标签行字面写 琥珀）。
用法:
  python scripts/angelpop_extract.py stats <ksdir>
  python scripts/angelpop_extract.py out   <ksdir> <outfile> [--files a,b,c]
"""
import sys, os, re, glob

NAME_MAP = {
    'sf.琥珀': '琥珀',
    'sf.ルキエル': 'ルキエル',
}
OPTION_SEP = '\n'

# 按标签区段整段跳过（结构判据：该段是名前入力ダイアログ＝系统 UI）
SKIP_RANGES = {
    'sinario1.ks': [('input_name', 'start10')],
}


_cls = {}


def tag_scan(s):
    """把 s 切成 ('t', 文本) / ('g', 标签名, 原始标签串) —— 属性里带 ] 的也能正确闭合"""
    out = []
    i = 0
    n = len(s)
    buf = []
    while i < n:
        c = s[i]
        if c != '[':
            buf.append(c)
            i += 1
            continue
        # 可能是标签，也可能是正文里孤立的 '['（本作正文无 '['，保守判定：能配对才当标签）
        j = i + 1
        q = None
        while j < n:
            ch = s[j]
            if q:
                if ch == q:
                    q = None
            elif ch in '"\'':
                q = ch
            elif ch == ']':
                break
            j += 1
        if j >= n:
            buf.append(c)
            i += 1
            continue
        inner = s[i + 1:j]
        m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)', inner)
        if not m:
            buf.append(c)
            i += 1
            continue
        if buf:
            out.append(('t', ''.join(buf)))
            buf = []
        out.append(('g', m.group(1), inner))
        i = j + 1
    if buf:
        out.append(('t', ''.join(buf)))
    return out


def parse_file(path):
    """返回 ([line, ...], [option, ...], stats)"""
    raw = open(path, 'rb').read()
    txt = raw.decode('cp932')
    phys = txt.split('\r\n')

    lines = []
    options = []
    cur = []
    opt = None
    in_macro = 0
    in_script = 0
    carry = ''
    dead = False          # [s] 之后到下一个 *label 之间的文本不可达
    label = None
    skipping = False
    st = {'flush': 0, 'dead_drop': 0, 'skip_drop': 0, 'b_clear': 0, 'empty': 0, 'tail': 0,
          'by': {}}
    ranges = SKIP_RANGES.get(os.path.basename(path), [])
    # f.選択肢N 的字面值（同文件 [eval] 直接给出）
    vmap = {}
    for m in re.finditer(r"f\.(選択肢\d+)='([^']*)'", txt):
        vmap['f.' + m.group(1)] = m.group(2)

    def flush(kind='click'):
        s = ''.join(cur).strip()
        del cur[:]
        if s:
            lines.append(s)
            st['flush'] += 1
            st['by'][kind] = st['by'].get(kind, 0) + 1
            if kind != 'click':
                st['b_clear'] += 1
        else:
            st['empty'] += 1

    for ln in phys:
        if ln.endswith('\\'):
            ln = ln[:-1]
        s = carry + ln
        carry = ''
        s = s.strip()
        if not s:
            continue
        if s.startswith(';'):
            continue
        if s.startswith('*'):
            nm = s[1:].split('|')[0].strip()
            label = nm
            dead = False
            if skipping and ranges and any(nm == e for _, e in ranges if True):
                # 结束标签（按当前命名空间匹配）
                for b, e in ranges:
                    if nm == e and skipping == b:
                        skipping = False
            if ranges and not skipping:
                for b, e in ranges:
                    if nm == b:
                        skipping = b
                        break
            if skipping:
                del cur[:]
                continue
            continue
        if s.startswith('@'):
            # 行レベル TJS：@iscript..@endscript 整块跳过
            if re.match(r'@iscript\b', s):
                in_script += 1
            elif re.match(r'@endscript\b', s):
                in_script = max(0, in_script - 1)
            continue
        if in_script:
            if '[endscript' in s:
                in_script = max(0, in_script - 1)
            continue

        if skipping:
            st['skip_drop'] += 1
            continue

        toks = tag_scan(s)
        for tok in toks:
            if tok[0] == 't':
                t = tok[1]
                if dead:
                    if t.strip():
                        st['dead_drop'] += 1
                    continue
                (opt if opt is not None else cur).append(t)
                continue
            name = tok[1]
            if name == 'iscript':
                in_script += 1
                continue
            if name == 'endscript':
                in_script = max(0, in_script - 1)
                continue
            if in_script:
                continue
            if name == 'macro':
                in_macro += 1
                continue
            if name == 'endmacro':
                in_macro = max(0, in_macro - 1)
                continue
            if in_macro:
                continue
            if name in ('l', 'p'):
                flush(name)
            elif name in ('ct', 'cm', 'er'):
                flush('clear')
            elif name == 'r':
                pass                      # 框内改行 -> 合并
            elif name == 's':
                flush('s')
                dead = True
            elif name == 'link':
                flush('opt')              # 选项前把已积累的正文收掉
                opt = []
            elif name == 'endlink':
                if opt is not None:
                    o = ''.join(opt).strip()
                    if o:
                        options.append(o)
                    opt = None
            elif name == 'emb':
                m = re.search(r'exp\s*=\s*"?([^"\]]+)"?', tok[2])
                k = (m.group(1).strip() if m else '')
                if k in NAME_MAP:
                    t = NAME_MAP[k]
                    (opt if opt is not None else cur).append(t)
                elif k in vmap:
                    (opt if opt is not None else cur).append(vmap[k])
                # 其它（f.* 数值 / bookmark）落在系统 UI，正文里不出现 -> 直接丢
    n0 = len(lines)
    flush('tail')
    st['tail'] = 1 if len(lines) > n0 else 0
    return lines, options, st


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    cmd, ksdir = a[0], a[1]
    files = sorted(glob.glob(os.path.join(ksdir, '*.ks')))
    if cmd == 'stats':
        tot = 0
        for f in files:
            L, O, st = parse_file(f)
            tot += len(L)
            print('%-26s lines=%5d opts=%3d dead=%d skip=%d noclr=%d empty=%3d tail=%d bytes=%7d' % (
                os.path.basename(f), len(L), len(O), st['dead_drop'], st['skip_drop'], st['b_clear'],
                st['empty'], st['tail'], os.path.getsize(f)))
        print('--- total lines', tot)
        return 0
    if cmd == 'out':
        outfile = a[2]
        order = None
        if '--order' in a:
            order = a[a.index('--order') + 1].split(',')
        allines = []
        idx = {os.path.basename(f): f for f in files}
        seq = ([idx[o] for o in order if o in idx] if order else files)
        for f in seq:
            L, O, st = parse_file(f)
            allines.extend(L)
            allines.extend(O)
        body = '\n'.join(allines) + '\n'
        open(outfile, 'wb').write(b'\xef\xbb\xbf' + body.encode('utf-8'))
        print('wrote', outfile, len(allines), 'lines', len(body), 'chars')
        return 0
    print('unknown cmd')
    return 1


if __name__ == '__main__':
    sys.exit(main())
