#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ariard / Latte (KiriKiri/KAG3) 成行器 —— 第八变体 XP3 专用

支持两作：
    under-the-rose : [JP]Ariard-少年アリス - Under the rose  (有 scenario/list.txt)
    alice          : [JP]Ariard-少年アリス-                 (无 list.txt, 有 patch.xp3 覆盖)

断框判据（全部来自 system/MainWindow.tjs 的标签表原文，非猜测）：
    c   = @macro "c"  -> @p 改ページ            一次点击
    c2  = @macro "c2" -> @c                     一次点击
    lr  = @macro "lr" -> @l 行クリック待ち       一次点击
    l   = showLineBreak()   // 行クリック待ち    一次点击
    p   = showPageBreak()   // ページクリック待ち 一次点击
    r   = processReturn()   // 改行  return actualChSpeed  <- 无等待 => 框内软换行, 合并
    ch  = text= 属性直接插字                      -> 原样输出
    ruby= text= 属性是振假名读音                  -> 丢弃读音, 保留后随基字
    selset = text= 属性即选项按钮文字              -> 选项行
    ps  = 独立名字窗 (gsys/standPlugin.ks: name_obj.showNameLayer) -> 正文剔除

MainWindow.tjs 原文（[r] 无等待）：
    r : function(elm){ // 改行
        if(currentWithBack) current.comp.processReturn();
        if(current.processReturn()){ var ret = showPageBreakAndClear(); ... }
        return actualChSpeed;
    }
    l : function(elm){ // 行クリック待ち
        return showLineBreak(elm);
    }
    p : function(elm){ // ページクリック待ち
        if(historyWriteEnabled) historyLayer.reline();
        return showPageBreak(elm);
    }

用法:
    python scripts/ariard_extract.py stats <src_root> [patch_dir]
    python scripts/ariard_extract.py build <src_root> <out.txt> [patch_dir]
