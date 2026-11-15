# -*- coding: utf-8 -*-
"""Director（8.5 / Afterburner 已由 ProjectorRays 解成 .dir）→ 全文本

用法:
    python scripts/director_xmed_text.py <含 .dir/.cst 的目录> <out.txt> [--files A,B,C]

判据（2026-11-03 [JP]D.Zone 实测，Ritz 系 Director 8.5 + 自制 Text Xtra）:
- 正文不在 STXT（那是 INI/画布设置），而在 **`XMED`** 块里，纯 cp932、行间用 `0x0D` 分隔。
- **1 个 `XMED` ＝ 1 个 text 成员（CASt type 15）＝ 1 个文本框 ＝ 一次点击**
  ⇒ 块内 `0x0D` 分行是**框内换行**，按口径**合并成一行**（不拆）。
  证据：D.Zone 各片 `XMED` 数 == CASt(type 15) 数（DAIL2：634 / 634）；块内页数中位 2–3 行；
  文本按块序读下去剧情连贯（DAIL2 第 0～15 块＝一场完整对话）。
- `XMED` 里除正文外还有**样式记录**（形如 `1\\x020ﾂ\\x07＝\\x01…` 含控制字节）⇒ 用
  「不含 C0 控制字节 ＋ 至少 1 个日文字符 ＋ 无 U+FFFD」过滤。
- 遍历：RIFX 的 size **不含 8 字节头**；ProjectorRays 写出的 .dir **不做偶数填充**（`off += 8+sz`）。
  个别文件若中途断掉（<=90% 文件长度），自动改试 `+1` 填充。
"""
import os
import re
import struct
import sys

JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
BAD = re.compile(r'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]')
# 「像正文」的判据：有日文字符，且**不含** C0 控制符 / U+FFFD / 私用区 / 半角片假名。
# 本作 XMED 的二进制尾巴正是「私用区（U+F8F0 一带）＋半角片假名」混出来的伪汉字，用它分开正好；
# 半角片假名不作为正文（这类 2000 年代 Director 作品不用半角假名）。
_CTRL = re.compile(r'[\x00-\x1f\x7f\ufffd]')
# 私用区 + **半角片假名字母**（U+FF66–FF9F）＝二进制尾巴的特征；
# 半角**标点**（U+FF61–FF65，如 `･`）不算垃圾，正文里真的会用。
_JUNK = re.compile(r'[\ue000-\uf8ff\uff66-\uff9f]')


def _junk_ratio(t):
    if not t:
        return 1.0
    return len(_JUNK.findall(t)) / len(t)


def _plausible(t):
    # 「像正文」：有日文字符；不含控制符；私用区/半角假名的占比 < 30%
    # （半角假名不能一刀切：正文里真的会出现 `･」`，但二进制尾巴是成片的私用区＋半角假名）
    return bool(JP.search(t)) and not _CTRL.search(t) and not _JUNK.search(t)


# 续行可以用「无日文但有标点」的片段（如 `CHIP'S……」`）：样式表是纯 ASCII 数字串，不含这些标点。
PUNCT = set('」』）｝〕】…。、！？♪―—─')


def _plausible_next(t):
    if not t or _CTRL.search(t) or _JUNK.search(t):
        return False
    return bool(JP.search(t)) or any(c in PUNCT for c in t)


def walk_chunks(d, pad):
    """返回 [(tag, off, size)]；tag 非 4 可打印字符即停。"""
    u = lambda o: struct.unpack_from('>I', d, o)[0]
    out = []
    off = 12
    while off + 8 <= len(d):
        cc = d[off:off + 4]
        if not all(32 <= x < 127 for x in cc):
            break
        sz = u(off + 4)
        out.append((cc.decode('latin1'), off, sz))
        off += 8 + sz + (pad if sz & 1 else 0)
    return out


def _tag_ok(d, o):
    if o + 8 > len(d):
        return False
    cc = d[o:o + 4]
    if not all(32 <= x < 127 for x in cc):
        return False
    sz = struct.unpack_from('>I', d, o + 4)[0]
    return 8 + sz <= len(d) - o


def _chain_ok(d, o, depth=2):
    """从 o 起连续 depth 个 chunk 头都合法 ⇒ 认为对齐正确。"""
    for _ in range(depth):
        if not _tag_ok(d, o):
            return False
        sz = struct.unpack_from('>I', d, o + 4)[0]
        o = o + 8 + sz if _tag_ok(d, o + 8 + sz) else o + 8 + sz + (sz & 1)
    return True


