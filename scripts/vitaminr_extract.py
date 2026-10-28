#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VitaminR (PSP, ULJS00592, 2013-08-08, D3P/Rejet) 全文本提取。

源：CHD v5 → ISO → PSP_GAME/USRDIR/PACKFILE.BIN（53,508,096 B）
容器：`PacK` 头 ＋ 0x400 对齐的 **gzip 成员流**（4,256 个，逐个可独立解压）
      —— 头部表未解出（字段非 offset/size 直排），改用「扫 gzip magic ＋ 解压」直接取成员，
      成员顺序＝原打包顺序（脚本按 VTR_xx_nnn 递增，表内 index 低字节亦递增，互相印证）。
脚本：**.ald / .txt 明文 CP932 标签脚本**（不是字节码！），标签形如
      <pb>（换页＝一次点击）/ <wait key="true">（等待按键＝一次点击）/ <textbox visible="on|off">
      / <set position object> / <voice name> / <facechange> / <select><case value="选项"> / <tips>
      / <color> / <ruby value="读音">汉字</ruby> / <monologue> / <tkmstart|tkmcase|tkmend>（ツッコミ机关）
      / <jump file|block> / <block name> / <value name> / <if> / <movie> / <chaptertitle> …
文本行：行首 `＠<名>` ＝名前札（§0 丢弃）；`＠`+全角空格 ＝地の文（无名牌）；
      其余行＝正文/独白；行内软换行＝同一文本框内多行，合并。
主角宏：`%name%`（优那 18,305 处）/ `%family%`（西野 367 处）
      —— EBOOT.dec @0x2fdf6c 串池 `lastfirstname / lastfamilyname / 西野 / 優那`，
      包内 0010.bin ＝`lastfirstname,優那 / lastfamilyname,西野`（默认名＝西野 優那，vndb c29056 可改名）。
用語辞典：包内 0017.bin，CSV `10,<よみ>,<見出し>,<解説（<br>换行）>,辞書NNN` → 末尾 `【見出し】解説`。

用法：python scripts/vitaminr_extract.py <PACKFILE.BIN|pack目录> <out.txt> [--all]

输出：**默认只写 `X_全文本_双版对照.txt`**（唯一交付：同框先列各点击段、再列合并行 A,B,C,ABC）。
      `--all` 额外写点击版（<out.txt>）与 `_一框一行.txt`，仅供行数闭合自校验，不交付。

★ 双产出（skill `S6-lines-proof.md` §10）：`<pb>`＝换页（清框）、`<wait key="true">`＝框内等待按键（不清框、文字续加），
  两条都是一次点击 ⇒ 同时写两版：
    ① <out.txt>           一次点击 = 一行（两处都断）—— 主交付
    ② <out>_一框一行.txt   一个文本框 = 一行（只在 <pb> 断，<wait key> 处续写合并）
  两版同源同序、正文不改；行数差 = 框内等待的中缝数（本作 972）。
