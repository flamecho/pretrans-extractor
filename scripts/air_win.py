"""打印某个 ABC 偏移附近的反汇编窗口。"""
import sys

sys.path.insert(0, 'tools')
sys.path.insert(0, '_work_rakido')
import air_abc as A
import air_body as B

t = int(sys.argv[1], 0)
before = int(sys.argv[2]) if len(sys.argv) > 2 else 30
after = int(sys.argv[3]) if len(sys.argv) > 3 else 60

d = B.abc_bytes('_work_rakido/app.swf')
bodies = B.find_bodies(d)
r = B.body_of(bodies, t)
if not r:
    print('no body covers %#x' % t)
    raise SystemExit(1)
rec, cs, cl, mid = r
print('# body method=%d  code=%#x len=%d  target=+%d' % (mid, cs, cl, t - cs))
import sh as SH
S = SH.Sh()
out = A.disasm(S, d[cs:cs + cl])
idx = None
for i, (at, _) in enumerate(out):
    if cs + at == t:
        idx = i
        break
lo = max(0, (idx if idx is not None else 0) - before)
hi = min(len(out), (idx if idx is not None else 0) + after)
for at, txt in out[lo:hi]:
    print('%s %04x  %s' % ('>>>' if cs + at == t else '   ', cs + at, txt))
print('# decoded %d insns, %d bytes of %d' % (len(out), out[-1][0] if out else 0, cl))
