# -*- coding: utf-8 -*-
"""[JP]Angel Knight (PC / SaiSys / Ferret-ZUI) 正文提取

用法：
    python scripts/angelknight_ssb.py --ssb <SCRIPT/Data.ssb> --out <成品.txt>

判据链（全部代码级，无内容猜测）：
  L0-1  Data.ssb 整体 XOR 0xAA          （0xAA→0x00 = NUL 补白；判别见 --check-key）
  L0-2  记录 = NUL 自定界串，起点 4 字节对齐
  L0-3  池文法 = [名札][正文][正文副本]  （正文恒定成对，相邻字节全等）
  L0-4  \\r(0x0D) 属排版层：SaiSys.bin @0x591a4 的排版分发表里 0x0D 走「递归下一行布局」；
        首行缩进 0/3960 vs 续行缩进 369/1244 ⇒ 框内换行，合并
  L1    正文段 = #781..#12557（段前全为素材标签+引擎报错+CG 回想标题+体验版提示；
        段后全为 pper/pcgpg/ptitle 标签与 ▼菜单／百分比／デバッグ UI）
"""
import argparse

KEY = 0xAA
SPAN = (781, 12558)      # 正文段记录区间 [a, z)
NAME_MAX = 24            # 名札字节上限（实测最长 12B，取 24 留余量）
INDENT = '\u3000'        # 全角空格 = 段首缩进


def is_text(b):
    """结构判据：含 ≥0x80 字节 = cp932 文本；纯 ASCII = 素材／UI／脚本标签"""
    return any(x >= 0x80 for x in b)


def records(data, key=KEY):
    """NUL 自定界切分（先整体 XOR）"""
    d = bytes(b ^ key for b in data)
    out, i, n = [], 0, len(d)
    while i < n:
        if d[i]:
            j = i
            while j < n and d[j]:
                j += 1
            out.append(d[i:j])
            i = j
        else:
            i += 1
    return out


def is_name(b):
    """名札：短、以 \\r 结尾（独立名字窗的行）、不以「起（排除台词）"""
    return len(b) <= NAME_MAX and b.endswith(b'\r') and not b.startswith(b'\x81\x75')


def merge(b):
    """把一次点击内的 \\r 分段合并成一行；续行去掉段首全角缩进"""
    parts = b.decode('cp932').split('\r')
    buf = [parts[0]]
    for ln in parts[1:]:
        ln = ln.lstrip(INDENT + ' ')
        if ln:
            buf.append(ln)
    return ''.join(buf).strip(INDENT + ' ')


def extract(data, span=SPAN):
    recs = records(data)
    a, z = span
    lines, names, st = [], {}, {'text': 0, 'option': 0, 'name': 0, 'copy': 0, 'tag': 0}

    def bump(nm):
        names[nm] = names.get(nm, 0) + 1

    k = a
    while k < z:
        b = recs[k]
        if not is_text(b):                            # ① 素材／UI／脚本标签
            st['tag'] += 1
            k += 1
            continue
        if k + 1 < z and recs[k] == recs[k + 1]:      # ② 正文（成对，取首份）
            lines.append(merge(b))
            st['text'] += 1
            k += 2
            continue
        if recs[k - 1] == b:                          # ③ 孤立副本（已取过）
            st['copy'] += 1
            k += 1
            continue
        nxt_pair = (k + 2 < z and recs[k + 1] == recs[k + 2] and is_text(recs[k + 1]))
        if is_name(b) and (nxt_pair or (k + 1 < z and is_name(recs[k + 1]))):
            bump(merge(b))                            # ④ 名札（独立名字窗 ⇒ 剔除）
            st['name'] += 1
            k += 1
            continue
        lines.append(merge(b))                        # ⑤ 选项／群衆の声（单份）
        st['option'] += 1
        k += 1
    return lines, names, st, len(recs)


def check_key(data):
    """二选一判别：假名产率 + cp932 非法序列数（不做穷举）"""
    import re
    kana = re.compile(r'[\u3041-\u309f\u30a0-\u30ff]')
    kanji = re.compile(r'[\u4e00-\u9fff]')
    print('%-6s %-8s %-8s %-8s %s' % ('key', '假名', '汉字', 'cp932非法', '抽样'))
    for k in (0x8A, 0xAA):
        d = bytes(b ^ k for b in data)
        bad = 0
        for i in range(0, len(d) - 1):
            if d[i] >= 0x80:
                try:
                    d[i:i + 2].decode('cp932')
                except UnicodeDecodeError:
                    bad += 1
        s = d.decode('cp932', 'ignore')
        print('0x%02X   %-8d %-8d %-8d %r'
              % (k, len(kana.findall(s)), len(kanji.findall(s)), bad,
                 s[0x50:0x62]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ssb', required=True, help='光盘上的 SCRIPT/Data.ssb')
    ap.add_argument('--out', help='成品 txt（UTF-8 BOM / 纯 LF）')
    ap.add_argument('--span', default='%d,%d' % SPAN, help='正文段记录区间 a,z')
    ap.add_argument('--check-key', action='store_true', help='只打印 XOR 键判别表')
    a = ap.parse_args()

    data = open(a.ssb, 'rb').read()
    print('源 %s  %d B' % (a.ssb, len(data)))
    if a.check_key:
        check_key(data)
        return

    span = tuple(int(x) for x in a.span.split(','))
    lines, names, st, nrec = extract(data, span)
    print('总记录 %d / 段 %d..%d' % (nrec, span[0], span[1] - 1))
    print('text=%d option=%d name=%d copy=%d tag=%d'
          % (st['text'], st['option'], st['name'], st['copy'], st['tag']))
    print('名札 %d 种：%s' % (len(names),
                            sorted(names.items(), key=lambda x: -x[1])[:10]))
    print('行 %d / 字 %d' % (len(lines), sum(len(x) for x in lines)))

    if a.out:
        body = '\n'.join(lines) + '\n'
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write(body)
        print('写出 %s  %d B' % (a.out, len(body.encode('utf-8'))))


if __name__ == '__main__':
    main()
