# -*- coding: utf-8 -*-
"""Last Convert (NScripter / nscript.dat, 全字节 XOR 0x84) -> 双版对照文本

口径（skill references/S6-lines-dual.md §5 NScripter）:
- A 类 = 行末 `\\`（改页/清框）      -> 框界
- B 类 = `@`（框内点击、文字原地续写） -> 框内段界
- 无终止符的文本行 = 同框软换行       -> 直接拼接
- 框内 >=2 段 => 先列各段，再列合并行；单段框只列一次
- `*label`（缓冲非空）/ `br` / `textclear` => 隐式框界
- 选项（select "…",*label）各占一行、按出现顺序
- 名札：独立行 `【名】` 整行丢弃（并作段界，防把名字并进上句）；行首 `【名】`+正文 => 去前缀
- 控制符：`_`（改行なしクリック待ち / 間）、`!w`/`!sd`/`!d`、`#RRGGBB` 一律剥除
- 只取正文段（*game_start 起，*define 前止）：其后为系统/おまけ/开发者留言的模板残留
"""
import re
import sys

XOR = 0x84
CMD = re.compile(r'^[!A-Za-z_/]')
PLATE_LINE = re.compile(r'^【([^】]{1,20})】$')
PLATE_HEAD = re.compile(r'^【[^】]{1,20}】')
INLINE_CODE = re.compile(r'![a-z]+\d*|#[0-9A-Fa-f]{6}')


def decode(path):
    return bytes(b ^ XOR for b in open(path, 'rb').read()).decode('cp932', 'replace')


def load_lines(text):
    """截取正文段：*game_start .. *define 之前。"""
    lines = text.split('\n')
    out, on = [], False
    for l in lines:
        s = l.strip()
        if s.startswith('*game_start'):
            on = True
            continue
        if s.startswith('*define'):
            break
        if on:
            out.append(l)
    return out


def tidy(s):
    s = INLINE_CODE.sub('', s)
    s = s.replace('_', '')          # 行内「間」クリック待ち，不换行、不切行
    return s.strip()


def extract(lines):
    frames, opts = [], []
    segs, seg = [], ''
    stats = dict(at=0, bs=0, soft=0, plates=0, plate_inline=0)

    def close_seg():
        nonlocal seg
        t = tidy(seg)
        seg = ''
        if t:
            segs.append(t)

    def close_frame():
        nonlocal segs
        close_seg()
        if segs:
            frames.append(segs)
        segs = []

    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        s = raw.strip()
        if not s:
            continue
        if s.startswith('*'):
            close_frame()
            continue
        if s.startswith(';'):
            continue
        # 选项
        if s == 'select' or s.startswith('select ') or s.startswith('csel'):
            close_frame()
            body = ''
            while i < len(lines):
                body += lines[i].strip()
                i += 1
                if body.rstrip().endswith(','):
                    continue
                break
            for q in re.findall(r'"([^"]*)"', body):
                if q.startswith('*') or q.startswith(':'):
                    continue
                q = tidy(q.replace('\\', ''))
                if q:
                    opts.append((len(frames), q))
            continue
        if s in ('br', 'textclear'):
            close_frame()
            continue
        if CMD.match(s):
            continue
        m = PLATE_LINE.match(s)
        if m:
            close_seg()               # 名札：整行丢弃，且不并入上一句
            stats['plates'] += 1
            continue
        m = PLATE_HEAD.match(s)
        if m:
            s = s[m.end():]
            stats['plate_inline'] += 1
            if not s:
                continue
        # 正文行：按 @ / \ 切
        for piece in re.split(r'([@\\])', s):
            if piece == '@':
                close_seg()
                stats['at'] += 1
                continue
            if piece == '\\':
                close_frame()
                stats['bs'] += 1
                continue
            body = tidy(piece)
            if not body:
                continue
            if CMD.match(body) or body.startswith('"'):
                close_seg()           # 行尾跟随命令（如 `@dwave …`）
                continue
            if seg:
                seg += body
                stats['soft'] += 1
            else:
                seg = body
    close_frame()
    return frames, opts, stats


def render(frames, opts):
    out = []
    by_pos = {}
    for pos, t in opts:
        by_pos.setdefault(pos, []).append(t)
    for n, segs in enumerate(frames):
        out.extend(by_pos.get(n, []))
        if len(segs) == 1:
            out.append(segs[0])
        else:
            out.extend(segs)
            out.append(''.join(segs))
    out.extend(by_pos.get(len(frames), []))
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    frames, opts, st = extract(load_lines(decode(src)))
    lines = [l for l in render(frames, opts) if l.strip()]
    multi = sum(1 for f in frames if len(f) > 1)
    seg_total = sum(len(f) for f in frames)
    print('frames=%d segs=%d multi=%d opts=%d 点击版=%d 页版=%d 对照版=%d '
          'A(\\)=%d B(@)=%d soft=%d plates=%d plate_inline=%d'
          % (len(frames), seg_total, multi, len(opts), seg_total + len(opts),
             len(frames) + len(opts), len(lines), st['bs'], st['at'],
             st['soft'], st['plates'], st['plate_inline']))
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
