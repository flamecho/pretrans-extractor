# -*- coding: utf-8 -*-
"""FD『二世の契り 想い出の先へ』(PSP-JP, Otomate, STCM2L) 全文本提取 —— 泛化版。

容器链: ISO9660 -> PSP_GAME/USRDIR/INSTALL.cpk (明文 CRI CPK) -> script/*
引擎: STCM2L (与本体同引擎，格式已实证)

记录结构 (复用 nisenochigiri_extract.units/recs/clean):
  unit = [u32 size][payload]; payload 内文本记录 = [0][L/4][1][L][cp932] (k=12)
  若干记录为 k=24 (选项)。

显示指令 (k=12) 实证结论:
  TEXT_CONT = {0xd2}              框内续行(合并同一文本框)
  TEXT_END  = {0xd3,0x05,0x9a,0x6e,0x6f,0xd4,0x1,0xe7,0x34,0x12b,0x77,0x13,0x41dc,0x35}
                                    框末点击(结束本文本框)；其中 0x05/0x9a/0x34 等为
                                    与 0xd3 同义的 "A/B 显示变体"，文本完全相同 -> 相邻去重。
  NAME_OP   = {0x7a,0x1dd,0x1d3}  名字窗/名表 op (剔除)
  控制/系统 = 0x33(処理開始) 0x190(立ち絵台本) 0x96(screen) 0x00(sureN) 等 (剔除/非文本)

关键事实 (本 FD 特有):
  * 每个文本框被脚本写了两遍 (0x05 变体 + 0xd3 变体，文本一致) -> prev_clean 相邻去重吸收。
  * 每篇情景 script 开头都带 FD 致谢块 (2 行)，全文重复 -> 仅末尾保留 1 份。
  * 配置/台本档 (script/0,1,2,3,4,5,6,7,18,19,20,21,45,86,99,200,3000,999) 仅含本体致谢块或立ち絵台本，
    不含情景文本 -> 排除 (见 EXCLUDE_FILES)。

用法: python scripts/nisenochigiri_fd_extract.py <输出txt>
"""
import io
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import sys

sys.path.insert(0, os.path.join(VNTRANS_HOME, "tools"))
import nisenochigiri_extract as N
import cpk

CPK_PATH = os.path.join(VNTRANS_HOME, "_work_nisefd/INSTALL.cpk")
HERO = '真奈'        # 名（given name）
PET = 'シロ'          # ペット名
# 姓（surname）：游戏内明说 白羽 是苗字——script/437「私の苗字が白羽だ」「白羽という姓」、
# script/139「白羽と申します」、script/943「『白羽』の苗字」；全名由 `白羽#Name[1]` 拼成
# （script/1027「はい、白羽#Name[1]」=白羽真奈）⇒ #Name[0]=姓=白羽，呼语「#Name[0]殿」=白羽殿。
SURNAME = '白羽'

RE_JP = N.RE_JP
RE_NAME_NO = N.RE_NAME_NO
NAME_TAIL_NO = N.NAME_TAIL_NO

# ---- 显示指令集 (FD 实证) ----
TEXT_CONT = {0xd2}
TEXT_END = {0xd3, 0x05, 0x9a, 0x6e, 0x6f, 0xd4, 0x1, 0xe7, 0x34,
            0x12b, 0x77, 0x13, 0x41dc, 0x35}
NAME_OP = {0x7a, 0x1dd, 0x1d3}

# ---- 表情/姿势标签 (非台词, 引擎运行时替换为立绘表情, 不应作为文本渲染) ----
# 实证: script/201 中 `笑顔` 是一条 k=12 / cmd=0xD3(框末) 的记录, 其全文即 `笑顔`,
# 紧跟在「……」等台词框之后、且下一记录常为名字窗/bg 指令。它既不是台词(玩家不读"笑顔"),
# 也不该被 is_name_head 误判为名字窗(否则会吞掉它并导致前后框错误合并)。
# 同族标签在 gallery(script/84) 以 `\tすまし\t`/`\t困り\t` 等形式附在 0x210 表情码后,
# 且 script/84/87 等已在 EXCLUDE_FILES 排除, 故主提取内仅 `笑顔` 泄漏。若日后发现更多, 在此扩充。
EXPR_LABELS = {'笑顔'}

# 去重(2026-11-11): 主角称呼「真奈」(昵称) 与全名「白羽　真奈」两份同场景孪生文件的昵称版。
# 8 对 +1000 孪生相似度 0.93~1.00；按用户决定保留全名版(1101/1201/1301/1401/1501/1601/1701/1901)，
# 丢弃昵称基础版。这些文件必须【完全跳过】：既不进主场景，也不进 gallery 附录
#（否则经 extract_gallery 无名字窗处理地拼接，会重复抽出昵称版旁白，如 `真奈今日の遊びは…`）。
DEDUP_FILES = {
    'script/101', 'script/201', 'script/301', 'script/401', 'script/501', 'script/601',
    'script/00701', 'script/00901',
}

