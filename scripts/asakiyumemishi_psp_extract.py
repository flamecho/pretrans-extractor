# -*- coding: utf-8 -*-
"""あさき、ゆめみし (PSP-JP / System-NNN「NNNLib」engine) 全文本提取 · 定稿

源：<游戏 dump 目录>/[PSP-JP]あさき、ゆめみし.rar  (RAR5, 密码 otoame)
    → 晨曦时梦见兮.iso（PSP GAME）
    → PSP_GAME/USRDIR/data.cpk（CRI CPK, CpkMode=3, 14414 entries）
    → spt/*.spt = 剧本字节码 / spt/*.xtx = 纯 cp932 配置

★★ .spt 格式（与 PC 版「ひととせ」同引擎 System-NNN，格式一致）
  * 整文件【逐字节 XOR 0xFF】→ 0x30 "SPTHEADER0"，0x00 u32 = 0x20
  * 头(0x00..0x40) + 4×(u32 count + u32 base) 描述 4 个字符串组
  * 布局: [头][指令流][地址表1][消息池1][小桩][地址表2][池2 杂多テーブル]
  * 消息 = `<说话人名>\r\n<正文>`（无 \r\n = 旁白）；说话人可为字面名 / `#名`(=主人公名) / `？？？`
  * 正文内联控制码: `#［Nよみ］`=注音(剔)、`#名`=主人公名(inline)、`#<字>`=图标(剔)

★★★ 关键结构性发现（本作 PSP 版 → 已消除 PC 版遗留的乱码前缀问题）
  字符串池的记录格式 = **[data][NUL][垃圾填充至 4 字节边界]**，
  即每条串的起点落在「池起点所在的那条 4 字节网格」上。
  ⇒ 按「4 字节对齐行走」读取（读到 NUL → 跳到下一格），
     串首不会再混入 1~3 字节填充垃圾（PC 版靠启发式重同步，本作实测 0 残留）。
  池起点本身可能不落在 0/4 相位 ⇒ 每池自动在 4 个相位中选「脏串最少」者。

池2（地址表2 之后）= 雑多な文字列テーブル：
  ★★ラベル★★ / `%#<色漢字>` = 選択肢の質問（= 上屏文本） / 質問直後の短い日本語文 = 選択肢 /
  日付・場面タイトル(■７月２８日・昼) / ジャンプ先スクリプト名・資源名（不收）

输出规范：UTF-8-BOM / 纯 LF / 一次点击 = 一行 / 框内换行合并 / 保留日文原文 /
  去说话人前缀 / 主人公名 inline / 不加翻译。
"""
import os, re, collections, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

SRC    = os.path.join(VNTRANS_HOME, '_work_asakayumemi/spt')
OUTDIR = os.path.join(VNTRANS_HOME, '提取结果')
TITLE  = 'あさき、ゆめみし'
PROTAG = '沙耶'

# 引擎文件加载顺序（project.xtx 列名）。
# sys / _catch = 系统・UI；asa_backscript = 演出标签＋资源名（无正文）→ 三者不收
ORDER = ['op', 'chapter1', 'chapter2', 'chapter3', 'chihaya', 'syuichi',
         'takatora', 'giou', 'shino', 'kagachi',
         '_chapter1sub', '_chapter3sub', '_chapter2sub', '_chapter3_night',
         '_kiyome', 'yasutuna']

NAMES = []
for _l in open(os.path.join(SRC, 'charaname.xtx'), 'rb').read().decode('cp932').splitlines():
    if ',' in _l:
        _v = _l.split(',', 1)[1].strip()
        if _v and _v != '名前なし':
            NAMES.append(_v)
MARKERS = ['#名', '？？？'] + sorted(set(NAMES), key=len, reverse=True)
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
    """返回 w 中「消息块」起点下标（连续 ≥6 条里半数以上含 CRLF）。"""
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
    """结构标记命中数 —— 相位选错的行走会破坏这些标记 ⇒ 判据锐利。
    `%#`（選択肢質問）与 NAME_RE（人名札）为最强锚点。"""
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
    """裁掉池起点前面混入的「地址表」区（表项短、无假名）。"""
    i0 = 0
    for k, (a, b) in enumerate(w):
        t = n[a:b].decode('cp932', 'ignore')
        if len(t) >= 3 and _KANA.search(t):
            i0 = k; break
    return w[max(0, i0 - 4):]


def read_pool(n, rng):
    """池起点常与前面的「地址表」区被误并；按 4 相网格行走，取结构标记最多者。"""
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


# ── 成行 ──────────────────────────────────────────────────────
def clean_body(s):
    s = re.sub(r'#［[^］]*］', '', s)              # 注音 -> 剔
    s = s.replace('#名', PROTAG)                  # 主人公名 inline
    s = re.sub(r'#[^\r\n]', '', s)                # 其余 #X 图标记号 -> 剔
    s = s.replace('\r\n\u3000', '').replace('\r\n', '')
    s = s.replace('\n', '').replace('\r', '')
    return s.strip()


def to_line(raw, plates):
    """`<名札>\r\n<正文>` → 正文；无名札 = 旁白。名札表含自举结果（含泛用身份札）。"""
    try:
        t = raw.decode('cp932')
    except UnicodeDecodeError:
        return ''
    if t and t[0] in '\r\n':
        t = t.lstrip('\r\n')
    if '\r\n' in t:
        seg0, rest = t.split('\r\n', 1)
        core = re.sub(r'#［[^］]*］', '', seg0).strip()
        if core in plates:
            return clean_body(rest)
        m = re.match(r'^(.{1,2}?)(.{1,12}?)\r\n', t)      # 容忍 ≤2 前置垃圾字
        if m and m.group(2).strip() in plates:
            return clean_body(t[m.end():])
    return clean_body(t)


