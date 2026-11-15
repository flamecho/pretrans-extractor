#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Director 8（XFIR 小端）text cast member（XMED）→ 一成员一框的正文文本。

与 `director_xmed_text.py` 的区别（同名 chunk、两种格式，别混）：

  * `director_xmed_text.py` —— **RIFX 大端** + XMED 体是**纯文本**（D.Zone 2002），
    以 C0 控制字节截断、`0x0D` 合并。
  * 本工具 —— **XFIR 小端** + XMED 体是 **Director 8 的 text 序列化**
    （`ecape` 2001/ESCAPE、D-Zone 之后的同族形态）：
    `\\x00` + `<hex 长度>,` + `<n 字节 cp932 文本>`；
    每个成员**恰好一条**这样的文本 run（实测 22,795/22,795），
    前面是字体表（`40,ＭＳ Ｐゴシック` padded 到 64 字节，含 `\\x00`）与样式 run。

判据（L1，本作实测）
  * 一个 XMED ＝ 一个 cast member ＝ 一屏（一次点击）：Lingo `NextFrame` 的行为是
    `on mouseUp → go(the frame + 1)`，`FrameWait` 用 `go(the frame)` 停等；score 逐帧换成员。
  * 成员内 `\\r` ＝ 框内换行（作者手断，段宽中位 13、段数 1..4 占 99.2%）⇒ 合并。
  * cast 成员顺序 ＝ 剧情顺序（含所有分支，不追求单线）。
  * 名牌：`\\u3000*名字\\u3000*`（固定 6 字位居中）的独立成员 ⇒ 剔除（独立名字窗）。
  * 选项：一个成员内含 N 段、每段一条选项 ⇒ 拆成 N 行（口径「选项一行一条」）。

用法
  python scripts/director_d8_text.py <含 NN_TXn.dir 的目录> --out out.txt
        [--options opts.txt] [--drop drop.txt] [--name-pad 8] [--stat]
