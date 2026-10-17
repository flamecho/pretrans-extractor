# -*- coding: utf-8 -*-
"""
Lucian Bee's: Resurrection Supernova (PSP, 2010, HuneX IKA SEQ SYSTEM v3.4)
==========================================================================
链路：ISO9660 → PSP_GAME/USRDIR/data/GAMEDT.afs (CRI AFS, 8 成员)
      → AFS[2] = SCRIPT (HFU2, 196 块) → 每块 UFFA+LZSS 解压 → IKA 字节码
      → 文本记录 `26 <cmd> 24 <nargs> 5C <L> <SJIS L-4> 00 00`

用法：
  python scripts/lucian_extract.py <GAMEDT.afs 路径> <输出 txt 路径>

记录语义（本作实测，16 位命令表见报告）：
  0x3e nargs1 名札（丢）      0x3c nargs1 台詞      0x44 nargs1 地の文
  0x41 nargs3 選択肢          0x9f nargs1 地名字幕   0x9e nargs2 時刻字幕
  0xcf nargs2 時期字幕（"6 months ago"）
宏：＠=名(アンナ)  ＄=姓(ヒイラギ)  @n=框内软换行  @k/@w/@b/@g=强调标记
用語辞典：块 1（WORD___001..545），`23 <L> <name> <tag>` 后紧跟两条 5C 串
"""
import struct
import sys

CMD_TEXT = 0x3C
CMD_NAME = 0x3E
CMD_JI = 0x44
CMD_SEL = 0x41
CMD_PLACE = 0x9F
CMD_TIME = 0x9E
CMD_DATE = 0xCF
KEEP = (CMD_TEXT, CMD_JI, CMD_SEL, CMD_PLACE, CMD_TIME, CMD_DATE)
SKIP_BLOCKS = {0, 1}       # 0＝测试/样例块（含「テスト」×2，正文另有副本）；1＝用語辞典专用块（另行解析）
NAME_MACRO = {'＠': 'アンナ', '＄': 'ヒイラギ'}
CTRL_STRIP = ('@k', '@w', '@b', '@g', '@y')

# 开发占位串（ステルス選択肢每组的第 4 槽恒为 'ダミー選択肢'，＝未使用的占位，不上屏）
DROP_EXACT = {'ダミー選択肢'}

# 源字节本身缺收束符的三行（整行定值表；勿写成正则泛修）
FIX = {
    'あら……この本って、え～っと『あぶない女きょう……、': 'あら……この本って、え～っと『あぶない女きょう……、』',
    '（……Ａの肌が少しでも傷ついたら、\u3000アタシが討ってやる……！': '（……Ａの肌が少しでも傷ついたら、\u3000アタシが討ってやる……！）',
    '（ああっ！？\u3000どうしようか考えてるうちに、\u3000焼却炉の中に！？': '（ああっ！？\u3000どうしようか考えてるうちに、\u3000焼却炉の中に！？）',
}


def afs_members(path):
    with open(path, 'rb') as f:
        h = f.read(8)
        assert h[:4] == b'AFS\x00', h[:4]
        cnt = struct.unpack('<I', h[4:8])[0]
        out = []
        for _ in range(cnt):
            o, s = struct.unpack('<II', f.read(8))
            out.append((o, s))
    return out


def lzss(src, out_size):
    d = bytearray(0x1010)
    dp = 0xFEE
    out = bytearray()
    i = 0
    flags = 0
    n = len(src)
    while len(out) < out_size:
        flags >>= 1
        if (flags & 0x100) == 0:
            if i >= n:
                break
            flags = src[i] | 0xFF00
            i += 1
        if flags & 1:
            if i >= n:
                break
            c = src[i]
            i += 1
            out.append(c)
            d[dp] = c
            dp = (dp + 1) & 0xFFF
        else:
            if i + 1 >= n:
                break
            lo = src[i]
            hi = src[i + 1]
            i += 2
            off = lo | ((hi & 0xF0) << 4)
            ln = (hi & 0x0F) + 3
            for k in range(ln):
                c = d[(off + k) & 0xFFF]
                out.append(c)
                d[dp] = c
                dp = (dp + 1) & 0xFFF
                if len(out) >= out_size:
                    break
    return bytes(out)


def hfu2_blocks(data):
    assert data[:4] == b'HFU2', data[:4]
    cnt, X = struct.unpack('<II', data[4:12])
    blks = []
    for i in range(cnt):
        off, size, size2 = struct.unpack('<III', data[24 + i * 16 - 8:24 + i * 16 - 8 + 12])
        blks.append((X + off, size, size2))
    return cnt, X, blks


def member(path, idx):
    ents = afs_members(path)
    o, s = ents[idx]
    with open(path, 'rb') as f:
        f.seek(o)
        return f.read(s)


def script_blocks(path, idx=2):
    data = member(path, idx)
    cnt, X, blks = hfu2_blocks(data)
    out = []
    for bo, bs, b2 in blks:
        blk = data[bo:bo + bs]
        if blk[:4] == b'UFFA':
            plen, osz = struct.unpack('<II', blk[4:12])
            out.append(lzss(blk[16:16 + plen], osz))
        else:
            out.append(blk)
    return out


