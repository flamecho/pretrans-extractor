#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""泡沫のユークロニア 剧本成行器（TIS 风格 [命令] 脚本）。

判据（L1，记录自定界）：
  · 空行 / 命令行 / 注释行 结束一个正文块 ⇒ 一个正文块 = 一个文本框 = 一次点击
  · **novel mode（[textmode=3]）也一样：块 = 一次点击**；`[nextpage]` 只是清屏，不产生行
    （2026-10-27 修正，同母作：161 个 novel 页里 52% 超过 ADV 单框上限 90 字，最长 156）
  · 块首 `【名】` / `【名/陰影】;【表示】` = 名札行 ⇒ 丢弃（有独立名字窗，见 [名 voice=] 命令）
  · 行内 `[dic no=N text=WORD'ruby]` ⇒ 还原为 WORD（去掉读音）
  · 行内 `[漢字'よみ]`（无 dic 前缀的普通 ruby）⇒ **保留汉字**（2026-10-27：旧版被 ANYCMD 删掉，52 块丢字）
  · `[seladd text="…"]` + `[select]` = 选项，按出现顺序一行一条，紧跟在提问块之后
用法: python scripts/ukronia_extract.py <scen目录|scenario01 bundle> <out.txt>
"""
import os, re, sys, json

TAG = re.compile(r'<[^>]*>')
PLATE = re.compile(r'^【[^】]*】(?:;【[^】]*】)*')   # ★ 不加 `$`：名札常与正文同一块（`【露草】「…」`）
CMD = re.compile(r'^[\[@*#]')
DIC = re.compile(r'\[dic\b[^\]]*\btext=([^\]]*)\]')
RUBY = re.compile(r"\[([^\[\]']*)'[^\[\]]*\]")
ANYCMD = re.compile(r'\[[^\]]*\]')
# 行内主角名宏（324 处）：`[主人公]` 是 UB 变量插入占位，替换为默认名，不可当空控制码丢弃
NAME_MACRO = {'[主人公]': '雛菊'}


def is_cmd(s):
    return bool(CMD.match(s))


def clean_line(s):
    for k, v in NAME_MACRO.items():
        s = s.replace(k, v)
    s = DIC.sub(lambda m: m.group(1).split("'")[0], s)
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
        # UnityPy 对非法 UTF-8 会给 str＋surrogate ⇒ 用 surrogateescape 还原原始字节流
        raw = d.m_Script if isinstance(d.m_Script, bytes) else d.m_Script.encode('utf-8', 'surrogateescape')
        # 个别脚本是 UTF-16LE，且带 **UTF-8 BOM 前缀**（EF BB BF + UTF-16LE）⇒ 先剥 3 字节再按 utf-16-le 解
        txt = None
        b = raw
        if b.startswith(b'\xef\xbb\xbf'):
            b = b[3:]
        if b.startswith(b'\xfe\xff'):
            txt = b[2:].decode('utf-16-be', 'replace')
        elif b.startswith(b'\xff\xfe'):
            txt = b[2:].decode('utf-16-le', 'replace')
        elif b'\x00' not in b:
            txt = b.decode('utf-8', 'replace')
        else:
            txt = b.decode('utf-16-le', 'replace')
        yield d.m_Name, txt


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
    stats = {'files': 0, 'blocks': 0, 'opts': 0, 'skipped': 0}

    SKIP = {'00_live2d_check'}          # Live2D 调试数据（系统/调试，不收）
    scripts = [(n, t) for n, t in iter_scripts(root)
               if re.match(r'^\d\d_', n) and 'test' not in n and n not in SKIP]
    scripts.sort()
    for fn, txt in scripts:
        txt = txt.replace('\r\n', '\n')
        stats['files'] += 1
        st = {'label': False}
        pend_opts, block = [], []

        def emit_opts():
            for t in pend_opts:
                lines_out.append(t)
                stats['opts'] += 1
            pend_opts.clear()

        def flush_block():
            if not block:
                return
            raw_b = ''.join(x.strip() for x in block)
            block.clear()
            body = clean_line(PLATE.sub('', raw_b))
            if not body:
                stats['skipped'] += 1
                return
            stats['blocks'] += 1
            # ★ 名前差分の互斥分支：`[next target=*nameXX eval="!(f.isDefaultName)"]` / `*nameXX|`
            #   之后的同名块＝同一处点击的另一版本（死写名版 / 宏版）。宏替换成默认名后正文全等 ⇒ 取一。
            duel = st['label'] or ('[主人公]' in raw_b)
            st['label'] = False
            if duel and lines_out and body == lines_out[-1]:
                stats['branch_dup'] = stats.get('branch_dup', 0) + 1
                return
            lines_out.append(body)
            emit_opts()

        for raw in txt.split('\n'):
            s = raw.strip()
            lead = raw.lstrip(' \t')   # ★ 不能用 strip()：行首 U+3000 是排版缩进，不是命令行
            # ★ 行首 `[主人公]は…` 是正文（62 行），替换名宏后再判命令行，否则整句被当指令吞掉
            for _k, _v in NAME_MACRO.items():
                lead = lead.replace(_k, _v)
            if not s:
                flush_block()
                continue
            if lead.startswith(';') or is_cmd(lead):
                flush_block()
                if re.match(r'^\*[^|]*\|', lead) or 'isDefaultName' in lead:
                    st['label'] = True      # 名前差分の分岐点（互斥分支判据）
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

    for title, text in load_dic(os.path.join('_w_W2_euchronia_trail', 'ta', 'dictionary.txt')):
        lines_out.append('【%s】%s' % (title, text))

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as w:
        for ln in lines_out:
            w.write(ln + '\n')
    print(stats)
    print('lines', len(lines_out), 'chars', sum(len(x) for x in lines_out))


if __name__ == '__main__':
    main()
