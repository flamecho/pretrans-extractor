"""更宽松的方法体定位：不限定 `d0 30` 序言，改用「6 个 u30 精确落在 code 起点 + 尾部结构自洽」。

ABC 的 method_body_info：
    u30 method_idx, max_stack, local_count, init_scope_depth, max_scope_depth,
    u30 code_len, u8 code[code_len], u30 ex_count, exceptions[], u30 trait_count, traits[]

判据（全部满足才算）：
  1. 6 个 u30 读完后正好停在 code 起点 q
  2. method_idx ∈ [1, nmeth]，max_stack/local_init/max_scope 落在合理区间
  3. d[q] == 0xD0（getlocal0），d[q+1] ∈ {0x30 pushscope, 0xD1..0xD7 setlocal*}
  4. code 末尾之后：ex_count 与 trait_count 都能读且不越界
"""
import sys
import re

sys.path.insert(0, __file__.rsplit('\\', 1)[0])
import air_abc as A

STARTS = (0x30, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0x57, 0x2A)


def abc_bytes(swf_path):
    body = A.load_swf(swf_path)
    pl = [x for c, x in A.swf_tags(body) if c == 82][0]
    off = pl.index(0, 4) + 1 if pl[:4] == b'\x01\x00\x00\x00' else 1
    return pl[off:]


def find_bodies(d, nmeth=4000):
    n = len(d)
    prols = [m.start() for m in re.finditer(b'\xd0', d)]
    out = []
    for q in prols:
        if q + 2 > n:
            break
        if d[q + 1] not in STARTS:
            continue
        for k in range(1, 16):
            p = q - k
            if p < 0:
                break
            try:
                vals = []
                pp = p
                for _ in range(6):
                    v, pp = A.u30(d, pp)
                    vals.append(v)
                if pp != q:
                    continue
                mid, mstack, nlocal, isc, msc, clen = vals
                if not (0 < mid <= nmeth):
                    continue
                if not (0 <= mstack < 300 and 0 <= nlocal < 300):
                    continue
                if not (0 <= isc <= 30 and 0 <= msc <= 60):
                    continue
                if not (2 <= clen < 300000) or q + clen > n:
                    continue
                # 尾部结构自洽
                e = q + clen
                exc, e2 = A.u30(d, e)
                if exc > 200:
                    continue
                e3 = e2 + exc * 8
                if e3 > n:
                    continue
                nt, _ = A.u30(d, e3)
                if nt > 500:
                    continue
            except Exception:
                continue
            out.append((p, q, clen, mid))
            break
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


if __name__ == '__main__':
    d = abc_bytes('_work_rakido/app.swf')
    b = find_bodies(d)
    print('abc %d  bodies %d  covered %d (%.1f%%)'
          % (len(d), len(b), sum(x[2] for x in b), 100.0 * sum(x[2] for x in b) / len(d)))
    ms = [x[3] for x in b]
    print('distinct method idx', len(set(ms)), 'max', max(ms) if ms else 0)
