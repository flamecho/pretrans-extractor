#!/usr/bin/env python3
"""wrapup.py —— **一条命令跑完收尾（S8）**：品检 → 手册对账 → 沉淀草案 → 落位片段。

为什么有它：收尾慢在「四件事分别跑、结果分散、还得自己记着谁没做」。
本工具把它们串起来，最后只输出**一张待办清单**（机器能判的都判完）。

用法:
  python scripts/wrapup.py --report "解析报告/XX_解析报告.md" \
                           --text "提取结果/[PSV-JP]XX_全文本.txt" --name 主角名
  # 只跑部分
  python scripts/wrapup.py --report R.md                 # 不跑品检
  python scripts/wrapup.py --text T.txt --name X         # 不跑沉淀/落位

参数:
  --report  解析报告（做沉淀草案 + 落位片段）
  --text    成品 txt（跑 check_text）
  --name    主角名（check_text 用）
  --game    作品名（缺省从报告 H1 推）
  --apply   把 WORKS / TOOLS 片段直接追加到目标册（默认只生成）
  --no-distill / --no-archive  跳过对应步骤

退出码: 0 = 机器项全过; 1 = 有 [E]/待沉淀，需人工处理
"""
import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or 'python'


def run(script, args):
    cmd = [PY, os.path.join(HERE, script)] + args
    p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def tail(text, n=6):
    ls = [l for l in text.split('\n') if l.strip()]
    return ls[-n:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report')
    ap.add_argument('--text')
    ap.add_argument('--name')
    ap.add_argument('--game')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--no-distill', action='store_true')
    ap.add_argument('--no-archive', action='store_true')
    a = ap.parse_args()
    if not a.report and not a.text:
        print('至少给 --report 或 --text')
        return 2

    todo, hard = [], []

    # ① 成品品检
    if a.text:
        args = [a.text] + (['--name', a.name] if a.name else [])
        rc, out = run('check_text.py', args)
        e = len(re.findall(r'\[E\]', out))
        w = len(re.findall(r'\[W\]', out))
        tag = 'PASS' if rc == 0 else 'FAIL'
        print('[1/4] 成品品检  %s   E=%d W=%d' % (tag, e, w))
        if rc != 0 and e == 0 and w == 0:
            for l in tail(out, 3):
                print('       原因：', l.strip()[:160])
        for l in tail(out, 4):
            if '[E]' in l or '[W]' in l:
                print('      ', l.strip()[:150])
        if rc != 0:
            hard.append('品检未通过（退出码 %d）⇒ 修完再交付' % rc)
    else:
        print('[1/4] 成品品检  跳过（未给 --text）')

    # ①b 行数一致性：报告声称的行数 vs 成品实际行数（防「用错文件 / 成品过期」）
    if a.text and a.report and os.path.isfile(a.report):
        try:
            sys.path.insert(0, HERE)
            from archive_work import infer
            d = infer(a.report)
            claim = re.sub(r'[^\d]', '', (d.get('rows') or ''))
            if claim and os.path.isfile(a.text):
                raw = open(a.text, 'rb').read()
                actual = raw.count(b'\n') + (0 if raw.endswith(b'\n') else 1)
                if abs(actual - int(claim)) > max(3, int(claim) * 0.01):
                    print('[1b] 行数一致性  [W] 报告 %s 行 ≠ 成品 %d 行' % (claim, actual))
                    todo.append('核对行数差异：报告 `%s` vs 成品 `%d`（是否用错文件 / 成品过期 / 报告未更新）'
                                % (claim, actual))
                else:
                    print('[1b] 行数一致性  OK（报告 %s / 成品 %d）' % (claim, actual))
        except Exception as e:
            print('[1b] 行数一致性  跳过（%s）' % type(e).__name__)

    # ①c 切行判据三行（S6-lines-proof §7）：缺了就提示补报告 —— 别让「猜的行粒度」静默过关
    if a.report and os.path.isfile(a.report):
        try:
            r = open(a.report, encoding='utf-8-sig', errors='replace').read()
            has_key = bool(re.search(r'断框判据|框界|换框|点击边界', r))
            has_proof = bool(re.search(r'L0|L1|覆盖率|串起点|必现|反例|未证|交叉验证|行数演算|直方图|全库|\d{2,}\s*(?:次|条|处)', r))
            l2 = bool(re.search(r'L2|未证|文本形态', r))
            if has_key and has_proof:
                print('[1c] 切行判据  OK%s' % ('（L2/未证已标注 ⇒ 需补代码级证据）' if l2 else ''))
            else:
                print('[1c] 切行判据  [W] 报告缺「断框判据 / 自证」三行')
                todo.append('补报告切行判据三行（`断框判据`/`自证`/`残余`）→ skill `S6-lines-proof.md` §7')
        except Exception as e:
            print('[1c] 切行判据  跳过（%s）' % type(e).__name__)

    # ② 手册对账（体积不再判：2026-10-26 取消硬线，该拆与否只看主题）
    rc, out = run('lint_docs.py', [])
    m = re.search(r'断链 (\d+) ｜ 路由缺 (\d+) ｜ 孤儿 (\d+) ｜ 空册 (\d+)', out)
    if m:
        print('[2/4] 手册对账  断链 %s / 路由缺 %s / 孤儿 %s / 空册 %s' % m.groups())
    else:
        print('[2/4] 手册对账  %s' % ('OK' if rc == 0 else '有问题'))
    if rc != 0:
        for l in tail(out, 12):
            s = l.strip()
            if s and not s.startswith('---'):
                print('      ', s[:160])
        todo.append('修手册对账：`python scripts/lint_docs.py`（断链 → 改指向；孤儿 → 进 00-index）')

    # ③ 沉淀草案
    if a.report and not a.no_distill:
        args = ['--report', a.report]
        if a.name:
            args += []
        rc, out = run('distill.py', args)
        m = re.search(r'候选 (\d+) ｜ 待沉淀 (\d+) ｜ 单作特例 (\d+) ｜ 已覆盖 (\d+)', out)
        path = ''
        mm = re.search(r'草案：(.+)', out)
        if mm:
            path = mm.group(1).strip()
        if m:
            c, t, lc, d = m.groups()
            print('[3/4] 沉淀草案  候选 %s / 待沉淀 %s / 单作特例 %s / 已覆盖 %s' % (c, t, lc, d))
            for ln in out.split('\n'):
                if ln.startswith('   →'):
                    print('      ', ln.strip()[:120])
            if int(t) > 0:
                todo.append('沉淀 %s 条 → 打开 `%s` 勾选后落位' % (t, path))
        else:
            err = [l for l in out.split('\n') if 'Error' in l or 'Exception' in l]
            print('[3/4] 沉淀草案  [!!] 未产出：%s' % (err[-1].strip()[:160] if err else '见上'))
            hard.append('distill 失败')
    else:
        print('[3/4] 沉淀草案  跳过')

    # ④ 落位片段
    if a.report and not a.no_archive:
        args = ['--report', a.report] + (['--apply'] if a.apply else [])
        if a.game:
            args = ['--report', a.report, '--name', a.game] + (['--apply'] if a.apply else [])
        rc, out = run('archive_work.py', args)
        print('[4/4] 落位片段')
        for l in out.split('\n'):
            if re.match(r'^(作品|平台|行数|工具|判据|落位|片段|  \[)', l):
                print('      ', l.strip()[:150])
        if rc != 0:
            hard.append('落位片段生成失败（见上）')
        elif not a.apply:
            todo.append('落位片段已生成 → 核对后加 `--apply` 追加到 WORKS / TOOLS 册')
    else:
        print('[4/4] 落位片段  跳过')

    print('\n--- 收尾待办（%d 项）---' % (len(hard) + len(todo)))
    n = 0
    for h in hard:
        n += 1
        print('%d. [必做] %s' % (n, h))
    for t in todo:
        n += 1
        print('%d. %s' % (n, t))
    if n == 0:
        print('（无；可直接交付）')
    return 1 if hard else 0


if __name__ == '__main__':
    sys.exit(main())
