#!/usr/bin/env python3
"""tenis2_extract.py —— テニスの王子様 SWEAT & TEARS 2 (PS2) 剧本提取。

链路：ISO9660 → SCRIPT.BIN/SCRIPT.HD（HD=u32 长度表，0x800 扇区对齐）
      → 各条目 SCPT 脚本（5 字节定长指令：op + u32）
      → op 0x06 压栈字符串 / op 0x19 调用（cid 0x0000=メッセージ, 0x3021=名札,
        0x3020=選択確定, 0x3020 前一条消息即选项列表）
用法：python scripts/tenis2_extract.py <iso> <out.txt>
"""
import struct
import sys
import os

SECTOR = 0x800


def load_iso_index(iso_path):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from iso9660 import ISO
    iso = ISO(iso_path)
    e = iso.find('SCRIPT.BIN')
    hde = iso.find('SCRIPT.HD')
    base = e['lba'] * 2048
    hd = iso.read_file(hde)
    sizes = struct.unpack('<%dI' % (len(hd) // 4), hd)
    offs = []
    p = 0
    for s in sizes:
        offs.append(p)
        p += (s + SECTOR - 1) // SECTOR * SECTOR
    assert p == e['size'], (p, e['size'])
    return iso, base, sizes, offs


def read_files(iso, base, sizes, offs):
    """yield (name, data) for every SCPT entry"""
    iso.f.seek(base)
    first = iso.f.read(sizes[0])
    names = [l for l in first.decode('cp932', errors='replace').split('\r\n') if l.strip()]
    assert len(names) == len(sizes), (len(names), len(sizes))
    for i, nm in enumerate(names):
        if not nm.upper().endswith('.BIN'):
            continue
        iso.f.seek(base + offs[i])
        head = iso.f.read(8)
        if head[:4] != b'SCPT':
            continue
        data = head + iso.f.read(sizes[i] - 8)
        yield nm, data


def route_of(name):
    fn = name.split('\\')[-1].upper()
    base = fn.replace('Ｇ', 'G')
    if base.startswith('CON_') or base.startswith('AGING'):
        return 'C'
    if base.startswith('ES'):
        return 'C'
    if len(base) > 4 and base[2:5].isdigit():
        c = base[5]
        if c == 'B':
            return 'B'
        if c == 'G':
            return 'G'
        if c == 'X':
            return 'C'
    if base.startswith('EVXXX'):
        if base[5] == 'B':
            return 'B'
        if base[5] == 'G':
            return 'G'
    return None


def read_script(data):
    """→ list of ('msg'|'choice', text) / ('name', text)"""
    code_off, code_len = struct.unpack('<II', data[8:16])
    n = code_len // 5
    items = []
    for k in range(n - 1):
        q = code_off + 5 * k
        op = data[q]
        if op != 0x06:
            continue
        nxt = data[q + 5]
        if nxt != 0x19:
            continue
        cid = struct.unpack('<I', data[q + 6:q + 10])[0]
        if cid not in (0x0000, 0x3021):
            continue
        a = struct.unpack('<I', data[q + 1:q + 5])[0]
        if a < code_off + code_len or a >= len(data):
            continue
        e = data.find(b'\x00', a)
        if e < 0:
            continue
        try:
            t = data[a:e].decode('cp932')
        except UnicodeDecodeError:
            continue
        if cid == 0x3021:
            items.append(('name', t))
            continue
        # 判定选项：后续指令里（遇到下一条 0x06 之前）出现 19 3020 / 19 3022（選択確定）
        is_choice = False
        for j in range(k + 2, min(n - 1, k + 8)):
            q2 = code_off + 5 * j
            if data[q2] == 0x06:
                break
            if data[q2] == 0x19 and struct.unpack('<I', data[q2 + 1:q2 + 5])[0] in (0x3020, 0x3022):
                is_choice = True
                break
        items.append(('choice' if is_choice else 'msg', t))
    return items


CHAR_MACRO = {}
for _n in ('桃城', '河村', '海堂', '手塚', '大石', '不二', '菊丸', '乾', '越前', '跡部',
           '樺地', '観月', '裕太', '橘', '亜久津', '神尾', '伊武', '壇', '竜崎', '小坂田',
           '堀尾', '加藤', '水野', '赤澤', '柳沢', '荒井', '池田', '堂本', '真田', '切原',
           '千石', '木更津', '佐々部', '榊'):
    CHAR_MACRO['<' + _n + '>'] = _n

PROTAG = {'B': ('赤月', '隼人'), 'G': ('赤月', '巴'), 'C': ('赤月', '')}

# <綽名> 默认绰号：SLPM_653.70 0x142620 起 8 B/槽「命名初始值表」
# (赤月 / 隼人 / ハヤト / 巴 / モエりん) = 姓・名B・綽名B・名G・綽名G；
# 同表在 0x140428 重复一次（同序同值），姊妹作 RUSH & DREAM 的 SLPM_658.77
# 0x160600 起为 (赤月 / 巴 / モエりん) 三槽，可证第 3 槽即綽名。
NICK = {'B': 'ハヤト', 'G': 'モエりん'}


def strip_codes(t):
    for m in ('$0', '$1', '$2', '$3', '$4', '$5', '$6', '$7', '$8', '$9',
              '$q', '$Q', '$a', '$b', '$c', '$d', '$e', '$f'):
        t = t.replace(m, '')
    return t


def replace_macros(t, route):
    for k, v in CHAR_MACRO.items():
        t = t.replace(k, v)
    last, first = PROTAG[route]
    t = t.replace('<lastname>', last).replace('<苗字>', last)
    t = t.replace('<名前>', first if first else '〔未解析〕')
    t = t.replace('<綽名>', NICK.get(route, '〔未解析〕'))
    return t


def clean(t, route):
    """正文：剥富文本→换宏→合并同框软换行"""
    t = replace_macros(strip_codes(t), route)
    return t.replace('\n', '').rstrip('　 ').strip('\ufeff')


def main():
    iso_path, out_path = sys.argv[1], sys.argv[2]
    iso, base, sizes, offs = load_iso_index(iso_path)

    files = []
    for nm, data in read_files(iso, base, sizes, offs):
        r = route_of(nm)
        if r is None:
            continue
        items = read_script(data)
        msgs = [t for k, t in items if k in ('msg', 'choice')]
        if not msgs:
            continue
        files.append((nm, r, items, len(msgs)))

    order = {'B': 0, 'C': 1, 'G': 2}

    def key(f):
        nm = f[0].split('\\')[-1].upper().replace('Ｇ', 'G')
        return (order[f[1]], nm)

    files.sort(key=key)

    seen = set()
    lines = []
    stat = {'msg': 0, 'choice': 0, 'file': 0, 'dupfile': 0}
    for nm, r, items, cnt in files:
        sig = tuple(t for k, t in items if k in ('msg', 'choice'))
        if sig in seen:
            stat['dupfile'] += 1
            continue
        seen.add(sig)
        stat['file'] += 1
        for kind, t in items:
            if kind == 'name':
                continue
            if kind == 'choice':
                for part in replace_macros(strip_codes(t), r).split('\n'):
                    part = part.strip('　 ').strip()
                    if part:
                        lines.append(part)
                        stat['choice'] += 1
            else:
                s = clean(t, r)
                if s:
                    lines.append(s)
                    stat['msg'] += 1

    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('files', stat['file'], 'dup dropped', stat['dupfile'],
          'msg', stat['msg'], 'choice', stat['choice'], 'lines', len(lines))


if __name__ == '__main__':
    main()