# ── 名札自举（charaname.xtx 只收了具名角色，泛用身份札须从数据挖）──────
_PUNCT_CORE = re.compile(r'[。、！？…「」『』（）・,，]')
_NAMEISH = re.compile(r'[\u4e00-\u9fff\u30a0-\u30ff]')


def _is_plate(core, rest, cnt=1):
    if not core or len(core) > 14:
        return False
    if rest[:1] not in ('「', '『'):        # 名札后必接台词
        return False
    if core == '―――':                     # 无声/不明
        return True
    if '・' in core:                       # 多人名札「祇王・虚空」「先輩・後輩」
        return bool(re.fullmatch(r'[\u4e00-\u9fff\u30a0-\u30ff・]+', core))
    c2 = core[:-1] if core[-1] in '？?' else core
    if _PUNCT_CORE.search(c2):
        return False
    if not _NAMEISH.search(c2):            # 纯平假名：仅「齐声」形态认（ふたり）
        return rest.startswith('「「')
    if c2 != core:                         # 以 ？ 收尾（東雲さん？）⇒ 须重复出现
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
                if rest.startswith('「「'):        # 齐声（ふたり/子供たち）
                    dbl.add(core)
    return {k for k, v in cnt.items() if _is_plate(k, '「「' if k in dbl else '「', v)}


def extract_pool1(n, rafts, plates):
    lines = []
    for a, b in rafts:
        s = to_line(n[a:b], plates)
        s = LINE_FIX.get(s, s)
        if len(s) < 2:
            continue
        # 纯符号台词（「…………」「？」「～～♪」）也是正文 ⇒ 以引号开头者一律保留；
        # 其余仍要求含假名/汉字（滤掉资源名・符号噪声）。
        if not JP.search(s) and s[0] not in '「『（':
            continue
        if re.search(r'[0-9A-Za-z]', s) and len(s) < 10:
            continue
        lines.append(s)
    return lines


# ★原文缺陷定值修（沿用 アーメン・ノワール／Little Aid 的 LINE_FIX 先例）
#   chapter3.spt @0x69a7e：该框正文以「…けど。」收尾即 NUL，**全库唯一、无平行副本**
#   ⇒ 判为原作用漏收尾「」；不补则行首「未闭合（引号配对必 E）。
LINE_FIX = {
    '「ん、いいねー。出来ればあと砂糖をスプーン１３杯くらい分の甘さは欲しいけど。':
    '「ん、いいねー。出来ればあと砂糖をスプーン１３杯くらい分の甘さは欲しいけど。」',
}


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
            items.append(('question', body.strip()))
            continue
        if '★' in t or '☆' in t:
            continue
        if t.startswith('■'):
            t2 = t[1:].strip()
            if _MONTH_RE.match(t2):
                items.append(('title', t2))
            continue                                   # 其余 ■… = 内部标签
        if '：' in t or '＿' in t:
            continue                                   # 内部标签（シーン名：分岐＿…）
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
    """池2 をその出現順に「質問＋選択肢」「場面タイトル」へ展開。"""
    out = []
    seen = set()
    items = pool2_items(n, rafts)
    i = 0
    while i < len(items):
        k, t = items[i]
        if k == 'question':
            out.append(t)
            j = i + 1; nopt = 0
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
    pools = {}
    for name in ORDER:
        p = os.path.join(SRC, name + '.spt')
        if os.path.exists(p):
            pools[name] = decrypt(p)

    blocks = []; diag = []
    PLATES = set(MARKERS) | mine_plates(pools)
    if dump == '@plates':
        print('名札表 %d 种：' % len(PLATES), sorted(PLATES))
        return
    for name in ORDER:
        if name not in pools:
            continue
        n = pools[name]
        r = find_pools(n)
        if not r:
            diag.append((name, 0, 0, -1)); blocks.append((name, [], [])); continue
        (r1, r2) = r
        w1, ph1 = read_pool(n, r1)
        w2, ph2 = read_pool(n, r2) if r2 else ([], 0)
        body = extract_pool1(n, w1, PLATES)
        extra = extras_in_order(n, w2) if w2 else []
        nq = sum(1 for x in extra if x.startswith('%#')) if False else 0
        blocks.append((name, body, extra))
        diag.append((name, len(body), len(extra), ph1 * 10 + ph2))
        if dump == name:
            print('### dump', name, 'phases', ph1, ph2, 'pool1 range', r1, 'pool2', r2)
            for s in body[:40]:
                print('   B|', s[:80])
            for s in extra[:90]:
                print('   X|', s[:80])

    lines = []
    for name, body, extra in blocks:
        lines.extend(body)
        lines.extend(extra)

    if dump:
        return

    txt = '\n'.join(lines) + '\n'
    assert '\r' not in txt and '\ufffd' not in txt
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, TITLE + '_全文本.txt')
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(txt)

    print('%-18s %7s %7s %5s' % ('file', 'body', 'extra', 'ph'))
    for d in diag:
        print('%-18s %7d %7d %5d' % d)
    print('total lines:', len(lines), '->', out, os.path.getsize(out), 'bytes')
    bad = [x for x in lines if re.search(r'[A-Za-z]', x)]
    hk = [x for x in lines if re.search(r'[\uff61-\uff9f]', x)]
    pua = [x for x in lines if re.search(r'[\ue000-\uf8ff]', x)]
    print('ASCII-letter lines:', len(bad), 'halfwidth-kana:', len(hk), 'PUA:', len(pua))
    for x in (bad + hk + pua)[:25]:
        print('   ', x[:78])


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
