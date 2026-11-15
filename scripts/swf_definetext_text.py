# -*- coding: utf-8 -*-
"""Macromedia Flash / Shockwave（SWF）→ 「一次点击 = 一行」。

输入需要两步（Flash 5 的 DefineText 位流细节各家实现不一，用参考实现取字形序列最稳）：
  ① node texts.js <in.SWF> <texts.json>        ← 用 swf-parser 取每个 DefineText 的 字形索引序列
  ② python scripts/swf_definetext_text.py --swf <in.SWF> --texts texts.json --out <成品.txt>

判据（全部结构级）：
  字体码表：DefineFont2 的 CodeTableOffset 基址 = **OffsetTable 起点**；
           OffsetTable 宽度 = flags & 0x08 ⇒ u32，否则 u16（本族实测，与部分规范实现不同）；
           校验 = 码表 100% 落在 cp932 合法区间。码表值即 **cp932 码**。
  断框：**一个 DefineText = 一个显示对象**（PlaceObject2 一个 depth 放一个对象）⇒ 一屏一框；
       框内 records = 行（每记录 ≤ ~21 字）⇒ 合并成一行。
  顺序：按该对象**首次被 PlaceObject2 放置的帧号**。
  剔除（结构级，不按文字内容）：
       ① 被 DefineButton2 引用的字符 ⇒ 按钮标签（系统 UI）
       ② 只出现在「常驻精灵」（跨度 ≥ 500 帧的组件）内 ⇒ 标题/控制组件
  名札：`【名】` 与正文同在一个 DefineText ⇒ 印在正文框内 ⇒ **保留原样**（品检加 --inline-name）
"""
import argparse, io, json, struct, sys, collections

LEGAL = lambda v: v < 0x80 or 0x8140 <= v <= 0x9FFC or 0xE040 <= v <= 0xFCFC
CODE_SHOWFRAME, CODE_PLACE2, CODE_REMOVE2 = 1, 26, 28
CODE_DEFTEXT, CODE_DEFBTN2, CODE_DEFSPRITE, CODE_DEFFONT2 = 11, 34, 39, 48
PERSIST_SPAN = 500


