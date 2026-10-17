# -*- coding: utf-8 -*-
"""L2 Love×Loop (PS2 / Idea Factory / SLPM-55191) 剧本文本提取

容器链路
  ISO9660 -> UNION/SCRIPT.UNI                    [CRI UNI2]
    UNI2 头 : "UNI2" + u32(0x10000) + u32 file_count + u32 1 + u32 4
    FAT     : 0x810 起, 16B/条 = [FileID][startCluster][sizeClusters][sizeBytes]
              绝对偏移 = startCluster*0x800
              子文件末尾须按 **簇对齐大小**(sizeClusters*0x800) 走, 否则尾条被截
    子文件  : [0x2000 符号/资源表][STCM2L 脚本 @ +0x2000]
    STCM2L 头: +0x00 generator32B ; +0x20 exports_offset(相对 fstart)
               -> "GLOBAL_DATA" ... -> "CODE_START_\0" -> 代码段 = 该串偏移 + 24
  代码段 = opcode 链 [u32 size][payload]
    文本记录 payload = [addr][样式*k][0][L/4][1][L][cp932 text][pad]
      k=12 (2 个样式字段) = 正文/台词/名札 (绝大多数)
      k=24 (5 个样式字段) = 选项(尾 230/231) / 资源名(其余)
    记录后尾随 12B 标记 [0][cmd][flag], cmd 即「该文本所属 opcode 号」:
      210/211(0xd2/0xd3) = 正文行, 211 = **换框(一次点击)**
      212(0xd4) = 说话人名札
      230/231            = 选项(二选一)
      2/3/4              = 正文整框(框内换行以字面 `#n` 表示, 须删除合并)
      52/102             = 行き先/キーワード 菜单项(选项)
      1 = 章选择菜单(系统) ; 406 = `なし`(填充) ; 0/51 = 标签/调试串
  行粒度 = 一次点击一行: 同框内 210 连续行直接拼接; 211 收行
  说话人名札(k=12 独立成条 / 同记录内 `名＋「`) -> 丢弃, 不加前缀
  #Name[1] = 主角名宏 -> ナナミ (默认名表见 SCRIPT.UNI 0x9060:
             [2][1][8]"ナナミ" / [2][1][8]"ななみ")
"""
import struct, os, re, sys, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC = os.path.join(VNTRANS_HOME, '_work_l2ll/iso/UNION/SCRIPT.UNI')
OUT = os.path.join(VNTRANS_HOME, '提取结果/L2 Love×Loop 全文本.txt')
PREFIX = 0x2000
HERO_DEFAULT = 'ナナミ'
A4 = lambda n: (n + 3) & ~3
JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')

d = open(SRC, 'rb').read()

# ── 收 / 不收 ─────────────────────────────────────────────
SKIP_FILES = {1, 2, 3, 4, 5, 7, 8,        # 系统数据 / 角色表
              50, 51, 52, 53, 54, 55, 56,  # 无正文
              80, 81, 82, 83,              # 调试脚本(デバッグ/バトルデバッグ/分岐テスト)
              115, 128, 145, 152}          # 纯「夜会话路由表」派发文件
DROP_EXACT = {'　', '\u3000', '処理開始', r'処理開始\n', 'スクリプト開始', r'スクリプト開始\n'}
SYS_PAT = [
    r'^クリアデータを引き継ぎますか？$',
    r'^プロローグをスキップしますか？$',
    r'^ＬＶ・アイテムを引き継ぎました$',
    r'^＜.+＞$',
    r'.+を選(択)?び?ました$',
    r'^夜会話で.+$',
    r'^.*へ到達$',
    r'^.+を選んでください$',
    r'^.+の動作チェックへ.*$',
    r'^バトルデバッグへいきますか？$',
    r'^通常選択肢です。$',
    r'^選択肢[１２]を選んだ結果$',
    r'^←否定　肯定→$',
    r'^次回予告！$',
    r'^情報収集選択肢[１-５]$',
    r'^ご指名ありがとうございます。$',
    r'^情報収集[１-５]ご指名ありがとうございます。$',
    r'^(キーワード|選択肢|ポイント)[^\u3040-\u30ff]*$',
    r'^処理開始.*$',
]
SYS_RE = re.compile('|'.join(SYS_PAT))
RE_ASCII = re.compile(r'^[\x20-\x7e]+$')
RE_MACRO_ONLY = re.compile(r'^(#[A-Za-z]+\[[^\]]*\])+$')
# 说话人名札判据: 短、无句读、含假名/汉字
RE_NAME_OK = re.compile(r'^[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uff10-\uff19\uff1f\uff01\u3005\u2010-\u2015０-９]+$')
# 名札候选的自举阈值: 出现 ≥3 次
NAME_MIN = 2
# 自举阈值(≥2) 之外的**低频说话人名札**(独立成条·紧邻引号, 逐条人工确认)
NAME_EXTRA = {'騎士団員', '壮年男性', '壮年の男性', '壮年の女性', '赤子', 'お姉さん',
              '女２', '子供１', '全員', 'ユン、リュカ', 'エウア？', 'かごめ？', '？？？・？？？'}
