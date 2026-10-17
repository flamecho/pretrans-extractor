# -*- coding: utf-8 -*-
"""SNOW BOUND LAND (PSP, Otomate / Idea Factory 2013) 剧本文本提取  —— 自包含

【容器链路】
  ISO9660  PSP_GAME/INSDIR/INSTALL.DNS              [PGD 加密, magic 00 'PGD']
    -> pgdecrypt（tpunix/kirk_engine 的 npdrm/pgd.c, libkirk amctrl）
    -> 内层 CRI CPK（解密产物 @0 起 = "CPK " magic）
    -> CPK 解包 -> script/*（STCM2L 脚本；system/* 是 TIM2 图, etc/sub 是表 -> 均无正文）

【STCM2L 结构（PSP 版, 与 PS2/Switch 版同族）】
  0x00 generator 32B  "STCM2L Jul 12 2010 10:20:01"
  0x20 u32 exports_offset（相对文件起点, = 代码段终点）
  0x50 "GLOBAL_DATA\\0" … "CODE_START_\\0"
      -> 代码段起点 = "CODE_START_" 偏移 + 24
  代码段 = opcode 链, 每条 [u32 size][payload(size-4)]
    文本记录 = [u32 0][u32 L/4][u32 1][u32 L][cp932 text][NUL pad]   (L=A4(len+1))
      记录在 payload 偏移 12 -> 正文/台词片段
      记录在 payload 偏移 24 -> 选项文本 / 符号表条目（switch・sureN・色変化判定・flag 名…）
      记录在 payload 偏移 36 -> 立绘/背景资源名（丢弃）
    换行 / 新框标记 opcode: 12B payload = [0][u32 cmd][u32 flag]  -> 一次点击
    控制流(goto/if) opcode: payload 首字段 0xffffff41            -> 断「段」不断点击

【成行规则】
  一次点击 = 一行；同一点击内相邻文本片段合并；名札(独立人名行)丢弃并断行；
  互斥分支（同一行两版本, 以 0xffffff41 控制流分隔）取一；选项各占一行；
  章节标题卡（序章／第N章／最終章）保留并跨文件去重。

【人名】
  主角可改名 -> 行内 `#Name[0]` 替换为默认名 **ゲルダ**（外核 vndb v12472）。
  独立名札行（`カイ` / `#Name[0]` / `#Color[0]祖母`）丢弃, 不加前缀。

用法:
  python scripts/snowboundland_extract.py <解密后的CPK 或 script脚本目录> <输出txt>
前置（一次性, 见报告）:
  pgdecrypt INSTALL.DNS  ->  INSTALL.DNS.decrypt（即 CPK）
"""
import struct
import re
import os
import sys
import io
import glob
import tempfile
import shutil
import collections
import difflib

A4 = lambda n: (n + 3) & ~3

HERO = {0: 'ゲルダ'}          # 主角默认名（vndb v12472, Nameable Protagonist）

RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_HIRA = re.compile(r'[\u3040-\u309f]')
RE_SYM = re.compile(r'^[A-Za-z0-9_./\\\-:]+$')
RE_NUM = re.compile(r'^\d{1,4}$')
RE_NAME_OK = re.compile(r'^[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff'
                        r'\uff10-\uff19\uff1f\uff01\u3005\uff0d\uff0e]+$')
RE_PLACEHOLDER = re.compile(r'^#Name\[(\d+)\]$')
RE_INLINE_NAME = re.compile(r'#Name\[(\d+)\]')
RE_ANY_TAG = re.compile(r'#(?!Name\[)[A-Za-z_]+\[[^\]]*\]')
RE_ASSET = re.compile(r'^(?:bg|mob|hub|fr|ev|chr|chara|[a-z]{2,5}[-_])[A-Za-z0-9_\-]*$')

# 说话人外部核对名单（vndb v12472 characters）
CHAR_NAMES = {
    'ゲルダ', 'カイ', 'オルヴァ', 'クラエス', 'アージェ', 'イヴァン',
    '悪魔', 'アルフレッド', 'ベイセル', 'フィネ', 'リーゼロッテ', 'リディア',
    'ナタリア', 'ウィル', '雪の女王', '祖母', 'マラン',
}

CHOICE_MARK = {'select', 'switch', 'end'}
SEG_MARKER = 0xffffff41
# 回想/画廊 专用脚本（菜单 UI, 非剧情）-> 整个文件排除
REPLAY_MARKERS = ('どのシーンを見ますか？', 'どちらのシーンを見ますか？', '画廊からのルート')
# 选项候选里的非选项标签（结局名/路线名等 UI）
RE_OPT_NOISE = re.compile(r'(?:[ＥE][ＤD]|[Rr][Oo][Uu][Tt][Ee]|ルート|エンド|ＥＮＤ)$')
# 章节标题卡（扉文）-> 保留
RE_CHAPTITLE = re.compile(
    r'(?:^|[\s\u3000])(?:序章|終章|最終章|第[0-9０-９一二三四五六七八九十]+章)')

