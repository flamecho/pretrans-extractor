# -*- coding: utf-8 -*-
"""DesperaDrops (NS-JP) 全文本提取 —— Utage 引擎 / .book 二进制

链路：NSP(PFS0) → Program NCA (Titlekey crypto) → RomFS
      → StreamingAssets/7Drops/Switch/7drops.scenarios.asset (UnityFS bundle)
      → MonoBehaviour(Utage.AdvImportBook) → .book 记录 → 正文
      → Boot.chapter (AdvChapterData)：用語辞典 Words 表 + 剧情流程图（定序）

用法:
  python outils/desperadrops_extract.py <patch.asset> <base.asset> <out.txt>
"""
import sys, os, struct, re, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import UnityPy
from dd_utage import parse_book

NAME_DEFAULT = 'ミカ'

# ---- 收录的 book（按剧情流程图定序，未匹配者按后备序） ----
INCLUDE = [
    'Prologue', 'Chapter1', 'Chapter2', 'Chapter3', 'Chapter4', 'Chapter5',
    'Chapter6', 'Chapter7', 'Chapter8', 'Chapter9', 'Chapter10', 'Chapter11',
    'Chapter12', 'Mission1', 'Mission2', 'Mission3', 'Mission4',
    'Ash_13', 'Ash_14', 'Ash_15', 'Ash_16', 'Ash_Happy', 'Ash_Bad',
    'Hamiel_13', 'Hamiel_14', 'Hamiel_15', 'Hamiel_16', 'Hamiel_Happy', 'Hamiel_Bad',
    'Gib_13', 'Gib_14', 'Gib_15', 'Gib_16', 'Gib_Happy', 'Gib_Bad',
    'Ramie_13', 'Ramie_14', 'Ramie_15', 'Ramie_16', 'Ramie_Happy', 'Ramie_Bad',
    'Camu_13', 'Camu_14', 'Camu_15', 'Camu_16', 'Camu_Happy', 'Camu_Bad',
    'Sally_13', 'Sally_14', 'Sally_15', 'Sally_16', 'Sally_Happy', 'Sally_Bad',
    'True_13', 'True_14', 'True_15', 'True_16',
    'DLC_01_Ash', 'DLC_02_Hamiel', 'DLC_03_Gib', 'DLC_04_Ramie',
    'DLC_05_Camu', 'DLC_06_Sally', 'DLC_07_True',
]
# 不收：Test* / *Demo* / EndRoll* / SceneChange(系统跳转) / SceneScenario(场景回想)
#       / StartGame(开机注意) / 7Drops(入口) / LabelLink* / Gallery / Words / Flow
#       / ScenarioData / UiText / Voice


def load_books(path):
    env = UnityPy.load(path)
    out = {}
    chap = None
    for o in env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        nm = o.peek_name()
        raw = o.get_raw_data()
        if nm == 'Boot.chapter':
            chap = raw
        elif nm.endswith('.book'):
            out[nm[:-5]] = raw
    return out, chap


def u32(b, p):
    return struct.unpack_from('<I', b, p)[0]


def read_str(b, p):
    n = u32(b, p)
    p += 4
    if n > 100000:
        raise ValueError('bad str len')
    s = b[p:p + n].decode('utf-8')
    p += n
    if n % 4:
        p += 4 - n % 4
    return s, p


def sheet_at(raw, start, limit_row=8000):
    """按行记录格式 [idx][cnt][cells][empty][comment] 顺序读到表尾。"""
    rows = []
    p = start
    while True:
        try:
            idx, cnt = u32(raw, p), u32(raw, p + 4)
        except Exception:
            break
        if cnt > 25 or idx > limit_row:
            break
        q = p + 8
        cells = []
        try:
            for _ in range(cnt):
                s, q = read_str(raw, q)
                cells.append(s)
            a, b = u32(raw, q), u32(raw, q + 4)
        except Exception:
            break
        if a > 1 or b > 1:
            break
        rows.append(cells)
        p = q + 8
    return rows


