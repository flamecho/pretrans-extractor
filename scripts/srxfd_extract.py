#!/usr/bin/env python3
"""srxfd_extract.py —— スカーレッドライダーゼクス STARDUST LOVERS (PSP)
Rejet ADV `PACK` 容器 ＋ `YOX` 字节码脚本（明文 CP932 串池）。

链路：image.bin(PACK) → USRDIR 条目 → *.SCE(YOX) → 串池 → 一次点击 = 一行
用法：
  python scripts/srxfd_extract.py unpack <image.bin> <outdir>
  python scripts/srxfd_extract.py text   <outdir> <out.txt>
"""
import os
import re
import struct
import sys

# ---------------------------------------------------------------- 容器
def unpack(path, outdir):
    f = open(path, 'rb')
    head = f.read(16)
    assert head[:4] == b'PACK', head[:8]
    cnt = struct.unpack_from('<I', head, 4)[0]
    hdr = head + f.read(0x0c + cnt * 0x90 - 16)
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for i in range(cnt):
        o = 0x0c + i * 0x90
        off, size = struct.unpack_from('<II', hdr, o + 8)
        name = hdr[o + 0x10:o + 0x90].split(b'\0')[0].decode('cp932')
        p = os.path.join(outdir, name.replace('/', '_'))
        f.seek(off)
        with open(p, 'wb') as g:
            g.write(f.read(size))
        n += 1
    print('unpacked', n, 'files ->', outdir)


# ---------------------------------------------------------------- YOX 串池
def _valid_cp932(b):
    """整串能否按 CP932（含半角片假名）线性解完。"""
    i, n = 0, len(b)
    while i < n:
        c = b[i]
        if 0x20 <= c <= 0x7e or 0xa1 <= c <= 0xdf:
            i += 1
        elif 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef:
            if i + 1 >= n:
                return False
            t = b[i + 1]
            if not (0x40 <= t <= 0xfc and t != 0x7f):
                return False
            i += 2
        else:
            return False
    return True


def pool_of(d):
    """YOX 文件尾部是连续 NUL 分隔的明文串池 ⇒ 取「到文件尾为止的最长合法后缀」。"""
    segs = d.split(b'\0')
    k = len(segs)
    while k > 0 and (_valid_cp932(segs[k - 1]) or not segs[k - 1]):
        k -= 1
    return [s for s in segs[k:]]


# 行内演出码：@L 软换行 / @I 等待按键 / @P 换页清框 / @S 颜色切换 / @Y#### 色号 /
# @Vs00 姓 / @Vs01 名 / @K 等「一声」演出码（无可读文本）
RE_CODE = re.compile(r'@[A-Za-z][0-9A-Za-z]*')
PROTAG_FAMILY = '麻黄'
PROTAG_GIVEN = 'アキラ'


def clean(t):
    t = t.replace('\r', '').replace('\n', '')
    t = t.replace('@Vs00', PROTAG_FAMILY).replace('@Vs01', PROTAG_GIVEN)
    t = t.replace('@L', '')            # 框内软换行 ⇒ 合并
    t = RE_CODE.sub('', t)             # 其余演出码剥净
    t = t.replace('@', '')
    t = ''.join(ch for ch in t if ch >= ' ' and ch != '\x7f')
    return t.strip()


