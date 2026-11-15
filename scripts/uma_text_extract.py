# -*- coding: utf-8 -*-
"""冬園サクリフィス (NS-JP) 全文本提取

容器: StreamingAssets/uma_talk_2.bytes
      16B 头(UTXT | ver | 0x37DB21 | data_off) | 头部块表 | 字符码流

码表: chartable.bin(TextAsset) 的原始文本 T（`\\r\\n` 占位，不剔除）
  - 1 字节 token t(0x01-0x7F) -> T[t-1]
  - 2 字节 token (lead>=0x80) -> T[(trail + 128*(lead-0x81)) + 127]
  - 0x00 -> 句读断点；0x05 '$' 词条壳；0x06 '%' 主人公名

⚠ 头部 `d[16:data_off]`（19,291 B，`head[3:]` 每字节 1..129）**不是框边界**，是引擎分块长度：
  按它切段末只有 23% 落在句读上，且大量段在词中间断（`エ|リアス`、`ページ|を`）。
  本作按下列规则成行。

成行（L0/L1）
  L0  0x00 断行（源数据在句读后断，故不会切在词中）
  L1a 」后接 「        ⇒ 断（说话人切换；零 token 相邻 7,407 处）
  L1b 」』】）后接非引用助词 ⇒ 断（台词/心声转旁白）；引用助词集 `と、。！？」』）`
  L1c 。！？ 后接 「『【（  ⇒ 断（旁白转台词/心声）
  L1d 长行兜底：无引号且 >60 字 ⇒ 按 。！？ 切（只在括号/引号深度 0 处切）
  L1e 相邻逐字重复行 ⇒ 删第二份（双版重排）
"""
import sys, os, struct, argparse, statistics, re

SRC = r'<本地路径>'
CHARTABLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_w_wgs', 'chartable.bin')
HERO = 'レティシア'
KEEP_AFTER_CLOSE = set('と、。！？」』）')
LONG_LIMIT = 60


def load_table(p):
    return list(open(p, 'rb').read().decode('utf-8'))


def to_stream(path, T):
    d = open(path, 'rb').read()
    off = struct.unpack_from('<I', d, 12)[0]
    blob = d[off:]
    out = []
    i, n = 0, len(blob)
    while i < n:
        b = blob[i]
        if b >= 0x80 and i + 1 < n:
            t = (b << 8) | blob[i + 1]
            i += 2
            code = (t & 0xFF) + 128 * ((t >> 8) - 0x81)
            j = code + 127
            if 0 <= j < len(T):
                out.append(T[j])
        else:
            i += 1
            if b == 0:
                out.append('\x00')
            elif b == 0x05:
                continue
            elif b == 0x06:
                out.append(HERO)
            else:
                j = b - 1
                if 0 <= j < len(T):
                    out.append(T[j])
    return ''.join(out)


def split_by_quotes(seg):
    out = []
    buf = []
    i, L = 0, len(seg)
    while i < L:
        c = seg[i]
        buf.append(c)
        i += 1
        nx = seg[i] if i < L else ''
        cut = False
        if c in '」』】）':
            if nx == '' or nx not in KEEP_AFTER_CLOSE:
                cut = True
        elif c in '。！？':
            if nx in '「『【（':
                cut = True
        if cut:
            out.append(''.join(buf))
            buf = []
    if buf:
        out.append(''.join(buf))
    return out


def split_long(lines, limit=LONG_LIMIT):
    out = []
    for l in lines:
        if len(l) <= limit:
            out.append(l)
            continue
        cuts = []
        depth = 0
        for i, c in enumerate(l):
            if c in '「『【（':
                depth += 1
            elif c in '」』】）':
                depth = max(0, depth - 1)
            elif c in '。！？' and depth == 0 and i + 1 < len(l):
                cuts.append(i + 1)
        if not cuts:
            out.append(l)
            continue
        buf = ''
        start = 0
        for k in cuts + [len(l)]:
            sent = l[start:k]
            start = k
            if not sent:
                continue
            if buf and len(buf) + len(sent) > limit:
                out.append(buf)
                buf = sent
            else:
                buf += sent
        if buf:
            out.append(buf)
    return out


