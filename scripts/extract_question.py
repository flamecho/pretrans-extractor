# -*- coding: utf-8 -*-
"""[JP]Question (KiriKiri/KAG3) 全文本提取 —— 专用提取器（S6）

KAG3 语法要点（本作实测）：
  * label          -> 标签行（整行丢弃，含 `*名|开发者备注`）
  ; comment        -> 注释行（整行丢弃）
  @command ...     -> at 命令（到行尾，剥离；@ 前若有文本保留）
  \\                -> 行尾续行符（全部删除，非上屏文本）
  [tag ...]        -> 内联标签（剥标签留文本；引号内 [] 不误判）
  [link]...[endlink] -> 菜单/载体导航（其文本非剧情，整段丢弃）
  [ruby text=読]基  -> 自闭合振假名，留基字（読音丢弃）

断框判据（全部 L0，读 system/MainWindow.tjs + マクロ.ks + 实测上下文）：
  plc  = [l][label][ct]            -> 页界（一次点击 + 清屏 = 一框）
  ct/cm/er/s                     -> 页界
  [l] 后跟 quiz(backlay / current layer=message1 / 選択肢始め / クイズ選択肢)
                                  -> 提问框页界（切到 message1 答题层）
  [l] 其他（同框续写 message0）      -> 段界（双版：同页二次点击）
  r / 間 / wt / wf / wait / 换行    -> 合并（框内/停顿，无点击）
  [名前]/[名前大] ... [名後]/[名後大] -> 内联名札（message0 同层）→ 接在同行台词前
  [クイズ選択肢 ...]TEXT[選択済み]    -> クイズ选项（文字），按序单行

交付：双版（同页≥2 点击 -> 先列段行，再列合并行）；名札内联接同行；选项单行按序。
UTF-8 BOM / LF / 0 CR。
"""
import re, os

SCN = '_work_question/scenario/'
OUT = '提取结果/[JP]Question.txt'

# 正文文件（按游戏内出现顺序；回想/エンディングリスト 为回想/结局载体 -> 排除；系统脚本排除）
MAIN_FILES = [
    'scenario__オープニング.ks', 'scenario__ステージ01.ks', 'scenario__ステージ02.ks',
    'scenario__ステージ03.ks', 'scenario__ステージ04.ks', 'scenario__ステージ05.ks',
    'scenario__ステージ06.ks', 'scenario__おまけ.ks',
]
PAGE_BREAK = {'plc', 'ct', 'cm', 'er', 's'}
NAME_OPEN = {'名前', '名前大'}
NAME_CLOSE = {'名後', '名後大'}


def read_ks(path):
    b = open(path, 'rb').read()
    if b[:2] == b'\xff\xfe':
        return b.decode('utf-16')
    if b[:3] == b'\xef\xbb\xbf':
        return b.decode('utf-8-sig')
    if b.count(0) > len(b) * 0.25:
        return b.decode('utf-16-le', 'replace')
    return b.decode('cp932', 'replace')


def preprocess(text):
    """丢弃 ; 注释行 / * 标签行，剥离 @ 命令到行尾，删除所有反斜杠续行符。返回拼接文本。"""
    out = []
    for line in text.split('\n'):
        ls = line.lstrip()
        if ls.startswith(';') or ls.startswith('*'):
            continue
        at = line.find('@')
        if at != -1:
            line = line[:at]
        out.append(line)
    text = '\n'.join(out)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\\\n', '\n', text)   # 只去除行尾续行符；保留串内转义 \' \"
    return text


def tokenize(s):
    """切成 ('tag', name, inner) / ('text', str)。

    KAG3 引号/括号处理规则（本作实测需要）：
      - " 或 ' 切换引号态；串内转义引号 \\' \\" 跳过不切换；
      - ] 仅在不处于引号态时关标签（引号内的 [storage:...] 之类 ] 当字面）；
      - 源文件偶发畸形（如 cond="kag.skipMode<=1"] 缺闭合引号），若跑到行尾仍处
        于未终止引号中，则强制闭合引号并按末 ] 关标签，不吞段。
    """
    toks = []
    i, n = 0, len(s)
    while i < n:
        if s[i] == '[':
            j, d, qs, q = i + 1, 1, False, ''
            while j < n:
                c = s[j]
                if c == '\\' and j + 1 < n and s[j + 1] in ('"', "'"):
                    j += 2; continue          # 串内转义引号 \' \"
                if c == ']':
                    if not qs:
                        d -= 1
                        if d == 0:
                            j += 1; break
                    j += 1; continue
                if qs:
                    if c == q:
                        qs = False
                        if j + 1 < n and s[j + 1] == q:   # 双引号 "" 当作单次闭合，跳过第二个（不重开）
                            j += 1
                    j += 1; continue
                if c == '"' or c == "'":
                    qs = True; q = c; j += 1; continue
                if c == '[':
                    d += 1
                j += 1
            if j >= n and qs:                 # 畸形：行尾仍处未终止引号 -> 强制闭合
                qs = False
                if d > 0:
                    d -= 1
            closed = (d == 0)
            if not closed:
                toks.append(('text', '['))
                i = i + 1
                continue
            inner = s[i + 1:j - 1]
            m = re.match(r'\s*([^\s\]]+)', inner)
            toks.append(('tag', m.group(1) if m else '', inner))
            i = j
        else:
            k = s.find('[', i)
            if k < 0:
                k = n
            toks.append(('text', s[i:k]))
            i = k
    return toks