# 尾随标记语义
T_TAIL = {210, 211}          # 正文行 (211 = 换框)
T_NAME = 212                 # 说话人名
T_OPT = {230, 231}           # 选项 (二选一)
T_BOX = {2, 3, 4}            # 正文整框 (框内 `#n`)
T_MENU = {52, 102}           # 行き先 / キーワード 菜单项(选项)


def load():
    count = struct.unpack_from('<I', d, 8)[0]
    ents = [struct.unpack_from('<4I', d, 0x810 + 16 * i) for i in range(count)]
    ents = [e for e in ents if e[0] and e[1]]
    starts = sorted(e[1] * 0x800 for e in ents) + [len(d)]

    def fend_of(e):
        fs = e[1] * 0x800
        nxt = next(s for s in starts if s > fs)
        return nxt + PREFIX               # 末条可能跨入下一文件的 0x2000 前缀区

    return [(e[0], e[1] * 0x800, fend_of(e)) for e in ents]


def scan(pay):
    res = []
    for k in range(0, len(pay) - 16 + 1, 4):
        if struct.unpack_from('<I', pay, k)[0] != 0:
            continue
        nn = struct.unpack_from('<I', pay, k + 4)[0]
        one = struct.unpack_from('<I', pay, k + 8)[0]
        L = struct.unpack_from('<I', pay, k + 12)[0]
        if one != 1 or L < 4 or L > 0x1000 or L % 4 or nn != L // 4:
            continue
        end = k + 16 + L
        if end > len(pay):
            continue
        raw = pay[k + 16:end].rstrip(b'\x00')
        if not raw or A4(len(raw) + 1) != L:
            continue
        try:
            s = raw.decode('cp932')
        except Exception:
            continue
        if not s or any(ord(c) < 0x20 for c in s):
            continue
        tail = struct.unpack_from('<I', pay, end + 4)[0] if end + 8 <= len(pay) else None
        res.append((k, s, tail))
    return res


def file_records(fs, fend):
    B = fs + PREFIX
    if d[B:B + 6] != b'STCM2L':
        return []
    exp = struct.unpack_from('<I', d, B + 0x20)[0]
    c = d.find(b'CODE_START_', B, fs + exp)
    if c < 0:
        return []
    i, out = c + 24, []
    while i + 4 <= fend:
        bs = struct.unpack_from('<I', d, i)[0]
        if bs == 0 or bs % 4 or i + bs > fend:
            break
        for rec in scan(d[i + 4:i + bs]):
            if rec[0] == 12 or rec[2] in (T_OPT | T_BOX | T_MENU):
                out.append(rec)
        i += bs
    return out


def RESOURCE(s):
    if RE_ASCII.match(s) and '「' not in s:
        return True
    if RE_MACRO_ONLY.match(s):
        return True
    return False


def clean(s):
    """#Name[1] -> 主角名; 框内换行标记 `#n` 删除(合并为一行)。"""
    return s.replace('#Name[1]', HERO_DEFAULT).replace('#n', '')