def scan_records(dec):
    """按位置顺序返回 [(pos, cmd, nargs, text)]，仅含白名单命令的合法 5C 记录"""
    n = len(dec)
    recs = []
    i = 0
    while True:
        i = dec.find(b'\x26', i + 1)
        if i < 0 or i + 6 > n:
            break
        if dec[i + 2] != 0x24 or dec[i + 4] != 0x5C:
            continue
        cmd = dec[i + 1]
        if cmd not in (CMD_TEXT, CMD_NAME, CMD_JI, CMD_SEL, CMD_PLACE, CMD_TIME, CMD_DATE):
            continue
        L = dec[i + 5]
        if L < 4 or i + 4 + L > n:
            continue
        if dec[i + 4 + L - 2:i + 4 + L] != b'\x00\x00':
            continue
        recs.append((i, cmd, dec[i + 3], dec[i + 6:i + 2 + L].decode('cp932', 'replace')))
    return recs


def clean(s):
    for c in CTRL_STRIP:
        s = s.replace(c, '')
    s = s.replace('@n', '')          # 框内软换行 → 合并（一次点击＝一行）
    for k, v in NAME_MACRO.items():
        s = s.replace(k, v)
    return s.strip('\u3000 \t')


def word_dict(block):
    """用語辞典：23 <L> WORD___NNN <tag> + 5C(見出し語) + 5C(解説)"""
    dec = block
    n = len(dec)
    out = []
    stat_names = []
    i = 0
    while True:
        i = dec.find(b'\x23\x0bWORD___', i + 1)
        if i < 0:
            break
        name = dec[i + 2:i + 12].decode('ascii')
        p = i + 2 + 11              # 越过 label(L=0x0b: 10B 名 + 1B tag)
        vals = []
        for _ in range(2):
            if p + 6 > n or dec[p] != 0x5C:
                break
            L = dec[p + 1]
            if L < 4 or p + L > n:
                break
            vals.append(dec[p + 2:p + L - 2].decode('cp932', 'replace'))
            p += L
        if len(vals) == 2:
            out.append((name, vals[0], vals[1]))
    return out


def label_before(dec, R):
    """`23 <L> <name L-1> <tag>` 记录结束恰在 R ⇒ 返回标签名（标签串载体）"""
    for L in range(4, 40):
        p = R - 2 - L
        if p < 0:
            break
        if dec[p] == 0x23 and dec[p + 1] == L:
            nm = dec[p + 2:R - 1]
            if all(32 <= c < 127 for c in nm):
                return nm.decode('ascii')
    return None


def _rec_at(dec, p):
    """p 处若是合法 5C 记录 ⇒ 返回 (text, end)"""
    n = len(dec)
    if p + 6 > n or dec[p] != 0x5C:
        return None
    L = dec[p + 1]
    if L < 4 or p + L > n:
        return None
    if dec[p + L - 2:p + L] != b'\x00\x00':
        return None
    return dec[p + 2:p + L - 2].decode('cp932', 'replace'), p + L


def walk_block(dec):
    """按字节位置顺序产出 (kind, label, text)；kind ∈ {'flow','labeled'}"""
    n = len(dec)
    out = []
    stat_names = []
    i = 0
    while i < n - 6:
        if dec[i] == 0x26 and dec[i + 2] == 0x24:
            cmd = dec[i + 1]
            if cmd in (CMD_TEXT, CMD_NAME, CMD_JI, CMD_SEL, CMD_PLACE, CMD_TIME, CMD_DATE):
                r = _rec_at(dec, i + 4)
                if r:
                    if cmd == CMD_NAME:      # 名札：丢弃（§0 不加说话人前缀），仅用于核对
                        stat_names.append(r[0])
                    else:
                        out.append(('flow', cmd, r[0]))
                    end = r[1]
                    # 0x9e（時刻字幕）带第 2 条串＝场景结束时刻
                    while cmd == CMD_TIME:
                        r2 = _rec_at(dec, end)
                        if not r2:
                            break
                        out.append(('flow2', cmd, r2[0]))
                        end = r2[1]
                    i = end
                    continue
        if dec[i] == 0x5C:
            r = _rec_at(dec, i)
            if r:
                lb = label_before(dec, i)
                if lb:
                    out.append(('labeled', lb, r[0]))
                    i = r[1]
                    continue
        i += 1
    return out, len(stat_names)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    afs, outp = sys.argv[1], sys.argv[2]
    blocks = script_blocks(afs, 2)
    main_lines = []
    stat = {}
    for bi, dec in enumerate(blocks):
        if bi in SKIP_BLOCKS:
            continue
        recs, nn = walk_block(dec)
        stat[0x3e] = stat.get(0x3e, 0) + nn
        for kind, tag, text in recs:
            key = tag if kind != 'labeled' else 'label'
            stat[key] = stat.get(key, 0) + 1
            t = clean(text)
            t = FIX.get(t, t)
            if t and t not in DROP_EXACT:
                main_lines.append(t)
    wd = word_dict(blocks[1])
    with open(outp, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(main_lines))
        f.write('\n')
        for name, head, body in wd:
            f.write('【%s】%s\n' % (clean(head), clean(body)))
    print('正文行数', len(main_lines), '用語辞典', len(wd), '合计', len(main_lines) + len(wd))
    print('命令统计', {hex(k) if isinstance(k, int) else k: v for k, v in sorted(stat.items(), key=str)})
    return 0


if __name__ == '__main__':
    sys.exit(main())
