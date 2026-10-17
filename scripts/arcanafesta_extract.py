#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アルカナ・ファミリア フェスタ・レガーロ! (PSP, HuneX「IKA SEQ SYSTEM v3.4/v4.2」) 全文本提取。

源：PSP ISO9660 → PSP_GAME/USRDIR/DATA/GAMEDT.AFS（CRI AFS，7 成员）
容器：
  AFS: 'AFS\\0' + u32 count + count×{u32 off,u32 size}（首项 off 即数据区）
  HFU2: 'HFU2' + u32 count + u32 X(头部/前缀大小) + u32 1 + count×16B{off,size,size2,hash}
        —— 绝对块位置 = X + off[k]；size = 16 + 载荷长；size2 = 解压后长度
  UFFA 块头(16B): 'UFFA' + u32 payload_len + u32 out_size + u32 0 + u32 0
LZSS（cLz.cpp / 经典 Okumura）：dict 0x1000、dictpos 初值 0xFEE、dict 清零
  flag 字节：flags>>=1；若 (flags&0x100)==0 则 flags = src[i] | 0xFF00
  flags&1==1 → 字面量；否则 match = {low,high}: off = low|((high&0xF0)<<4)、len = (high&0x0F)+3
字节码：指令 `26 <cmd> 24 <nargs> <operands>`；字符串记录 `5C <L> <SJIS L-4> 00 00`（L=记录总长）
文本命令：
  0x3E n=1  名前札（丢弃，不产出说话人）
  0x80 n=3  台詞（要收）
  0x3C n=3  台詞/独白（要收）
  0x41 n=4  選択肢（要收；其后参数为写入值 → 丢）
