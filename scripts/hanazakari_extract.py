# -*- coding: utf-8 -*-
"""花朧 ～戦国伝乱奇～ (PSV, PCSG00855, Otomate/Idea Factory) 文本提取

链路：
  pkg -> pkg2zip -x -> psvpfsparser -z(zRIF) -> dec/data/{STORY,GAME,SYSTEM}.cpk
  STORY.cpk/SCRIPT/<route>/*.DAT = STCM2L (UTF-8)
  SYSTEM.cpk/DATABASE/dbDictionary.gbin = 用語辞典

STCM2L(本作变体)
  0x00 'STCM2L <date>'
  0x20 export_addr   0x2c collection_addr
  'CODE_START_' (+12) -> 指令流，止于 export_addr
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length] + nparams*[p0,p1,p2]
         串参数指向 [0][L/4][1][L][utf8 text][pad]

  ★ opcode 逐文件位移 Δ∈{0,+0x20,+0x40,-0x20}（内置 op 不位移）
      TEXT   = 0xD0C4 + Δ
      NAME   = 0xD7C0 + Δ     名札（整行丢弃）
      OPT    = 0xE2E8 + Δ     选项（p0=选项文本）
      OPTLBL = 0xE23C + Δ     '選択肢Ａ' 槽位标记
      WAIT   = 0x1F4          显示+等待点击（内置，不位移）= 断框 L0 证据

  ★ 一次点击 = 一行：连续 TEXT（其间无 WAIT/NAME/OPT）⇒ 同框软换行，合并。
    全库仅此一种「等待」指令，无第二种清框指令 ⇒ 单版。
"""
import struct, re, os, sys, glob, json

HERO = '市'          # #Name[1] 主角（vndb v19288：織田市／nameable，默认名 市）

# 字体槽替换（字体 advfont.ffu 无 U+3001/U+3002 等映射，游戏用下列槽位渲染标点）
SLOT = {
    'Χ': '、', 'Δ': '。', 'Λ': 'っ', 'Ι': '！',
    '∴': '『', '∵': '』', '∫': '「', '∨': '」',
    'П': '（', 'Ц': '）', 'Ж': 'ょ', 'Ф': 'ゅ', 'И': 'ゃ', '∇': 'ッ',
}
RE_NAME = re.compile(r'#Name\[1\]')
RE_TITLE = re.compile(r'^(序ノ章|[^\s]{1,12}\u3000[^\s]{1,8}ノ章(\u3000.+)?)$')
RE_COLOR = re.compile(r'#(?:Color|color)\[\d+\]')

WAIT = 0x1F4
TEXT_BASE = 0xD0C4
NAME_BASE = 0xD7C0
OPT_BASE = 0xE2E8
OPTLBL_BASE = 0xE23C


def clean(s):
    s = RE_COLOR.sub('', s)
    s = RE_NAME.sub(HERO, s)
    s = s.replace('#n', '')
    for k, v in SLOT.items():
        s = s.replace(k, v)
    return s


def srec(d, p, np_, ln, k):
    if k >= np_:
        return None
    q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
    if not (p < q < p + ln - 16) or q + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, q)
    if c != 1 or b != L // 4 or not (0 < L < 0x8000) or q + 16 + L > len(d):
        return None
    return d[q + 16:q + 16 + L]


def text_of(d, p, np_, ln, k=0):
    raw = srec(d, p, np_, ln, k)
    if raw is None:
        return None
    raw = raw.split(b'\x00')[0]
    try:
        return raw.decode('utf-8')
    except Exception:
        return None


def parse(d):
    ins = []
    if b'CODE_START_' not in d:
        return ins
    export = struct.unpack_from('<I', d, 0x20)[0]
    p = d.find(b'CODE_START_') + 12
    while p < export:
        if p + 16 > len(d):
            break
        ic, op, np_, ln = struct.unpack_from('<4I', d, p)
        if ln < 16 or ln % 4 or p + ln > len(d) or np_ > 0x200:
            break
        ins.append((p, ic, op, np_, ln))
        p += ln
    return ins