# ---- 配置/台本/本体致谢档/立ち絵回想ギャラリー (无 FD 情景文本) ----
# ギャラリー判据: k12 记录里含 CG 文件名(下划线) >=20 条 或 "立ち絵を確認" 系统提示
EXCLUDE_FILES = {
    'script/0', 'script/1', 'script/2', 'script/3', 'script/4', 'script/5', 'script/6',
    'script/7', 'script/18', 'script/19', 'script/20', 'script/21', 'script/45',
    'script/86', 'script/99', 'script/200', 'script/3000', 'script/999',
    # 立ち絵/CG ギャラリー (系统 UI，非剧情)
    'script/70', 'script/71', 'script/72', 'script/73', 'script/74', 'script/75',
    'script/80', 'script/81', 'script/82', 'script/83', 'script/84', 'script/85',
    'script/87', 'script/998',
} | DEDUP_FILES

# ---- 致谢块 (每篇开头重复) -> 各档剔除，仅末尾留 FD 致谢 1 份 ----
# 本体(前作)致谢块 9 行 + FD 致谢 2 行，全部在档内剔除
BASE_CREDIT = [
    'ここまで二世の契りを遊んでいただき、',
    '誠にありがとうございます。',
    '先程のエンディングを持ちまして、全てのグッドエンドを見ていただいた',
    '事になります。',
    'ただ、通ったルートによっては、見ていないエピソードやエンディングも',
    'あるかも知れません。',
    '中には、クリアした後に通ると追加されるエピソードもありますので、',
    '良かったら探してみて下さい。',
    '二世の契りのキャラクターやエピソード等で、気に入っていただけるものがありましたら、',
    'とても嬉しく思います。',
    'それでは失礼致します。',
]
FD_CREDIT = [
    'ここまで『二世の契り\u3000想い出の先へ』を',
    '遊んでいただき、誠にありがとうございます！',
]
CREDIT_SET = set(BASE_CREDIT) | set(FD_CREDIT)

# 系统/控制噪声行 + CG 文件名标签(含下划线，正文不会出现)
DROP_LINES = {'処理開始', '処理開始\n', '処理開始\\n', '\u3000', 'screen', 'syou_0'}

RE_NAME_TOKEN = re.compile(r'^[぀-ヿー・々〆＃#\s]+$')
# 全称 "姓　名" (含字间全/半角空格) -> 名字窗标签
NAME_FULL = re.compile(r'^[぀-ヿー・々〆]{1,6}[\s\u3000][぀-ヿー・々〆]{1,6}$')


def norm(s):
    return s.replace('\u3000', '').replace(' ', '')


def is_name_like(s):
    s = s.strip()
    if not s or len(s) > 8:
        return False
    if RE_NAME_NO.search(s):
        return False
    if len(s) > 2 and s[-1] in NAME_TAIL_NO:
        return False
    return bool(RE_JP.search(s))


def is_credit(txt):
    """(备用) 整框子串判定。"""
    return ('遊んでいただき' in txt
            or ('ここまで' in txt and '二世の契り' in txt)
            or 'それでは失礼致します' in txt)


def is_credit_start(s):
    """致谢块起始锚点（均为致谢专有的短语，避免误触发）：
       FD 致谢(二世の契り+想い出の先へ) / 本体致谢开头(二世の契り+遊んでいただき) /
       本体致谢内部开头(先程のエンディングを持ちまして)。"""
    return (('二世の契り' in s and '想い出の先へ' in s)
            or ('二世の契り' in s and '遊んでいただき' in s)
            or '先程のエンディングを持ちまして' in s)


def is_credit_end(s):
    """致谢块结束锚点：FD 致谢结尾(!) 或 本体致谢结尾(それでは失礼致します)。"""
    return ('誠にありがとうございます！' in s) or ('それでは失礼致します' in s)


def clean(t):
    t = t.replace('\\n', '')
    t = N.RE_KANA.sub('', t)
    t = N.RE_COLOR.sub('', t)
    t = N.RE_SCALE.sub('', t)
    t = N.RE_OTHER.sub('', t)
    t = N.RE_PUA.sub('', t)
    t = t.replace('#Name[1]', HERO).replace('#Name[2]', PET).replace('#Name[0]', SURNAME)
    # 框内软换行码 #n（盒内换行，非点击分隔）→ 合并（按“一行=一框”口径，框内换行并入）
    t = t.replace('#n', '')
    # 全角名字变量 ＃＃＃＃＃ (STCM2 名字槽占位符, 引擎运行时替换为角色注册名;
    # 默认渲染为空, 对应正文里别人直呼"ルル", 故此处剥离即得真名)
    t = re.sub(r'＃+', '', t)
    return t


