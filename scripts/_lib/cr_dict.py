# -*- coding: utf-8 -*-
"""SYSTEM.cpk → DATABASE/dbDictionary_0{1,2}.gbin —— Code:Realize 用語辞典

## 结构（L0，本作自证）
  表 = **32 B/行** `[u64 gid][u64 名称off][u64 名称域宽(=0x46)][u64 说明off]`，表从 0 起
  表尾另有 **32 B 页脚**（u16 打包的 `0x0002 0001 0000 0002 …`，非条目）⇒ 行区间校验会判它不合法而丢弃
  字符串区 base = 第一个日文串偏移（本作 0x1440 = 161×32 + 32 页脚），自证：row0 的名称off = 0
  名称区间 = `[名称off, 说明off)`（末尾 　 + NUL 补齐）；说明区间 = `[说明off, 下一行名称off)`
  说明内 `#n` = **显示换行**（说明框定宽 ~10 字）⇒ 合并为一行

## 输出格式（本工程口径）
  一条一行 `【术语】说明`
"""
import re
import struct


def _is_jp_start(d, o):
    return 0xE3 <= d[o] <= 0xE9 and all(0x80 <= d[o + i] <= 0xBF for i in (1, 2))


def parse(path):
    d = open(path, 'rb').read()
    base = None
    for m in re.finditer(rb'(?:[\xe3-\xe9][\x80-\xbf]{2}){4,}', d):
        base = m.start()
        break
    assert base, '字符串区起点未定位'
    n = base // 32
    rows = [struct.unpack_from('<4Q', d, i * 32) for i in range(n)]
    while rows and not (rows[-1][1] < rows[-1][3] <= len(d) - base):
        rows.pop()
    bad = [i for i in range(len(rows) - 1)
           if not rows[i][1] < rows[i][3] <= rows[i + 1][1]]
    assert not bad, '行区间不单调: %s' % bad[:5]
    out = []
    for i, (gid, w, wl, dsc) in enumerate(rows):
        end = rows[i + 1][1] if i + 1 < len(rows) else len(d) - base
        name = d[base + w: base + dsc].split(b'\x00')[0].decode('utf-8')
        name = name.replace('\u3000', '').strip()
        desc = d[base + dsc: base + end].split(b'\x00')[0].decode('utf-8')
        desc = re.sub(r'#n', '', desc)
        desc = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', desc)
        desc = desc.replace('\u3000', ' ').replace('\x00', '').strip()
        if name and desc:
            out.append('【%s】%s' % (name, desc))
    return out, base, len(rows)
