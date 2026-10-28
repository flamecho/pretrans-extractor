"""星の降る刻 (PS2-JP) —— UNION/SCRIPT.UNI 文本提取
引擎：Idea Factory / Otomate "STCM2 File Make By Minku 06.0"（非 STCM2L）
容器：ISO9660 -> UNION/SCRIPT.UNI（21 个 STCM2 子文件，0x800 对齐）

记录（LE u32）：
  文本  [L/4][1][L][cp932 L bytes(NUL padded)][0]
  指令  [op][nparams][size] + nparams*12 params + [0] + children ...（size == 本记录总字节）
  0x118 = 正文一行（1 param = 语音 id）
  0x119 = クリック待ち（16 字节：op,0,0x10,0）—— 断「一次点击」
  0x00  = テキストクリア（16 字节：0,0,0x10,0）—— 同样断行（清框后为新显示单位）
  0x11a = 名札（独立名字窗，丢弃）
  0x11b = 选项（一行一条）
  0x124 = 章节题卡（上屏文字，收）
  0x1e3 = 章末好感度状态画面（系统 UI，不收）
  其余 0x9x~0x1xx = 立绘/表情/背景/事件/跳转等资源指令，其内文本为资源名，不收
"""
import struct, re, sys, os

SRC = sys.argv[1] if len(sys.argv) > 1 else '_work_hoshi/x/UNION/SCRIPT.UNI'
DST = sys.argv[2] if len(sys.argv) > 2 else '_work_hoshi/out.txt'

D = open(SRC, 'rb').read()
u32 = lambda p: struct.unpack_from('<I', D, p)[0]

BODY, NAME, OPT, TITLE, STATUS = 0x118, 0x11a, 0x11b, 0x124, 0x1e3
WAIT_PAT = b'\x19\x01\x00\x00' + b'\x00' * 4 + b'\x10\x00\x00\x00' + b'\x00' * 4
CLEAR_PAT = b'\x00' * 8 + b'\x10\x00\x00\x00' + b'\x00' * 4
BLOCKS = [b'GLOBAL_DATA', b'CODE_START_', b'EXPORT_DATA']


def dec(b):
    core = b.rstrip(b'\x00')
    if 0 in core:
        return None
    try:
        s = core.decode('cp932')
    except Exception:
        return None
    for c in s:
        o = ord(c)
        if o < 0x20 or 0xe000 <= o <= 0xf8ff or 0xff61 <= o <= 0xff9f:
            return None
    return s


def code_region(fs, size):
    cs = D.find(b'CODE_START_', fs, fs + size)
    st, en = cs + 16, fs + size
    for b in BLOCKS:
        q = D.find(b, st, fs + size)
        if q != -1:
            en = min(en, q)
    return st, en


def scan(fs):
    size = u32(fs + 0x20)
    st, en = code_region(fs, size)
    out = []
    p = st
    while p + 12 <= en:
        op, n, v = u32(p), u32(p + 4), u32(p + 8)
        if n == 1 and v % 4 == 0 and 4 <= v <= 0x1000 and op == v // 4 and p + 12 + v <= en:
            s = dec(D[p + 12:p + 12 + v])
            if s is not None:
                tend = p + 12 + v + 4
                par = None
                for q in range(p - 12, max(p - 300, st), -4):
                    if u32(q + 8) == tend - q and u32(q) < 0x400:
                        par = u32(q)
                        break
                out.append((p, par, s, p + 12 + v))
                p += 12 + v
                if p + 4 <= en and u32(p) == 0:
                    p += 4
                continue
        p += 4
    return out


def build():
    files = [m.start() for m in re.finditer(b'STCM2 File Make By Minku', D)]
    lines = []
    name_cnt = {}
    cnt = {'body': 0, 'opt': 0, 'title': 0, 'name': 0, 'status': 0, 'merge': 0}
    for fs in files:
        recs = scan(fs)
        body = sorted([r for r in recs if r[1] == BODY], key=lambda r: r[0])
        others = sorted([r for r in recs if r[1] in (NAME, OPT, TITLE, STATUS)], key=lambda r: r[0])
        for r in recs:
            if r[1] == NAME:
                name_cnt[r[2]] = name_cnt.get(r[2], 0) + 1
        groups = []
        cur = []
        for i, r in enumerate(body):
            if cur:
                gap = D[cur[-1][3] + 4:r[0]]
                if WAIT_PAT in gap or CLEAR_PAT in gap:
                    groups.append(cur)
                    cur = []
            cur.append(r)
        if cur:
            groups.append(cur)
        events = [(g[0][0], 0, g) for g in groups]
        events += [(r[0], 1, r) for r in others]
        events.sort(key=lambda e: e[0])
        for pos, kind, val in events:
            if kind == 0:
                txt = ''.join(x[2] for x in val).strip('\u3000 ')
                if txt:
                    lines.append(txt)
                    cnt['body'] += 1
                    if len(val) > 1:
                        cnt['merge'] += 1
            else:
                r = val
                if r[1] == OPT:
                    lines.append(r[2])
                    cnt['opt'] += 1
                elif r[1] == TITLE:
                    lines.append(r[2])
                    cnt['title'] += 1
                elif r[1] == STATUS:
                    cnt['status'] += 1
    return lines, cnt, name_cnt


if __name__ == '__main__':
    lines, cnt, names = build()
    with open(DST, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('lines=%d %s' % (len(lines), cnt))
    print('names(%d): %s' % (len(names), sorted(names.items(), key=lambda kv: -kv[1])))
