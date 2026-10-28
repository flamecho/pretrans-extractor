"""批量生成字符台账：对 `提取结果/` 下全部成品跑 `check_text --init-charset`。"""
import os
import subprocess
import sys
import io

if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__.strip())
    print('\n用法：在「成品所在目录」下直接运行（无参数）—— 遍历 ./提取结果/*.txt，'
          '逐个跑 check_text --init-charset 再复检。')
    raise SystemExit(0)

T = '提取结果'
if not os.path.isdir(T):
    raise SystemExit('× 当前目录没有「%s/」——本脚本要在成品根目录下跑（cd 到含 提取结果/ 的那层）。' % T)
SPECIAL = {
    '[NS-JP]十三支演義 偃月三国伝1・2 for Nintendo Switch': ('scripts/jusanshi_allow.txt', False),
    '[NS-JP]白と黒のアリス for Nintendo Switch': ('解析报告/allow/[NS-JP]白と黒のアリス for Nintendo Switch.txt', True),
    '[NS-JP]闇色の魔珠': ('解析报告/allow/[NS-JP]闇色の魔珠.txt', True),
}


def run(p, al, dual, init):
    cmd = [sys.executable, 'scripts/check_text.py', p, '--quiet']
    if os.path.exists(al):
        cmd += ['--allow', al]
    if dual:
        cmd += ['--dual', '--expect-dual']
    if init:
        cmd += ['--init-charset']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    errs = [l.strip() for l in (r.stdout + r.stderr).split('\n') if '[E]' in l]
    return r.returncode, errs


ok = 0
bad = []
tot = 0
for f in sorted(os.listdir(T)):
    if not f.endswith('.txt'):
        continue
    k = f[:-4]
    p = os.path.join(T, f)
    al, dual = SPECIAL.get(k, ('解析报告/allow/%s.txt' % k, False))
    run(p, al, dual, True)
    rc, errs = run(p, al, dual, False)
    n = sum(1 for x in io.open(p, encoding='utf-8-sig') if x.strip())
    tot += n
    if rc == 0:
        ok += 1
    else:
        bad.append((k, n, errs[:2]))
    print('%-46s %6d  %s' % (k[:46], n, 'PASS' if rc == 0 else 'FAIL'))
print('\nPASS %d/27｜总行数 %d' % (ok, tot))
for k, n, e in bad:
    print('FAIL', k[:46], n)
    for x in e:
        print('   ', x[:130])
