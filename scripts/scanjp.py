import sys, re, collections
p = sys.argv[1]
d = open(p, 'rb').read()
print(p, len(d))
n = len(d)
i = 0
runs = []
while i < n - 1:
    b = d[i]
    if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef:
        j = i
        while j < n - 1:
            c = d[j]
            if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef:
                if 0x40 <= d[j+1] <= 0xfc and d[j+1] != 0x7f:
                    j += 2
                else:
                    break
            elif 0x20 <= c <= 0x7e or 0xa1 <= c <= 0xdf:
                j += 1
            else:
                break
        if j - i >= 10:
            try:
                s = d[i:j].decode('cp932')
                jp = sum(1 for c in s if '\u3041' <= c <= '\u309f' or '\u30a1' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff')
                if jp >= 6:
                    runs.append((i, jp, s))
            except Exception:
                pass
        i = j if j > i else i + 2
    else:
        i += 1
print('runs', len(runs), 'total jp', sum(r[1] for r in runs))
runs.sort(key=lambda r: -r[1])
for o, jp, s in runs[:40]:
    print('%08x' % o, jp, repr(s[:70]))
