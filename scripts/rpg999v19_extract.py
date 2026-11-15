# -*- coding: utf-8 -*-
"""999,Victory ver1.9（RPGツクールVX Ace / RGSS3）文本提取

容器 RGSSAD v3 → Data/*.rvdata2（Ruby Marshal）
成行（L0）：code 101（文章の表示）开一个文本框，紧随 N×code 401 为其显示行 ⇒ 一框＝一次点击＝一行。
  \! = 0、\^ = 0；每框显示行数（401 行数＋行内 \n）1:67 / 2:344 / 3:271 / 4:129，超 4 = 0 ⇒ 无自动分页 ⇒ 单版。
  code 105/405（スクロール）＝一次自动播放＝一行。
名札：无 name 命令、无独立名字窗；名字是 101 框内第一行 401（【…】）与台词同框同屏 ⇒ 上屏 ⇒ 保留，去【】贴同行。

用法：
  python rpg999v19_extract.py <Game.rgss3a> <out.txt> [--work <dir>] [--list-all] [--dump-json <p>]
"""
import io, os, re, struct, sys, json
from collections import Counter

NAME_DEFAULT = {1: 'マフィン'}
CURRENCY = 'Ｇ'

# ------------------------------------------------------------------ RGSSAD v3
def read_rgssad(path, outdir):
    d = open(path, 'rb').read()
    assert d[:8] == b'RGSSAD\x00\x03', d[:8]
    seed = struct.unpack('<I', d[8:12])[0]
    key = (seed * 9 + 3) & 0xffffffff
    kb = struct.pack('<I', key)

    def u32(o):
        return struct.unpack('<I', bytes(d[o + i] ^ kb[i] for i in range(4)))[0]

    pos, ents = 12, []
    while pos + 16 <= len(d):
        off, sz, dk, ln = u32(pos), u32(pos + 4), u32(pos + 8), u32(pos + 12)
        if off == 0 or ln == 0 or ln > 512 or pos + 16 + ln > len(d):
            break
        nm = bytes(d[pos + 16 + i] ^ kb[i % 4] for i in range(ln)).decode('cp932').replace('\\', '/')
        ents.append((off, sz, dk, nm))
        pos += 16 + ln
    assert ents[-1][0] + ents[-1][1] == len(d), 'index/data not closed'

    for off, sz, dk, nm in ents:
        buf = bytearray(d[off:off + sz])
        k, nfull = dk, sz // 4
        for i in range(nfull):
            w = struct.pack('<I', k)
            for j in range(4):
                buf[i * 4 + j] ^= w[j]
            k = (k * 7 + 3) & 0xffffffff
        w = struct.pack('<I', k)
        for j in range(nfull * 4, sz):
            buf[j] ^= w[j - nfull * 4]
        dst = os.path.join(outdir, nm)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(buf)
    return ents


def load_rv2(path):
    from rubymarshal.reader import load as rload
    return rload(io.BytesIO(open(path, 'rb').read()))


def A(o, n):
    return o.attributes.get(n) if hasattr(o, 'attributes') else None


def dec(v):
    t = getattr(v, 'text', None)
    if isinstance(t, str):
        return t
    if isinstance(v, (bytes, bytearray)):
        for enc in ('utf-8', 'cp932'):
            try:
                return bytes(v).decode(enc)
            except UnicodeDecodeError:
                pass
        return bytes(v).decode('cp932', 'replace')
    if isinstance(v, str):
        return v
    return str(v)


# ------------------------------------------------------------------ 文本清洗
NAME_MACRO = re.compile(r'\\[Nn]\[\s*(\d+)\s*\]')     # \n[1] / \N[1]（\n 后接 [ 即名字宏）
VAR_MACRO = re.compile(r'\\[Vv]\[\s*(\d+)\s*\]')
ICON_OR_COLOR = re.compile(r'\\[CcIiAaFfPp]\[\s*[^\]]*\]')
FLAGS = re.compile(r'\\[<>|!$^{}.]')
PLATE = re.compile(r'^【(.+?)】$')


def clean(s):
    s = NAME_MACRO.sub(lambda m: NAME_DEFAULT.get(int(m.group(1)), '〔未解析〕'), s)
    s = VAR_MACRO.sub('〔未解析〕', s)
    s = re.sub(r'\\[Gg]', CURRENCY, s)
    s = ICON_OR_COLOR.sub('', s)
    s = FLAGS.sub('', s)
    return s.replace('\\', '').strip(' \u3000\t')


QUOTES = '「『（［'


def split_plate(rows):
    """框内第一行是名札：整行形如 【名】，**且次行以「『（( 起头**（结构判据）。
    只认【】不带后随引号的是标题/面板（如【ハーブの効果】），不是名札。"""
    if len(rows) < 2:
        return None, rows
    m = PLATE.match(rows[0].strip())
    if not m:
        return None, rows
    if not rows[1].strip().startswith(tuple(QUOTES)):
        return None, rows
    return m.group(1), rows[1:]