def parse_attrs(inner):
    d = {}
    for m in re.finditer(r'(\w+)\s*=\s*("([^"]*)"|\'([^\']*)\'|(\S+))', inner):
        d[m.group(1)] = m.group(3) or m.group(4) or m.group(5) or ''
    return d


def is_quiz_break(toks, idx):
    """[l] 之后 30 个 token 内是否出现 quiz 信号。"""
    for t in toks[idx + 1:idx + 31]:
        if t[0] != 'tag':
            continue
        if t[1] in ('backlay', '選択肢始め', 'クイズ選択肢'):
            return True
        if t[1] == 'current':
            a = parse_attrs(t[2])
            if 'layer' in a and 'message1' in a['layer']:
                return True
    return False


def extract_file(path, toks):
    out = []
    segs = ['']            # 当前页的各段（按 [l] 段界切分）
    pending_name = None    # 待接到下一段文本前的内联名
    capture = None         # None / 'name' / 'opt'
    capbuf = ''
    cur_opts = []          # 当前提问框收集到的选项
    in_link = False        # [link]...[endlink] 内 -> 文本丢弃

    def flush_opts():
        nonlocal cur_opts
        for o in cur_opts:
            out.append(o)
        cur_opts = []

    def new_page():
        nonlocal segs
        seglist = [re.sub(r'\s+', '', x) for x in segs if x.strip()]
        if seglist:
            if len(seglist) == 1:
                out.append(seglist[0])
            else:
                for s in seglist:
                    out.append(s)
                out.append(''.join(seglist))
        segs = ['']

    def add_text(t):
        nonlocal segs, pending_name, capture, capbuf
        if capture == 'name':
            capbuf += t; return
        if capture == 'opt':
            capbuf += t; return
        if in_link:
            return
        if pending_name is not None:
            segs[-1] += pending_name + t
            pending_name = None
        else:
            segs[-1] += t

    for idx, t in enumerate(toks):
        if t[0] == 'text':
            add_text(t[1])
            continue
        nm = t[1]
        inner = t[2]
        if nm in NAME_OPEN:
            capture, capbuf = 'name', ''
            continue
        if nm in NAME_CLOSE:
            capture = None
            pending_name = capbuf.strip()
            capbuf = ''
            continue
        if nm == 'link' or nm == '/link' or nm == 'endlink':
            in_link = (nm != 'endlink' and nm != '/link')
            continue
        if nm == 'クイズ選択肢':
            capture, capbuf = 'opt', ''
            continue
        if nm == '選択済み':
            capture = None
            opt = re.sub(r'\s+', '', capbuf)
            if opt:
                cur_opts.append(opt)
            capbuf = ''
            continue
        if nm == '選択肢終わり':
            flush_opts()
            continue
        if nm in PAGE_BREAK:
            new_page(); flush_opts()
            continue
        if nm == 'l':
            if is_quiz_break(toks, idx):
                new_page(); flush_opts()
            else:
                segs.append('')
            continue
        if nm == 'ch':
            a = parse_attrs(inner)
            if 'text' in a:
                add_text(a['text'])
            continue
        # 其余标签（r/間/wt/wf/wait/ruby/eval/emb/jump/rclick/delay/record/history/
        # image/backlay/trans/lay*/position/locate/current/clickskip/font/deffont/
        # defstyle/resetfont/fade*/playse/stopse/nowait/endnowait/style/layopt/oldMovie*
        # iscript/endscript/if/endif/macro/endmacro/return/label/er 等）= 剥除
        continue
    new_page(); flush_opts()
    return out


def main():
    os.makedirs('提取结果', exist_ok=True)
    all_out = []
    stats = []
    for f in MAIN_FILES:
        raw = preprocess(read_ks(SCN + f))
        toks = tokenize(raw)
        lines = extract_file(f, toks)
        stats.append((f, len(lines)))
        all_out.extend(lines)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        for ln in all_out:
            fh.write(ln + '\n')
    print('files:', len(MAIN_FILES))
    for f, n in stats:
        print('  %-28s %d lines' % (f, n))
    print('TOTAL lines:', len(all_out))


if __name__ == '__main__':
    main()
