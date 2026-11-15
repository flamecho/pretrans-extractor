# -*- coding: utf-8 -*-
"""[JP]エロトマニア（吉里吉里2 / KAG3，2016 女性向け18禁BL）文本提取驱动。

用法:
    python eroto_extract.py <解包后 ks 根目录> [输出.txt] [--verify]
    ks 根目录需含 scenario/ 与 macro/（由 unxp3.py 解出）

★ 控制符语义全部在本作原始脚本/引擎实证（最高约束）：

- **页界＝`[>]`**（6,614 次）。L0 定义在 `macro/macro2.ks`：
      [macro name=">"] [ws buf=… cond=…] [p][hr] … [cm][cf] [position layer=message4 visible=false] …
  即「待ち＋改ページ＋清屏」。本作 `[p]`/`[l]` 直接使用 **0 次**。
- **`[r]`＝软换行（合并）**。L0 引擎 `system/MainWindow.tjs:4681`：
      r : function(elm) { // 改行 … current.processReturn() … }   ← 无 conductor.wait
  对比 `p`(L4803「ページクリック待ち」→showPageBreak)、`l`(L4797「行クリック待ち」→showLineBreak)。
- **`[waitclick]`＝等点击不清屏**（`MainWindow.tjs:4996`「クリックを待つ」→waitClick）。
  本作 12 次全部紧跟 `[EV img=…]`（纯图展示），页内无第二段正文 ⇒ **不构成双版**。
- **双版判定**：按 `[>]` 切页后统计页内点击码（waitclick/ws/p/l/wp/pnt）＝17 页有点击，
  其中**页内 ≥2 段有正文者＝0**（唯一命中是 main.ks 的 `[eval]` 代码碎片，属系统）⇒ **单版**。
- **名札**：`@【X】` 宏 → `[名前欄]` 宏 → `[position layer=message4 …]` ⇒ **独立名字窗(message4)**。
  按 2026-11-08 修订「名札一律保留」⇒ 取宏体默认名并前缀到该页正文。
  默认名取自 macro.ks 的 `[else]X[endif]`（或纯文本行）；调用点 `name=？？？` 覆盖之（70 处）。
- **`[「]/[」]/[（]/[）]`** 是 macro2.ks 定义的**排版宏**，体里含真实括号字符 ⇒ 还原为 `「」 （）`。
- **`[はぁと]`** ＝ `[graph storage=テキスト_ハート alt=""]`（alt 为空）⇒ **无文字**，不造字（见报告）。
- **选项**：`[slctbtn str=…]` 37 条（回想分歧，玩家可见）＋ `[link …]文字[endlink]`（105.ks 的 OK/キャンセル）。
  `[button graphic=…]` 278 条**无 text/normal 属性**＝纯图按钮（探索点击区/メモ导航）⇒ 按「图片式无字选项跳过」。
"""
import os
import re
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))

# 阅读顺序（源：scenario/main.ks 的 storage 链：000 → 探索 101-107 → 结局 → 200 妄想）
ORDER = (['000.ks', '005a.ks'] +
         ['%d.ks' % i for i in range(100, 108)] + ['105a.ks'] +
         ['%03d.ks' % i for i in range(1, 11)] + ['200.ks'])
# 系统/UI/开发/片尾（不收）
SKIP = {'about.ks', 'endinglist.ks', 'first.ks', 'flag.ks', 'main.ks', 'main2.ks',
        'm_cg.ks', 'm_omake.ks', 'm_rp.ks', 'm_title.ks', 'memo.ks', 'memo_flag.ks',
        'memo_omake.ks', 'version.ks', 'テスト.ks', 'スタッフロール.ks',
        # 100.ks＝探索台词草稿库：**无任何脚本引用**（全库 grep `100.ks` 零命中），
        # 其 12 条台词的语音 ID(kyo_100_001..012) 与文字均已并入 101–107 正式版 ⇒ 未挂载草稿，排除。
        '100.ks'}

MACRO_DEF = re.compile(r'\[macro\s+name="?([^"\s\]]+)"?\s*\](.*?)\[endmacro', re.S)
# KAG 标签：属性值里可能含 `]`（如 [eval exp="sf.ED['x'] = 1"]）⇒ 引号内整体吃掉
TAG = re.compile(r'''\[((?:[^\]"']|"[^"]*"|'[^']*')*)\]|@((?:[^\[\n\r"']|"[^"]*"|'[^']*')+)''')
BRACKET_MACROS = {'「': '「', '」': '」', '（': '（', '）': '）'}


def read_ks(p):
    b = open(p, 'rb').read()
    if b[:2] in (b'\xff\xfe', b'\xfe\xff'):
        s = b.decode('utf-16', 'replace')
    else:
        s = b.decode('cp932', 'replace')
    # 源多为 CRLF；统一成 LF（成品要求纯 LF）
    return s.replace('\r\n', '\n').replace('\r', '\n')


def load_name_macros(macro_dir):
    """名札宏 → 默认名（L0：macro.ks 的 [else]X[endif] 或纯文本行）。"""
    names = {}
    for fn in sorted(os.listdir(macro_dir)):
        if not fn.lower().endswith('.ks'):
            continue
        t = read_ks(os.path.join(macro_dir, fn))
        for m in MACRO_DEF.finditer(t):
            nm, body = m.group(1), m.group(2)
            if not (nm.startswith('【') and nm.endswith('】')):
                continue
            if '[名前欄]' not in body:
                continue
            els = re.findall(r'\[else\]([^\[]+)\[endif\]', body)
            if els:
                names[nm] = els[0].strip()
            else:
                plain = [l.strip() for l in body.split('\n')
                         if l.strip() and not l.strip().startswith(('[', ';'))]
                if plain:
                    names[nm] = plain[0]
    return names


