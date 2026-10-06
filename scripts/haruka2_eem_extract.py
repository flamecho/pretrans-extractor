# -*- coding: utf-8 -*-
"""遙かなる時空の中で２ (PSP) 全文本提取  — 最终版
容器: KOEID0.BIN = Koei CDAR v2
EEM 剧本: het/%02d%04d（972 个）+ het/GPM（汎用メッセージ）
       头部/表A/正文B 各自以 55 字节密钥 XOR 解密（每块从块首重置相位）
       密钥 = b"(C) KOEI. Copyright KOEI Co.,ltd. All rights reserved.\x00"
      （该密钥位于 BOOT.BIN 文件偏移 0x1737D4）
"""
import struct, zlib, re, sys, io

P = 'iso/PSP_GAME/USRDIR/KOEID0.BIN'
ROWS = [l.split('\t') for l in open('names0.txt', encoding='utf-8').read().splitlines()]
_F = open(P, 'rb')
ELF = open('iso/SYSDIR/BOOT.BIN', 'rb').read()
KEY = ELF[0x173780 + 0x54: 0x173780 + 0x54 + 55]


# ===== 16x16「呼び名」称呼矩阵（BOOT.BIN 偏移 0x17C9AC 的指针表）=====
_MBASE = 0x17C9AC
_CH = ['高倉花梨', '源\u3000頼忠', '平\u3000勝真', 'イサト', '彰紋', '藤原幸鷹', '翡翠',
       '源\u3000泉水', '安倍泰継', 'アクラム', 'シリン', '和仁', '源\u3000時朝',
       '平\u3000千歳', '藤原\u3000紫', '藤原深苑']

def _mstr(i):
    va = struct.unpack_from('<I', ELF, _MBASE + 4 * i)[0]
    if not (0x100000 < va < 0x200000):
        return ''
    fo = va + 0x54
    e = ELF.find(b'\x00', fo)
    if e < 0 or e - fo > 40:
        return ''
    try:
        return ELF[fo:e].decode('cp932')
    except Exception:
        return ''

MATRIX = [[_mstr(r * 16 + c) for c in range(16)] for r in range(16)]
_NAME_ROW = {n: i for i, n in enumerate(_CH)}

def appellation(speaker, target):
    r = _NAME_ROW.get(speaker); c = _NAME_ROW.get(target)
    if r is None or c is None:
        return ''
    return MATRIX[r][c]

FONT_REMAP = {'\uff04': '\uff01\uff1f', '\uffe0': '\uff01\uff01', '\uffe1': '\uff1f\uff01'}

# CHR 文件给出的官方人物名 → 呼び名（通称）
APP = {'高倉花梨': '花梨', '主人公': '花梨',
       '源\u3000頼忠': '頼忠', '平\u3000勝真': '勝真', 'イサト': 'イサト', '彰紋': '彰紋',
       '藤原幸鷹': '幸鷹', '翡翠': '翡翠', '源\u3000泉水': '泉水', '安倍泰継': '泰継',
       'アクラム': 'アクラム', 'シリン': 'シリン', '和仁': '和仁',
       '源\u3000時朝': '時朝', '平\u3000千歳': '千歳', '藤原\u3000紫': '紫', '藤原深苑': '深苑'}
NAMES = set(APP)
# 全部 43 个官方人物名（CHR）——用于识别说话人行首标签
SPEAKERS = set(APP) | {
 '高倉花梨','源\u3000頼忠','平\u3000勝真','イサト','彰紋','藤原幸鷹','翡翠','源\u3000泉水','安倍泰継',
 'アクラム','シリン','和仁','源\u3000時朝','平\u3000千歳','藤原\u3000紫','藤原深苑','上級貴族','武士',
 '女房','青年貴族','男の子','老婆','僧侶','おばさん','翁','陰陽師','？？？','泉水の母','院','帝',
 '青龍','朱雀','白虎','玄武','降三世明王','軍荼利明王','大威徳明王','金剛夜叉明王','連理の賢木',
 '龍神','応龍','白龍','黒龍'}

