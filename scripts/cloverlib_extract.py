# -*- coding: utf-8 -*-
"""クローバー図書館の住人たち (PC-JP / 澪 / System-NNN「NNNLib」系) 全文本提取

链路
  ISO9660 → SETUP.EXE(Inno Setup 5.5.0) → app/{spt/*.spt, spt/*.xtx, init2/*.fxf}
  .spt / .fxf 一律【逐字节 XOR 0xFF】;  .xtx = 明文 cp932

.spt 结构（本作实测，头部四组 count 全部对上）
  0x00 u32=0x20 | 0x10 起 4×(u32 count, u32 base) | 0x30 "SPTHEADER0"
  布局 = [头][指令流][地址表1][消息池1][16 字节桩][地址表2(g1 条)][杂多池(pool2)]
  · 消息池1 = g0 条记录；记录 = [cp932 串][NUL][补齐到 4 字节]
  · 记录内 `<名札>\r\n<正文>`；正文内 `\r\n` = 框内换行；`#名`/`#姓` = 主角名宏；
    `#［Nよみ］` = 注音
  池1 终点 e 的判据 = 走完 g0 条后紧跟 16 字节桩 `[u32][6666 1][5555 2][4444 N]`；
  池2 起点 = e + 16 + 4*g1。二者均与头部 count 自洽（无枚举）。
"""
import os, re, struct, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_src_cloverlib/x/app')
SPT = os.path.join(SRC, 'spt')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]クローバー図書館の住人たち.txt')

ORDER = ['kyoutuu_1_1', 'kyoutuu_1_2', 'map', 'route_1', 'route_2',
         'route_3', 'route_4', 'route_5', 'route_6']   # project.xtx 顺序；sys/tosho_backscript = 系统 UI

PROTAG_SEI, PROTAG_MEI = '相川', '千紘'


def cp932(p):
    return open(p, 'rb').read().decode('cp932')


PLATES = set()
for _l in cp932(os.path.join(SPT, 'charaname.xtx')).splitlines():
    if ',' in _l:
        _v = _l.split(',', 1)[1].strip()
        if _v and _v != '名前なし':
            PLATES.add(_v)
for _l in cp932(os.path.join(SPT, 'namecol.xtx')).splitlines():
    _p = _l.split(' ')
    if _p and _p[0]:
        PLATES.add(_p[0])
PLATES |= {'#名', '？？？'}
PLATES.discard('')


def decrypt(p):
    return bytes(b ^ 0xFF for b in open(p, 'rb').read())


def read_recs(D, o, n):
    out = []
    for _ in range(n):
        j = o
        while j < len(D) and D[j] != 0:
            j += 1
        try:
            out.append(D[o:j].decode('cp932'))
        except UnicodeDecodeError:
            out.append(None)
        o = (j + 4) // 4 * 4
    return out, o


def pool_infos(D):
    g = [struct.unpack_from('<2I', D, 0x10 + 8 * i) for i in range(4)]
    n0, n1, n2 = g[0][0], g[1][0], g[2][0]
    # 池1 起点：唯一满足「走完 n0 条 + 16 字节桩」的 4 字网格起点
    start = None
    o = 0x40
    while o + 4 <= len(D):
        if D[o] == 0:
            o += 4
            continue
        j = o
        while j < len(D) and D[j] != 0:
            j += 1
        try:
            t = D[o:j].decode('cp932')
        except UnicodeDecodeError:
            o += 4
            continue
        if not re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', t):
            o += 4
            continue
        recs, e = read_recs(D, o, n0)
        if all(r is not None for r in recs) and \
                D[e + 4:e + 8] == b'\x01\x00\x66\x66' and \
                D[e + 8:e + 12] == b'\x02\x00\x55\x55' and \
                D[e + 14:e + 16] == b'\x44\x44':
            start = o
            break
        o += 4
    if start is None:
        raise RuntimeError('pool1 not found')
    recs1, e1 = read_recs(D, start, n0)
    p2 = e1 + 16 + 4 * n1
    recs2, _ = read_recs(D, p2, n2)
    return recs1, recs2


