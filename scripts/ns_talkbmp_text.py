# -*- coding: utf-8 -*-
"""NScripter：正文 + **位图台词（talk_*.bmp ＋ 作者 `;` 注释）** 双版对照提取

用法:
  python scripts/ns_talkbmp_text.py <nscript.dat> <out.txt> [--key 0x84] [--single]

为什么需要这个工具（[JP]DAN☆ICE 2026-11-03）:
  本作在 ストーリー/スピード/ゆっくり 三种模式的「幕」里先 `textoff`，然后逐行
  `lsp <n>,"...game\\talk\\talk_xxx.bmp"` + `print 2` + `\\` 把台词**画成位图**上屏，
  文字窗口是关的 ⇒ 正文里没有这些句子；但作者在每张位图前用 `;` 注释抄了同一句台词。
  判据（L1，结构式）：注释与紧跟其后的 `lsp` 之间**只允许** `lsp`/`csp`/`vsp`/`print`，
  且该 `lsp` 的资源路径含 `talk` ⇒ 这条注释就是那一击上屏的台词。

成行口径与 ns_dual.py 完全一致（同一份 skill 判据）:
  `\\` = 改行＋等待＋清框 ⇒ 框界；`@` = 等待点击不清框 ⇒ 框内段界；
  物理换行 = 软换行（拼接）；`br` = 同框换行；`textclear` = 隐式框界。
  位图台词：一条注释 = 一击 = 一框（1 段，故不出合并行）。
"""
import os
import re
import sys

CMD = re.compile(r'^[!A-Za-z_]')
SPRITE_TIME = re.compile(r'![sd]\d+')
COLOR = re.compile(r'#\$?[0-9A-Fa-f]{6}')
INLINE_CMD = re.compile(r':[A-Za-z_][A-Za-z0-9_]*(?:\s[^:」』]*)?:')
RUBY = re.compile(r'\(([^()/\s]{1,10})/([^()/\s]{1,20})\)')
PURE_ASCII = re.compile(r'[A-Za-z0-9_/,\.\-\s"\']+')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
# 注释与 talk 位图之间允许出现的「只画不写字」命令
BETWEEN_OK = re.compile(r'^(lsp|csp|vsp|print)\b')
# 台词位图 = 文件名以 `talk_` 开头（**不能**用「路径含 talk」判：立绘也放在 `game\talk\` 下，
# 例如 `game\talk\kaito_mk_nm_08.bmp` 是表情差分包，不是字）
TALK_BMP = re.compile(r'["\']?[^"\']*[\\/](talk_[^\\/"\']*\.bmp)', re.I)


def is_talk_bmp(line):
    m = TALK_BMP.search(line)
    return bool(m) and m.group(1).lower().startswith('talk_')


def decode(path, key=0x84):
    d = open(path, 'rb').read()
    return bytes(b ^ key for b in d).decode('cp932', 'replace')


def tidy(s):
    s = SPRITE_TIME.sub('', s)
    s = COLOR.sub('', s)
    s = RUBY.sub(r'\1', s)
    s = s.replace('\u3000\u3000', '\u3000').strip()
    return s


def split_blocks(text):
    """-> [(label, [line, ...])]，按文件顺序。"""
    out = []
    cur = None
    for raw in text.split('\n'):
        s = raw.strip()
        if s.startswith('*'):
            name = s.split(';')[0].split('|')[0].lstrip('*').strip()
            cur = (name, [])
            out.append(cur)
        elif cur is not None:
            cur[1].append(s)
    return out


def find_comment_frames(lines):
    """位图台词：返回 {行号: 台词}（行号 = talk lsp 所在下标）。"""
    m = {}
    for i, s in enumerate(lines):
        if not s.startswith(';'):
            continue
        body = s[1:].strip()
        if not JP.search(body):
            continue
        # 注释体内若还出现 `;`，是作者在同一行「重启注释」的记号（本作 1 处：
        # `;ああっ、…!?;ま、まさか………`）——`;` 本身不可能上屏，按注释符处理、直接拼接
        body = ''.join(p.strip() for p in body.split(';'))
        for j in range(i + 1, min(len(lines), i + 10)):
            x = lines[j]
            if not x:
                continue
            if x.startswith('lsp'):
                if is_talk_bmp(x):
                    m[j] = body          # 同一条注释只认最近的台词位图
                    break
                continue
            if BETWEEN_OK.match(x):
                continue
            break
    return m


def extract_block(lines):
    """-> (frames, n_bitmap, n_at) ；frames = [[seg, ...], ...]"""
    talk = find_comment_frames(lines)
    frames = []
    segs = []
    seg = ''

    def close_seg():
        nonlocal seg
        s = tidy(seg)
        seg = ''
        if s:
            segs.append(s)

    def close_frame():
        nonlocal segs
        close_seg()
        if segs:
            frames.append(segs)
        segs = []

    for i, s in enumerate(lines):
        if not s:
            continue
        if s.startswith(';') or s.startswith('~'):
            continue
        if i in talk:
            close_frame()                    # 位图台词自成一体：先结算上一框
            t = tidy(talk[i])
            if t:
                frames.append([t])
            continue
        if s.startswith('lsp'):
            continue
        if s.startswith(':') or CMD.match(s):
            k = s.split()[0]
            if k in ('textclear', 'cl', 'clear'):
                close_frame()
            continue
        for piece in re.split(r'([@\\])', s):
            if piece == '@':
                close_seg()
                continue
            if piece == '\\':
                close_frame()
                continue
            body = INLINE_CMD.sub('', piece).strip()
            if not body:
                continue
            if CMD.match(body) or body in ('"', "'"):
                close_seg()
                continue
            if PURE_ASCII.fullmatch(body):
                close_seg()
                continue
            if seg:
                if body[0] == '\u3000':
                    body = body.lstrip('\u3000')
                seg += body
            else:
                seg = body
    close_frame()
    return frames, len(talk)


def render(frames, single=False):
    out = []
    for segs in frames:
        if single or len(segs) == 1:
            out.append(''.join(segs))
        else:
            out.extend(segs)
            out.append(''.join(segs))
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    key = 0x84
    single = False
    for a in sys.argv[3:]:
        if a.startswith('--key'):
            key = int(a.split('=', 1)[1], 0)
        elif a == '--single':
            single = True

    text = decode(src, key)
    all_frames = []
    rows = []
    for name, lines in split_blocks(text):
        frames, nb = extract_block(lines)
        if not frames:
            continue
        all_frames += frames
        rows.append((name, len(frames), nb, sum(len(x) for f in frames for x in f)))

    lines_out = render(all_frames, single)
    segs = sum(len(f) for f in all_frames)
    multi = sum(1 for f in all_frames if len(f) > 1)
    print('blocks=%d frames=%d segments=%d multi=%d lines=%d chars=%d'
          % (len(rows), len(all_frames), segs, multi, len(lines_out),
             sum(len(x) for x in lines_out)), file=sys.stderr)
    for name, nf, nb, ch in rows:
        print('  %-28s frames=%-4d bitmap=%-4d chars=%d' % (name, nf, nb, ch), file=sys.stderr)
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    open(dst, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines_out) + '\n')


if __name__ == '__main__':
    main()
