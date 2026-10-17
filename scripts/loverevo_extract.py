#!/usr/bin/env python3
"""乙女的恋革命★ラブレボ!! Portable (PSP) 全文本提取

链路：
  ISO9660 → res/script/{scradr,scrbin}.mrg  （mrgd00 容器）
         → 成员 MZX0 解压 → 全字节 XOR 0xFF
         → 脚本 = `_CMD(args);` 文本，正文在 `_ZM<id>(<字形码流>)`
  ★ 字形码：2 字节 / 1 字，`idx = (b0-0xA0)*60 + (b1-0x3F)`
     idx 0..134 = 记号/全角英数（HuneX 标准字序）
     idx 136..218 = 平假名（JIS 区 0x24）
     idx 219..304 = 片假名（JIS 区 0x25）
     idx >= 305  = 汉字（JIS 区 0x30 起，行内 94 进）
  字符来源表 res/ccc/jis2ucs.bin（JIS→UCS2，0x10000 项）。
  ASCII 单字节：`^`=框内软换行，`$2`..`$0`=强调（去标记留文字），`$n`=名字宏。
"""
import os
import re
import sys
from io import BytesIO
from struct import unpack_from

NAME_SURNAME = '桜川'
NAME_GIVEN = 'ヒトミ'

# 源笔误：3 处整框漏收尾「」（脚本内该 _ZM 串确实缺 」字节，下一框已是他人台词）
PATCH = {
    '「先生が、ヒトミちゃんではダメ、っていうようなことを言っているのなら話は別だけど……': '「先生が、ヒトミちゃんではダメ、っていうようなことを言っているのなら話は別だけど……」',
    '「あれ、ちょっとほっそりしてきたかな？': '「あれ、ちょっとほっそりしてきたかな？」',
}

# HuneX 标准字序前 135 项（记号＋全角英数）
SYMBOLS = (
    " 　、。，．・：；？！゛ヽヾゝ"
    "ゞ〃々〆〇ー―‐～∥｜…‥“"
    "”≪≫《》＜＞＿＋－×÷＝±"
    "αβγ（）■〈〉「」『』【】"
    "￥＄％＃＆＊＠※○●◇◆□▲"
    "♪★０１２３４５６７８９ＡＢ"
    "ＣＤＥＦＧＨＩＪＫＬＭＮＯＰ"
    "ＱＲＳＴＵＶＷＸＹＺａｂｃｄ"
    "ｅｆｇｈｉｊｋｌｍｎｏｐｑｒ"
    "ｓｔｕｖｗｘｙｚ"
)

