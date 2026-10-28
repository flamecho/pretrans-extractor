#!/usr/bin/env python3
"""カヌチ 二つの翼 (PSP / Idea Factory 'YDP1' -> SCRIPT_LSB) 剧本文本提取

记录形态 (LSB 字节码内嵌 NUL 结尾 cp932 串):
    [头][名札\\0][正文\\0]   名札与正文零间隔
    [头][正文\\0]            无名札
正文控制: 5C='\\' 框内换行(合并) ; 5C5C='\\\\' 翻页(新行)
名字宏(单字节): 26='&'->アキ 25='%'->ミヤズ 40='@'->カヤナ 24='$'->アキ(真名)
用语标记: 23='#'...'#' 成对, 去除外壳
"""
import os, re, sys, json

NAME_MACRO = {'&': 'アキ', '%': 'ミヤズ', '@': 'カヤナ', '$': 'アキ'}
BAD_NAME = set('\\。！？、…‥「」『』（）()#\n：；〜～　 0123456789!')
JP_PUNCT = '…‥、。！？「」『』（）〜～・：；―—‐－※♪★☆　'
ASCII_OK = set('0123456789 &@#%$\\.,!?-~:;()/\"')

STR = re.compile(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]|[ -~])+\x00')


def is_jp(c):
    return ('\u3041' <= c <= '\u309f') or ('\u30a1' <= c <= '\u30fa') or ('\u4e00' <= c <= '\u9fff')


def kana_kanji(t):
    return sum(1 for c in t if is_jp(c))


def char_ok(c):
    o = ord(c)
    if 0x3041 <= o <= 0x309f or 0x30a0 <= o <= 0x30ff:
        return True
    if 0x4e00 <= o <= 0x9fff or o in (0x3005, 0x3006, 0x3007, 0x303b):
        return True
    if 0x3000 <= o <= 0x303f:      # 、。「」『』〜・
        return True
    if 0xff00 <= o <= 0xffef:      # 全角
        return True
    if o in (0x2026, 0x2015, 0x2014, 0x2018, 0x2019, 0x201c, 0x201d, 0x203b, 0x25cb, 0x25cf):
        return True
    return c in ASCII_OK


def valid(t):
    """是否可能是正文/名札串（拒绝字节码被误读出来的假串）"""
    if not t or len(t) > 500:
        return False
    for c in t:
        if ord(c) < 32:
            return False
        if not char_ok(c):
            return False
    if len(t) == 1:
        return False
    if t[0] in '、。，．）」』】！？：；':
        return False
    if t[0] in '（(' and t[-1] in '&@%$#':
        return False
    jp = kana_kanji(t)
    asc = sum(1 for c in t if 32 <= ord(c) < 127)
    if jp == 0:
        # 纯标点/宏（……、——、@……&っ！！）也算正文
        return (len(t) >= 2 and all(c in JP_PUNCT or c in '&@%$#' for c in t)
                and any(c in JP_PUNCT for c in t))
    if len(t) <= 2 and asc:
        return False
    if asc >= 2 and jp <= 2:
        return False
    return True


def strings(b):
    out = []
    for m in STR.finditer(b):
        try:
            t = m.group()[:-1].decode('cp932')
        except UnicodeDecodeError:
            continue
        if valid(t):
            out.append((m.start(), m.end(), t))
    return out


HIRA_END = set('いくすよかてるなわねのどばらりけせめろぶぐず')


def is_name(t, nxt):
    if len(t) > 12 or (set(t) & BAD_NAME) or kana_kanji(t) < 1:
        return False
    # 以平假名动词/助动词结尾的多半是选项句，不是名札
    if len(t) >= 4 and t[-1] in HIRA_END:
        return False
    return True


def transform(t):
    if '#' in t:
        t = re.sub(r'#([^#]*)#', r'\1', t).replace('#', '')
    out = []
    for page in t.split('\\\\'):
        s = page.replace('\\', '')
        for k, v in NAME_MACRO.items():
            s = s.replace(k, v)
        s = s.strip()
        if s:
            out.append(s)
    return out


CHOICE = re.compile(rb'\xfd\xff\xff\xff')


def choice_offsets(b):
    """选项块: fd ff ff ff + 8B 头 + 连续 N 个 NUL 结尾选项串"""
    out = set()
    for m in CHOICE.finditer(b):
        q = m.end() + 8
        while q < len(b):
            e = b.find(b'\x00', q)
            if e <= q:
                break
            try:
                t = b[q:e].decode('cp932')
            except UnicodeDecodeError:
                break
            if not valid(t):
                break
            out.add(q)
            q = e + 1
    return out


def main():
    src, out_txt = sys.argv[1], sys.argv[2]
    files = sorted(os.listdir(src), key=lambda n: (int(re.search(r'EV(\d+)', n).group(1)), n)
                   if re.search(r'EV(\d+)', n) else (0, n))
    lines, names, where = [], {}, []
    stat = dict(files=0, strings=0, names=0, pages=0)
    for fn in files:
        b = open(os.path.join(src, fn), 'rb').read()
        ss = strings(b)
        ch = choice_offsets(b)
        stat['files'] += 1
        stat['strings'] += len(ss)
        i = 0
        while i < len(ss):
            st, en, t = ss[i]
            if t == 'タイトル無し':
                i += 1
                continue
            nxt = ss[i + 1] if i + 1 < len(ss) else None
            empty_box = (b[en:en + 2] == b'\x64\x00' and len(t) <= 8
                         and not any('\u3041' <= c <= '\u309f' for c in t)
                         and not all('\u4e00' <= c <= '\u9fff' for c in t))  # 名札直后即窗口头
            if st not in ch and ((nxt and nxt[0] == en and is_name(t, nxt[2]))
                                 or (empty_box and is_name(t, ''))):
                names[t] = names.get(t, 0) + 1
                stat['names'] += 1
                i += 1
                continue
            for s in transform(t):
                lines.append(s)
                where.append('%s\t%x\t%s' % (fn, st, s))
                stat['pages'] += 1
            i += 1
    # 残留名札（名札与正文间夹了其它指令）按名札表剔除
    keep = [i for i, l in enumerate(lines) if l not in names]
    lines = [lines[i] for i in keep]
    where = [where[i] for i in keep]
    with open(out_txt, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print(json.dumps(stat, ensure_ascii=False), 'lines', len(lines))
    with open(out_txt + '.where.txt', 'w', encoding='utf-8') as w:
        w.write('\n'.join(where) + '\n')
    with open(out_txt + '.names.txt', 'w', encoding='utf-8') as w:
        for k, v in sorted(names.items(), key=lambda x: -x[1]):
            w.write('%s\t%d\n' % (k, v))


if __name__ == '__main__':
    main()
