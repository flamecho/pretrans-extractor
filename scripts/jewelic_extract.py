# -*- coding: utf-8 -*-
"""Jewelic Nightmare (PSP, Otomate 2013, ULJM06326) 全文本提取

【容器链】
  CHD(v5/zstd) → ISO9660 → PSP_GAME/INSDIR/INSTALL.DNS（PGD, key_index=1/drm_type=1）
    --scripts/pgdecrypt.exe--> 内层 CRI CPK → script/*（STCM2L）＋ sub/10（覚書＝用語辞典）
  ※ PSP_GAME/USRDIR/UMD.cpk 只装 voice/ 与 movie/，无正文。

【STCM2L 记录】
  代码段起点 = "CODE_START_" + 24；每条 = [u32 size][payload]
  文本记录      = [0][L/4][1][L][cp932 text(pad)]，记录落在 payload 偏移 12
  其后 u32      = 命令码：0xd3/0xd2/0xd4/0x7a = 上屏文本；0xbf = 名札辞書(定义表)
  选项          = payload 偏移 24 的记录且其后 6 token 内有 select/switch/sure*
  资源名        = payload 偏移 36 的记录（立绘/背景），丢弃
  一次点击      = payload 12 字节标记 [a][cmd][flag]（a∈{0,1}）
  控制流        = payload 首字段 0xffffff41（断「段」不断点击）

【成行】一次点击 = 一行；同框多行文本拼接；名札丢弃并断行；互斥分支取一；
        章节/宝石的结尾卡保留；调试脚本（1000〜1005）与 CPK 内副本条目整档排除。
【主角】月代 みちる（vndb v12436, Nameable）⇒ #Name[0]=月代, #Name[1]=みちる 行内替换。

用法：python jewelic_extract.py <解密后的CPK 或 script 目录> <输出txt> [--prov]
前置：pgdecrypt.exe INSTALL.DNS → INSTALL.DNS.decrypt（= CPK）
"""
import struct, re, os, sys, io, glob, collections, difflib

A4 = lambda n: (n + 3) & ~3

HERO = {0: '月代', 1: 'みちる'}          # 主角默认名（vndb v12436）

RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\uff01\uff1f\u3000\u2026\u300c\u300d\u300e\u300f\uff08\uff09]')
RE_KANA_KANJI = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_SYM = re.compile(r'^[A-Za-z0-9_./\\\-:]+$')
RE_NUM = re.compile(r'^\d{1,4}$')
RE_NAME_OK = re.compile(r'^[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff'
                        r'\uff10-\uff19\uff1f\uff01\u3005\uff0d\uff0e]+$')
RE_PLACEHOLDER = re.compile(r'^#Name\[(\d+)\]$')
RE_INLINE_NAME = re.compile(r'#Name\[(\d+)\]')
RE_ANY_TAG = re.compile(r'#(?!Name\[)[A-Za-z_]+\[[^\]]*\]')
RE_ASSET = re.compile(r'^(?:bg|mob|hub|fr|ev|chr|chara|[a-z]{2,5}[-_])[A-Za-z0-9_\-]*$')
RE_JPANY = re.compile(r'[぀-ゟ゠-ヿ一-鿿々…「」『』（）！？、。]')
TEXT_CMDS = {0xd2, 0xd3, 0xd4, 0x7a}

CMD_NAME_DICT = 0xbf                     # 名札辞書（每档开头的说话人/道具名定义表）
SEG_MARKER = 0xffffff41
MENU_NOISE = {'誰とのイベントを見ますか？', 'どちらのシーンを見ますか？',
              '解放されていません。', '処理開始', '処理開始\n'}
EXCLUDE_FILES = { '1000', '1001', '1002', '1003', '1004', '1005'}   # 136=回想菜单；1000〜1005=调试测试
RE_OPT_NOISE = re.compile(r'(?:[ＥE][ＤD]|[Rr][Oo][Uu][Tt][Ee]|ルート|エンド|ＥＮＤ|end)$')