class BR:
    def __init__(s, d, p):
        s.d, s.p, s.bit = d, p, 0

    def align(s):
        if s.bit:
            s.p += 1
            s.bit = 0

    def ub(s, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | ((s.d[s.p] >> (7 - s.bit)) & 1)
            s.bit += 1
            if s.bit == 8:
                s.bit = 0
                s.p += 1
        return v

    def sb(s, n):
        if n == 0:
            return 0
        v = s.ub(n)
        return v - (1 << n) if v & (1 << (n - 1)) else v

    def rect(s):
        n = s.ub(5)
        return [s.sb(n) for _ in range(4)]

    def matrix(s):
        if s.ub(1):
            n = s.ub(5); s.sb(n); s.sb(n)
        if s.ub(1):
            n = s.ub(5); s.sb(n); s.sb(n)
        n = s.ub(5); s.sb(n); s.sb(n)


def walk(d, start, end, out=None, depth=0):
    out = [] if out is None else out
    p = start
    while p + 2 <= end:
        h = struct.unpack_from('<H', d, p)[0]
        code, ln = h >> 6, h & 0x3F
        p += 2
        if ln == 0x3F:
            ln = struct.unpack_from('<I', d, p)[0]
            p += 4
        out.append((code, p, ln, depth))
        if code == CODE_DEFSPRITE and ln >= 4:
            walk(d, p + 4, p + ln, out, depth + 1)
        p += ln
    return out


def load_fonts(d, tl):
    fonts = {}
    for code, b, ln, _dp in tl:
        if code != CODE_DEFFONT2:
            continue
        fid = struct.unpack_from('<H', d, b)[0]
        flags, nlen = d[b + 2], d[b + 4]
        q = b + 5 + nlen
        ng = struct.unpack_from('<H', d, q)[0]
        wide = (flags >> 3) & 1
        off = 4 if wide else 2
        cto = struct.unpack_from('<I' if wide else '<H', d, q + 2 + ng * off)[0]
        ct = q + 2 + cto
        fonts[fid] = [struct.unpack_from('<H', d, ct + i * 2)[0] for i in range(ng)]
    return fonts


def button_chars(d, tl):
    """DefineButton2 引用的字符 ID（含其内精灵递归闭包）"""
    direct = {}
    for code, b, ln, _dp in tl:
        if code != CODE_DEFBTN2:
            continue
        ids, q = [], b + 5
        while q < b + ln:
            fl = d[q]
            if fl == 0:
                break
            q += 1
            cid = struct.unpack_from('<H', d, q)[0]
            q += 4
            r = BR(d, q)
            r.matrix(); r.align(); q = r.p
            r2 = BR(d, q)
            for _ in range(2):
                if r2.ub(1):
                    n = r2.ub(4)
                    for _ in range(4):
                        r2.sb(n)
            r2.align(); q = r2.p
            if fl & 0x20:
                break
            if fl & 0x10:
                q += 1
            if cid:
                ids.append(cid)
        direct[struct.unpack_from('<H', d, b)[0]] = ids
    return direct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--swf', required=True)
    ap.add_argument('--texts', required=True)
    ap.add_argument('--out')
    ap.add_argument('--dump')
    a = ap.parse_args()

    d = open(a.swf, 'rb').read()
    p = 8
    nb = d[p] >> 3
    p += (5 + 4 * nb + 7) // 8 + 4
    tl = walk(d, p, len(d))
    fonts = load_fonts(d, tl)
    print('字体 %d 个：%s' % (len(fonts), {k: len(v) for k, v in fonts.items()}))

    # 顶层舞台：depth -> charId，记录每个对象出现的帧
    frame, stage, seen = 0, {}, collections.defaultdict(list)
    for code, b, ln, dp in tl:
        if code == CODE_SHOWFRAME and dp == 0:      # ★ 只数主时间轴（精灵内 ShowFrame 不计）
            frame += 1
        elif code == CODE_PLACE2 and dp == 0:
            fl = d[b]
            depth = struct.unpack_from('<H', d, b + 1)[0]
            if fl & 0x02:
                cid = struct.unpack_from('<H', d, b + 3)[0]
                stage[depth] = cid
                seen[cid].append(frame)
            elif fl & 0x01 and depth in stage:
                seen[stage[depth]].append(frame)
        elif code == CODE_REMOVE2 and dp == 0:
            stage.pop(struct.unpack_from('<H', d, b)[0], None)
    print('总帧 %d ／ 顶层被放置对象 %d' % (frame, len(seen)))

    # 精灵 → 内含字符
    inner = {}
    for code, b, ln, dp in tl:
        if code == CODE_DEFSPRITE:
            sid = struct.unpack_from('<H', d, b)[0]
            inner[sid] = [struct.unpack_from('<H', d, b2 + 3)[0]
                          for c2, b2, l2, d2 in tl
                          if c2 == CODE_PLACE2 and b < b2 < b + ln and (d[b2] & 0x02)]
    persistent = {sid for sid, fr in ((s, seen.get(s)) for s in inner)
                  if fr and max(fr) - min(fr) >= PERSIST_SPAN and len(set(fr)) <= 12}
    print('精灵 %d 个；常驻组件（跨度 ≥%d 帧）%d 个：%s'
          % (len(inner), PERSIST_SPAN, len(persistent), sorted(persistent)[:12]))

    # 字符 → 直接所在精灵；精灵自身也可能只被别的精灵放置 ⇒ 逐层上溯到「有顶层帧」的精灵
    owner = {}
    for sid, chs in inner.items():
        for c in chs:
            owner.setdefault(c, []).append(sid)

    def order_key(cid, deep=0):
        """返回 (帧号, 说明)；只看顶层时间轴 ⇒ 精灵内的文本借其宿主精灵的首帧"""
        if cid in seen:
            return min(seen[cid]), 'top'
        if deep > 3:
            return None, 'deep'
        best = None
        for sid in owner.get(cid, []):
            k, _w = order_key(sid, deep + 1)
            if k is not None and (best is None or k < best):
                best = k
        return best, 'sprite' if best is not None else 'none'

    btn = button_chars(d, tl)
    # 按钮闭包：按钮引用的字符 + 这些精灵内含的字符
    ban = set()
    for ids in btn.values():
        for c in ids:
            ban.add(c)
            ban.update(inner.get(c, []))
    for sid in persistent:
        ban.update(inner.get(sid, []))

    data = json.load(open(a.texts, encoding='utf-8'))
    rows, ex = [], []
    for t in data['texts']:
        cid = t['id']
        s, cur = '', None
        for r in t['records']:
            if r['f']:
                cur = r['f']
            cs = fonts.get(cur, [])
            for g in r['e']:
                if g >= len(cs):
                    continue
                v = cs[g]
                s += chr(v) if v < 0x80 else v.to_bytes(2, 'big').decode('cp932', 'replace')
        if cid in ban:
            ex.append(('UI/组件', cid, s))
            continue
        if any(ord(ch) < 0x20 or ch == '\ufffd' for ch in s):
            ex.append(('不可解码', cid, s))
            continue
        k, how = order_key(cid)
        if k is None:
            ex.append(('未上屏', cid, s))
            continue
        rows.append((k, cid, s))
    rows.sort()
    print('收入 %d 条 ／ 剔除 %d 条（%s）'
          % (len(rows), len(ex), collections.Counter(k for k, _c, _s in ex)))
    for k, c, s in ex:
        print('   剔[%s] id=%-5d %r' % (k, c, s[:40]))
    print('总字 %d ／ 最长 %d' % (sum(len(s) for _f, _c, s in rows), max(len(s) for _f, _c, s in rows)))
    if a.out:
        with io.open(a.out, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('\n'.join(s for _f, _c, s in rows) + '\n')
        print('→ %s' % a.out)
    if a.dump:
        json.dump([[f, c] for f, c, _s in rows], open(a.dump, 'w'))


if __name__ == '__main__':
    main()
