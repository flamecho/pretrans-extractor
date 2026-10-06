import sys, re, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdar import CDAR

SJIS = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc])+')
HIRA = re.compile(r'[\u3041-\u309f]')
SKIP = (b'TIM2', b'GXT\x00', b'XF1G', b'GT1G', b'KSEF', b'TOD2')


def scan(base):
    files = sorted(glob.glob(base + '/*_cdar'))
    print('nested CDARs:', len(files), flush=True)
    hits = []
    for fp in files:
        try:
            a = CDAR(fp)
        except Exception:
            continue
        for i in range(a.count):
            try:
                d = a.data(i)
            except Exception:
                continue
            if len(d) < 200 or len(d) > 3_000_000:
                continue
            if d[:4] in SKIP:
                continue
            n = 0
            samp = None
            for m in SJIS.finditer(d[:800000]):
                if len(m.group()) < 8:
                    continue
                try:
                    t = m.group().decode('cp932')
                except Exception:
                    continue
                if HIRA.search(t) and '\ufffd' not in t:
                    n += 1
                    if samp is None or len(t) > len(samp):
                        samp = t
            if n >= 5:
                hits.append((n, os.path.basename(fp), i, len(d), samp, d[:4]))
    hits.sort(reverse=True)
    print('hits:', len(hits), flush=True)
    for n, f, i, sz, s, m in hits[:40]:
        print('  %-22s e%-5d size=%-9d runs=%-5d magic=%-8r %s' %
              (f, i, sz, n, m.decode('latin1', 'replace'), (s or '')[:55]), flush=True)


if __name__ == '__main__':
    scan(sys.argv[1])
