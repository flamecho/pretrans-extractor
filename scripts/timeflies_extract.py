# -*- coding: utf-8 -*-
"""
[JP]Time Flies — KiriKiri KAG3 全文本提取（双版对照）

容器: data.xp3 (KiriKiri XP3；未加密；索引为尾部 zlib 流)
引擎: KiriKiri XP3 + KAG3

判据（skill S6-lines-dual §11 KAG3）:
- 页界 = `[p]`（清屏+等点击）与 `[SCN]`（= `[delay][cm][wait]`，ラベル変更時のクリア+待ち ⇒ 真·新框）
- 段界（框内点击）= `[l]`（showLineBreak→wait(click)；config chNonStopToPageBreak=false ⇒ 真会停）
  `[RTN]` 宏 = `[l][r]` ⇒ 展开为 `[l]`（点击）+ `[r]`（软换行，合并）
- `[r]` = processReturn（改行，无点击）⇒ 合并；`[s]`/`[delay]`/`[wait]`/`[jump]` = 控制标签，剥离
- 选项 = `[link target=*X]TEXT[endlink]`（本作 21 处选择 × 2 选项 = 42）；`target=*x` 且无文本为透明热区（本作无）
- 名窗: 无独立名字窗（主角「俺」第一人称）⇒ 无 `【名】`；正文内无名字前缀
- `▼…END` 仅出现在 `*label|caption` 行首（标签说明，非上屏文本）⇒ 整行丢弃

双版: 一框≥2 次点击 ⇒ 段行(A,B,…) ＋ 合并行(ABC)；单段页只出一行；选项各占一行（置于本页合并行之后，保证合并行紧邻段行）。
输出: UTF-8 BOM / 纯 LF / 一行＝一次点击。
"""
import zlib, struct, re, os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

XP3 = os.path.join(VNTRANS_HOME, '_work_timeflies/tfout/[JP]Time Flies/data.xp3')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]Time Flies.txt')

TAG_RE = re.compile(r'\[[^\]]*\]')           # 所有 KAG 标签（剥离用）
LINK_RE = re.compile(r'\[link[^]]*?\](.*?)\[endlink\]', re.S)
CMT_RE = re.compile(r'^\s*[;]')               # 行首注释
AT_RE = re.compile(r'^\s*@')                  # 行首 @ (TJS 代码)
LAB_RE = re.compile(r'^\s*\*')                # 行首 * (KAG 标签行, 含 *| / *label|caption)
JP = re.compile(r'[぀-ヿ㐀-鿿　-〿＀-￯]')
# 选项前缀判定：剥离标签后，只剩「全角字母/数字/甲乙… ＋ 冒号」⇒ 是 `Ａ：`/`Ｂ：` 这类选项字母前缀
PREFIX_RE = re.compile(r'^[　 \t]*[Ａ-Ｚ０-９甲乙丙丁一二三四五六七八九十][　 \t]*[：:]?[　 \t]*$')

# 页界（清屏+等点击）：`[p]` 与 `[scn]`（= `[delay][cm][wait]`，label 变更时清框+待ち ⇒ 新框）
PAGE_RE = re.compile(r'\[p\]', re.I)
SCN_RE = re.compile(r'\[scn\]', re.I)
# 段界（框内点击）：`[l]`（在 `[rtn]` 展开为 `[l]` 后统一定位）
L_RE = re.compile(r'\[l\]', re.I)
# `[rtn]` 宏 → `[l][r]`：展开为 `[l]`（框内点击）即可，`[r]` 为软换行合并（剥标签时去）
RTN_RE = re.compile(r'\[rtn\]', re.I)


def load_xp3(path):
    d = open(path, 'rb').read()
    n = len(d)
    tail = d[-60_000_000:]
    idx = None
    for pat in (b'\x78\x01', b'\x78\x9c', b'\x78\xda', b'\x78\x5e'):
        s = 0
        while True:
            i = tail.find(pat, s)
            if i < 0:
                break
            try:
                o = zlib.decompress(tail[i:i + 2_000_000])
            except Exception:
                o = None
            if o and o[:4] == b'File':
                idx = o
                break
            s = i + 1
        if idx:
            break
    if idx is None:
        raise RuntimeError('index not found')
    files = {}
    p = 0
    while p + 12 <= len(idx):
        if idx[p:p + 4] != b'File':
            break
        size = struct.unpack_from('<Q', idx, p + 4)[0]
        pl = idx[p + 12:p + 12 + size]
        name = None
        segs = []
        q = 0
        while q + 12 <= len(pl):
            t2 = pl[q:q + 4]
            s2 = struct.unpack_from('<Q', pl, q + 4)[0]
            sp = pl[q + 12:q + 12 + s2]
            if t2 == b'info':
                nl = struct.unpack_from('<H', sp, 20)[0]
                name = sp[22:22 + nl * 2].decode('utf-16-le', 'replace')
            elif t2 == b'segm':
                for i in range(0, len(sp), 28):
                    _, off, a, _b = struct.unpack_from('<IQQQ', sp, i)
                    segs.append((off, a))
            q += 12 + s2
        if name:
            files[name] = segs
        p += 12 + size
    return d, files