def collect_names(all_recs):
    """说话人名札自举: 「独立成条 · 短 · 无句读 · 紧邻引号/括注起头」且频次 ≥ NAME_MIN。"""
    c = collections.Counter()
    for fid, recs in all_recs:
        if fid in SKIP_FILES:
            continue
        seq = [(k, s, t) for k, s, t in recs if k == 12 and t in (T_TAIL | {T_NAME})]
        for i, (k, s, t) in enumerate(seq):
            if not s or len(s) > 12:
                continue
            if re.search(r'[。「」『』、]', s):          # 名札不含句读
                continue
            # 含 ？/! 者: 仅「？？？」这类无名说话人占位(整串都是 ？/!)可作名札
            if re.search(r'[？！?]', s) and not re.fullmatch(r'[？?！!]+', s.strip()):
                continue
            if s.endswith(('た', 'だ')):                # 过去式叙述(如 `姉さんが言っていた`)⇒ 非名札
                continue
            # 可用字: 假名/汉字 / 「？？？」占位(仅 ？!) / 全半角拉丁数字(如 `ＭＣ`)
            if not (JP.search(s) or re.fullmatch(r'[？?！!]+', s)
                    or re.fullmatch(r'[Ａ-Ｚａ-ｚ０-９A-Za-z0-9]+', s)):
                continue
            nx = seq[i + 1][1] if i + 1 < len(seq) else None
            if nx and nx[:1] in ('「', '『', '（'):
                c[s.strip()] += 1
    return {s for s, n in c.items() if n >= NAME_MIN} | NAME_EXTRA


def strip_inline(s, names):
    """同行内『名＋引号』(如 `老婆「もしも…`) -> 去掉名字前缀。"""
    for p in ('「', '『'):
        j = s.find(p)
        if 0 < j <= 12 and s[:j].strip() in names:
            return s[j:]
    return s


# ── 后处理 ───────────────────────────────────────────────
def normalize_punct(lines):
    """全/半角括号、半角｢｣ 混用归一(原作笔误; 仅当同现全角时归一)。"""
    out = []
    for s in lines:
        if '（' in s or '）' in s:
            s = s.replace('(', '（').replace(')', '）')
        if '「' in s or '」' in s:
            s = s.replace('｢', '「').replace('｣', '」')
        out.append(s)
    return out


def merge_unclosed(lines):
    """B17「未闭合引号 ⇒ 与次行归并」: 原作把一句台词拆到两个文本框时次框会重开引号
    ⇒ 归并并去掉重开的引号(不造字)。"""
    out, i, n = [], 0, len(lines)
    while i < n:
        cur = lines[i]
        while (cur.count('「') > cur.count('」') or cur.count('（') > cur.count('）')) and i + 1 < n:
            nxt = lines[i + 1]
            if len(cur) + len(nxt) > 140:      # 续写不会这么长 ⇒ 停止归并, 交后续人工表处理
                break
            core = cur.lstrip('「（')
            cand = nxt[1:] if nxt[:1] in ('「', '（') else nxt
            if cand.startswith(core):       # 次行为同句完整版
                cur = nxt
                i += 1
                continue
            if cur.count('「') > cur.count('」') and nxt.startswith('「'):
                nxt = nxt[1:]
            elif cur.count('（') > cur.count('）') and nxt.startswith('（'):
                nxt = nxt[1:]
            cur = cur + nxt
            i += 1
        out.append(cur)
        i += 1
    return out


def dedupe(lines):
    out = []
    for l in lines:
        if out and out[-1] == l:
            continue
        out.append(l)
    return out


def drop_prefix_variants(lines):
    """相邻两行互为真前缀(≥10 字) ⇒ 原作「截断版／完整版」双写, 只留完整版。"""
    out = []
    i = 0
    while i < len(lines):
        a = lines[i]
        b = lines[i + 1] if i + 1 < len(lines) else None
        if b is not None and len(a) >= 10 and len(b) >= 10 and a != b:
            if a.startswith(b):          # b = a 的截断版 -> 丢 b
                out.append(a); i += 2; continue
            if b.startswith(a):          # a = b 的截断版 -> 丢 a
                out.append(b); i += 2; continue
        out.append(a)
        i += 1
    return out


