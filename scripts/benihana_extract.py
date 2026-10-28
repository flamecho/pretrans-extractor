# -*- coding: utf-8 -*-
r"""越えざるは紅い花 after disc～綾なす未来～（YU-RIS / YPF v500）全文本提取。

链路：
  pac/scenario.ypf → YPF 索引（[u32 crc][name 加密][00 01][u32 usize][u32 csize][u32 off][u32 hash]）
                   → zlib 条目 → **明文 cp932 场景源码脚本**（#esuta1…/#uru7 共 37 本）
  → 逐行：`\\命令` 行丢弃；`//` 注释、`#ラベル`、`/* */` 块注释丢弃
  → 正文行 = 一次点击（1 源行 = 1 框 = 1 点击，L0 源语法）
  → 行内 `\\r` / `\\R` = 框内手动换行（同框软换行）⇒ 删除后拼接
  → `\\TXSG(123)` = 主角名变量 ⇒ 就地替换（\\INPUT.G 默认值「ナァラ」）
  → `\\SEL(a, b)` = 选项，按顶层逗号拆分逐条成行
  → `\\c` 77 处全部紧跟 \BG 演出（清框），无一处紧跟正文行 ⇒ 不存在「同点击二义指令」⇒ 单版

用法：python benihana_extract.py <工作目录> [主角名]
"""
import struct
import sys
import os
import zlib

NAME_VAR_123 = '\\TXSG(123)'
RUBY = __import__('re').compile(r'≪([^≪≫／]+)／[^≪≫]*≫')   # ≪親文字／ルビ≫ → 親文字


def unpack_ypf(path):
    """按数据偏移返回 [(off, raw)]（记录自定界：[00 01] 定界 + 三重校验）。"""
    d = open(path, 'rb').read()
    assert d[:4] == b'YPF\x00', 'not YPF'
    count = struct.unpack_from('<I', d, 8)[0]
    doff = struct.unpack_from('<I', d, 12)[0]
    out, p = [], 0x20
    while p + 30 < doff:
        e = d.find(b'\x00\x01', p + 5, doff)
        if e < 0:
            break
        us, cs, off, _ = struct.unpack_from('<IIII', d, e + 2)
        if not (off >= doff and off + cs <= len(d) and cs > 0 and us >= cs):
            p = e + 2
            continue
        blob = d[off:off + cs]
        try:
            raw = zlib.decompress(blob)
        except zlib.error:
            raw = blob[:us]
        out.append((off, raw))
        p = e + 22
    out.sort()
    # 同族 ysbin.ypf 头写 count、实际少 1 条（末条结束位 == 数据区起点）；scenario 应全等
    assert count - 1 <= len(out) <= count, (len(out), count)
    return out


def split_sel(body):
    """\\SEL(...) 的实参按顶层逗号拆分（引号/括号内逗号不拆）。"""
    parts, buf, d1, d2 = [], [], 0, 0
    for ch in body:
        if ch in '「『':
            d1 += 1
        elif ch in '」』':
            d1 -= 1
        elif ch in '（(':
            d2 += 1
        elif ch in '）)':
            d2 -= 1
        if ch == ',' and d1 == 0 and d2 == 0:
            parts.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append(''.join(buf))
    return [p.strip() for p in parts if p.strip()]


def extract_one(text, name):
    lines = text.split('\r\n')
    res, stat = [], {'text': 0, 'opt': 0, 'name': 0, 'softwrap': 0, 'ruby': 0}
    in_block = False
    for ln in lines:
        s = ln.strip()
        if in_block:
            if '*/' in s:
                in_block = False
            continue
        if s.startswith('/*'):
            if '*/' not in s:
                in_block = True
            continue
        if not s or s.startswith('//') or s.startswith('#'):
            continue
        if s.startswith('\\'):
            if s.startswith('\\SEL('):
                body = s[s.index('(') + 1:]
                body = body[:body.rfind(')')] if ')' in body else body
                for opt in split_sel(body):
                    res.append(opt)
                    stat['opt'] += 1
            continue
        t = s
        if NAME_VAR_123 in t:
            stat['name'] += t.count(NAME_VAR_123)
            t = t.replace(NAME_VAR_123, name)
        if '≪' in t:
            stat['ruby'] += len(RUBY.findall(t))
            t = RUBY.sub(r'\1', t)
        for tok in ('\\r', '\\R'):
            if tok in t:
                stat['softwrap'] += t.count(tok)
                t = t.replace(tok, '')
        t = t.strip()
        if t:
            res.append(t)
            stat['text'] += 1
    return res, stat


def main():
    work = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else 'ナァラ'
    ents = unpack_ypf(os.path.join(work, 'game', 'app', 'pac', 'scenario.ypf'))
    by_off = {off: raw for off, raw in ents}

    SKIP = {
        141098: 'リプレイ用（回想一覧・\\RP.END のみ、正文 0）',
        195896: '#SCENARIO_START_RELEASE（起動ロゴ）',
        230796: '#SCENARIO_MAIN（テストテキスト・debug）',
    }

    all_lines, stat = [], {'text': 0, 'opt': 0, 'name': 0, 'softwrap': 0, 'ruby': 0}
    per_file = []

    # 1) #op_senntaku：开局（名前入力→プロローグ 2 行→キャラ選択 2 画面）——正文与选项，置首
    pro, st = extract_one(by_off[140280].decode('cp932', 'replace'), name)
    for k in stat:
        stat[k] += st[k]
    all_lines.extend(pro)
    per_file.append(('#op_senntaku', len(pro), 2175))

    for off, raw in ents:
        if off in SKIP or off == 140280:
            continue
        head = raw.decode('cp932', 'replace').split('\r\n')[0].strip() or '(no-label)'
        ls, st = extract_one(raw.decode('cp932', 'replace'), name)
        for k in stat:
            stat[k] += st[k]
        all_lines.extend(ls)
        per_file.append((head, len(ls), len(raw)))

    print('ypf entries', len(ents))
    for h, n, sz in per_file:
        print('  %-18s lines=%-5d bytes=%d' % (h[:18], n, sz))
    print('skip:', SKIP)
    print('stat', stat)
    print('total', len(all_lines))

    # 互斥分支同段重复：分支 a 的末句与分支 b 的唯一句逐字相同且相邻（naran1_3a/3b）
    # ⇒ 同一点击的多版本正文，取一（pitfalls B1-10）；只吃掉完全相同的相邻长行
    dedup, dropped = [], 0
    for l in all_lines:
        if dedup and l == dedup[-1] and len(l) >= 8:
            dropped += 1
            continue
        dedup.append(l)
    all_lines = dedup
    print('分支重复取一', dropped)

    out = os.path.join(work, '_out.txt')
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf' + ('\n'.join(all_lines) + '\n').encode('utf-8'))
    print('wrote', out)


if __name__ == '__main__':
    main()
