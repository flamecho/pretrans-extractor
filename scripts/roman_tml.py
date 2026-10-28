# -*- coding: utf-8 -*-
"""召しませ浪漫茶房 (PS2-JP / SLPM_657.37) —— TML 剧本解析（草案，供调参）

TML 命令流：u32 op = 0xFF000000|opcode，紧跟定长参数（少数带长度字节）。
  0x01F4      正文一行      [4][u8 len][len]   (JIS X 0208 7bit，+0x80=EUC-JP)
  0x01F5      中央消息      [4][u8 len][len]
  0x012C/12E  名札          [4][u8 color][u8 len][len]
  0x01F6      枠内改行（软换行）
  0x01F7      枠終了 = 一次点击
  0x0064/68/6A 角色/语音 id
  0x0190      跳转（u32 绝对偏移）
"""
import struct

TEXT_OPS = (0x01F4,)
CENTER_OPS = (0x01F5,)
NAME_OPS = (0x012C, 0x012E)
CHOICE_OPS = (0x0191, 0x0192)   # 0x192 首项 / 0x191 续项：[4][u8][u32 id][u8 len][len]
LF_OP = 0x01F6
END_OP = 0x01F7

FIXED = {
    0x0000: 8, 0x0001: 0, 0x0064: 2, 0x0065: 0, 0x0066: 2, 0x0067: 0, 0x0068: 2,
    0x0069: 0, 0x006A: 2, 0x006B: 2, 0x006C: 0, 0x00C8: 5, 0x00C9: 0, 0x00CA: 4,
    0x00CB: 4, 0x00CC: 4, 0x00CD: 0, 0x00CE: 3, 0x00CF: 3, 0x00D0: 5, 0x012D: 0,
    0x012F: 0, 0x0130: 0, 0x0131: 0, 0x0190: 4, 0x0191: 8, 0x0192: 8, 0x0193: 4,
    0x0194: 0, 0x0195: 0, 0x0196: 4, 0x0197: 4, 0x0198: 4, 0x01F6: 0, 0x01F7: 0,
    0x01F8: 0, 0x01F9: 4, 0x01FA: 2, 0x0258: 1, 0x0259: 0, 0x025A: 0, 0x025B: 0,
    0x025C: 0, 0x025D: 1, 0x02BC: 1, 0x02BD: 0, 0x02BE: 1, 0x02BF: 0, 0x02C0: 1,
    0x0320: 8, 0x0384: 8, 0x03E8: 2, 0x03E9: 1, 0x03EA: 4, 0x03EB: 4, 0x03EC: 0,
    0x03ED: 0, 0x03EE: 0, 0x03EF: 0, 0x03F0: 1, 0x03F1: 0, 0x03F2: 0, 0x03F3: 8,
    0x03F4: 0, 0x03F5: 2, 0x03F6: 4, 0x03F7: 0, 0x03F8: 8, 0x03F9: 0, 0x03FA: 3,
    0x03FB: 2, 0x03FC: 1, 0x03FD: 2,
}
ALL_OPS = set(FIXED) | set(TEXT_OPS) | set(NAME_OPS)


def jis(buf):
    try:
        s = bytes(b + 0x80 for b in buf).decode('euc_jp')
        return s
    except Exception:
        return None


def isop(b, i):
    if i + 4 > len(b):
        return None
    w, = struct.unpack_from('<I', b, i)
    if (w >> 16) != 0xff00:
        return None
    op = w & 0xffff
    return op if op in ALL_OPS else None


def walk(b):
    """→ events [(kind, payload, off)]; kind: text/name/lf/end/other"""
    i, ev, rs = 0, [], 0
    n = len(b)
    while i < n:
        op = isop(b, i)
        if op is None:
            i += 1
            rs += 1
            continue
        if op in TEXT_OPS:
            if i + 5 > n:
                break
            L = b[i + 4]
            if i + 5 + L > n:
                i += 1
                rs += 1
                continue
            s = jis(b[i + 5:i + 5 + L])
            if s is None:
                i += 1
                rs += 1
                continue
            ev.append(('text', s, i))
            i += 5 + L
            continue
        if op in NAME_OPS:
            if i + 6 > n:
                break
            L = b[i + 5]
            if i + 6 + L > n:
                i += 1
                rs += 1
                continue
            s = jis(b[i + 6:i + 6 + L])
            if s is None:
                i += 1
                rs += 1
                continue
            ev.append(('name', s, i))
            i += 6 + L
            continue
        a = FIXED.get(op)
        if a is None:
            i += 1
            rs += 1
            continue
        if i + 4 + a > n:
            break
        if op == LF_OP:
            ev.append(('lf', None, i))
        elif op == END_OP:
            ev.append(('end', None, i))
        else:
            ev.append(('other', op, i))
        i += 4 + a
    return ev, rs


def boxes(ev):
    """→ [(text, name)] 一次点击 = 一枠"""
    out, cur, name = [], [], None
    for kind, pay, off in ev:
        if kind == 'name':
            name = pay
        elif kind == 'text':
            cur.append(pay)
        elif kind == 'end':
            if cur:
                out.append((''.join(cur), name))
            cur, name = [], None
    if cur:
        out.append((''.join(cur), name))
    return out
