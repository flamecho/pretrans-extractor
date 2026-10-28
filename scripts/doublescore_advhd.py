# -*- coding: utf-8 -*-
"""WillPlus / AdvHD —— Double Score 系列（Marguerite×Tulip 等）变体。

在通用核心 ``scripts/advhd.py`` 之上只做两处**本系列**所需增补（不改动 advhd.py，
以免影响已交付的 Butterfly 系）：

  1. STRING + 0x71（参数 0）   资源名（FA_I06 / FA_A06 …），必须跳过而不是报错；
  2. GENERIC + 0x4B = 20       原作/通用表记 16，本系列实测 **20**。
     （取证：16 → 仅 255/273 脚本走通；20 → 272/273 走通；剩 MAINMENU 是系统脚本，
       且其中 0xAB 也只在系统脚本里出现，不参与交付。）

容器/解密与 advhd.py 完全一致：``Rio.arc`` 扩展组表 + WSC 每字节 rotl_8(c,6)。

用法（CLI）::

    python scripts/doublescore_advhd.py <RIO.ARC> <out.txt> [--only T06,T07,W03]

可复用性：同系列 Cattleya×Narcissus / Cosmos×Camellia 若同为 AdvHD + Rio.arc，
直接换 ``--arc`` 路径即可；若行走仍在中途中断，按
``scripts/ds_walkdiag.py`` 打印的首个未知 opcode 再补一条表项。
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import advhd

# ---- 本系列表项增补 --------------------------------------------------------

STRING = dict(advhd.STRING)
STRING[0x71] = 0                      # 资源名（贴图/表情），无参数、带 NUL 串
GENERIC = dict(advhd.GENERIC)
GENERIC[0x4B] = 20                    # 原作表 16，本系列实测 20 字节参数

DOUBLESTRING = dict(advhd.DOUBLESTRING)

# ---- 脚本分类（只取正文；系统/UI/回想一律排除）----------------------------

SYSTEM_SCRIPTS = {
    'ALBUM', 'ARTCHAR', 'ARTDISP', 'ARTENTRY', 'ARTMAIN', 'ARTWAIT',
    'BGMCTRL', 'BGMCTRL_CHK', 'BGMCTRL_CNT', 'BGMCTRL_NUM', 'BGMLIST',
    'BGMLIST_CLK', 'BGMLIST_INIT', 'BGMLIST_NUM', 'BGMLIST_ON', 'BGMPLAY',
    'CHK_CONGRA', 'CHK_ED', 'CHK_ENTRY', 'COLFILTER', 'CONGRA', 'CONGRAPLAY',
    'EDLIST', 'EVENTRY', 'EVEXEC', 'EVMODE', 'EVPLAY', 'EVREST', 'EVRET',
    'EXTRA', 'EXTRAENTRY', 'EXTRAPLAY', 'INITVAL', 'MAINMENU', 'NAME',
    'NOTICE', 'RESTBGM', 'SCENECHAR', 'START', 'TITLE', 'TITLECALL',
}

# 正文前缀。T01 序章 / T02 コスモス編 / T03 椿編 / W01 双花編 /
# C0x_ は EXTRA（EXTRAPLAY が再生する 27 本のショートストーリー）/
# M0x_ は CONGRAPLAY が再生する「密着２４時」おまけ。
# Marguerite×Tulip には C/M が存在しないため、本拡張は前作の出力を変えない。
STORY_RE = re.compile(r'^(?:T\d\d|W\d\d|C0\d|M0\d)_')


def is_story(name):
    return name not in SYSTEM_SCRIPTS and bool(STORY_RE.match(name))


def sort_key(name):
    """章节号 → 后缀字母 → 其余，保证 T06_01 先于 T06_01A。"""
    m = re.match(r'^([A-Z])(\d\d)_(.+)$', name)
    if not m:
        return (9, 0, name)
    series, chap, rest = m.group(1), int(m.group(2)), m.group(3)
    m2 = re.match(r'^(\d+)([A-Z]*)', rest)
    order = {'T': 0, 'W': 1, 'C': 2, 'M': 3}.get(series, 4)
    if m2:
        return (order, chap, int(m2.group(1)), m2.group(2), rest)
    # BED / GED / NED / LOED / M24 之类结尾块，排在正片之后
    tail_rank = 0 if rest.startswith('M') else 1
    return (order, chap, 990, rest, str(tail_rank))


# ---- 字节码行走 ------------------------------------------------------------

def walk(b):
    """Yield (op, [s1, s2?]) —— 文本记录自带 NUL 定界，永不失去同步。"""
    i, n = 0, len(b)
    while i < n:
        op = b[i]
        i += 1
        if op == 0x02:                                   # 选项组
            nch = struct.unpack_from('<H', b, i)[0]
            i += 2
            ch = []
            for _ in range(nch):
                i += 2
                s1 = b[i:b.index(b'\x00', i)]
                i += len(s1) + 1
                i += 3                                   # 01 XX 03 头
                op2 = b[i]
                i += 1
                s2 = b''
                if op2 in STRING:
                    i += STRING[op2]
                    s2 = b[i:b.index(b'\x00', i)]
                    i += len(s2) + 1
                elif op2 in GENERIC:
                    i += GENERIC[op2]
                elif op2 in DOUBLESTRING:
                    i += DOUBLESTRING[op2]
                    i = b.index(b'\x00', i) + 1
                    s2 = b[i:b.index(b'\x00', i)]
                    i += len(s2) + 1
                else:
                    raise ValueError('choice-target op %02X' % op2)
                ch.append((s1, s2))
            yield (op, ch)
        elif op in STRING:
            i += STRING[op]
            s = b[i:b.index(b'\x00', i)]
            i += len(s) + 1
            yield (op, [s])
        elif op in GENERIC:
            i += GENERIC[op]
        elif op in DOUBLESTRING:
            i += DOUBLESTRING[op]
            s1 = b[i:b.index(b'\x00', i)]
            i += len(s1) + 1
            s2 = b[i:b.index(b'\x00', i)]
            i += len(s2) + 1
            yield (op, [s1, s2])
        else:
            raise ValueError('op %02X @0x%X' % (op, i - 1))


# ---- 成行 ------------------------------------------------------------------

RESIDUE = re.compile(r'^[A-Za-z0-9_]+＞$')      # 脚本名残留（如 `_ver2＞` / `6_29c＞`）


def clean(t):
    """同一文本框内的软换行合并；去终止控制码与名札。"""
    t = t.replace('\r', '')
    t = t.replace('%K%P', '').replace('%K', '').replace('%P', '').replace('%O', '')
    t = re.sub(r'(?:\\n)+[ \u3000]*', '', t)             # 软换行 + 续行缩进
    t = t.strip(' \u3000\t')
    m = re.match(r'^【[^】]*】[ \u3000]*', t)              # 行首名札
    if m:
        t = t[m.end():].strip(' \u3000\t')
    if RESIDUE.match(t):                                 # 调试残串，直接丢
        return ''
    return t


def lines_of(b):
    out = []
    for op, ss in walk(b):
        if op == 0x41:                                    # 地の文
            t = clean(ss[0].decode('cp932', 'replace'))
            if t:
                out.append(t)
        elif op == 0x42:                                  # 名＋台詞（名札は捨てる）
            t = clean(ss[1].decode('cp932', 'replace'))
            if t:
                out.append(t)
        elif op == 0x02:                                  # 選択肢
            for s1, _s2 in ss:
                t = clean(s1.decode('cp932', 'replace'))
                if t:
                    out.append(t)
    return out


def extract(arc_path, prefixes=None):
    """→ (lines, per_script_counts)。prefixes 形如 ('T01','T06')，None＝全部正文脚本。"""
    d = open(arc_path, 'rb').read()
    ents = advhd.parse_arc(d)
    names = [n for n in ents if is_story(n)]
    if prefixes:
        names = [n for n in names if n.split('_')[0] in prefixes]
    names.sort(key=sort_key)
    lines, stat = [], []
    for n in names:
        _e, ln, so = ents[n]
        b = advhd.decrypt(d[so:so + ln])
        ls = lines_of(b)
        lines.extend(ls)
        stat.append((n, len(ls)))
    return lines, stat


def write_txt(path, lines):
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    arc, out = argv[1], argv[2]
    prefixes = None
    if '--only' in argv:
        prefixes = tuple(argv[argv.index('--only') + 1].split(','))
    lines, stat = extract(arc, prefixes)
    write_txt(out, lines)
    print('scripts %d  lines %d' % (len(stat), len(lines)))
    for n, c in stat:
        print('%6d  %s' % (c, n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
