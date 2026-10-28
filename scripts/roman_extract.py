# -*- coding: utf-8 -*-
"""召しませ浪漫茶房（SIMPLE2000 Vol.98 THE 浪漫茶房 / PS2-JP / SLPM_657.37）全文本提取

链路：ISO9660 → DATA/TML/TMLPACK.PAC（NonComp Pack）→ 306 个 *.TML → 命令流

TML 命令：u32 = 0xFF000000|opcode，参数紧随。正文 JIS X 0208 7bit（+0x80 = EUC-JP）。
  0x01F4 正文一行 [4][u8 len][len]          0x01F5 中央消息（扉文/字幕/旁白块）
  0x012C/0x012E 名札（独立名字窗，丢弃）     0x012D 名字清除
  0x0130 插入主角姓 / 0x0131 插入主角名
  0x01F6 枠内改行（软换行）                  0x01F7 枠終了 = 一次点击
  0x0192/0x0191 选项（首/续）：[4][u8][u32 id][u8 len][len]
"""
import os
import struct
import sys

SURNAME = '甘味'
GIVEN = '千歳'

TEXT, CENTER = 0x01F4, 0x01F5
NAME_OPS = (0x012C, 0x012E)
NAME_INS = {0x0130: SURNAME, 0x0131: GIVEN}
CHOICE = (0x0192, 0x0191)
LF, END = 0x01F6, 0x01F7

FIXED = {
    0x0000: 8, 0x0001: 0, 0x0002: 1, 0x0064: 2, 0x0065: 0, 0x0066: 2, 0x0067: 0, 0x0068: 2,
    0x0069: 0, 0x006A: 2, 0x006B: 2, 0x006C: 0, 0x00C8: 5, 0x00C9: 0, 0x00CA: 4,
    0x00CB: 4, 0x00CC: 4, 0x00CD: 0, 0x00CE: 3, 0x00CF: 3, 0x00D0: 5, 0x012D: 0,
    0x012F: 0, 0x0130: 0, 0x0131: 0, 0x0190: 4, 0x0193: 4, 0x0194: 0, 0x0195: 0, 0x0196: 7, 0x0197: 6, 0x0198: 6,
    0x01F6: 0, 0x01F7: 0, 0x01F8: 0, 0x01F9: 4,
    0x01FA: 2, 0x0258: 1, 0x0259: 0, 0x025A: 0, 0x025B: 0, 0x025C: 0, 0x025D: 1,
    0x02BC: 1, 0x02BD: 0, 0x02BE: 1, 0x02BF: 0, 0x02C0: 1, 0x0320: 8, 0x0384: 8,
    0x03E8: 2, 0x03E9: 1, 0x03EA: 4, 0x03EB: 4, 0x03EC: 0, 0x03ED: 0, 0x03EE: 0,
    0x03EF: 0, 0x03F0: 1, 0x03F1: 0, 0x03F2: 0, 0x03F3: 8, 0x03F4: 0, 0x03F5: 2,
    0x03F6: 4, 0x03F7: 0, 0x03F8: 8, 0x03F9: 0, 0x03FA: 3, 0x03FB: 2, 0x03FC: 1,
    0x03FD: 2,
}
ALL = set(FIXED) | {TEXT, CENTER} | set(NAME_OPS) | set(NAME_INS) | set(CHOICE)


def jis(buf):
    try:
        return bytes(b + 0x80 for b in buf).decode('euc_jp')
    except Exception:
        return None


def isop(b, i):
    if i + 4 > len(b):
        return None
    w, = struct.unpack_from('<I', b, i)
    if (w >> 16) != 0xff00:
        return None
    op = w & 0xffff
    return op if op in ALL else None


def tml_boxes(b):
    """→ [str]：一次点击 = 一行；同框软换行合并；中央消息块单独成行；选项各成一行"""
    out, cur = [], []
    mode = [None]
    i, n = 0, len(b)

    def flush():
        if cur:
            t = ''.join(cur).strip('\u3000 ')
            if t:
                out.append(t)
            cur.clear()
        mode[0] = None

    while i < n:
        op = isop(b, i)
        if op is None:
            if b[i:i + 4] == b'\x00\x00\x00\x00':
                j = i
                while j < n and b[j] == 0:
                    j += 1
                i = j
                continue
            if mode[0] == 'center':
                flush()
            i += 1
            continue
        if op in (TEXT, CENTER):
            if i + 5 > n:
                break
            L = b[i + 4]
            if i + 5 + L > n:
                i += 1
                continue
            s = jis(b[i + 5:i + 5 + L])
            if s is None:
                i += 1
                continue
            tag = 'text' if op == TEXT else 'center'
            if mode[0] is not None and mode[0] != tag:
                flush()
            mode[0] = tag
            cur.append(s)
            i += 5 + L
            continue
        if op in NAME_INS:
            cur.append(NAME_INS[op])
            i += 4
            continue
        if op in CHOICE:
            if i + 10 > n:
                break
            L = b[i + 9]
            if i + 10 + L > n:
                i += 1
                continue
            s = jis(b[i + 10:i + 10 + L])
            if s is None:
                i += 1
                continue
            flush()
            out.append(s)
            i += 10 + L
            continue
        if op in NAME_OPS:
            if i + 6 > n:
                break
            L = b[i + 5]
            i += 6 + L
            continue
        if op == LF:
            i += 4
            continue
        if op == END:
            flush()
            i += 4
            continue
        a = FIXED.get(op)
        if a is None:
            i += 1
            continue
        if i + 4 + a > n:
            break
        if mode[0] == 'center':
            flush()
        i += 4 + a
    flush()
    return out


def read_pack(path):
    d = open(path, 'rb').read()
    cnt, = struct.unpack_from('<I', d, 0x08)
    off, ents = 0x18 + cnt * 0x20, []
    for i in range(cnt):
        o = 0x18 + i * 0x20
        nm = d[o:o + 16].split(b'\0')[0].decode('cp932')
        sz, = struct.unpack_from('<I', d, o + 0x10)
        ents.append((nm, off, sz))
        off += sz
    return d, ents


def main():
    pac = sys.argv[1] if len(sys.argv) > 1 else '_work_msr/iso/DATA/TML/TMLPACK.PAC'
    out = sys.argv[2] if len(sys.argv) > 2 else '提取结果/[PS2-JP]召しませ浪漫茶房.txt'
    d, ents = read_pack(pac)
    blob = b''.join(d[o:o + s] for nm, o, s in ents)
    lines = tml_boxes(blob)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('files', len(ents), 'lines', len(lines), 'chars', sum(len(x) for x in lines))


if __name__ == '__main__':
    main()
