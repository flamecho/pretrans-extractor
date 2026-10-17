# -*- coding: utf-8 -*-
"""LZO1X-1 (miniLZO) 解压器 + event.enc entry 解压测试"""
import struct, sys
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())


def lzo1x_decompress(src, out_len=None):
    out = bytearray(out_len if out_len else 0)
    op = 0
    ip = 0
    n = len(src)

    def ensure(k):
        nonlocal out
        if op + k > len(out):
            out.extend(b'\x00' * (op + k - len(out) + 4096))

    def copy_lit(cnt):
        nonlocal ip, op
        ensure(cnt)
        out[op:op + cnt] = src[ip:ip + cnt]
        op += cnt
        ip += cnt

    def copy_match(mpos, cnt):
        nonlocal op
        ensure(cnt)
        for _ in range(cnt):
            out[op] = out[mpos]
            op += 1
            mpos += 1

    if src[ip] > 17:
        t = src[ip] - 17
        ip += 1
        if t < 4:
            copy_lit(t)
            t = src[ip]
            ip += 1
            state = 'match'
        else:
            copy_lit(t)
            state = 'first_literal_run'
    else:
        state = 'literal_run'

    while True:
        if state == 'literal_run':
            t = src[ip]; ip += 1
            if t >= 16:
                state = 'match'
                continue
            if t == 0:
                while src[ip] == 0:
                    t += 255; ip += 1
                t += 15 + src[ip]; ip += 1
            copy_lit(t + 3)
            state = 'first_literal_run'
            continue
        if state == 'first_literal_run':
            t = src[ip]; ip += 1
            if t >= 16:
                state = 'match'
                continue
            mpos = op - 1 - 0x800 - (t >> 2) - (src[ip] << 2)
            ip += 1
            ensure(3)
            out[op] = out[mpos]; out[op + 1] = out[mpos + 1]; out[op + 2] = out[mpos + 2]
            op += 3
            t = src[ip - 2] & 3
            if t:
                copy_lit(t)
            state = 'literal_run'
            continue
        # match
        if t >= 64:
            mpos = op - 1 - ((t >> 2) & 7) - (src[ip] << 3); ip += 1
            copy_match(mpos, ((t >> 5) - 1) + 2)
        elif t >= 32:
            t &= 31
            if t == 0:
                while src[ip] == 0:
                    t += 255; ip += 1
                t += 31 + src[ip]; ip += 1
            mpos = op - 1 - ((src[ip] >> 2) + (src[ip + 1] << 6)); ip += 2
            copy_match(mpos, t + 2)
        elif t >= 16:
            mpos = op - ((t & 8) << 11)
            t &= 7
            if t == 0:
                while src[ip] == 0:
                    t += 255; ip += 1
                t += 7 + src[ip]; ip += 1
            mpos -= (src[ip] >> 2) + (src[ip + 1] << 6); ip += 2
            if mpos == op:
                break
            mpos -= 0x4000
            copy_match(mpos, t + 2)
        else:
            mpos = op - 1 - (t >> 2) - (src[ip] << 2); ip += 1
            copy_match(mpos, 2)
        t = src[ip - 2] & 3
        if t:
            copy_lit(t)
            t = src[ip]; ip += 1
            state = 'match'
        else:
            state = 'literal_run'
    return bytes(out[:op])


if __name__ == '__main__':
    raw = open(os.path.join(VNTRANS_HOME, '_work_hak/out1/event.enc'), 'rb').read()
    cnt = struct.unpack_from('<I', raw, 0)[0]
    recs = [struct.unpack_from('<III', raw, 0x10 + 12 * i) for i in range(cnt)]
    print('count', cnt)
    ok = 0
    for i in (0, 1, 2, 4, 173):
        sz, sz2, off = recs[i]
        comp = (sz >> 31) & 1
        size = sz & 0x7fffffff
        payload = raw[off:off + size]
        try:
            dec = lzo1x_decompress(payload, sz2)
            pct = 100 * len(dec) / max(sz2, 1)
            sample = dec[:0].decode('cp932', 'replace')
            print('e%-4d size=%-7d size2=%-7d comp=%d -> 解出 %d B (%.1f%% of size2)'
                  % (i, size, sz2, comp, len(dec), pct))
            print('     前 120 字节: %s' % dec[:120].decode('cp932', 'replace').replace('\n', '|'))
            ok += 1
        except Exception as e:
            print('e%-4d FAIL: %s' % (i, e))