VARMAP = {'＄０': '【変数0】', '＄１': '【変数1】', '＄２': '【変数2】', '＄３': '【変数3】',
          '地名称': '【地名称】', '現在地名称': '【現在地名称】', '現在地属性': '【現在地属性】',
          '現在地道具': '【現在地道具】', '現在地術': '【現在地術】',
          '味方勢力': '【味方勢力】', '敵勢力': '【敵勢力】', '人物属性': '【人物属性】',
          '八葉情報': '【八葉情報】',
          '呼び名指定同行八葉１': '【同行八葉１】', '呼び名指定同行八葉２': '【同行八葉２】',
          '指定同行八葉１': '【同行八葉１】', '指定同行八葉２': '【同行八葉２】',
          '同行八葉１': '【同行八葉１】', '同行八葉２': '【同行八葉２】',
          '指定同行者２': '【同行者２】', '指定人物２': '【指定人物２】', '指定人物': '【指定人物】',
          '同行者１': '【同行者１】', '同行者２': '【同行者２】',
          '好きな場所１': '【好きな場所１】', '好きな場所２': '【好きな場所２】', '好きな場所３': '【好きな場所３】',
          '主人公姓名': '高倉花梨', '主人公姓': '高倉', '主人公名': '花梨',
          '初日': '初日', '中日１': '中日１', '中日２': '中日２', '中日３': '中日３', '中日４': '中日４',
          '終日': '終日'}
TAGRE = re.compile(r'［([^］]*)］')
var_used = {}

def entry(i):
    idx, name, a, off, size = ROWS[i]; off = int(off); size = int(size)
    _F.seek(off); blob = _F.read(max(size, 1))
    if blob[:1] == b'\x78':
        try: return zlib.decompress(blob)
        except Exception: return blob
    return blob

def hpt(i):
    """HPT 家族 (CHR/DIC/FLT/GPM): 头 8 字节明文, 正文自偏移 8 起以同一 55 字节密钥解密"""
    d = entry(i)
    return bytes(d[8 + j] ^ KEY[j % 55] for j in range(len(d) - 8))

def dec(b):
    return bytes(b[i] ^ KEY[i % 55] for i in range(len(b)))

def eem_body(i):
    d = entry(i)
    h = dec(d[8:0x100])
    chkA, chkB, typ, boff, sizeA, sizeB = struct.unpack_from('<6I', h, 0)
    A = dec(d[boff:boff + sizeA])
    B = dec(d[boff + sizeA:boff + sizeA + sizeB])
    return A, B, (sum(A) & 0xffffffff) == chkA and (sum(B) & 0xffffffff) == chkB

def all_idx():
    return sorted([i for i in range(len(ROWS)) if len(ROWS[i][1]) == 6 and ROWS[i][1].isdigit()],
                  key=lambda i: ROWS[i][1])

def resolve(s, speaker=None):
    s = TAGRE.sub(lambda m: '\x00' + m.group(1) + '\x01', s)
    def _app(m):
        tgt = m.group(1)
        v = appellation(speaker, tgt)
        if not v:
            v = APP.get(tgt, tgt)
        return v
    s = re.sub('\x00呼び名\x01\x00([^\x00\x01]*)\x01', _app, s)
    s = s.replace('主人公姓名', '高倉花梨').replace('主人公姓', '高倉').replace('主人公名', '花梨')
    def rep(m):
        t = m.group(1)
        if t in NAMES or t == '呼び名':
            return t
        if t in VARMAP:
            v = VARMAP[t]
            if v.startswith('【'):
                var_used[t] = var_used.get(t, 0) + 1
            return v
        return ''                     # 表情 / 音声 / 眨眼 / 等待 / 场景标签 → 丢弃
    s = re.sub('\x00([^\x00\x01]*)\x01', rep, s)
    s = s.replace('\x00', '').replace('\x01', '')
    s = s.replace('｛', '').replace('｝', '')
    for k, v in FONT_REMAP.items():
        s = s.replace(k, v)
    return s

