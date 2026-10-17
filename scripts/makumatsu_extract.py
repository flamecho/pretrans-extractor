#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《幕末Rock 超魂》(PS Vita / PCSG00425 / Marvelous) 全文本提取

管线
----
  1) 解 PKG(NoNpDrm)   : scripts/pkg2zip.exe -x <.pkg>            # work.bin 同目录自动取授权
  2) 解密 PFS           : util/rif2zrif.py <work.bin> -> zRIF
                          psvpfsparser.exe -i app/PCSG00425 -o dec \
                              -k <work.bin[0x50:0x60] 的 hex> -f cma.henkaku.xyz
       ⚠ zRIF 路线报 `header signature is invalid`；改用 -k klicensee 通过（实测）
       ⚠ 必须放行网络 cma.henkaku.xyz:80（否则 `Error: ...expected value` 假错误）
       成功判据 `keystone: matched retail hmac`
  3) 解 CRI CPK         : python scripts/cpk.py dec/INST.CPK <out>   # 2.x / @UTF 明文
  4) 本脚本             : python scripts/makumatsu_extract.py <CPK解包根> <输出.txt>

脚本格式（逆向结论）
------------------
  文件 = b'MZ\\0\\0' + 命令流；命令 = [u16 op][u16 a] + (a-1)×u32；
  字符串参数 = [u16 tag][u16 wc] + wc*4 字节 cp932（尾部 NUL 填充）。
  tag 0x0003 = 台词    tag 0xFB03 = 资源路径 / 选项文本 / 名字表
  · 正文    op 0x62 (scene/*)  : [u32 msgid][str tag=3][u32 flag]
  · 选项    op 0x51 (scene/*)  : [str tag=FB03][u32 跳转偏移]；连续多条 = 一组
  · 名字表  op 0x8C2F / 0xFB03 : [str…]      ⇒ **不取**（交付规范：不加说话人前缀）
  · 演职员  op 0x4C  (staffroll)             ⇒ **不取**（非剧情正文）
  · ライブ歌詞 op 0x2C (play/*) : [u32×6 计时/标志][str tag=3] ⇒ 取（歌詞）
  ⇒ **正文按 msgid 升序输出 = 游戏内显示顺序**（msgid 全局唯一，实测 13058 个）

PUA（cp932 用户定义区）映射
--------------------------
  U+E000→'！' U+E001→'？' U+E0B1→'・' U+E0AE→'！' U+E0B7→'？'
  依据：U+E000 前接 ぜよ/じゃ/ます/です（断定）⇒ 感叹；U+E001 前接 のか/んだ/だと/かよ（疑问）⇒ 问号；
        U+E0B1 见于 マシュー・カルブレイス / 龍馬・高杉・桂 / お・じ・さ・ん ⇒ 中黑。
  play/* 中其余 PUA 为**演出标记**（无日文、取值各异）⇒ 从串中剔除；剔后无日文者丢弃。
"""
import os
import re
import sys
import glob
import struct

STR_TAGS = {0x0003, 0xFB03}
PUA_MAP = {'\ue000': '！', '\ue001': '？', '\ue0b1': '・', '\ue0af': '・',
           '\ue0ae': '！', '\ue0b7': '？'}
FNT = re.compile(r'\\fnt\d')
JP = re.compile(r'[ぁ-んァ-ヶー一-龯]')


def walk(d, start=4):
    pos, n, cmds = start, len(d), []
    while pos + 4 <= n:
        op, a = struct.unpack_from('<HH', d, pos)
        end = pos + max(a, 1) * 4
        if end > n:
            break
        cmds.append((pos, op, a, end))
        pos = end
    return cmds


def strings_of(d, pos, end):
    out, p = [], pos
    while p + 4 <= end:
        w = struct.unpack_from('<I', d, p)[0]
        lo, hi = w & 0xFFFF, (w >> 16) & 0xFFFF
        if 1 <= hi <= 0x400 and lo in STR_TAGS and p + 4 + hi * 4 <= end:
            blob = d[p + 4:p + 4 + hi * 4].rstrip(b'\x00')
            try:
                s = blob.decode('cp932')
            except Exception:
                s = None
            if s is not None:
                out.append(s)
                p += 4 + hi * 4
                continue
        p += 4
    return out


def clean(s, drop_pua=False):
    s = FNT.sub('', s)
    for k, v in PUA_MAP.items():
        s = s.replace(k, v)
    if drop_pua:
        s = ''.join(c for c in s if not (0xE000 <= ord(c) <= 0xF8FF))
    s = s.replace('\\n', '').replace('\n', '').replace('\r', '')
    return s.strip()


# ---------------- 幕間劇 SKTH ----------------
def skit_strings(d, start=0x30):
    """SKTH 容器：槽 = [u32 字段] + cp932 文本（NUL 填充）。按 NUL 自定界顺序扫描。"""
    n = len(d)
    out = []
    i = start
    while i < n:
        b = d[i]
        if 0x81 <= b <= 0xFC:
            j = i
            while j < n and d[j] != 0:
                b1 = d[j]
                if 0x81 <= b1 <= 0x9F or 0xE0 <= b1 <= 0xFC:
                    if j + 1 < n and 0x40 <= d[j + 1] <= 0xFC and d[j + 1] != 0x7F:
                        j += 2
                    else:
                        break
                elif b1 in (0x0A, 0x0D) or 0x20 <= b1 < 0x7F:
                    j += 1
                else:
                    break
            if j < n and d[j] == 0 and j - i >= 2:
                try:
                    s = d[i:j].decode('cp932')
                except Exception:
                    s = None
                if s:
                    out.append(s)
                    i = j
                    continue
        i += 1
    return out


SKIT_WIN = 4      # 引擎写入回声：与最近 4 条已保留行相同 ⇒ 丢弃

_OPEN = [('（', '）'), ('「', '」'), ('『', '』'), ('《', '》'), ('【', '】')]


def _unclosed(s):
    """行尾存在未闭合的成对符号 ⇒ 该行是「同一文本框的续行」。"""
    for a, b in _OPEN:
        if s.count(a) > s.count(b):
            return True
    return False


def _stray_closer(s):
    """出现多于开括号的闭括号 ⇒ 该行是「被截断的括号句片段」。"""
    for a, b in _OPEN:
        if s.count(b) > s.count(a):
            return True
    return False


def _fix_parens(lines):
    """收尾清理：删掉开括号已在别处出现过的孤立闭括号片段；否则并回上一行。"""
    out = []
    for i, t in enumerate(lines):
        if _stray_closer(t):
            key = t
            for a, b in _OPEN:
                key = key.replace(a, '').replace(b, '')
            key = key.strip()
            win = lines[:i] + lines[i + 1:]
            if key and any(key in w for w in win):
                continue                      # 片段/回声 ⇒ 丢弃
            if out and _unclosed(out[-1]):
                out[-1] += t                  # 并回上一行（补全括号）
                continue
        out.append(t)
    return out


def extract_skits(sysdir):
    """读 ui_skit_00/01/02.skt，返回清洗后的行序列。"""
    files = sorted(glob.glob(os.path.join(sysdir, 'ui_skit_*.skt')))
    lines = []
    for f in files:
        d = open(f, 'rb').read()
        seq = []
        # ① 先做「续行合并」：行尾括号未闭合 ⇒ 与下一槽同属一个文本框，先并起来
        for s in skit_strings(d):
            t = clean(s)
            if not t:
                continue
            if t.endswith('\u3000'):        # 独立名札行（「晋作　」等）⇒ 丢弃
                continue
            if not (JP.search(t) or (len(t) <= 8 and all(
                    c in '…‥・！？、。「」『』（）ー～♪' for c in t))):
                continue
            if seq and _unclosed(seq[-1]) and len(seq[-1]) < 60:
                seq[-1] += t
            else:
                seq.append(t)
        # ② 再做「回声去重」：与最近 4 条已保留行相同 ⇒ 丢弃（引擎写入回声）
        for t in seq:
            if t in lines[-SKIT_WIN:]:
                continue
            lines.append(t)
    return _fix_parens(lines)


def main():
    root, out = sys.argv[1], sys.argv[2]
    scene = [f for f in glob.glob(os.path.join(root, 'scene', 'script', '*.bin'))
             if not os.path.basename(f).startswith('staffroll')]
    play = [f for f in glob.glob(os.path.join(root, 'play', 'script', '*.bin'))
            if os.path.basename(f) != 'test_cutin2.bin']

    # ---- 采集正文(0x62)/选项(0x51)，key = (msgid, 序号) ----
    items = []          # (msgid, seq, text, tag)
    pua_play_drop = 0
    for fi, f in enumerate(sorted(scene)):
        d = open(f, 'rb').read()
        cur = -1
        seq = 0
        for pos, op, a, e in walk(d):
            if op == 0x62 and e >= pos + 8:
                mid = struct.unpack_from('<I', d, pos + 4)[0]
                cur = mid
                for s in strings_of(d, pos + 4, e):
                    t = clean(s)
                    if t:
                        items.append((mid, seq, t)); seq += 1
            elif op == 0x51:
                for s in strings_of(d, pos + 4, e):
                    t = clean(s)
                    if t:
                        items.append((cur, seq, t)); seq += 1

    # 去重：相邻完全相同的 (msgid, 文本) 只留一条
    items.sort(key=lambda x: (x[0], x[1]))
    text_lines, seen = [], set()
    for mid, sq, t in items:
        k = (mid, t)
        if k in seen:
            continue
        seen.add(k)
        if text_lines and text_lines[-1] == t:
            continue
        text_lines.append(t)
    scene_n = len(text_lines)

    # ---- play/*（ライブ歌詞）：按文件 + 记录顺序 ----
    play_lines = []
    play.sort(key=lambda x: [int(k) for k in re.findall(r'\d+', os.path.basename(x))] or [0])
    for f in play:
        d = open(f, 'rb').read()
        for pos, op, a, e in walk(d):
            if op != 0x2C or not e:
                continue
            for s in strings_of(d, pos + 4, e):
                t = clean(s, drop_pua=True)
                if not t:
                    pua_play_drop += 1
                    continue
                if not JP.search(t):
                    continue
                if play_lines and play_lines[-1] == t:
                    continue
                play_lines.append(t)

    # ---- 幕間劇（ui_skit_*.skt，NOINST.CPK/systemdata）----
    skit_lines = []
    skit_dir = sys.argv[3] if len(sys.argv) > 3 else None
    if skit_dir and os.path.isdir(skit_dir):
        skit_lines = extract_skits(skit_dir)

    all_lines = text_lines + play_lines + skit_lines

    # 全局相邻去重（跨段）
    final = []
    for t in all_lines:
        t = t.replace('\r', '').replace('\x00', '').strip()
        if not t:
            continue
        if final and final[-1] == t:
            continue
        final.append(t)

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(final) + '\n')

    print('scene files=%d  play files=%d' % (len(scene), len(play)))
    print('正文+选项=%d  ライブ歌詞=%d  幕間劇=%d  合计=%d' %
          (scene_n, len(play_lines), len(skit_lines), len(final)))
    print('play 丢弃的纯标记串=%d' % pua_play_drop)


if __name__ == '__main__':
    main()