_BAD_IN_NAME = '。！？…「」『』（）()、,.!?　'
_PARTICLE_END = 'がをはにへとでもやのねよ'


def scan_records(pay):
    """-> [(k, text, cmd)]；cmd 为记录后紧随的 u32 命令码（可能 None）"""
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
        cmd = None
        p = k + 16 + f3 + 4
        if p + 4 <= n:
            cmd = struct.unpack_from('<I', pay, p)[0]
        res.append((k, s, cmd))
    return res


def file_ops(b):
    if b[:6] != b'STCM2L':
        return None
    exp = struct.unpack_from('<I', b, 0x20)[0]
    ci = b.find(b'CODE_START_')
    if ci < 0:
        return None
    i, idx, out = ci + 24, 0, []
    while i + 4 <= exp:
        bs = struct.unpack_from('<I', b, i)[0]
        if bs < 4 or i + bs > len(b):
            break
        pay = b[i + 4:i + bs]
        mk = None
        if len(pay) == 12 and struct.unpack_from('<I', pay, 0)[0] in (0, 1):
            mk = 'brk'
        elif len(pay) >= 4 and struct.unpack_from('<I', pay, 0)[0] == SEG_MARKER:
            mk = 'seg'
        # 末尾 16 字节内的 u32（正文命令码常在末尾 cmd+flag 组的第一个）
        tailwords = set()
        for off in range(4, min(20, len(pay)) + 1, 4):
            tailwords.add(struct.unpack_from('<I', pay, len(pay) - off)[0])
        out.append((idx, mk, scan_records(pay), tailwords))
        i += bs
        idx += 1
    return out


_BAD_PREFIX = '。、！？…―─「」『』（）'


def strip_speaker_prefix(s):
    """行首「名札」+「台词」⇒ 去名札（§0：不加说话人前缀）。
    名札常被直接烘进文本记录（`おばあちゃん「…」`），故在输出层剥离。"""
    m = re.match(r'^([^\s「」（）]{1,12})「', s)
    if m and not any(ch in m.group(1) for ch in _BAD_PREFIX):
        return s[m.end() - 1:]
    return s


def clean(s):
    s = RE_INLINE_NAME.sub(lambda m: HERO.get(int(m.group(1)), m.group(0)), s)
    s = RE_ANY_TAG.sub('', s)
    s = s.replace('#n', '')
    return s


def is_code_like(s):
    """资源名/纯编号/纯 ASCII 参数值/单字符半角假名控制码（不是正文片段）"""
    if not s:
        return False
    if len(s) == 1 and '｡' <= s <= 'ﾟ':
        return True
    return bool(RE_SYM.match(s)) or bool(RE_NUM.match(s)) or bool(RE_ASSET.match(s))


def is_noise(s):
    if not s:
        return True
    if is_code_like(s):
        return True
    if not RE_JPANY.search(s):          # 连假名/汉字/日文标点都没有 ⇒ 'Z'、'OK' 等占位
        return True
    return False


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


def load_scripts(src):
    if os.path.isdir(src):
        out = []
        for f in sorted(glob.glob(os.path.join(src, '*'))):
            nm = os.path.basename(f)
            if not nm.isdigit() or nm in EXCLUDE_FILES:
                continue
            out.append((nm, open(f, 'rb').read()))
        return out
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cpk import CPK
    cpk = CPK(src)
    ent = [e for e in cpk.entries if (e.get('dir') or '') == 'script']
    ent.sort(key=lambda e: int(e['file']) if e['file'].isdigit() else 1 << 30)
    out = []
    for e in ent:
        nm = e['file']
        if not nm.isdigit() or nm in EXCLUDE_FILES:
            continue
        out.append((nm, cpk.raw(e)))
    return out


