# -*- coding: utf-8 -*-
"""PANDORA ～君の名前を、僕は知る～ (PS2, Otomate / Idea Factory 2010) 剧本文本提取

容器链路
  ISO9660 -> UNION/SCRIPT.UNI          [CRI UNI2 容器]
  UNI2 头: "UNI2" + u32 data_off(0x10000) + u32 file_count + u32 1 + u32 3
  UNI2 FAT: 从 0x810 起, 每条 16B = [FileID][startCluster][sizeClusters][sizeBytes]
            数据绝对偏移 = startCluster * 0x800
  每个子文件 = [0x1800 前缀][STCM2L 脚本]
  STCM2L 头 (偏移 +0x1800):
     0x00  generator 32B  "STCM2L <date>"
     0x20  exports_offset (相对子文件起点)
     0x24  exports_count
     0x28  unk
     0x2c  coll_link_offset
     0x30  reserved 32B
     0x50  "GLOBAL_DATA\\0" 12B
     0x5c  globals_section (u32 数组, 至 "CODE_START_")
     ...   "CODE_START_\\0" 12B  (代码段起点 = 该串偏移 + 24)
  code_section: 一串 opcode, 每条 = [u32 size][payload(size-4)]
     文本型 opcode payload = [addr][c1][c2][0][L/4][1][L][cp932 text][pad]
     换行/新框标记 opcode payload = [0][cmd][flag]   (cmd in 0xd2/0xd3/0xd4/0xf5...)

输出: 一次点击 = 一行; 说话人名丢弃; #Name[n] -> 主角名
"""
import struct
import re
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), '_work_pandora', 'UNION', 'SCRIPT.UNI')

A4 = lambda n: (n + 3) & ~3

# 换行/新框标记: 12 字节 payload 且首字段 a==0 (payload=[a][cmd][flag])
RE_SYM = re.compile(r'^[A-Za-z0-9_./\\\-:]+$')
RE_NUM = re.compile(r'^\d+$')
RE_NAME_OK = re.compile(r'^[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uff10-\uff19\uff1f\uff01\u3005\uff0d\uff0e]+$')
HIRA = re.compile(r'[\u3040-\u309f]')
RE_TEXTY = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3000-\u303f\uff01-\uff60\u2010-\u2030\u2026\u2015]')
RE_PLACEHOLDER = re.compile(r'^#Name\[(\d+)\]$')
RE_INLINE_NAME = re.compile(r'#Name\[(\d+)\]')

HEROINE = {1: 'カンナ'}      # 主角默认名 (#Name[1])

# vndb (v7866) 角色名 —— 作为说话人名的外部核对兜底
CHAR_NAMES = {
    'カンナ', 'カズト', 'ユウキ', 'マクシミリアン', 'キース', 'ボリス', 'ジョーカー',
    'イスパーダ', 'レイモンド', 'ロニー', 'トラヴィス', 'リプス', 'ジュリアンナ',
    'ロバート', 'ダグラス', 'ヘンリー', 'アシュリー', 'エリザベス',
}


def load():
    d = open(SRC, 'rb').read()
    count = struct.unpack_from('<I', d, 8)[0]
    ents = [struct.unpack_from('<IIII', d, 0x810 + 16 * i) for i in range(count)]
    return d, [e for e in ents if e[0]]


def code_range(d, fstart):
    """返回 (code_start, code_end) 绝对偏移"""
    B = fstart + 0x1800
    exp_off = struct.unpack_from('<I', d, B + 0x20)[0]
    cs = d.find(b'CODE_START_', B, fstart + exp_off)
    if cs < 0:
        return None
    return cs + 24, fstart + exp_off


