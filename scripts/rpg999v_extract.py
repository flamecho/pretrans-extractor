# -*- coding: utf-8 -*-
"""RPG Maker VX Ace (RGSS3) 文本提取

容器：Game.rgss3a = RGSSAD v3
  [8] 'RGSSAD\\x00\\x03'  [u32 seed]  ->  索引 key = seed*9+3
  索引项：u32 offset / u32 size / u32 data_key / u32 name_len + name(cp932)  （全部 ^ 索引 key，按 4 字节循环）
  数据：逐 4 字节 word ^= data_key，data_key = data_key*7+3；长度非 4 倍数时尾字节用下一个 key 的低字节

成行（L0，RGSS3 语义）：
  code 101（文章の表示）开一个文本框；紧随的 401（文章行）是该框的显示行；
  Window_Base#process_normal_character 不自动折行（无 word wrap），行数＝401 行数；
  Window_Message 的窗口恰好 4 行（fitting_height(4)，line_height 24 → 内容高 96），
  本作全部 101 块 ≤4 行 ⇒ 无 need_new_page 自动分页 ⇒ 一框＝一次点击＝一页＝一行。单版。

  名札：本作无 name 类命令、无独立名字窗；说话人名是框内第一行 401（正文框内 ⇒ 上屏 ⇒ 保留），
  按 skill 口径去任何括弧、直接贴在台词前。

用法：
  python rpg999v_extract.py <Game.rgss3a> <out.txt> [--work <dir>] [--list-all]
"""
import io, os, re, struct, sys, zlib

# ---------------------------------------------------------------- RGSSAD v3
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


# ---------------------------------------------------------------- marshal
def load_rv2(path):
    from rubymarshal.reader import load as rload
    return rload(io.BytesIO(open(path, 'rb').read()))


def A(o, n):
    return o.attributes.get(n) if hasattr(o, 'attributes') else None


def dec(v):
    if isinstance(v, bytes):
        try:
            return v.decode('utf-8')
        except UnicodeDecodeError:
            return v.decode('cp932', 'replace')
    return str(v)


# ---------------------------------------------------------------- 清洗
ACTOR_NAME = {1: 'マフィン'}
CTRL = re.compile(r'\\[Cc]\[\d+\]|\\[Ii]\[\d+\]|\\[Ff]\[\d+\]|\\[Aa]\[\d+\]|'
                  r'\\[<>|!.^{}$]|\\G|<PICEX[0-9A-Za-z]+>|<[A-Za-z]+>')
NAME_MACRO = re.compile(r'\\[Nn]\[(\d+)\]')
VAR = re.compile(r'\\[Vv]\[(\d+)\]')


def clean(s):
    s = NAME_MACRO.sub(lambda m: ACTOR_NAME.get(int(m.group(1)), '〔未解析〕'), s)
    s = CTRL.sub('', s)
    s = VAR.sub('〔未解析〕', s)
    s = s.replace('\\', '')
    return s.strip(' \u3000\t')


QUOTE_START = '「『（［('


def split_name(rows):
    """框内第一行是否为说话人名：非空、无引号、短、下一行以引号/括号起。
    判据作用在「剥掉控制码之后」的文本上（`\\>`、`\\c[n]` 等不影响名札形态）。"""
    if len(rows) < 2:
        return None, rows
    head, nxt = rows[0].strip(' \u3000'), rows[1].lstrip(' \u3000')
    if not head or len(head) > 12:
        return None, rows
    if any(c in head for c in '「」『』（）()。、…！？"'):
        return None, rows
    if not nxt.startswith(tuple(QUOTE_START)):
        return None, rows
    return head, rows[1:]


# ---------------------------------------------------------------- 排除判据
DEBUG_EV = re.compile(r'デバック|デバッグ')
HELP_EV = re.compile(r'ヘルプ')
TUTORIAL_EV = re.compile(r'初回イベント$')
SYS_NOTICE = re.compile(
    r'を手に入れた！|を入手した！|を習得した！|このエリア内には|これ以上果実を持てません|'
    r'ＢＯＸが空になりました|活力が足りなかった|強さ：|が手に入れた')
SYS_LIST = re.compile(r'残り装備リスト|確率表記|結果内訳|当選数|ガチャ内訳|所持数：')
CREDIT = re.compile(r'999,Victory -Return-|効果音ラボ|地図から消えた村')
# 纯数值面板（无台词，只有变量/图标/计数）
STAT_PANEL = re.compile(r'遊んだ合計分間|BOX残り数|強さ：|残り装備')
# 商店/抽卡价目菜单（选项里带货币或抽卡名）
SHOP_CHOICE = re.compile(r'\\G|ガチャ|購入|売却')


