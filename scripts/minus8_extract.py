# -*- coding: utf-8 -*-
"""マイナスエイト (-8)  PSP, Otomate/Rejet, ULJM06341, vndb v12155  —— 全文本提取

【容器链】
  CHD(v5/zstd) --scripts/chd_to_iso.js--> ISO9660
    -> PSP_GAME/INSDIR/INSTALL.DNS (PGD key_index=1/drm_type=1) --scripts/pgdecrypt.exe--> 内层 CRI CPK
       -> script/*  = STCM2L (Apr 22 2013) 剧本
       -> xls/0     = 選択肢テーブル（96B/记录：group[16] + 本文[64] + 场景名[16]）
       -> xls/100   = mail 主题/发信人（非正文）
       -> USRDIR/UMD.cpk 只装 voice/movie，无正文

【STCM2L 记录】
  代码段 = "CODE_START_" + 24；每 unit = [u32 size][payload]
  正文记录 = [0][L/4][1][L][cp932]（payload 偏移 12）；记录后 [0][cmd]
    cmd 0xd2 = 新框（新点击）   cmd 0xd3 = 同框续行（软换行，需拼接）
  一次点击 = 12 字节单元 `[a][cmd][n]`（a∈{0,1}）＝ 框边界（实测每框 ≤3 行、每行 ≤12 字）
  选项     = unit 内出现记录 `sel_[a-z]{3}_\\d\\d`（偏移 24）→ 该处取 xls/0 对应组的选项文本

【主角】八乙女 玲（vndb v12155, Nameable）⇒ #Name[1]=姓=八乙女, #Name[2]=名=玲

用法: python minus8_extract.py <解密后的 CPK 或 DNS 目录> <输出txt>
"""
import struct, re, os, sys, io

A4 = lambda n: (n + 3) & ~3

HERO = {'#Name[1]': '八乙女', '#Name[2]': '玲'}

RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_SEL = re.compile(r'^sel_[a-z]{3}_\d\d$')
RE_ANY_TAG = re.compile(r'#(?!Name\[)[A-Za-z_]+\[[^\]]*\]')
DROP_TEXT = {'処理開始', '処理開始\n', '処理開始\r\n', '処理開始\\n'}
RE_HANKAKU = re.compile(r'^[\uff61-\uff9f]+$')      # 单字节参数（0xA1-0xDF）被误读成半角假名
RE_PUA = re.compile(r'^[\ue000-\uf8ff]+$')          # 私用区：参数/图标槽，非正文

# 顺序：共通 900-907 → 特別 999 → 各ルート 100-870
def file_order(names):
    nums = []
    for n in names:
        b = os.path.basename(n)
        if b.isdigit():
            nums.append((int(b), n))
    nums.sort()
    first = [n for v, n in nums if 900 <= v <= 907]
    mid = [n for v, n in nums if v == 999]
    rest = [n for v, n in nums if v < 900]
    return first + mid + rest


def units(b):
    if b[:6] != b'STCM2L':
        return []
    ci = b.find(b'CODE_START_')
    if ci < 0:
        return []
    exp = struct.unpack_from('<I', b, 0x20)[0]
    i = ci + 24
    out = []
    while i + 4 <= exp:
        bs = struct.unpack_from('<I', b, i)[0]
        if bs < 4 or i + bs > len(b):
            break
        out.append(b[i + 4:i + bs])
        i += bs
    return out


def records(pay):
    """-> [(k, text)]; 记录头 [0][L/4][1][L]"""
    res = []
    n = len(pay)
    for k in range(0, n - 16 + 1, 4):
        f0, f1, f2, f3 = struct.unpack_from('<4I', pay, k)
        if f0 != 0 or f2 != 1:
            continue
        if f3 < 4 or f3 > 0x4000 or f3 % 4 or f1 != f3 // 4:
            continue
        if k + 16 + f3 > n:
            continue
        raw = pay[k + 16:k + 16 + f3].rstrip(b'\x00')
        if not raw or A4(len(raw) + 1) != f3:
            continue
        try:
            s = raw.decode('cp932')
        except Exception:
            continue
        res.append((k, s))
    return res


