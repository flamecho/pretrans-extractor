"""批量复检 `提取结果/`：按双版清单逐个跑 `check_text`，汇总 PASS/FAIL 并列出 E/W。"""
import glob,os,re,subprocess,sys

if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
    print(__doc__.strip())
    print('\n用法：在成品根目录下直接运行（无参数）—— 按 解析报告/ 与双版清单逐个跑 check_text。')
    raise SystemExit(0)
def pure(s):
    s=re.sub(r'`[^`]*`','',s).replace('**','').strip()
    return re.split(r'[（(／、，,\s]',s)[0].strip()
DUAL={'END END SUMMER','Last Convert','Pentagon Syndrome','星と鴉の屑籠影絵旅','落下点','落下点2','DistortedCode ―生者の残り香―'}
res=[]
for f in sorted(glob.glob('提取结果/*.txt')):
    n=os.path.basename(f)[:-4]; nm2=re.sub(r'^\[[^\]]+\]','',n)
    rp=f'解析报告/{n}_解析报告.md'; ap=f'解析报告/allow/{n}.txt'
    name=''
    if os.path.exists(rp):
        t=open(rp,encoding='utf-8',errors='replace').read()
        m=re.search(r'^\- \*\*主角名?名?\*\*[：:]\s*(.+)$',t,re.M) or re.search(r'^\- \*\*主角\*\*[：:]\s*(.+)$',t,re.M)
        if m:
            p=pure(m.group(1))
            if p and not re.search(r'无|玩家|ELF',p) and len(p)<=12: name=p
    cmd=[sys.executable,'scripts/check_text.py',f,'--report',rp,'--quiet']
    if name: cmd+=['--name',name]
    if os.path.exists(ap): cmd+=['--allow',ap]
    if nm2 in DUAL: cmd+=['--dual','--expect-dual']
    r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace')
    out=r.stdout+r.stderr
    es=[l.strip() for l in out.splitlines() if l.startswith('[E]')]
    ws=[l.strip() for l in out.splitlines() if l.startswith('[W]')]
    dvm=re.search(r'\[i\] 版式：(.+?)（',out)
    res.append((n,r.returncode,es,ws,dvm.group(1) if dvm else '?',name))
# 结果只打印到 stdout，**不落盘**——别在当前目录建 `_recheck/`（2026-10-27 清掉一处调试残留：
# 曾硬编码写 `_recheck/52.md`，每跑一次就污染一次运行目录，还被带进了发行包）。
fails=[x for x in res if x[1]!=0]
print(f'总计 {len(res)} · PASS {len(res)-len(fails)} · FAIL {len(fails)}')
for n,rc,es,ws,dv,name in fails:
    print(f'\n### {n}\n  版式={dv} 名={name}')
    for e in es[:6]: print('   '+e[:150])