# ---------------------------------------------------------------- 成行
# 正文脚本（按剧情顺序）：SRXFD_*（去掉 SR=战斗 / TEST / DEMO=010 的重复副本）+ TR_01_CM_*（剧本对话）
STORY = [
    'SRXFD_01_010', 'SRXFD_01_020', 'SRXFD_01_020_HIJIRI', 'SRXFD_01_020_HIRO',
    'SRXFD_01_020_KAZUKI', 'SRXFD_01_020_TAKUTO', 'SRXFD_01_020_YOUSUKE',
    'SRXFD_01_020_YUJI', 'SRXFD_01_030', 'SRXFD_01_040', 'SRXFD_01_040_HIJIRI',
    'SRXFD_01_040_HIRO', 'SRXFD_01_040_KAZUKI', 'SRXFD_01_040_SOICHIRO',
    'SRXFD_01_040_TAKUTO', 'SRXFD_01_040_YOUSUKE', 'SRXFD_01_040_YUJI',
    'SRXFD_02_010', 'SRXFD_02_020', 'SRXFD_02_020_GOMAKASHI',
    'SRXFD_02_020_JIKAN_AMAKASU', 'SRXFD_02_020_JIKAN_OTHER',
    'SRXFD_02_020_MIMAWARI', 'SRXFD_02_020_YOFUKASHI', 'SRXFD_02_030',
    'SRXFD_02_040', 'SRXFD_02_050', 'SRXFD_03_010', 'SRXFD_03_020',
    'SRXFD_03_020_GRUNBACH', 'SRXFD_03_020_HIJIRI', 'SRXFD_03_020_HIRO',
    'SRXFD_03_020_KAZUKI', 'SRXFD_03_020_SOICHIRO', 'SRXFD_03_020_SUBSTANCE',
    'SRXFD_03_020_TAKT', 'SRXFD_03_020_YOSUKE', 'SRXFD_03_020_YUJI',
    'SRXFD_03_030_HIJIRI', 'SRXFD_03_030_HIRO', 'SRXFD_03_030_KAZUKI',
    'SRXFD_03_030_SOICHIRO', 'SRXFD_03_030_SUBSTANCE', 'SRXFD_03_030_TAKT',
    'SRXFD_03_030_YOSUKE', 'SRXFD_03_030_YUJI', 'SRXFD_03_040',
    'TR_01_CM_000', 'TR_01_CM_009', 'TR_01_CM_010_C', 'TR_01_CM_010_HIRO',
    'TR_01_CM_010_KAZUKI', 'TR_01_CM_010_TAKUTO', 'TR_01_CM_010_YOUSUKE',
    'TR_01_CM_010_YUJI', 'TR_01_CM_Z_01', 'TR_01_CM_Z_02', 'TR_01_CM_Z_99',
    'SRXFD_ED_01', 'SRXFD_ED_02', 'SRXFD_ED_03', 'SRXFD_ED_04', 'SRXFD_ED_05',
    'SRXFD_ED_06', 'SRXFD_ED_07', 'SRXFD_ED_08', 'SRXFD_ED_09', 'SRXFD_ED_10',
]


def file_text(path):
    d = open(path, 'rb').read()
    if d[:3] != b'YOX':
        return []
    out = []
    for s in pool_of(d):
        if b'@I' not in s:
            continue
        t = clean(s.decode('cp932', 'replace'))
        if t:
            out.append(t)
    return out


def build_text(imgdir, out):
    lines = []
    for name in STORY:
        p = os.path.join(imgdir, 'SCRIPT_GAME_%s.SCE' % name)
        if not os.path.exists(p):
            print('MISSING', p)
            continue
        got = file_text(p)
        print('%-26s %5d' % (name, len(got)))
        lines.extend(got)
    # 选项：SELECT_SPECIAL_LV（诱い／相談 各 3 択，@L 分行；同文去重）
    p = os.path.join(imgdir, 'SCRIPT_LIB_SELECT_SPECIAL_LV.SCE')
    if os.path.exists(p):
        seen = []
        for s in pool_of(open(p, 'rb').read()):
            if b'@I' not in s:
                continue
            for part in re.split('@L', s.decode('cp932', 'replace')):
                t = clean(part)
                if t and t not in seen:
                    seen.append(t)
        print('%-26s %5d' % ('SELECT_SPECIAL_LV', len(seen)))
        lines.extend(seen)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('total lines', len(lines))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'unpack':
        unpack(sys.argv[2], sys.argv[3])
    elif cmd == 'text':
        build_text(sys.argv[2], sys.argv[3])
