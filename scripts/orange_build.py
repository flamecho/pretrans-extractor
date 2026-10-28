#!/usr/bin/env python3
"""Orange Honey 全文本成行

规则：
  - 每个 .OHS 的 A 表（u16 偏移数组，cntA = hdr[5]>>16）= 一条消息 = 一次点击
  - A 表首项恒为偏移 0（空），跳过
  - 首行场景标题 = 文本池第 1 条串（代码首条 `3c 0f 60 01 00` 引用）
  - 名札【…】在 B 表（另一张表），不进 A 表，天然剔除
  - 文本池内 `\n` = 同框软换行 → 直接拼接
  - %family% → 加瀬 / %name% → 愛葉
  - 选项：SCENARIO.OHS 的 A 表（流程脚本），按 A 序附于末尾
"""
import glob, os, re, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orange_ohs import decrypt_text

FAMILY = '加瀬'
NAME = '愛葉'

SKIP = ('SCENARIO.OHS', 'MAINSCRIPT.OHS')


def is_path(s):
    return '\\' in s or s.endswith('.tm2') or s.endswith('.ads') or s.endswith('.adv')


def clean(s):
    s = s.replace('\r', '')
    s = s.replace('\n', '')
    s = s.replace('%family%', FAMILY).replace('%name%', NAME)
    return s.strip()


def a_table(d):
    h = struct.unpack_from('<12I', d, 0)
    cnt = h[5] >> 16
    off = h[7]
    if cnt == 0 or off + cnt * 2 > len(d):
        return []
    return list(struct.unpack_from('<%dH' % cnt, d, off))


def build():
    files = sorted(glob.glob('_work_orange/scr/*.OHS'))
    out = []
    stats = {'files': 0, 'titles': 0, 'lines': 0}
    for f in files:
        base = os.path.basename(f)
        if base in SKIP:
            continue
        d = open(f, 'rb').read()
        if d[:4] != b'\xb5\xda\xca\xc6':
            continue
        blob, _ = decrypt_text(d)
        parts = blob.split(b'\x00')
        A = a_table(d)
        lines = []
        # 场景标题（池内第 1 条）
        if len(parts) > 1:
            t = clean(parts[1].decode('cp932', 'replace'))
            if not t and len(parts) > 2:
                t2 = clean(parts[2].decode('cp932', 'replace'))
                if t2 and t2 not in [blob[a:].split(b'\x00')[0].decode('cp932', 'replace') for a in A]:
                    t = t2
            if t and not is_path(t) and not t.startswith('【'):
                lines.append(t)
                stats['titles'] += 1
        for a in A:
            if a == 0 or a >= len(blob):
                continue
            s = clean(blob[a:].split(b'\x00')[0].decode('cp932', 'replace'))
            if not s or is_path(s):
                continue
            if re.fullmatch(r'【[^】]*】', s):
                continue
            lines.append(s)
        if lines:
            out.extend(lines)
            stats['files'] += 1
            stats['lines'] += len(lines)
    # 选项
    d = open('_work_orange/scr/SCENARIO.OHS', 'rb').read()
    blob, _ = decrypt_text(d)
    opts = []
    for a in a_table(d):
        if a == 0 or a >= len(blob):
            continue
        s = clean(blob[a:].split(b'\x00')[0].decode('cp932', 'replace'))
        if not s or is_path(s):
            continue
        opts.append(s)
    out.extend(opts)
    stats['options'] = len(opts)
    print(stats)
    return out


if __name__ == '__main__':
    lines = build()
    dst = sys.argv[1]
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as w:
        for l in lines:
            w.write(l + '\n')
    print('wrote', dst, len(lines))
