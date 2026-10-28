#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
SA7 - Silent Ability Seven - (PSV / PCSG00640 / プチレーヴ) 全文本提取器

引擎：自研「テキスト方式」ADV（脚本 = UTF-16LE 行式文本 ＋ data/*.txt 指令表）
链路：pkg2zip -x → psvpfsparser(zRIF=work.bin[0x50:0x60]) → cmp.psarc
      → script/scriptN.txt（1 行 = 1 步＝1 次点击）
      → eboot.bin → ELF 的用語辞典（UTF-16LE 见出語/解説 对）

行语义：
  · 名札 = `姓<U+3000>名` 或「独立短行 + 其后为「台词」」→ 整行丢弃
  · 选项 = ≥2 连续裸行（非名札）→ 一行一条
  · 効果音/演出キュー（se.txt 登记名 + 音/足音/動作说明）→ 丢弃
  · `\` = 框内软换行 → 合并；`#` = 主人公名变量分隔符 → 去

用法：
  python sa7_extract.py --scripts <cmp解包目录> --out <成品.txt>
  python sa7_extract.py --elf <eboot.elf> --dict-only <辞典.txt>
  python sa7_extract.py --scripts <cmp> --elf <elf> --out <成品> --audit
"""
import os, re, sys, argparse, collections

PUNCT = set('。、！？…「」『』（）()～―♪–—')

# data 表未登记的演出/系统指令
EFFECTS = set('''横揺れ 縦揺れ 縦横 回転 フェード短 フェード長 白フェードイン 瞬時切り替え
フラッシュ2回 引き戸開閉手動 場面転換 場面転換遠背景 場面転換長 場面転換近遠 住宅地夕
BG ALL CHARA ALBUM2 NEXT SA7ロゴ 菱型中心から円状 スチルスタート黒 そよ風 端末'''.split())
EFFECT_RE = re.compile(r'^x[^。、「」『』（）]{1,14}$')
CUE_RE = re.compile(r'(革靴|ブーツ|スリッパ|足音|衣擦れ)')
# 手工判定的演出キュー（非 se.txt 登记、亦非台词）
CUE_EXTRA = set('''ナイフで浅い傷を負う チップを落とす チップを手に取る 銃でチップを狙う
麻衣走り出す 麻衣走り去る 歩き激しい木材裸足一人'''.split())
# 手工判定的「形似名札实为正文」行
TEXT_EXTRA = set(['誰も選ばない', '押し入れが怪しいね', '父より', 'あやか#へ',
                  '手紙', '・\\・\\・'])


def rd(p):
    return open(p, 'rb').read().decode('utf-16-le', 'replace')


def load_tables(root):
    cmds = set()

    def add(f, cols):
        p = os.path.join(root, 'data', f)
        if not os.path.exists(p):
            return
        for l in rd(p).replace('\r', '').split('\n'):
            if not l:
                continue
            parts = l.split(',')
            for c in cols:
                if len(parts) > c and parts[c].strip():
                    cmds.add(parts[c])
    add('se.txt', [0]); add('bg.txt', [0]); add('bgm.txt', [0])
    add('change.txt', [0, 1]); add('chara.txt', [3, 5])
    rows = []
    for l in rd(os.path.join(root, 'data', 'scrlst.txt')).replace('\r', '').split('\n'):
        if not l:
            continue
        p = l.split(',')
        rows.append(p); cmds.add(p[0])
    return cmds, rows


def has_punct(l):
    return any(c in PUNCT for c in l)


def is_cmd(l, cmds):
    return (l in cmds or l in EFFECTS or bool(EFFECT_RE.match(l))
            or bool(re.fullmatch(r'\d+', l)))


def is_cue(l):
    if l in CUE_EXTRA:
        return True
    if has_punct(l):
        return False
    return l.endswith('音') or bool(CUE_RE.search(l))


def clean(t):
    return t.replace('\\', '').replace('#', '')


def load_scripts(root):
    cmds, rows = load_tables(root)
    files = []
    for row in rows:
        if len(row) < 4 or not row[1] or row[1] in ('script', 'script0'):
            continue
        p = os.path.join(root, 'script', row[1] + '.txt')
        if os.path.exists(p):
            files.append((row, rd(p).split('\n')))
    return cmds, files


def classify_file(lines, cmds, names):
    kinds = []
    for l in lines:
        if not l.strip():
            kinds.append('blank')
        elif is_cmd(l, cmds) or is_cue(l):
            kinds.append('cmd')
        elif l in names or re.fullmatch(r'[?？]+', l):
            kinds.append('name')
        elif len(l) <= 24 and not has_punct(l):
            kinds.append('bare')
        else:
            kinds.append('text')
    return kinds


def detect_names(cmds, files):
    """名札 = 姓<U+3000>名；或「独立裸行 + 其后首个正文行以「开头」"""
    names = set()
    for _, lines in files:
        for l in lines:
            if '\u3000' in l and not has_punct(l) and len(l) <= 16 and l.strip():
                names.add(l)
    for _ in range(3):
        add = set()
        for _, lines in files:
            kinds = classify_file(lines, cmds, names)
            i, n = 0, len(lines)
            while i < n:
                if kinds[i] != 'bare':
                    i += 1
                    continue
                j = i
                while j < n and kinds[j] == 'bare':
                    j += 1
                if j - i == 1:
                    k = j
                    while k < n and kinds[k] in ('cmd', 'blank'):
                        k += 1
                    if k < n and lines[k].startswith('「') and lines[i] not in TEXT_EXTRA:
                        add.add(lines[i])
                i = j
        if add <= names:
            break
        names |= add
    return names


def build_text(root, audit=False):
    cmds, files = load_scripts(root)
    names = detect_names(cmds, files)
    out = []
    stats = collections.Counter()
    aud = collections.defaultdict(collections.Counter)
    valid = []
    for row, lines in files:
        kinds = classify_file(lines, cmds, names)
        i, n = 0, len(lines)
        while i < n:
            if kinds[i] != 'bare':
                i += 1
                continue
            j = i
            while j < n and kinds[j] == 'bare':
                j += 1
            if j - i >= 2:
                for r in range(i, j):
                    kinds[r] = 'option'
            i = j
        clicks = 0
        for i, l in enumerate(lines):
            k = kinds[i]
            if k in ('option', 'bare', 'text'):
                t = clean(l)
                if t.strip():
                    out.append(t)
                    stats['text'] += 1
                    clicks += 1
                    aud[k][l] += 1
            elif k == 'name':
                stats['name'] += 1; aud['name'][l] += 1
            elif k == 'cmd':
                stats['cmd'] += 1
        valid.append((row[0], int(row[3]) - int(row[2]), clicks))
    return out, stats, aud, names, valid


# ---------------- 用語辞典（eboot ELF） ----------------
DICT_EXTRA = {0x2026, 0x2015, 0x2018, 0x2019, 0x201c, 0x201d, 0x301c, 0x3005,
              0x25cb, 0x25cf, 0x266a, 0x2665, 0x2192, 0x2190, 0x3003, 0x3010,
              0x3011, 0x203b, 0x00d7, 0x00b1} | set(range(0x2460, 0x2474))
DICT_CATS = {'キャラクター', 'キーワード', '組織', 'スポット', '能力', '秘密道具'}


def _ok(cp):
    return ((0x20 <= cp < 0x7f) or (0x3000 <= cp <= 0x30ff)
            or (0x4e00 <= cp <= 0x9fff) or (0xff00 <= cp <= 0xffef)
            or cp in DICT_EXTRA)


def extract_dict(elf_path):
    d = open(elf_path, 'rb').read()
    start = d.find('結城あやか'.encode('utf-16-le'))
    if start < 0:
        return []
    i, n, strs = start, len(d), []
    gap = 0
    while i < n - 1:
        cp = d[i] | (d[i + 1] << 8)
        if cp and _ok(cp):
            j, s = i, []
            while j < n - 1:
                c = d[j] | (d[j + 1] << 8)
                if c == 0:
                    break
                if not _ok(c):
                    s = []
                    break
                s.append(chr(c)); j += 2
            if s:
                strs.append(''.join(s)); i = j + 2; gap = 0
                continue
        i += 2; gap += 2
        if gap > 400:
            break
    # 截到分类名之前
    cut = len(strs)
    for k, s in enumerate(strs):
        if s in DICT_CATS:
            cut = k
            break
    strs = [s for s in strs[:cut] if s not in DICT_CATS]
    if len(strs) % 2:
        strs = strs[:-1]
    out = []
    for k in range(0, len(strs), 2):
        head, body = strs[k].strip(), strs[k + 1].strip()
        body = body.replace('\\', '')
        out.append('【%s】%s' % (head, body))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scripts')
    ap.add_argument('--elf')
    ap.add_argument('--out')
    ap.add_argument('--dict-only')
    ap.add_argument('--audit', action='store_true')
    a = ap.parse_args()

    if a.dict_only:
        rows = extract_dict(a.elf)
        with open(a.dict_only, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(rows) + '\n')
        print('dict entries =', len(rows))
        return

    lines, stats, aud, names, valid = build_text(a.scripts, a.audit)
    dict_rows = extract_dict(a.elf) if a.elf else []
    all_lines = lines + dict_rows
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(all_lines) + '\n')
    print('body=%d dict=%d total=%d %s -> %s'
          % (len(lines), len(dict_rows), len(all_lines), dict(stats), a.out))
    exact = sum(1 for _, e, c in valid if e == c)
    print('scrlst 步数校验：%d/%d 精确，合计 %d/%d (%+.2f%%)'
          % (exact, len(valid), sum(c for _, _, c in valid),
             sum(e for _, e, _ in valid),
             100.0 * (sum(c for _, _, c in valid) / max(1, sum(e for _, e, _ in valid)) - 1)))
    if a.audit:
        print('\nnames(%d): %s' % (len(names), sorted(names)))
        for k in ('option', 'bare', 'text', 'name'):
            print('\n=== %s (%d) ===' % (k, len(aud[k])))
            for s, v in aud[k].most_common(400):
                print(v, repr(s))


if __name__ == '__main__':
    main()
