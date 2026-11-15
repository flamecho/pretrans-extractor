# -*- coding: utf-8 -*-
"""神足町人妖譚 (PC-JP / System-NNN「NNNLib」engine) 全文本提取 · 定稿（对齐槽版）

源：<游戏 dump 目录>/[PC-JP]神足町人妖譚 ~迷イ子ノ章~.rar (RAR5, 密码 otoame)
    → app/spt/*.spt = 剧本字节码 / app/spt/*.xtx = 纯 cp932 配置

★★ .spt 格式（与 あさき、ゆめみし 同引擎 System-NNN，格式一致）
  * 整文件【逐字节 XOR 0xFF】→ 0x30 "SPTHEADER0"，0x00 u32 = 0x20
  * 字符串池记录 = [data][NUL][垃圾填充至 4 字节边界] ⇒ 每条串起点落在「池起点所在
    的 4 字节网格」上。按「4 字节对齐行走」读取（读到 NUL → 跳到下一格），串首不再
    混入 1~3 字节填充垃圾（这是旧版 koutari_extract.py 用 naive null-split 产生 っ/て/
    泊魔驕B 类乱码的根因）。
  * 消息 = `<说话人名>\r\n<正文>`（无 \r\n = 旁白）；说话人可为字面名 / `#名`(主人公宏)
    / `？？？` / 泛用身份札（―――・妖・青年…）。
  * 正文内联：`#［Nよみ］`=注音(剔)、`#名`=主人公宏(解析)、`#<字>`=图标(剔)。

★★ 与 あさき 工具的差异（本作口径）
  * 【名札一律保留】：输出 = `名 + 正文`（名印在正文页内，接在台词前），不剥名前缀。
  * `#名` 主人公宏解析为 `逢坂 千世`（vndb c49534 外部依据；本作主人公 Nameable，
    游戏内 charaname.xtx 仅 `名前なし` 占位板、无默认名 ⇒ 取 vndb canon）。
"""
import os, re, collections, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC    = os.path.join(VNTRANS_HOME, '_work_koutari/iso/app/spt')
OUTDIR = os.path.join(VNTRANS_HOME, '提取结果')
TITLE  = '[PC-JP]神足町人妖譚 ~迷イ子ノ章~'
PROTAG = '千世'        # 主人公宏 #名 解析值：vndb c49534 逢坂千世，用户定仅取 given name「千世」（不要姓）
ORDER_FILE = os.path.join(SRC, 'project.xtx')

# 不收：系统 / 演出标签＋资源名（无正文）
EXCLUDE = {'sys', 'koutari_backscript'}

# ── 名札表（charaname.xtx 具名 ＋ namecol.xtx 泛用身份札）──────────────
def load_names():
    names = []
    for fn in ('charaname.xtx', 'namecol.xtx'):
        p = os.path.join(SRC, fn)
        if not os.path.exists(p):
            continue
        for line in open(p, 'rb').read().decode('cp932', 'ignore').splitlines():
            line = line.strip()
            if ',' in line:
                v = line.split(',', 1)[1].strip()
            else:
                v = line
            if v and v != '名前なし':
                names.append(v)
    return sorted(set(names), key=len, reverse=True)

NAMES = load_names()
MARKERS = ['#名', '？？？'] + NAMES
_ALT = '|'.join(re.escape(m) for m in MARKERS)
NAME_RE = re.compile('^(' + _ALT + r')\r\n')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')


# ── 基础 ──────────────────────────────────────────────────────
def decrypt(p):
    return bytes(b ^ 0xFF for b in open(p, 'rb').read())


def is_lead(b):
    return (0x81 <= b <= 0x9f) or (0xe0 <= b <= 0xfc)


def scan_strings(n, start=0, end=None):
    L = len(n) if end is None else end
    out = []; i = start
    while i < L:
        if n[i] == 0:
            i += 1; continue
        j = i; ok = True
        while j < L:
            c = n[j]
            if c == 0:
                break
            if is_lead(c):
                if j + 1 < L and ((0x40 <= n[j + 1] <= 0x7e) or (0x80 <= n[j + 1] <= 0xfc)):
                    j += 2
                else:
                    ok = False; break
            elif 0x20 <= c <= 0x7e or 0xa1 <= c <= 0xdf or c in (0x0d, 0x0a, 0x09):
                j += 1
            else:
                ok = False; break
        if ok and j > i:
            out.append((i, j)); i = j
        else:
            i += 1
    return out