def to_line(raw):
    t = raw
    if '\r\n' in t:
        seg0, rest = t.split('\r\n', 1)
        if seg0 in PLATES:          # 独立名字窗（messageWindow.fxf: nameWindowFlag 1）⇒ 名札剔
            t = rest
    parts = t.split('\r\n')         # 框内换行 ⇒ 合并（续行行首全角空格为缩进）
    t = parts[0] + ''.join(p.lstrip('\u3000') for p in parts[1:])
    t = re.sub(r'#［[^］]*］', '', t)  # 注音（保留汉字，剔读音）
    t = t.replace('#姓#名', PROTAG_SEI + PROTAG_MEI)
    t = t.replace('#姓', PROTAG_SEI).replace('#名', PROTAG_MEI)
    return t.strip()


JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


# ── 池2：選択肢 ────────────────────────────────────────────────
AREA = re.compile(r'^[０-９]+階')          # map.spt 的 10 个「場所」热点名（selectplace.fxf placeNumber 10）
LABEL_HINT = re.compile(r'[：＿]|（＋|▲|◆')


def is_option(t, fname):
    if not t or len(t) > 40:
        return False
    if t[0] in '%★☆' or t[0] in '①②③④⑤⑥⑦⑧⑨':
        return False
    if LABEL_HINT.search(t):
        return False
    if re.search(r'[0-9A-Za-z_]', t):
        return False
    if fname == 'map' and AREA.match(t):
        return False
    return bool(JP.search(t))


def pool2_lines(recs, fname):
    """返回 [(kind, text)]，kind ∈ {'title','q','opt'}；按池内出现序。"""
    out = []
    if recs and recs[0] and recs[0].startswith('★'):
        recs = recs[1:]
    if recs:                                   # 每文件第 1 条 = 章題／ルート名（扉文）
        out.append(('title', recs[0]))
        recs = recs[1:]
    i = 0
    while i < len(recs):
        t = recs[i]
        if t and t.startswith('%'):
            out.append(('q', t[1:]))       # 每条 % 记录 = 一条消息 = 一次点击（不跨记录合并）
            i += 1
            while i < len(recs) and is_option(recs[i], fname):
                out.append(('opt', recs[i]))
                i += 1
        else:
            i += 1
    return out


def main():
    # 池1（正文，执行序）与池2（選択肢，出现序）地址空间不相交 ⇒ 按文件分块：
    # 章題 → 正文 → 該文件的選択肢
    lines = []
    stat = []
    for name in ORDER:
        D = decrypt(os.path.join(SPT, name + '.spt'))
        recs1, recs2 = pool_infos(D)
        p2 = pool2_lines(recs2, name)
        for kind, t in p2:
            if kind == 'title':
                lines.append(t)
        body = [to_line(r) for r in recs1]
        body = [b for b in body if b]          # 池1 每条 = 一次点击，全收（含「…………」纯符号台词）
        lines.extend(body)
        for kind, t in p2:
            if kind != 'title':
                lines.append(t)
        stat.append((name, len(body), sum(1 for k, _ in p2 if k == 'q'),
                     sum(1 for k, _ in p2 if k == 'opt')))

    txt = '\n'.join(lines) + '\n'
    assert '\r' not in txt and '\ufffd' not in txt
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(txt)
    print('%-12s %6s %5s %5s' % ('file', 'body', 'q', 'opt'))
    for s in stat:
        print('%-12s %6d %5d %5d' % s)
    print('total lines:', len(lines), '->', OUT, os.path.getsize(OUT), 'bytes')
    for pat, label in ((r'[A-Za-z]', 'ASCII'), (r'[\uff61-\uff9f]', '半角カナ'), (r'[\ue000-\uf8ff]', 'PUA'),
                       (r'#', '残留#')):
        hit = [x for x in lines if re.search(pat, x)]
        print('%s lines: %d' % (label, len(hit)))
        for x in hit[:5]:
            print('   ', x[:80])


if __name__ == '__main__':
    main()