def parse(B):
    out, seg = [], []
    state = {'spk': None}
    def flush():
        if seg:
            t = resolve(''.join(seg), state['spk']).strip()
            if t:
                out.append(t)
        seg.clear()
    for ln in B.decode('cp932', 'replace').split('\r\n'):
        if ln.startswith('#'):
            continue
        s = ln.strip()
        if not s:
            continue
        m = re.match(r'^(\d{4})\.(.*)$', s)
        if m:
            flush()
            rest = m.group(2)
            mm = re.match(r'^［([^］]*)］', rest)
            if mm and mm.group(1) in SPEAKERS:
                state['spk'] = mm.group(1)      # 记录说话人（用于称呼矩阵）
                rest = rest[mm.end():]          # 去掉说话人行首标签
            if not rest.strip():
                continue
            s = rest
        while True:
            pos = [p for p in (s.find('■'), s.find('▼'), s.find('▽')) if p >= 0]
            if not pos:
                seg.append(s); break
            k = min(pos)
            seg.append(s[:k]); flush()
            s = s[k + 1:]
            if not s.strip():
                break
    flush()
    return out

def dump_plain(txt, path):
    with io.open(path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(txt.replace('\r\n', '\n'))


def dict_lines():
    """豆辞典 -> 【条目名】内容  (内容 = 说明正文；读音另存 out_dictionary*.txt)"""
    raw = hpt(2636).decode('cp932', 'replace').replace('\r\n', '\n')
    i = raw.find('\n000.')
    body = raw[i + 1:]
    out, k = [], 0
    ls = body.split('\n')
    while k < len(ls):
        m = re.match(r'^\d*\.(.+)$', ls[k])
        if m and not ls[k].startswith('#'):
            term = m.group(1).strip()
            k += 2                                   # 跳过读音行
            b = []
            while k < len(ls) and ls[k].strip() and not re.match(r'^\d*\.', ls[k]):
                b.append(ls[k].strip()); k += 1
            if term and b:
                out.append('【%s】%s' % (term, ''.join(b)))
        else:
            k += 1
    return out

def main():
    # 1) EEM 剧本 972 个
    lines = []
    for i in all_idx():
        A, B, ok = eem_body(i)
        if ok:
            lines.extend(parse(B))
    # 2) GPM 汎用メッセージ
    n_eem = len(lines)
    lines.extend(parse(hpt(2638)))
    # 3) 豆辞典按【条目名】内容 追加到 dialogue 末尾
    dl = dict_lines(); nd = len(dl); lines.extend(dl)
    with io.open('out_dialogue.txt', 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('dialogue lines:', len(lines), '(EEM %d + GPM %d + 豆辞典 %d)' % (n_eem, len(lines) - n_eem - nd, nd))

    # 3) 豆辞典
    dump_plain(hpt(2636).decode('cp932', 'replace'), 'out_dictionary.txt')
    # 4) 人物表 / 表情表
    dump_plain(hpt(2635).decode('cp932', 'replace'), 'out_names.txt')
    dump_plain(hpt(2637).decode('cp932', 'replace'), 'out_expressions.txt')
    # 5) HP 帮助
    dump_plain(entry(2639).decode('cp932', 'replace'), 'out_help.txt')
    build_dictionary()
    print('unresolved:', var_used)


def build_dictionary():
    """豆辞典: 解析 out_dictionary.txt 的条目"""
    raw = hpt(2636).decode('cp932', 'replace').replace('\r\n', '\n')
    lines = raw.split('\n')
    ents, i = [], 0
    while i < len(lines):
        m = re.match(r'^(\d+)\.(.+)$', lines[i])
        if m and not lines[i].startswith('#'):
            term = m.group(2).strip()
            i += 1
            ruby = lines[i].strip() if i < len(lines) else ''
            i += 1
            body = []
            while i < len(lines) and lines[i].strip() and not re.match(r'^\d+\.', lines[i]) and not lines[i].startswith('#'):
                body.append(lines[i].strip()); i += 1
            ents.append((term, ruby, ''.join(body)))
        else:
            i += 1
    out = []
    for term, ruby, body in ents:
        out.append('%s（%s）\t%s' % (term, ruby, body))
    with io.open('out_dictionary_clean.txt', 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('dictionary entries:', len(out))

if __name__ == '__main__':
    main()