def walk_resync(d):
    """鲁棒遍历：用「后续 2 个 chunk 头都合法」判定该块是否补 1 字节填充；
    失步则在 4 KB 内重同步。（PR 写出的 .dir 里奇偶填充混用，单一规则会中途失步 —— KEENED 曾只走到 14%）"""
    u = lambda o: struct.unpack_from('>I', d, o)[0]
    out = []
    off = 12
    guard = 0
    while off + 8 <= len(d) and guard < 300000:
        guard += 1
        if not _tag_ok(d, off):
            nxt = None
            for k in range(off + 1, min(len(d) - 8, off + 4096)):
                if _tag_ok(d, k):
                    nxt = k
                    break
            if nxt is None:
                break
            off = nxt
            continue
        cc = d[off:off + 4].decode('latin1')
        sz = u(off + 4)
        out.append((cc, off, sz))
        c0, c1 = off + 8 + sz, off + 8 + sz + (sz & 1)
        if _chain_ok(d, c0):
            off = c0
        elif _chain_ok(d, c1):
            off = c1
        elif _tag_ok(d, c0):
            off = c0
        elif _tag_ok(d, c1):
            off = c1
        else:
            off = c0
    return out


def parse_mmap(d):
    """读 `mmap`（chunk 索引表），返回 [(fourCC, 偏移, 体长)]。
    头部 24 B：u16 头长(24) + u16 条目长(20) + u32 条目数 + 4 个 u32（junk/free 链）
    条目 20 B：fourCC(4) + 体长(4) + 偏移(4) + flags(2) + unk(2) + next(4)。
    ★ 这是**权威表**：比线性遍历稳（线性遍历在奇偶填充混用处会吞掉 1 块）。"""
    o = d.find(b'mmap')
    if o < 0:
        return None
    body = o + 8
    if body + 24 > len(d):
        return None
    hl, el, cnt = struct.unpack_from('>HHI', d, body)
    if not (el == 20 and 24 <= hl <= 64 and 0 < cnt < 200000):
        return None
    out = []
    st = body + hl
    for k in range(cnt):
        p = st + k * el
        if p + el > len(d):
            break
        cc = d[p:p + 4].decode('latin1')
        ln, off, fl = struct.unpack_from('>III', d, p + 4)
        if off + 8 > len(d) or ln > len(d) - off - 8:
            continue
        out.append((cc, off, ln))
    return out


def chunks_of(d):
    e = parse_mmap(d)
    if e:
        return e
    return [(t, o, s) for t, o, s in walk_resync(d)]


def pages_of(d):
    """按块序取每个 XMED 的一页文本（框内换行已合并）。"""
    ch = chunks_of(d)
    found = {off: sz for tag, off, sz in ch if tag == 'XMED'}
    out = []
    for off in sorted(found):
        sz = found[off]
        body = d[off + 8:off + 8 + sz]
        parts = []
        started = False
        for seg in body.split(b'\x0d'):
            # 一段 = 一行显示文字 +（可能）其后的样式表；只取「首个 C0 控制字节之前」的干净前缀
            cut = len(seg)
            for i, b in enumerate(seg):
                if b < 0x20 or b == 0x7f:
                    cut = i
                    break
            t = ''
            if cut:
                # 坏字节只丢那一个字符、**不截断整段**（本作有「いっ<坏字节>･」」这类源缺陷，
                # 截断会把收尾的 」 一起丢掉 ⇒ 引号不平衡）
                t = seg[:cut].decode('cp932', 'replace').replace('\ufffd', '')
            if not started:
                # 头段是 ASCII 样式表；跳过直到第一段像正文的
                if t and _plausible(t):
                    started = True
                    parts.append(t.strip('\u3000 ').strip())
                continue
            # 正文行是**连续的**：出现空段 / 不像正文 ⇒ 已到样式表区，收尾
            if not _plausible_next(t):
                break
            parts.append(t.strip('\u3000 ').strip())
        page = ''.join(p for p in parts if p)
        out.append(page)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    only = None
    drop = set()
    for a in sys.argv[3:]:
        if a.startswith('--files'):
            v = a.split('=', 1)[1] if '=' in a else ''
            only = [x.strip().lower() for x in v.split(',') if x.strip()]
        elif a.startswith('--exclude'):
            v = a.split('=', 1)[1] if '=' in a else ''
            drop |= {x.strip().lower() for x in v.split(',') if x.strip()}
    names = []
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith(('.dir', '.cst')):
            continue
        if f.lower() in drop:
            continue
        if only and f.lower() not in only:
            continue
        names.append(f)

    total = 0
    lines = []
    for f in names:
        d = open(os.path.join(src, f), 'rb').read()
        ps = pages_of(d)
        keep = [p for p in ps if p]
        lines.extend(keep)
        total += len(keep)
        print('%-16s 文本成员 %-4d 有字 %-4d 字 %d' % (f, len(ps), len(keep), sum(map(len, keep))),
              file=sys.stderr)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')
    print('文件 %d｜正文行 %d｜字 %d｜字节 %d' % (len(names), total, sum(map(len, lines)),
                                          os.path.getsize(dst)), file=sys.stderr)


if __name__ == '__main__':
    main()