def _isjp(s):
    return bool(JP.search(s))


def find_pools(n):
    ss = scan_strings(n, 0)
    if not ss:
        return None
    runs = []; cur = [ss[0]]
    for k in range(1, len(ss)):
        if ss[k][0] - ss[k - 1][1] <= 8:
            cur.append(ss[k])
        else:
            runs.append(cur); cur = [ss[k]]
    runs.append(cur)
    scored = []
    for r in runs:
        if len(r) < 10:
            continue
        crlf = sum(1 for a, b in r if b'\x0d\x0a' in n[a:b])
        txt = sum(1 for a, b in r if _isjp(n[a:b].decode('cp932', 'ignore')))
        scored.append((crlf * 2 + txt, r[0][0], r[-1][1]))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    p1 = scored[0]
    p2 = None
    for s in scored[1:]:
        if s[1] >= p1[2]:
            p2 = s; break
    return ((p1[1], p1[2]), (p2[1], p2[2]) if p2 else None)


# ── 4 字节对齐行走 ────────────────────────────────────────────
_JIS2_LO, _JIS2_HI = 0x989F, 0xEAA4


def _lvl2(ch):
    b = ch.encode('cp932', 'ignore')
    if len(b) != 2:
        return False
    v = b[0] << 8 | b[1]
    return _JIS2_LO <= v <= _JIS2_HI or v >= 0xFA40


def dirty_score(n, w):
    s = 0
    for a, b in w:
        try:
            t = n[a:b].decode('cp932')
        except UnicodeDecodeError:
            s += 3; continue
        if not t:
            continue
        o = ord(t[0])
        if t[0] not in '#？' and (0x20 <= o < 0x80 or 0xff61 <= o <= 0xff9f):
            s += 1
        if t[0] != '#' and t[0] != '？' and _lvl2(t[0]):
            s += 1
        if re.search(r'[\uff61-\uff9f]', t):
            s += 2
    return s


