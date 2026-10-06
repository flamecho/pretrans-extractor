# -*- coding: utf-8 -*-
"""悪役令嬢は隣国の王太子に溺愛される (Switch, OPERAHOUSE, Unity / CSR1.00) 全文本提取。

源：romfs/Data/StreamingAssets/
  csr/adv*.CSR    剧本（CSR1.00 自定义字节码）
  localize.csv    UI/章节/图鉴 文本（Jp/En）

CSR 结构：
  "CSR1.00\\0"(8) + u32 header_size + (header_size-12)/8 × {u32 id, u32 off}
  脚本流（<u16 opcode> + 操作数）：
    0x0600 <u8 nameid>  : 设置说话人（nameid 见 localize_name.csv）
    0x0601 <UTF-8> \\0   : 文本框 A —— 有名字=台词；nameid 0/98=旁白/地の文
    0x0603 <UTF-8> \\0   : 文本框 B —— 内心独白
    0x0410 <UTF-8> \\0   : 提问横幅
    0x0411 <u8 0> <UTF-8> \\0 : 选择支
  正文内 0x01 = 框内换行（合并）；少数行前置 0x1e XX XX XX 非文本 token，取最后一个 text opcode 之后的正文。

★ 引号（游戏由 UI 自动加，脚本里不含）：
    剧本全语料中「」出现 0 次；旁白引用用 『』、独白内引用用 “” 代替
    ⇒ 0x0601 且有名字 = 台词 → 「…」
       0x0603              = 内心独白 → （…）
       0x0601 且 nameid∈{0,98} = 旁白/地の文 → 不加
用法（解包出 romfs 后）：
    python akuyaku_extract.py <StreamingAssets 目录> <输出.txt> [副输出_无括号.txt]

默认值对应恶役令嬢的临时解包目录；换作品时按上表传参即可。
"""
import glob, re, os, sys, csv, io

BASE = sys.argv[1] if len(sys.argv) > 1 else 'StreamingAssets'
CSRDIR = os.path.join(BASE, 'csr')
LOC = os.path.join(BASE, 'localize.csv')
NAMECSV = os.path.join(BASE, 'localize_name.csv')
OUT = sys.argv[2] if len(sys.argv) > 2 else 'akuyaku_全文本.txt'
OUT_NOQ = sys.argv[3] if len(sys.argv) > 3 else (os.path.splitext(OUT)[0] + '_无括号.txt')

BRACKET = True                    # 是否按游戏显示加引号
Q_SPEECH = ('「', '」')            # 台词
Q_MONO = ('（', '）')              # 内心独白

JP = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')
TEXT_OPS = [b'\x06\x01', b'\x06\x03']


def load_names():
    rows = list(csv.DictReader(io.StringIO(open(NAMECSV, encoding='utf-8-sig').read())))
    return {int(r['ID']): r['Jp'] for r in rows}


def clean(t):
    best = -1
    for op in TEXT_OPS:
        k = t.rfind(op.decode('latin1'))
        if k > best:
            best = k
    if best >= 0:
        t = t[best + 2:]
    t = re.sub('\x01\u3000', '', t).replace('\x01', '')
    t = ''.join(c for c in t if ord(c) >= 0x20 or c == '\u3000')
    return t.strip('\u3000 \t')


def extract_csr(fn, names):
    d = open(fn, 'rb').read()
    items = []

    def nameid(pos):
        for k in range(pos - 2, max(-1, pos - 60), -1):
            if d[k] == 0x06 and d[k + 1] == 0x00 and k + 2 < len(d) and d[k + 2] in names:
                return d[k + 2]
        return None

    def push(pos, op, raw):
        try:
            t = raw.decode('utf-8')
        except UnicodeDecodeError:
            return
        if not JP.search(t):
            return
        t = clean(t)
        if not t:
            return
        if BRACKET:
            nid = nameid(pos)
            narration = nid in (0, 98)
            if op == b'\x06\x03' and not narration:
                t = Q_MONO[0] + t + Q_MONO[1]
            elif op == b'\x06\x01' and not narration:
                t = Q_SPEECH[0] + t + Q_SPEECH[1]
        items.append((pos, t))

    for op in TEXT_OPS:
        for m in re.finditer(re.escape(op), d):
            s = m.end(); j = d.find(b'\x00', s)
            if j >= 0:
                push(m.start(), op, d[s:j])
    for m in re.finditer(rb'\x04\x10', d):
        s = m.end(); j = d.find(b'\x00', s)
        if j >= 0:
            push(m.start(), b'\x04\x10', d[s:j])
    for m in re.finditer(rb'\x04\x11', d):
        s = m.end()
        if s < len(d) and d[s] == 0:
            s += 1
        j = d.find(b'\x00', s)
        if j >= 0:
            push(m.start(), b'\x04\x11', d[s:j])
    items.sort(key=lambda x: x[0])
    out, last = [], None
    for pos, t in items:
        if last == (pos, t):
            continue
        out.append(t)
        last = (pos, t)
    return out


def read_localize(path):
    txt = open(path, encoding='utf-8-sig').read().splitlines()
    res = []
    for r in csv.DictReader(io.StringIO('\n'.join(txt))):
        v = (r.get('Jp') or '').strip()
        if v:
            res.append(v.replace('\\n', ''))
    return res


def main():
    names = load_names()
    story = []
    for fn in sorted(glob.glob(os.path.join(CSRDIR, 'adv*.CSR'))):
        story += extract_csr(fn, names)
    lines = story + read_localize(LOC)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        for ln in lines:
            w.write(ln + '\n')
    print('story %d  +  system %d  =  %d' % (len(story), len(lines) - len(story), len(lines)))
    print('->', OUT)

    # 无括号变体
    global BRACKET
    BRACKET = False
    story2 = []
    for fn in sorted(glob.glob(os.path.join(CSRDIR, 'adv*.CSR'))):
        story2 += extract_csr(fn, names)
    lines2 = story2 + read_localize(LOC)
    with open(OUT_NOQ, 'w', encoding='utf-8-sig', newline='\n') as w:
        for ln in lines2:
            w.write(ln + '\n')
    print('->', OUT_NOQ, len(lines2))


if __name__ == '__main__':
    main()