def strip_lines(t):
    """剥注释行 / iscript 块 / label 前缀。"""
    out = []
    in_script = False
    for L in t.split('\n'):
        s = L.lstrip()
        if s.startswith('[iscript]'):
            in_script = True
        if in_script:
            if s.startswith('[endscript]'):
                in_script = False
            continue
        if s.startswith(';'):
            continue
        L = re.sub(r'^\s*\*[^\s|]*\|?', '', L)
        out.append(L)
    return '\n'.join(out)


def parse(path, names, stat):
    t = strip_lines(read_ks(path))
    rows = []
    buf = []
    name = ''
    pos = 0
    skip_until = 0

    def flush():
        nonlocal buf, name
        s = ''.join(buf).strip(' \u3000\t\r\n')
        if s:
            rows.append(('line', (name + s) if name else s))
            stat['pages'] += 1
        elif name:
            stat['name_only'] += 1
        buf = []
        name = ''

    for m in TAG.finditer(t):
        if m.start() < skip_until:
            continue
        bare = t[pos:m.start()]
        if bare:
            # KAG 里脚本的物理换行/缩进不上屏（只有 [r] 才是显示换行）⇒ 去掉
            bare = bare.replace('\n', '').replace('\t', '')
            if bare:
                buf.append(bare)
        pos = m.end()
        raw = (m.group(1) if m.group(1) is not None else m.group(2) or '').strip()
        if not raw:
            continue
        head = raw.split()[0]
        # 页界
        if head == '>':
            flush()
            stat['page_code'] += 1
            continue
        # 软换行 ⇒ 合并（不插分隔符）
        if head == 'r':
            stat['soft_break'] += 1
            continue
        # 名札宏
        if head.startswith('【') and head.endswith('】'):
            nm = re.search(r'\bname\s*=\s*"?([^"\s]+)"?', raw)
            name = nm.group(1) if nm else names.get(head, '')
            stat['nameplate'] += 1
            continue
        # 排版括号宏 ⇒ 还原字符
        if head in BRACKET_MACROS and raw == head:
            buf.append(BRACKET_MACROS[head])
            stat['bracket'] += 1
            continue
        # 选项
        if head == 'slctbtn':
            sm = re.search(r'\bstr\s*=\s*"?([^"\]]+?)"?\s*(?:target|slct_|$)', raw)
            if sm:
                rows.append(('opt', sm.group(1).strip()))
                stat['opt'] += 1
            continue
        if head == 'link':
            # 取 [link …]文字[endlink] 的文字作选项，并把该段从正文流里吃掉
            # （否则 link 文字会同时留在 buf 里，与后续正文粘连）
            e = t.find('[endlink]', m.end())
            if e >= 0:
                txt = t[m.end():e].strip()
                if txt and not re.search(r'[<>]', txt):
                    rows.append(('opt', txt))
                    stat['opt'] += 1
                pos = e + len('[endlink]')
                # 跳过 finditer 已越过但落在 link 体内的匹配
                skip_until = pos
            continue
        # 振假名：[eruby text=よみ str=基底] —— `str` 是**上屏基底文字**，必须留；
        # `text` 是注音（ルビ），按口径剥注音留基底（L0：others/eruby.ks 的 initRuby(mp.text, mp.str)）
        if head == 'eruby':
            sm = re.search(r'\bstr\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s\]]+))', raw)
            if sm:
                base = sm.group(1) or sm.group(2) or sm.group(3) or ''
                buf.append(base)
                stat['eruby_base'] += 1
            else:
                stat['eruby_no_str'] += 1
            continue
        # 其余标签：不产生字符（资源/演出/系统）
        stat['other_tag'] += 1
    flush()
    return rows


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    root = sys.argv[1]
    verify = '--verify' in sys.argv
    args = [a for a in sys.argv[2:] if not a.startswith('--')]
    out = args[0] if args else os.path.join(os.path.dirname(HERE), '提取结果', '[JP]エロトマニア.txt')

    names = load_name_macros(os.path.join(root, 'macro'))
    print('名札宏 %d：%s' % (len(names), names))
    scen = os.path.join(root, 'scenario')
    have = set(os.listdir(scen))
    files = [f for f in ORDER if f in have and f not in SKIP]
    files += sorted(f for f in have if f.endswith('.ks') and f not in ORDER and f not in SKIP)
    print('收录 %d 本：%s' % (len(files), ', '.join(files)))
    print('排除 %d 本：%s' % (len(SKIP & have), ', '.join(sorted(SKIP & have))))

    stat = collections.Counter()
    rows = []
    for fn in files:
        for kind, txt in parse(os.path.join(scen, fn), names, stat):
            rows.append(txt)
    print('\n统计:', dict(stat))
    print('产行 %d（正文 %d ＋ 选项 %d）' % (len(rows), stat['pages'], stat['opt']))
    if verify:
        print('（--verify：未写文件）')
        return 0
    with open(out, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(rows) + '\n').encode('utf-8'))
    print('written', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
