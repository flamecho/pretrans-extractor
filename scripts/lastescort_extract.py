# -*- coding: utf-8 -*-
"""ラストエスコート -Club Katze- (PSP) 全文本提取 —— 通用驱动

链路：ISO9660 → PSP_GAME/USRDIR/script.paf（NK/PAF 归档）→ PSCB 脚本 → 字符串池

用法：
  python scripts/lastescort_extract.py <iso> <out.txt> [--paf 已有的 script.paf]

NK/PAF 归档（本作全部 .paf）：
  +0x00 'NK' | +0x02 u16 count | +0x04 u32 总长 | +0x08 u32 hdr(=0x14)
  0x14 起 count×16B：[compSize][uncompSize][nameOff][dataOff]；数据按 0x800 对齐
  —— script.paf 内混有 MIG.(动画)/NC4/NC2/NK(嵌套, 内为 AM+MIG)，文本只在 PSCB。

PSCB 脚本：
  +0x00 'PSCB' | +0x04 u32 ver=2 | +0x0c u32 size | +0x14 u32 codeOff(=0x1c)
  +0x18 u32 dataOff → [dataOff,size) 为 NUL 分隔字符串池
  池语义：`$k`=文本框结束（一次点击）；`$r`=框内软换行（合并）
         无 `$k`+含 `/` = 选项组；无 `$k` 长句（op 0x36 消费）= 叙述；
         其余无 `$k` = 名札（姓/名分存）或回想菜单「タイトル＋あらすじ」
  ★ 校验：op `11 00 30 10`(=0x11) 出现次数 == `$k` 串数（本作 37570/37570）
  ★ 调试菜单脚本（本作 index 545「キャラ表示確認」）整脚本排除
"""
import struct, sys, os, re

SECTOR = 2048
SKIP_SCRIPTS = {'/545'}
UI_OPT = ('戻る', '次へ', '終了')


# ---------- ISO9660 ----------
def iso_entries(path):
    f = open(path, 'rb')
    f.seek(16 * SECTOR)
    d = f.read(SECTOR)
    if d[1:6] != b'CD001':
        raise SystemExit('不是 ISO9660：%s' % path)
    root_lba = struct.unpack('<I', d[158:162])[0]
    root_size = struct.unpack('<I', d[166:170])[0]
    out = []

    def walk(lba, size, prefix):
        f.seek(lba * SECTOR)
        buf = f.read(size)
        i = 0
        while i < len(buf):
            rl = buf[i]
            if rl == 0:
                i = ((i // SECTOR) + 1) * SECTOR
                continue
            if i + rl > len(buf):
                break
            ext, nlen = buf[i + 25], buf[i + 32]
            name = buf[i + 33:i + 33 + nlen]
            off = struct.unpack('<I', buf[i + 2:i + 6])[0]
            sz = struct.unpack('<I', buf[i + 10:i + 14])[0]
            if nlen == 1 and name[0] in (0, 1):
                i += rl
                continue
            nm = name.decode('latin1')
            if nm.endswith(';1'):
                nm = nm[:-2]
            full = prefix + '/' + nm
            if ext == 2:
                walk(off, sz, full)
            else:
                out.append((full, off, sz))
            i += rl

    walk(root_lba, root_size, '')
    return f, out


def iso_read(path, want):
    f, ents = iso_entries(path)
    for p, lba, sz in ents:
        if p.upper().endswith(want.upper()):
            f.seek(lba * SECTOR)
            return f.read(sz)
    raise SystemExit('ISO 内找不到 %s' % want)


# ---------- NK / PAF ----------
def paf_entries(d, base=0, depth=0, path=''):
    out = []
    if d[base:base + 2] != b'NK':
        return out
    cnt = struct.unpack('<H', d[base + 2:base + 4])[0]
    hdr = struct.unpack('<I', d[base + 8:base + 12])[0]
    if hdr != 0x14:
        return out
    for e in range(cnt):
        q = base + hdr + e * 16
        comp, unc, nameOff, doff = struct.unpack('<4I', d[q:q + 16])
        if comp == 0 or comp > 0x8000000:
            continue
        s = base + doff
        lab = path + '/%d' % e
        out.append((lab, s, comp))
        if d[s:s + 2] == b'NK' and depth < 3:
            out += paf_entries(d, s, depth + 1, lab)
    return out


# ---------- PSCB ----------
def pscb_pool(d, s, size):
    codeoff = struct.unpack('<I', d[s + 0x14:s + 0x18])[0]
    dataoff = struct.unpack('<I', d[s + 0x18:s + 0x1c])[0]
    if not (0x1c <= codeoff <= dataoff <= size):
        return None, None
    return d[s + codeoff:s + dataoff], [x for x in d[s + dataoff:s + size].split(b'\x00') if x]


def count_op36(code):
    n = 0
    for m in range(len(code) - 3):
        if code[m] == 0x36 and code[m + 1] == 0 and code[m + 2] == 0x20 and code[m + 3] == 0x10:
            n += 1
    return n


def clean(t):
    return t.replace('$r', '').replace('$k', '')


def extract(paf_bytes, fixes=None):
    fixes = fixes or {}
    lines = []
    for lab, s, comp in paf_entries(paf_bytes):
        if paf_bytes[s:s + 4] != b'PSCB':
            continue
        idx = lab
        code, strs = pscb_pool(paf_bytes, s, comp)
        if strs is None:
            continue
        ts = [x.decode('cp932', 'replace') for x in strs]
        if idx in SKIP_SCRIPTS:
            continue
        lead = []
        for t in ts:
            if t.endswith('$k'):
                break
            lead.append(t)
        n36 = count_op36(code)
        narration = set(lead[:n36]) if n36 else set()
        for t in ts:
            if t.endswith('$k') or t in narration:
                b = clean(t)
                if b.strip():
                    lines.append(b)
            elif '/' in t:
                for x in (clean(y).strip() for y in t.split('/')):
                    if x and x not in UI_OPT:
                        lines.append(x)
    txt = '\n'.join(fixes.get(l, l) for l in lines) + '\n'
    return txt, len(lines)


FIXES = {
    '（流聖さん、本気で言ってくれてるのよね……。': '（流聖さん、本気で言ってくれてるのよね……。）',
    '（酔っぱらってるみたいだから、声をかけないほうがいいわよね。)': '（酔っぱらってるみたいだから、声をかけないほうがいいわよね。）',
    '(今日は流聖さんとデートできるはずだったのに、急にキャンセルなんて残念……）': '（今日は流聖さんとデートできるはずだったのに、急にキャンセルなんて残念……）',
    '(そんなこと言われたら、顔が赤くなっちゃう……）': '（そんなこと言われたら、顔が赤くなっちゃう……）',
    '(それでこの顔って、本当にうらやましいなぁ……)': '（それでこの顔って、本当にうらやましいなぁ……）',
}


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    src, out = argv[1], argv[2]
    if src.lower().endswith('.paf'):
        data = open(src, 'rb').read()
    else:
        data = iso_read(src, 'USRDIR/script.paf')
    txt, n = extract(data, FIXES)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(txt)
    print('行 %d -> %s' % (n, out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
