#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SympathyKiss (NS) STCM2L 文本提取

链路: NSP(PFS0) → 主 NCA → romfs/CONTENTS/STORY.cpk → SCRIPT/*.DAT (STCM2L, UTF-8)
指令: [u32 func][u32 argc][u32 len][argc*3 u32 槽][行内串区]
串记录: [u32 size][u32 0x10][u32 0][u32 L/4][u32 1][u32 L][utf8][NUL][pad]（24B 头）
语义（跨文件稳定，仅两套函数编号）:
  正文  0x54b4c（A 组）/ 0x16ff0（B 组：X00 文件）
  地の文 0x17160 / 手机邮件正文 0x18704
  名札  0x54568 / 0x527f0 / 0x1849c / 0x1a588（丢弃）
  收框  0x54e5c / 0x52e30 / 0x1f4（一次点击）
  选项  0x1c7e4 / 0x19a70 / 0x4ad1c（槽内 sureN 跳转标签）
  变体  0x333e0 / 0x336c8 / 0x33a08 / 0x340b4 / 0x33da0 / 0x34734 / 0x34420
        （同句两版：明文版 + #Name 版，取明文版）
用法: python scripts/sympathy_extract.py <SCRIPT目录> <out.txt>
"""
import sys, os, glob, struct, re

HERO = '朱里'          # 天沢 朱里（vndb c111870）；#Name[1]=天沢 / #Name[2]=朱里
BODY = {0x54b4c, 0x16ff0, 0x17160, 0x18704}
VARIANT = {0x333e0, 0x336c8, 0x33a08, 0x340b4, 0x33da0, 0x34734, 0x34420}
TITLE = {0x2fa8}
CHOICE = {0x1c7e4, 0x19a70, 0x4ad1c}
FLUSH = {0x54e5c, 0x52e30, 0x1f4}
RE_SURE = re.compile(r'^sure\d+$')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff01-\uff60\u2010-\u2030\u2026\u2015]')
RE_RUBY = re.compile(r'#Ruby\[([^,\]]*),[^\]]*\]')
RE_MACRO = re.compile(r'#[A-Za-z][A-Za-z0-9_]*(\[[^\]]*\])?')
SKIP_FILES = {'1000.DAT', '99.DAT',
              '950.DAT', '951.DAT', '952.DAT', '953.DAT', '954.DAT',
              '955.DAT', '956.DAT', '957.DAT', '958.DAT', '959.DAT'}


def readrec(d, off):
    """槽指针 → 串；24 字节头 [size][0x10][0][L/4][1][L]，也兼容 16/12 字节头。"""
    if off < 0 or off + 24 > len(d) or off % 4:
        return None
    try:
        if (struct.unpack_from('<I', d, off + 8)[0] == 0
                and struct.unpack_from('<I', d, off + 12)[0] * 4
                == struct.unpack_from('<I', d, off + 20)[0]
                and struct.unpack_from('<I', d, off + 16)[0] == 1):
            L = struct.unpack_from('<I', d, off + 20)[0]
            body = off + 24
        else:
            a, l4, one, L = struct.unpack_from('<4I', d, off)
            if a == 0 and one == 1 and L == l4 * 4:
                body = off + 16
            else:
                l4, one, L = struct.unpack_from('<3I', d, off)
                if one != 1 or L != l4 * 4:
                    return None
                body = off + 12
    except struct.error:
        return None
    if not (4 <= L <= 20000) or body + L > len(d):
        return None
    raw = d[body:body + L]
    z = raw.find(b'\x00')
    if z < 0:
        z = len(raw)
    if raw[z:].strip(b'\x00'):
        return None
    try:
        return raw[:z].decode('utf-8')
    except Exception:
        return None


def walk(d):
    i = d.find(b'CODE_START_')
    if i < 0:
        return []
    o, n, out = i + 16, len(d), []
    while o + 12 <= n:
        op, argc, ln = struct.unpack_from('<3I', d, o)
        if ln < 12 or ln % 4 or o + ln > n or argc > 200 or 12 + argc * 12 > ln:
            break
        args = struct.unpack_from('<%dI' % (argc * 3), d, o + 12) if argc else ()
        ss = [readrec(d, args[k * 3]) for k in range(argc)]
        out.append((op, ss))
        o += ln
    return out


def clean(s):
    s = RE_RUBY.sub(lambda m: m.group(1), s)
    s = s.replace('#Name[1]', '天沢').replace('#Name[2]', '朱里')
    s = s.replace('#n', '')
    s = RE_MACRO.sub('', s)
    s = s.replace('\\n', '')
    return s.strip()


def is_text(s):
    return bool(s) and bool(JP.search(s))


def variant_text(ss):
    """取同句两版中的明文版（第一段）。"""
    got, seen = [], False
    for s in ss:
        if is_text(s):
            got.append(s)
            seen = True
        elif seen:
            break
    return got


def main():
    src, dst = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(src, '*.DAT')),
                   key=lambda p: int(re.sub(r'\D', '', os.path.basename(p)) or 0))
    lines, stats, dropped = [], [], []
    for f in files:
        name = os.path.basename(f)
        if name in SKIP_FILES:
            continue
        d = open(f, 'rb').read()
        if not d.startswith(b'STCM2L'):
            continue
        # 2026-10-27 判据：本作 romfs 里混有**两套指令体系**，只有 A 组是在用的。
        #   A 组（在用；dbEntryScript.gbin 已登记）：正文 0x54B4C + 地の文 0x17160 + 收框 {0x54E5C,0x1F4}
        #   B 组（未登记；另一版旧稿）：单一正文 0x16FF0 + 收框 0x52E30，无 0x17160
        # B 组 6 个文件（300/400/500/600/700/800.DAT）与同组 X01 重复 35–49%，
        # 且成品里全部 145 处 `＃＃＃` 名字掩码、以及「台词+地の文被合成一行」的样本都出自它们 ⇒ 剔除。
        ops_seen = {op for op, _ in walk(d)}
        if 0x16FF0 in ops_seen and 0x17160 not in ops_seen:
            dropped.append(name)
            continue
        cur, cnt = [], 0

        def flush():
            nonlocal cur, cnt
            if cur:
                t = clean(''.join(cur))
                if t:
                    lines.append(t)
                    cnt += 1
                cur = []

        for op, ss in walk(d):
            if op in BODY:
                if ss and is_text(ss[0]):
                    cur.append(ss[0])
            elif op in VARIANT:
                cur.extend(variant_text(ss))
            elif op in TITLE:
                flush()
                t = [s for s in ss if is_text(s)]
                if t:
                    lines.append(clean(t[0]))
                    cnt += 1
            elif op in CHOICE:
                flush()
                t = [s for s in ss if is_text(s) and not RE_SURE.match(s)]
                if t:
                    lines.append(clean(t[0]))
                    cnt += 1
            elif op in FLUSH:
                flush()
        flush()
        stats.append((name, cnt))

    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('lines', len(lines))
    if dropped:
        print('dropped B-set (未登记的另一版脚本): %s' % ' '.join(sorted(dropped)))
    for n, c in stats:
        print('  %-10s %5d' % (n, c))


if __name__ == '__main__':
    main()