def find_sheet(raw, probe_bytes, limit_row=8000):
    i = raw.find(probe_bytes)
    if i < 0:
        return None
    return sheet_at(raw, i, limit_row)


def ruby_strip(t):
    """漢字《よみ》/カナ《語》 → 只留底字（ルビのみ剥がす）"""
    return re.sub('《[^》]*》', '', t)


def clean(t):
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    t = re.sub('\n[ \u3000]+', '', t)      # 框内软换行 + 行首全角缩进 → 合并
    t = t.replace('\n', '')
    t = ruby_strip(t)
    t = t.replace('[UserName]', NAME_DEFAULT)
    t = t.replace('\u00a0', '\u3000')      # NBSP → 全角空格（源数据 1 处排版字符）
    return t.strip(' \u3000\t')


def main():
    patch, base, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    books, chap = load_books(patch)
    if chap is None:
        raise SystemExit('Boot.chapter not found')

    # ---- 用語辞典（Words 表）----
    words = find_sheet(chap, struct.pack('<II', 0, 11) + struct.pack('<I', 6) + b'Number')
    dic = []
    if words:
        hdr = words[0]
        ix = {k: i for i, k in enumerate(hdr)}
        cur_title = ''
        for r in words[1:]:
            def g(k):
                i = ix.get(k)
                return r[i] if i is not None and i < len(r) else ''
            if g('Number') and g('Title'):
                cur_title = g('Title')
            body = clean(g('Text'))
            if not body:
                continue
            who = g('CharaIcon').strip()
            if g('Title'):
                dic.append('【%s】%s' % (clean(g('Title')), body))
            elif cur_title:
                dic.append('【%s（%s）】%s' % (clean(cur_title), who, body) if who
                           else '【%s】%s' % (clean(cur_title), body))
            else:
                dic.append(body)

    # ---- 剧情顺序：用流程图 ScenarioLabel→chapter 的行序 ----
    flow = find_sheet(chap, struct.pack('<II', 0, 12) + struct.pack('<I', 13) + b'ScenarioLabel'
                      + b'\x00' * 3 + struct.pack('<I', 7) + b'chapter')
    order = {}
    if flow:
        for i, r in enumerate(flow):
            if r:
                lab = r[0].strip()
                if lab.startswith('*') and lab not in order:
                    order[lab] = i
    first = {}
    for nm, raw in books.items():
        try:
            b = parse_book(raw)
        except Exception:
            continue
        for s in b['sheets']:
            for r in s['rows']:
                if r['cells']:
                    lab = r['cells'][0].strip()
                    if lab.startswith('*') and lab in order:
                        first[nm] = min(first.get(nm, 1 << 30), order[lab])

    seq = [n for n in INCLUDE if n in books]
    seq.sort(key=lambda n: (first.get(n, 1 << 29), INCLUDE.index(n)))

    lines = []
    stat = []
    for nm in seq:
        b = parse_book(books[nm])
        cnt = 0
        for s in b['sheets']:
            hdr = None
            for r in s['rows']:
                if r['index'] == s['header_row']:
                    hdr = r['cells']
                    break
            if not hdr or 'Text' not in hdr:
                continue
            ci = hdr.index('Command') if 'Command' in hdr else None
            ti = hdr.index('Text')
            for r in s['rows']:
                c = r['cells']
                if ti >= len(c):
                    continue
                cmd = c[ci] if ci is not None and ci < len(c) else ''
                if cmd in ('NameU', 'Command'):
                    continue          # NameU=与 NameD 同文的可变名版本；Command=表头行
                t = clean(c[ti])
                if not t:
                    continue
                lines.append(t)
                cnt += 1
        stat.append((nm, cnt))

    lines += dic
    with io.open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('story=%d dic=%d total=%d' % (sum(c for _, c in stat), len(dic), len(lines)))
    for nm, c in stat:
        print('  %-16s %5d' % (nm, c))


if __name__ == '__main__':
    main()
