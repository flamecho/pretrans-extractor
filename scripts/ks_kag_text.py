# -*- coding: utf-8 -*-
"""KAG3（KiriKiri）剧本 .ks -> 全文本（双版：段行＋合并行）

用法: python scripts/ks_kag_text.py <scenario 目录> <out.txt> [--mode dual|page] [--only REGEX]

判据全部取自**引擎自身的标签处理器**（`system/MainWindow.tjs` 的 getHandlers()，L0）：
  [p]  = showPageBreak   -> 清屏 + 等点击      => 一次点击、一个文本框
  [np] = 宏（macro.ks）= [p][cm][label][cm]     => 同上（本作用它当页界）
  [l]  = showLineBreak   -> 等点击但**不清屏**  => 框内再一次点击（B 类）
  [r]  = 改行（无点击；行满才触发自动翻页）
  [er] = current.clear()  清屏，无点击
  [hr] = 只写 history（バックログ），不影响正文
  [cm]/[ct] = 清消息层
  [waitclick] = 等点击（本作只出现在系统脚本）
  [名前 n="X"] = 宏：名字画在 **message1 层** 的独立窗（frame="ネーム_re"）
                 ⇒ 独立名字窗 ⇒ 名字**不加前缀**（口径「有独立名字窗才剔」）
  [link …]选项[endlink] = 选项文本（属性里可能含 `%[...]` 内嵌数组，需按深度配平找 `]`）

口径：一行 = 一次点击；页内 `[r]`/裸换行都是排版换行 ⇒ 合并。
双版 = 同页先列段行，再列合并行（单段页不重复）。
"""
import sys, os, re, argparse

TAG = re.compile(r'\[([^\[\]\s]+)')


def read_ks(p):
    """KiriKiri 的 .ks 可能**逐文件**用 cp932 或 UTF-16LE（带/不带 BOM）。

    2026-11-02 [JP]Cocoon：42 个剧情 .ks 里 **25 个 cp932 ＋ 17 个 UTF-16LE(BOM)**。
    ⛔ 先试 cp932 会「成功」——cp932 几乎任何字节对都能解出来 ⇒ 得到满篇乱码而不报错。
    判据顺序：BOM → NUL 比例 → cp932。
    """
    b = open(p, 'rb').read()
    if b[:2] == b'\xff\xfe':
        return b.decode('utf-16')          # 'utf-16' 会剥掉 BOM；'utf-16-le' 会把 U+FEFF 留在正文里
    if b[:3] == b'\xef\xbb\xbf':
        return b.decode('utf-8-sig')
    if b.count(0) > len(b) * 0.25:
        return b.decode('utf-16-le', 'replace')
    return b.decode('cp932', 'replace')


def split_tags(s):
    """把一行拆成 ('text', str) / ('tag', name, attrs) —— 处理 `%[...]` 嵌套的 `]`。"""
    out, i, n = [], 0, len(s)
    buf = ''
    while i < n:
        c = s[i]
        if c != '[':
            buf += c; i += 1; continue
        # 找配平的 ']'
        j, depth = i, 0
        while j < n:
            if s[j] == '[':
                depth += 1
            elif s[j] == ']':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= n:
            # 本行内配不平 ⇒ 源码写坏了（2026-11-02 [JP]Cocoon 1_バックボーン.ks L309：
            #   `[fadeinbgm storage="アラーム"[fadeinbgm storage="アラーム" time="1000"]`
            #   第一个 `]` 漏了）。KAG 解析器按**第一个 `]`** 收尾 ⇒ 照样当标签丢弃，
            #   绝不能把整段当正文（否则 `[fadeinbgm …` 会进成品）。
            k = s.find(']', i + 1)
            if k < 0:
                break                       # 整行无 `]`：当残缺标签丢弃
            j = k
        if buf:
            out.append(('text', buf)); buf = ''
        inner = s[i+1:j]
        m = re.match(r'([^\[\]\s=]+)', inner)
        out.append(('tag', m.group(1) if m else '', inner))
        i = j + 1
    if buf:
        out.append(('text', buf))
    return out