def walk(n, start, end, phase):
    o = start; out = []
    while o < end:
        j = o
        while j < end and n[j] != 0:
            j += 1
        if j >= end:
            break
        out.append((o, j))
        k = j + 1
        o = ((k - phase + 3) // 4) * 4 + phase
        if o <= j:
            o = j + 1
    return out


def _crlf_dense(n, w):
    for i in range(len(w)):
        win = w[i:i + 16]
        if not win:
            break
        good = sum(1 for a, b in win if b'\r\n' in n[a:b])
        if good >= max(6, len(win) * 0.5):
            return i
    return 0


_MONTH_RE = re.compile(r'^[０-９]{1,2}月[０-９]{1,2}日')


def marker_score(n, w):
    s = 0
    for a, b in w:
        t = n[a:b].decode('cp932', 'ignore')
        if t.startswith('%#'):
            s += 20
        if NAME_RE.match(t):
            s += 10
        if t.startswith('■') or _MONTH_RE.match(t):
            s += 2
        if b'\x0d\x0a' in n[a:b]:
            s += 1
        if re.search(r'[\uff61-\uff9f]', t):
            s -= 3
    return s


_KANA = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')


def head_trim(n, w):
    i0 = 0
    for k, (a, b) in enumerate(w):
        t = n[a:b].decode('cp932', 'ignore')
        if len(t) >= 3 and _KANA.search(t):
            i0 = k; break
    return w[max(0, i0 - 4):]


def read_pool(n, rng):
    if not rng:
        return [], 0
    start, end = rng
    best = None
    for ph in range(4):
        w = walk(n, start, end, ph)
        if not w:
            continue
        w = head_trim(n, w)
        sc = marker_score(n, w)
        cand = (-sc, -len(w), ph, w)
        if best is None or cand[:3] < best[:3]:
            best = cand
    return best[3], best[2]


# ── 成行（名札保留）────────────────────────────────────────────
def clean_inline(s):
    s = re.sub(r'#［[^］]*］', '', s)          # 注音 -> 剔
    s = re.sub(r'#(?!名)[^\r\n]', '', s)        # 其余 #X 图标 -> 剔（保留 #名）
    s = s.replace('#名', PROTAG)               # 主人公宏 -> vndb canon（逢坂 千世）
    s = s.replace('\r\n', '')                   # 页内软换行合并
    s = s.replace('\n', '').replace('\r', '')
    return s.strip()


def to_line(raw):
    """`<名札>\r\n<正文>` → `名札＋正文`（名印在正文页内，保留）；无名札=旁白。"""
    try:
        t = raw.decode('cp932')
    except UnicodeDecodeError:
        return ''
    if t and t[0] in '\r\n':
        t = t.lstrip('\r\n')
    if '\r\n' in t:
        seg0, body = t.split('\r\n', 1)
        name = clean_inline(seg0)
        body = clean_inline(body)
        if name:
            return name + body
        return body
    return clean_inline(t)


# ── 名札自举（charaname/namecol 只收了部分，泛用身份札须从数据挖）──────
_PUNCT_CORE = re.compile(r'[。、！？…「」『』（）・,，]')
_NAMEISH = re.compile(r'[\u4e00-\u9fff\u30a0-\u30ff]')


def _is_plate(core, rest, cnt=1):
    if not core or len(core) > 14:
        return False
    if rest[:1] not in ('「', '『'):
        return False
    if core == '―――':
        return True
    if '・' in core:
        return bool(re.fullmatch(r'[\u4e00-\u9fff\u30a0-\u30ff・]+', core))
    c2 = core[:-1] if core[-1] in '？?' else core
    if _PUNCT_CORE.search(c2):
        return False
    if not _NAMEISH.search(c2):
        return rest.startswith('「「')
    if c2 != core:
        return cnt >= 2
    return True


def mine_plates(pools):
    cnt = collections.Counter(); dbl = set()
    for name, n in pools.items():
        r = find_pools(n)
        if not r:
            continue
        w, _ = read_pool(n, r[0])
        for a, b in w:
            t = n[a:b].decode('cp932', 'ignore')
            if '\r\n' not in t:
                continue
            seg0, rest = t.split('\r\n', 1)
            core = re.sub(r'#［[^］]*］', '', seg0).strip()
            if rest[:1] in ('「', '『') and core and len(core) <= 14:
                cnt[core] += 1
                if rest.startswith('「「'):
                    dbl.add(core)
    return {k for k, v in cnt.items() if _is_plate(k, '「「' if k in dbl else '「', v)}


# ── 池1 故事正文 ───────────────────────────────────────────────
def extract_pool1(n, rafts):
    lines = []
    for a, b in rafts:
        s = to_line(n[a:b])
        if len(s) < 2:
            continue
        # 纯符号台词（「…………」「？」）也是正文 ⇒ 以引号/括号开头者一律保留；
        # 其余仍要求含假名/汉字（滤掉资源名・符号噪声）。
        if not JP.search(s) and s[0] not in '「『（':
            continue
        if re.search(r'[0-9A-Za-z]', s) and len(s) < 10:
            continue
        lines.append(s)
    return lines


# ── 池2：選択肢・場面タイトル ──────────────────────────────────
COLORS = set('黄赤青白緑紫桃橙灰黒金')


def pool2_items(n, rafts):
    items = []
    for a, b in rafts:
        t = n[a:b].decode('cp932', 'ignore').strip()
        if not t:
            continue
        if t.startswith('%#'):
            body = t[2:]
            if body and body[0] in COLORS:
                body = body[1:]
            items.append(('question', body.strip())); continue
        if '★' in t or '☆' in t:
            continue
        if t.startswith('■'):
            t2 = t[1:].strip()
            if _MONTH_RE.match(t2):
                items.append(('title', t2))
            continue
        if '：' in t or '＿' in t:
            continue
        if _MONTH_RE.match(t):
            items.append(('title', t)); continue
        if re.search(r'[A-Za-z0-9]', t) or len(t) < 2:
            continue
        items.append(('other', t))
    return items


_OPT_OK = re.compile(r'^[\u3040-\u30ff\u4e00-\u9fffー、。…！？「」『』（）・～]+$')


def option_like(t):
    return bool(t) and 1 <= len(t) <= 24 and bool(_OPT_OK.match(t))


def extras_in_order(n, rafts):
    out = []; seen = set()
    items = pool2_items(n, rafts)
    i = 0
    while i < len(items):
        k, t = items[i]
        if k == 'question':
            out.append(t); j = i + 1; nopt = 0
            while j < len(items) and nopt < 6 and items[j][0] == 'other' \
                    and option_like(items[j][1]):
                out.append(items[j][1]); j += 1; nopt += 1
            i = j
        elif k == 'title':
            if t not in seen:
                seen.add(t); out.append(t)
            i += 1
        else:
            i += 1
    return out


# ── main ──────────────────────────────────────────────────────
def main(dump=None):
    order = [l.strip() for l in open(ORDER_FILE, 'rb').read().decode('cp932', 'ignore').splitlines() if l.strip()]
    pools = {}
    for name in order:
        p = os.path.join(SRC, name + '.spt')
        if os.path.exists(p):
            pools[name] = decrypt(p)

    if dump == '@names':
        print('NAMES(%d):' % len(NAMES), NAMES)
        PLATES = set(MARKERS) | mine_plates(pools)
        print('PLATES(%d):' % len(PLATES), sorted(PLATES))
        return

    PLATES = set(MARKERS) | mine_plates(pools)
    blocks = []; diag = []
    for name in order:
        if name not in pools:
            continue
        if name in EXCLUDE:
            diag.append((name, 0, 0, -2, 'EXCLUDE')); continue
        n = pools[name]
        r = find_pools(n)
        if not r:
            diag.append((name, 0, 0, -1, 'NOPOOL')); continue
        (r1, r2) = r
        w1, ph1 = read_pool(n, r1)
        w2, ph2 = read_pool(n, r2) if r2 else ([], 0)
        body = extract_pool1(n, w1)
        extra = extras_in_order(n, w2) if w2 else []
        blocks.append((name, body, extra))
        diag.append((name, len(body), len(extra), ph1 * 10 + ph2, ''))
        if dump == name:
            print('### dump', name, 'phases', ph1, ph2, 'r1', r1, 'r2', r2)
            for s in body[:50]:
                print('   B|', s[:90])
            for s in extra[:60]:
                print('   X|', s[:90])

    lines = []
    for name, body, extra in blocks:
        lines.extend(body)
        lines.extend(extra)

    if dump:
        print('%-16s %7s %6s %6s %s' % ('file', 'body', 'extra', 'ph', 'note'))
        for d in diag:
            print('%-16s %7d %6d %6d %s' % d)
        print('total lines:', len(lines))
        return

    txt = '\n'.join(lines) + '\n'
    # 主角名 surname 剥离（user 定：不要姓，仅取 given name 千世）：
    # 仅作用于主角全名「逢坂千世」（含 #名 宏已解析处 + 源硬写自报处），
    # 不影响家族指称「逢坂家/逢坂の家」等。
    txt = txt.replace('逢坂千世', '千世')
    assert '\r' not in txt and '\ufffd' not in txt
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, TITLE + '.txt')
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(txt)

    print('%-16s %7s %6s %6s' % ('file', 'body', 'extra', 'ph'))
    for d in diag:
        print('%-16s %7d %6d %6d' % d[:4])
    print('total lines:', len(lines), '->', out, os.path.getsize(out), 'bytes')
    bad = [x for x in lines if re.search(r'[A-Za-z]', x)]
    hk = [x for x in lines if re.search(r'[\uff61-\uff9f]', x)]
    pua = [x for x in lines if re.search(r'[\ue000-\uf8ff]', x)]
    print('ASCII-letter lines:', len(bad), 'halfwidth-kana:', len(hk), 'PUA:', len(pua))
    for x in (bad + hk + pua)[:30]:
        print('   ', x[:80])


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
