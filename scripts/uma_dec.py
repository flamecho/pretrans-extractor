import sys, io
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
T = open(os.path.join(VNTRANS_HOME, '_w_wgs/chartable.bin'),'rb').read().decode('utf-8')
SRC = r'<本地路径>'

def decode(body, start=0x10):
    """yield (byteoffset, char_or_special)"""
    out = []
    i = start
    n = len(body)
    while i < n:
        b = body[i]
        if b == 0:
            out.append((i, None))   # 0x00 special
            i += 1
        elif b < 0x80:
            out.append((i, T[b-1]))
            i += 1
        else:
            code = body[i+1] + 128*(b-0x81)
            idx = code + 127
            out.append((i, T[idx] if idx < len(T) else '\uFFFD'))
            i += 2
    return out

if __name__ == '__main__':
    d = open(SRC,'rb').read()
    st = int(sys.argv[1],0) if len(sys.argv)>1 else 0x10
    ln = int(sys.argv[2],0) if len(sys.argv)>2 else 600
    res = decode(d, st)
    # print from st, take chars covering ln bytes
    buf=[]
    for off,ch in res:
        if off < st: continue
        if off > st+ln: break
        buf.append('⟦00⟧' if ch is None else ch)
    print(''.join(buf))