_BAD_IN_NAME = '。！？…「」『』（）()、,.!?　'
_PARTICLE_END = 'がをはにへとでもやのねよ'


# ---------------------------------------------------------------- 基础
def scan_records(pay):
    """payload 内 [0][L/4][1][L][text] 记录 -> [(k, text)]"""
    res = []
    n = len(pay)
    for k in range(0, n - 16 + 1, 4):
        f0, f1, f2, f3 = struct.unpack_from('<4I', pay, k)
        if f0 != 0 or f2 != 1:
            continue
        if f3 < 4 or f3 > 0x2000 or f3 % 4 or f1 != f3 // 4:
            continue
        if k + 16 + f3 > n:
            continue
        raw = pay[k + 16:k + 16 + f3].rstrip(b'\x00')
        if not raw or A4(len(raw) + 1) != f3:
            continue
        try:
            s = raw.decode('cp932')
        except Exception:
            continue
        if not s or any(ord(c) < 0x20 for c in s):
            continue
        res.append((k, s))
    return res


def file_tokens(b):
    """STCM2L bytes -> [('brk'|'seg'|'t'|'c'|'a', text)]"""
    if b[:6] != b'STCM2L':
        return None
    exp = struct.unpack_from('<I', b, 0x20)[0]
    ci = b.find(b'CODE_START_')
    if ci < 0:
        return None
    cs = ci + 24
    toks = []
    i = cs
    while i + 4 <= exp:
        bs = struct.unpack_from('<I', b, i)[0]
        if bs < 4 or i + bs > len(b):
            break
        pay = b[i + 4:i + bs]
        ev = []
        # 12B 换行/新框标记：`[a][cmd][flag]`，**a ∈ {0,1} 都是框边界**。
        # ⚠ 只认 a==0 会把「台词框 + 地の文框」粘成一行（`「…」地の文。`）——
        #   实测 a==1 形态如 `[1][0xbf00][4]`，占全部标记的 ~15%，漏掉它即系统性并句。
        if len(pay) == 12 and struct.unpack_from('<I', pay, 0)[0] in (0, 1):
            ev.append((0, 'brk', ''))
        elif len(pay) >= 4 and struct.unpack_from('<I', pay, 0)[0] == SEG_MARKER:
            ev.append((0, 'seg', ''))
        for k, s in scan_records(pay):
            km = {12: 't', 24: 'c', 36: 'a'}.get(k)
            if km:
                ev.append((k, km, s))
        ev.sort(key=lambda x: x[0])
        for _, kind, s in ev:
            toks.append((kind, s))
        i += bs
    return toks


def clean_tags(s):
    s = RE_INLINE_NAME.sub(lambda m: HERO.get(int(m.group(1)), m.group(0)), s)
    s = RE_ANY_TAG.sub('', s)
    s = s.replace('#n', '')
    return s


def is_noise(s):
    if not s:
        return True
    if RE_SYM.match(s) or RE_NUM.match(s):
        return True
    if RE_ASSET.match(s):
        return True
    if s.replace('\n', '').replace('\\n', '') in ('処理開始',):
        return True
    return False


def is_option_noise(s):
    return is_noise(s) or bool(RE_OPT_NOISE.search(s))


def name_of(s):
    return RE_ANY_TAG.sub('', s)


def looks_like_name(s):
    if not s or len(s) > 14:
        return False
    t = RE_ANY_TAG.sub('', RE_INLINE_NAME.sub('', s))
    return bool(t) and RE_NAME_OK.match(t) is not None


def is_name_token(s):
    t = RE_ANY_TAG.sub('', RE_INLINE_NAME.sub('', s)).strip()
    if not t or len(t) > 10:
        return False
    if any(ch in t for ch in _BAD_IN_NAME):
        return False
    if t[-1] in _PARTICLE_END:
        return False
    return True


def is_dialog(s):
    return s[:1] in ('「', '『', '（', '(')


