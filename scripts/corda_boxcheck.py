# -*- coding: utf-8 -*-
"""诊断: 同一文本框被拆? 对某个 コルダ 提取器, 找「间隔含追加码 1e7e02b205」的记录对,
用该作自己的 process() 跑, 检查两条记录是否落在同一输出行。

用法: python corda_boxcheck.py <module> <DATA.BIN> [limit]
"""
import sys, os, struct, zlib, importlib, io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

APPEND = b'\x1e\x7e\x02\xb2\x05'
BOUND = b'\x1e\x8b\x05\x24\x22'
M91 = b'\x1e\x91\x0b\xbd\xa0'
C7 = b'\x1e\xc7\x09\x47\x74'
CLOSE = b'\x1e\xf9\x07\x87\x4c'


def leaves(rfile, base, path=''):
    rfile.seek(base)
    head = rfile.read(16)
    if head[:4] != b'CDAR':
        return
    cnt = struct.unpack_from('<I', head, 8)[0]
    rfile.seek(base + 0x10 + 4 * cnt)
    et = rfile.read(12 * cnt)
    for i in range(cnt):
        off, dec, sz = struct.unpack_from('<III', et, 12 * i)
        if sz == 0:
            continue
        rfile.seek(base + off)
        seg = rfile.read(sz)
        p = f'{path}{i}'
        if seg[:4] == b'CDAR' and len(seg) >= 8 and struct.unpack_from('<I', seg, 4)[0] == 4:
            yield from leaves(io.BytesIO(seg), 0, p + '/')
        else:
            data = seg
            if dec != sz and seg[:1] == b'\x78':
                try:
                    data = zlib.decompress(seg)
                except Exception:
                    pass
            yield (p, data)


def main():
    modname, datafile = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    mod = importlib.import_module(modname)
    seen = set()
    found = 0
    splits = 0
    for path, b in leaves(open(datafile, 'rb'), 0):
        if len(b) < 8 or len(b) > 0x2000000:
            continue
        if APPEND not in b:
            continue
        h = hash(b)
        if h in seen:
            continue
        seen.add(h)
        try:
            recs = mod.find_records(b)
        except Exception:
            continue
        if len(recs) < 2:
            continue
        try:
            out = mod.process(b)
            msgs = out[0]
        except Exception:
            continue
        joined = '\x00'.join(str(m) for m in msgs)
        for i in range(1, len(recs)):
            gap = b[recs[i - 1][1]:recs[i][0]]
            if APPEND in gap and not (BOUND in gap or C7 in gap or M91 in gap):
                t1 = recs[i - 1][2]
                t2 = recs[i][2]
                if not isinstance(t1, str):
                    t1 = t1.decode('cp932', 'replace')
                if not isinstance(t2, str):
                    t2 = t2.decode('cp932', 'replace')
                found += 1
                merged = (t1 in joined) and (t2 in joined)
                # 更强判据: 两段文本在同一行相邻出现(允许中间插入的少量字符)
                same_line = False
                t1s, t2s = t1.strip(), t2.strip()
                for m in msgs:
                    idx = 0
                    while True:
                        p1 = m.find(t1s, idx)
                        if p1 < 0:
                            break
                        seg = m[p1 + len(t1s):p1 + len(t1s) + len(t2s) + 4]
                        if t2s and t2s in seg:
                            same_line = True
                            break
                        idx = p1 + 1
                    if same_line:
                        break
                if not same_line:
                    splits += 1
                    if splits <= 20:
                        print(f'  [未合并] {path} pair#{i}')
                        print('     A:', repr(t1[:70]))
                        print('     B:', repr(t2[:70]))
                        print('     gap:', gap.hex(' ')[:60])
                if found <= limit:
                    print(f'--- {path}  pair#{i}')
                    print('    recA:', repr(t1[:60]))
                    print('    recB:', repr(t2[:60]))
                    print('    same_line:', same_line)
                break
        if found >= 100000:
            break
    print(f'[{modname}] 检查追加码记录对 {found} 处 —— 未并入同一行 {splits} 处')


if __name__ == '__main__':
    main()
