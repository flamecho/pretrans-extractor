#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ネオアンジェリークSpecial (PSP-JP, Koei) 全文本提取

容器  : USRDIR/DATA.BIN = Koei CDAR v4
        16B 头 {magic'CDAR', ver=4, count, unk} + count*u32 + count*12B {off, decompSize, size}
        条目若为 zlib(78 9c/01/da) 则 inflate；子条目可为嵌套 CDAR
引擎  : Koei Ruby Party CDAR 脚本 VM（与 コルダ / 遥か 同族，逐作需重证）
文本  : 04 <u16 len> <cp932> 00      (记录驱动扫描; len 含结尾 00)
行内  : 1b XX 样式码(剔除) ; 0x0a 框内软换行(合并)
分隔  : 1e8b052422(BOUND) / 1ef907874c(CLOSE) / 1ec7094774(C7) / 1e910bbda0(M91) -> 一次点击
选项  : 1e7203910b 前导的 04 记录 = 选项, 1ec6028706 = 选项提示
名字宏: 1ecf021e0a 后的 02/1e <u32> 值。本作变量定义表(DATA.BIN root#161「主人公/名前/愛称」)实证:
        0x06010233 = 主人公.名前(默认 アンジェリーク) / 0x05fa0288 = 主人公.愛称(默认 アンジェ)
        0x0d8503f6 = 主人公名(1e 通道)          (默认 アンジェリーク)
用語辞典: root#957 情报模块 —— `（読み）解説` 记录 + `07 ff ff 02 <idx>` 取见出し語表(root#1292)
        -> 输出 `【見出し語】解説`, 并入末尾
排除  : 条目级 —— 1e9003cd(メモリースティック通知) / 1ed7036411(ギャラリー·デバッグ·メニュー)
        / 0282021d06(ヘルプ) / 1e73077434(チュートリアル·通知)
        记录级 —— イベントラベル / 条件: / ・項目 / 増加→通知 / 操作ボタン記号 / ASCII
用法  : python scripts/neoange_psp_extract.py <DATA.BIN> <out.txt> [--given X] [--nick Y] [--map F]
"""
import sys, os, re, struct, zlib, hashlib, argparse, collections

BOUND = b'\x1e\x8b\x05\x24\x22'
CLOSE = b'\x1e\xf9\x07\x87\x4c'
C7 = b'\x1e\xc7\x09\x47\x74'
M91 = b'\x1e\x91\x0b\xbd\xa0'
SEPS = (BOUND, C7, M91)
INS = b'\x1e\xcf\x02\x1e\x0a'
OPT = b'\x1e\x72\x03\x91\x0b'
ZMAGIC = (b'\x78\x9c', b'\x78\x01', b'\x78\xda')
TBL_MAGIC = bytes.fromhex('9b474074')             # 見出し語表(root#1292) の魔数
TBL_SIG = '天使の庭リース'.encode('cp932')
TBL_SIG2 = '聖都セレスティザム'.encode('cp932')

DROP_HEADS = {
    bytes.fromhex('1e9003cd10'): 'sys_notify',
    bytes.fromhex('1ed7036411'): 'gallery_debug',
    bytes.fromhex('0282021d06'): 'help',
    bytes.fromhex('1e73077434'): 'tutorial',
}
# 信息模块(依頼一覧/話題一覧/人物情報)数据叶子 —— 菜单载体, 非正文
INFO_MARKERS = tuple(s.encode('cp932') for s in (
    'この話題は最初から知っています',
    '依頼主に会えば',
    '（主人公のプロフィールは削除予定',
))
MACRO = {0x06010233: 'given', 0x0d8503f6: 'given', 0x05fa0288: 'nick'}
SEM = {
    0x0c5e03a3: '〔同行者名〕', 0x250305c2: '〔人物名〕', 0x108f03c8: '〔スチル名〕',
    0x3c9a072f: '〔デザート名〕', 0x10270388: '〔材料名〕',
    0x5254086c: '〔用語〕', 0x1e84051b: '〔用語〕', 0x4ff30875: '〔用語〕',
    0x1a8b0518: '〔用語〕', 0x0d0f03c7: '〔用語〕', 0x21580589: '〔用語〕',
    0x05940274: '〔用語〕', 0x067a02ae: '〔用語〕', 0x191f04da: '〔用語〕',
    0x283405e3: '〔用語〕', 0x0db403e5: '〔用語〕', 0x17c60544: '〔用語〕',
}
CONSTS = {0x15500462, 0x1af9056c, 0x0d6503f2, 0x13d404bc, 0x019200ff,
          0x0b49032e, 0x1f470562} | set(range(0x40))


# ---------------- CDAR ----------------
def _inflate(blob):
    if blob[:2] in ZMAGIC:
        try:
            return zlib.decompress(blob)
        except Exception:
            return None
    return blob


def leaves(path):
    f = open(path, 'rb')

    def walk(off, size, label, depth):
        f.seek(off)
        head = f.read(16)
        if len(head) < 16 or head[:4] != b'CDAR':
            return
        _, ver, cnt, _u = struct.unpack('<4sIII', head)
        if ver != 4 or cnt > 100000:
            return
        f.seek(off + 16 + cnt * 4)
        tbl = f.read(cnt * 12)
        for i in range(cnt):
            o, dec, st = struct.unpack_from('<III', tbl, i * 12)
            if st == 0:
                continue
            f.seek(off + o)
            d = _inflate(f.read(st))
            if d is None:
                continue
            if d[:4] == b'CDAR' and depth < 4:
                yield from walk(off + o, len(d), '%s#%d' % (label, i), depth + 1)
            else:
                yield '%s#%d' % (label, i), d

    yield from walk(0, os.path.getsize(path), 'root', 0)
    f.close()


# ---------------- 文本记录 ----------------
_CTRL_OK = {0x09, 0x0a, 0x1b}


def decode_rec(body):
    out, i, n = [], 0, len(body)
    while i < n:
        c = body[i]
        if c == 0x1b:
            i += 2
            continue
        if c < 0x20:
            out.append('\n' if c == 0x0a else chr(c))
            i += 1
            continue
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            if i + 2 <= n:
                out.append(body[i:i + 2].decode('cp932', 'replace'))
                i += 2
            else:
                i += 1
        else:
            out.append(chr(c))
            i += 1
    return ''.join(out)


def valid_record(b, i):
    n = len(b)
    if i + 3 > n or b[i] != 4:
        return None
    ln = struct.unpack_from('<H', b, i + 1)[0]
    if ln < 2 or ln > 4000:
        return None
    e = i + 3 + ln
    if e > n or b[e - 1] != 0:
        return None
    body = b[i + 3:e - 1]
    if b'\x00' in body:
        return None
    for x in body:
        if x < 0x20 and x not in _CTRL_OK:
            return None
    return (i, e, decode_rec(body))


def find_records(b):
    out, i, n, find = [], 0, len(b), b.find
    while True:
        i = find(b'\x04', i)
        if i < 0 or i >= n - 3:
            break
        r = valid_record(b, i)
        if r:
            out.append(r)
            i = r[1]
        else:
            i += 1
    return out


# ---------------- 名字宏 / 表参照 ----------------
def parse_ins(gap):
    """返回 gap 内 INS 块列表: [(parts, tbl_idx)]，tbl_idx = `07 <u16>` 后的 `02 <u32>`。"""
    blocks, pos = [], 0
    while True:
        k = gap.find(INS, pos)
        if k < 0:
            break
        p, parts, tbl_idx, saw07 = k + len(INS), [], None, False
        while p < len(gap):
            op = gap[p]
            if op in (0x02, 0x1e) and p + 5 <= len(gap):
                v = struct.unpack_from('<I', gap, p + 1)[0]
                if saw07 and op == 0x02:
                    tbl_idx = v
                elif v not in CONSTS:
                    parts.append(v)
                saw07 = False
                p += 5
            elif op == 0x07 and p + 3 <= len(gap):
                saw07 = True
                p += 3
            elif op == 0x0d:
                p += 1
            else:
                break
        blocks.append((parts, tbl_idx))
        pos = p if p > k else k + 1
    return blocks


def resolve(parts, tbl_idx, names, tbl, unres):
    # 07 <u16> 索引 + 名字变量并存 = 「按索引指定的人物名」-> 语义占位
    if tbl_idx is not None and parts and parts[-1] in MACRO:
        unres['sem:〔人物名〕'] += 1
        return ('text', '〔人物名〕')
    if parts and parts[-1] in MACRO:
        return ('text', names[MACRO[parts[-1]]])
    if tbl_idx is not None and not parts:
        s = tbl[tbl_idx + 1] if 0 <= tbl_idx + 1 < len(tbl) else None
        if s:
            return ('tbl', s)
        unres['tbl_bad'] += 1
        return None
    if not parts:
        return None
    if len(parts) == 1 and parts[0] in SEM:
        unres['sem:' + SEM[parts[0]]] += 1
        return ('text', SEM[parts[0]])
    head = next((v for v in parts if v in SEM), None)
    if head is not None and len(parts) <= 4:
        unres['sem:' + SEM[head]] += 1
        return ('text', SEM[head])
    unres['%08x' % parts[0]] += 1
    return ('text', '〔未解析:%08x〕' % parts[0])


# ---------------- 记录过滤 ----------------
RE_LABEL = re.compile(r'^(イベント|システム|スチル|サウンド|ＢＧＭ|シナリオ|スクリプト|ヘルプ)[・_／/]')
RE_EVENT = re.compile(r'^(日常|誕生日|恋愛|夜想祭|雪祈祭|特別|スペシャル|序章|終章)[～_0-9０-９]')
RE_LABEL2 = re.compile(
    r'^[承起結][ⅠⅡⅢⅣⅤⅥ]$'
    r'|恋愛[０-９0-9]+(誘導|手遅れ|成功|失敗|終了)'
    r'|の[０-９0-9]+番目の会話$'
    r'|^タナトスの噂[０-９0-9]'
    r'|^分岐ミス'
    r'|^(成功|失敗)終了$'
    r'|^(屋外|屋内|室内|街中)[０-９0-9１-９]$'
    r'|エンディング[０-９0-9]?$'
    r'|^(FV|ＦＶ)'
    r'|^ネコの鳴き声[０-９0-9]'
    r'|(に誘導|フラグをセット|の初期化終了|を消去)$'
    r'|フラグ[ＯＯＮF]+$'
    r'|^[起承転結]$'
    r'|^(ラスボス|中ボス|大ボス)$'
    r'|(エピローグ|オープニング|チュートリアル)$'
    r'|^ビンゴトーク'
    r'|(入手|段階更新|上限セット|救援)$'
    r'|^.{1,8}について$')
RE_NOTIFY = re.compile(r'(友好度|幸福度|ポイント|好感度)(増加|減少|上昇|下降)|→$|になった$')
RE_NOTIFY2 = re.compile(r'^[^。！？]{0,24}(」入手|」を知った|を請け負えます|を知った|」表示|」再生|」達成|」発生|」追加)$')
RE_BTN = re.compile(r'[㊧㊨㊤㊦㊥]')
CIRC = set('①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳')


def is_drop(t):
    if not t:
        return True
    if RE_LABEL.match(t) or RE_EVENT.match(t) or RE_LABEL2.search(t):
        return True
    if '_' in t:
        return True
    if t.startswith('・') or t.startswith('条件：') or t.startswith('このメッセージは表示されない'):
        return True
    if RE_NOTIFY.search(t) or RE_NOTIFY2.match(t):
        return True
    if RE_BTN.search(t):
        return True
    if sum(1 for c in t if c in CIRC) >= 2:
        return True
    if all(ord(c) < 0x80 for c in t):
        return True      # 纯 ASCII = 非日文文本(标识符/调试串)
    if '\ufffd' in t or any(0xE000 <= ord(c) <= 0xF8FF for c in t):
        return True      # 解码失败 / PUA = 二进制误命中
    return False


def clean(t):
    t = re.sub(r'[\u3000]*\n[\u3000]*', '', t)
    return t.replace('\t', '').replace('\n', '')


RE_GLOSS = re.compile(r'^（[ぁ-んァ-ヶー・]+）')


def gap_tbl_idx(gap):
    """取 gap 中最后一个 `07 ff ff 02 <u32>` 的索引（见出し語表参照）。"""
    k = gap.rfind(b'\x07\xff\xff')
    if k >= 0 and k + 7 <= len(gap) and gap[k + 3] == 0x02:
        return struct.unpack_from('<I', gap, k + 4)[0]
    return None


# ---------------- 成行 ----------------
def process(b, names, tbl, diag, unres):
    """返回 (lines, glosses)。lines = 正文+选项; glosses = 用語辞典行。"""
    recs = find_records(b)
    if not recs:
        return [], []
    is_gloss = sum(1 for _, _, t in recs if RE_GLOSS.match(clean(t))) >= max(2, len(recs) * 0.4)
    out, gl = [], []
    cur, cur_opt, cur_head = [], False, None
    for i, (s, e, t) in enumerate(recs):
        gap = b[(recs[i - 1][1] if i > 0 else 0):s]
        # 换框符 = BOUND/C7/M91（**显式换框**，与 INS 位置无关）;
        # CLOSE/INS 本身不换框 —— 名字插入(INS)只是把值绑到后文，仍属同一文本框。
        sep = any(x in gap for x in SEPS)
        if sep and cur:
            out.append((''.join(cur), cur_opt, cur_head))
            cur, cur_opt, cur_head = [], False, None
        opt = OPT in gap[-24:]
        if is_gloss:
            gidx = gap_tbl_idx(gap)
            if gidx is not None and 0 <= gidx + 1 < len(tbl):
                if cur_head is None:
                    cur_head = tbl[gidx + 1]
            elif gidx is not None:
                unres['tbl_bad'] += 1
        for parts, ti in parse_ins(gap):
            r = resolve(parts, ti, names, tbl, unres)
            if r:
                cur.append(r[1])
                if r[0] == 'tbl' and cur_head is None:
                    cur_head = r[1]
        txt = clean(t)
        if is_drop(txt):
            diag['drop_rec'] += 1
            continue
        cur.append(txt)
        cur_opt = cur_opt or opt
        nxt = recs[i + 1][0] if i + 1 < len(recs) else len(b)
        after = b[e:nxt]
        if not (after.startswith(CLOSE) or after.startswith(INS)):
            out.append((''.join(cur), cur_opt, cur_head))
            cur, cur_opt, cur_head = [], False, None
    if cur:
        out.append((''.join(cur), cur_opt, cur_head))

    lines = []
    for txt, opt, head in out:
        if not txt:
            continue
        if is_gloss:
            m = RE_GLOSS.match(txt)
            if m:
                head2 = head or ''
                body = txt[m.end():]
                if head2 and body.startswith(head2):
                    body = body[len(head2):]
                if not head2:
                    head2 = '〔未解析见出し語〕'
                    unres['gloss_nohead'] += 1
                gl.append('【%s】%s' % (head2, body))
                continue
        if opt:
            diag['option'] += 1
        lines.append(txt)
    return lines, gl


def load_tbl(path):
    """見出し語表 = magic 9b474074 且つ先头为 天使の庭リース/聖都セレスティザム 的叶子; T[idx+1]。"""
    for lab, d in leaves(path):
        if d[:4] == TBL_MAGIC and TBL_SIG in d and TBL_SIG2 in d:
            ss = [m.group().decode('cp932', 'replace')
                  for m in re.finditer(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc])+', d)]
            if len(ss) > 500:
                return ss, lab
    return [], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('out')
    ap.add_argument('--given', default='アンジェリーク')
    ap.add_argument('--nick', default='アンジェ')
    ap.add_argument('--map', default=None)
    a = ap.parse_args()
    names = {'given': a.given, 'nick': a.nick}

    tbl, tbl_lab = load_tbl(a.data)
    print('見出し語表: %s (%d 项)' % (tbl_lab, len(tbl)))

    lines, glosses, srcs = [], [], []
    seen, diag, unres = set(), collections.Counter(), collections.Counter()
    diag_samples = []
    n_leaf = n_script = n_opt = 0
    for lab, d in leaves(a.data):
        n_leaf += 1
        if len(d) < 32 or d[:4] in (b'TIM2', b'RIFF'):
            continue
        hd = DROP_HEADS.get(d[:5])
        if hd:
            diag['drop_' + hd] += 1
            continue
        if any(m in d for m in INFO_MARKERS):
            diag['drop_info_data'] += 1
            continue
        if len(d) > 1 << 20 and BOUND not in d and CLOSE not in d:
            diag['skip_big'] += 1
            continue
        h = hashlib.md5(d).digest()
        if h in seen:
            diag['dedup'] += 1
            continue
        seen.add(h)
        ms, gl = process(d, names, tbl, diag, unres)
        if not ms and not gl:
            if d.count(CLOSE) >= 3 or d.count(BOUND) >= 3:
                diag['script_no_output'] += 1
                if len(diag_samples) < 20:
                    diag_samples.append((lab, len(d)))
            continue
        n_script += 1
        for txt in ms:
            if not txt:
                continue
            lines.append(txt)
            srcs.append(lab)
        for g in gl:
            glosses.append(g)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines + glosses) + '\n')
    if a.map:
        with open(a.map, 'w', encoding='utf-8', newline='\n') as f:
            for i, s in enumerate(srcs, 1):
                f.write('%d\t%s\n' % (i, s))
    print('leaves=%d script_leaf=%d lines=%d gloss=%d options=%d'
          % (n_leaf, n_script, len(lines), len(glosses), diag.get('option', 0)))
    print('diag:', dict(diag))
    print('== 宏解析统计（sem: = 语义占位）==')
    for v, n in unres.most_common(30):
        print('  %s x%d' % (v, n))
    if diag_samples:
        print('== 有分隔符但无输出的条目 ==')
        for lab, sz in diag_samples:
            print('   %s size=%d' % (lab, sz))


if __name__ == '__main__':
    main()
