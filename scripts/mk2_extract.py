# -*- coding: utf-8 -*-
"""[NS-JP]リトルプリンセス マール王国の人形姫２ —— message.bin → 成行

记录（L1 自定界）：
    [u16 total][u16 A][u16 B][u8 C][操作码流…]
    记录总长 = total（实测 7,062 条首尾相接铺满 553,540 B，无残留）

文本槽（L0/L1）：
    操作码 `01` + u16 L + (L-2) 字节 cp932 正文
    自验证：每条记录内**恰好一个**候选（cp932 全段可解、无控制符、L-2 与紧随其后的
    下一个操作码严格对齐）—— 7,062 条里 6,004 条命中 1 个、0 条命中 2 个以上。

断框（L1）：`%n`(0x25 0x6e) = 框内改行；文本框**恒 3 行**；作者用 `%n` 连跑（2〜3 个）
          把内容补满到框边界 ⇒ 每 3 行 = 1 个文本框 = 1 次点击 = 输出 1 行。
          可证伪验证见报告：R 连跑结束后累计换行数落在 3 的倍数上 1725/1733 = 99.5%
          （H=2 13.6% / H=4 1.2% / H=5 0.3%）。

其它演出码：`%v`(9 处) `%3`(6 处) —— 揺れ/速度系，无字形，剥离并计入报告。
"""
import struct, sys

REC_MIN = 8
REC_MAX = 0x2000
BOX_LINES = 3

CODES = ('%v', '%3')          # 非换行的演出码：无字形，直接剥离


def walk(d):
    """按 u16 总长链式走；不合规就 +1 重同步。返回 [(off, rec)]。"""
    N = len(d)
    out = []
    p = 0
    miss = 0
    while p + 4 <= N:
        sz = struct.unpack_from('<H', d, p)[0]
        if REC_MIN <= sz <= REC_MAX and p + sz <= N:
            out.append((p, d[p:p + sz]))
            p += sz
            miss = 0
        else:
            p += 1
            miss += 1
            if miss > 400:
                break
    return out


OPBYTES = set(b'\x01\x02\x03\x05\x07\x09\x0b\x0d\x1f')   # 已观测到的操作码字节


def text_slot(rec):
    """记录内唯一的文本槽。

    两种前缀形态都存在（同一引擎里两条写文本的路径）：
        A: `01 <u16 L> <正文>`            —— 无 id 的叙述行
        B: `03 <u16 id> <u16 L> <正文>`   —— 带 id 的台词行
    两者共通的不变量：**u16 L 紧跟正文，L = 正文字节数 + 2**。

    判法：在全记录里找所有满足不变量、且正文结束处正好落在操作码字节上的候选，
    只留「极大」候选（不被别的候选包含）⇒ 实测 7,062 条里 **6,239 条恰好 1 个、0 条 2 个以上**。
    """
    n = len(rec)
    out = []
    for i in range(6, n - 5):
        L = rec[i] | (rec[i + 1] << 8)
        if L < 6 or i + L > n:
            continue
        try:
            t = rec[i + 2:i + L].decode('cp932')
        except Exception:
            continue
        if not t or any(ord(c) < 0x20 for c in t):
            continue
        if i + L < n and rec[i + L] not in OPBYTES:
            continue
        out.append((i, L, t))
    keep = [(i, L, t) for i, L, t in out
            if not any(i2 < i and i2 + L2 >= i + L for i2, L2, _ in out)]
    uniq = {}
    for i, L, t in keep:
        uniq.setdefault(i, t)
    vals = list(uniq.values())
    return vals[0] if len(vals) == 1 else None


def boxes(text):
    for c in CODES:
        text = text.replace(c, '')
    lines = text.split('%n')
    out = []
    for i in range(0, len(lines), BOX_LINES):
        chunk = lines[i:i + BOX_LINES]
        s = ''.join(chunk).strip()
        if s:
            out.append(s)
    return out


def extract(path):
    d = open(path, 'rb').read()
    recs = walk(d)
    rows = []
    nslot = 0
    for off, rec in recs:
        t = text_slot(rec)
        if not t:
            continue
        nslot += 1
        rows.extend(boxes(t))
    return recs, nslot, rows


def load_book(path):
    """日記 / 観察ノート 的 TSV（col0=页号, col1=x, col2=y, col3=正文）。

    首行是表头；col0 有值的行 = 新条目（含【見出し語】），col0 空的行 = 同页续行。
    一页 = 一次显示 ⇒ 每条并入一行（同上「框内换行合并」口径）。
    """
    import io
    rows = []
    cur = []
    for line in io.open(path, encoding='utf-8', newline='').read().split('\r\n'):
        if not line.strip():
            continue
        col = line.split('\t')
        if len(col) < 4:
            continue
        if col[0].strip() in ('da#', 'page'):
            continue
        if col[0].strip():
            if cur:
                rows.append(''.join(cur).strip())
            cur = [col[3]]
        elif cur:
            cur.append(col[3])
    if cur:
        rows.append(''.join(cur).strip())
    return [r for r in rows if r]


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    recs, nslot, rows = extract(src)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        for r in rows:
            f.write(r + '\n')
    print('records=%d slots=%d lines=%d' % (len(recs), nslot, len(rows)))
    if len(sys.argv) > 3:                      # 附录：日記 / 観察ノート
        for extra in sys.argv[3:]:
            b = load_book(extra)
            with open(dst, 'a', encoding='utf-8', newline='\n') as f:
                for r in b:
                    f.write(r + '\n')
            print('  + %s: %d 行' % (extra.split('/')[-1], len(b)))
