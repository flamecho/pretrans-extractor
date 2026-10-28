#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""十三支演義 偃月三国伝1・2 正文提取（AdvScript / MessagePack 容器）。

⚠ 未交付：本工具只覆盖 `Contents` 字段（280 bundle 出 507 行，约 2%）；正文大头在
   `Elements` 子树的自定义字节码里，需要 `AdvScriptElementFormatter.Serialize` 的 tag/len
   编码宽度才能解。详见 `解析报告/[NS-JP]十三支演義 偃月三国伝1・2 for Nintendo Switch_解析报告.md`。

★ 实测结构（2026-10-26）：
  bundle(UnityFS) → 唯一 TextAsset(`m_Script`) → **MessagePack**：
    顶层 `dc 00 22` = array(N)：元素是「1 个 ExtType(98) + N-1 个 bytes 块」
    各块直接拼接（**不要**去 2 字节头，块首 `F0/F1/F4` 是 msgpack 负 fixint 操作码）
    块内是 `{Functions: [ {Id, Type, Name, Contents, Elem} … ]}`
      · `Contents` = **数组**，元素是带控制码的日文串（正文就在这里）
      · `Elem`     = 自定义字节码（`AdvScriptElementFormatter` 写的），**不用解**
  控制码夹在串内：u16 op + u16 param（如 `03 00 f2 12`），按 UTF-8 合法性跳过。

用法: python scripts/jusanshi_dialog.py <advscripts_bundle目录> <out.tsv> [--final 成品.txt]
"""
import argparse
import glob
import io
import os
import re
import sys

import msgpack
import UnityPy

JP = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')
CONTENTS = b'\xa8Contents'


def char_len(b, i):
    c = b[i]
    if c < 0x80:
        return 1
    if 0xC2 <= c <= 0xDF:
        return 2
    if 0xE0 <= c <= 0xEF:
        return 3
    if 0xF0 <= c <= 0xF4:
        return 4
    return 0


def clean(b):
    """去掉串内 2+2 字节控制码，保留正文。"""
    out, i, n = [], 0, len(b)
    while i < n:
        L = char_len(b, i)
        if L and i + L <= n:
            try:
                out.append(b[i:i + L].decode('utf-8'))
                i += L
                continue
            except Exception:
                pass
        if i + 4 < n and char_len(b, i + 4):
            i += 4                      # u16 op + u16 param
        else:
            i += 2
    return ''.join(out)


def textasset_bytes(bundle):
    env = UnityPy.load(bundle)
    for o in env.objects:
        if o.type.name == 'TextAsset':
            s = o.read().m_Script
            return s.encode('utf-8', 'surrogateescape') if isinstance(s, str) else s
    return None


def lines_of(blob):
    res = []
    for m in re.finditer(re.escape(CONTENTS), blob):
        u = msgpack.Unpacker(io.BytesIO(blob[m.end():]), raw=True, strict_map_key=False)
        try:
            val = next(u)
        except Exception:
            continue
        if not isinstance(val, list):
            continue
        t = ''.join(clean(x) for x in val if isinstance(x, (bytes, bytearray)))
        t = re.sub(r'[A-Za-z_]{2,}$', '', t).strip()      # 尾巴粘连的 ASCII 资源名
        if t and JP.search(t):
            res.append(t)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--final')
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.src, '*advscripts*.bundle')),
                   key=lambda p: (0 if 'jyuza1' in p else 1, p))
    rows, nerr = [], 0
    for p in files:
        name = os.path.basename(p).split('_assets_all')[0].replace('advscripts-', '')
        try:
            b = textasset_bytes(p)
            v = msgpack.unpackb(b, raw=True, strict_map_key=False)
            blob = b''.join(x.data if isinstance(x, msgpack.ExtType) else x
                            for x in v if isinstance(x, (bytes, bytearray, msgpack.ExtType)))
            ls = lines_of(blob)
        except Exception:
            nerr += 1
            continue
        for k, t in enumerate(ls, 1):
            rows.append((name, k, t))

    open(a.out, 'w', encoding='utf-8').write('\n'.join('%s\t%d\t%s' % r for r in rows))
    print('bundle %d（失败 %d）  行 %d' % (len(files), nerr, len(rows)))
    if a.final:
        with open(a.final, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(r[2] for r in rows))
        print('成品 -> %s  %d 行' % (a.final, len(rows)))
    for r in rows[:3]:
        print('  ', r[0], r[2][:60])


if __name__ == '__main__':
    main()