# ------------------------------------------------------------------ 收弃判据
# 系统提示 / 教学面板（判据：结构字段＋系统文案，非「像不像」）
# 收：消息窗内的叙述与系统提示（`～を手に入れた！`/`～に遭遇した！`/壺不足の地の文 等）——它们直接渲染到画面。
# 不收：整块以 `\>` 起头且讲操作/数值机制的教学文与数值面板、≥3 个 `\v` 的运行期面板。
PANEL_WORDS = re.compile(r'キー|矢印|メニュー画面|画面右上|画面左上|ゲージ|確率表記')
VAR = re.compile(r'\\[Vv]\[\s*\d+\s*\]')
QUOTE_CH = '「『（［'
DEBUG_EV = re.compile(r'デバック|デバッグ')
START_EV = re.compile(r'^スタートマップ / ゲームスタート')   # 名前入力＋開始メニュー（系统 UI，非剧本）
# 系统播报（物品/技能入手、数值变化、机制反馈等固定文案；与 ver1.6 同系列口径一致）：只作用于「无台词引号」的消息框
SYS_NOTICE = re.compile(
    r'手に入れた！|入手した！|を覚えた！|が使用可能になった！|に遭遇した！|'
    r'ギャラリーのグラフィックがすべて開放|壺を壊すには|'
    r'ＢＯＸが空になりました|エリア内の壺をすべて破壊した|何も手に入らなかった|'
    r'だが壺の中身も共にほぼ消滅した|ステータスが上昇した|ティラミスに装備品を渡した|'
    r'ドスケベ修道女服を身に着けた')


def box_is_dialog(rows):
    """台词/心声框判据（结构）：框内任一行含「（［ 之一。
    『』只用于包物品名（`『魔王様ブロマイド』を手に入れた！`），不作为台词依据。"""
    return any(ch in r for r in rows for ch in '「（［')


def classify(kind, path, rows, params=None):
    """收弃判据（L0 结构，不做「像不像」的内容过滤）：
    收 —— 101/401 消息框内的台词 / 心声 / 地の文，102 剧情选项。
    弃（逐条登记，报告 §5）——
      ① 调试事件；② 开始菜单里的「名字确认 / 游戏开始」提示（系统 UI）；
      ③ 系统播报（`～を手に入れた！` `～に遭遇した！` `～を覚えた！` 等固定文案，非剧本）；
      ④ 整块以 `\\>` 起头且讲操作/数值机制的教学文与数值面板；
      ⑤ 运行期变量 ≥3 的面板（静态不可求值）；⑥ 商店/抽卡价目选项；
      ⑦ 355 脚本（実績弹窗文案 / 画廊与结局旗标）；⑧ 105/405 staff roll。
    """
    joined = ''.join(rows)
    if DEBUG_EV.search(path):
        return '调试菜单'
    if kind == 'script':
        if re.search(r'実績更新|Window_Getinfo', joined):
            return '実績弹窗（系统 UI）'
        return '脚本无文本（旗标/调用）'
    if kind == 'scroll':
        return '制作名单（staff roll）'
    if kind == 'choice':
        if re.search(r'ガチャ|\\G|購入|売却', joined):
            return '系统菜单选项（商店/抽卡价目）'
        if START_EV.search(path) and all(c.strip() in ('ＯＫ', 'やり直す') for c in rows):
            return '名字输入确认（系统 UI）'
        return None
    if kind == 'msg' and START_EV.search(path) and re.search(r'プレイヤーの名前は|ゲームを開始します', joined):
        return '开始菜单（名字确认/开场提示）'
    nm, _ = split_plate([clean(r) for r in rows])
    if nm:
        return None                       # 框内有名札【名】＋台词 ⇒ 收（含敌人交钱等上屏台词）
    if SYS_NOTICE.search(joined):
        return '系统播报'
    nonempty = [r for r in rows if r.strip()]
    if nonempty and all(r.lstrip().startswith('\\>') for r in nonempty):
        # `\>`＝作者用于左对齐的系统/教学文本（正文与台词一律全角缩进）
        return '教学说明/系统面板（全行 \\> 左对齐，无台词）'
    if VAR.search(joined):
        return '数值面板（含运行期变量 \\v[n]，静态不可求值）'
    return None


