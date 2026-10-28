# -*- coding: utf-8 -*-
"""LSB 剧本解析（VSC 引擎 / ラスト・エスコート2 ～深夜の甘い棘～ PS2-JP）

容器：DATA/SYSTEM.VDP → SCRIPT 条目 → 765 个 *.LSB

LSB 文件头
  0x00 u32 fileSize / 0x04 u32 cmdCount / 0x08 u32 ? / 0x0C u32 cmdOff(0x58)
  0x10 u32 bodyOff / 0x14 u32 0 / 0x18 标题 cp932（场景名，不渲染正文）

正文区（按偏移顺序；串一律 NUL 结尾，cp932）
  * 名札 + 正文 = 两个**紧邻**的串（名札短，正文长）
  * 主角行 = `26 00` + 正文（名札即 0x26 名宏，故只占 1 字节）
  * 选项块 = `cc cc cc cc` 填充 + [u32 A][u32 B] + 若干紧邻串
  * 单个孤立串 = 旁白 / 字幕（扉文、时间跳跃）

正文内控制字节：0x5C / 0x23 = 同框软换行（合并）；0x25 = 演出停顿；0x26 = 主角名
"""
import struct, sys

BRK = {0x23, 0x5c}


def read_str(d, i, limit=400):
    n, j = len(d), i
    while j < n and j - i <= limit:
        b = d[j]
        if b == 0:
            break
        if 0x20 <= b <= 0x7e:
            j += 1
            continue
        if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xfc:
            t = d[j+1] if j + 1 < n else 0
            if 0x40 <= t <= 0x7e or 0x80 <= t <= 0xfc:
                j += 2
                continue
            return None, i
        return None, i
    if j >= n or j == i:
        return None, i
    s = d[i:j].decode('cp932', 'replace')
    if '\ufffd' in s:
        return None, i
    return s, j + 1


def jp(s):
    return any(ord(c) > 0xff for c in s)


def _field(d, a, b):
    """a..b 区间视为若干 u32 字段（<0x01000000 或 -1）"""
    n = b - a
    for g in range(0, n - n % 4, 4):
        v = struct.unpack('<I', d[a+g:a+g+4])[0]
        if not (v < 0x01000000 or v == 0xffffffff):
            return False
    return True


def strings(d, start):
    """全部 NUL 结尾的日文串 [(off, end, s)]"""
    out, i, n = [], start, len(d)
    while i < n - 2:
        s, e = read_str(d, i)
        if s is not None and jp(s):
            out.append((i, e, s))
            i = e
        else:
            i += 1
    return out


def opt_spans(d):
    """选项块 [(cc起点, 选项起点, 结束)]"""
    out, i = [], 0
    while True:
        i = d.find(b'\xcc\xcc\xcc\xcc', i)
        if i < 0:
            break
        head = d[i-8:i]
        A, B = struct.unpack('<II', d[i+4:i+12])
        ok = head == b'\xff' * 8 or (d[i-4:i] == b'\xff' * 4 and A < 0x10000 and B < 0x10000)
        if ok:
            p, strs = i + 12, []
            while True:
                s, q = read_str(d, p, 200)
                if s is None:
                    break
                strs.append(s)
                p = q
            if len(strs) >= 2:
                out.append((i, i + 12, p))
                i = p
                continue
        i += 1
    return out


def parse(path, keep_span=False):
    d = open(path, 'rb').read()
    if len(d) < 0x30:
        return ([], '', [], []) if keep_span else ([], '')
    body = struct.unpack('<I', d[0x10:0x14])[0]
    try:
        title = d[0x18:d.find(b'\x00', 0x18)].decode('cp932')
    except Exception:
        title = ''
    opts = opt_spans(d)

    def in_opt(o):
        for a, o0, b in opts:
            if a <= o < b:
                return True
        return False

    items, span = [], []
    for a, o0, b in opts:                       # 选项
        p = o0
        while p < b:
            s, q = read_str(d, p, 200)
            if s is None:
                break
            items.append((p, 'O', '', s))
            p = q
        span.append((a, b))

    ss = strings(d, body)
    k = 0
    while k < len(ss):
        o, e, s = ss[k]
        if in_opt(o):
            k += 1
            continue
        run = [ss[k]]
        j = k + 1
        while j < len(ss) and ss[j][0] == run[-1][1] and not in_opt(ss[j][0]):
            run.append(ss[j])
            j += 1
        if len(run) >= 2:                        # 名札 + 正文
            nm = run[0][2]
            good = (len(nm) <= 8 and not any(c in nm for c in '。！？…、')
                    and len(run[1][2]) >= 2)
            if good:
                for o2, e2, s2 in run[1:]:
                    if len(s2) < 2:              # 1 字残渣（结构字节误读）
                        span.append((o2, e2 - 1))
                        continue
                    items.append((o2, 'T', nm if len(nm) <= 12 else '', s2))
                    span.append((o2, e2 - 1))
                span.append((run[0][0], run[0][1] - 1))
                k = j
                continue
        if o >= 2 and d[o-2:o] == b'\x26\x00':   # 主角行
            items.append((o, 'T', '\x01MC', s))
        elif len(s) >= 2 and o >= 8 and _field(d, o - 8, o):
            items.append((o, 'T', '', s))        # 孤立串：旁白/字幕（前 8 字节为字段）
        span.append((o, e - 1))
        k += 1
    items.sort(key=lambda x: x[0])
    res = [(kd, nm, tx) for _, kd, nm, tx in items]
    return (res, title, span, []) if keep_span else (res, title)


def clean(s, name, sur='安藤'):
    for c in BRK:
        s = s.replace(chr(c), '')
    return s.replace(chr(0x25), sur).replace(chr(0x26), name)


if __name__ == '__main__':
    items, title = parse(sys.argv[1])
    out = ['title ' + title + ' items ' + str(len(items))]
    for k, nm, tx in items:
        out.append(k + ' [' + nm + '] ' + tx.replace(chr(0x5c), '/').replace(chr(0x23), '/'))
    sys.stdout.buffer.write(('\n'.join(out) + '\n').encode('utf-8'))
