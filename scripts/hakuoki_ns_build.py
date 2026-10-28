#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""薄桜鬼 遊戯録 隊士達の大宴会 (NS) —— 成品构建（正文＋选项＋扉文＋用語辞典）。

数据源
  cpk/d00|d01|d02/script/*  STCM2L（UTF-8）：正文/名札/选项/扉文
  cpk/d02/script/57         固定长表：状況ヒント 106 条（日文 100 条）
  cpk/sys/DATABASE/dbDictionary.gbin  用語辞典（cp932，#n=行内换行）

行粒度（L0/L1）
  一次点击 = 两条 {0x4BB,0x41B,0x41C,0x41D} 之间（0x41B/C/D=按名访问变量，引擎在此冲刷文本框）
  同点击内 0x6(goto) 互斥分支 ⇒ 取不含 #Name[ 的直写名版
  相邻相同正文且两侧点击都含 0x3(条件分岐) ⇒ 同一台詞的分支重複，只留一条
  0x4BC 名札 ⇒ 有独立名窗，丢弃
  0x4C0 扉文 ⇒ 输出【…】；紧随/紧邻 0x3 的是章名表，剔除

用法: python hakuoki_ns_build.py <out.txt>
"""
import sys, os, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hakuoki_ns_extract2 as E

ROOT = E.ROOT
SRC = E.SRC
TEXT, TITLE, OPT, NAME = E.TEXT, E.TITLE, E.OPT, E.NAME
HERO = E.HERO


def clicks_of(path):
    recs = E.walk(path)
    clicks, cur = [], []
    for gi, (op, ss) in enumerate(recs):
        if op in E.WAIT:
            clicks.append(cur)
            cur = []
        else:
            cur.append((gi, op, ss))
    if cur:
        clicks.append(cur)
    return recs, clicks


def click_rows(recs, ck):
    """返回 (rows, text, has_cond)。"""
    segs, s0 = [], 0
    for i, (gi, op, ss) in enumerate(ck):
        if op == E.GOTO:
            segs.append((s0, i))
            s0 = i + 1
    segs.append((s0, len(ck)))

    best, best_key = None, None
    for a, b in segs:
        txts = [ss[0] for gi, op, ss in ck[a:b] if op == TEXT and ss and ss[0].strip()]
        if not txts:
            continue
        body = E.seg_text(txts)
        key = (0 if '#Name[' in body else 1, len(body))
        if best_key is None or key > best_key:
            best, best_key = (a, b), key

    a, b = best if best else (0, 0)
    rows, buf = [], []

    def flush():
        if buf:
            t = E.clean(E.seg_text(buf)).strip()
            if t:
                rows.append(t)
            buf.clear()

    for i, (gi, op, ss) in enumerate(ck):
        if op == TEXT:
            if a <= i < b and ss and ss[0].strip():
                buf.append(ss[0])
        elif op == TITLE and ss and ss[0].strip():
            if (gi + 1 < len(recs) and recs[gi + 1][0] == 0x3) or \
               (gi > 0 and recs[gi - 1][0] == 0x3):
                continue
            flush()
            rows.append('【%s】' % E.clean(ss[0]).strip())
        elif op == OPT and ss and ss[0].strip():
            flush()
            rows.append(E.clean(ss[0]).strip())
    flush()
    body = ''.join(rows)
    has_cond = any(op == 0x3 for gi, op, ss in ck)
    return rows, body, has_cond


# —— 弃用（系统・UI）：结构与文本双重锚定，整点击剔除 ——
DROP_TEXT = ('どのシーンを見ますか',        # シーン選択メニュー（d00/100 开头，含 6 个菜单标签）
             '『桜下恋語り',                # 自動再生の可否ダイアログ（d02/203・207・211・215・219・223）
             '自動再生を有効に')            # 同上第二框（問い＋はい/いいえ）


def build_body():
    rows, prev, prev_cond, dropped = [], '', False, []
    for part in ('d00', 'd01', 'd02'):
        for f in sorted(glob.glob(os.path.join(SRC, part, 'script', '*')),
                        key=lambda p: int(os.path.basename(p))):
            recs, clicks = clicks_of(f)
            for ck in clicks:
                rs, body, cond = click_rows(recs, ck)
                if not rs:
                    continue
                if any(d in body for d in DROP_TEXT):
                    dropped.append((part + '/' + os.path.basename(f), rs[:3]))
                    continue
                # 条件分岐の重複台詞：両側に 0x3 があるときだけ 1 条に
                if body and body == prev and cond and prev_cond:
                    prev_cond = cond
                    continue
                rows.extend(rs)
                if body:
                    prev, prev_cond = body, cond
    return rows, dropped


def build_hints():
    """d02/script/57：固定长表（[u32 106][u32 8] + 记录），每条 #n 合并为一行。"""
    d = open(os.path.join(SRC, 'd02', 'script', '57'), 'rb').read()
    out = []
    for p in re.split(rb'\x00+', d):
        if len(p) < 6:
            continue
        try:
            s = p.decode('utf-8')
        except UnicodeDecodeError:
            continue
        if '\ufffd' in s or '#' in s.replace('#n', ''):
            continue
        if re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', s):
            out.append(s.replace('#n', '').strip())
    return out


def build_dict():
    """dbDictionary.gbin：头表 + 串区（0x1670..GBNL），每条 = 見出し語 / 読み / 解説。"""
    d = open(os.path.join(SRC, 'sys', 'DATABASE', 'dbDictionary.gbin'), 'rb').read()
    seg = d[0x1670:d.rfind(b'GBNL')]
    strs = [p.decode('cp932') for p in seg.split(b'\x00') if p]
    hira = lambda s: bool(s) and all(('\u3040' <= c <= '\u309f') or c in 'ー、・' for c in s)
    is_body = lambda s: s.endswith('#n') or s.endswith('。') or len(s) > 20

    out, skipped = [], 0
    i = 0
    while i < len(strs):
        head = strs[i]
        i += 1
        if i < len(strs) and hira(strs[i]) and len(strs[i]) <= 14:
            i += 1
        body = ''
        if i < len(strs) and is_body(strs[i]):
            body = strs[i]
            i += 1
        body = body.replace('#n', '').strip()
        if body:
            out.append('【%s】%s' % (head, body))
        else:
            skipped += 1
    return out, skipped, len(strs)


def main():
    dst = sys.argv[1]
    body, dropped = build_body()
    hints = build_hints()
    dic, skipped, nstr = build_dict()

    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for t in body + hints + dic:
            t = t.strip()
            if t:
                fh.write(t + '\n')

    print('正文/选项/扉文 %d' % len(body))
    print('状況ヒント %d' % len(hints))
    print('用語辞典 %d（串 %d，空解説跳过 %d）' % (len(dic), nstr, skipped))
    print('合计 %d' % (len(body) + len(hints) + len(dic)))
    print('剔除点击 %d:' % len(dropped))
    for f, r in dropped:
        print('   %s  %s' % (f, r))


if __name__ == '__main__':
    main()