def mzx0_decompress(buf, exlen):
    f = BytesIO(buf)
    out = BytesIO()
    ring = [b'\xff\xff'] * 64
    wpos = 0
    clear = 0
    last = b'\xff\xff'
    maxp = len(buf)
    while out.tell() < exlen:
        if f.tell() >= maxp:
            break
        if clear <= 0:
            clear = 0x1000
        flags = f.read(1)[0]
        clear -= 1 if (flags & 3) == 2 else flags // 4 + 1
        if flags & 3 == 0:
            out.write(last * (flags // 4 + 1))
        elif flags & 3 == 1:
            k = 2 * (f.read(1)[0] + 1)
            for _ in range(flags // 4 + 1):
                out.seek(-k, 1)
                last = out.read(2)
                out.seek(0, 2)
                out.write(last)
        elif flags & 3 == 2:
            last = ring[flags // 4]
            out.write(last)
        else:
            for _ in range(flags // 4 + 1):
                last = bytes(b ^ 0xFF for b in f.read(2))
                ring[wpos] = last
                wpos = (wpos + 1) % 64
                out.write(last)
    return out.getvalue()


def unpack_mrg(path):
    d = open(path, 'rb').read()
    assert d[:6] == b'mrgd00', path
    n = unpack_from('<H', d, 6)[0]
    ents = []
    for i in range(n):
        so, of, su, sz = unpack_from('<HHHH', d, 8 + i * 8)
        ents.append(8 + n * 8 + so * 0x800 + of)
    ents.sort()
    out = []
    for i, off in enumerate(ents):
        end = ents[i + 1] if i + 1 < len(ents) else len(d)
        blob = d[off:end]
        if blob[:4] == b'MZX0':
            raw = mzx0_decompress(blob[8:], unpack_from('<I', blob, 4)[0])
        else:
            raw = blob
        out.append(bytes(b ^ 0xFF for b in raw))
    return out


class CharTable:
    def __init__(self, jis2ucs_path):
        self.u = unpack_from('<65536H', open(jis2ucs_path, 'rb').read(), 0)
        hira = [chr(self.u[0x2421 + k]) for k in range(0x2473 - 0x2421 + 1)]
        kata = [chr(self.u[0x2521 + k]) for k in range(0x2576 - 0x2521 + 1)]
        self.tbl = list(SYMBOLS[:135]) + ['\u3000'] + hira + kata
        self.kanji_base = 305

    def char(self, idx):
        if 0 <= idx < len(self.tbl):
            return self.tbl[idx]
        n = idx - self.kanji_base
        j = ((0x30 + n // 94) << 8) | (0x21 + n % 94)
        v = self.u[j] if 0x3021 <= j <= 0x74FF else 0
        return chr(v) if v else ''


def decode_text(seg, ct):
    out = []
    p = 0
    n = len(seg)
    while p < n:
        b = seg[p]
        if b >= 0xA0 and p + 1 < n:
            out.append(ct.char((b - 0xA0) * 60 + (seg[p + 1] - 0x3F)))
            p += 2
        elif b == 0x5E:          # ^ 框内软换行
            p += 1
        elif b == 0x24 and p + 1 < n and 0x30 <= seg[p + 1] <= 0x39:
            p += 2               # $n 名字/强调标记（$2 开 $0 关）
        elif 0x20 <= b < 0x7F:
            out.append(chr(b))
            p += 1
        else:
            p += 1
    s = ''.join(out)
    s = s.replace('＊Ｂ', NAME_SURNAME).replace('＊Ｃ', NAME_GIVEN)
    s = s.replace('＊Ａ', NAME_SURNAME)
    s = s.strip()
    return PATCH.get(s, s)


def collect(base, ct):
    adr = unpack_mrg(os.path.join(base, 'scradr.mrg'))
    bn = unpack_mrg(os.path.join(base, 'scrbin.mrg'))
    rows = []
    for mi in range(min(len(adr), len(bn))):
        araw = adr[mi].decode('cp932', 'replace')
        braw = bn[mi]
        ents = []
        for line in araw.split('\r\n'):
            parts = line.split()
            if len(parts) >= 2 and ',' in parts[1]:
                ents.append((parts[0], int(parts[1].split(',')[1], 16)))
        ents.sort(key=lambda x: x[1])
        for i, (name, off) in enumerate(ents):
            end = ents[i + 1][1] if i + 1 < len(ents) else len(braw)
            seg = braw[off:end]
            p = 0
            while True:
                j = seg.find(b'_ZM', p)
                if j < 0:
                    break
                k = seg.find(b'(', j)
                e = seg.find(b');', j)
                if k < 0 or e < 0:
                    break
                txt = decode_text(seg[k + 1:e], ct)
                if txt:
                    rows.append((name, txt))
                p = e + 2
    return rows


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else r'..\_work_loverevo\PSP_GAME\USRDIR\res\script'
    ccc = os.path.join(os.path.dirname(base), 'ccc', 'jis2ucs.bin')
    out = sys.argv[2] if len(sys.argv) > 2 else r'..\提取结果\[PSP-JP]乙女的恋革命★ラブレボ!!Portable_全文本.txt'
    ct = CharTable(ccc)
    rows = collect(base, ct)
    print('lines', len(rows))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for _, t in rows:
            f.write(t + '\n')
    print('written', out)


if __name__ == '__main__':
    main()
