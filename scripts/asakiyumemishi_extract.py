# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""あさき、ゆめみし～ひととせ～ (PC / 澪 / System-NNN「NNNLib」引擎) 全文本提取 · 定稿

源：<游戏原始 dump 目录>/[PC-JP]あさき、ゆめみし～ひととせ～.rar
    RAR5 加密（密码 otoame）→ asaki_hitotose/{asaki_hitotose.exe, spt/*.spt, spt/*.xtx, dwq/*.gpk}
    · .spt = 剧本（二进制字节码）—— 文本在此
    · .xtx = 配置（纯 cp932 文本）
    · .gpk/.gtb = 图片包（实为 PNG 集合，非文本）

★★ .spt 格式（本作逆向结论）
  * 整文件【逐字节 XOR 0xFF】混淆（即字节取反）。
  * 取反后：
      0x00 u32 = 0x20          版本号
      0x30 "SPTHEADER0"        魔术字
      0x80+ 指令流（4B 对齐，op 形如 `?? 00 66 66` / `?? 00 55 55` …）
      之后   字符串池：消息串以 \0 结尾、按剧本执行顺序排列，
             两条之间偶尔夹 0~3 字节控制数据（其字节恰可解作 cp932 时，
             会把下一条串“污染”出 1~3 个字的前缀 —— 本作最主要的陷阱）。
  * 消息串 = `<说话人名>\r\n<正文>`：
      · 说话人名可为字面名(高虎/愁一郎/虚空/風鬼/水鬼/金鬼/望/暁…)、
        `#名`(=主人公名，本作=沙耶)、`？？？`(未知人物)
      · 不含 `\r\n` 者 = 旁白
  * 正文内联控制码：
      `#［Nよみ］` = 注音（N=被注音字数）→ 保留汉字、剔读音
      `#名`       = 主人公名 → inline 换成「沙耶」（如 `伊織#名` = 伊織沙耶）
      `#心`       = 图标记号(ハート) → 剔
      `\r\n`      = 消息框内换行 → 合并为一行

重同步（本脚本核心，修掉 ~400 条错名 + ~130 条错前缀）
  ① 字节级找 `^<说话人标记>\r\n`（起点 p=0..5），命中即锚定；
  ② 字级容忍 ≤3 个前置垃圾字的同类锚定；
  ③ 首字为“可疑字”时逐 p 前进取第一个正常起点。可疑字判据：
       ASCII / 半角カナ / 全角英数記号 / U+3000 / **JIS X0208 第2水準汉字** /
       「只在行首高频出现且正文中从不出现」的伪字（finit≥2 且 fmid==0）。

输出规范（跨作统一）：UTF-8-BOM / 纯 LF / 一行为一次点击 /
  行内换行合并 / 保留日文原文 / 去说话人前缀 / 主人公名 inline / 不加翻译。
  顺序 = takatora.spt（高虎編）→ syuichirou.spt（愁一郎編）→ 场景标题与系统 UI。
"""

import os, re, collections

VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
SRC = os.path.join(VNTRANS_HOME, '_asakiyumemishi/extracted/asaki_hitotose')
SPT = os.path.join(SRC, 'spt')
OUTDIR = os.environ.get('VN_OUTDIR', os.path.join(VNTRANS_HOME, '提取结果'))
TITLE = 'あさき、ゆめみし～ひととせ～'
PROTAG = '沙耶'

NAMES = []
for _l in open(os.path.join(SPT, 'charaname.xtx'), 'rb').read().decode('cp932').splitlines():
    if ',' in _l:
        _v = _l.split(',', 1)[1].strip()
        if _v and _v != '名前なし':
            NAMES.append(_v)
MARKERS = ['#名', '？？？'] + sorted(set(NAMES), key=len, reverse=True)
_ALT = '|'.join(re.escape(m) for m in MARKERS)
NAME_RE = re.compile('^(' + _ALT + r')\r\n')
NAME_CHAR_RE = re.compile('^(?:.{1,3}?)(' + _ALT + r')\r\n')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff\u3000-\u303f\uff01-\uff60]')
_SAFE_FW = set('！？、。…ー〜・「」『』（）～…—')


def decrypt(p):
    return bytes(b ^ 0xFF for b in open(p, 'rb').read())


def is_lead(b):
    return (0x81 <= b <= 0x9f) or (0xe0 <= b <= 0xfc)


def scan_strings(n, start=0):
    L = len(n); out = []; i = start
    while i < L:
        if n[i] == 0:
            i += 1; continue
        j = i; ok = True
        while j < L:
            c = n[j]
            if c == 0:
                break
            if is_lead(c):
                if j + 1 < L and ((0x40 <= n[j + 1] <= 0x7e) or (0x80 <= n[j + 1] <= 0xfc)):
                    j += 2
                else:
                    ok = False; break
            elif 0x20 <= c <= 0x7e or 0xa1 <= c <= 0xdf or c in (0x0d, 0x0a, 0x09):
                j += 1
            else:
                ok = False; break
        if ok and j > i:
            out.append((i, j)); i = j
        else:
            i += 1
    return out


def clean_body(s):
    s = re.sub(r'#［[^］]*］', '', s)      # 注音 -> 剔
    s = s.replace('#名', PROTAG)         # 主人公名 inline
    s = re.sub(r'#.', '', s)             # 其余 #X 图标记号( #心 / #猫 …) -> 剔
    s = s.replace('\r\n', '').replace('\n', '').replace('\r', '')
    return s.strip()


def _jis_level2(c):
    """cp932 中 JIS X0208 第2水準 (0x989F..0xEAA4) / IBM 拡張 = 罕见汉字"""
    b = c.encode('cp932', 'ignore')
    if len(b) != 2:
        return False
    v = b[0] << 8 | b[1]
    return 0x989F <= v <= 0xEAA4 or v >= 0xFA40


def suspicious(c, freq):
    o = ord(c)
    if c == '\u3000':                                   # 全角空格（本作正文无行首空格）
        return True
    if 0x20 <= o < 0x80:                                # ASCII
        return True
    if 0xff61 <= o <= 0xff9f:                           # 半角カナ
        return True
    if (0xff01 <= o <= 0xff60 or 0xffe0 <= o <= 0xffee) and c not in _SAFE_FW:
        return True                                     # 全角英数記号
    if 0x4e00 <= o <= 0x9fff and _jis_level2(c):        # 第2水準汉字
        return True
    return False


def garble_init(c, finit, fmid):
    """只在“行首”高频出现、正文中从不出现的字 —— 判为控制数据伪字"""
    return fmid.get(c, 0) == 0 and finit.get(c, 0) >= 2


def parse_message(raw, susp):
    try:
        t0 = raw.decode('cp932')
    except UnicodeDecodeError:
        t0 = ''
    # ① 人名硬锚点（字节级）
    for p in range(0, 6):
        if p >= len(raw):
            break
        try:
            t = raw[p:].decode('cp932')
        except UnicodeDecodeError:
            continue
        m = NAME_RE.match(t)
        if m:
            return clean_body(t[m.end():])
    # ①b 人名锚点（字级，容忍 ≤3 个前置垃圾字）
    if t0:
        m = NAME_CHAR_RE.match(t0)
        if m:
            return clean_body(t0[m.end():])
    # ② 首字可疑 -> 前进
    p = 0
    while p < 7:
        try:
            t = raw[p:].decode('cp932')
        except UnicodeDecodeError:
            p += 1; continue
        if not t:
            break
        if t[0] in '\r\n':
            p += 1; continue
        if not susp(t[0]):
            return clean_body(t)
        p += 1
    # ③ 兜底
    if not t0:
        return ''
    t = t0.lstrip('\r\n')
    i = 0
    while i < len(t) and (ord(t[i]) < 0x80 or 0xff61 <= ord(t[i]) <= 0xff9f):
        i += 1
    if 0 < i < len(t):
        t = t[i:]
    return clean_body(t)


def block_bounds(n, start):
    ss = scan_strings(n, start)
    end = len(n)
    for k in range(len(ss) - 1):
        if ss[k + 1][0] - ss[k][1] > 256:
            end = ss[k][1]; break
    return start, end


def collect(fn, po):
    n = decrypt(os.path.join(SPT, fn))
    a0, a1 = block_bounds(n, po)
    b1, b2 = [], []
    for a, b in scan_strings(n, a0):
        (b1 if a < a1 else b2).append(n[a:b])
    return b1, b2


def collect_all(fn):
    n = decrypt(os.path.join(SPT, fn))
    return [n[a:b] for a, b in scan_strings(n, 0)]


def main():
    t1, t2 = collect('takatora.spt', 0xcf5a4)
    s1, s2 = collect('syuichirou.spt', 0xa8424)

    # 频率表：初字统计 finit / 正文(非初字)统计 fmid —— 用于判别“控制数据伪字”
    finit = collections.Counter()
    fmid = collections.Counter()
    parse0 = lambda r: parse_message(r, lambda c: suspicious(c, None))
    for _round in range(3):
        finit = collections.Counter(); fmid = collections.Counter()
        for r in t1 + s1:
            b = parse0(r) if _round == 0 else parse_message(r, lambda c: suspicious(c, None) or garble_init(c, finit, fmid))
            if not b or not JP.search(b):
                continue
            finit[b[0]] += 1
            fmid.update(b[1:])
    def susp(c):
        return suspicious(c, None) or garble_init(c, finit, fmid)

    def gen(rafts):
        for r in rafts:
            b = parse_message(r, susp)
            if not b or not JP.search(b):
                continue
            if re.search(r'[0-9A-Za-z]', b) and len(b) < 10:   # 短 ASCII 混入 = 垃圾
                continue
            yield b

    tak, syu = list(gen(t1)), list(gen(s1))

    extra, seen = [], set()

    def add(s):
        if len(s) >= 2 and JP.search(s) and not re.search(r'[0-9A-Za-z]', s) \
                and not s.startswith('★') and s not in seen:
            seen.add(s); extra.append(s)

    for fn in ('sys.spt', 'charaselect.spt'):
        for r in collect_all(fn):
            add(parse_message(r, susp))
    for r in t2 + s2:
        s = parse_message(r, susp)
        if any(k in s for k in ('演出', 'スタッフロール', '鑑賞音楽')):
            continue
        if re.match(r'^[★%\s]', s):
            continue
        add(s)

    extra = [x for x in extra
             if not any(y != x and x.endswith(y) for y in extra)]
    lines = tak + syu + extra
    body = '\n'.join(lines) + '\n'
    assert '\r' not in body and '\ufffd' not in body
    os.makedirs(OUTDIR, exist_ok=True)
    out = os.path.join(OUTDIR, TITLE + '_全文本.txt')
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(body)

    print('takatora:', len(tak), 'syuichirou:', len(syu), 'extra:', len(extra), 'total:', len(lines))
    print('->', out, os.path.getsize(out), 'bytes')
    bad = [x for x in lines if re.search(r'[A-Za-z]', x)]
    hk = [x for x in lines if re.search(r'[\uff61-\uff9f]', x)]
    print('ASCII-letter lines:', len(bad), 'halfwidth-kana lines:', len(hk))
    for x in (bad + hk)[:30]:
        print('   ', x[:78])


if __name__ == '__main__':
    main()