# ---- ギャラリー(立ち絵/回想/ボイス) ファイルから、シナリオ外の固有台詞のみ抽出 ----
# 这些档混有 UI：立ち絵選択プロンプト・キャラ選択肢・背景/立ち絵位置ラベル・
# CG ファイル名・本体致谢块。只保留 "ボイス/回想" 里的角色台詞(含「」)。
GALLERY_UI_KW = ('立ち絵を確認', '確認しますか', 'パクパク', '表情説明後', '追加分どっち',
                 '用だからきにすんな', '嬉しく思います', '気に入って', '中には、クリア',
                 '遊んでいただき', '二世の契り', '失礼致', 'エンディング', 'グッドエンド',
                 'エピソード', '良かったら')


def is_gallery_ui(s):
    if re.match(r'^(screen|処理開始|sure\d*|select|てすとめっせーじ)$', s.strip()):
        return True
    if '：' in s or ':' in s:                      # bg/ev CG ラベル
        return True
    if 'のどれー' in s:                            # キャラ選択肢
        return True
    if any(k in s for k in GALLERY_UI_KW):
        return True
    # 背景/立ち絵 位置ラベル (例: 居候する家・自室　夜) — 中点付きで台詞カッコなし
    if '・' in s and '「' not in s and '」' not in s:
        return True
    return False


def _flush_gal(cur, seen, scen_text, out):
    txt = ''.join(cur)
    del cur[:]
    if not re.search(r'[぀-ヿー「」]', txt):
        return
    if txt in seen or txt in scen_text:
        return
    seen.add(txt)
    out.append(txt)


def extract_gallery(c, files, scen_text):
    """ギャラリー各档をボックス結合し、UI/致谢/重複を除いた固有台詞だけ返す。"""
    out = []
    seen = set()
    for fn in files:
        raw = c.raw(c.by_name[fn])
        flat = []
        for u in N.units(raw):
            for k, t, cmd, arg in N.recs(u):
                flat.append((k, t, cmd, arg))
        cur = []
        in_credit = False
        for idx in range(len(flat)):
            k, t, cmd, arg = flat[idx]
            if k == 24:                     # 選択肢(キャラ名など)は除外
                if cur:
                    _flush_gal(cur, seen, scen_text, out)
                    cur = []
                continue
            if k != 12:
                if cur:
                    _flush_gal(cur, seen, scen_text, out)
                    cur = []
                continue
            s = clean(t)
            if not s.strip():
                if cur:
                    _flush_gal(cur, seen, scen_text, out)
                    cur = []
                continue
            # 致谢块：最高优先级，必须先于 CG/UI 判定，否则会被 UI 关键词截走
            # （GALLERY_UI_KW 含 '二世の契り' 等致谢短语，会把致谢起始行误判为 UI）。
            if in_credit:
                if is_credit_end(s) or k == 24:
                    in_credit = False
                else:
                    continue
            if is_credit_start(s):
                if cur:
                    _flush_gal(cur, seen, scen_text, out)
                    cur = []
                in_credit = True
                continue
            if '_' in s or '＿' in s:         # CG ファイル名ラベル
                if cur:
                    _flush_gal(cur, seen, scen_text, out)
                    cur = []
                continue
            if is_gallery_ui(s):
                if cur:
                    _flush_gal(cur, seen, scen_text, out)
                    cur = []
                continue
            if cmd in TEXT_CONT:
                cur.append(s)
                continue
            if cmd in TEXT_END:
                if s.strip():
                    cur.append(s)
                if not cur:
                    continue
                _flush_gal(cur, seen, scen_text, out)
                cur = []
                continue
            if re.search(r'[぀-ヿー]', s) and len(s.strip()) >= 2:
                if s.strip():
                    cur.append(s)
                if not cur:
                    continue
                _flush_gal(cur, seen, scen_text, out)
                cur = []
    return out


# ---- 非 STCM2 的数据表 (script/10,11,35,37,51 等)：内含真实可显示文本 ----
# 这些档是 CRI 表格式：固定宽度字段 + 0xff 填充 + 0x80/0xff 分隔，cp932 文本以 \0 结尾。
# 0xff / 0x80 仅作填充/分隔（cp932 合法前导字节为 0x81-9F/0xE0-FC，故可安全替换）。
def _read_field(raw, pos):
    """从 pos 起，跳过 0xff/0x80 填充后，读到 \0（或再遇填充）为止；返回 (bytes, 新pos)。
    返回的 bytes 不含终止 \0。"""
    n = len(raw)
    while pos < n and raw[pos] in (0xff, 0x80):
        pos += 1
    if pos >= n:
        return b'', pos
    start = pos
    while pos < n and raw[pos] != 0 and raw[pos] not in (0xff, 0x80):
        pos += 1
    end = pos                              # 停在 \0 / 填充 处
    if pos < n and raw[pos] == 0:          # 越过 \0 终止符
        pos += 1
    return raw[start:end], pos


def _decode(b):
    return b.decode('cp932', 'ignore').replace('#n', '').strip()


