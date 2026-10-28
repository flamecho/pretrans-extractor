# -*- coding: utf-8 -*-
"""Double Score ～Cattleya×Narcissus～ 专用入口。

复用 scripts/doublescore_advhd.py（不改动它），仅做本作实测差异：

  * GENERIC 0x66 = **22**（同系列 Marguerite×Tulip 为 18；本作取 18 时
    W02_02C 在 0x1028 失步于 op 00；取 22 时 303/303 脚本精确走到字节末）；
  * 脚本分组与顺序**自包含**（不依赖共享解析器的 STORY_RE，因其被并行作业单元
    扩展为含 C0x/M0x）：正文 T01→T04→T05→W02；おまけ C04/C05 按 EXTRAPLAY
    菜单序；クリア特典 M24 按 CONGRAPLAY 序。

用法：python scripts/dscatt_extract.py <RIO.ARC> <out.txt>
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import advhd
import doublescore_advhd as D

_G = dict(D.GENERIC)
_G[0x66] = 22
D.GENERIC = _G

MAIN_RE = re.compile(r'^(?:T01|T04|T05|W02)_')

# EXTRAPLAY 内的脚本顺序（おまけ短編 24 篇）
OMAKE_ORDER = [
    'C04_14TO', 'C04_47TO', 'C04_49TO', 'C04_47KM', 'C04_07MY', 'C04_45MY',
    'C04_GEDY', 'C04_32SK', 'C04_36SK', 'C04_48SK', 'C04_09TG', 'C04_45TG',
    'C04_GEDT', 'C04_28AM', 'C04_GEDM', 'C05_10TC', 'C05_29TC', 'C05_48TC',
    'C05_22AK', 'C05_GEKM', 'C05_55SN', 'C05_38MK', 'C05_50AM', 'C05_LEMK',
]
# CONGRAPLAY 内的顺序（クリア特典 3 篇）
CONGRA_ORDER = ['M24_SA', 'M24_SE', 'M24_SR']


def main_key(name):
    """T01_00 → (0,1,0,...)；同章内 01 < 01A < 01AA，GED/NED 等结尾块后置。"""
    m = re.match(r'^([TW])(\d\d)_(.+)$', name)
    series, chap, rest = m.group(1), int(m.group(2)), m.group(3)
    m2 = re.match(r'^(\d+)([A-Z]*)', rest)
    order = {'T': 0, 'W': 1}[series]
    if m2:
        return (order, chap, int(m2.group(1)), m2.group(2), rest)
    return (order, chap, 990, rest, '')


def order(names):
    s = set(names)
    main = sorted([n for n in s if MAIN_RE.match(n)], key=main_key)
    tail = [n for n in OMAKE_ORDER + CONGRA_ORDER if n in s]
    return main + tail


def main(argv):
    arc, out = argv[1], argv[2]
    d = open(arc, 'rb').read()
    ents = advhd.parse_arc(d)
    names = order(list(ents))
    lines, stat = [], []
    total = 0
    for n in names:
        _e, ln, so = ents[n]
        b = advhd.decrypt(d[so:so + ln])
        ls = D.lines_of(b)
        lines.extend(ls)
        stat.append((n, len(ls), ln))
        total += ln
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('scripts %d  lines %d  bytes %d' % (len(stat), len(lines), total))
    for n, c, ln in stat:
        print('%6d  %7d  %s' % (c, ln, n))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