# ---------------------------------------------------------------- 成行
def build(all_toks, labels, global_str):
    lines = []
    seen_chap = set()

    for toks in all_toks:
        opt_idx = set()
        for i, (k, s) in enumerate(toks):
            if k != 'c':
                continue
            for j in range(i + 1, min(len(toks), i + 6)):
                t2 = toks[j][1]
                if t2 in CHOICE_MARK or t2.startswith('sure') or t2 == 'd':
                    opt_idx.add(i)
                    break

        clicks, cur = [], []
        for i, (k, s) in enumerate(toks):
            if k == 'brk':
                if cur:
                    clicks.append(cur)
                cur = []
                continue
            if k == 'seg':
                cur.append(('seg', ''))
                continue
            if k == 't':
                if is_noise(s):
                    continue
                nm0 = name_of(s).strip()
                # `#Name[n]` 是「说话人名/主角占位」记录 —— 必须当**框边界**处理，
                # 否则会被下面的 global_str 静默丢掉，导致「同一行的两个版本」粘成一行
                # （实测：`「それじゃ……行こう、ゲルダ」` + `「それじゃ……行こう、#Name[0]」`）。
                if RE_PLACEHOLDER.match(nm0):
                    cur.append(('N', s))
                    continue
                if looks_like_name(s) and nm0 in labels:
                    cur.append(('N', s))
                    continue
                if is_name_token(s):
                    # 后随「台词 / 心声」的记录 = 名札（「…」台词、「（…）」心声独白）
                    nxt = None
                    for j in range(i + 1, min(len(toks), i + 4)):
                        if toks[j][0] == 't':
                            nxt = toks[j][1]
                            break
                    if nxt and nxt[:1] in ('「', '『', '（', '('):
                        cur.append(('N', s))
                        continue
                if s in global_str:
                    continue
                cur.append(('T', s))
            elif k == 'c' and i in opt_idx:
                if is_option_noise(s) or s in global_str:
                    continue
                cur.append(('O', s))
            elif k == 'c' and RE_CHAPTITLE.search(s):
                if s not in seen_chap:
                    seen_chap.add(s)
                    cur.append(('O', s))
            elif k == 'a':
                if cur:
                    clicks.append(cur)
                    cur = []
        if cur:
            clicks.append(cur)

        for click in clicks:
            units, buf = [], ''
            state = {'name': None}

            def close():
                nonlocal buf
                if buf.strip():
                    units.append((state['name'], buf))
                buf = ''

            for kind, s in click:
                if kind == 'seg':
                    continue
                if kind == 'N':
                    close()
                    state['name'] = s
                    continue
                if kind == 'O':
                    close()
                    units.append(('O', s))
                    continue
                buf += s
            close()

            kept = []
            for u in units:
                if u[0] != 'O' and kept and kept[-1][0] != 'O':
                    a, b = clean_tags(kept[-1][1]), clean_tags(u[1])
                    if len(a) >= 4 and len(b) >= 4:
                        if difflib.SequenceMatcher(None, a, b).ratio() >= 0.75:
                            continue     # 互斥分支 -> 保留前段
                kept.append(u)
            for _, txt in kept:
                t = clean_tags(txt)
                if t.strip() and not is_noise(t):
                    lines.append(t)
    return lines


# ---------------------------------------------------------------- 输入
def load_scripts(src):
    """返回 [(名字, STCM2L bytes)]；src 可为 CPK 或已解包的 script 目录。"""
    if os.path.isdir(src):
        out = []
        for f in sorted(glob.glob(os.path.join(src, '*')),
                        key=lambda p: int(os.path.basename(p))):
            out.append((os.path.basename(f), open(f, 'rb').read()))
        return out
    # CPK
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cpk import CPK
    cpk = CPK(src)
    entries = [e for e in cpk.entries if (e.get('dir') or '') == 'script']
    entries.sort(key=lambda e: int(e['file']))
    out = []
    for e in entries:
        nm = e['name'].encode('latin-1', 'ignore').decode('cp932', 'replace')
        out.append((nm.split('/')[-1], cpk.raw(e)))
    return out


def main():
    src, outpath = sys.argv[1], sys.argv[2]
    per, freq = [], collections.Counter()
    skipped = []
    for name, b in load_scripts(src):
        if any(m.encode('cp932') in b for m in REPLAY_MARKERS):
            skipped.append(name)
            continue
        toks = file_tokens(b)
        if toks is None:
            continue
        per.append(toks)
        for k, s in toks:
            if k in ('t', 'c'):
                freq[s] += 1
    if skipped:
        print('skip replay/menu files:', skipped, file=sys.stderr)

    global_str = {s for s, c in freq.items()
                  if c >= 12 and s[:1] not in ('「', '『', '（', '(')
                  and not RE_HIRA.search(s)}

    labels = set()
    seq = [s for toks in per for k, s in toks if k == 't']
    for i, s in enumerate(seq):
        nm = name_of(s)
        if is_noise(s) or not looks_like_name(s) or is_dialog(s):
            continue
        if RE_HIRA.search(nm) or freq[s] < 2:
            continue
        for j in range(i + 1, min(len(seq), i + 5)):
            nx = seq[j]
            if is_noise(nx):
                continue
            if nx[:1] in ('「', '『'):
                labels.add(nm)
            break
    labels |= CHAR_NAMES

    lines = build(per, labels, global_str)
    with io.open(outpath, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('files=%d lines=%d -> %s' % (len(per), len(lines), outpath))


if __name__ == '__main__':
    main()
