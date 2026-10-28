# -*- coding: utf-8 -*-
"""[PS2-JP] エーデルブルーメ (SLPM-66976 / Design Factory・Otomate 2008) 剧本文本提取

容器链路
  ISO9660 -> UNION/SCRIPT.UNI                        [CRI UNI2]
    UNI2 头 : "UNI2" + u32(0x10000) + u32 file_count(80) + u32 1 + u32 2
    FAT     : 0x800 起 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
              绝对偏移 = startCluster * 0x800
    子文件  : [0x1000 前缀区][STCM2 @ +0x1000]  ("STCM2 File Make By Minku 07.0")
    "CODE_START_\0" -> 代码段 = 该串偏移 + 24
  代码段 = op 链 [u32 size][payload(size-4)]
    文本记录 payload = [u32 槽]*3 [u32 0][u32 L/4][u32 1][u32 L][cp932 text][u32 0][u32 cmd][u32 flag]
      => 端锚定: 末 12B = [0][cmd][flag];  text = pay[k+16 : len-12]  (k=12)

本作 cmd 语义（实测，fid 100-113 正文）:
  k==12 cmd==0xd2 flag=1 -> 框内软换行（同框下一行），不点击，并入当前行
  k==12 cmd==0xd3 flag=0 -> 框末（一次点击）
  k==12 cmd==0x34 flag=2 -> 框末（同 0xd3）
  k==12 cmd==0xe7 flag=2 -> 框末（其后续接选项）
  k==12 cmd==0x33        -> '処理開始' 调试串
  k==12 cmd==0x5         -> 'sureN' SE 名
  k==24 cmd∈{0xe6,0xe7}  -> 选项（一行一条）
  k==24 其余 + k==12 纯 ASCII -> 资源名/标签/章节索引表

名札: k==12 cmd==0xd2 的短串（无句读/引号，仅'？'允许），**恒在框首**，后随 `「『（(` 起的台词。
      76 种（含 `？？？`/`オーギュストの声`）=> 独立名字窗, 整行丢弃, 不加说话人前缀。
      独立窗佐证：正文框容量 3 行（不带名札最多 4 段时全部其实是 `？？？` 札）；
      带名札的框正文段数恒 ≤3 —— 名札不占正文框行。
主角宏: #Name[1] = 默认名 メアリ（fid 0 的 k=24 cmd=0x0 记录；vndb: Mary / 名称可改）
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC  = os.path.join(HOME, '_work_edel/x/UNION/SCRIPT.UNI')
OUT  = os.path.join(HOME, '提取结果/[PS2-JP]エーデルブルーメ.txt')
FAT, PREFIX = 0x800, 0x1000

END_CMDS  = {0xd3, 0x34, 0xe7, 0x3f, 0x35, 0x1ad}   # 0x3f/0x35/0x1ad = 孤立单段框的框末变体（共 3 条，已核）
CONT_CMDS = {0xd2}
OPT_CMDS  = {0xe6, 0xe7, 0x1ad}     # 0x1ad = 选项的第三种收尾（2 条，夹在 e7 与 e6 之间）
NAME = {'#Name[1]': 'メアリ'}
SYS_TEXT = {'処理開始', '処理開始\\n'}
SYS_PROMPT = ('プロローグをスキップしますか？',)
MACRO = re.compile(r'#(?:Scale|Kana|Color|Font|Wait|Voice|Effect|Speed|Pos)\[[^\]]*\]')
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e\\]+$')
PLATE_BAD = set('。、，．！？…「」『』（）・―─〜～!?,.:;')
STORY_FIDS = lambda fid: 100 <= fid <= 113

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
    return [(fid, fs, next(s for s in starts if s > fs) + PREFIX) for fid, fs, sb in ents]


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
        out.append(d[i + 4:i + bs]); i += bs
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
        if not raw or any(b >= 0xfd for b in raw):
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
    return [(fid, [r for r in (rec_of(p) for p in file_ops(fs, fe)) if r])
            for fid, fs, fe in load_files() if STORY_FIDS(fid)]


def is_plate(t):
    return not (set(t) & (PLATE_BAD - set('？')))


def main():
    data = collect()

    plates = collections.Counter()
    for fid, ev in data:
        seq = [e for e in ev if e[0] == 12]
        for i, (k, s, cmd, fl) in enumerate(seq):
            t = s.strip()
            if cmd != 0xd2 or not t or len(t) > 14 or not is_plate(t):
                continue
            if not (i == 0 or seq[i - 1][2] in END_CMDS):
                continue
            if i + 1 < len(seq) and seq[i + 1][1].lstrip()[:1] in '「『（(':
                plates[t] += 1
    plates = set(plates)
    print('名札 %d 種: %s' % (len(plates), ' '.join(sorted(plates))), file=sys.stderr)

    lines, st = [], collections.Counter()
    buf = []
    skip_opt = [False]

    def flush():
        if buf:
            lines.append(''.join(buf))
            buf.clear()

    for fid, ev in data:
        for k, s, cmd, fl in ev:
            t = s.strip()
            if k == 24:
                if cmd in OPT_CMDS and JP.search(s):
                    if skip_opt[0]:
                        st['sysopt'] += 1
                        continue
                    flush()
                    lines.append(MACRO.sub('', s).strip())
                    st['opt'] += 1
                continue
            if k != 12:
                continue
            if ASCII_ONLY.match(t):
                st['label'] += 1
                continue
            if not t:
                continue
            if t in plates:
                flush(); st['plate'] += 1
                continue
            if cmd in CONT_CMDS:
                buf.append(s if not buf else s.lstrip('\u3000'))
                continue
            if cmd in END_CMDS:
                if t in SYS_TEXT:
                    st['debug'] += 1
                    continue
                if any(p in s for p in SYS_PROMPT):
                    flush(); skip_opt[0] = True
                    st['sysprompt'] += 1
                    continue
                skip_opt[0] = False
                buf.append(s if not buf else s.lstrip('\u3000'))
                flush(); st['box'] += 1
                continue
            st['sys'] += 1
    flush()

    out = []
    for l in lines:
        for a, b in NAME.items():
            l = l.replace(a, b)
        l = MACRO.sub('', l)
        l = re.sub(r'[ \t]+', ' ', l).strip()
        if l:
            out.append(l)
    print('stats: %s  lines=%d' % (dict(st), len(out)), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('->', OUT, file=sys.stderr)


if __name__ == '__main__':
    main()
