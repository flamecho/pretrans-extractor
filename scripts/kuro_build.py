# -*- coding: utf-8 -*-
"""蒼黒の楔 (NS-JP, Unity/Utage) 剧本 → 全文本（双版对照）

链路: XCI -> NCA(Standard crypto) -> RomFS -> Data/StreamingAssets/Soukoku/Switch/boot.chapter.asset
      (UnityFS, MonoBehaviour AdvImportBook; rows=[Command,Arg1..6,WaitType,Text,PageCtrl,Voice,WindowType])
      -> scripts/kuro_dump.py 落 all.jsonl -> 本脚本成行。

断框（L0，引擎列 PageCtrl＝Utage AdvCommandText.PageCtrlType）:
  A 类 = '' / 'Next'  -> 一页结束（换页清框）
  B 类 = 'InputBr'    -> 框内等待，文字在原框续接（不清框）
  ⇒ 两指令并存 ⇒ 只交「双版对照」：同框先列各段，再列合并行 A,B,C,ABC。

名札: 文本行 Arg1 列＝独立名字窗内容 ⇒ 整列丢弃（不加前缀）。
主角名: <param==main_p_name|fd_p_name> 珠紀 / *_p_familyname 春日 / *_o_name おーちゃん
        （默认值取自 sharedassets1.assets MonoBehaviour 804 的参数表）。

用法: python scripts/kuro_build.py <all.jsonl> <out.txt> [--dict 目录]
"""
import json, csv, os, re, sys

PARAM = {
    'main_p_name': '珠紀', 'fd_p_name': '珠紀',
    'main_p_familyname': '春日', 'fd_p_familyname': '春日',
    'main_o_name': 'おーちゃん', 'fd_o_name': 'おーちゃん',
}

# 收录的 book（剧本正文/短篇/教学），按故事顺序
BOOKS = ['本編_シナリオ.book', '本編_映し鏡.book', '本編_思い出.book', '本編_チュートリアル.book',
         'FD_シナリオ.book', 'FD_200写し鏡.book', 'FD_300個別.book', 'FD_400おまけ.book']

# 分支/场景边界：这些命令出现即断开同框累积
BREAK_CMDS = {'If', 'Else', 'ElseIf', 'EndIf', 'Jump', 'JumpSubroutine', 'JumpRandom',
              'EndScenario', 'EndThread', 'Thread', 'Selection', 'SelectionEnd',
              'SelectionClick', 'SelectionClickEnd', 'ChangeMessageWindow',
              'HideMessageWindow', 'ShowMessageWindow', 'MessageWindowInit'}

TAG = re.compile(r'<[^<>]{1,80}>')


def clean(t):
    for k, v in PARAM.items():
        t = t.replace('<param==%s>' % k, v)
    t = TAG.sub('', t)
    t = t.replace('\r', '')
    # 软换行合并：逐行去首尾空白后拼接；ASCII 词间补一个空格（避免 promise/I'll 粘连）
    lines = [ln.strip(' \u3000\t') for ln in t.split('\n')]
    buf = ''
    for ln in lines:
        if not ln:
            continue
        if buf and re.search(r'[A-Za-z0-9]$', buf) and re.match(r'[A-Za-z0-9]', ln):
            buf += ' '
        buf += ln
    return buf


def build(jsonl):
    R = [json.loads(l) for l in open(jsonl, encoding='utf-8')]
    out = []          # 对照版行
    n_click = 0       # 点击版行数
    n_page = 0        # 页版行数
    n_multi = 0       # 多段框数
    n_b = 0           # B 类段数
    n_opt = 0         # 选项行数
    segs = []
    cur = None

    def flush():
        nonlocal n_click, n_page, n_multi, segs
        if not segs:
            return
        n_page += 1
        n_click += len(segs)
        if len(segs) == 1:
            out.append(segs[0])
        else:
            out.extend(segs)
            out.append(''.join(segs))
            n_multi += 1
        segs = []

    for bk in BOOKS:
        for x in R:
            if x['b'] != bk:
                continue
            s = x['s']
            key = (x['b'], x['g'])
            if key != cur:
                flush()
                cur = key
            cmd, text, pc = s[0], s[8], s[9]
            if cmd == 'Command' and text == 'Text':     # 表头行
                continue
            if cmd == 'Selection':
                flush()
                t = clean(text)
                if t:
                    out.append(t); n_click += 1; n_page += 1; n_opt += 1
                continue
            if cmd:
                if cmd in BREAK_CMDS:
                    flush()
                continue
            if not text:
                continue
            t = clean(text)
            if not t:
                continue
            if pc == 'InputBr':
                segs.append(t); n_b += 1
            else:                                        # '' / 'Next' = A 类
                segs.append(t)
                flush()
    flush()
    return out, n_click, n_page, n_multi, n_b, n_opt


def load_dict(d):
    ent = []
    for fn in ('DICT.csv', 'DICT_FD.csv'):
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            continue
        for row in csv.reader(open(p, encoding='utf-8-sig')):
            if len(row) < 4 or not row[1].strip():
                continue
            term = row[1].strip()
            desc = row[3].replace('\\n', '').replace('\n', '').strip()
            desc = clean(desc)
            if term and desc:
                ent.append('【%s】%s' % (term, desc))
    return ent


def main():
    src, dst = sys.argv[1], sys.argv[2]
    ddir = None
    if '--dict' in sys.argv:
        ddir = sys.argv[sys.argv.index('--dict') + 1]
    lines, nc, np_, nm, nb, no = build(src)
    if ddir:
        lines += load_dict(ddir)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('点击版=%d  页版=%d  多段框=%d  B类段=%d  选项=%d  对照版=%d' % (nc, np_, nm, nb, no, len(lines)))
    print('闭合: 点击版(含选项)=%d = 页版 + B类段 => %s ; 对照版=%d = 点击版+多段框+辞典' % (
        nc, (nc - nb == np_), len(lines)))


if __name__ == '__main__':
    main()
