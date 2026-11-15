"""NScripter `nscript.dat` → 双版对照文本（海色小夜曲ーウミイロセレナーデー）。

## 判据（L0：NScripter 文本语义；本作 `*define` 内无 `clickstr`/`linepage`，走默认）
- `nscript.dat` **整文件逐字节 XOR 0x84** ⇒ cp932（首行 `;mode800`）——与 2026-10-05「時函」同一方案。
- **一行正文 ＝ 一次点击**：行末 `@`＝显示并等待（不清框，内容累加）、`\\`＝显示并等待（翻页清框）、
  无标记＝显示并等待。⇒ 段行＝每条正文行。
- **页边界＝`\`**（翻页清框）⇒ 同一页内 ≥2 次点击时，先列段行、再列整页合并行（双版）。
- 行内控制：`br`＝框内空行（不收）、`/`（行末）＝取消行末换行、`_`＝取消紧接着一次等待 ⇒ 都剥掉。
- 命令行 vs 正文行：行首首字符 ASCII 字母/`_` ⇒ 命令；`*` 标签 / `;` 注释 / `~` / `:` / `"` 特殊；其余＝正文。
- **`if <条件> <正文>`**：剥掉条件表达式后若仍含日文 ⇒ 当作正文行（否则会静默丢分支台词）。
- 选项：`csel "A",*l1,"B",*l2` ⇒ 每个引号串一行。

用法：
  python scripts/nscripter_dat.py --dat <nscript.dat> --out 成品.txt [--raw raw.txt]
"""
import argparse
import io
import re
import sys

CMD = re.compile(r'[A-Za-z_]')
Q = re.compile(r'"([^"]{1,200})"')
CTRL = re.compile(r'(?:\\|@|br|_|/)\s*$')


def decrypt(path):
    d = io.open(path, 'rb').read()
    return bytes(b ^ 0x84 for b in d).decode('cp932', 'replace').replace('\r\n', '\n')


def strip_comment(s):
    out, q = [], False
    for ch in s:
        if ch == '"':
            q = not q
        if ch == ';' and not q:
            break
        out.append(ch)
    return ''.join(out)


def text_of(line):
    """返回 (是否正文, 文本, 是否页结束)。行首缩进（全角空格）保留。"""
    s = strip_comment(line).rstrip()
    if not s.strip():
        return False, '', False
    # 剥 NScripter 的 ! 控制命令（!dN 延迟 / !wN 等待），其后可能跟 inline 正文
    s = re.sub(r'!(?:d|w)\d+', '', s)
    if not s.strip():
        return False, '', False
    t = s.lstrip()
    # 纯颜色码 #rrggbb（setwindow/bg 等的颜色参数残留）非叙事文本
    if re.match(r'^#[0-9a-fA-F]{6}$', t):
        return False, '', False
    if t[0] in '*;~:"' or CMD.match(t):
        if t.startswith('if '):
            m = re.match(r'if\s+\S+\s+(.*)$', t)
            rest = m.group(1) if m else ''
            if re.search(r'[\u3041-\u3096\u30a1-\u30f6\u4e00-\u9fa5]', rest):
                return _text(rest)
        return False, '', False
    return _text(s)


def _text(s):
    page = s.endswith('\\')
    s = s.rstrip()
    while s.endswith(('@', '\\', '/', '_')):
        s = s[:-1].rstrip()
        if s.endswith('@') or s.endswith('\\') or s.endswith('/') or s.endswith('_'):
            continue
        break
    s = s.replace('br', '')
    s = s.rstrip()          # 保留行首全角空格缩进
    return True, s, page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dat', required=True)
    ap.add_argument('--out')
    ap.add_argument('--raw')
    ap.add_argument('--single', action='store_true')
    a = ap.parse_args()

    t = decrypt(a.dat)
    rows, opts, raw = [], [], []
    buf = []            # 当前页内的段行
    for ln in t.split('\n'):
        s = strip_comment(ln).strip()
        # 选项：csel / selgosub / selnum 的引号串
        m = re.match(r'(csel|selgosub|selnum)\s+(.*)$', s)
        items = []
        if m:
            items = Q.findall(m.group(2))
        elif s.startswith('"') and re.search(r'",\*', s):
            # 裸选项格式： "文字",*label, "文字",*label, ...（本作 Last trick）
            items = re.findall(r'"([^"]{1,200})",\*[A-Za-z0-9_]+', s)
        items = [x for x in items if re.search(r'[ぁ-んァ-ヴ一-龥]', x)]
        if items:
            for x in items:
                opts.append(x)
                raw.append('OPT\t' + x)
            continue
        ok, txt, page = text_of(ln)
        if not ok:
            continue
        raw.append('TXT\t%s\t%s' % ('P' if page else '-', txt))
        if not txt:
            if page and buf:
                rows.extend(buf)
                if not a.single and len(buf) >= 2:
                    rows.append(''.join(buf))
                buf = []
            continue
        buf.append(txt)
        if page:
            rows.extend(buf)
            if not a.single and len(buf) >= 2:
                rows.append(''.join(buf))
            buf = []
    if buf:
        rows.extend(buf)

    rows = [r for r in rows if r.strip()]
    out = rows + opts
    print('段行 %d / 选项 %d → 合计 %d' % (len(rows), len(opts), len(out)), file=sys.stderr)
    if a.raw:
        io.open(a.raw, 'w', encoding='utf-8', newline='\n').write('\n'.join(raw))
    if not a.out:
        return
    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for s in out:
            f.write(s + '\n')


if __name__ == '__main__':
    main()