def detect_delta(d, ins):
    import collections
    c = collections.Counter()
    for (p, ic, op, np_, ln) in ins:
        if ic == 1 and np_ == 1 and 0xD000 <= op <= 0xD400:
            c[op] += 1
    if not c:
        return None
    op = c.most_common(1)[0][0]
    return op - TEXT_BASE


def extract_file(path, hero=HERO):
    d = open(path, 'rb').read()
    ins = parse(d)
    if not ins:
        return []
    delta = detect_delta(d, ins)
    if delta is None:
        return []
    TEXT, NAME, OPT, OPTLBL = TEXT_BASE + delta, NAME_BASE + delta, OPT_BASE + delta, OPTLBL_BASE + delta
    out, cur = [], []

    def flush():
        if cur:
            t = ''.join(cur).strip(' \u3000\t')
            # 系统 UI：章選択時の「選択肢確認」プロンプト（直接上屏但不是正文）
            if t and not t.startswith('通過した選択肢を決定して下さい。'):
                out.append(t)
            del cur[:]

    seen_opt = False
    for (p, ic, op, np_, ln) in ins:
        if op == TEXT:
            s = text_of(d, p, np_, ln, 0)
            if s is None:
                continue
            if s.strip(' \u3000\t') == '':
                flush()
            else:
                cur.append(clean(s))
        elif op == NAME:
            flush()
        elif op == OPTLBL:
            flush()
        elif op == OPT:
            flush()
            s = text_of(d, p, np_, ln, 0)
            if s and s.strip():
                out.append(clean(s).strip(' \u3000\t'))
        elif op == WAIT:
            flush()
    flush()
    return out


def glossary(path):
    """dbDictionary.gbin：20 字节记录表 [u16 id][u8][u8][u32 pad][u32 见出し][u32 読み][u32 解説]
    三个偏移是「字符串区基址」的相对偏移（基址 = 首条见出し语偏移）。"""
    d = open(path, 'rb').read()
    base = d.find('明智光秀'.encode('utf-8'))
    if base < 0:
        return []
    out = []
    for i in range(0, base, 20):
        f1, f2, f3 = struct.unpack_from('>3I', d, i + 8)
        if not (f1 < f2 < f3) or base + f3 >= len(d):
            continue
        t = d[base + f1:d.find(b'\x00', base + f1)]
        de = d[base + f3:d.find(b'\x00', base + f3)]
        try:
            t = t.decode('utf-8')
            de = de.decode('utf-8')
        except Exception:
            continue
        if not t.strip() or not de.strip():
            continue
        out.append('【%s】%s' % (clean(t), clean(de)))
    return out


if __name__ == '__main__':
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    # 只收 00(共通+序章)〜06(あとがたり)；07=MISSION 战斗提示(系统 UI)、08=シーン選択(回想) 不收
    files = []
    for d in ['00', '01', '02', '03', '04', '05', '06']:
        fs = sorted(glob.glob(os.path.join(root, 'SCRIPT', d, '*.DAT')))
        if d == '00':
            # 序章 pro_01 排最前
            fs.sort(key=lambda p: (0 if 'pro_' in os.path.basename(p) else 1, p))
        files += fs
    lines = []
    for f in files:
        lines += extract_file(f)
    lines += glossary(sys.argv[3] if len(sys.argv) > 3 else os.path.join(root, 'DATABASE', 'dbDictionary.gbin'))
    txt = '\ufeff' + '\n'.join(lines) + '\n'
    sys.stdout.reconfigure(encoding='utf-8')
    out = sys.argv[2] if len(sys.argv) > 2 else 'out.txt'
    open(out, 'w', encoding='utf-8', newline='\n').write(txt)
    print('files', len(files), 'lines', len(lines))