def read_file(d, segs):
    b = b''.join(d[o:o + s] for o, s in segs)
    try:
        b = zlib.decompress(b)
    except Exception:
        pass
    # 规范化换行：源 .ks 为 CRLF，split('\n') 会残留行尾 '\r'，须先清掉，
    # 否则 '\r' 会被写回正文造成 CRLF（违反纯 LF 交付规范）。
    return b.decode('cp932', 'replace').replace('\r\n', '\n').replace('\r', '\n')


def process_segment(raw):
    """处理一个段（两次点击之间）：抽取选项 + 剥标签 + 清空格；返回 (segs_texts, opt_texts)。"""
    segs, opts = [], []
    pos = 0
    for m in LINK_RE.finditer(raw):
        before = raw[pos:m.start()]
        inner = m.group(1)
        pos = m.end()
        before_clean = strip_tags(before).strip()
        inner_clean = strip_tags(inner).strip()
        if inner_clean:
            if before_clean and PREFIX_RE.match(before_clean):
                opt = before_clean + inner_clean
            elif before_clean:
                # 前缀是正文（非选项字母）⇒ 作为段文本，选项不带前缀
                if JP.search(before_clean):
                    segs.append(before_clean)
                opt = inner_clean
            else:
                opt = inner_clean
            if opt:
                opts.append(opt)
        elif before_clean and JP.search(before_clean):
            segs.append(before_clean)
    after = raw[pos:]
    after_clean = strip_tags(after).strip()
    if after_clean and JP.search(after_clean):
        segs.append(after_clean)
    return segs, opts


def strip_tags(text):
    return TAG_RE.sub('', text)


def clean_ws(text):
    # 折叠全/半角空白与多余空格（日文无词间空格）；去首尾空白
    text = text.replace('\u3000', ' ')          # 全角空格 → 半角（参与折叠）
    text = re.sub(r'[ \t\u3000]+', ' ', text)
    return text.strip()


def main():
    d, files = load_xp3(XP3)
    # 仅处理含真实 [p] 的脚本（其余 .ks 为系统/菜单，无真实对话框）
    pages_all = []
    for name in sorted(files):
        if not name.endswith('.ks'):
            continue
        text = read_file(d, files[name])
        if PAGE_RE.search(text) is None and SCN_RE.search(text) is None:
            continue
        # 1) 行级清理：去除注释/代码/标签行/空行；KAG 中裸物理换行＝续行（非上屏断行），
        #    故用 '' 拼接（不插换行）；真正的断行只来自 [l]/[p]/[scn]，[r] 与续行一律合并。
        kept = []
        for ln in text.split('\n'):
            st = ln.strip()
            if not st:
                continue
            if CMT_RE.match(ln) or AT_RE.match(ln) or LAB_RE.match(ln):
                continue
            kept.append(ln)
        joined = ''.join(kept)
        # 2) 展开 `[rtn]` → `[l]`（框内点击）
        joined = RTN_RE.sub('[l]', joined)
        # 3) 按页界 `[p]`/`[scn]` 切页
        #    合并相邻边界（[p] 后紧跟 [scn] 的 label 段记为空页，过滤）
        raw_pages = re.split(r'(?:\[p\]|\[scn\])', joined, flags=re.I)
        for rp in raw_pages:
            # 4) 页内按 `[l]` 切段（框内点击）
            raw_segs = L_RE.split(rp)
            seg_texts, opt_texts = [], []
            for rs in raw_segs:
                st, ot = process_segment(rs)
                for s in st:
                    c = clean_ws(s)
                    if c and JP.search(c):
                        seg_texts.append(c)
                for o in ot:
                    co = clean_ws(o)
                    if co and JP.search(co):
                        opt_texts.append(co)
            pages_all.append((seg_texts, opt_texts))

    # 5) 发射：每页 → 段行(依次) ＋ (段≥2 则合并行) ＋ 选项行（置于合并行之后，保证合并行紧邻段行）
    lines = []
    n_pages = 0
    n_multi = 0
    n_merged = 0
    n_opts = 0
    for seg_texts, opt_texts in pages_all:
        if not seg_texts and not opt_texts:
            continue  # 空页（label 段等）丢弃
        n_pages += 1
        for s in seg_texts:
            lines.append(s)
        if len(seg_texts) >= 2:
            merged = ''.join(seg_texts)
            lines.append(merged)
            n_multi += 1
            n_merged += 1
        for o in opt_texts:
            lines.append(o)
            n_opts += 1

    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\ufeff')
        f.write('\n'.join(lines))
        f.write('\n')
    print('pages(real):', n_pages)
    print('multi-seg pages:', n_multi, ' merged lines:', n_merged)
    print('options:', n_opts)
    print('total lines:', len(lines))


if __name__ == '__main__':
    main()