# ★ 两种宏定义写法都要认：`@macro name="X" … @endmacro`（Collision/CORE X 风格）与
#   `[macro name="X"] … [endmacro]`（本作 マクロ.ks 里 **17 个宏全是这种**）。
#   只认 `@macro` 时，`選択肢`（＝`[link …][graph …]`）不会被登记 ⇒ 选项文本会当正文并进台词。
# ★ `name="X" ]` 里引号与 `]` 之间可能有空格（`[JP]TrickCall` 的 `[macro name="クラト" ]` 就是），
#   所以 `\]?` 前要放 `\s*` 把空格吃掉，否则会把残留的 `]` 带进宏体，
#   导致 `macro_texts` 的「除名字外只含控制标签」判据失败、名字宏漏登（クラト/昴 漏名）。
MACRO_DEF = re.compile(r'[@\[]macro\s+name="?([^"\s\]]+)"?\s*\]?(.*?)[@\[]endmacro', re.S)
_EV_CACHE = {}


def load_macros(dirpath):
    """收集全部 `.ks` 里的 `@macro name="X" … @endmacro`（后定义不覆盖先定义）。"""
    macros = {}
    for f in os.listdir(dirpath):
        if not f.lower().endswith('.ks'):
            continue
        try:
            t = read_ks(os.path.join(dirpath, f))
        except Exception:
            continue
        for m in MACRO_DEF.finditer(t):
            macros.setdefault(m.group(1), m.group(2))
    return macros


def macro_texts(macros):
    """宏体里带**正文文本**的宏 → 该文本（如 FUSYRO 的 `[荻原真人]`＝`　荻原真人`＋改行）。

    判据：把宏体里的**控制标签**（nowait/endnowait/history/r/l/p/cm/ct/er/delay）剥掉后，
    剩下的仍是纯文本（不含 `[`/`]`）⇒ 这个宏就是「只往当前消息层写一段字」。
    有这种宏的作品（`EN` 2026-11-03 EveningGlow）：`[人名]` 把名字写进**正文框第一行**
    （不是独立名字窗：宏体是 `[nowait]　荻原真人[endnowait][r]`，`[SCN]` 里隐藏的是 message0），
    ⇒ 按口径「名札印在正文文本框内 ⇒ 保留并接在同行台词前」。
    """
    CTRL = re.compile(r'\[(?:nowait|endnowait|history[^\]]*|r|l|p|cm|ct|er|delay[^\]]*)\]')
    # ★ 名字宏（TrickCall 系写法）：宏体是 `[hr][label][ch text="名前"][r][playse…][eval…]`
    #   ⇒ 名字以 `[ch text=…]` 上屏（印在正文框第一行，**不是独立名字窗**）
    #   ⇒ 按口径「名札印在正文文本框内 ⇒ 保留并接在同行台词前」。
    #   判据：剥掉 `[ch text="…"]` 后，再把所有 `[…]` 标签剥掉，若什么都不剩，
    #   说明宏体除名字外只含控制/演出标签 ⇒ 是纯名字宏。
    #   2026-11-08 [JP]TrickCall：アベル/クラト/昴 等 200+ 个角色名宏全是这种写法。
    CH = re.compile(r'\[ch\s+text="([^"]*)"\]')
    # ★ AkaAka 名字宏（`macro_charaName.ks`）：`@macro name="【X】"`
    #   体：`[eval exp=%name|f.name='X'] … [nowait]　【[emb exp=f.name]】[endnowait] …`
    #   ⇒ 名字以 `【X】` 上屏（印在 message0 正文框第一行，**非独立名字窗**）
    #   ⇒ 按口径「名札印在正文文本框内 ⇒ 保留并接在同行台词前」。
    #   判据：体里含 `f.name='X'` 与 `[emb exp=f.name]` ⇒ 名字是 `X` ⇒ 输出 `【X】`。
    #   特例 `【ナレ】` 体里是 `[nowait]ナレーション[endnowait]`（无 f.name）→ 输出 `ナレーション`；
    #        `【空白】` 体里是 `[nowait]　　[endnowait]`（仅空格）→ 输出空（无名字）。
    NAME_EVAL = re.compile(r"f\.name\s*=\s*'([^']*)'")
    NOWAIT_TXT = re.compile(r'\[nowait\]\s*(.*?)\s*\[endnowait\]', re.S)
    # ★ 必须排除「宏体里是 TJS 代码/注释」的宏（`[systembutton]` 体里是
    #   `@eval exp="systembutton_object.setOptions(mp)"` ＋ `; mp が…` 注释）——
    #   它们剥完控制标签后**看起来也像纯文本**，误判会把脚本代码写进成品（本作实测 7 处、14 行）。
    BAD = set('@;{}\"\\<>=`')
    out = {}
    for name, body in (macros or {}).items():
        mc = CH.search(body)
        if mc:
            rest = CH.sub('', body)
            rest = re.sub(r'\[[^\]]*\]', '', rest).replace('\r', '').replace('\n', '').strip(' \t')
            if not rest:                      # 名字之外只含控制/演出标签 ⇒ 纯名字宏
                out[name] = mc.group(1)
                continue
        # ★ AkaAka 名字/旁白宏
        if 'emb exp=f.name' in body or 'emb exp="f.name"' in body:
            ne = NAME_EVAL.search(body)
            if ne:
                out[name] = '【' + ne.group(1) + '】'
                continue
        if name.startswith('【') and name.endswith('】'):
            m = NOWAIT_TXT.search(body)
            if m:
                txt = re.sub(r'\[[^\]]*\]', '', m.group(1)).replace('\r', '').replace('\n', '').strip()
                if txt:                        # 旁白 【ナレ】→ナレーション；【空白】→仅空格→不输出
                    out[name] = txt
                continue
        txt = CTRL.sub('', body)
        # ★ 宏体是多行源码 ⇒ 剥完控制标签会留下 `\r\n`；直接追加进正文会把一行拆成多行
        #   （2026-11-04 invisible sign 的 `[syun]`＝`\r\n\r\n【相沢　舜】\r\n\r\n`）。
        #   只去换行与首尾半角空白，**不动 U+3000**（`相沢　舜` 里的全角间隔是原文）。
        txt = txt.replace('\r', '').replace('\n', '').strip(' \t')
        if not txt or '[' in txt or ']' in txt:
            continue
        if any(c in BAD for c in txt):        # 代码/注释特征
            continue
        if all(ord(c) < 0x80 for c in txt if not c.isspace()):   # 必须含全角/日文字符
            continue
        out[name] = txt
    return out