def main():
    src, out = sys.argv[1], sys.argv[2]
    work = os.path.join(os.path.dirname(out) or '.', '_work_rgss')
    for i, a in enumerate(sys.argv):
        if a == '--work':
            work = sys.argv[i + 1]
    list_all = '--list-all' in sys.argv
    os.makedirs(work, exist_ok=True)

    ents = read_rgssad(src, work)
    data = os.path.join(work, 'Data')
    maps = sorted(f for f in os.listdir(data) if re.fullmatch(r'Map\d{3}\.rvdata2', f))
    infos = load_rv2(os.path.join(data, 'MapInfos.rvdata2'))
    name_of = {'Map%03d.rvdata2' % k: dec(A(v, '@name') or '') for k, v in infos.items()}

    items = []

    def walk(lst, path):
        i = 0
        while i < len(lst):
            c = A(lst[i], '@code')
            if c == 101:
                p = A(lst[i], '@parameters') or ['']
                rows = []
                i += 1
                while i < len(lst) and A(lst[i], '@code') == 401:
                    rows.append(dec(A(lst[i], '@parameters')[0]))
                    i += 1
                items.append(dict(kind='msg', path=path, rows=rows,
                                  params=[dec(x) for x in p]))
                continue
            if c == 105:
                rows = []
                i += 1
                while i < len(lst) and A(lst[i], '@code') == 405:
                    rows.append(dec(A(lst[i], '@parameters')[0]))
                    i += 1
                items.append(dict(kind='scroll', path=path, rows=rows))
                continue
            if c == 102:
                p = A(lst[i], '@parameters') or [[], 0]
                items.append(dict(kind='choice', path=path, rows=[dec(x) for x in p[0]]))
            if c == 355:
                buf = [dec(A(lst[i], '@parameters')[0])]
                j = i + 1
                while j < len(lst) and A(lst[j], '@code') == 655:
                    buf.append(dec(A(lst[j], '@parameters')[0]))
                    j += 1
                items.append(dict(kind='script', path=path, rows=['\n'.join(buf)]))
            i += 1

    for f in maps:
        m = load_rv2(os.path.join(data, f))
        for eid, ev in (A(m, '@events') or {}).items():
            evname = dec(A(ev, '@name') or '')
            for pi, pg in enumerate(A(ev, '@pages') or []):
                walk(A(pg, '@list') or [], '%s / %s (ev%03d p%d)' % (name_of.get(f, f), evname, eid, pi))

    for e in load_rv2(os.path.join(data, 'CommonEvents.rvdata2')):
        if e is None:
            continue
        walk(A(e, '@list') or [], '共通: %s (CE%03d)' % (dec(A(e, '@name') or ''), A(e, '@id')))

    for t in load_rv2(os.path.join(data, 'Troops.rvdata2')):
        if t is None:
            continue
        for pi, pg in enumerate(A(t, '@pages') or []):
            walk(A(pg, '@list') or [], '戦闘: %s (Troop%d p%d)' % (dec(A(t, '@name')), A(t, '@id'), pi))

    kept, excluded = [], []
    for it in items:
        reason = classify(it['kind'], it['path'], it['rows'], it.get('params'))
        (excluded.append((reason, it)) if reason else kept.append(it))

    if list_all:
        for reason, it in excluded:
            print('[EXC] %-18s %s' % (reason, it['path']))
            print('       ', ' / '.join(x.strip() for x in it['rows'])[:170])
        print('kept', len(kept), 'excluded', len(excluded))
        return

    if '--dump-json' in sys.argv:
        p = sys.argv[sys.argv.index('--dump-json') + 1]
        json.dump({'kept': kept, 'excluded': [dict(reason=r, **it) for r, it in excluded]},
                  open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('dumped', p)

    out_lines = []
    for it in kept:
        rows = [clean(r) for r in it['rows']]
        if it['kind'] == 'choice':
            for c in rows:
                c = re.sub(r'\s*(en|if)\([^)]*\)', '', c, flags=re.I).strip()
                if c:
                    out_lines.append(c)
            continue
        if it['kind'] == 'scroll':
            body = ''.join(r.strip(' \u3000') for r in rows if r.strip(' \u3000'))
            if body:
                out_lines.append(body)
            continue
        nm, body_rows = split_plate(rows)
        body = ''.join(r.strip(' \u3000') for r in body_rows if r.strip(' \u3000'))
        if not body:
            continue
        out_lines.append((nm + body) if nm else body)

    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(out_lines) + '\n').encode('utf-8'))

    print('items', len(items), 'kept', len(kept), 'excluded', len(excluded))
    print('lines', len(out_lines), 'bytes', os.path.getsize(out))
    print('excluded by reason', Counter(r for r, _ in excluded))
    print('kept by kind', Counter(i['kind'] for i in kept))
    # 行完整性探针
    bad_open = [l for l in out_lines if l.count('「') != l.count('」')]
    bad_par = [l for l in out_lines if l.count('（') != l.count('）')]
    print('「」不配对行', len(bad_open), '（）不配对行', len(bad_par))
    for l in bad_open[:10]:
        print('   Q', l[:120])
    for l in bad_par[:10]:
        print('   P', l[:120])


if __name__ == '__main__':
    main()