"""
import argparse
import os
import re
import struct
import sys

REC = re.compile(rb'\x00([0-9A-Fa-f]{1,8}),')
NAME = re.compile(r'^[\u3000]+\S{1,5}[\u3000]+$')


# ---------- 容器 ----------

def _mmap_le(d):
    o = d.find(b'pamm')
    if o < 0:
        return None
    body = o + 8
    if body + 24 > len(d):
        return None
    hl, el, cnt = struct.unpack_from('<HHI', d, body)
    if not (el == 20 and 24 <= hl <= 64 and 0 < cnt < 300000):
        return None
    out, st = [], body + hl
    for k in range(cnt):
        p = st + k * el
        if p + el > len(d):
            break
        cc = d[p:p + 4][::-1].decode('latin1')
        ln, off, _fl = struct.unpack_from('<III', d, p + 4)
        if off + 8 > len(d):
            continue
        out.append((cc, off, ln))
    return out


def _mmap_be(d):
    o = d.find(b'mmap')
    if o < 0:
        return None
    body = o + 8
    if body + 24 > len(d):
        return None
    hl, el, cnt = struct.unpack_from('>HHI', d, body)
    if not (el == 20 and 24 <= hl <= 64 and 0 < cnt < 200000):
        return None
    out, st = [], body + hl
    for k in range(cnt):
        p = st + k * el
        if p + el > len(d):
            break
        cc = d[p:p + 4].decode('latin1')
        ln, off, _fl = struct.unpack_from('>III', d, p + 4)
        if off + 8 > len(d):
            continue
        out.append((cc, off, ln))
    return out


def chunks_of(d):
    """按文件头判字节序：`XFIR` ＝ 小端（Director 在 x86 上的写法），`RIFX` ＝ 大端。"""
    if d[:4] == b'XFIR':
        return _mmap_le(d) or []
    return _mmap_be(d) or []


# ---------- 文本 ----------

def xmed_text(body):
    """XMED → 文本（一个成员只有一条正文 run；字体表条目含 \\x00 被跳过）。"""
    for m in REC.finditer(body):
        n = int(m.group(1), 16)
        p = m.end()
        seg = body[p:p + n]
        if n == 0 or len(seg) < n or b'\x00' in seg:
            continue
        try:
            return seg.decode('cp932')
        except UnicodeDecodeError:
            continue
    return None


def merge(t):
    """框内换行合并：`\\r` 去掉；续行行首全角空格＝缩进（排版），一并去掉；
    段内（非行首）全角空格保留（原文空格）。"""
    parts = t.split('\r')
    out = [parts[0]]
    for seg in parts[1:]:
        out.append(seg.lstrip('\u3000'))
    return ''.join(out).strip('\u3000')


def split_quotes(t):
    """一屏多句：成员里**每一段都是完整的 `「…」`**⇒ 返回各段（用于双版）。

    ★ 判据是结构的（段内首尾各是「」），不是字宽/语气：
      被折行的长台词只有**首段**以「开头、**末段**以」收尾，中间段两头都没有，
      所以不会误命中（例：`「今日、うちに来てくれないと、薫彦と\r　オフィスでした…」`）。
    """
    parts = [x for x in t.split('\r') if x.strip()]
    if len(parts) < 2:
        return None
    if all(x.startswith('\u300c') and x.endswith('\u300d') for x in parts):
        return parts
    return None


def split_option(t):
    """选项屏 → 每段一条（空段/纯空白段丢弃）。"""
    return [x.strip('\u3000 ') for x in t.split('\r') if x.strip('\u3000 ')]


# ---------- 主流程 ----------

def chapters(root):
    files = {}
    for fn in os.listdir(root):
        if not fn.lower().endswith('.dir'):
            continue
        m = re.match(r'^(\d+)_TX(\d)$', fn[:-4])
        if m:
            files[(int(m.group(1)), int(m.group(2)))] = os.path.join(root, fn)
    return [(f'{k[0]:02d}_TX{k[1]}', v) for k, v in sorted(files.items())]


def read_list(path):
    if not path or not os.path.exists(path):
        return set()
    out = set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            s = line.split('#')[0].strip()
            if s:
                out.add(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', help='含 NN_TXn.dir 的目录（ProjectorRays 解保护后的 .dir）')
    ap.add_argument('--out', required=True)
    ap.add_argument('--options', help='选项屏清单，每行 `NN_TXn:成员序号`')
    ap.add_argument('--drop', help='整条剔除清单（多行名牌等），同样格式')
    ap.add_argument('--split-quotes', action='store_true',
                    help='一屏多句（每段都是完整「…」）出双版：先列各段行、再列合并行')
    ap.add_argument('--stat', action='store_true')
    a = ap.parse_args()

    opts = read_list(a.options)
    drop = read_list(a.drop)
    lines, st = [], {'member': 0, 'name': 0, 'drop': 0, 'opt': 0, 'optline': 0, 'none': 0,
                      'dual': 0, 'dual_line': 0}

    for tag, path in chapters(a.root):
        d = open(path, 'rb').read()
        i = 0
        for cc, off, sz in chunks_of(d):
            if cc != 'XMED':
                continue
            key = f'{tag}:{i}'
            i += 1
            st['member'] += 1
            t = xmed_text(d[off + 8:off + 8 + sz])
            if t is None:
                st['none'] += 1
                continue
            if key in drop:
                st['drop'] += 1
                continue
            if NAME.match(t) and len(t) <= 8:
                st['name'] += 1
                continue
            if key in opts:
                segs = split_option(t)
                st['opt'] += 1
                st['optline'] += len(segs)
                lines.extend(segs)
                continue
            if a.split_quotes:
                segs = split_quotes(t)
                if segs:
                    st['dual'] += 1
                    st['dual_line'] += len(segs)
                    lines.extend(x.strip('\u3000') for x in segs)   # 先列段行
                    lines.append(merge(t))                           # 再列合并行
                    continue
            lines.append(merge(t))

    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    if a.stat:
        print(st)
        print('输出', len(lines), '行', sum(len(x) for x in lines), '字',
              '最长', max(len(x) for x in lines))
    else:
        print(st, len(lines), '行')


if __name__ == '__main__':
    main()
