"""ABC 方法体（method_body_info）定位器。

不依赖 class/trait 段解析（该 SWF 的 class 段比标准偏移 3 字节，全量解析会失步），
改用**结构反推**：方法体 code 通常以 `d0 30`（getlocal0; pushscope）开头，而它前面
正好是 6 个 u30：

    u30 method_idx, max_stack, local_count, init_scope_depth, max_scope_depth, code_len

对每个 `d0 30` 位置 q，向前试 k=1..15 字节，从 q-k 读 6 个 u30，若正好停在 q
且各字段落在合理区间，就认定 (q-k, q, code_len) 是一个方法体。

用法：
    python scripts/air_body.py <app.swf>            # 打印统计
    python scripts/air_body.py <app.swf> 0x1e67a    # 反汇编覆盖该偏移的方法
"""
import sys
import re

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
import air_abc as A

PROLOGUES = (b'\xd0\x30', b'\xd0\x30\x57', b'\xd0\x30\x2a')


def abc_bytes(swf_path):
    body = A.load_swf(swf_path)
    pl = [x for c, x in A.swf_tags(body) if c == 82][0]
    off = pl.index(0, 4) + 1 if pl[:4] == b'\x01\x00\x00\x00' else 1
    return pl[off:]


def find_bodies(d, nmeth=3000):
    """返回 [(rec_off, code_start, code_len, method_idx)]，按 code_start 升序。"""
    n = len(d)
    prols = [m.start() for m in re.finditer(re.escape(PROLOGUES[0]), d)]
    out = []
    for q in prols:
        for k in range(1, 16):
            p = q - k
            if p < 0:
                break
            try:
                vals = []
                pp = p
                ok = True
                for _ in range(6):
                    v, pp = A.u30(d, pp)
                    vals.append(v)
                if pp != q:
                    continue
                mid, mstack, nlocal, isc, msc, clen = vals
                if not (0 < mid <= nmeth):
                    continue
                if not (0 <= mstack < 200 and 0 <= nlocal < 200):
                    continue
                if not (0 <= isc <= 20 and 0 <= msc <= 40):
                    continue
                if not (4 < clen < 200000) or q + clen > n:
                    continue
            except Exception:
                continue
            out.append((p, q, clen, mid))
            break
    # 去掉区间互相包含的（同一方法被多个 k 命中）
    out.sort(key=lambda x: (x[1], -x[2]))
    keep = []
    for r in out:
        if keep and r[1] < keep[-1][1] + keep[-1][2]:
            if r[2] <= keep[-1][2]:
                continue
            keep.pop()
        keep.append(r)
    return keep


def body_of(bodies, off):
    for r in bodies:
        if r[1] <= off < r[1] + r[2]:
            return r
    return None


def main():
    path = sys.argv[1]
    d = abc_bytes(path)
    bodies = find_bodies(d)
    print('abc len %d  bodies %d  covered %d (%.1f%%)'
          % (len(d), len(bodies), sum(b[2] for b in bodies),
             100.0 * sum(b[2] for b in bodies) / len(d)))
    if len(sys.argv) > 2:
        t = int(sys.argv[2], 0)
        r = body_of(bodies, t)
        if not r:
            print('no body covers %#x' % t)
            return
        rec, cs, cl, mid = r
        print('body rec=%#x code=%#x len=%d method=%d  (target %#x @+%d)'
              % (rec, cs, cl, mid, t, t - cs))
        sh = A.ABC.__new__(A.ABC)
        # 名字解析只要常量池，sh.py 提供了只解 cpool 的轻量壳
        for cand in ('.', '..', '_work_rakido', '../_work_rakido'):
            if cand not in sys.path:
                sys.path.insert(0, cand)
        import sh as SH
        S = SH.Sh()
        out = A.disasm(S, d[cs:cs + cl])
        for at, txt in out:
            mark = '>>>' if cs + at == t else '   '
            print('%s %04x  %s' % (mark, cs + at, txt))
        print('--- decoded %d bytes of %d ---' % (out[-1][0] if out else 0, cl))


if __name__ == '__main__':
    main()