def scan_strings(pay):
    """在 opcode payload 中找出所有 [0][n][1][L][text] 型字符串, 返回 [(off,text)]"""
    res = []
    n = len(pay)
    for k in range(0, n - 16 + 1, 4):
        if struct.unpack_from('<I', pay, k)[0] != 0:
            continue
        nn = struct.unpack_from('<I', pay, k + 4)[0]
        one = struct.unpack_from('<I', pay, k + 8)[0]
        L = struct.unpack_from('<I', pay, k + 12)[0]
        if one != 1 or L < 4 or L > 0x1000 or L % 4 or nn != L // 4:
            continue
        if k + 16 + L > n:
            continue
        raw = pay[k + 16:k + 16 + L].rstrip(b'\x00')
        if not raw:
            continue
        if A4(len(raw) + 1) != L:
            continue
        try:
            s = raw.decode('cp932')
        except Exception:
            continue
        if not s or any(ord(c) < 0x20 for c in s):
            continue
        res.append((k, s))
    return res


def prefix_tokens(d, fstart):
    """UNI2 子文件起始 0x1800 区块 (独立于 +0x1800 处的 STCM2L)。

    内含: 每章的小测(一问两答) / 结局用脚本 / 玩法说明 / 人名表。
    记录框架与代码段不同, 用「字符串记录扫描 + 换行标记扫描」还原:
      换行标记 = [u32 a=0][u32 cmd<0x2000][u32 flag in {0,1,2,3,4,5,6,8,9}][u32 size]
    """
    a = fstart
    b = fstart + 0x1800
    if b > len(d):
        return []
    recs = scan_strings(d[a:b])
    recset = {}
    for off, s in recs:
        recset[a + off] = s
    # 小测: 以 ？ 结尾的问题 + 紧随 2 条选项 -> 各自成行
    quiz = set()
    bal = 0
    i = 0
    while i < len(recs):
        q = recs[i][1]
        opts = recs[i + 1:i + 3]
        if (bal == 0 and len(opts) == 2
                and '「' not in q and not q.startswith(('『', '（', '('))
                and '「' not in opts[0][1]
                and q.replace('#n', '').rstrip().endswith('？')):
            for r in [recs[i]] + opts:
                quiz.add(a + r[0])
            i += 3
        else:
            bal += q.count('「') - q.count('」') + q.count('『') - q.count('』')
            i += 1
    ev = []
    for off, s in recs:
        ev.append((a + off, 'qopt' if (a + off) in quiz else 'str', s))
    for i in range(a, b - 16, 4):
        if i in recset:
            continue
        A, B, C, D = struct.unpack_from('<4I', d, i)
        if A == 0 and B < 0x2000 and C in (0, 1, 2, 3, 4, 5, 6, 8, 9) \
                and D % 4 == 0 and 0x10 <= D <= 0x10000:
            ev.append((i, 'brk', None))
    ev.sort(key=lambda x: x[0])
    return [(k, s) for _, k, s in ev]


def file_tokens(d, fstart, with_prefix=True):
    r = code_range(d, fstart)
    if not r:
        return []
    cs, ce = r
    toks = []
    i = cs
    while i < ce:
        bs = struct.unpack_from('<I', d, i)[0]
        if bs == 0 or bs % 4 or i + bs > len(d):
            break
        pay = d[i + 4:i + bs]
        ev = []
        if len(pay) == 12:
            a, cmd, fl = struct.unpack_from('<3I', pay, 0)
            if a == 0:
                ev.append((0, 'brk', None))
        ss = scan_strings(pay)
        multi_jp = len(ss) >= 2 and all(JP.search(s) for _, s in ss)
        for k, s in ss:
            # 单选记录且 "0" 字段位于 payload 偏移 24 => 5 段样式块 = 选项(菜单项)
            if k == 24 and len(ss) == 1:
                kind = 'opt'
            elif multi_jp:
                kind = 'mopt'         # 一问多答/多条并排 (小测等) -> 各自成行
            else:
                kind = 'str'
            ev.append((k, kind, s))
        ev.sort(key=lambda x: x[0])
        for _, kind, s in ev:
            toks.append((kind, s))
        i += bs
    return toks + (prefix_tokens(d, fstart) if with_prefix else [])