def extract_glossary(raw):
    """script/11 用語辞典：每条目 = [flagname] + 标记 + 見出し語 + 読み + 解説文。
    以 8 字节标记 00 00 00 00 80 00 80 00 锚定每条目，取其 見出し語 与 解説文。"""
    marker = b'\x00\x00\x00\x00\x80\x00\x80\x00'
    out = []
    pos = 0
    n = len(raw)
    while True:
        i = raw.find(marker, pos)
        if i < 0:
            break
        pos = i + len(marker)
        term, pos = _read_field(raw, pos)
        reading, pos = _read_field(raw, pos)   # 読み（假名），丢弃
        definition, pos = _read_field(raw, pos)
        ts, ds = _decode(term), _decode(definition)
        if ts and ds:
            out.append('【%s】%s' % (ts, ds))
        elif ts:
            out.append('【%s】' % ts)
    return out


def extract_synopsis(raw):
    """script/51 あらすじ：按 FF FF FF PP 00 NN 00 记录头分块。

    每条记录 = 一个显示行(NN)，PP 为页码(翻页点击单位)。
    分页首行的头部是 FF FF FF FF PP 00 00 00(比页内行多一个 FF)，页内行是
    FF FF FF PP 00 NN 00(NN=01..05)；两种都用同一判据
    (raw[j+3] 非 FF/00 且 j+4=00 且 j+6=00) 捕获，靠逐字节重扫重叠 FF
    拿到首行那条（否则跳得太远会漏掉每页首行，造成剧情缺口）。页首行 NN=00。

    按页归并：每页(PP)一条行，页内 NN 显示行连续拼合（屏幕上即按 21 字宽
    换行，文本本身连续，无语义断句）。一页 = 一次点击 = 一行
    （本作あらすじ阅读器的翻页单位）。"""
    n = len(raw)
    marker = b'\xff\xff\xff'

    def is_header(j):
        return (j + 6 < n and raw[j + 3] not in (0xff, 0x00)
                and raw[j + 4] == 0x00 and raw[j + 6] == 0x00)

    records = []  # (PP, NN, text)
    i = 0
    while True:
        j = raw.find(marker, i)
        if j < 0:
            break
        if is_header(j):
            PP = raw[j + 3]; NN = raw[j + 5]
            q = j + 7
            while q < n and raw[q] != 0:
                q += 1
            text = raw[j + 7:q].decode('cp932', 'ignore')
            records.append((PP, NN, text))
            i = q
        else:
            i = j + 1   # 逐字节重扫, 处理重叠的 FF(分页首行头部多一个 FF)

    # 第一个记录之前的 JP 文本 = 第1页首行(文件头之后, 无 FF FF FF 头)
    jj = 0
    first_header = n
    while jj < n:
        if is_header(jj):
            first_header = jj
            break
        nxt = raw.find(marker, jj + 1)
        if nxt < 0:
            break
        jj = nxt
    pre = raw[:first_header].replace(b'\xff', b'\x00').replace(b'\x80', b'\x00').decode('cp932', 'ignore')
    first_runs = [s for s in pre.split('\x00') if re.search(r'[぀-ヿ一-龠]', s)]

    pages = {}
    if first_runs:
        pages[1] = [(-1, ''.join(first_runs))]
    for PP, NN, text in records:
        pages.setdefault(PP, []).append((NN, text))

    out = []
    for PP in sorted(pages):
        lines = sorted(pages[PP], key=lambda x: x[0])
        out.append(''.join(t for _, t in lines))
    return out


def extract_voice_quotes(raw):
    """script/37 ボイス/おみくじ 台詞表：抽取所有 「…」 引用台詞。

    注意：不能用 [「『][^」』]*[」』] —— 一旦文本内嵌 『…』（如『吉』），
    该贪心式会停在内部 』 处，把外层 」 漏掉，导致引号不配对 + 宏未解析。
    正确做法：先抽外层 「[^」]*」（内部可含 『』），再补抽不在任何外层句中的独立 『…』；
    每个候选都过 clean() 解析 #Name/#Kana/#n 等控制码。"""
    txt = raw.replace(b'\xff', b'\x00').replace(b'\x80', b'\x00').decode('cp932', 'ignore')
    outer = re.findall(r'「[^」]*」', txt)
    outer_text = '\n'.join(outer)
    inner = [q for q in re.findall(r'『[^』]*』', txt) if q not in outer_text]
    out = []
    seen = set()
    for q in outer + inner:
        q = clean(q).strip()
        if len(q) < 2 or not re.search(r'[぀-ヿ一-龠]', q):
            continue
        if q in seen:
            continue
        seen.add(q)
        out.append(q)
    return out


def extract_short_labels(raw):
    """script/10(地名) / script/35(回想タイトル) 等短标签：抽出含日文的字段，剥前导非日文噪声。"""
    txt = raw.replace(b'\xff', b'\x00').replace(b'\x80', b'\x00').decode('cp932', 'ignore')
    out = []
    for f in txt.split('\x00'):
        f = f.strip()
        m = re.search(r'[぀-ヿ一-龠]', f)
        if not m:
            continue
        f2 = f[m.start():]
        if len(f2) >= 2:
            out.append(f2)
    return out