# 原作个别行的引号/括号笔误(全篇仅此数处) —— 逐行定值修(勿正则泛修)
FIXED = {
    'この中には――私の記憶が正しければということだが、コアとそれを擁する広間、それに”ブレイン”がいるだろう」':
        '「この中には――私の記憶が正しければということだが、コアとそれを擁する広間、それに”ブレイン”がいるだろう」',
    'そして証明し続けていかねばならない。誰に受け入れられなくても」':
        '「そして証明し続けていかねばならない。誰に受け入れられなくても」',
    '川の傍まで来たけど――」':
        '「川の傍まで来たけど――」',
    '「なんだよー！　じろじろ見るなよなー！」」':
        '「なんだよー！　じろじろ見るなよなー！」',
    '「わーい！　ナナミと一緒！」リュカ、うらやましいでしょ」':
        '「わーい！　ナナミと一緒！リュカ、うらやましいでしょ」',
    '「こんな時代に他人の手助けをしようなんていうのは変人しかいない「うーん。そうなのかな？」':
        '「こんな時代に他人の手助けをしようなんていうのは変人しかいない」「うーん。そうなのかな？」',
    '（……）」': '（……）',
    '「ナナミ、おいしいってどういう意味ですか？｣':
        '「ナナミ、おいしいってどういう意味ですか？」',
    '（ネムとこんなに近い距離に来るなんていつぶりだろう……)':
        '（ネムとこんなに近い距離に来るなんていつぶりだろう……）',
    '（間違いない――姉さんだ！でも、どうして！？)':
        '（間違いない――姉さんだ！でも、どうして！？）',
}


def main():
    ents = load()
    all_recs = []
    for fid, fs, fend in ents:
        all_recs.append((fid, file_records(fs, fend)))
    NAMES = collect_names(all_recs)
    print('names(%d): %s' % (len(NAMES), sorted(NAMES)), file=sys.stderr)

    lines = []
    skipped = collections.Counter()
    for fid, recs in all_recs:
        if fid in SKIP_FILES:
            continue
        # 前瞻: 下一条「未被排除的正文记录」
        nxtmap = [None] * len(recs)
        nxt = None
        for j in range(len(recs) - 1, -1, -1):
            nxtmap[j] = nxt
            k, s, t = recs[j]
            if k == 12 and not (s in DROP_EXACT or RESOURCE(s) or SYS_RE.match(s)):
                nxt = s
        buf = []
        for j, (k, s, t) in enumerate(recs):
            if k != 12:
                ok = bool(JP.search(s)) and not SYS_RE.match(s)
                if t in T_OPT or t in T_MENU:
                    if ok and s.strip() != 'なし':
                        if buf:
                            lines.append(''.join(buf)); buf = []
                        lines.append(clean(s))
                        skipped['opt'] += 1
                    else:
                        skipped['noise'] += 1
                elif t in T_BOX:
                    if ok and (s[:1] in ('「', '（', '(') or len(s) > 12):
                        if buf:
                            lines.append(''.join(buf)); buf = []
                        lines.append(clean(s))
                    else:
                        skipped['noise'] += 1
                continue
            # k == 12
            if is_plate(s, nxtmap[j], not buf, NAMES):
                if buf:
                    lines.append(''.join(buf)); buf = []
                skipped['name'] += 1
                continue
            if s in DROP_EXACT or RESOURCE(s) or SYS_RE.match(s):
                skipped['noise'] += 1
                if t == 211 and buf:
                    lines.append(''.join(buf)); buf = []
                continue
            buf.append(clean(strip_inline(s, NAMES)))
            if t == 211:
                lines.append(''.join(buf)); buf = []
        if buf:
            lines.append(''.join(buf))

    out = []
    for l in lines:
        l = l.strip()
        if l:
            out.append(l)
    out = dedupe(out)
    out = normalize_punct(out)
    out = drop_prefix_variants(out)
    out = merge_unclosed(out)
    out = [FIXED.get(l, l) for l in out]
    out = dedupe(out)
    print('records=%d lines=%d  opt=%d name=%d noise=%d' % (
        sum(len(r) for _, r in all_recs), len(out),
        skipped['opt'], skipped['name'], skipped['noise']), file=sys.stderr)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('->', OUT, file=sys.stderr)


def is_plate(s, nxt, buf_empty, names):
    if not s or s.strip() not in names:
        return False
    if not buf_empty and not (nxt and nxt[:1] in ('「', '『', '（', '(')):
        return False
    return True


if __name__ == '__main__':
    main()