RE_TAG = re.compile(r'^(?:#[A-Za-z]+\[[^\]]*\])+$')
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_MUSIC = re.compile(r'^[０-９0-9]{1,2}．')          # サウンドテスト曲目 (系统/UI)
# 分支/进度标签（非玩家可见文本），实测残留
LABEL_BLACK = {'プロローグ', '拠点更新', '通過チェック', '奪還'}
GLOBAL_STR = set()


def is_noise(s):
    if s in GLOBAL_STR or s in LABEL_BLACK:
        return True
    if RE_MUSIC.match(s):
        return True
    if RE_NUM.match(s):
        return True
    if RE_SYM.match(s):
        return True
    if RE_TAG.match(s):
        return True
    return False


def looks_like_name(s):
    return 1 <= len(s) <= 10 and RE_NAME_OK.match(s) is not None


def is_dialog(s):
    return s[:1] in ('「', '『', '（', '(')


def resolve_opts(toks):
    """`opt`(5 段样式记录) 只有在同一消息内出现 select/switch/sure 标记时
    才是真正的选项; 否则还原为普通正文 (两遍法)。"""
    CHOICE_MARK = {'select', 'switch', 'end'}
    out = list(toks)
    n = len(out)
    for i in range(n):
        if out[i][0] != 'opt':
            continue
        j = i + 1
        is_choice = False
        while j < n and out[j][0] != 'brk':
            s2 = out[j][1]
            if s2 and (s2 in CHOICE_MARK or s2.startswith('sure')):
                is_choice = True
                break
            j += 1
        if not is_choice:
            out[i] = ('str', out[i][1])
    return out


def collect_labels(all_toks, freq, lookahead=4):
    labels = set()
    seq = [t[1] for t in all_toks if t[0] in ('str', 'opt', 'qopt', 'mopt')]
    for k, s in enumerate(seq):
        if is_noise(s) or not looks_like_name(s) or is_dialog(s):
            continue
        if not RE_TEXTY.search(s) or HIRA.search(s):
            continue
        if freq[s] < 2:          # 说话人名会反复出现; 章节/结局标题只出现一次
            continue
        for j in range(k + 1, min(len(seq), k + 1 + lookahead)):
            nx = seq[j]
            if is_noise(nx) or (looks_like_name(nx) and nx in labels):
                continue
            if nx[:1] in ('「', '『'):
                labels.add(s)
            break
    return labels | CHAR_NAMES


def sub_placeholder(s):
    return RE_INLINE_NAME.sub(lambda m: HEROINE.get(int(m.group(1)), m.group(0)), s)


def clean(s):
    """#Name[n] -> 主角名; 行内软换行标记 #n / #n#n 合并(删除)。"""
    return RE_INLINE_NAME.sub(
        lambda m: HEROINE.get(int(m.group(1)), m.group(0)), s).replace('#n', '')


def repair_quotes(s):
    """原作脚本个别行只写了单侧引号 (照原始字节核对属实), 按作者意图补足。
    仅做引号补/删, 不改动任何文字。"""
    o, c = s.count('「'), s.count('」')
    if o != c:
        if c > o:
            if c - o == 1 and s.endswith('」」'):
                s = s[:-1]                     # 多打了一个 」
            elif '（' in s and s.endswith('」'):  # 括号误用 」 收尾
                s = s[:-1] + '）'
            else:
                s = '「' * (c - o) + s          # 缺开引号
        else:
            s += '」' * (o - c)                 # 缺闭引号
    o, c = s.count('（'), s.count('）')
    if o != c:
        s += '）' * (o - c) if o > c else '（' * (c - o)
    o, c = s.count('('), s.count(')')
    if o != c:
        s += ')' * (o - c) if o > c else '(' * (c - o)
    return s