def load_names(c, files):
    """名札白名单：全 STCM2L 档的 名表 cmd(0x1ae) + 名札 op(NAME_OP: 0x7a/0x1dd/0x1d3) 文本。
    注：0x1dd 既承载名字也承载背景/事件文件名标签(bg95_b/ev8150 等)，
    但后者无日文(RE_JP 不匹配) -> 不会被收入 names，故不会污染说话人判定。"""
    names = set()
    for fn in files:
        raw = c.raw(c.by_name[fn])
        if raw[:5] != b'STCM2':
            continue
        for u in N.units(raw):
            for k, t, cmd, arg in N.recs(u):
                if cmd in NAME_OP or cmd == 0x1ae:
                    s = clean(t).strip()
                    if s and len(s) <= 16 and RE_JP.search(s):
                        names.add(s)
    names.add('？？？')
    # #Name 宏解析出的主角/宠物名也纳入名字集, 使 #Name[1]->真奈 等名字窗能被识别
    # (clean 把 #Name[1] 解析为 HERO, 但该宏非字面名字记录 -> 不进上面的循环)。
    names.add(HERO)
    names.add(PET)
    names.add(SURNAME)
    return names


def is_name_head(s, nxt, names):
    s2 = s.strip().lstrip('※')     # 剥「※」思考泡泡标记
    if not s2:
        return False
    if s2 in names:                # 已知名字(汉字姓/名、片假名) -> 无论后续是台词还是旁白都判为名字窗
        return True
    if NAME_FULL.match(s2):        # 姓　名 全称 -> 名字窗
        return True
    n2 = nxt.strip().lstrip('※')
    # 名字窗后接台词(以「『（开头)才可能是"名字窗+正文"; 但该分支须限制长度:
    # 长句(如 `本当に#Name[1]は面白いことを言いますね」`)即便后接「也不能当名字窗,
    # 否则正文里嵌 #Name 宏的语句会被误判为名字窗而整句丢弃。名字窗本身是短串(≤12)。
    if (nxt in ('「', '『', '（') or n2 in names) and len(s2) <= 12:
        if RE_NAME_TOKEN.match(s2):
            return True
        if is_name_like(s2):
            return True
    return False


def _emit(cur, cur_name, out, prev_clean, stat, norm, names):
    """合并当前文本框为一行并输出。

    台词判据(用户要求: 台词加说话人名, 旁白不加):
      框文本**以「/『开头**才视为角色发言(台词) -> 加说话人名;
      否则(首字符非引号, 即便框内嵌『…』引用)视为旁白 -> 不加名。
      理由: 本引擎把发言包在「…」内, 旁白为叙述散文(可能内嵌『引用』);
      且同一发言跨多框续行(0xd2/0xd3)会被并合成一条以「开头的行,
      故"开头判据"在"已并合的行"层面可靠。

    为支持同说话人连续多框发言, 台词后**保留** cur_name;
    旁白(或非台词)后**清空** cur_name, 避免名字泄漏到后续旁白
    (本 FD 名字窗常领先于一段旁白, 如 prologue 真奈名窗后整段叙述)。
    """
    txt = ''.join(cur)
    del cur[:]
    if not txt.strip():
        return prev_clean, cur_name
    if txt.strip() in names:           # 残留纯名字 -> 剔除
        stat['plate_txt'] += 1
        return prev_clean, cur_name
    st = txt.lstrip('\u3000 ')
    is_dialogue = st[:1] in ('「', '『')
    if is_dialogue and cur_name is not None:
        line = cur_name + txt
        new_name = cur_name             # 同说话人连续框: 保留名字
    else:
        line = txt
        new_name = None                 # 旁白或无说话人: 清空, 防泄漏
    if line == prev_clean or norm(line) == norm(prev_clean or ''):
        stat['dup'] += 1
        return prev_clean, new_name
    out.append(line)
    stat['frame'] += 1
    return line, new_name


def _branch_diff(a, b):
    """判断 a,b 是否为"同一句只差一个替换词"的互斥分支变体。

    判据（代码级、严格，避免误吞真正不同的两句）：
      去掉公共前缀/后缀后, 剩余差异段很短(≤8字), 且公共部分覆盖两串较短者的 ≥80%。
    例: `「っ！ 瑠璃丸、真奈の馬を――！」` vs `「っ！ 瑠璃丸、こいつの馬を――！」
        公共前缀「っ！ 瑠璃丸、(8) + 后缀 馬を――！」(5) =13 ≥ 0.8*16,
        差异段 真奈の/こいつ (3+3=6 ≤8) -> True。
    """
    if not a or not b or a == b:
        return False
    # 最长公共前缀
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    # 最长公共后缀（跳过前缀重叠部分）
    j = 0
    while (j < len(a) - i and j < len(b) - i
           and a[len(a) - 1 - j] == b[len(b) - 1 - j]):
        j += 1
    mid1 = a[i:len(a) - j]
    mid2 = b[i:len(b) - j]
    cover = (i + j) / min(len(a), len(b))
    return cover >= 0.80 and (len(mid1) + len(mid2)) <= 8


