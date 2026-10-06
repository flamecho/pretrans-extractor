# -*- coding: utf-8 -*-
"""从 BOOT.BIN 读取 16x16「呼び名」称呼矩阵
指针表位于文件偏移 0x17C9AC（VA 0x17C958），16 行 x 16 列，
行/列顺序 = CHR 人物表 00..15；指针为 VA（= 文件偏移 - 0x54）。
"""
import struct

ELF = open('iso/SYSDIR/BOOT.BIN', 'rb').read()
BASE = 0x17C9AC
CH = ['高倉花梨', '源\u3000頼忠', '平\u3000勝真', 'イサト', '彰紋', '藤原幸鷹', '翡翠',
      '源\u3000泉水', '安倍泰継', 'アクラム', 'シリン', '和仁', '源\u3000時朝',
      '平\u3000千歳', '藤原\u3000紫', '藤原深苑']

def _s(i):
    va = struct.unpack_from('<I', ELF, BASE + 4 * i)[0]
    if not (0x100000 < va < 0x200000):
        return ''
    fo = va + 0x54
    e = ELF.find(b'\x00', fo)
    if e < 0 or e - fo > 40:
        return ''
    try:
        return ELF[fo:e].decode('cp932')
    except Exception:
        return ''

MATRIX = [[_s(r * 16 + c) for c in range(16)] for r in range(16)]
NAME_ROW = {n: i for i, n in enumerate(CH)}

def appellation(speaker, target):
    """话者 speaker 对 target 的称呼；查不到返回 ''"""
    r = NAME_ROW.get(speaker)
    c = NAME_ROW.get(target)
    if r is None or c is None:
        return ''
    return MATRIX[r][c]

if __name__ == '__main__':
    print('      ' + ' | '.join('%-6s' % c[:4] for c in CH))
    for r in range(16):
        print('%-5s ' % CH[r][:4], ' | '.join('%-6s' % x for x in MATRIX[r]))
    print()
    print('紫→深苑 =', appellation('藤原\u3000紫', '藤原深苑'))
    print('花梨→頼忠 =', appellation('高倉花梨', '源\u3000頼忠'))
    print('深苑→紫 =', appellation('藤原深苑', '藤原\u3000紫'))
