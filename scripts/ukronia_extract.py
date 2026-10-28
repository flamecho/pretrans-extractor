#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""泡沫のユークロニア 剧本成行器（TIS 风格 [命令] 脚本）。

判据（L1，记录自定界）：
  · 空行 / 命令行 / 注释行 结束一个正文块 ⇒ 一个正文块 = 一个文本框 = 一次点击
  · **novel mode（[textmode=3]）也一样：块 = 一次点击**；`[nextpage]` 只负责清屏，不产生行
    （2026-10-27 修正：旧版把整页多块 join 成一行，证据见解析报告 §10）
  · 块首 `【名】` / `【名/陰影】;【表示】` = 名札行 ⇒ 丢弃（有独立名字窗，见 [名 voice=] 命令）
  · 行内 `[dic no=N text=WORD'ruby]` ⇒ 还原为 WORD（去掉读音）
  · 行内 `[漢字'よみ]`（普通 ruby，**无 dic 前缀**）⇒ **保留汉字**，去读音
    （2026-10-27 修正：旧版被 `ANYCMD` 整段删掉，75 处正文丢字）
  · `[主人公]` ⇒ 主角名（`NAME`）；与紧邻「直写名版」重复时只留一条（源侧双写 329 对）
  · `[seladd text="…"]` + `[select]` = 选项，按出现顺序一行一条，紧跟在提问块之后
用法: python scripts/ukronia_extract.py <scen目录|scenario01 bundle> <out.txt>
"""
import os, re, sys, json

NAME = '雛菊'          # 主角名（可改名，默认名）—— `[主人公]` 宏的回填值

TAG = re.compile(r'<[^>]*>')
PLATE = re.compile(r'^【[^】]*】(?:;【[^】]*】)*')
CMD = re.compile(r'^[\[@*#]')
DIC = re.compile(r'\[dic\b[^\]]*\btext=([^\]]*)\]')
RUBY = re.compile(r"\[([^\[\]']*)'[^\[\]]*\]")
ANYCMD = re.compile(r'\[[^\]]*\]')


def is_cmd(s):
    return bool(CMD.match(s))


def clean_line(s):
    s = DIC.sub(lambda m: m.group(1).split("'")[0], s)
    s = s.replace('[主人公]', NAME)
    s = RUBY.sub(lambda m: m.group(1), s)   # ★ 普通 ruby 保汉字
    s = ANYCMD.sub('', s)
    s = TAG.sub('', s)
    return s.strip(' \u3000')     # ★ 只去首尾缩进（行首 U+3000 是悬挂缩进），行内全角空格保留原文


def iter_scripts(root):
    """产出 (文件名, 文本)。root 为目录或 scenario*.unity3d bundle。"""
    if os.path.isdir(root):
        for fn in sorted(os.listdir(root)):
            if not fn.endswith('.txt'):
                continue
            yield fn[:-4], open(os.path.join(root, fn), encoding='utf-8-sig').read()
        return
    import UnityPy
    env = UnityPy.load(root)
    for o in env.objects:
        if o.type.name != 'TextAsset':
            continue
        d = o.read()
        raw = d.m_Script if isinstance(d.m_Script, bytes) else str(d.m_Script).encode('utf-8', 'replace')
        yield d.m_Name, raw.decode('utf-8-sig', 'replace')


def load_dic(path):
    if not os.path.exists(path):
        return []
    try:
        j = json.load(open(path, encoding='utf-8-sig'))
    except Exception:
        return []
    return [(d['title'], ' '.join(d.get('text', '').split('\n'))) for d in j.get('data', [])]


def main():
    root, out = sys.argv[1], sys.argv[2]
    lines_out = []
    stats = {'files': 0, 'blocks': 0, 'dual_drop': 0, 'opts': 0, 'skipped': 0}

    scripts = [(n, t) for n, t in iter_scripts(root)
               if re.match(r'^\d\d_', n) and 'test' not in n]
    scripts.sort()
    for fn, txt in scripts:
        txt = txt.replace('\r\n', '\n')
        stats['files'] += 1
        pend_opts, block = [], []

        def emit_opts():
            for t in pend_opts:
                lines_out.append(t)
                stats['opts'] += 1
            pend_opts.clear()

        def flush_block():
            if not block:
                return
            raw = ''.join(x.strip() for x in block)
            block.clear()
            body = clean_line(PLATE.sub('', raw))
            if not body:
                stats['skipped'] += 1
                return
            stats['blocks'] += 1
            # 源侧双写：`【名】「雛菊にも…」` / `【名】「[主人公]にも…」` 相邻两条 ⇒ 宏版只留名版
            if '[主人公]' in raw and lines_out and body == lines_out[-1]:
                stats['dual_drop'] += 1
                return
            lines_out.append(body)
            emit_opts()

        for raw in txt.split('\n'):
            s = raw.strip()
            lead = raw.lstrip(' \t')   # ★ 不能用 strip()：行首 U+3000 是排版缩进，不是命令行
            if not s:
                flush_block()
                continue
            if lead.startswith(';') or is_cmd(lead):
                flush_block()
                m = re.match(r'\[seladd\s+text="([^"]*)"', lead)
                if m:
                    t = clean_line(m.group(1))
                    if t:
                        pend_opts.append(t)
                    continue
                continue        # `[nextpage]` / `[textmode=N]` 只切页/切模式，不产生行
            block.append(raw)
        flush_block()
        emit_opts()

    for title, text in load_dic(os.path.join('_w_D_ukronia', 'ta', 'dictionary.txt')):
        lines_out.append('【%s】%s' % (title, text))

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as w:
        for ln in lines_out:
            w.write(ln + '\n')
    print(stats)
    print('lines', len(lines_out), 'chars', sum(len(x) for x in lines_out))


if __name__ == '__main__':
    main()