def _collect_branch_boxes(flat, start, names):
    """从 start 起收集连续 k=12 文本框(续框 TEXT_CONT 并入), 直到出现非文本框/
    名字窗/控制记录为止。若收集到 ≥2 个且两两近重复(同一句分支变体), 返回它们;
    否则返回 []。每个元素: {start,end,text,has_name}。`has_name`=该框原始含 #Name[ 宏
    (clean 已解析为 真奈 等命名版)。
    """
    boxes = []
    i = start
    n = len(flat)
    while i < n:
        kk, tt, cc, aa = flat[i]
        if kk == 12 and cc in TEXT_END and not is_name_head(clean(tt), '', names):
            txt = clean(tt)
            has_name = '#Name[' in tt
            # 仅当框含日文才视为对话分支; 纯 ASCII 测试串(sure2/sure3 等)虽近重复
            # 但非剧情文本, 不在此合并, 避免误吞测试占位串。
            if not RE_JP.search(txt):
                break
            j = i + 1
            # 续框只并入真正的文本续行; 若续框记录实为名字窗(0xd2 名札)则停止,
            # 让外层在它处断开(不同说话人=非分支), 避免名字被误并入上一框文本。
            while (j < n and flat[j][0] == 12 and flat[j][2] in TEXT_CONT
                   and not is_name_head(clean(flat[j][1]), '', names)):
                txt += clean(flat[j][1])
                if '#Name[' in flat[j][1]:
                    has_name = True
                j += 1
            boxes.append({'start': i, 'end': j, 'text': txt, 'has_name': has_name})
            i = j
        else:
            break
    if len(boxes) >= 2 and all(_branch_diff(boxes[0]['text'], b['text']) for b in boxes[1:]):
        return boxes
    return []


def _is_script_comment(s):
    """脚本编辑器注释框（引擎运行时不渲染）: 文本以 */ 或 /* 起首(通常 */ 收尾),
    如 `*/シナリオここまで 202へ*/`(场景跳转标记)。此类框非剧情文本, 不应并入台词行。"""
    s = s.strip()
    if not s:
        return False
    return s.startswith('*/') or s.startswith('/*')


