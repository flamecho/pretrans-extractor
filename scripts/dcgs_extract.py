# -*- coding: utf-8 -*-
"""D.C. Girl's Symphony Pocket (PSP, ULJM05690) 剧本文本提取

容器链路
  ISO9660 -> PSP_GAME/USRDIR/UNION/SCRIPT.UNI         [CRI UNI2]
    UNI2 头: "UNI2" + u32(0x10000) + u32 file_count(=161) + u32 1 + u32 3
    FAT    : 0x800 起, 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
             绝对偏移 = startCluster * 0x800
    子文件 : [0x1800 前缀区(资源/符号表)][STCM2 @ +0x1800]
    STCM2 头: +0x00 generator 32B ("STCM2 File Make By Minku 07.0")
              +0x20 exports_offset(u32) ; +0x50 "GLOBAL_DATA" ...
              "CODE_START_\0" 12B -> 代码段 = 该串偏移 + 24
  代码段 = opcode 链 [u32 size][payload(size-4)]
    文本记录 payload = [u32 addr][u32 style]*n [u32 0][u32 L/4][u32 1][u32 L][cp932 text(L B)][u32 0][u32 cmd][u32 flag]
      端锚定解析: 末 12B = 标记 [0][cmd][flag];  text 区 = pay[k+16 : len-12]
    以 (k, cmd) 分派语义:
      k==12 cmd==0xd2 (flag=1)      = 正文续行(同框软换行)
      k==12 cmd==0xd3 (flag=0)      = 正文框末(新框 / 一次点击)
      k==12 cmd==0xe7 (flag=2)      = 正文框末(其后续接选项)
      k==12 cmd==0xd6/0x35/0x3d     = 正文框末(同上, 少量)
      k==12 cmd==0x0/0x33           = 符号/系统串(sureN / 処理開始) -> 弃
      k!=12 cmd==0xe6/0xe7/0xec     = 选项
    名札: k==12 cmd==0xd2 的短串(无句读, 紧随「/『 台词) -> 丢弃, 不加前缀
    #Kana[n,よみ] = 注音(ruby) -> 只留基底语
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HOME, '_work_dcgs/src/PSP_GAME/USRDIR/UNION/SCRIPT.UNI')
OUT = os.path.join(HOME, "提取结果/D.C. Girl's Symphony Pocket 全文本.txt")
FAT, PREFIX = 0x800, 0x1800
DLG_CONT = {0xd2}                      # 正文续行(同框软换行)
NON_DLG = {0x0, 0x33, 0x64, 0x96}      # k=12 上的符号/系统串: sureN / 処理開始 / screen
OPT_CMDS = {0xe6, 0xe7, 0xec}
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e]+$')
MACRO = re.compile(r'#Kana\[[^\]]*\]')
# 名札候选字符集: 假名/汉字/长音/中点/？/全角数字(女子生徒１・３年女子), 无句读
NAME_OK = re.compile(r'^[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3005\u2010-\u2015\u30fb\uff1f\uff01\uff10-\uff19]+$')
# 行内『名＋「台词」』形态: 行尾必须是闭合引号(排除 “名为句中主语” 的 `稜平くん（…）だって`)
INLINE_PLATE = re.compile(r'^([\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3005\u2010-\u2015\u30fb\uff10-\uff19]{1,8})(「|『)(.*)(」|』)$')

d = open(SRC, 'rb').read()


def load():
    n = struct.unpack_from('<I', d, 8)[0]
    ents = []
    for i in range(n):
        fid, sc, scl, sb = struct.unpack_from('<IIII', d, FAT + 16 * i)
        if sb:
            ents.append((fid, sc * 0x800, sb))
    starts = sorted(e[1] for e in ents) + [len(d)]

    def fend(fs):
        return next(s for s in starts if s > fs) + PREFIX    # 末条可能跨入下一文件前缀区
    return [(fid, fs, fend(fs)) for fid, fs, sb in ents]


def rec_of(pay):
    n = len(pay)
    if n < 28 or pay[n - 12:n - 8] != b'\x00\x00\x00\x00':
        return None
    cmd, flag = struct.unpack_from('<II', pay, n - 8)
    for k in range(12, min(n - 16, 208), 4):
        if pay[k:k + 4] != b'\x00\x00\x00\x00':
            continue
        nn, one, L = struct.unpack_from('<III', pay, k + 4)
        if one != 1 or L < 4 or L > 0x2000 or L % 4 or nn != L // 4:
            continue
        if k + 16 + L != n - 12:
            continue
        raw = pay[k + 16:n - 12].rstrip(b'\x00')
        if not raw:
            return None
        # 0xFD/0xFE/0xFF 非合法 cp932 字节(cp932 仅 0x00-0xFC); 出现即样式哨兵区误匹配
        if any(b >= 0xfd for b in raw):
            return None
        try:
            s = raw.decode('cp932')
        except Exception:
            return None
        if not s or '\ufffd' in s or any(ord(c) < 0x20 for c in s):
            return None
        return (k, s, cmd, flag)
    return None


def file_ops(fs, fe):
    if d[fs + PREFIX:fs + PREFIX + 6] not in (b'STCM2L', b'STCM2 '):
        return []
    c = d.find(b'CODE_START_\0', fs + PREFIX, fe)
    if c < 0:
        return []
    i, out = c + 24, []
    while i + 4 <= fe:
        bs = struct.unpack_from('<I', d, i)[0]
        if bs == 0 or bs % 4 or i + bs > fe:
            break
        out.append(d[i + 4:i + bs])
        i += bs
    return out


def collect(files):
    """返回 [(fid, [(k, text, cmd, flag), ...]), ...]"""
    all_ev = []
    for fid, fs, fe in files:
        O = file_ops(fs, fe)
        if not O:
            continue
        ev = []
        for pay in O:
            r = rec_of(pay)
            if r:
                ev.append(r)
        all_ev.append((fid, ev))
    return all_ev


def find_names(all_ev):
    """名札自举: k==12 cmd==0xd2 · 短 · 无句读 · 紧邻「/『 台词"""
    cnt = collections.Counter()
    for fid, ev in all_ev:
        seq = ev
        for i, (k, s, cmd, fl) in enumerate(seq):
            if k != 12 or cmd != 0xd2:
                continue
            t = s.strip()
            if not t or len(t) > 10 or not NAME_OK.match(t):
                continue
            nx = None
            for j in range(i + 1, min(i + 3, len(seq))):
                if seq[j][0] == 12:
                    nx = seq[j][1]
                    break
            if nx and nx[:1] in ('「', '『', '（'):
                cnt[t] += 1
    return cnt


def clean(s):
    return MACRO.sub('', s)


def main():
    files = load()
    all_ev = collect(files)
    cnt = find_names(all_ev)
    names = set(cnt)
    print('名札 %d 個: %s' % (len(names), sorted(names)), file=sys.stderr)

    lines, st = [], collections.Counter()
    buf = []
    for fid, ev in all_ev:
        for (k, s, cmd, fl) in ev:
            t = s.strip()
            if k == 12:
                if cmd in NON_DLG:
                    st['sym'] += 1
                    continue
                if ASCII_ONLY.match(t):                 # 'op' 等场景标签
                    if buf:
                        lines.append(''.join(buf)); buf = []
                    st['label'] += 1
                    continue
                if t in names:                          # 名札 -> 丢弃(不加前缀)
                    if buf:
                        lines.append(''.join(buf)); buf = []
                    st['name'] += 1
                    continue
                mo = INLINE_PLATE.match(s)              # 同行内『名＋「台词」』
                if mo:
                    s = s[len(mo.group(1)):]; st['inline'] += 1
                buf.append(clean(s))
                if cmd != 0xd2:
                    lines.append(''.join(buf)); buf = []
            else:
                if cmd in OPT_CMDS and JP.search(s):
                    if buf:
                        lines.append(''.join(buf)); buf = []
                    lines.append(clean(s)); st['opt'] += 1
    if buf:
        lines.append(''.join(buf))

    out = [l.strip() for l in lines]
    out = [l for l in out if l]
    # 相邻完全重复行去重
    ded = []
    for l in out:
        if ded and ded[-1] == l:
            st['dup'] += 1
            continue
        ded.append(l)
    print('stats: %s  lines=%d' % (dict(st), len(ded)), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(ded) + '\n')
    print('->', OUT, file=sys.stderr)


if __name__ == '__main__':
    main()