def _ev_name(n, macros, stack):
    """把一个标签名翻成边界事件：'p'（页界）/ 'l'（段界）/ 'clear'（清屏⇒页界）/ 'link' / 'endlink'。"""
    if n in ('p', 'np'):
        return ('p',)
    if n == 'l':
        return ('l',)
    if n == 'r':
        return ()                      # 改行，不是边界
    # ★ 清屏类**必须作为事件带进宏里**：`plc`＝`[l]\ [label]\ [ct]\`（本作 4,117 次）——
    #   只认 `l` 会把「点击+清屏」误判成「段界」，整部会变成一屏到底。
    if n in ('ct', 'er', 'cm'):
        return ('clear',)
    if n == 'resetmsg':            # AkaAka：`@macro name="resetmsg"` 全消息层初始化・非表示 ⇒ 清屏＝页界
        return ('clear',)
    # ★ 选项也是宏：`選択肢`＝`[link …][graph …]`、`選択済み`＝`[endlink][resetfont]`。
    #   只展开 p/l 时这两个宏会被当成「无事件宏」整体吞掉 ⇒ 选项文本混进正文。
    if n == 'link':
        return ('link',)
    if n == 'endlink':
        return ('endlink',)
    if n in macros and n not in stack:
        return _ev_body(macros[n], macros, stack + (n,))
    return ()


def _ev_body(body, macros, stack):
    out = []
    for line in body.split('\n'):
        s = line.strip()
        if not s or s.startswith(';'):
            continue
        if s.startswith('@'):           # `@p` / `@label` 这种简写
            m = re.match(r'@(\S+)', s)
            if m:
                out.extend(_ev_name(m.group(1), macros, stack))
            continue
        for tok in split_tags(s):
            if tok[0] == 'tag':
                out.extend(_ev_name(tok[1], macros, stack))
    return tuple(out)


def macro_events(macros):
    """name → 该宏蕴含的边界事件序列（`p`＝页界 / `l`＝段界），递归展开＋缓存。"""
    if not macros:
        return {}
    _EV_CACHE.clear()
    for n in macros:
        _EV_CACHE[n] = _ev_name(n, macros, ())
    return _EV_CACHE