def extract_file(raw, names, stat):
    out = []
    flat = []
    for u in N.units(raw):
        for k, t, cmd, arg in N.recs(u):
            flat.append((k, t, cmd, arg))
    cur = []
    opts = []
    prev_clean = None
    in_credit = False
    framed = False
    cur_name = None                 # 当前说话人（名字窗/名表 op 设置；旁白框无「」不带名）
    n = len(flat)
    skip = set()                    # def_check 分支: 被丢弃的代称版记录索引
    for idx in range(n):
        if idx in skip:
            continue
        k, t, cmd, arg = flat[idx]
        nxt = flat[idx + 1][1][:1] if idx + 1 < n else ''
        if k == 24:
            # 互斥分支: def_check(cmd=0x05) 后紧跟两个近重复文本框(只差一个替换词)。
            # 命名版用 #Name[1] 宏(解析为 真奈), 代称版用字面代词(こいつ等)。
            # 只保留命名版、丢弃代称版, 避免成品出现"幽灵重复行"(同周目只出一句)。
            # 其余 def_check(绝大多数) 不受影响, 照常跳过。
            if cmd == 0x05:
                boxes = _collect_branch_boxes(flat, idx + 1, names)
                if boxes:
                    chosen = next((b for b in boxes if b['has_name']), boxes[0])
                    if cur:
                        prev_clean, cur_name = _emit(cur, cur_name, out, prev_clean, stat, norm, names)
                    prev_clean, cur_name = _emit([chosen['text']], cur_name, out,
                                                 prev_clean, stat, norm, names)
                    stat['branch'] = stat.get('branch', 0) + 1
                    if len(stat.get('branch_samples', [])) < 40:
                        stat.setdefault('branch_samples', []).append(
                            (stat.get('_cur_file'), [b['text'] for b in boxes]))
                    for b in boxes:
                        skip.update(range(b['start'], b['end']))
                    continue
            if cmd in (0xe7, 0xe6) or (cmd == 0x1 and opts):
                s = clean(t).strip()
                if stat.get('skip'):
                    stat['skip'] -= 1
                    continue
                if s and not re.match(r'^[A-Za-z_0-9]+$', s):
                    if s in opts[-4:]:
                        stat['opt_dup'] += 1
                        continue
                    out.append(s)
                    prev_clean = s
                    opts.append(s)
                    stat['opt'] += 1
                else:
                    stat['opt_noise'].append(s)
            continue
        if k != 12:
            continue
        if cmd in NAME_OP:
            # 名札 op(0x7a/0x1dd/0x1d3): 已限定 k=12 (非 k12 的精灵/背景标签如
            # masatora_b_* / bg95_b / ev8150 已在上一步 k!=12 跳过)。
            # 注意 0x1d3/0xd3 同时是文本框末记录: 0xd3 既作名字窗也作框末。
            # 故仅当文本**确为已收录名字**才当名字窗(设 cur_name 并跳过);
            # 否则 0xd3 文本落回下方 TEXT_END 当正文输出, 否则正文会被误吞
            # (如 script/233 的 `　本当に真奈は面白いことを言いますね」` 框末被吞 → 丢字+引号失衡)。
            # 0x7a/0x1dd 为纯名字窗 op, 非名字文本(背景/事件标签 bg95_b)直接跳过。
            nm = clean(t).strip()
            if nm and '_' not in nm and '＿' not in nm and nm in names:
                cur_name = nm
                stat['plate_op'] += 1
                continue
            if cmd != 0xd3:
                stat['plate_op'] += 1
                continue
            # cmd==0xd3 且文本非名字 -> 落回 TEXT_END 当正文处理

        s = clean(t)
        if not s:
            # 空框末记录(0xd3 '') -> 冲刷待输出文本框, 避免跨框并合(如 script/100 prologue)
            if cur:
                prev_clean, cur_name = _emit(cur, cur_name, out, prev_clean, stat, norm, names)
                del opts[:]
                framed = True
            continue
        # 表情/姿势标签 (如 `笑顔`): 非台词, 引擎用于切换立绘表情。
        # 冲刷前面挂起的正文框(干净归属上一说话人)后丢弃, 既不泄漏为文本,
        # 也不被 is_name_head 误吞(避免吞掉标签并导致前后文本框错误合并)。
        if s in EXPR_LABELS:
            if cur:
                prev_clean, cur_name = _emit(cur, cur_name, out, prev_clean, stat, norm, names)
                del opts[:]; framed = True
            stat['expr'] = stat.get('expr', 0) + 1
            continue
        # 脚本编辑器注释框(引擎运行时不渲染): 文本以 */ 或 /* 起止, 如
        # `*/シナリオここまで 202へ*/`(场景跳转标记)。先冲刷前面挂起的正文(干净输出),
        # 再单独作为注释标记行输出(不静默丢弃、不与台词混淆、不冠名)。
        if _is_script_comment(s):
            if cur:
                prev_clean, cur_name = _emit(cur, cur_name, out, prev_clean, stat, norm, names)
                del opts[:]; framed = True
            inner = s.strip('*/').strip()
            out.append('/* ' + inner + ' */')
            stat['comment'] = stat.get('comment', 0) + 1
            continue
        # 致谢块：文件开头连续区域，用起止锚点整段跳过
        # （吸收 0xd2 碎片 + 0xd3 结尾，避免碎片污染 cur 后并合到正文框）
        if in_credit:
            if is_credit_end(s):
                in_credit = False
                stat['credit'] += 1
            continue
        if (not framed) and is_credit_start(s):
            in_credit = True
            stat['credit'] += 1
            continue
        # 纯空白框(仅全角/半角空格) 或 噪声串(処理開始/screen/syou_0…): 先冲刷前面挂起的正文框
        # (正确归属上一说话人) 再丢弃, 否则直接 continue 会使 cur 与后继框并合成同一行、
        # 吞掉中间的说话人切换(如 script/1026: 刀儀 兼久「…」被并进 瑠璃丸「…」)。
        if not s.strip() or s in DROP_LINES:
            if cur:
                prev_clean, cur_name = _emit(cur, cur_name, out, prev_clean, stat, norm, names)
                del opts[:]; framed = True
            continue
        # CG 文件名标签 (含下划线) 非正文 -> 剔除
        if '_' in s or '＿' in s:
            stat['cg_label'] += 1
            continue
        # 独立名字窗（不含正文）：记录当前说话人，不输出；
        # 后继若为正文台词(含「」)则带名，旁白(无「」)不带名。
        # 名字窗判定以"解析后文本是否为名字"为准: clean 已将 #Name[1]->HERO 等宏解析,
        # HERO/PET 已纳入 names 集合, 故 #Name 解析出的主角/宠物名窗口能被 is_name_head 识别。
        # 注意不可仅判 raw 含 '#Name[' —— 正文里也会嵌 #Name[1] 宏(如 `本当に#Name[1]は…`),
        # 那是台词里提到主角名, 非名字窗, 若误判会把整句正文当名字窗丢弃。
        if is_name_head(s, nxt, names):
            cur_name = s.strip().lstrip('※')
            stat['plate_txt'] += 1
            if len(stat['plate_samples']) < 120:
                stat['plate_samples'].append((stat['_cur_file'], s))
            continue
        if cmd in TEXT_CONT:
            cur.append(s)
            continue
        if cmd in TEXT_END:
            # 框末记录(0xd3/0x05 等)常常携带本框最后一段文本，必须并入
            if s.strip():
                cur.append(s)
            if not cur:
                continue
            prev_clean, cur_name = _emit(cur, cur_name, out, prev_clean, stat, norm, names)
            del opts[:]
            framed = True
            continue
        # 兜底：其余 k=12 带日文文本的记录，按框末处理 (吸收罕见 end 变体)
        if RE_JP.search(s) and len(s.strip()) >= 2:
            if s.strip():
                cur.append(s)
            if not cur:
                continue
            prev_clean, cur_name = _emit(cur, cur_name, out, prev_clean, stat, norm, names)
            del opts[:]
            framed = True
    if cur:
        prev_clean, cur_name = _emit(cur, cur_name, out, prev_clean, stat, norm, names)
    return out


