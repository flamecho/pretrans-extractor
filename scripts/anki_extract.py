# -*- coding: utf-8 -*-
"""アンジェリーク 魔恋の六騎士 (PSP, ULJM05986, Otomate 2011-11-17, vndb v8799)
STCM2L（Oct  7 2010 17:55:27 构建）剧本正文＋选项提取

容器链：CHD v5 → ISO(ULJM05986) → USRDIR/UNION.CPK（CPK v7，无 TOC，条目名＝纯数字 ID）
        → CRILAYLA 解压 → STCM2L 脚本 406 个（id 03000〜03639）→ _work_anki/script/*.bin
        （INSDIR/UNION.DNS＝同内容 PGD 加密副本；STREAM.CPK＝HCA 语音；MOVIE.CPK＝视频）

记录结构：
  unit = [u32 size][payload]；一次点击 = 一个 unit
  payload = 48B 头（4×(ptr,color,color)）+ 文本记录链 [0][L/4][1][L][cp932][pad]
  记录链首条若为名札（≤12 字・无句读・下一条以 「/（/『 起头）⇒ 丢弃
  选项  = `SEL_nnn` 组标记 + 逐条选项文本，末端 `select`；
          取「自首个 SEL_ 到 select 之间全部选项 unit」（SEL_ 标记跳过）

口径：不加说话人前缀 / 一次点击一行（框内软换行合并）/ #Name[1]→テレサ（主角可改名）
排除：名札辞書（每档 49 条裸名）/ 処理開始 / 符号表（色変化判定・場所１…）

用法: python scripts/anki_extract.py <script_dir> <out.txt>
"""
import struct, re, glob, os, sys, collections

HERO = 'テレサ'          # 主角（vndb v8799, Nameable；默认名 テレサ）
RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_TAG = re.compile(r'#Color\[[^\]]*\]|#Scale\[[^\]]*\]')
RE_PUA = re.compile('[\ue000-\uf8ff]')
RE_LABEL = re.compile(r'^[0-9A-Za-z_]+$')
RE_SEL = re.compile(r'^SEL_[0-9A-Za-z]+$')
BARE_STOP = re.compile(r'[。、！？」』）…‥]')
DEBUG = ('処理開始', 'クリアフラグ', '色変化判定', '再生ＢＧＭ')


def units(b):
    if b[:6] != b'STCM2L':
        return []
    exp = struct.unpack_from('<I', b, 0x20)[0]
    ci = b.find(b'CODE_START_')
    if ci < 0:
        return []
    i, out = ci + 24, []
    while i + 4 <= exp:
        s = struct.unpack_from('<I', b, i)[0]
        if s < 4 or i + s > len(b):
            break
        out.append(b[i + 4:i + s])
        i += s
    return out


def records(p):
    """链式取文本记录；失步则 4 字节前移重同步"""
    out, n, k = [], len(p), 0
    while k + 16 <= n:
        f0, f1, f2, f3 = struct.unpack_from('<4I', p, k)
        if f0 == 0 and f2 == 1 and 4 <= f3 <= 0x8000 and f3 % 4 == 0 and f1 == f3 // 4 and k + 16 + f3 <= n:
            raw = p[k + 16:k + 16 + f3].rstrip(b'\x00')
            try:
                s = raw.decode('cp932')
            except Exception:
                s = None
            if s is not None:
                out.append((k, s))
                k += 16 + f3
                continue
        k += 4
    return out


def looks_name(s, nxt):
    """名札判定：≤12 字・无句读・下一条以 「/（/『 起头
    ★ 允许名札误带一个句号（实测 1 处 `ジョヴァンニ。「…`，03142）"""
    if not s:
        return False
    s2 = s[:-1] if s.endswith('。') else s
    if not s2 or len(s2) > 12 or BARE_STOP.search(s2):
        return False
    return bool(nxt) and nxt[0] in '「（『'


def clean(s):
    s = s.replace('\r', '').replace('\n', '')
    s = RE_PUA.sub('', s)
    s = RE_TAG.sub('', s)
    s = s.replace('#Name[1]', HERO)
    return s.strip()


def is_bare_name(s):
    return (len(s) <= 12 and not BARE_STOP.search(s)
            and '「' not in s and '（' not in s and '『' not in s and bool(RE_JP.search(s)))


def option_map(us):
    """-> {unit_index: option_text}：select 之前、跨 SEL_ 标记的连续选项 unit"""
    out = {}
    for i, p in enumerate(us):
        recs = records(p)
        if not any(s.strip() == 'select' for k, s in recs):
            continue
        j, skip = i - 1, 0
        while j >= 0 and skip < 4:
            rr = records(us[j])
            if not rr:
                j -= 1
                skip += 1
                continue
            if len(rr) == 1 and RE_SEL.match(rr[0][1]):
                j -= 1
                skip = 0
                continue
            if len(rr) == 1 and rr[0][0] >= 24 and RE_JP.search(rr[0][1]) and len(rr[0][1]) <= 40 \
                    and not RE_LABEL.match(rr[0][1]):
                out[j] = clean(rr[0][1])
                j -= 1
                skip = 0
                continue
            break
    return out


def extract(sdir, out_path):
    files = sorted(glob.glob(os.path.join(sdir, '*.bin')))
    tags = collections.Counter()
    for path in files:
        for p in units(open(path, 'rb').read()):
            r = records(p)
            if len(r) >= 2 and looks_name(r[0][1], r[1][1]):
                tags[r[0][1]] += 1

    lines, dropped = [], collections.Counter()
    for path in files:
        b = open(path, 'rb').read()
        us = units(b)
        opts = option_map(us)
        prev = None
        for idx, p in enumerate(us):
            recs = records(p)
            if not recs:
                continue
            if idx in opts:
                line = opts[idx]
            else:
                txts = [s for k, s in recs]
                if len(txts) >= 2 and looks_name(txts[0], txts[1]):
                    txts = txts[1:]
                line = clean(''.join(txts))
                if not line:
                    continue
                line = re.sub(r'^([？\?]{2,})(?=[「（『])', '', line)
                m0 = re.match(r'^([^\s「（『]{1,12})(?=[「（『])', line)
                if m0 and m0.group(1) in tags:
                    line = line[m0.end():]
            if not line or not RE_JP.search(line) or RE_LABEL.match(line):
                dropped['label'] += 1
                continue
            if line.startswith(DEBUG):
                dropped['debug'] += 1
                continue
            if idx not in opts and is_bare_name(line):
                dropped['bare'] += 1
                continue
            if line == prev:
                dropped['dup'] += 1
                continue
            lines.append(line)
            prev = line
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('lines=%d dropped=%s tags=%d' % (len(lines), dict(dropped), len(tags)))
    return lines


if __name__ == '__main__':
    extract(sys.argv[1], sys.argv[2])