def parse(text, macro_ev=None, opt_locate=False, macro_txt=None, opt_map=None,
          name_window=False):
    """返回 (pages, opts, stats)。pages = [[seg, seg, ...], ...]

    name_window=True：跟踪 message1 独立名字窗状态（`[名前 n="X"]` 置名、`[名前なし]` 清名，
    跨页持续到被改/被清），在每页首段行前缀 `【X】`（整页行＝段行拼接，随之带名）。
    ⇒ 把被剔除的独立名字窗加回成品（用户口径：名札加回去）。
    """
    pages, opts = [], []   # opts = [(page_idx, text)]
    cur, segs = '', []
    in_link = False
    in_script = False
    current_name = [None]  # 名字窗当前显示的名字（跨页持久）
    st = dict(np=0, p=0, l=0, r=0, name=0, link=0, drop_tag=0, rawjoin=0, mac=0, clear_flush=0)


    def close_seg():
        nonlocal cur
        # ★ 段行**只裁行尾空白，保留行首空白**：`[l]　…` 的**全角空格是原文字符**
        #   （本作 1,643 个 `[l]` 里 471 个后接 `　`，是作者的行首縮排）⇒ 用 strip() 会删原文，
        #   还会让 `[l]　どう？[l]　どう？` 变成两行同文（品检误报「相邻重复行」）。
        # ★ 段末空白**必须保留**：本作 `[l]` 前的全角空格是分句间隔
        #   （`…うざいなお前！　[l]もう今日は帰る！`）⇒ rstrip 会让合并行丢掉这个间隔（实测丢 3 字）。
        #   段行末尾带一个空白不影响阅读，但合并行必须与原文一致。
        s = cur
        cur = ''
        if s.strip():
            segs.append(s)

    def close_page():
        nonlocal segs
        close_seg()
        # ★ 名字窗加回：当前名字窗有名字且本页有正文 ⇒ 首段行前缀 【名】
        if name_window and current_name[0] and segs:
            segs[0] = '【' + current_name[0] + '】' + segs[0]
        if segs:
            pages.append(segs)
        segs = []

    prev_r = False          # 同一段内上一个标签是否为 `[r]`（行首缩进判定用）
    for rawline in text.split('\n'):
        first_tok = True    # 本源码行的第一个文本 token
        line = rawline.rstrip('\r')
        s = line.strip()
        # ★ `[iscript]…[endscript]` / `@iscript…@endscript` 是 **TJS 代码块**，不是正文。
        #   2026-11-02 [JP]Cocoon 的 cg_mode*/exsystembutton 等系统脚本整篇都是它；
        #   若跟着剧情一起喂进来，代码会当正文写进成品（本作剧情文件里 0 处，属预防）。
        if in_script:
            if 'endscript' in s.lower():
                in_script = False
            continue
        if s.lower().startswith(('@iscript', '[iscript')):
            in_script = True
            continue
        if not s or s.startswith(('*', ';')):
            continue
        # ★ `--opt-locate`：选项文字与按钮分离 —— 行首 `[locate x=.. y=..]选项文字`，
        #   按钮另起一行 `[locate ...][button target=*xxx graphic=sys_sen]`。
        #   不特判会当正文累加，两个选项粘成 `多分そうだもう忘れた`（2026-11-03 ESCAPE 实测）。
        if opt_locate:
            m = re.match(r'^\[locate[^\]]*\]\s*([^\[\s][^\[]*)', s)
            if m:
                t = m.group(1).strip()
                if t:
                    opts.append((len(pages), t))
                    st['optchars'] = st.get('optchars', 0) + len(t)
                    st['link'] = st.get('link', 0) + 1
                continue
        if s.startswith('@'):
            # ★ KAG 的 `@cmd attrs` 是 `[cmd attrs]` 的简写。**不能整行跳过** ——
            #   否则 `@ple`／`@lr` 这类**宏调用**（体内含 `p`/`l`）会把页界/段界整个丢掉
            #   （2026-11-02 [JP]Collision×Collision 的 `[ple]` 虽写在行末，但 `@名前1` 等
            #   仍走这条；若将来有人把 `@ple` 单独写一行，跳过就会漏框）。
            line = '[' + s[1:].strip() + ']'
        for tok in split_tags(line):
            if tok[0] == 'text':
                # ★ KAG 的 `\`（行末）＝**改行**（排版换行，不点击）⇒ 直接去掉这个字符。
                #   本作几乎每行都以 `[plc]\` 收尾（4,117 处）；若把 `\` 当正文，成品会满篇反斜杠，
                #   当边界则整部被切碎。两者都错 —— 它只是「改行」。
                t = tok[1].replace('\r', '').replace('\\', '')
                # ★ 行首全角空格＝**排版缩进**（源码行首 / `[r]` 之后），合并进一行后是伪空格，
                #   与「框内换行一律合并」冲突 ⇒ 删掉。**只删 token 开头**，
                #   句中的全角间隔（`「なんだ？　和久井じゃないか」`）原样保留。
                #   2026-11-04 [JP]invisible sign -イス-：`[r]` 后 1,000+ 处 `　…` 缩进。
                if (first_tok or prev_r) and t[:1] == '\u3000':
                    t = t.lstrip('\u3000')
                first_tok = False
                if in_link:
                    if t.strip():
                        opts.append((len(pages), t.strip()))
                        st['optchars'] = st.get('optchars', 0) + len(t.strip())
                elif t.strip():
                    cur += t
                    # ★ 累计**真正进入正文的字符数**（含行首/行尾空白），用于交付时的闭合校验：
                    #   「段字 == 源码文本 token 之和」差 0 才算没丢字（2026-11-03 起各作都跑这条）。
                    st['chars'] = st.get('chars', 0) + len(t)
            else:
                name = tok[1]
                prev_r = (name == 'r')
                if macro_txt and name in macro_txt:
                    # 文本型宏（名字宏）：把它的字追加进当前段；**不 continue** ——
                    # 宏体里若还带 p/l（如 `[N・・・]`），边界事件必须照常执行（否则少 8 个页界）。
                    cur += macro_txt[name]
                    st['chars'] = st.get('chars', 0) + len(macro_txt[name])
                    st['mac_text'] = st.get('mac_text', 0) + 1
                ev = macro_ev.get(name) if macro_ev else None
                if ev:
                    # 宏调用：按体内**出现顺序**执行它蕴含的边界事件
                    st['mac'] += 1
                    for e in ev:
                        if e == 'p':
                            close_page()
                        elif e == 'l':
                            close_seg()
                        elif e == 'clear':
                            # 清屏 ⇒ 页界（已显示的字不可能与之后同屏）
                            close_page()
                        elif e == 'link':
                            in_link = True; st['link'] += 1
                        elif e == 'endlink':
                            in_link = False
                    continue
                if name in ('np',):
                    st['np'] += 1; close_page()
                elif name in ('sen-set', 'sen-set2'):
                    # ★ 图形按钮式选项（`[sen-set no1="s05_1a" no2="s05_1b" …]` 宏）：
                    #   宏体是 `[layopt layer=message0 visible=false]…[button graphic="%no1"]…[s]`
                    #   ⇒ 文字**不在脚本里**，只在 `others/<id>.png`（1350×38＝三态并排）。
                    #   映射由人工目视转写后经 `--opt-buttons` 传入（禁 OCR）。
                    #   2026-11-04 [JP]invisible sign -イス-：47 组 / 94 条。
                    if cur.strip():
                        close_page()
                    st['sen'] = st.get('sen', 0) + 1
                    if opt_map:
                        for k in ('no1', 'no2'):
                            m = re.search(r'\b' + k + r'\s*=\s*"([^"]*)"', tok[2])
                            if not m:
                                continue
                            key = m.group(1)
                            t = opt_map.get(key) or opt_map.get(key.rsplit('.', 1)[0])
                            if t:
                                opts.append((len(pages), t))
                                st['optchars'] = st.get('optchars', 0) + len(t)
                            else:
                                st['opt_miss'] = st.get('opt_miss', 0) + 1
                elif name == 'p':
                    st['p'] += 1; close_page()
                elif name == 'l':
                    st['l'] += 1; close_seg()
                elif name == 'r':
                    st['r'] += 1; prev_r = True
                elif name == 'waitclick':
                    close_seg()
                elif name == 'hg':
                    # ★ `[hg index="端末"]` 是**用語辞典的インラインリンク**（Dic.ks 的宏）：
                    #   宏体最后是 `[emb exp="mp.index"]` ⇒ **词面本身会上屏**，必须当正文收回。
                    #   2026-11-02 [JP]CORE X：12 处，漏了会得到「ベッドから降り、を開く」这种断句。
                    st['hg'] = st.get('hg', 0) + 1
                    m = re.search(r'index\s*=\s*"([^"]*)"', tok[2]) or \
                        re.search(r'index\s*=\s*([^\s\]]+)', tok[2])
                    if m:
                        if in_link:
                            opts.append((len(pages), m.group(1)))
                        else:
                            cur += m.group(1)
                elif name in ('名前', '名前なし'):
                    st['name'] += 1
                    if name_window:
                        if name == '名前なし':
                            current_name[0] = None
                        else:
                            m = re.search(r'n\s*=\s*"([^"]*)"', tok[2])
                            if m:
                                current_name[0] = m.group(1)
                elif name == 'link':
                    in_link = True; st['link'] += 1
                elif name == 'endlink':
                    in_link = False
                elif name in ('er', 'ct', 'cm'):
                    # ★ 清屏（`current.clear()` / `clearMessageLayers()`）不是点击，但**会抹掉已显示的文本**
                    #   ⇒ 清屏前累积的字与之后的字**不可能同时在同一屏**，必须先收行。
                    #   2026-11-02 [JP]Collision×Collision 的「閃光テキスト」块：
                    #     `[ct][delay speed=nowait][hfont]…◆　◆　◆[r]…[er]`
                    #   若不在 er 处收行，`◆　◆　◆` 会并进下一段地の文（实测第 1 行被污染）。
                    # ★ 无条件收页：清屏即页界（`close_page()` 内部对空 segs 不产空页）。
                    #   2026-11-04 [JP]invisible sign -イス-（本篇）：每段都是 `…[l][cm]` 紧邻，
                    #   若沿用「只有累积了字才收页」，`[l]` 已把 cur 清空 ⇒ `[cm]` 被吞掉，
                    #   整本 132 段会缩成 3 页、判成「一页多点击」⇒ 误出双版。
                    st['clear_flush'] += 1
                    close_page()
                elif name in ('s',):
                    # ★ `s`＝実行停止（MainWindow.tjs `s : function` → `return -1`）：
                    #   在此停下等用户动作（本作都写在选项按钮之后）。已累积的字**不可能**与之后的字同屏 ⇒ 收段。
                    if cur.strip():
                        st['stop_flush'] = st.get('stop_flush', 0) + 1
                        close_seg()
                elif name in ('indent', 'endindent', 'ruby', 'title'):
                    # indent/endindent＝首行縮排的**排版属性**（setIndent/resetIndent），不产生字符；
                    # ruby text="・"＝圏点（annotation 是「・」，基底字紧跟其后）⇒ 丢标签即保留基底；
                    # title＝setTitle(name)，写**窗口标题/栞ラベル**，不上画面 ⇒ 不收（章节名另记报告）。
                    st[name] = st.get(name, 0) + 1
                elif name in ('hr',
                              'wt', 'wq', 'ws', 'wp',
                              'wait', 'nowait', 'endnowait', 'eval', 'if',
                              'endif', 'history', 'position', 'layopt', 'current',
                              'backlay', 'trans', 'image', 'quake', 'playse',
                              'seopt', 'bgmopt', 'style', 'jump', 'call', 'return',
                              'fadeinbgm', 'fadeoutbgm', 'fadeinse', 'fadeoutse',
                              'clickskip', 'tempsave', 'tempload', 'mapimage',
                              'mapaction', 'mapdisable', 'disablestore', 'delay',
                              'rclick', 'eventcg', 'openvideo', 'playvideo', 'video',
                              'wv', 'stopse', 'stopbgm', 'playbgm', 'font', 'pimage',
                              'gotostart', 'nextskip', 'unlocklink', 'locksnapshot',
                              'unlocksnapshot', 'loadplugin', 'set', 'laycount',
                              'load', 'save', 'pimage', 'quake',
                              'メッセージ0消す', 'メッセージ0戻す', 'フェードアウト',
                              '人物左イン', '人物左差分', '人物右イン', '人物右差分',
                              '人物中央イン', '人物アウト1', '人物アウト2',
                              '画面切り替え', '上から下へ', '下から上へ', '画面',
                              'exsysbtopt', 'video', 'playvideo',
                              # 2026-11-03 [JP]Dream Dreamer：MainWindow.tjs 的处理器表里有、
                              # 但不产生字符也不点击的 6 个（wb=BGM フェード待ち 318 处、
                              # wf=効果音フェード待ち、stopvideo、snowinit/snowopt/snowuninit 下雪插件参数）
                              'wb', 'wf', 'stopvideo', 'snowinit', 'snowopt', 'snowuninit',
                              # 2026-11-03 [JP]EveningGlow（FUSYRO.MINI 宏体系，83 个宏）：
                              #   这些都是 `scenario/fusyro_macro.ks` 里定义的**排版/演出宏**，不产生字符；
                              #   SCN＝清屏（体内含 cm）、HNR＝改行（体内含 r）、O*/M*/K*＝立绘层、B/CTR/UTR＝backlay+trans。
                              'RTN', 'WTT', 'SCN', 'EVS', 'MES', 'MESC', 'MESCSET', 'HMES', 'HSP', 'HMAK', 'HHH', 'HLN', 'HLL', 'HNR', 'HNRS', 'HNRTN', 'HNRTNS', 'BGICTR', 'B', 'BGISET', 'flay0', 'flay1', 'flay2', 'flay6', 'BGIUTR', 'CTR', 'UTR', 'PLBGM', 'FIBGM', 'FOBGM', 'WBF', 'PLSE', 'FISE', 'STSE', 'FOSE', 'WSF', 'WSEP', 'EFE1', 'FM', 'FK', 'FO', 'O1', 'O2', 'O3', 'O4', 'O5', 'O6', 'O7', 'O8', 'O9', 'O10', 'OO6', 'OO7', 'K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7', 'KK5', 'KK6', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'MM5', 'BISEND', 'MTR', 'LPS1', 'LPS2', 'N'):

                    pass
                else:
                    st['drop_tag'] += 1
                    nm = st.setdefault('drop_names', {})
                    nm[name] = nm.get(name, 0) + 1
    close_page()
    return pages, opts, st


