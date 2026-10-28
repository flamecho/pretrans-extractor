#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re;quartz零度 (NS) SCRIPT.PAK → 全文本（双版对照）

记录形状（L1 自定界，实测 2026-10-24 修订）：
  消息 `24 03 | X(u16) | Y(u16) | Z(u16) | n(u16) | n×UTF-16LE | 00 00 | TT 0a 00 00 00 00`
    X = 场景内偏移（递增）
    Y = 全局行号（跳号处为被过滤的非正文记录）
    Z = 0 ⇒ 地文（旁白）；>0 ⇒ 角色台词序号（不同角色各自计数）
    TT = 页/段标记：0x0b = 清屏（页首）／0x03 · 0x05 = 同页追加（不清屏）

版式判定：
  S1 一次点击 = 每条消息记录（三条尾标记都含"显示后等待"）
  S2 页边界   = 尾标记 0x0b（清屏）
  S3 一页点击 = 1（页首）+ 后续 0x03/0x05 条数
  ⇒ 存在 ≥2 次/页（连续非 0b 段长 2:379 / 3:95 / 4:40 / 5:58 / 6:32 / 7:19 …14:1）⇒ 双版对照

选项 `"am" | A(u16) | B(u16) | C(u16) | n(u16) | n×UTF-16LE | 00 00`，串内 `$d` 分隔各选项。
正文形态：`@名前@本文` / `名前@本文` / 本文；注音 `$[本体$/よみ$]`；软换行 `\n`／`$N`／`$n`
"""
import struct, re, os

SRC = '_w_rq/romfs/SCRIPT.PAK'
OUT = '提取结果/[NS-JP]Re;quartz零度.txt'
RUBY = re.compile(r'\$\[([^$]*)(?:\$/[^$]*)?\$\]')
BLANK = re.compile(r'\$\[\$b\$b?([^]]*)\$\]')


def strip_ruby(s):
    s = re.sub(r'\$\[([^\]]*)\]',
               lambda m: '$[' + m.group(1).replace('$b', '') + ']', s)
    s = BLANK.sub(lambda m: m.group(1), s)
    return RUBY.sub(lambda m: m.group(1), s)


def split_name(s):
    if s.startswith('@'):
        t = s[1:]
        i = t.find('@')
        return t[i + 1:] if 0 < i <= 12 else t
    i = s.find('@')
    if 0 < i <= 12 and not any(c in s[:i] for c in '「」『』、。！？…'):
        return s[i + 1:]
    return s


def clean(s):
    s = strip_ruby(s)
    s = split_name(s)
    s = s.replace('$N', '').replace('$n', '')        # 排版换行 → 合并（停顿由记录边界体现）
    s = s.replace('\n', '').replace('\r', '')
    if s.startswith('$d'):
        s = s[2:]
    s = s.replace('$', '').replace('[', '').replace(']', '')
    return s.replace('\u00a0', '\u3000').strip()


def read_str(d, ts, n):
    raw = d[ts:ts + 2 * n]
    if d[ts + 2 * n:ts + 2 * n + 2] != b'\x00\x00':
        return None
    try:
        s = raw.decode('utf-16le')
    except Exception:
        return None
    if '\x00' in s or '\ufffd' in s:
        return None
    if any(ord(c) < 0x20 and c != '\n' for c in s):
        return None
    return s


def speaker(s):
    """取说话人前缀（'@女の声@「…」' → '女の声'；地文 → ''）"""
    if s.startswith('@'):
        t = s[1:]
        i = t.find('@')
        return t[:i] if 0 < i <= 12 else ''
    i = s.find('@')
    if 0 < i <= 12 and not any(c in s[:i] for c in '「」『』、。！？…'):
        return s[:i]
    return ''


def main():
    d = open(SRC, 'rb').read()
    N = len(d)
    recs = []
    for p in range(0x400, N - 6):
        if d[p - 8:p - 6] != b'\x24\x03':
            continue
        n = struct.unpack_from('<H', d, p)[0]
        if n == 0:
            # 空记录：纯控制（0b＝清屏，1796/1802）
            recs.append((p, d[p + 2], '', ''))
            continue
        if not (1 <= n <= 900) or p + 4 + 2 * n + 2 > N:
            continue
        s = read_str(d, p + 2, n)
        if s is None:
            continue
        end = p + 2 + 2 * n
        recs.append((p, d[end + 2], clean(s), speaker(s)))

    opts = []
    q = 0x400
    while True:
        q = d.find(b'\x61\x6d', q)
        if q < 0:
            break
        n = struct.unpack_from('<H', d, q + 8)[0]
        if 1 <= n <= 900 and q + 12 + 2 * n <= N:
            s = read_str(d, q + 10, n)
            if s is not None and ('$d' in s or n < 100):
                if q != 0x44c4:     # タイトル画面の章選択メニュー（UI）→ 不收
                    for k, opt in enumerate(s.split('$d')):
                        opt = re.sub(r'^\[\([^\]]*\),?\]', '', opt)
                        opts.append((q, 1, k, clean(opt)))
        q += 2

    # 双版对照（用户实机核对 + 连续 03 实例，2026-10-24 终版）
    # 唯一规则：**前一条是 0x03 ⇒ 并入同一框；否则另起一框**
    #   （0x03 自身总在"前一条非 03"时开框；0x05 与 0x0b 一律按"前一条是否 03"决定）
    #
    # 三处实测锚点全部自洽：
    #  ① 开场 5 条地文（真っ暗闇だ 等）全为 0b、前一条均非 03 ⇒ 各自独立成框 ✓
    #  ② 0x06354：`この際、さっきの女で良い。`(03) → `誰でも良い。`(0b，前一条 03 ⇒ 并入)
    #             → `人肌がないと――`(0b，前一条 0b ⇒ 新框)  ✓ 与用户实机一致
    #  ③ 连续 13 个 03（0x0e3xx 一带，表现剧痛）：
    #       `痛い、`×13 全部前一条是 03 ⇒ 并成同框（一屏连续显示），末条后接 05 收尾 ✓
    #  ④ 0x5aa8 物心ついた時には…(03) + 0x5ae8 ヒトあらざる者として…(0b) 同框 ✓
    pages, cur = [], []
    prev03 = False
    for p, mark, txt, pre in recs:
        if mark == 0x03:
            if not prev03 and cur:            # 前一条不是 03 ⇒ 开新框
                pages.append(cur)
                cur = []
            if txt:
                cur.append((p, txt, pre))
            prev03 = True
        else:
            if prev03 and cur:                # 前一条是 03 ⇒ 并入
                if txt:
                    cur.append((p, txt, pre))
            else:
                if cur:
                    pages.append(cur)
                    cur = []
                if txt:
                    cur = [(p, txt, pre)]
            prev03 = False
    if cur:
        pages.append(cur)

    events = [(pg[0][0], 0, 0, pg) for pg in pages]
    events += [(o[0], 1, o[2], [o]) for o in opts]
    events.sort(key=lambda x: (x[0], x[1], x[2]))

    lines, nmerged, nseg = [], 0, 0
    for _, kind, _, payload in events:
        if kind == 1:
            lines.append(payload[0][3])
            continue
        segs = [t for _, t, _ in payload]
        lines.extend(segs)          # 段行
        nseg += len(segs)
        if len(segs) >= 2:          # 合并行（单段页不重复）
            lines.append(''.join(segs))
            nmerged += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')

    multi = sum(1 for pg in pages if len(pg) >= 2)
    print('rec %d  pages %d  multi-page %d  choice %d'
          % (len(recs), len(pages), multi, len(opts)))
    print('段行 %d  合并行 %d  总行 %d  闭合校验 %d'
          % (nseg, nmerged, len(lines), nseg + nmerged + len(opts)))
    for pg in pages[:3]:
        print('  [框]', len(pg), '段：')
        for seg in pg:
            print('     -', seg[1][:44])


if __name__ == '__main__':
    main()