def build(files, labels, global_str, prov=None):
    lines = []
    for name, ops in files:
        clicks, cur = [], []
        prev_dict = False
        for idx, mk, recs, tail in ops:
            ev = []
            is_dict = any(c == CMD_NAME_DICT for k2, s2, c in recs if k2 == 12)
            if not is_dict and prev_dict:
                rs = [(k2, s2, c) for k2, s2, c in recs if k2 == 12]
                # 名札辞書的末条：命令码为 0（无后继），沿续前一条判定为辞書
                if len(rs) == 1 and rs[0][2] in (0, None) and is_name_token(rs[0][1]):
                    is_dict = True
            prev_dict = is_dict
            if mk == 'brk':
                ev.append((-1, 'brk', ''))
            elif mk == 'seg':
                ev.append((-1, 'seg', ''))
            has12 = any(k == 12 for k, s, c in recs)
            for k, s, cmd in recs:
                km = {12: 't', 24: 'c', 36: 'a'}.get(k)
                if km:
                    ev.append((k, km, s, cmd))
            if not has12 and (tail & TEXT_CMDS):
                cand = sorted((k, s) for k, s, c in recs
                              if k >= 48 and len(s) > 2 and not is_code_like(s)
                              and RE_JPANY.search(s))
                if len(cand) >= 2:
                    txts = [x[1] for x in cand]
                    # 本作「一框＝一条文本记录」，故 payload 内出现 ≥2 条文本 = 同一句的 A/B 双版：
                    #   A＝字面默认名，B＝#Name 宏 / 代词（あなた・きみ・オマエ…）。只保留 A 版。
                    # 两版条数可不等（A 1 行 / B 2 行）⇒ 在 1..n-1 找「前段 vs 后段」最相似的分割点。
                    if len(txts) == 2:
                        txts = txts[:1]      # n=2 必为 A₁/B₁，直接取 A
                    else:
                        best_r, best_s = 0.0, 0
                        for s in range(1, len(txts)):
                            a = clean(''.join(txts[:s]))
                            b = clean(''.join(txts[s:]))
                            r = difflib.SequenceMatcher(None, a, b).ratio()
                            if r > best_r:
                                best_r, best_s = r, s
                        if best_r >= 0.45:
                            txts = txts[:best_s]
                    ev.append((48, 't', ''.join(txts), None))
            ev.sort(key=lambda x: x[0])

            opt_idx = set()
            for i2, it in enumerate(ev):
                if it[1] != 'c':
                    continue
                for j in range(i2 + 1, min(len(ev), i2 + 6)):
                    t2 = ev[j][2]
                    if t2 in ('select', 'switch', 'end') or t2.startswith('sure'):
                        opt_idx.add(i2)
                        break

            for i2, it in enumerate(ev):
                k, kind, s = it[0], it[1], it[2]
                cmd = it[3] if len(it) > 3 else None
                if kind == 'brk':
                    if cur:
                        clicks.append(cur)
                    cur = []
                    continue
                if kind == 'seg':
                    cur.append(('seg', ''))
                    continue
                if kind == 't':
                    if is_dict:                       # 名札辞書定义表
                        for part in re.findall(r'#Name\[\d+\]|[^\s]+', s):
                            if is_name_token(part):
                                labels.add(part)
                        continue
                    if is_code_like(s):
                        continue
                    nm0 = RE_ANY_TAG.sub('', s).strip()
                    if RE_PLACEHOLDER.match(nm0):
                        cur.append(('N', s))
                        continue
                    if looks_like_name(s) and nm0 in labels:
                        cur.append(('N', s))
                        continue
                    if is_name_token(s):
                        nxt = None
                        for j in range(i2 + 1, min(len(ev), i2 + 4)):
                            if ev[j][1] == 't':
                                nxt = ev[j][2]
                                break
                        if nxt and nxt[:1] in ('「', '『', '（', '('):
                            cur.append(('N', s))
                            continue
                    if s in global_str:
                        continue
                    cur.append(('T', s))
                elif kind == 'c' and i2 in opt_idx:
                    if is_noise(s) or s in global_str:
                        continue
                    if RE_OPT_NOISE.search(s):
                        continue
                    cur.append(('O', s))
                elif kind == 'a':
                    if cur:
                        clicks.append(cur)
                        cur = []
        if cur:
            clicks.append(cur)

        for click in clicks:
            units, buf = [], ''

            def close():
                nonlocal buf
                if buf.strip():
                    units.append((None, buf))
                buf = ''

            for kind, s in click:
                if kind == 'seg':
                    close()          # 互斥分支分隔：断 unit，交给 0.75 相似度取一
                    continue
                if kind == 'N':
                    close()
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
                    a, b = clean(kept[-1][1]), clean(u[1])
                    if len(a) >= 4 and len(b) >= 4:
                        if difflib.SequenceMatcher(None, a, b).ratio() >= 0.75:
                            continue
                kept.append(u)
            for _, txt in kept:
                t = clean(txt).strip('\n')
                t = strip_speaker_prefix(t)
                if len(t) >= 8 and len(t) % 2 == 0:      # 兜底：整行恰为两半同名（变体残留）
                    h = len(t) // 2
                    if t[:h] == t[h:]:
                        t = t[:h]
                if '\\n' in t or t.strip() in MENU_NOISE:
                    continue
                if t.strip() and not is_noise(t):
                    lines.append(t)
                    if prov is not None:
                        prov.append((name, t))
    return lines