控制码：@n = 框内软换行 → 合并；其余无
"""
import sys, os, struct

OKUMURA_MAXLEN = 0x12


def parse_iso_afs(iso_path):
    """返回 GAMEDT.AFS 的 bytes"""
    with open(iso_path, 'rb') as f:
        f.seek(0x8000)
        pvd = f.read(0x800)
        assert pvd[1:6] == b'CD001'
        # 遍历目录找 USRDIR/DATA/GAMEDT.AFS
        def walk(ext, size, prefix):
            f.seek(ext * 2048)
            data = f.read(size)
            p = 0
            while p < len(data):
                L = data[p]
                if L == 0:
                    p = (p // 2048 + 1) * 2048
                    continue
                rec = data[p:p + L]
                e = struct.unpack_from('<I', rec, 2)[0]
                sz = struct.unpack_from('<I', rec, 10)[0]
                flags = rec[25]
                nlen = rec[32]
                name = rec[33:33 + nlen].decode('latin1')
                if name not in ('\x00', '\x01'):
                    full = prefix + '/' + name
                    if flags & 2:
                        r = walk(e, sz, full)
                        if r:
                            return r
                    elif full.endswith('GAMEDT.AFS'):
                        f.seek(e * 2048)
                        return f.read(sz)
                p += L
            return None
        root_ext = struct.unpack_from('<I', pvd, 0x9C + 2)[0]
        root_sz = struct.unpack_from('<I', pvd, 0x9C + 10)[0]
        return walk(root_ext, root_sz, '')


def lzs_decode(src, outsize):
    N = 0x1000
    db = bytearray(N)
    out = bytearray()
    flags = 0
    i = 0
    dp = 0xFEE
    n = len(src)
    ap = out.append
    while i < n and len(out) < outsize:
        flags >>= 1
        if (flags & 0x100) == 0:
            flags = src[i] | 0xFF00
            i += 1
        if flags & 1:
            c = src[i]; i += 1
            ap(c); db[dp] = c; dp = (dp + 1) & (N - 1)
        else:
            low = src[i]; high = src[i + 1]; i += 2
            off = low | ((high & 0xF0) << 4)
            ln = (high & 0x0F) + 3
            for t in range(ln):
                c = db[(off + t) & (N - 1)]
                ap(c); db[dp] = c; dp = (dp + 1) & (N - 1)
    return bytes(out)


def decode_hfu2(data):
    assert data[:4] == b'HFU2', data[:4]
    cnt = struct.unpack_from('<I', data, 4)[0]
    X = struct.unpack_from('<I', data, 8)[0]
    outs = []
    for k in range(cnt):
        o, s, s2, h = struct.unpack_from('<IIII', data, 0x10 + k * 16)
        p = X + o
        if data[p:p + 4] != b'UFFA':
            outs.append(b'')
            continue
        cs, us, _c3, _c4 = struct.unpack_from('<IIII', data, p + 4)
        outs.append(lzs_decode(data[p + 16:p + 16 + cs], us))
    return outs


def parse_afs_members(data):
    assert data[:4] == b'AFS\x00'
    cnt = struct.unpack_from('<I', data, 4)[0]
    return [struct.unpack_from('<II', data, 8 + i * 8) for i in range(cnt)]


def iter_str_records(stream):
    """产出 (pos, cmd, nargs, text) —— 文本命令的 5C 串（自定界，永不失步）"""
    i = 0
    N = len(stream)
    while i < N - 6:
        if stream[i] == 0x26 and stream[i + 2] == 0x24 and stream[i + 4] == 0x5C:
            L = stream[i + 5]
            if 4 <= L <= 400 and i + 4 + L <= N and stream[i + 4 + L - 2] == 0 and stream[i + 4 + L - 1] == 0:
                body = stream[i + 6:i + 4 + L - 2]
                try:
                    txt = body.decode('cp932')
                except UnicodeDecodeError:
                    i += 1; continue
                yield (i, stream[i + 1], stream[i + 3], txt)
                i += 4 + L
                continue
        i += 1


TEXT_CMDS = {0x80, 0x3C, 0x4D}   # 台詞（0x4D = 複数名の後のセリフ）
CHOICE_CMD = 0x41
NAME_CMDS = {0x3E, 0x4C}        # 名札（0x4C = 複数名"ジョルジョ他"）

# ★ 姓名槽宏：全角＄（SJIS 0x8190 / U+FF04）。ELF `EBOOT.BIN.dec` @0x218F30 内有槽表
#   `＄フェリチータ`／`＄フェル`／`＄フクロータ` ＋ 对应默认名（フェリチータ／フェル／フクロータ）
#   ⇒ `＄<默认名>` = 可改名槽；交付按默认名 inline（去宏符，保留其后默认名）。
#   （同族全角记号 0x8190-0x819F 均为引擎保留符；本作文本内只出现 ＄。）
NAME_SLOT_MACRO = '\uff04'


def clean_text(t):
    return t.replace('@n', '').replace(NAME_SLOT_MACRO, '')


def extract_lines(stream):
    """按出现顺序产出成品行（正文＋选项）；丢弃名札；@n 合并；姓名槽宏按默认名 inline。"""
    lines = []
    stats = {}
    for pos, cmd, nargs, txt in iter_str_records(stream):
        stats[cmd] = stats.get(cmd, 0) + 1
        if cmd in NAME_CMDS:
            continue
        if cmd in TEXT_CMDS:
            lines.append(clean_text(txt))
        elif cmd == CHOICE_CMD:
            lines.append(clean_text(txt))
        else:
            stats.setdefault('_other_%#x' % cmd, 0)
    return lines, stats


def main():
    iso = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else '_work_arcanafesta'
    os.makedirs(outdir, exist_ok=True)
    afs = parse_iso_afs(iso)
    assert afs, 'GAMEDT.AFS not found'
    print('GAMEDT.AFS %d bytes' % len(afs))
    mems = parse_afs_members(afs)
    blobs = {}
    for idx, (off, size) in enumerate(mems):
        d = afs[off:off + size]
        if d[:4] == b'HFU2':
            cnt = struct.unpack_from('<I', d, 4)[0]
            outs = decode_hfu2(d)
            blob = b''.join(outs)
            blobs[idx] = blob
            open(os.path.join(outdir, 'mem%d.dec' % idx), 'wb').write(blob)
            print('AFS[%d] HFU2 count=%d decoded=%d' % (idx, cnt, len(blob)))
        elif d[:4] == b'AFS\x00':
            print('AFS[%d] nested AFS size=%d' % (idx, size))
    return blobs


if __name__ == '__main__':
    main()