# 教学说明：整块每行都以左对齐码 `\>` 起头，且讲操作/数值机制（作者写死的帮助文）
TUTORIAL_WORDS = re.compile(
    r'アクション|能力値|ゲージ|メニュー画面|画面右上|画面左下|バトル|騎乗|収穫|換金|餌|探知値|決定キー|'
    r'行動不能|復帰し|成功した人物|威厳|可憐|清廉')


def is_tutorial(rows):
    body = ' '.join(r for r in rows if r.strip())
    if not body:
        return False
    lines_ = [r for r in rows if r.strip()]
    if not all(r.lstrip().startswith('\\>') for r in lines_):
        return False
    return bool(TUTORIAL_WORDS.search(body))


def main():
    src, out = sys.argv[1], sys.argv[2]
    work = None
    for i, a in enumerate(sys.argv):
        if a == '--work':
            work = sys.argv[i + 1]
    list_all = '--list-all' in sys.argv
    work = work or os.path.join(os.path.dirname(out) or '.', '_work_rgss')
    os.makedirs(work, exist_ok=True)

    ents = read_rgssad(src, work)
    data = os.path.join(work, 'Data')

    maps = sorted(f for f in os.listdir(data)
                  if re.fullmatch(r'Map\d{3}\.rvdata2', f))
    infos = load_rv2(os.path.join(data, 'MapInfos.rvdata2'))
    name_of = {}
    for k, v in infos.items():
        name_of['Map%03d.rvdata2' % k] = dec(A(v, '@name') or '')

    items, excluded, lines = [], [], []

    def push(kind, path, rows, payload=None):
        items.append(dict(kind=kind, path=path, rows=rows, payload=payload))

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
                push('msg', path, rows, dict(face=dec(p[0]) if p else ''))
                continue
            if c == 105:
                rows = []
                i += 1
                while i < len(lst) and A(lst[i], '@code') == 405:
                    rows.append(dec(A(lst[i], '@parameters')[0]))
                    i += 1
                push('scroll', path, rows)
                continue
            if c == 102:
                p = A(lst[i], '@parameters') or [[], 0]
                push('choice', path, [dec(x) for x in p[0]])
            if c == 355:
                # プラグインコマンド：TMMRBT の頭上フキダシ mrbt(id, "…") も上屏文本
                buf = [dec(A(lst[i], '@parameters')[0])]
                j = i + 1
                while j < len(lst) and A(lst[j], '@code') == 655:
                    buf.append(dec(A(lst[j], '@parameters')[0]))
                    j += 1
                src_line = '\n'.join(buf)
                for m in re.finditer(r'mrbt\s*\(\s*-?\d+\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)', src_line):
                    push('bubble', path, [m.group(1)])
            i += 1

    for f in maps:
        if f == 'MapInfos.rvdata2':
            continue
        m = load_rv2(os.path.join(data, f))
        for eid, ev in (A(m, '@events') or {}).items():
            evname = dec(A(ev, '@name') or '')
            for pi, pg in enumerate(A(ev, '@pages') or []):
                path = '%s / %s (ev%03d p%d)' % (name_of.get(f, f), evname, eid, pi)
                walk(A(pg, '@list') or [], path)

    ce = load_rv2(os.path.join(data, 'CommonEvents.rvdata2'))
    for e in ce:
        if e is None:
            continue
        walk(A(e, '@list') or [], '共通: %s (CE%03d)' % (dec(A(e, '@name') or ''), A(e, '@id')))

    for t in load_rv2(os.path.join(data, 'Troops.rvdata2')):
        if t is None:
            continue
        for pi, pg in enumerate(A(t, '@pages') or []):
            walk(A(pg, '@list') or [], '戦闘: %s (Troop%d p%d)' % (dec(A(t, '@name')), A(t, '@id'), pi))

    # TMMRBT「村人のつぶやき」：角色头顶气泡的台词库（DATABASE["类型"] = [...]），
    # 由 <mrbt 类型> 注释放到事件上、start_mrbt 逐字画进 Sprite → 上屏。
    # 该库写在 Scripts.rvdata2 的某个脚本条目里（zlib 压缩），故逐条解压后匹配。
    sc_path = os.path.join(data, 'Scripts.rvdata2')
    if os.path.exists(sc_path):
        sb = open(sc_path, 'rb').read()
        off = 0
        while True:
            off = sb.find(b'\x78\x9c', off)
            if off < 0:
                break
            try:
                txt = zlib.decompressobj().decompress(sb[off:], 4 << 20).decode('utf-8')
            except zlib.error:
                off += 1
                continue
            if 'DATABASE' in txt and 'TMMRBT' in txt:
                for m in re.finditer(r'^\s*DATABASE\["([^"]+)"\]\s*=\s*\[(.*?)\]\s*$', txt, re.M):
                    for lit in re.findall(r"'((?:[^'\\]|\\.)*)'", m.group(2)):
                        push('bubble', '頭上つぶやき: %s' % m.group(1), [lit.replace("\\'", "'")])
            off += 1

    # ---------------- 收弃判定 ----------------
    for it in items:
        path, rows = it['path'], it['rows']
        reason = None
        if DEBUG_EV.search(path):
            reason = '调试菜单'
        elif HELP_EV.search(path):
            reason = '系统帮助'
        elif it['kind'] == 'msg' and is_tutorial(rows):
            reason = '教学说明'
        elif it['kind'] == 'msg' and SYS_NOTICE.search(''.join(rows)) and len(''.join(rows)) < 70:
            reason = '系统提示'
        elif it['kind'] == 'msg' and STAT_PANEL.search(''.join(rows)) and '\\v[' in ''.join(rows).lower():
            reason = '数值面板'
        elif it['kind'] == 'msg' and '<PICEX' in ''.join(rows):
            reason = '数值面板'      # 头顶浮动状态面板（<PICEX…> 是插件背景图占位）
        elif it['kind'] == 'msg' and '\\i[517]' in ''.join(rows):
            reason = '数值面板'      # ブグロフ音声确认框（含运行期数值变量）
        elif it['kind'] == 'scroll' and '<PICEX' in ''.join(rows) and STAT_PANEL.search(''.join(rows)):
            reason = '数值面板'
        elif it['kind'] == 'scroll' and ''.join(rows).lower().count('\\v[') >= 3:
            reason = '数值面板'
        elif it['kind'] == 'scroll' and (SYS_LIST.search(''.join(rows)) or CREDIT.search(''.join(rows))):
            reason = '系统一览/制作名单'
        elif it['kind'] == 'choice' and (HELP_EV.search(path) or DEBUG_EV.search(path)):
            reason = '系统菜单选项'
        elif it['kind'] == 'choice' and any(re.search(r'ガチャ|\\G|購入|売却', c) for c in rows):
            reason = '系统菜单选项'      # 商店/抽卡价目（系统 UI）
        elif it['kind'] == 'choice' and any(re.search(r'デバック|お金アイテムセット', c) for c in rows):
            reason = '调试菜单'
        elif it['kind'] == 'popup':
            reason = '地图标签(namepop)'
        elif it['kind'] == 'bubble' and re.search(r'キー|操作', ''.join(rows)):
            reason = '教学说明'      # 头顶气泡里的按键提示
        if reason:
            excluded.append((reason, it))
        else:
            lines.append(it)

    if list_all:
        for reason, it in excluded:
            print('[EXC] %-14s %s' % (reason, it['path']))
            print('        ', ' / '.join(x.strip() for x in it['rows'])[:160])
        return

    if '--dump-json' in sys.argv:
        import json
        p = sys.argv[sys.argv.index('--dump-json') + 1]
        json.dump({'kept': lines, 'excluded': [dict(reason=r, **it) for r, it in excluded]},
                  open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('dumped', p)

    # ---------------- 成行 ----------------
    out_lines = []
    for it in lines:
        rows = [clean(r) for r in it['rows']]
        if it['kind'] == 'choice':
            for c in rows:
                c = re.sub(r'\s*(en|if)\([^)]*\)', '', c).strip()
                if c:
                    out_lines.append(c)
            continue
        if it['kind'] == 'scroll':
            body = ''.join(r.strip(' \u3000') for r in rows if r.strip(' \u3000'))
            if body:
                out_lines.append(body)
            continue
        if it['kind'] == 'bubble':
            body = ''.join(r.strip(' \u3000') for r in rows if r.strip(' \u3000'))
            if body:
                out_lines.append(body)
            continue
        rows = [r for r in rows]
        nm, body_rows = split_name(rows)
        body = ''.join(r.strip(' \u3000') for r in body_rows if r.strip(' \u3000'))
        if not body:
            continue
        if nm:
            body = clean(nm) + body
        out_lines.append(body)

    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(out_lines) + '\n').encode('utf-8'))
    print('items', len(items), 'kept', len(lines), 'excluded', len(excluded))
    print('lines', len(out_lines), 'bytes', os.path.getsize(out))
    from collections import Counter
    print('excluded by reason', Counter(r for r, _ in excluded))


if __name__ == '__main__':
    main()
