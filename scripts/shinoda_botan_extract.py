#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""篠田新宿探偵事務所 唐獅子牡丹  (HolicWorks Disc Blue / 2018-10-26 / PC-JP)
KiriKiri Z + wamsoft RAT 引擎 —— 剧本文本提取器（端到端）

容器链路
--------
  SFX .exe (WinRAR RAR5, offset 0x48E00, 无密码)
    -> 7z x  => Shinoda Botan.iso (UDF)
    -> 7z x  => 篠田新宿探偵事務所/{data.xp3, voice.xp3, fgimage.xp3, evimage.xp3, video.xp3}
  data.xp3 (KiriKiri XP3, 731 MB) 的索引块 **头 11 字节被改过**（防解析），
  但 zlib 流本身是明文：文件末尾 ~26 KB 处可直接 inflate 出 149 KB 索引。
    index chunk = [11B(乱) magic][u64 size][zlib]
    File 记录 = tag[4]='File' + u64 size + payload{ info | segm | adlr }
      info: u16 len@+20, 名字 UTF-16LE@+22
      segm: 28B/条 = {u32 flags; u64 off; u64 osize; u64 csize}   flags&1 => zlib

文本层
------
  剧本 = data.xp3>scenario/**.ks，KAG 脚本（`[tag]` + 文本行）。
  解析器 = 引擎 `system/RATKAGParser.tjs`（extends KAGParser；扩展名 .txt 才走 RAT，
  .ks 一律走 KAG）。文本/换行的语义在 `system/LineMode.tjs`：

      0 NONE 通常 / 1 PAGE 行単位で[p] / 2 LINE 行単位で[l] /
      3 VN   行単位で[l] 空行で[p] / 4 TEX 改行無視・空行で[p] /
      5 FREE **改行は[r]。空行で[p]** / 6 FRVN 改行は[r]・空行で[l]

  本作 scenario/macro.ks 的 `[macro name=initscene]` 里写死 `[linemode mode=free]`
  ⇒ **一次点击 = 一个空行分隔的段落**；段落内部的换行 = 框内软换行（= [r]）→ 合并为一行。
  `【キャラクタ名/表示名】`（行首、仅首次出现）由 parseCh 的 nameMode 抽走，
  不属于正文（规范：不加说话人前缀）→ 剔除。

  边界判定（照抄 LineMode.parseR / LINEMODE_FREE）：
    空行（无文本、无标签，含 `;` 整行注释）紧跟在「有文本的行」之后 => 改页 [p]
    只有标签的行不算空行（commandLine=true），不会触发改页。

用法
----
  python shinoda_botan_extract.py <data.xp3> <输出txt>
"""
import os, re, sys, zlib, struct

# ---------------------------------------------------------------- XP3 ------
XP3_MAGIC_TAIL = 0x2b9381d3          # 本作实测：索引 zlib 流起点（下方自动定位）


def find_index(fh, fsize):
    WIN = 1 << 20
    fh.seek(max(0, fsize - WIN))
    buf = fh.read()
    for i in range(len(buf) - 2):
        if buf[i] == 0x78 and buf[i + 1] in (0x01, 0x5e, 0x9c, 0xda):
            try:
                out = zlib.decompress(buf[i:])
                if out[:4] == b'File' and len(out) > 10000:
                    return out
            except Exception:
                pass
    raise RuntimeError('XP3 index (zlib) not found')


def read_xp3(path):
    fh = open(path, 'rb')
    fh.seek(0, 2)
    fsize = fh.tell()
    idx = find_index(fh, fsize)
    files, p = {}, 0
    while p + 12 <= len(idx):
        tag = idx[p:p + 4]
        size = struct.unpack_from('<Q', idx, p + 4)[0]
        payload = idx[p + 12:p + 12 + size]
        if tag != b'File':
            break
        q = 0
        name, segs = None, []
        while q + 12 <= len(payload):
            t2 = payload[q:q + 4]
            s2 = struct.unpack_from('<Q', payload, q + 4)[0]
            sp = payload[q + 12:q + 12 + s2]
            if t2 == b'info':
                nlen = struct.unpack_from('<H', sp, 20)[0]
                name = sp[22:22 + nlen * 2].decode('utf-16-le', 'replace')
            elif t2 == b'segm':
                for i in range(0, len(sp), 28):
                    segs.append(struct.unpack_from('<IQQQ', sp, i))
            q = q + 12 + s2
        if name:
            files[name] = segs
        p = p + 12 + size

    def read(name):
        buf = bytearray()
        for fl, off, osz, csz in files[name]:
            fh.seek(off)
            d = fh.read(csz)
            buf += zlib.decompress(d) if (fl & 1) else d
        return bytes(buf)

    return files, read


def decode_ks(raw):
    if raw[:2] == b'\xff\xfe':
        return raw[2:].decode('utf-16-le', 'replace')
    if raw[:2] == b'\xfe\xff':
        return raw[2:].decode('utf-16-be', 'replace')
    return raw.decode('cp932', 'replace')


# ----------------------------------------------------------- LineMode ------
TAGRE = re.compile(r'\[([^\]]*)\]')
CHOICE = re.compile(r'text\s*=\s*"([^"]*)"')
JUMP = re.compile(r'\[(?:next|call)\s[^\]]*storage\s*=\s*"?([^"\s\]]+)"?')


def split_tokens(line):
    """`[tag]` / 文本 的顺序流。

    * `[` 起，到**引号外**的第一个 `]` 结束（`[eval exp="…flags[0] = 1"]` 内含 `]`）。
    * 行首 `;` = KAG 注释（整行丢弃）。
    """
    if line.lstrip()[:1] == ';':
        return []
    toks, i, n = [], 0, len(line)
    while i < n:
        c = line[i]
        if c == '[':
            j, depth = i + 1, 1          # 标签以「方括号深度归零」收尾
            while j < n:
                if line[j] == '[':
                    depth += 1
                elif line[j] == ']':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j >= n:                       # 未闭合 -> 整行剩余当文本
                toks.append(('t', line[i:]))
                break
            toks.append(('g', line[i + 1:j]))
            i = j + 1
        else:
            j = i
            while j < n and line[j] != '[':
                j += 1
            toks.append(('t', line[i:j]))
            i = j
    return toks


def killname(line):
    """行首 【名前/表示名】 -> 去掉（仅当 【 是行内第一个正文字符）"""
    if line[:1] != '【':
        return line
    k = line.find('】')
    if k < 0:
        return line
    return line[k + 1:]


def logical_lines(text):
    """把以 '\\' 结尾的行与下一行合并（KAG 行继续）。"""
    out, buf = [], None
    for raw in text.split('\n'):
        ln = raw.rstrip('\r')
        if buf is not None:
            ln = buf + ln
            buf = None
        if ln.endswith('\\'):
            buf = ln[:-1]
            continue
        out.append(ln)
    if buf is not None:
        out.append(buf)
    return out


def ruby_split(tag):
    """LineMode.checkRubyParam：tagname（到首个 ASCII 空格/Tab 为止）含 `,`(pos>0)
    -> 通常ルビ [本文,ルビ]；否则含 `'`(pos>0) -> 簡易ルビ [本文'ルビ]。"""
    tn = re.split(r'[ \t]', tag, maxsplit=1)[0]
    k = tn.find(',')
    if k > 0:
        return tn[:k], tn[k + 1:]
    k = tn.find("'")
    if k > 0:
        return tn[:k], tn[k + 1:]
    return None


def extract_boxes(text):
    """LINEMODE_FREE 状态机 -> [文本...]，选择支按 seladd 出现位置内联。"""
    boxes, cur = [], []
    rubies = []                    # (box_index, base, ruby)
    pend = []                      # 現在の箱に属するルビ
    emptyLine = True
    commandLine = False
    prevEmptyLine = True
    nameMode = 0

    def flush():
        nonlocal cur, pend
        s = ''.join(cur).strip()
        if s:
            idx = len(boxes)
            boxes.append(s)
            for b, r in pend:
                rubies.append((idx, b, r))
        cur = []
        pend = []

    in_script = False
    for line in logical_lines(text):
        emptyLine = True
        commandLine = False
        nameMode = 0
        if in_script:
            if 'endscript' in line:
                in_script = False
            continue
        if line.lstrip()[:1] == '*':          # *label|标题 —— 非正文
            prevEmptyLine = True
            continue

        for kind, val in split_tokens(line):
            if kind == 't':
                if not val:
                    continue
                if nameMode:
                    if '】' in val:
                        nameMode = 0
                    continue
                if emptyLine:
                    if val[:1] == '【':       # 【キャラ/表示名】= 名前表示（非正文）
                        k = val.find('】')
                        if k >= 0:
                            val = val[k + 1:]
                        else:
                            nameMode = 1
                            continue
                    emptyLine = False
                if val:
                    cur.append(val)
                continue
            # --- tag ---
            name = re.split(r'[ \t=]', val, maxsplit=1)[0]
            low = name.lower()
            if low in ('iscript', 'endscript'):
                in_script = (low == 'iscript')
                flush()
                continue
            if low in ('l', 'p'):
                flush()
                commandLine = True
                continue
            if low == 'seladd':
                m = CHOICE.search(val)
                flush()
                if m:
                    boxes.append(m.group(1).strip())
                commandLine = True
                continue
            if low == 'r':
                continue
            rb = ruby_split(val)              # [本文,ルビ]
            if rb:
                if rb[1]:
                    pend.append((rb[0], rb[1]))
                emptyLine = False
                cur.append(rb[0])
                continue
            commandLine = True

        # --- 行末 (= [r eol=true]) ---
        if emptyLine:
            if not commandLine and not prevEmptyLine:
                flush()
            prevEmptyLine = True
        else:
            prevEmptyLine = False
    flush()
    return boxes, rubies


# ------------------------------------------------------------- order ------
SYSTEM_KS = {'macro.ks', 'parsermacro.ks', 'z_macro.ks', 'z_flag.ks', 'z_test.ks'}


def play_order(read, files):
    scen = sorted(n for n in files if n.startswith('scenario/') and n.endswith('.ks'))
    seen, order = set(), []

    def visit(name):
        if name in seen or name not in files:
            return
        seen.add(name)
        order.append(name)
        try:
            body = decode_ks(read(name))
        except Exception:
            return
        for m in JUMP.finditer(body):
            tgt = m.group(1)
            cand = tgt if tgt in files else 'scenario/' + os.path.basename(tgt)
            visit(cand)

    visit('scenario/start.ks')
    for n in scen:                                  # 未达脚本（回想等）
        if os.path.basename(n) in SYSTEM_KS:
            continue
        visit(n)
    return order


# -------------------------------------------------------------- main ------
def main():
    xp3, outp = sys.argv[1], sys.argv[2]
    files, read = read_xp3(xp3)
    print('xp3 files:', len(files))
    order = play_order(read, files)
    print('scenario order:', len(order))

    all_lines = []
    rubies = []
    stat = {}
    for name in order:
        if os.path.basename(name) in SYSTEM_KS:
            continue
        if '/replay/' in name:              # 回想モード：本編と 100% 重複（後述）
            continue
        text = decode_ks(read(name))
        boxes, rbs = extract_boxes(text)
        off = len(all_lines)
        for idx, b, r in rbs:
            rubies.append((off + idx, b, r))
        stat[name] = len(boxes)
        all_lines.extend(boxes)

    with open(outp, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(all_lines) + '\n').encode('utf-8'))

    rbf = os.path.splitext(outp)[0] + '_ルビ対訳.txt'
    with open(rbf, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('# ルビ注記一覧（KAG `[本文,ルビ]` = 画面上で本文の上に小さく表示される振り仮名）\n'
                  '# 形式：<その箱の本文全文> TAB <ルビ対象の本文> TAB <ルビ>\n'
                  '# ※ ルビ対象は行頭の 1 文字を含まないことがある（例 `「Y[ou…,…]` の `ou…`）。\n'
                  '#    その 1 文字はタグの外にあり、本文側には正しく入っている。\n').encode('utf-8'))
        for idx, b, r in rubies:
            head = all_lines[idx] if idx < len(all_lines) else ''
            f.write((head + '\t' + b + '\t' + r + '\n').encode('utf-8'))

    data = ('\n'.join(all_lines) + '\n')
    print('boxes:', len(all_lines), 'chars:', len(data))
    print('rubies:', len(rubies), '->', rbf)
    print('CR:', data.count('\r'), 'U+FFFD:', data.count('\ufffd'),
          '[:', data.count('['), ']:', data.count(']'),
          '【:', data.count('【'), '%%s:', data.count('%s'))
    leftovers = sorted({c for c in data if c in '〓\ufffd'})
    print('leftover special:', leftovers[:20])
    print('bytes:', os.path.getsize(outp))
    print('\n-- top files --')
    for n, c in sorted(stat.items(), key=lambda x: -x[1])[:15]:
        print(f'{c:6d}  {n}')


if __name__ == '__main__':
    main()
