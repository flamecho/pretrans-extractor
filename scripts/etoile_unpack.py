# -*- coding: utf-8 -*-
"""
アンジェリーク エトワール (PS2, SLPM_657.15, 2004 Koei/Ruby Party) 归档解包器

已确认链路（2026-10-18）:
  ISO9660 -> DATA00..04.HD + DATAxx.BIN
    .HD  = u32 LE 尺寸表（逐条）
    .BIN = 条目顺序拼接，每条按 2048 对齐（校验 sum(align2048) == len(BIN)）
  条目 #0 通常是 FILENAME.LST（cp932, CRLF）=> 索引 i 即文件名
  条目本身多为 PACK 容器：
    'PACK' + u32 nameLen + name[nameLen] + u32 A + u32 B + u32 dataOff + u32 dataSize
    A = 头部长度, B = 表长度, dataOff = A + B
    表区两种变体:
      V1 (DATA01 常见): 记录 = name[48](cp932) + u32 off + u32 storedSize + u32 decompSize + u32 step
      V2 (DATA02/03 常见): 记录 = name[64]（游戏自研 2 字节字符码，非 cp932）
  成员数据 = 压缩/加密流（**未攻克**，见解析报告 §5）

用法:
  python etoile_unpack.py <DATADIR> --manifest out.tsv [--dump DIR] [--only PREFIX]
"""
import os, sys, struct, argparse

SECTOR = 2048

def load_pair(base):
    hd = open(base + '.HD', 'rb').read()
    sizes = struct.unpack('<%dI' % (len(hd) // 4), hd)
    data = open(base + '.BIN', 'rb').read()
    ents, o = [], 0
    for s in sizes:
        ents.append((o, s))
        o += (s + SECTOR - 1) // SECTOR * SECTOR
    if o != len(data):
        sys.stderr.write('WARN %s: 表尾对齐和不等于 BIN 大小 (%d vs %d)\n' % (base, o, len(data)))
    return sizes, ents, data

def read_names(data, sizes):
    """仅当条目 #0 是 FILENAME.LST 时才认名表（DATA03 不是，返回空）"""
    if not sizes:
        return []
    head = data[:16]
    if not head.startswith(b'FILENAME.LST'):
        return []
    t = data[:sizes[0]].decode('cp932', 'replace')
    return [x for x in t.split('\r\n') if x]

def safe_name(s):
    return ''.join(ch if 0x20 <= ord(ch) < 0x7f or ch in '　' else '_' for ch in s)[:96]

def parse_pack(b):
    """返回 (headerFields, members)。members = [(name, off, stored, decomp, step)]
    解析失败返回 (None, [])"""
    if b[:4] != b'PACK' or len(b) < 0x30:
        return None, []
    nl = struct.unpack('<I', b[4:8])[0]
    if 8 + nl + 16 + 16 > len(b):
        return None, []
    hdrname = b[8:8 + nl]
    pos = 8 + nl
    A, B, doff, dsize = struct.unpack('<4I', b[pos:pos + 16])
    pos += 16
    c1, c2, recsize, _z = struct.unpack('<4I', b[pos:pos + 16])
    c1 = c2          # 计数在第二个字段（第一个恒为 0/1）
    members = []
    if recsize in (48, 64, 72) and c1 and doff <= len(b):
        tbl = b[pos + 16:pos + 16 + min(B, len(b) - pos - 16)]
        n = min(c1, len(tbl) // recsize)
        for k in range(n):
            r = tbl[k * recsize:(k + 1) * recsize]
            nmlen = recsize - 16
            raw = r[:nmlen]
            try:
                nm = raw.split(b'\0')[0].decode('cp932')
                if not nm or any(ord(ch) < 0x20 for ch in nm):
                    raise ValueError
            except Exception:
                nm = '<code:' + raw[:8].hex() + '>'
            off, stored, decomp, step = struct.unpack('<4I', r[nmlen:nmlen + 16])
            if off + stored > max(dsize, 0) + 4096:
                members = []
                break
            members.append((nm, doff + off, stored, decomp, step))
    return dict(nameLen=nl, name=hdrname, A=A, B=B, doff=doff, dsize=dsize,
                count=c1, recsize=recsize, tail=c2), members

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('datadir')
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--dump')
    ap.add_argument('--members', help='成员表清单输出（tsv）：set/idx/pak/name/stored/decomp/step')
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    out = open(a.manifest, 'w', encoding='utf-8')
    out.write('set\tidx\tname\tsize\tkind\thdr\tmembers\n')
    mo = open(a.members, 'w', encoding='utf-8') if a.members else None
    if mo:
        mo.write('set\tidx\tpak\tmember\tstored\tdecomp\tstep\n')
    total = 0
    for tag in ('DATA00', 'DATA01', 'DATA02', 'DATA03', 'DATA04'):
        base = os.path.join(a.datadir, tag)
        if not os.path.exists(base + '.HD'):
            continue
        sizes, ents, data = load_pair(base)
        names = read_names(data, sizes)
        npack = 0
        for i, (o, s) in enumerate(ents):
            nm0 = names[i] if i < len(names) else ''
            if a.only and not nm0.startswith(a.only):
                continue
            b = data[o:o + s]
            nm = safe_name(names[i]) if i < len(names) else ''
            hdr, mem = parse_pack(b)
            if hdr:
                npack += 1
                kind = 'PACK'
                h = 'A=%d,B=%d,off=%d,size=%d,n=%d,rs=%d' % (
                    hdr['A'], hdr['B'], hdr['doff'], hdr['dsize'], hdr['count'], hdr['recsize'])
            else:
                kind = 'RAW:' + b[:4].hex()
                h = ''
            out.write('%s\t%d\t%s\t%d\t%s\t%s\t%d\n' % (tag, i, nm, s, kind, h, len(mem)))
            if mo:
                for (mn, moff, mst, mdc, mstp) in mem:
                    mo.write('%s\t%d\t%s\t%s\t%d\t%d\t%d\n' % (tag, i, nm, mn, mst, mdc, mstp))
            if a.dump and mem:
                d = os.path.join(a.dump, '%s_%05d' % (tag, i))
                os.makedirs(d, exist_ok=True)
                for (mn, moff, mst, mdc, mstp) in mem:
                    safe = ''.join(ch if ch.isalnum() or ch in '._-' else '_' for ch in mn)
                    open(os.path.join(d, safe), 'wb').write(b[moff:moff + mst])
            total += 1
        print('%s entries=%d  names=%d  PACK=%d' % (tag, len(ents), len(names), npack))
    out.close()
    print('rows', total)

if __name__ == '__main__':
    main()
