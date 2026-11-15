# -*- coding: utf-8 -*-
"""Ren'Py（RPA-3.0 + .rpy 明文源码）文本提取驱动 —— [PC-JP]神立ノ雨、鬼ノ唄。

链路：RAR5(otoame) → game/archive.rpa（RPA-3.0，key 0x42424242）→ 成员 .rpy（明文 Ren'Py 脚本）
      → 逐语句提取 say / menu 选项 / centered 上屏 → 剥 `{tag}` / `[name]` 回填 → 成行。

L0 判据（引擎语义）：
  · Ren'Py 每条 say 语句＝一次点击＝一个文本框（说话人名在独立 namebox ⇒ 剔除，只留正文）。
  · `{p}`（点击继续）/ `{w}`（等待点击）在一句内 ⇒ 同框多次点击 ⇒ 出双版（本作 0 处）。
  · 跨语句「开口不闭 / 括号开口不闭」⇒ 作者把一句拆到多框 ⇒ 出双版（本作 0 组）。

用法：
    python scripts/kamidachi_extract.py --rpa "<game>/archive.rpa" --out "提取结果/[PC-JP]神立ノ雨、鬼ノ唄.txt" --verify
    python scripts/kamidachi_extract.py --rpa "<game>/archive.rpa" --out "..." --name ヒカリ
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
import zlib
import pickle

# 流程顺序（由 script.rpy start1 → s00 → s01 → s02 → s03 → bunki 的跳转，
# 以及 bunki 两条菜单分支的选项顺序得出；endroll 收尾）
FLOW = ['script.rpy', 's00.rpy', 's01.rpy', 's02.rpy', 's03.rpy', 'bunki.rpy',
        'end2.rpy', 'end6.rpy', 'end3.rpy', 'end1.rpy', 'end4.rpy', 'end5.rpy', 'endroll.rpy']

CHAR_DEF = re.compile(r"define\s+(\w+)\s*=\s*Character\(")
TAG = re.compile(r'\{[^{}]*\}')
CLICK_P = re.compile(r'\{p\}')
CLICK_W = re.compile(r'\{w\}')


def extract_rpa(path, out_dir, suffix=('.rpy',)):
    """RPA-3.0：header `RPA-3.0 <off16> <key8>`，索引＝zlib(pickle(dict))；
    条目 chunks=(off, dlen, prefix)，off/dlen 均 XOR key，正文＝prefix + data。"""
    with open(path, 'rb') as f:
        hdr = f.readline().decode('ascii')
        off = int(hdr[8:24], 16)
        key = int(hdr[25:33], 16)
        f.seek(off)
        index = pickle.loads(zlib.decompress(f.read()))
        n = 0
        for name, chunks in index.items():
            if not name.lower().endswith(suffix):
                continue
            parts = []
            for ro, rd, prefix in chunks:
                f.seek(ro ^ key)
                parts.append(prefix.encode('utf-8') if isinstance(prefix, str) else prefix)
                parts.append(f.read(rd ^ key))
            blob = b''.join(parts)
            dst = os.path.join(out_dir, name)
            d = os.path.dirname(dst)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(dst, 'wb') as w:
                w.write(blob)
            n += 1
    return index, n


def read(p):
    return open(p, encoding='utf-8-sig').read().replace('\r\n', '\n')


def scan_string(line, pos):
    q = line[pos]
    i = pos + 1
    out = []
    while i < len(line):
        c = line[i]
        if c == '\\' and i + 1 < len(line):
            out.append(line[i:i + 2]); i += 2; continue
        if c == q:
            return ''.join(out), i + 1
        out.append(c); i += 1
    return ''.join(out), i


def load_characters(rpy_dir):
    chars = {}
    for f in FLOW:
        p = os.path.join(rpy_dir, f)
        if not os.path.isfile(p):
            continue
        t = read(p)
        for m in CHAR_DEF.finditer(t):
            pos = m.end()
            if pos < len(t) and t[pos] in '"\'':
                nm, _ = scan_string(t, pos)
                chars[m.group(1)] = nm
            else:
                chars[m.group(1)] = ''      # 无名 Character（narrator 等）
    return chars


def parse_file(path, chars):
    """返回 [(kind, who, raw_text, lineno)]；kind ∈ say/opt/centered

    只在 `label` 块内收语句：顶层 `image ctc_blink:` / `image rain:` 等定义块里的
    裸字符串（"ctc.png" / "images/bg/rain1.png"）不是台词，必须排除。
    """
    t = read(path)
    out = []
    in_menu, menu_indent = False, -1
    in_label = False
    for no, line in enumerate(t.split('\n'), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        indent = len(line) - len(line.lstrip())
        s = line.strip()
        if indent == 0:
            if re.match(r'^label\s+\w+:', s):
                in_label = True; in_menu = False
                continue
            # 本作 bunki.rpy 的 `menu:` 写在列 0（Ren'Py 容忍该缩进）⇒ 不能当归零块
            if s.startswith('menu:') and in_label:
                in_menu, menu_indent = True, indent
                continue
            in_label = False; in_menu = False
            continue
        if not in_label:
            continue
        if s.startswith('menu:'):
            in_menu, menu_indent = True, indent
            continue
        if in_menu:
            if indent <= menu_indent:
                in_menu = False
            elif s[0] in '"\'':
                txt, endp = scan_string(s, 0)
                rest = s[endp:].lstrip()
                if rest.startswith(':') or rest.startswith('if '):
                    out.append(('opt', '', txt, no))
                    continue
        m = re.match(r'^centered\s+(["%s])' % "'", s)
        if m:
            txt, _ = scan_string(s, m.end() - 1)
            out.append(('centered', '', txt, no)); continue
        m = re.match(r'^([A-Za-z_]\w*)\s+(["%s])' % "'", s)
        if m and m.group(1) in chars:
            txt, _ = scan_string(s, m.end() - 1)
            out.append(('say', chars[m.group(1)], txt, no)); continue
        if s[0] in '"\'':
            txt, _ = scan_string(s, 0)
            out.append(('say', '', txt, no)); continue
    return out


def clean(raw, name):
    txt = raw
    txt = CLICK_P.sub('\x01', txt)
    txt = CLICK_W.sub('\x01', txt)
    txt = TAG.sub('', txt)               # {color}/{size}/{/...} 等富文本标记
    txt = txt.replace('[name]', name)
    txt = txt.replace('\x01', '')
    return txt.strip()


def build_units(rpy_dir, chars, name):
    units = []
    for f in FLOW:
        p = os.path.join(rpy_dir, f)
        if not os.path.isfile(p):
            print('  ⚠ 缺文件', f); continue
        for kind, who, raw, no in parse_file(p, chars):
            # 同框多次点击：切段（{p}/{w}）
            segs = [clean(x, name) for x in re.split(r'\{p\}|\{w\}', raw)]
            segs = [x for x in segs if x]
            text = ''.join(segs)
            if not text:
                continue
            units.append({'file': f, 'line': no, 'kind': kind, 'who': who,
                          'text': text, 'segs': segs})
    return units


def delta(s):
    return (s.count('「') - s.count('」'), s.count('（') - s.count('）'))


def main():
    ap = argparse.ArgumentParser(description='Ren\'Py RPA/.rpy 文本提取（神立ノ雨、鬼ノ唄）')
    ap.add_argument('--rpa', required=True)
    ap.add_argument('--out')
    ap.add_argument('--name', default='ヒカリ', help='主角默认名（[name] 回填；游戏默认=ヒカリ）')
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix='_renpy_')
    try:
        index, n_rpy = extract_rpa(a.rpa, tmp)
        print('RPA 索引 %d 项 → 提取 .rpy %d 个（临时目录 %s）' % (len(index), n_rpy, tmp))
        chars = load_characters(tmp)
        print('角色表：', {k: v for k, v in chars.items() if v})

        units = build_units(tmp, chars, a.name)
        print('文本单元 %d（say %d / 选项 %d / 上屏 %d）' % (
            len(units), sum(1 for u in units if u['kind'] == 'say'),
            sum(1 for u in units if u['kind'] == 'opt'), sum(1 for u in units if u['kind'] == 'centered')))

        # 双版判定：① 同框多段（segs>=2）；② 跨行开口（「/（ 未闭合）
        multi_inline = [u for u in units if len(u['segs']) >= 2]
        groups = []
        i = 0
        while i < len(units):
            dq, dp = delta(units[i]['text'])
            if dq > 0 or dp > 0:
                gd = [dq, dp]; j = i + 1
                while j < len(units) and (gd[0] > 0 or gd[1] > 0) and j - i < 4:
                    dq2, dp2 = delta(units[j]['text'])
                    gd[0] += dq2; gd[1] += dp2; j += 1
                if gd[0] == 0 and gd[1] == 0 and j - i >= 2:
                    groups.append((i, j))
                    i = j; continue
            i += 1
        dual = bool(multi_inline) or bool(groups)
        print('双版判定：同框多段 %d 处 / 跨行开口组 %d 组 ⇒ %s' % (
            len(multi_inline), len(groups), '双版' if dual else '单版'))

        lines = []
        gi = {g[0]: g for g in groups}
        k = 0
        while k < len(units):
            if k in gi:
                s, e = gi[k]
                segs = [units[x]['text'] for x in range(s, e)]
                lines.extend(segs)
                lines.append(''.join(segs))
                k = e
                continue
            u = units[k]
            if len(u['segs']) >= 2:
                lines.extend(u['segs']); lines.append(''.join(u['segs']))
            else:
                lines.append(u['text'])
            k += 1

        print('成品 %d 行 / %d 字' % (len(lines), sum(len(x) for x in lines)))
        if a.out and not a.verify:
            os.makedirs(os.path.dirname(a.out), exist_ok=True)
            with open(a.out, 'wb') as f:
                f.write(b'\xef\xbb\xbf' + ''.join(x + '\n' for x in lines).encode('utf-8'))
            print('写出 %s（%d B）' % (a.out, os.path.getsize(a.out)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