def useful(s):
    return bool(s.strip()) and bool(RE_JP.search(s))


def main():
    dst = sys.argv[1]
    c = cpk.CPK(CPK_PATH)
    c.by_name = {e['name']: e for e in c.entries if e.get('name')}
    all_stcm = [e['name'] for e in c.entries
                if (e.get('name', '') or '').startswith('script/') and c.raw(e)[:5] == b'STCM2']
    files = [f for f in all_stcm if f not in EXCLUDE_FILES]
    files.sort(key=lambda f: (0, int(f.split('/')[1])) if f.split('/')[1].isdigit() else (1, f))
    # ギャラリー(立ち絵/回想/ボイス) ファイル：UI 混在のため本編から除外し、
    # 单独に "シナリオ外の固有台詞" だけ抽出して末尾に添付。
    # DEDUP_FILES(昵称版孪生) 必须彻底跳过: 既不进主场景, 也不进 gallery 附录。
    GALLERY_FILES = sorted(
        [f for f in all_stcm if f in EXCLUDE_FILES and f.startswith('script/') and f not in DEDUP_FILES],
        key=lambda f: (0, int(f.split('/')[1])) if f.split('/')[1].isdigit() else (1, f))
    names = load_names(c, all_stcm)  # 从全部 STCM2L 取名字表
    print("STCM2L total:", len(all_stcm), " extracting:", len(files),
          " gallery:", len(GALLERY_FILES), " names:", len(names))
    stat = {'frame': 0, 'opt': 0, 'plate_op': 0, 'plate_txt': 0, 'dup': 0,
            'plate_samples': [], 'opt_noise': [], 'credit': 0, 'skip': 0,
            'opt_dup': 0, 'cg_label': 0, '_cur_file': None}
    lines = []
    for f in files:
        stat['_cur_file'] = f
        seg = [s for s in extract_file(c.raw(c.by_name[f]), names, stat) if useful(s)]
        lines += seg
    lines += FD_CREDIT  # 致谢块仅末尾保留 1 份
    scen_text = '\n'.join(lines)
    # ギャラリー添付：シナリオ外の固有台詞(UI/致谢/重複除外)
    gal = extract_gallery(c, GALLERY_FILES, scen_text)
    # 追加 script/37 ボイス/おみくじ 台詞表 中、シナリオ外且未重复的固有台詞
    seen = set(gal)
    if 'script/37' in c.by_name:
        for q in extract_voice_quotes(c.raw(c.by_name['script/37'])):
            q = q.strip()
            if len(q) < 2 or not re.search(r'[぀-ヿ一-龠]', q):
                continue
            if q in seen or q in scen_text:
                continue
            seen.add(q)
            gal.append(q)
    if gal:
        lines.append('========== ギャラリー ボイス/回想 サンプル（シナリオ外の固有台詞・重複除外） ==========')
        lines += gal
    # 補足：非 STCM2 数据表中的真实可显示文本（用語辞典/あらすじ/回想タイトル/地名）
    sup = []
    if 'script/11' in c.by_name:
        g = extract_glossary(c.raw(c.by_name['script/11']))
        if g:
            sup.append('---- 用語辞典 (script/11) ----')
            sup += g
    if 'script/51' in c.by_name:
        s = extract_synopsis(c.raw(c.by_name['script/51']))
        if s:
            sup.append('---- あらすじ (script/51) ----')
            sup += s
    labels = []
    for fn in ('script/35', 'script/10'):
        if fn in c.by_name:
            labels += extract_short_labels(c.raw(c.by_name[fn]))
    if labels:
        sup.append('---- 回想タイトル・地名 (script/35 / script/10) ----')
        sup += labels
    if sup:
        lines.append('========== 補足：用語辞典・あらすじ・回想タイトル・地名 ==========')
        lines += sup
    with io.open(dst, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('frames %d  options %d  plate_op %d  plate_txt %d  dup %d  credit %d  cg_label %d  opt_dup %d'
          % (stat['frame'], stat['opt'], stat['plate_op'], stat['plate_txt'],
             stat['dup'], stat['credit'], stat['cg_label'], stat['opt_dup']))
    print('opt_noise:', stat['opt_noise'][:20])
    print('plate_samples:', stat['plate_samples'][:30])
    print('WROTE', dst, len(lines), 'lines')


if __name__ == '__main__':
    main()
