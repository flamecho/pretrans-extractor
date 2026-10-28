#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""白と黒のアリス for Nintendo Switch —— .qui(Lisp DSL) → 全文本（双版对照）

语法（L1/自定界）：
  `(message 話者 nil BODY...)`    一次点击＝一个文本框（ADV）⇒ 一行
  `(message-kw 話者 nil BODY...)` 同框追加（NVL）；连续 kw 段（其间只隔 message-nw）＝一页
  `(message-nw nil nil "\\n")`    换行，非文本
  `(message-clear)`               页边界
  `(select "a" "b" ...)`          选项，一行一条
  BODY = 若干字符串 ＋ `(str-append ...)`；`(name-w)`→愛日梨 / `(name-b)`→ルナ
"""
import os, sys, glob, re

SRC = '_w_W1_alice/out'
OUT = '提取结果/[NS-JP]白と黒のアリス for Nintendo Switch.txt'
NAME_W, NAME_B = '愛日梨', 'ルナ'
# 开发注释冒充正文（`sub story.たぶん◯◯用パラメータ` ×12、`Album Replay.たぶん◯◯用パラメータ` ×7）
SYS = re.compile(r'^(?:sub story|Album Replay)\.たぶん.+用パラメータ$')


def tokens(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in ' \t\r\n':
            i += 1
        elif c == ';':
            j = s.find('\n', i)
            i = n if j < 0 else j + 1
        elif c in '()':
            yield c
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                if s[j] == '\\' and j + 1 < n:
                    e = s[j + 1]
                    buf.append({'n': '\n', 't': '\t', '"': '"', '\\': '\\'}.get(e, e))
                    j += 2
                    continue
                if s[j] == '"':
                    break
                buf.append(s[j])
                j += 1
            yield ('STR', ''.join(buf))
            i = j + 1
        else:
            j = i
            while j < n and s[j] not in ' \t\r\n()";':
                j += 1
            yield ('ATOM', s[i:j])
            i = j


def parse(tok):
    stack = [[]]
    for t in tok:
        if t == '(':
            stack.append([])
        elif t == ')':
            if len(stack) > 1:
                f = stack.pop()
                stack[-1].append(f)
        else:
            stack[-1].append(t)
    return stack[0]


def head(f):
    if isinstance(f, list) and f and isinstance(f[0], tuple) and f[0][0] == 'ATOM':
        return f[0][1]
    return None


def is_str(x):
    return isinstance(x, tuple) and x[0] == 'STR'


def eval_body(x, out):
    """把 BODY（字符串 / (str-append ...) / (name-w) …）拼成纯文本。"""
    if is_str(x):
        out.append(x[1])
    elif isinstance(x, list):
        h = head(x)
        if h == 'str-append':
            for y in x[1:]:
                eval_body(y, out)
        elif h == 'name-w':
            out.append(NAME_W)
        elif h == 'name-b':
            out.append(NAME_B)
        elif h in ('str-insert', 'str-replace'):
            for y in x[1:]:
                eval_body(y, out)
    elif isinstance(x, tuple) and x[0] == 'ATOM':
        a = x[1]
        if a == "'white":
            out.append(NAME_W)
        elif a == "'black":
            out.append(NAME_B)


def body_text(f, start):
    out = []
    for x in f[start:]:
        eval_body(x, out)
    return ''.join(out)


def clean(t):
    t = t.replace('\n\u3000', '').replace('\n', '').replace('\r', '')
    return t.strip().strip('\u3000').strip()


def walk(f, ctx):
    """递归遍历，把消息/选项按出现顺序写入 ctx['out']。"""
    h = head(f)
    if h in ('message', 'message-kw'):
        txt = clean(body_text(f, 3))          # f[1]=話者 f[2]=nil f[3:]=BODY
        if txt:
            if h == 'message':
                ctx['flush']()
                ctx['out'].append(txt)
            else:
                ctx['page'].append(txt)
        return
    if h in ('message-nw', 'message-wait'):
        return
    if h in ('message-clear', 'meswin-open', 'meswin-close', 'novel-mode'):
        ctx['flush']()
        return
    if h == 'select':
        ctx['flush']()
        for x in f[1:]:
            if is_str(x):
                t = clean(x[1])
                if t:
                    ctx['out'].append(t)
        return
    for x in f:
        if isinstance(x, list):
            walk(x, ctx)


def make_ctx():
    ctx = {'out': [], 'page': [], 'nseg': 0, 'npage2': 0}

    def flush():
        p = ctx['page']
        if len(p) >= 2:
            ctx['out'].extend(p)
            ctx['out'].append(''.join(p))
            ctx['npage2'] += 1
        elif len(p) == 1:
            ctx['out'].append(p[0])
        ctx['nseg'] += len(p)
        ctx['page'] = []

    ctx['flush'] = flush
    return ctx


def main():
    files = sorted(glob.glob(os.path.join(SRC, 'ev[0-9]*.qui')))
    # scene 16 整章＝开发调试（「テストモード」章，正常游玩不可达）⇒ 全章剔除。
    #   ev1602 文字装飾/TODO 试验   ev1603 sysvalue 数值试验   ev1605 fadetype 试验
    #   ev1607/1608 レイヤー・フェード试验   ev1609 パーティクル试验   ev1610 加算试验
    #   ev1611 ボイス/BGM/SE 试验   ev1612 フィルタ试验   ev1613 好感度试验
    #   ev1614 Cut-In 试验   ev1615 名前入力テスト   ev1616 テストモード（章選択）
    # 判据：`(scene-set 16 nn)` ＋ 文件名 ev16xx；ev1601/1604/1606 无正文亦一并剔除
    SKIP = {'ev16%02d.qui' % i for i in range(1, 17)} | {'evtest.qui'}
    files = [p for p in files if os.path.basename(p) not in SKIP]
    allout = []
    seg = page2 = 0
    for p in files:
        s = open(p, encoding='utf-8-sig', errors='replace').read()
        ctx = make_ctx()
        for f in parse(tokens(s)):
            walk(f, ctx)
        ctx['flush']()
        allout.extend(ctx['out'])
        seg += ctx['nseg']
        page2 += ctx['npage2']
        print('%-14s 行 %5d  双版页 %d' % (os.path.basename(p), len(ctx['out']), ctx['npage2']))
    body = '\n'.join([t for t in allout if not SYS.match(t)]) + '\n'
    out = sys.argv[1] if len(sys.argv) > 1 else OUT
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(body)
    print('总行 %d（NVL 段 %d，其中双版页 %d）' % (len(allout), seg, page2))
    print('->', out)


if __name__ == '__main__':
    main()
