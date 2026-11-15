# -*- coding: utf-8 -*-
"""VB5 自研 AVG（剧本库＝Access Jet `.MDB`，台本＝日文指令 DSL）→ 「一次点击 = 一行」。

适用：PC 老作里「`.MDB` 头 = `00 01 00 00 "Standard Jet DB"`」的剧本库（本例 BOY×BOY 2005）。
依赖：`pip install access_parser`（纯 Python，不需要装 Office/Jet 驱动）。

    python mdb_scen_text.py --mdb <BOYxBOY.MDB> --out 成品.txt [--dump lines.txt] [--table ScenData]

DSL（每行一条指令，`：` 分隔，`//` 注释）：
    台詞：  台词（同框可多条）       文字：  地の文/ナレーション
    名前：  说话人（独立指令 ⇒ 独立名字窗 ⇒ 剔除）   待つ：  等待（0000=等点击）
    選択：/献立：  选项（取 \\t 前文本）         DATA,/MENU,（含 受信：前缀）  掲示板/メール

判据（L0）：**`待つ：` 是引擎的等待指令 ⇒ 相邻两个 `待つ：` 之间的文本＝同一消息框**，合并成一行。
反向验证（仅验收）：每个 `待つ：` 前最多 4 条文本行（0:42/1:7,727/2:3,296/3:584/4:2 ⇒ 框高 4 行）；
单行 12〜22 字（框宽约 20 字）。详见解析报告 §6。
"""
import argparse, io, re, sys, collections

FMT = re.compile(r'%%\d')          # 内联颜色/格式标记
ESC = re.compile(r'\\[A-Za-z]')    # 掲示板转义 \H \B \C...\c \b \h \J \K0 \k..\j..
HEAD = re.compile(r'^([^\s：,、]{1,8})[：,]')


def dec(s):
    """access_parser 把 cp932 字节按 latin1 解出 ⇒ 复原"""
    if isinstance(s, str):
        try:
            return s.encode('latin1').decode('cp932')
        except Exception:
            return s
    return '' if s is None else str(s)


def clean(t):
    return ESC.sub('', FMT.sub('', t)).strip()


def load(mdb, table='ScenData'):
    from access_parser import AccessParser
    db = AccessParser(mdb)
    d = db.parse_table(table)
    return [(dec(a), dec(b), dec(c)) for a, b, c in zip(d['sSceID'], d['sTitle'], d['mScena'])]


def order_key(i):
    """剧本顺序：MMDD-xx-yy 按日期 → 其余按 ID"""
    m = re.match(r'^(\d{4})-(\d+)-(\d+)(?:-(\d+))?', i)
    if m:
        return (0, m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0), '')
    return (1, i, 0, 0, 0, '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mdb', required=True)
    ap.add_argument('--table', default='ScenData')
    ap.add_argument('--out')
    ap.add_argument('--dump')
    ap.add_argument('--skip', default='_START,_OP,_ENDING,_S0000,_DEBUG,_EXEC,_INIT,_SAVELOAD,_KEYCHECK,-------,#Version')
    ap.add_argument('--board', default='_KEI_,_MAIL', help='掲示板/メール类 ID 前缀（逗号分隔）')
    ap.add_argument('--only', default=r'^(\d{4}-|SA[0-9A-Z]|SS\d|K[0-9]|SH\d|_外出|__外出|_NET|__NET|_DAYPASS|_HOLYDAY|_S06$|_KEI_|_MAIL)',
                    help='只收 ID 匹配该正则的脚本（其余＝系统/调试，排除）')
    a = ap.parse_args()
    SKIP = {x for x in a.skip.split(',') if x}
    BOARD = tuple(x for x in a.board.split(',') if x)

    ONLY = re.compile(a.only)
    rows = [r for r in load(a.mdb, a.table) if ONLY.match(r[0])]
    body, opts, board = [], [], []
    for sid, title, s in rows:
        if not s.strip() or sid in SKIP:
            continue
        if sid.startswith(BOARD):                       # 掲示板/メール：slot0 一条投稿=一行；slot≠0 一条一行
            cur = None
            for line in s.split('\r\n'):
                if line.startswith('受信：'):
                    line = line[3:]
                if line.startswith('MENU,'):
                    if cur:
                        board.append(cur.strip())
                    m = re.search(r'\\k(.*?)\\j(.*)$', line)
                    cur = clean(m.group(1)) + clean(m.group(2)) if m else ''
                elif line.startswith('DATA,'):
                    f = line.split(',', 2)
                    idx = f[1].strip() if len(f) > 2 else '0'
                    tx = clean(f[2] if len(f) > 2 else '')
                    if not tx:
                        continue
                    if idx == '0':                      # 正文槽：并入当前投稿
                        cur = (cur or '') + tx
                    else:                               # 其它槽＝并列条目/分支变体（互斥）⇒ 各自成行
                        if cur:
                            board.append(cur.strip())
                            cur = ''
                        board.append(tx)
            if cur and cur.strip():
                board.append(cur.strip())
            continue
        pend = []
        for line in s.split('\r\n'):
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('DATA,'):
                continue
            cmd, _, arg = line.partition('：')
            if cmd in ('台詞', '文字'):
                pend.append(clean(arg))
            elif cmd == '待つ':                          # ★ 一次显示单位的边界
                if pend:
                    body.append((order_key(sid), sid, ''.join(pend)))
                    pend = []
            elif cmd in ('選択', '献立'):
                t = arg.split('\t')[0].strip()
                if t:
                    opts.append((order_key(sid), sid, clean(t)))
        if pend:
            body.append((order_key(sid), sid, ''.join(pend)))
    body.sort(key=lambda x: x[0])
    opts.sort(key=lambda x: x[0])
    lines = [t for *_r, t in body] + [t for *_r, t in opts] + board
    print('正文 %d 行 ／ 选项 %d 项 ／ 掲示板·メール %d 条 → 合计 %d 行（%d 字）'
          % (len(body), len(opts), len(board), len(lines), sum(len(x) for x in lines)))
    if a.dump:
        with io.open(a.dump, 'w', encoding='utf-8', newline='\n') as f:
            for _k, sid, t in body:
                f.write('%s\t%s\n' % (sid, t))
    if a.out:
        with io.open(a.out, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('\n'.join(lines) + '\n')
        print('→ %s' % a.out)


if __name__ == '__main__':
    main()
