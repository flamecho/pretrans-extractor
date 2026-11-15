#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ひぐらしのなく頃に奉＋Origin (NS) main.snr → 全文本

引擎：Entergram SNR（与 うみねこのなく頃に咲 同族）
记录：`<u16 len><cp932 text><0x00>`
  消息串 = `名前@r@v<voice>.本文`；`@k`＝一次点击（换页），`@r`＝框内软换行（合并）
  同页 ≥2 次点击 ⇒ 追加合并行（双版对照）

用法：
  python scripts/hg_extract.py <main.snr> <out.txt>

★ 半角假名 = **平假名语义**（判据：同句内已是全角平假名的「が」与半角假名并存 ⇒
  半角部分必须是平假名，否则「モヤがカッタ」片平混排）；`ﾞ`→`！`、`ﾟ`→`？`、`･`→`…`。
★ 本作有 **data.rom（旧）与 patch.rom（新）两版 main.snr**：patch 是把正文**重新编码成全角**并改写过的版本，
  故以 patch 为准（旧版独有 172 串，抽样 30% 能在 patch 找到原文，其余为旧版クイズ/おまけ，已验不属现行剧本）。
"""
import struct, re, os, sys, collections

HW = str.maketrans({
    '｡': '。', '｢': '「', '｣': '」', '､': '、', '･': '…', 'ｰ': 'ー', 'ｦ': 'を',
    'ｧ': 'ぁ', 'ｨ': 'ぃ', 'ｩ': 'ぅ', 'ｪ': 'ぇ', 'ｫ': 'ぉ', 'ｬ': 'ゃ', 'ｭ': 'ゅ', 'ｮ': 'ょ', 'ｯ': 'っ',
    'ｱ': 'あ', 'ｲ': 'い', 'ｳ': 'う', 'ｴ': 'え', 'ｵ': 'お', 'ｶ': 'か', 'ｷ': 'き', 'ｸ': 'く',
    'ｹ': 'け', 'ｺ': 'こ', 'ｻ': 'さ', 'ｼ': 'し', 'ｽ': 'す', 'ｾ': 'せ', 'ｿ': 'そ', 'ﾀ': 'た',
    'ﾁ': 'ち', 'ﾂ': 'つ', 'ﾃ': 'て', 'ﾄ': 'と', 'ﾅ': 'な', 'ﾆ': 'に', 'ﾇ': 'ぬ', 'ﾈ': 'ね',
    'ﾉ': 'の', 'ﾊ': 'は', 'ﾋ': 'ひ', 'ﾌ': 'ふ', 'ﾍ': 'へ', 'ﾎ': 'ほ', 'ﾏ': 'ま', 'ﾐ': 'み',
    'ﾑ': 'む', 'ﾒ': 'め', 'ﾓ': 'も', 'ﾔ': 'や', 'ﾕ': 'ゆ', 'ﾖ': 'よ', 'ﾗ': 'ら', 'ﾘ': 'り',
    'ﾙ': 'る', 'ﾚ': 'れ', 'ﾛ': 'ろ', 'ﾜ': 'わ', 'ﾝ': 'ん', 'ﾞ': '！', 'ﾟ': '？',
})

RUBY = re.compile(r'@b[^@]*?\.@<([^@]*)@>')
VOICE = re.compile(r'@v[^.]*\.')
RESID = re.compile(r'\|[A-Za-z0-9]{1,10}/[A-Za-z0-9_]{1,24}\.?')
C_PARAM = re.compile(r'@c[\w$]*\.?')
N_PARAM = re.compile(r'@[xsaowz]\d*\.?')
SINGLE = re.compile(r'@[rkyet|<>\[\]/\-]')
PUA = re.compile('[\ue000-\uf8ff]')

# DUAL=True 时额外输出「合并行」（一条记录的各次点击拼回）；本作判据显示 @k＝一次点击＝一屏，
# 合并行不是画面上出现过的文本 ⇒ 默认关闭（原双版可用 --dual 打开）
import os as _os
DUAL = '--dual' in sys.argv
# `--split-voice`：额外按 `@v`（换语音）再拆一次框。默认关——按 `@v` 拆会让 33% 的行引号半开，
# 与半角块（一条记录＝一个框）不符；留作对照用。
SPLIT_VOICE = '--split-voice' in sys.argv

LAB = re.compile(r'(@r)?[０-９Ａ-Ｚａ-ｚ_]+')
RES = re.compile(r'^[A-Z][A-Z0-9_]*@r')


def parse_snr(d):
    N = len(d)
    out = []
    p = 0
    while p < N - 4:
        L = struct.unpack_from('<H', d, p)[0]
        if 4 <= L <= 8000 and p + 2 + L <= N and d[p + 2 + L - 1] == 0:
            try:
                t = d[p + 2:p + 2 + L - 1].decode('cp932')
            except Exception:
                t = None
            if t is not None and not any(ord(c) < 0x20 for c in t) and '\x00' not in t:
                out.append((p, t))
                p += 2 + L
                continue
        p += 1
    return out


def clean(s):
    s = re.sub(r'@k((?:@[A-Za-z][^.]*\.)*)\u3000+', r'@k\1', s)   # 合并改行时去掉续行缩进
    s = re.sub(r'@k\u3000*', '', s)
    s = RUBY.sub(r'\1', s)
    s = VOICE.sub('', s)
    s = RESID.sub('', s)
    s = C_PARAM.sub('', s)
    s = N_PARAM.sub('', s)
    s = SINGLE.sub('', s)
    s = PUA.sub('', s)
    s = s.translate(HW)
    return s.strip('\u3000 ')


def is_resource(t):
    return bool(LAB.fullmatch(t)) or bool(RES.match(t)) or '@rｱｱｱｱ' in t


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    src, outpath = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    recs = parse_snr(d)

    # ---- 正文起点：最后一个「资源名/标签」记录之后，且该记录含 @r/@k/@v ----
    last = -1
    for i, (p, t) in enumerate(recs):
        if is_resource(t):
            last = i
    story = [(p, t) for p, t in recs[last + 1:]
             if ('@r' in t or '@k' in t or '@v' in t)]

    lines = []
    n_chunk = 0
    merged = 0
    n_dbg = 0
    unbal = munbal = 0
    by_k = collections.Counter()
    for p, t in story:
        body = t.split('@r', 1)[1] if '@r' in t else t
        if clean(body).startswith('デバッグ'):
            n_dbg += 1          # 制作メモ（「デバッグ用選択肢＜レＡ＞あり、なしでテキスト相違。」）＝ 不上屏
            continue
        # ★ L0（框＝一次点击）：`@r`＝新框（旁白框也用它）；`@k`/`\uF8F0`＝框内改行（合并）
        #   依据：① 半角块一条记录 = 一个框，其内只用 `@k`/`\uF8F0` 断行（`@r` 只在记录头分隔名字）；
        #   ② 同一场景两块的对照：`｢…詩音ﾞﾞ\uF8F0亡霊…`（半角，同框）⇔ `「…詩音！！@k@x….　亡霊…`（全角）
        #      ⇒ `@k` ≡ `\uF8F0` = 框内改行；而半角块拆成 5 条记录时，全角块用 4 个 `@r` 对齐 ⇒ `@r` = 新框；
        #   ③ 反证：若按 `@v` 拆框，全库 33% 的行会「引号半开」（317,728 行里 103,517 行），
        #      而按 `@r` 拆只剩 457 行（0.2%）⇒ `@v` 不是框边界。
        chunks = [clean(x) for x in body.split('@r')]
        if SPLIT_VOICE:
            chunks = [y for x in chunks for y in (clean(z) for z in re.split(r'(?=@v)', x))]
        chunks = [x for x in chunks if x]
        if not chunks:
            continue
        n_chunk += len(chunks)
        by_k[len(chunks)] += 1
        lines.extend(chunks)
        unbal += sum(1 for c in chunks if c.count('「') != c.count('」'))
        if DUAL and len(chunks) >= 2:
            m = ''.join(chunks)
            lines.append(m)
            merged += 1
            if m.count('「') != m.count('」'):
                munbal += 1

    os.makedirs(os.path.dirname(os.path.abspath(outpath)), exist_ok=True)
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')

    print(f'records={len(recs)} story={len(story)} start={story[0][0]:#x} '
          f'debug_dropped={n_dbg} chunks={n_chunk} merged={merged} rows={len(lines)}')
    print('chunks_per_record ' + ' '.join(f'{k}:{v}' for k, v in sorted(by_k.items())))
    print(f'unbalanced seg_rows={unbal} merged_rows={munbal}')
    print('maxlen', max(len(x) for x in lines))
    for x in lines[:3]:
        print('  |', x[:70])
    print('->', outpath)


if __name__ == '__main__':
    main()
