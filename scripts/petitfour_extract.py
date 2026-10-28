# -*- coding: utf-8 -*-
"""プティフール (PS2-JP, SLPM-66945 / Otomate·Design Factory 2008) 剧本文本提取

容器链路
  ISO9660 -> UNION/SCRIPT.UNI                        [CRI UNI2]
    UNI2 头 : "UNI2" + u32(0x10000) + u32 file_count(157) + u32 1 + u32 3
    FAT     : 0x800 起 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
              绝对偏移 = startCluster * 0x800
    子文件  : [0x1800 前缀区][STCM2 @ +0x1800]  ("STCM2 File Make By Minku 07.0")
    "CODE_START_\0" -> 代码段 = 该串偏移 + 24
  代码段 = op 链 [u32 size][payload(size-4)]
    文本记录 payload = [u32 槽]*3 [u32 0][u32 L/4][u32 1][u32 L][cp932 text][u32 0][u32 cmd][u32 flag]
      => 端锚定: 末 12B = [0][cmd][flag];  text = pay[28 : len-12]  (k=12)

本作 cmd 语义（实测）:
  k==12 cmd==0xd2 flag=1 -> 框内追加(同框软换行)，不点击，并入当前行
  k==12 cmd==0xd3 flag=0 -> 框末（一次点击）
  k==12 cmd==0x34 flag=2 -> 框末（同 0xd3，另一种演出收尾）
  k==12 cmd==0xe7 flag=2 -> 框末，其后续接选项
  k==12 cmd==0x33        -> '処理開始\\n' 系统串
  k==12 cmd==0x 5        -> 'sureN' SE 名
  k==24 cmd∈{0xe6,0xe7}  -> 选项（一行一条）
  k==24 与 k==12 纯 ASCII -> 资源名/标签(switch/select/bgNN/thNN)，不收

名札: k==12 cmd==0xd2 的短串(无句读, 1-10 字)，**恒出现在框首(前一条必为框末)**，
      共 35 种(含 `？？？`/`２人`/`スタッフ一同`) => 独立名字窗, 丢该行, 不加前缀。
主角宏: #Name[1]=姓 神崎 / #Name[2]=名 芽衣（ymgal/vndb: 神崎 芽衣）
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC  = os.path.join(HOME, '_x/UNION/SCRIPT.UNI')
OUT  = os.path.join(HOME, '提取结果/[PS2-JP]プティフール.txt')
FAT, PREFIX = 0x800, 0x1800

END_CMDS  = {0xd3, 0x34, 0xe7, 0x33}   # 框末（= 一次点击）; 0x33 多为 '処理開始' 系统串, 按值丢
CONT_CMDS = {0xd2}                 # 框内追加
OPT_CMDS  = {0xe6, 0xe7}           # k==24 选项
NAME = {'#Name[1]': '神崎', '#Name[2]': '芽衣'}
SYS_PROMPT = ('プロローグをスキップしますか？',)
SYS_TEXT = {'処理開始', '処理開始\\n'}
MACRO = re.compile(r'#(?:Scale|Kana|Color|Font|Wait|Voice)\[[^\]]*\]')
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
# ★不要用「含假名/汉字」当串过滤判据：纯标点＋宏的串(如 `「#Name[2]……。`)会被误删致整行断折
LABEL_PAD = re.compile(r'^[\s\u3000]*【[^】]*】[\s\u3000]*$')
NONASCII = re.compile(r'[^\x00-\x7f\u3000]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e\\]+$')
# 名札判据: k=12 cmd=0xd2 · 短(<=12) · 无句读/引号 · **前一条必为框末** · 下一条以 「/『 起
# （不看字符集：本作有 中年Ｂ/マダムＥ/記者Ａ 这类含全角拉丁的名札，字符集判定会漏）
PLATE_BAD = set('。、，．！？…「」『』（）・―─～!?,.')

d = open(SRC, 'rb').read()


def load_files():
    n = struct.unpack_from('<I', d, 8)[0]
    ents = []
    for i in range(n):
        fid, sc, scl, sb = struct.unpack_from('<IIII', d, FAT + 16 * i)
        if sb:
            ents.append((fid, sc * 0x800, sb))
    ents.sort()
    starts = sorted(e[1] for e in ents) + [len(d)]

    def fend(fs):                      # 末条会跨入下一文件的前缀区
        return next(s for s in starts if s > fs) + PREFIX
    return [(fid, fs, fend(fs)) for fid, fs, sb in ents]


def file_ops(fs, fe):
    if d[fs + PREFIX:fs + PREFIX + 5] != b'STCM2':
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
        if not raw or any(b >= 0xfd for b in raw):   # cp932 合法域 0x00-0xFC
            return None
        try:
            s = raw.decode('cp932')
        except Exception:
            return None
        if '\ufffd' in s or any(ord(c) < 0x20 and c != '\u3000' for c in s):
            return None
        return (k, s, cmd, flag)
    return None


def collect():
    data = []
    for fid, fs, fe in load_files():
        ev = [r for r in (rec_of(p) for p in file_ops(fs, fe)) if r]
        data.append((fid, ev))
    return data


def main():
    data = collect()
    # 名札表：k=12 cmd=0xd2 短串 + 下一条以 「/『 开头
    plates = collections.Counter()
    for fid, ev in data:
        seq = [e for e in ev if e[0] == 12]
        for i, (k, s, cmd, fl) in enumerate(seq):
            t = s.strip()
            if cmd != 0xd2 or not t or len(t) > 12:
                continue
            if (set(t) & PLATE_BAD) and set(t) - PLATE_BAD - set('？?！'):   # 允许纯「？？？」名札
                continue
            if not (i == 0 or seq[i - 1][2] in END_CMDS):
                continue
            if i + 1 < len(seq) and seq[i + 1][1].lstrip()[:1] in '「『':
                plates[t] += 1
    plates = set(plates)
    print('名札 %d 種: %s' % (len(plates), ' '.join(sorted(plates))), file=sys.stderr)

    lines, st = [], collections.Counter()
    buf = []
    skip_opt = [False]        # 系统确认框(skip prologue)后紧跟的 はい/いいえ 一并剔

    def flush():
        if buf:
            lines.append(''.join(buf))
            buf.clear()

    for fid, ev in data:
        for k, s, cmd, fl in ev:
            t = s.strip()
            if k == 24:
                if cmd in OPT_CMDS and JP.search(s):     # 选项
                    if skip_opt[0]:
                        st['sysopt'] += 1
                        continue
                    flush()
                    lines.append(MACRO.sub('', s).strip())
                    st['opt'] += 1
                continue
            if k != 12:
                continue
            if ASCII_ONLY.match(t):                      # 资源名/标签(switch/select/bgNN/sureN)
                st['label'] += 1                          # 不上屏, 也不打断当前框
                continue
            if not NONASCII.search(s):                   # 纯 ASCII 之外全空 => 空串/全角空格
                continue
            if t in plates:                              # 名札 -> 丢
                flush(); st['plate'] += 1
                continue
            # 居中留白: 整条只有「前导空格+【…】」的定位串, 或紧跟 】 的续段
            if LABEL_PAD.match(s) or (buf and buf[-1].endswith('】') and t != s):
                s = s.strip()
            if cmd == 0x5:                               # 菜名等定位串
                buf.append(s.strip()); continue
            skip_opt[0] = False
            if cmd in CONT_CMDS:
                buf.append(s); continue
            if cmd in END_CMDS:
                if t in SYS_TEXT:                        # 调试标记, 不上屏
                    st['debug'] += 1
                    continue
                if any(p in s for p in SYS_PROMPT):      # 系统确认框, 不上屏为剧情
                    buf.clear(); skip_opt[0] = True
                    st['sysprompt'] += 1
                    continue
                buf.append(s); flush(); st['box'] += 1
                continue
            st['sys'] += 1                               # 其余：系统串
    flush()

    out = []
    for l in lines:
        for a, b in NAME.items():
            l = l.replace(a, b)
        l = MACRO.sub('', l).strip()
        if l:
            out.append(l)
    print('stats: %s  lines=%d' % (dict(st), len(out)), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('->', OUT, file=sys.stderr)


if __name__ == '__main__':
    main()