# ---------------------------------------------------------------- 用語辞典（sub/10 = 覚書）
def term_dict(path='x_sub/sub/10'):
    if not os.path.exists(path):
        return []
    d = open(path, 'rb').read()
    cnt = struct.unpack_from('<I', d, 0)[0]
    head = 8
    stride = (len(d) - head) // cnt
    out = []
    for i in range(cnt):
        rec = d[head + i * stride: head + (i + 1) * stride]
        if len(rec) < stride:
            break

        def cut(b):
            t = b.decode('cp932', 'replace')
            return t.split('\x00')[0].split('\uf8f3')[0].strip()

        head_word = cut(rec[34:74])
        desc = cut(rec[74:]).replace('#n', '').replace('\n', '').strip()
        if not head_word or not desc:
            continue
        out.append('【%s】%s' % (head_word, desc))
    return out


def main():
    src, outpath = sys.argv[1], sys.argv[2]
    want_prov = '--prov' in sys.argv

    files_raw = load_scripts(src)
    files, freq = [], collections.Counter()
    for name, b in files_raw:
        ops = file_ops(b)
        if ops is None:
            print('not STCM2L:', name, file=sys.stderr)
            continue
        files.append((name, ops))
        for _op in ops:
            recs = _op[2]
            for k, s, cmd in recs:
                if k in (12, 24):
                    freq[s] += 1

    global_str = {s for s, c in freq.items()
                  if c >= 12 and s[:1] not in ('「', '『', '（', '(')
                  and not re.search(r'[\u3040-\u309f]', s)}
    print('global_str', len(global_str), file=sys.stderr)

    labels = set()
    seq = [s for _, ops in files for op in ops for k, s, cmd in op[2] if k == 12]
    for i, s in enumerate(seq):
        nm = RE_ANY_TAG.sub('', s)
        if is_noise(s) or not looks_like_name(s) or s[:1] in ('「', '『', '（', '('):
            continue
        if re.search(r'[\u3040-\u309f]', nm) or freq[s] < 2:
            continue
        for j in range(i + 1, min(len(seq), i + 5)):
            nx = seq[j]
            if is_noise(nx):
                continue
            if nx[:1] in ('「', '『'):
                labels.add(nm)
            break
    print('labels', len(labels), sorted(labels)[:40], file=sys.stderr)

    prov = [] if want_prov else None
    lines = build(files, labels, global_str, prov)
    dedup = []
    for t in lines:
        if dedup and t == dedup[-1] and len(t) >= 12:
            continue
        dedup.append(t)
    lines = dedup
    terms = term_dict()
    if terms:
        lines.extend(terms)
    with io.open(outpath, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('files=%d lines=%d terms=%d -> %s' % (len(files), len(lines) - len(terms), len(terms), outpath),
          file=sys.stderr)
    if prov is not None:
        with io.open(outpath + '.prov.tsv', 'w', encoding='utf-8') as o:
            for name, t in prov:
                o.write('%s\t%s\n' % (name, t))


if __name__ == '__main__':
    main()