NO_HEAD = set('ぁぃぅぇぉゃゅょゎァィゥェォャュョヮー')
NO_LINE_HEAD = set('、。，．・：；？！）〕］｝〉》」』】ー…―')


def build(path, T):
    s = to_stream(path, T)
    # 0x00 是「断点」，但既有框边界也有框内换行：
    #   前一段若未以句末/收尾符号结束（`、`/`…`/汉字等）⇒ 是框内换行，续行合并。
    parts = [x.strip('\r\n') for x in s.split('\x00')]
    parts = [x for x in parts if x.strip()]
    raw = []
    for x in parts:
        if raw and not raw[-1].endswith(('。', '！', '？', '」', '』', '）')):
            raw[-1] += x
        else:
            raw.append(x)
    # 防止极端累积（无句号的连续段）
    tmp = []
    for x in raw:
        while len(x) > 160:
            tmp.append(x[:160]); x = x[160:]
        if x.strip(): tmp.append(x)
    raw = tmp
    # L0：0x00 段即一行（源数据在句读后断，中位 31 字、不会切在词中）
    #    仅对超长段（>60 字）再按引号/句末细分，避免"74 字一行"
    merged = []
    for x in raw:
        if len(x) > LONG_LIMIT:
            merged.extend(split_by_quotes(x))
        elif '」「' in x:
            # 同框多句台词（说话人切换，零 token 相邻）⇒ 必断，即使段很短
            segs = x.split('」「')
            for k, y in enumerate(segs):
                if k == 0:
                    merged.append(y + '」')
                elif k == len(segs) - 1:
                    merged.append('「' + y)
                else:
                    merged.append('「' + y + '」')
        else:
            merged.append(x)
    merged = [x.rstrip() for x in merged if x.strip()]
    # 跨行引号：本行 「 未闭合 ⇒ 并回；下一行以 「 开头时不并（那是新台词）
    fixed = []
    for l in merged:
        if fixed and fixed[-1].count('「') > fixed[-1].count('」') and not l.startswith('「'):
            cand = fixed[-1] + l
            if len(cand) <= 100 and cand.count('「') >= cand.count('」'):
                fixed[-1] = cand
                continue
        fixed.append(l)
    fixed = split_long(fixed)
    # 词首/行首禁则：下一行以小假名或不能行首的标点开头 ⇒ 从上一行末尾逐字移过来
    for i in range(len(fixed) - 1, 0, -1):
        nxt, prev = fixed[i], fixed[i - 1]
        moved = 0
        while nxt and nxt[0] in (NO_HEAD | NO_LINE_HEAD) and prev and moved < 4:
            prev, nxt = prev[:-1], prev[-1] + nxt
            moved += 1
        fixed[i - 1], fixed[i] = prev, nxt
    # 孤立单字符行并入上一行
    for i in range(len(fixed) - 1, 0, -1):
        if fixed[i] and len(fixed[i]) <= 1 and fixed[i - 1]:
            fixed[i - 1] += fixed[i]
            fixed[i] = ''
    fixed = [x for x in fixed if x.strip()]
    ded = []
    for l in fixed:
        if ded and ded[-1] == l:
            continue
        ded.append(l)
    return ded, len(fixed) - len(ded)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--chartable', default=CHARTABLE)
    a = ap.parse_args()
    T = load_table(a.chartable)
    lines, dup = build(os.path.join(SRC, 'uma_talk_2.bytes'), T)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as w:
        for l in lines:
            w.write(l + '\n')
    L = [len(x) for x in lines]
    print('行 %d（双版去重 %d）/ 中位 %d / 均值 %.1f / 最长 %d' %
          (len(lines), dup, statistics.median(L), sum(L) / len(L), max(L)), file=sys.stderr)


if __name__ == '__main__':
    main()