def cmd_after(pay, k, f3):
    p = k + 16 + f3
    if p + 8 > len(pay):
        return None
    return struct.unpack_from('<I', pay, p + 4)[0] & 0xffff


def load_choices(cpk_path):
    """xls/0 -> {group: [option texts in order]}"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
    import cpk as cpkmod
    c = cpkmod.CPK(cpk_path)
    ent = [e for e in c.entries if e['name'] == 'xls/0']
    if not ent:
        return {}
    b = c.raw(ent[0])
    n = struct.unpack_from('<I', b, 0)[0]
    RE = re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc])+')
    out = {}
    for i in range(n):
        r = b[8 + i * 96: 8 + (i + 1) * 96]
        g = r[:16].split(b'\x00')[0].decode('latin1')
        if not RE_SEL.match(g):
            continue
        txt = ''.join(m.group().decode('cp932') for m in RE.finditer(r[16:80]))
        txt = RE_ANY_TAG.sub('', txt).strip()
        if txt:
            out.setdefault(g, []).append(txt)
    return out


def clean(s):
    s = s.replace('\r', '').replace('\n', '')
    for k, v in HERO.items():
        s = s.replace(k, v)
    s = RE_ANY_TAG.sub('', s)
    return s.strip()


def is_noise(s):
    """非正文判定：调试串 / 单字节参数（半角假名）/ 私用区槽 / 纯 ASCII"""
    if not s or s in DROP_TEXT or s.startswith('処理開始'):
        return True
    if s.isascii() or RE_HANKAKU.match(s) or RE_PUA.match(s):
        return True
    return False


def extract(src, dst, prov=False, cpkpath=None):
    if cpkpath is None:
        for cand in ('_src_psp8/INSTALL.DNS.decrypt', 'INSTALL.DNS.decrypt'):
            if os.path.exists(cand):
                cpkpath = cand
                break
    choices = load_choices(cpkpath)
    # script 目录
    sdir = src if os.path.isdir(src) else None
    if sdir is None:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
        import cpk as cpkmod
        c = cpkmod.CPK(src)
        c.extract(os.path.splitext(src)[0] + '_files', pred=lambda nm: nm.startswith('script/'))
        sdir = os.path.join(os.path.splitext(src)[0] + '_files', 'script')
    files = file_order([os.path.join(sdir, f) for f in os.listdir(sdir)])

    lines = []
    stats = {}
    for path in files:
        fn = os.path.basename(path)
        b = open(path, 'rb').read()
        us = units(b)
        if not us:
            continue
        buf = []
        nline = nopt = 0

        def flush():
            nonlocal buf, nline
            if not buf:
                return
            s = clean(''.join(buf))
            buf = []
            if is_noise(s):
                return
            lines.append(s)
            nline += 1

        for pay in us:
            if len(pay) == 12 and pay[0] in (0, 1):
                flush()
                continue
            recs = records(pay)
            for k, s in recs:
                if k != 12:
                    continue
                if not s or s.isascii():
                    continue
                s = s.replace('\r', '').replace('\n', '')
                if s in DROP_TEXT:
                    continue
                buf.append(s)
            # 选项：unit 内出现 sel_ 组名
            grp = None
            for k, s in recs:
                if RE_SEL.match(s):
                    grp = s
                    break
            if grp and grp in choices:
                flush()
                for t in choices[grp]:
                    lines.append(t)
                    nopt += 1
            elif grp:
                print('  [warn] 未知选项组', fn, grp)
        flush()
        stats[fn] = (nline, nopt)

    txt = '\n'.join(lines) + '\n'
    with io.open(dst, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write(txt)
    print('lines', len(lines), 'bytes', len(txt.encode('utf-8')))
    if prov:
        for k, v in stats.items():
            print('  %-6s lines=%-5d opt=%d' % (k, v[0], v[1]))
    return len(lines)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opt = [a for a in sys.argv[1:] if a.startswith('--cpk=')]
    src, dst = args[0], args[1]
    extract(src, dst, '--prov' in sys.argv, opt[0].split('=', 1)[1] if opt else None)
