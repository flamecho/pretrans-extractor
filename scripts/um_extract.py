#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""うみねこのなく頃に咲 (NS) main.snr → 全文本
引擎：Entergram SNR（cp932 半角仮名スクリプト）
记录：<u16 len><cp932 text><0x00>
  消息串 = `名前@r@v<voice>.<本文>`，`@k`＝一次点击（换页），`@r`＝框内软换行（合并）
  用語辞典 = `@b<よみ>.@<見出し>@>` ＋ 次串（解説），区间 0x52000–0x90000
"""
import struct, re, os, sys

SRC = '_w_um/rom/main.snr'
OUT = '提取结果/[NS-JP]うみねこのなく頃に咲 ～猫箱と夢想の交響曲～.txt'
STORY_MIN = 0x92000
TIPS_LO, TIPS_HI = 0x52000, 0x90000

HW = {}
for i, c in enumerate('ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ'):
    pass
# 半角假名 → **平假名**（本作大文字半角假名＝平仮名语义；外来语与强调词原文写的是全角片假名，
# 不在本表内，故不受影响）。2026-10-24 修正：原先一律映射成全角片假名，
# 导致「聴診器ヲ外シナがラ」这类本该是平假名的句子整句变片假名。
_PAIRS = ('｡。｢「｣」､、･…ｰーｦをｧぁｨぃｩぅｪぇｫぉｬゃｭゅｮょｯっ'
          'ｱあｲいｳうｴえｵおｶかｷきｸくｹけｺこｻさｼしｽすｾせｿそﾀたﾁちﾂつﾃてﾄと'
          'ﾅなﾆにﾇぬﾈねﾉのﾊはﾋひﾌふﾍへﾎほﾏまﾐみﾑむﾒめﾓもﾔやﾕゆﾖよ'
          'ﾗらﾘりﾙるﾚれﾛろﾜわﾝん')
for i in range(0, len(_PAIRS), 2):
    HW[_PAIRS[i]] = _PAIRS[i + 1]
HW['ﾞ'] = '！'
HW['ﾟ'] = '？'
# 「･」→「…」：本作中点全部用于省略号（实测 18 万余处，无一处作词间分隔），
# 游戏字体中即省略号；连续「・・・・」＝「…………」。用户实机核对（2026-10-24）。


def to_full(s):
    return ''.join(HW.get(c, c) for c in s)


RUBY = re.compile(r'@b([^.]*)\.@<([^@]*)@>?')
TAG_DOT = re.compile(r'@[aczeoswagt]\d*\.')
# 立绘/表情资源码残留：`|42/RG5_00010|43/RG6_00020ルシ姉が…` / `|13/10400165.「「` / `|27/20700134_1.…`
# ★资源名**必须限定 ASCII**（[A-Za-z0-9_]）—— 早一版用 [^\s|「」『』]{1,24} 贪婪吃掉了后面的日文正文
#   （`RG6_00020ルシ姉が悪いでーすッ！！` 整段被删，用户指出"删多了"）。
RESID = re.compile(r'\|[A-Za-z0-9]{1,10}/[A-Za-z0-9_]{1,24}\.?')
VOICE = re.compile(r'@v\d+/[A-Za-z0-9_]+\.?')
SPAN = re.compile(r'@\[(.*?)@\]', re.S)
PUA = re.compile('[\ue000-\uf8ff]')


def clean_seg(s):
    s = RUBY.sub(lambda m: m.group(2), s)
    s = VOICE.sub('', s)
    s = TAG_DOT.sub('', s)
    s = RESID.sub('', s)
    s = SPAN.sub(lambda m: m.group(1), s)
    for t in ('@r', '@k', '@y', '@|', '@e', '@<', '@>', '@t', '@b', '@c'):
        s = s.replace(t, '')
    s = s.replace('@\u3000', '')
    s = PUA.sub('', s)
    s = s.replace('\x00', '')
    s = to_full(s)
    return s.strip()


def parse(d, N):
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


def main():
    d = open(SRC, 'rb').read()
    N = len(d)
    strs = parse(d, N)
    story = [(p, t) for p, t in strs if p >= STORY_MIN
             and ('@k' in t or '@v' in t or t.startswith('@r'))
             and 'vvtest' not in t]
    tips = [(p, t) for p, t in strs if TIPS_LO <= p < TIPS_HI]

    lines = []
    nmerge = 0
    for p, t in story:
        body = t
        if '@r' in body:
            body = body.split('@r', 1)[1]
        segs = [clean_seg(x) for x in body.split('@k')]
        segs = [x for x in segs if x]
        if not segs:
            continue
        lines.extend(segs)
        if len(segs) >= 2:          # 一页 ≥2 次点击 ⇒ 追加合并行
            lines.append(''.join(segs))
            nmerge += 1

    gl = []
    i = 0
    while i < len(tips) - 1:
        nm, ds = tips[i][1], tips[i + 1][1]
        if nm.startswith('@b') and '.@<' in nm and len(ds) > 10:
            headline = clean_seg(nm)
            desc = clean_seg(ds)
            if headline and desc:
                gl.append('【%s】%s' % (headline, desc))
                i += 2
                continue
        i += 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines + gl) + '\n')
    print('story strings', len(story), 'lines', len(lines), 'merged', nmerge)
    print('tips', len(gl))
    print('maxlen', max(len(x) for x in lines))
    for x in lines[:3]:
        print('  |', x[:70])
    for x in gl[:2]:
        print('  #', x[:70])


if __name__ == '__main__':
    main()