def render(pages, opts, mode):
    out = []
    multi = 0
    bypos = {}
    for pos, txt in opts:
        bypos.setdefault(pos, []).append(txt)
    for i, segs in enumerate(pages):
        out.extend(bypos.get(i, []))
        if len(segs) == 1 or mode == 'page':
            out.append(''.join(segs))
        else:
            multi += 1
            out.extend(segs)
            out.append(''.join(segs))
    out.extend(bypos.get(len(pages), []))
    return out, multi


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('out')
    ap.add_argument('--mode', choices=['dual', 'page'], default='dual')
    ap.add_argument('--only', default=r'^\d+_',
                    help='只收文件名匹配该正则的脚本（默认：数字开头的剧情文件）')
    ap.add_argument('--macros', choices=['auto', 'off'], default='auto',
                    help='auto=读全目录的 `@macro` 定义，把 `@ple`/`[lr]` 这类**宏调用**按体内 '
                         '`p`/`l` 展开成页界/段界（2026-11-02 Collision×Collision 必需）；off=不展开')
    ap.add_argument('--order', default='',
                    help='按子串给定的先后顺序排文件（逗号分隔；未列出的排后面，按文件名）')
    ap.add_argument('--exclude', default='',
                    help='排除文件名匹配该正则的脚本（逗号分隔多个）')
    ap.add_argument('--macro-text', choices=['auto', 'off'], default='auto',
                    help='auto=把「宏体剥掉控制标签后只剩纯文本」的宏展开成正文（名字宏）')
    ap.add_argument('--name-window', choices=['auto', 'off'], default='off',
                    help='auto=把 message1 独立名字窗（[名前 n="X"]/[名前なし]）加回成品：'
                         '每页首段行前缀【X】（整页行随之带名）；off=按口径剔除名字窗')
    ap.add_argument('--opt-locate', action='store_true',
                    help='选项文字与按钮分离：行首 [locate ...]文字 视为一条选项')
    ap.add_argument('--files', default='',
                    help='显式给出文件名（逗号分隔，**按此顺序**）；给了就不看 --only/--order。'
                         '2026-11-02 CORE X：文件名是 scenario1/T/T1/T2/E/E1/3P/3P1/3P2/K，'
                         '子串匹配会互相命中（`T` 命中 `T1`/`T2`），只能点名。')
    ap.add_argument('--opt-buttons', default='',
                    help='图形选项映射文件（`id<TAB>文字`，人工目视转写）。给了就把 '
                         '`[sen-set no1=… no2=…]` 的按钮图按 id 换成文字，按调用点顺序插入。')
    ap.add_argument('--exclude-opt', default='',
                    help='排除选项文本匹配该正则的「调试/非玩家」选项（如开发期 flag-label '
                         '选择肢）。仅过滤选项文本，**不影响**同文件里的正文与其他选项。')
    a = ap.parse_args()
    # 图形选项映射：`id<TAB>文字`（人工目视转写，禁 OCR）
    opt_map = {}
    if a.opt_buttons:
        for ln in open(a.opt_buttons, encoding='utf-8'):
            ln = ln.rstrip('\n')
            if not ln or ln.startswith('#') or '\t' not in ln:
                continue
            k, v = ln.split('\t', 1)
            opt_map[k.strip()] = v.strip()
    only = re.compile(a.only)
    excl = [re.compile(x) for x in a.exclude.split(',') if x]
    order = [x for x in a.order.split(',') if x]

    def key(f):
        for i, o in enumerate(order):
            if o in f:
                return (i, f)
        return (len(order), int(re.match(r'(\d+)', f).group(1)) if re.match(r'(\d+)', f) else 999, f)

    if a.files:
        want = [x if x.endswith('.ks') else x + '.ks' for x in a.files.split(',') if x]
        files = [f for f in want if os.path.exists(os.path.join(a.dir, f))]
        missing = [f for f in want if f not in files]
        if missing:
            print('!! 缺文件: %s' % ', '.join(missing), file=sys.stderr)
    else:
        files = sorted((f for f in os.listdir(a.dir)
                        if f.endswith('.ks') and only.match(f)
                        and not any(e.search(f) for e in excl)), key=key)
    _macros = load_macros(a.dir) if a.macros == 'auto' else {}
    macro_ev = macro_events(_macros) if _macros else {}
    macro_txt = macro_texts(_macros) if (_macros and a.macro_text == 'auto') else {}
    allpages, allopts = [], []
    tot = dict(np=0, p=0, l=0, r=0, name=0, link=0, drop_tag=0, mac=0, clear_flush=0, hg=0,
               chars=0, optchars=0)
    for f in files:
        pages, opts, st = parse(read_ks(os.path.join(a.dir, f)), macro_ev,
                                opt_locate=a.opt_locate, macro_txt=macro_txt,
                                opt_map=opt_map,
                                name_window=(a.name_window == 'auto'))
        # ★ 选项位置是**文件内**的 `len(pages)` ⇒ 合并多文件时必须加基准偏移，
        #   否则后几本的选项会全部插到前面的错误位置（2026-11-04 invisible sign 实测：
        #   `途方に暮れ…`（file06）被插到 day_1 的药选项后面）。
        allopts += [(pos + len(allpages), t) for pos, t in opts]
        allpages += pages
    # ★ 排除「调试/非玩家」选项（`--exclude-opt`）：仅过滤选项文本，
    #   正文与其他选项不受影响。例：AkaAka 的 `E_saga3_31c.ks` 在
    #   `@if f.playmode=='kobetsu.ks'` 分支内写了 `[link]フラグ：ミコトＥＤの場合[endlink]`
    #   这类开发期 flag-label 选择肢（非玩家文本），须剔除。
    if a.exclude_opt:
        rx = re.compile(a.exclude_opt)
        allopts = [(p, t) for p, t in allopts if not rx.search(t)]
        for k in tot:
            tot[k] += st.get(k, 0)
    lines, multi = render(allpages, allopts, a.mode)
    segs = sum(len(p) for p in allpages)
    print('文件=%d 页=%d 段=%d 多段页=%d 选项=%d 行=%d 字=%d | np=%d p=%d l=%d r=%d 宏=%d 名前=%d link=%d hg=%d 清屏收行=%d 未识别标签=%d | 段字=%d 选项字=%d'
          % (len(files), len(allpages), segs, multi, len(allopts), len(lines),
             sum(len(x) for x in lines), tot['np'], tot['p'], tot['l'], tot['r'], tot['mac'],
             tot['name'], tot['link'], tot['hg'], tot['clear_flush'], tot['drop_tag'],
             tot.get('chars', 0), tot.get('optchars', 0)), file=sys.stderr)
    open(a.out, 'w', encoding='utf-8-sig', newline='\n').write('\n'.join(lines) + '\n')