"""
import os
import re
import sys
import collections

BREAK = {'c', 'c2', 'lr', 'l', 'p'}
SOFT = {'r'}
DROP_TEXT_ATTR = {'ruby'}          # 读音, 丢弃

TAG = re.compile(r'\[([^\]\n]*)\]')
ATTR_TEXT = re.compile(r'text=("[^"]*"|[^\s\]]+)')

# alice 篇：无 list.txt，按 [jump] 图与章号重建的阅读顺序
# (子目录, 文件名, 是否被 patch.xp3 覆盖)
ALICE = [
    ('共通', ['00_chap_01', '00_chap_02', '00_chap_03', '00_chap_04',
              '00_chap_05',                    # 主线；分支插入点在下方五个
              '00_chap_05_rab', '00_chap_05_cat', '00_chap_05_hat',
              '00_chap_05_d', '00_chap_05_pupa',
              '00_chap_06']),                  # 六话收尾共通，之后 @if 分到各线七话
    ('白兎', ['01_chap_06_rab1', '01_chap_07_rab1', '01_chap_08_rab1',
              '01_chap_08_rab2', '01_chap_09_rab1', '01_chap_09_rab2',
              '01_chap_10_rab1', '01_chap_10_rab2']),
    ('チェシャ猫', ['02_chap_06_cat1', '02_chap_07_cat1', '02_chap_08_cat1',
                    '02_chap_09_cat1', '02_chap_09_cat2',
                    '02_chap_10_cat1', '02_chap_10_cat2']),
    ('帽子屋', ['03_chap_06_hat1', '03_chap_07_hat1', '03_chap_08_hat1',
                '03_chap_09_hat1', '03_chap_09_hat2',
                '03_chap_10_hat1', '03_chap_10_hat2']),
    ('双子', ['04_chap_06_d1', '04_chap_07_d1', '04_chap_08_d1',
              '04_chap_08_d2', '04_chap_09_d1', '04_chap_09_d2',
              '04_chap_09_d3', '04_chap_10_d1', '04_chap_10_d2',
              '04_chap_10_d3']),
    ('蛹', ['05_chap_06_pupa1', '05_chap_07_pupa1', '05_chap_07_pupa2',
            '05_chap_08_pupa1', '05_chap_09_pupa1', '05_chap_09_pupa2',
            '05_chap_10_pupa1', '05_chap_10_pupa2']),
    ('バッド', ['10_bad_01', '10_bad_02', '10_bad_03', '10_bad_04',
                '10_bad_06', '10_bad_07', '10_bad_08']),   # 原作即无 05
    ('',      ['comp_ss']),                                # 番外 SS（@ssmsg 全屏文本）
]


def unq(v):
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v


def tag_name(tag):
    t = tag.strip()
    if not t:
        return ''
    return re.split(r'[\s=]', t, 1)[0]


def parse_file(path):
    """返回 [(kind, text)]，kind in {'text','choice'}"""
    d = open(path, 'rb').read().decode('cp932')
    d = d.replace('\r\n', '\n').replace('\r', '\n')
    rows = []
    buf = []
    choices = []
    diag = collections.Counter()

    def flush():
        t = ''.join(buf).strip(' \t\u3000')
        buf.clear()
        if t:
            rows.append(('text', t))
            return True
        return False

    for line in d.split('\n'):
        s = line.strip()
        if not s:
            continue
        if s[0] == ';' or s[0] == '*' or s[0] == '@':
            if s[0] == '@':
                diag['atcmd:' + s.split()[0]] += 1
            continue

        pos = 0
        for m in TAG.finditer(line):
            frag = line[pos:m.start()].strip(' \t')
            if frag:
                buf.append(frag)
            body = m.group(1)
            name = tag_name(body)
            if name == 'ch':
                mm = ATTR_TEXT.search(body)
                if mm:
                    buf.append(unq(mm.group(1)))
                else:
                    diag['ch_no_text'] += 1
            elif name in DROP_TEXT_ATTR:
                # ruby: text= 是读音, 后随基字才是正文; 丢弃时不追加任何内容
                diag['drop_' + name] += 1
            elif name == 'selset':
                mm = ATTR_TEXT.search(body)
                if mm:
                    flush()                      # 选项提示句先落地
                    choices.append(unq(mm.group(1)))
                else:
                    diag['selset_no_text'] += 1
            elif name == 'select':
                flush()
                rows.extend(('choice', c) for c in choices)
                choices = []
            elif name in BREAK:
                if flush():
                    diag['flush_' + name] += 1
            elif name in SOFT:
                diag['soft_' + name] += 1
            else:
                diag['tag:' + name] += 1
            pos = m.end()

        frag = line[pos:].strip(' \t')
        if frag:
            buf.append(frag)

    if flush():
        diag['flush_eof'] += 1
    if choices:
        rows.extend(('choice', c) for c in choices)
        diag['choice_at_eof'] += len(choices)
    return rows, diag


def sources(src_root, patch_dir=None):
    """返回 [(显示名, 实际路径)]；patch_dir 中同名文件优先"""
    out = []
    lst = os.path.join(src_root, 'list.txt')
    if os.path.exists(lst):
        # rose 篇：list.txt 给主线顺序，其后接番外 SS
        for line in open(lst, 'rb').read().decode('cp932').split('\n'):
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            p = os.path.join(src_root, s.replace('/', os.sep))
            if os.path.exists(p):
                out.append((s, p))
        import glob
        for p in sorted(glob.glob(os.path.join(src_root, '*_omake_ss.ks'))):
            out.append((os.path.basename(p), p))
        return out

    for sub, names in ALICE:
        for nm in names:
            base = os.path.join(src_root, sub, nm + '.ks') if sub else \
                   os.path.join(src_root, nm + '.ks')
            p = base
            if patch_dir:
                cand = os.path.join(patch_dir, nm + '.ks')
                if os.path.exists(cand):
                    p = cand
            if not os.path.exists(base):
                raise SystemExit('缺少源文件: %s' % base)
            label = (sub + '/' if sub else '') + nm + '.ks'
            if p != base:
                label += '  [patch]'
            out.append((label, p))
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    mode = sys.argv[1]
    src_root = sys.argv[2]
    if mode == 'stats':
        out_path = None
        patch_dir = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        if len(sys.argv) < 4:
            print(__doc__)
            return 2
        out_path = sys.argv[3]
        patch_dir = sys.argv[4] if len(sys.argv) > 4 else None

    srcs = sources(src_root, patch_dir)
    all_rows = []
    total_diag = collections.Counter()
    per = []
    for label, p in srcs:
        rows, diag = parse_file(p)
        per.append((label, len(rows), sum(1 for k, _ in rows if k == 'choice')))
        all_rows.extend(rows)
        total_diag.update(diag)

    if mode == 'stats':
        print('文件 %d 个' % len(srcs))
        for label, n, nc in per:
            print('  %-34s %5d 行%s' % (label, n, ('  (选项 %d)' % nc) if nc else ''))
        ntext = sum(1 for k, _ in all_rows if k == 'text')
        nch = sum(1 for k, _ in all_rows if k == 'choice')
        print('合计 %d 行 = 正文 %d + 选项 %d' % (len(all_rows), ntext, nch))
        print('空冲刷：', {k: v for k, v in total_diag.items() if k.startswith('flush_')})
        print('软换行 [r] 合并点：', total_diag.get('soft_r', 0))
        print('振假名 [ruby] 丢弃：', total_diag.get('drop_ruby', 0))
        lens = [len(t) for _, t in all_rows]
        print('最长行 %d 字符；平均 %.1f' % (max(lens), sum(lens) / len(lens)))
        bad = [(k, t) for k, t in all_rows if '[' in t or ']' in t]
        print('残留括号行：', len(bad))
        for k, t in bad[:5]:
            print('   ', t[:120])
        other = {k: v for k, v in total_diag.items()
                 if not k.startswith('flush_') and k not in ('soft_r', 'drop_ruby')}
        print('其它标签/命令计数：')
        for k, v in sorted(other.items(), key=lambda x: -x[1]):
            print('   %-22s %d' % (k, v))
        return 0

    if mode == 'build':
        text = '\n'.join(t for _, t in all_rows) + '\n'
        os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(b'\xef\xbb\xbf')
            f.write(text.encode('utf-8'))
        print('写出 %s  %d 行  %d 字节' % (out_path, len(all_rows), os.path.getsize(out_path)))
        return 0

    print('unknown mode', mode)
    return 2


if __name__ == '__main__':
    sys.exit(main())