"""
import sys, os, re, zlib, json, glob

NAME = '優那'      # %name%  → 名
FAMILY = '西野'    # %family% → 姓

TAG_RUBY = re.compile(r'<ruby value="[^"]*">(.*?)</ruby>', re.S)
TAG_KEEP = re.compile(r'<(tips|color|objectcolor)\b[^>]*>(.*?)</\1>', re.S)
TAG_ANY = re.compile(r'<[^>]*>')
CASE_RE = re.compile(r'^\s*<case\s+value="([^"]*)"')


def strip_markup(s):
    """去标签：ruby 保留基底字，tips/color/objectcolor 保留内容，其余标签删除。"""
    s = TAG_RUBY.sub(r'\1', s)
    s = TAG_KEEP.sub(r'\2', s)
    s = s.replace('<br>', '')
    s = TAG_ANY.sub('', s)
    return s


def unpack_members(blob):
    """PacK 容器：扫 0x400 对齐的 gzip 成员，返回 [bytes]（按文件内出现顺序）。"""
    out = []
    pos = [m.start() for m in re.finditer(b'\x1f\x8b\x08\x00', blob)]
    for p in pos:
        o = zlib.decompressobj(31)
        out.append(o.decompress(blob[p:p + 8000000]))
    return out


def logical_lines(text):
    """按物理行切分，但把跨行的标签（`<facechange …` 下一行才 `>`）合并回一行。"""
    out, pend = [], None
    for raw in text.splitlines():
        cur = raw if pend is None else pend + raw
        if re.search(r'<[^>]*$', cur) and ('>' not in cur[cur.rfind('<'):]):
            pend = cur          # 标签未闭合 ⇒ 与下一行拼接
            continue
        pend = None
        out.append(cur)
    if pend is not None:
        out.append(pend)
    return out


def parse_boxes(data, names):
    """一个脚本 → **框列表**：每个框 = 若干「点击段」（<pb> 关框、<wait key> 只分段）。

    这样三种口径都由同一份结构派生，永远不会互相漂移：
      · 一次点击 = 一行 → 展平各框的所有段
      · 一个文本框 = 一行 → 各框的段直接拼接
      · 双版对照       → 逐框「先列各段、再列合并行」（仅当该框 >1 段时追加）
    """
    boxes, segs, buf = [], [], []

    def flush_seg():
        if buf:
            s = ''.join(buf).strip('　 \t\u3000')
            buf.clear()
            if s:
                segs.append(s)

    def close_box():
        flush_seg()
        if segs:
            boxes.append(list(segs))
            segs.clear()

    text = data.decode('cp932')
    for s in logical_lines(text):
        s = s.rstrip()
        if not s.strip():
            continue
        if s.lstrip().startswith('//'):
            continue
        m = CASE_RE.match(s)
        if m:                      # <select> 内选项：独立成行（各算一个单段框）
            close_box()
            opt = strip_markup(m.group(1)).strip()
            if opt:
                boxes.append([opt])
            continue
        if s.startswith('＠'):      # 名前札（＠/＠%name%/＠+全角空格）⇒ 丢弃，且视为新框
            nm = s[1:].strip('　 \t')
            if nm:
                names[nm] = names.get(nm, 0) + 1
            close_box()
            continue
        body = strip_markup(s)
        if not body.strip():
            if '<pb>' in s:
                close_box()        # 换页＝清框 ⇒ 关框
            elif 'wait key="true"' in s:
                flush_seg()        # 等待按键＝同框分段
            continue
        if body.lstrip().startswith('//'):
            continue
        buf.append(body.rstrip())
    close_box()
    return boxes


def flatten(boxes):
    """一次点击 = 一行"""
    return [seg for box in boxes for seg in box]


def merge_boxes(boxes):
    """一个文本框 = 一行"""
    return [''.join(box) for box in boxes]


def dual_view(boxes):
    """对照片：逐框「各段… ＋ 合并行」（单段框不重复输出）"""
    out = []
    for box in boxes:
        out.extend(box)
        if len(box) > 1:
            out.append(''.join(box))
    return out


def parse_script(data, names, flush_on=('page', 'wait')):
    """兼容旧接口：按 flush_on 直接出成品行。"""
    boxes = parse_boxes(data, names)
    return flatten(boxes) if 'wait' in flush_on else merge_boxes(boxes)


def parse_glossary(members):
    """0017.bin：`10,<よみ>,<見出し>,<解説>,辞書NNN` ⇒ [(見出し, 解説)]"""
    entries, seen = [], set()
    for data in members:
        try:
            text = data.decode('cp932')
        except UnicodeDecodeError:
            continue
        if '辞書' not in text or '<br>' not in text:
            continue
        for ln in text.splitlines():
            if ',辞書' not in ln:          # 首字段＝解说者 id（0〜10），不是常量
                continue
            rest = ln.rsplit(',', 1)[0]
            parts = rest.split(',', 3)
            if len(parts) < 4:
                continue
            head = parts[2].strip()
            desc = parts[3].replace('<br>', '').strip()
            if not head or not desc:
                continue
            key = (head, desc)
            if key in seen:
                continue
            seen.add(key)
            entries.append((head, desc))
    return entries


def main():
    src, out = sys.argv[1], sys.argv[2]
    if os.path.isdir(src):
        members = [open(f, 'rb').read() for f in sorted(glob.glob(os.path.join(src, '*.bin')))]
    else:
        members = unpack_members(open(src, 'rb').read())

    scripts, skipped = [], []
    for i, data in enumerate(members):
        if b'<pb>' not in data:
            continue
        head = data[:400].decode('cp932', 'replace')
        if ('サンプル' in head) or ('仮タイトル' in head) or ('テストブロック' in head):
            skipped.append(i)          # 開発用テスト（1613 仮タイトル / 1614 サンプルシナリオ / 1615 ツッコミサンプル）
            continue
        scripts.append((i, data))

    gloss = parse_glossary(members)
    gloss_lines = ['【%s】%s' % (h, d) for h, d in gloss]

    names, boxes = {}, []
    for i, data in scripts:
        boxes.extend(parse_boxes(data, names))

    def fin(lines):
        return [l.replace('%name%', NAME).replace('%family%', FAMILY) for l in lines]

    click_lines = fin(flatten(boxes) + gloss_lines)     # ① 一次点击 = 一行（主交付）
    page_lines = fin(merge_boxes(boxes) + gloss_lines)  # ② 一个文本框 = 一行
    dual_lines = fin(dual_view(boxes) + gloss_lines)    # ③ 双版对照：A,B,C,ABC

    # ★ 交付只出「对照版」一版（2026-10-19 用户定）；--all 才额外落点击版/一框行版（仅供校验）
    base = os.path.splitext(out)[0]
    targets = [(base + '_双版对照.txt', dual_lines)]
    if '--all' in sys.argv:
        targets = [(out, click_lines), (base + '_一框一行.txt', page_lines)] + targets
    for path, lines in targets:
        with open(path, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')

    multi = sum(1 for b in boxes if len(b) > 1)
    print('skipped', skipped)
    print('members', len(members), 'scripts', len(scripts), 'boxes', len(boxes),
          'click-lines', len(click_lines), 'page-lines', len(page_lines),
          'dual-lines', len(dual_lines), 'multi-seg boxes', multi,
          'glossary', len(gloss), 'nameplates', sum(names.values()), 'distinct names', len(names))


if __name__ == '__main__':
    main()
