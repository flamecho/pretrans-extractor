# -*- coding: utf-8 -*-
"""『っポイ!』ひと夏の経験!? (PS2-JP, SLPM-55012 / Otomate·Design Factory 2008) 剧本文本提取

容器链路（与 プティフール 同族 UNI2＋STCM2，但前缀区 0x1000 而非 0x1800）
  ISO9660 -> UNION/SCRIPT.UNI                        [CRI UNI2]
    UNI2 头 : "UNI2" + u32(0x10000) + u32 file_count(115) + u32 1 + u32 2
    FAT     : 0x800 起 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
              绝对偏移 = startCluster * 0x800
    子文件  : [0x1000 前缀区][STCM2 @ +0x1000]  ("STCM2 File Make By Minku 07.0")
    "CODE_START_\0" -> 代码段 = 该串偏移 + 24
  代码段 = op 链 [u32 size][payload(size-4)]
    文本记录 payload = [u32 槽]*3 [u32 0][u32 L/4][u32 1][u32 L][cp932 text][u32 0][u32 cmd][u32 flag]
      => 端锚定: 末 12B = [0][cmd][flag];  text = pay[28 : len-12]

本作 cmd 语义（实测，见报告 §4）:
  k==12 cmd==0xd2(210) flag=1 -> 框内追加(同框软换行)，不点击，并入当前行
  k==12 cmd==0xd3(211) flag=0 -> 框末（一次点击）
  k==12 cmd==0x34(52)  flag=2 -> 框末（带 select/演出收尾）
  k==12 cmd==0xe7(231) flag=2 -> 框末，其后续接选项
  k==12 cmd==0x33(51)         -> '処理開始' 调试串
  k==24 cmd∈{0xe7(231),0xe6(230)} -> 选项（231=非末项, 230=末项）
名札: k==12 cmd==0xd2 的短串，恒在框首(前一条必为框末)、下一条以 「 起；共 21 种（独立名字窗）⇒ 整行丢弃。
主角宏: #Name[1]=姓 沢原 / #Name[2]=名 明日弥（vndb v9914 char「沢原 明日弥」Nameable）
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

HOME = os.environ.get('VNTRANS_HOME', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(HOME, '_work_poi/_x/UNION/SCRIPT.UNI')
OUT = os.path.join(HOME, '提取结果/[PS2-JP]『っポイ!』ひと夏の経験!？.txt')
FAT, PREFIX = 0x800, 0x1000

CONT_CMDS = {0xd2}
END_CMDS = {0xd3, 0x34, 0xe7}
OPT_CMDS = {0xe7, 0xe6}
NAME = {'#Name[1]': '沢原', '#Name[2]': '明日弥'}
MACRO = re.compile(r'#(?:Scale|Kana|Color|Font|Wait|Voice)\[[^\]]*\]')
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e\\]+$')
NONASCII = re.compile(r'[^\x00-\x7f\u3000]')

PLATES = {
    '#Name[1]\u3000#Name[2]',
    '天野\u3000平', '花島田\u3000英達', '日下\u3000万里', '鷹丘\u3000虎雄', '相模\u3000真',
    '一ノ瀬\u3000雛姫', '室生\u3000朔', '大風\u3000一夏', '黒崎\u3000和志', '犬飼\u3000勝頼',
    '五条\u3000薫', '香具師のおじちゃん', '#Name[2]の姉', '先輩', '花島田＆鷹丘',
    '平＆万里', '女の子１', '女の子２', 'みんな', '３人', '？？？',
}
SYS_TEXT = {'処理開始', '処理開始\\n'}
SYS_PROMPT = ('プロローグをスキップしますか？', 'どのルートのシーンを再生しますか？')

d = open(SRC, 'rb').read()


def load_files():
    n = struct.unpack_from('<I', d, 8)[0]
    ents = []
    for i in range(n):
        fid, sc, scl, sb = struct.unpack_from('<IIII', d, FAT + 16 * i)
        if sb:
            ents.append((fid, sc * 0x800, sb))
    ents.sort(key=lambda x: x[1])
    starts = sorted(e[1] for e in ents) + [len(d)]

    def fend(fs):
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


def main():
    lines, st = [], collections.Counter()
    buf = []
    skip_opt = [False]

    def flush():
        if buf:
            lines.append(''.join(buf))
            buf.clear()

    for fid, fs, fe in load_files():
        ev = [r for r in (rec_of(p) for p in file_ops(fs, fe)) if r]
        for k, s, cmd, flag in ev:
            t = s.strip()
            if k == 24:
                if cmd in OPT_CMDS and JP.search(s):
                    if skip_opt[0]:
                        st['sysopt'] += 1
                        continue
                    flush()
                    lines.append(s.strip())
                    st['opt'] += 1
                continue
            if k != 12:
                continue
            if ASCII_ONLY.match(t):
                st['label'] += 1
                continue
            if not NONASCII.search(s):
                continue
            if t in PLATES:
                # 名札＝独立名字窗，整条丢弃；框内重绘(0xd2)不清框，故不断行
                st['plate'] += 1
                continue
            if cmd == 0x33:
                st['debug'] += 1
                continue
            if t in SYS_TEXT:
                st['debug'] += 1
                continue
            if any(p in s for p in SYS_PROMPT):
                buf.clear()
                skip_opt[0] = True
                st['sysprompt'] += 1
                continue
            skip_opt[0] = False
            if cmd in CONT_CMDS:
                buf.append(s)
                st['cont'] += 1
                continue
            if cmd in END_CMDS:
                buf.append(s)
                flush()
                st['box'] += 1
                continue
            st['sys'] += 1
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