def build_lines(all_toks, labels):
    lines = []
    buf = []

    def flush():
        if buf:
            t = ''.join(buf)
            if t.strip():
                lines.append(t)
            buf.clear()

    def open_quote(nxt=None):
        """缓冲区里有未闭合的 「 且下一段不是新起的台词(不以「开头) -> 该句被拆到下一框, 不切。"""
        t = ''.join(buf)
        if not t or len(t) >= 200:
            return False
        op = t.count('「') + t.count('（') + t.count('(')
        cl = t.count('」') + t.count('）') + t.count(')')
        if op <= cl:
            return False
        return not (nxt and nxt[:1] in ('「', '（', '('))

    def next_text(k):
        j = k + 1
        while j < len(all_toks) and all_toks[j][0] == 'brk':
            j += 1
        return all_toks[j][1] if j < len(all_toks) else None

    for idx, (kind, s) in enumerate(all_toks):
        if kind == 'brk':
            if open_quote(next_text(idx)):
                continue
            flush()
            continue
        if kind == 'opt':
            # 选项(菜单项)/并排多条: 独立成行
            flush()
            if not is_noise(s):
                lines.append(clean(s))
            continue
        if kind in ('qopt', 'mopt'):
            flush()
            if not is_noise(s):
                lines.append(clean(s))
            continue
        # 资源/系统/符号串: 作为边界, 内容丢弃
        if is_noise(s):
            if open_quote(next_text(idx)):
                continue
            flush()
            continue
        # 独立占位符 = 说话人(主角) -> 丢弃并断行
        if RE_PLACEHOLDER.match(s):
            if open_quote(next_text(idx)):
                continue
            flush()
            continue
        # 说话人名 (两遍法判定) -> 丢弃并断行
        if looks_like_name(s) and s in labels:
            if open_quote():
                continue
            flush()
            continue
        buf.append(s)
    flush()
    return [repair_quotes(clean(x)) for x in lines]


def prefix_quiz(d, fstart):
    """UNI2 子文件 0x1800 前缀里的小测数据 (一问两答)。

    仅取「以 ？ 结尾的问题 + 紧随的 2 个选项」，其余(玩法说明/人名表)丢弃。
    """
    recs = scan_strings(d[fstart:fstart + 0x1800])
    out = []
    i = 0
    while i < len(recs):
        s = recs[i][1]
        if s.replace('#n', '').rstrip().endswith('？'):
            out.append(('opt', s))
            for j in (i + 1, i + 2):
                if j < len(recs):
                    out.append(('opt', recs[j][1]))
            i += 3
        else:
            i += 1
    return out


def main():
    global GLOBAL_STR
    d, ents = load()
    per = []
    pfx = []          # 各文件 0x1800 前缀里的「ミッション小测(豆知識)」-> 统一并入文末
    for e in ents:
        pt = prefix_tokens(d, e[1] * 0x800)
        per.append((e[0], file_tokens(d, e[1] * 0x800, with_prefix=False)
                    + [t for t in pt if t[0] != 'qopt']))
        pfx.extend(t for t in pt if t[0] == 'qopt')
    # 外层全局脚本 (fstart=0): 军用术语小测(豆知識)等, 置于全文末尾
    outer = [t for t in file_tokens(d, 0)]
    freq = collections.Counter()
    for _, t in per + [(0, outer)]:
        for s in set(x[1] for x in t if x[0] in ('str', 'opt', 'qopt', 'mopt')):
            freq[s] += 1
    GLOBAL_STR = {s for s, c in freq.items() if c >= 20}
    print("global/system strings:", sorted(GLOBAL_STR)[:20], file=sys.stderr)
    all_toks = []
    for _, t in per:
        all_toks.extend(t)
    all_toks.extend(outer)
    all_toks.extend(pfx)
    all_toks = resolve_opts(all_toks)
    print("files:", len(ents), "tokens:", len(all_toks), file=sys.stderr)
    labels = collect_labels(all_toks, freq)
    print("labels(%d):" % len(labels), sorted(labels), file=sys.stderr)
    lines = build_lines(all_toks, labels)
    out = os.path.join(os.path.dirname(HERE), '提取结果', 'PANDORA_全文本.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print("lines:", len(lines), "->", out, file=sys.stderr)


if __name__ == '__main__':
    main()
