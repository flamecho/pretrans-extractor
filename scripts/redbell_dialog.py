#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""レッドベルの慟哭 正文提取（成品生成）。

★ 与 ネオンクラッシュ 同构（2026-10-26 实证）：
  `CMsg.Text.value` = `作者号,语音资源名,语音变体名`（如 `6,@06_0198,@06_0198z`、`0,EV37_0101,moge`），
  **不含正文**；真日文正文 = 该 CMsg 前面连续的 `CommentScriptLine.commentText`，按序直接拼接。

输入是 W1 dump 的 Script 原始对象字节（`_w_W1_redbell/nani/*.bin`，无 typetree 也能解）：
  16B m_GameObject | 4B m_Enabled | 12B m_Script | string m_Name
  u32 行数 n，随后 n×8B {rid u32, u32 0}
  i32 ver=2 | i32 refCount
  每个 ref：u32 rid, u32 0, string 类名, string ns, string asm, 然后**直接**跟数据（无 dataSize）
    CommentScriptLine : u32 lineIndex, string lineHash, string commentText
    CommandScriptLine : u32 lineIndex, string lineHash, u32 目标rid → 指向 CMsg
    EmptyScriptLine   : u32 lineIndex, string lineHash

用法: python scripts/redbell_dialog.py <nani目录> <all.tsv> [--final 成品.txt]
"""
import argparse
import glob
import os
import re
import struct

JP = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')
# 行尾挂的资源 id（`c04p0`、`c03p5` …，来自 @cCharaAdd c04p01_a,C,C,N）——全库 179 处，只有正文行尾的才会漏
INLINE_CODE = re.compile(r'[a-z]\d{2}[a-z]\d+(_[a-z0-9]+)?')
# 行首名札（`ロドス・ハートフィールド「…」`；不含句读、不以助词收尾才剥）
NAME_TAG = re.compile(r'^[^\s。、！？…「」『』（）?!：:]{1,16}(?=「|（|『)')
PART_END = re.compile(r'(は|が|を|に|で|と|も|の|へ|や|から|まで|より|て|ば|る|た|だ)$')
CLASSES = ('CommentScriptLine', 'CommandScriptLine', 'EmptyScriptLine', 'LabelScriptLine', 'CMsg')
SKIP_HEAD = ('◆', '◇', '＝', '=', '■', '●', '＊', '*', '※')
SKIP_WORD = ('話者名', '演技', 'BGM', 'SE：', 'SE:', '登場人物', 'pg遷移', 'pg構築', '演出',
             '名前表記', '読み：', '読み:', '字幕', 'ルビ', '注釈', 'メモ')


def rdstr(d, o):
    n = struct.unpack_from('<I', d, o)[0]
    o += 4
    if n > len(d) - o:
        raise ValueError
    s = d[o:o + n].decode('utf-8', 'replace')
    return s, (o + n + 3) & ~3


def is_stage(s):
    if not s:
        return True
    if s.startswith(SKIP_HEAD):
        return True
    return any(s.startswith(w) for w in SKIP_WORD)


def entries(d):
    out = []
    for cls in CLASSES:
        k = cls.encode()
        i = 0
        while True:
            i = d.find(k, i)
            if i < 0:
                break
            if struct.unpack_from('<I', d, i - 4)[0] == len(k):
                out.append((i - 12, cls))
            i += 1
    out.sort()
    res = []
    for k, (pos, cls) in enumerate(out):
        o = pos + 8
        try:
            _c, o = rdstr(d, o)
            _n, o = rdstr(d, o)
            _a, o = rdstr(d, o)
        except ValueError:
            continue
        res.append((pos, struct.unpack_from('<I', d, pos)[0], cls, o))
    return res


def comment_text(d, o):
    _li = struct.unpack_from('<I', d, o)[0]
    o += 4
    _h, o = rdstr(d, o)
    t, o = rdstr(d, o)
    return t


def cmd_target(d, o):
    _li = struct.unpack_from('<I', d, o)[0]
    o += 4
    _h, o = rdstr(d, o)
    return struct.unpack_from('<I', d, o)[0]


# ---- 剔除黑名单（team-lead 2026-10-26 规格）----
DEV_WORDS = ('フェードイン', 'フェードアウト', 'コメントアウト', '調整', 'TODO', 'メモ', 'でも良いかも', '確認用', '仮置き')
SENT_END = ('。', '！', '？', '…', '」', '』', '）', '♪', 'ー')


DEV_MARK = ('話者ID表', '話者表', '合成ボイス', 'ID変更', 'IDを変更', 'ボイス差し替え', 'ボイスID', '話者ID')
_NOTE_PAT = [
    r'^EV\d+_\d+(で|のため|に)?',
    r'^★+\s*',
    r'^合成ボイス(が流れるので|のため|ここから|ここまで)?',
    r'^ここからボイスも[^、。]*',
    r'^ボイス差し替え',
    r'^話者ID表', r'^話者表',
    r'^ID(を)?変更',
]


def strip_dev_fragment(t):
    """剥掉开发注记：尾随型在最后一个收尾引号处截断；前导型按注记词表反复削前缀，削完为空则整行丢弃。"""
    hit = [t.find(w) for w in DEV_MARK if t.find(w) >= 0]
    if not hit:
        return t
    first = min(hit)
    for q in ('」', '』', '）'):
        k = t.rfind(q, 0, first)
        if k >= 0:                       # 术语在台词之后 → 截到最后一个收尾引号
            return t[:k + 1]
    prev = None
    while prev != t:                     # 术语在行首一侧 → 反复削掉注记前缀
        prev = t
        for pat in _NOTE_PAT:
            t = re.sub(pat, '', t)
    t = t.strip()
    if not re.search('[\u3040-\u30ff\u4e00-\u9fff]', t):
        return ''                        # 削完只剩标点 → 视为无正文
    return t


NOTE_KEY = ('立ち絵', '非表示', '暗転', '時間経過', '場面転換', '回想', 'カット', '選択肢', '汎用',
            '名前呼び変え', '演出', 'フェード', '画面', '立ち位置', 'モヤ', 'スチル')

# 出现即判注记的**制作用语**（不管在行内什么位置）：一条正文台词/地の文不会用到这些词
PROD_ANY = ('立ち絵', 'スチル', '立ち位置', 'カットイン', '名前呼び変え', 'モーション', 'アイコン', '代用')
# 敬体收尾且**无句点**＝作者备忘（`〜にしています` `〜しておきます` `〜してください`）。
# 本作 68 条此类行全部是注记；正文里唯一的例外是叠词 `ますます`，用 (?<!ま) 排掉。
POLITE_END = re.compile(r'(?<!ま)(します|ください|ません|ます)$')


def is_note(s):
    """判断一条注释是**作者注记/演出指示**（不上屏），还是正文。"""
    s = s.strip()
    if not s:
        return True
    if s.startswith(('@', '//', '#', '◆', '◇', '■', '●', '＝', '=', '※', '↓', '↑', '←', '→', '・')):
        return True
    if re.match(r'^[^：:]{1,10}[：:]', s):          # 演技：… / 話者名：… / 立ち絵IN：…
        return True
    if any(k in s[:12] for k in NOTE_KEY):
        return True
    if len(s) <= 14 and not re.search(r'[。！？…」』）]', s):
        return True                                # 短句、无句末标点 ⇒ 名簿/指示
    # ★ 2026-10-27：`（アイラ）はミドル（獣）でも代用できないので立ち絵なしで進行します` 这类
    #   长句注记既不以标记开头、也不短 ⇒ 靠「制作用语」与「敬体无句点」两条兜住。
    if not s.endswith(('」', '』', '）')) and any(k in s for k in PROD_ANY):
        return True
    if not s.endswith(('」', '』', '）')) and POLITE_END.search(s):
        return True
    return False


DIGIT = str.maketrans('０１２３４５６７８９', '0123456789')
BARE = re.compile(r'^(?:#{2,})?・?[^\s。、！？…「」『』（）?!：:]{1,16}$')
HIRA = re.compile('[\u3040-\u309f]')


def norm_name(s):
    """名札归一化：去 `#`/`・` 前缀，全角数字→半角（作者 `２人`/`2人` 混写）。"""
    s = s.strip().lstrip('#').strip()
    if s.startswith('・'):
        s = s[1:]
    return s.translate(DIGIT)


def build_names(files):
    """全库名札集合：`短、无平假名、无标点` 且**下一行是引号开头**的注释，出现 ≥2 次即认定为名札。
    用于剔除「框内第二个名札」（本作 23,663 框里只有 1 框出现，属作者改稿残留）。"""
    from collections import Counter
    cnt = Counter()
    for p in files:
        try:
            d = open(p, 'rb').read()
            ents = entries(d)
        except Exception:
            continue
        texts = []
        for pos, rid, cls, o in ents:
            if cls != 'CommentScriptLine':
                continue
            try:
                t = comment_text(d, o) or ''
            except Exception:
                continue
            t = t.strip()
            if t:
                texts.append(t)
        for i, t in enumerate(texts[:-1]):
            if not BARE.match(t) or HIRA.search(t):
                continue
            if t.startswith(('@', '//', '◆', '◇', '※', '↓', '↑', '←', '→', '＝')):
                continue
            if any(k in t for k in NOTE_KEY) or any(k in t for k in PROD_ANY):
                continue
            if texts[i + 1].startswith(('「', '（', '『')):
                cnt[norm_name(t)] += 1
    return {k for k, v in cnt.items() if v >= 2}


def strip_nametag(t):
    """`ロドス・ハートフィールド「…」` → `「…」`。
    名札在源侧是**单独一条注释**（下一行才是台词），拼过来后粘在行首 ⇒ 剥。
    判据：前缀 ≤16 字、不含句读、不以助词收尾（`〜は「…」` 这种是正文，不能剥）。"""
    m = NAME_TAG.match(t)
    if m and not PART_END.search(m.group(0)):
        return t[m.end():]
    m = KATA_NAME.match(t)          # `ギャレット・ウェルキン私は…` 这种裸名札粘连
    if m and len(m.group(0)) >= 4:
        return t[m.end():]
    return t


NOTE_HEAD = ('前セリフの名前呼び変え', '以下、元のシナリオ')
# 作者注记前缀（`↓目的もなくカット`、`引用ここまで（アシェル②）`、`EV02_0001から引用` …）
NOTE_HEAD_RE = [
    re.compile(r'^↓[^「（]{0,24}?カット'),
    re.compile(r'^↓王への謁見のほうが正しいです'),
    re.compile(r'^↓なくてもいいかも'),
    re.compile(r'^↓これなくてもよいかも？'),
    re.compile(r'^引用ここまで（[^）]*）'),
    re.compile(r'^引用ここまで'),
    re.compile(r'^EV\d{2}_\d{4}から引用'),
    re.compile(r'^以下、元のシナリオ[-ー―─\s]*'),
    # 单条注释里「注记 + 正文」直接粘连（没有 Empty 分隔）的几种句式
    re.compile(r'^ここから(?:ジュリエットの|２人とも)?(?:私服|隊服)?立ち絵(?:は(?:私服|隊服))?'),
    re.compile(r'^「[^」]{0,24}」をカットすると[^。]{0,40}?(?:ます|です|ください)'),
    re.compile(r'^「[^」]{0,24}」もカットしたほうが[^。]{0,30}?思います'),
    re.compile(r'^「[^」]{0,24}」とありますが.*?、、、'),
]
# 裸名札（片假名+・）粘在正文前：`ギャレット・ウェルキン私は…` ⇒ 剥（下一个字是助词/标点时不剥）
KATA_NAME = re.compile(r'^[ァ-ヶー・]{2,24}(?=[^ァ-ヶー・はがをにでとものへや、。！？…「」『』（）])')
# 行尾的修订注记（`※修正前「…」`）——出现即截断
NOTE_CUT = ('※修正前', '※修正後', '※メモ')


def strip_note_head(t):
    """作者注记粘在正文行首/行尾（`前セリフの名前呼び変え…`、`＠名　←追加テキスト「…`、`…「台词」※修正前「旧稿」`）。
    有 `「` 的 ⇒ 从第一个 `「` 起保留；否则按注记词表反复削前缀；`※修正` 类从该处截断。"""
    for w in NOTE_CUT:
        k = t.find(w)
        if k > 0:
            t = t[:k]
    if '「' in t:
        k = t.find('「')
        if k > 0:
            t = t[k:]
    for w in NOTE_HEAD:
        if t.startswith(w):
            t = t[len(w):]
            break
    prev = None
    while prev != t:
        prev = t
        for pat in NOTE_HEAD_RE:
            t = pat.sub('', t)
    return t.strip()


def strip_speaker(t):
    """`・ローズ「台词」` → `「台词」`；只有名札（`・ローズ`）→ 空串（丢弃）。"""
    if not t.startswith('・'):
        return t
    m = re.match(r'^・[^「（【]{1,14}(?=[「（【])', t)
    if m:
        return t[m.end():]
    return ''


def classify_drop(t):
    """返回剔除类别（None=保留）。判据见报告 §剔除。"""
    if not t:
        return None
    if t.startswith('・'):
        return 'speaker-label'      # 只有 strip_speaker 之后仍以 ・ 开头（无正文）才落到这里
    if t.startswith('◆') or t.startswith('◇') or t.startswith('＝'):
        return 'stage'
    for w in ('BGM', 'SE：', 'SE:', 'Voice', 'ボイス'):
        if t.startswith(w):
            return 'sfx'
    if any(w in t for w in DEV_WORDS) and not t.rstrip().endswith(SENT_END):
        return 'dev-comment'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--final')
    a = ap.parse_args()

    rows, reasons, drops, dsamples = [], {}, {}, {}
    mid_close = []      # 框内非末行提前闭引号（作者笔误）
    dual_name = []      # 单框出现 ≥2 个名札（本作仅 1 框）
    files = sorted(glob.glob(os.path.join(a.src, '*.bin')))
    NAME_SET = build_names(files)      # 全库名札（含 `２人`/`2人` 归一）
    for p in files:
        d = open(p, 'rb').read()
        name = os.path.basename(p).split('_', 1)[-1].replace('.bin', '')
        ents = entries(d)
        refs = {rid: (cls, o) for pos, rid, cls, o in ents if rid}
        o = 28
        try:
            nl = struct.unpack_from('<I', d, o)[0]
            o = (o + 4 + nl + 3) & ~3
            n = struct.unpack_from('<I', d, o)[0]
            o += 4
        except Exception:
            print('skip', p)
            continue
        seq = []
        for k in range(n):
            rid = struct.unpack_from('<I', d, o + k * 8)[0]
            if rid not in refs:
                seq.append(('?', None))
                continue
            cls, off = refs[rid]
            if cls == 'CommandScriptLine':
                try:
                    t = cmd_target(d, off)
                    cls = refs.get(t, ('CommandScriptLine', None))[0]
                except Exception:
                    pass
            if cls == 'CommentScriptLine' and off is not None:
                # ★ `@cMsg -1,EV14_0001,…` 这类内联指令＝「显示这条消息」⇒ 视作框尾（虚拟 CMsg）
                #   `@cMsgWinClose` 是关窗，不是显示，别算
                try:
                    cs = (comment_text(d, off) or '').strip()
                except Exception:
                    cs = ''
                if cs.startswith('@cMsg ') or cs == '@cMsg':
                    cls = 'CMsg'
            seq.append((cls, off))

        idx = 0
        for i, (cls, off) in enumerate(seq):
            if cls != 'CMsg':
                continue
            idx += 1
            buf, stage = [], False
            ntag = 0          # 本框已剔除的名札个数（≥2 = 作者改稿残留，需人工看一眼）
            for j in range(i - 1, -1, -1):
                cc, oo = seq[j]
                if cc == 'EmptyScriptLine':
                    # ★ 2026-10-27 实机核对：Empty 常把「注记」和「正文」隔开
                    #   （`ここから私服立ち絵` / `演技：…` / `ギャレットキーラン…` ⇒ Empty ⇒ 正文）。
                    #   但正文也可能被 Empty 切开（同一框两段）。判据：看 Empty 外侧那条像不像注记。
                    nxt = None
                    for jj in range(j - 1, -1, -1):
                        c2, o2 = seq[jj]
                        if c2 == 'EmptyScriptLine':
                            continue
                        if c2 != 'CommentScriptLine':
                            break
                        try:
                            t2 = (comment_text(d, o2) or '').strip().lstrip('#').strip()
                        except Exception:
                            break
                        if t2:
                            nxt = t2
                        break
                    if nxt is not None and is_note(nxt):
                        break        # 外侧是注记 ⇒ 到此为止（注记不进正文）
                    continue         # 外侧是正文 ⇒ 只是被空行切开的同框段落，继续收
                if cc != 'CommentScriptLine':
                    break
                s = (comment_text(d, oo) or '').strip().lstrip('#').strip()
                if not s:
                    continue
                if s.startswith('@') or s.startswith('//'):
                    break        # ★ 注记/指令行（@cMsg / @cCharaAdd / //…）到此为止，别并进正文
                s = INLINE_CODE.sub('', s)   # ★ 行尾挂的资源 id（c04p0 之类）剥掉
                if not s:
                    continue
                if is_stage(s):
                    stage = True
                    break
                m = re.match(r'^[^\s「」]{1,10}：(.*)$', s)
                if m:
                    tail = m.group(1)
                    if '「' in tail:
                        s = tail
                    else:
                        stage = True
                        break
                if s.startswith('@'):          # 内联命令注记（@cFront / @cCutinSingle …）
                    continue
                if any(w in s for w in DEV_WORDS) and not s.rstrip().endswith(SENT_END):
                    drops['dev-comment'] = drops.get('dev-comment', 0) + 1
                    dsamples.setdefault('dev-comment', []).append(s[:50])
                    continue
                if not JP.search(s):
                    break
                # ★ 框内第二个名札：本作 23,663 框只有 1 框出现（作者改稿残留），
                #   名札永远不会出现在正文流里 ⇒ 跳过（文本不丢，只丢名字）
                if (buf and BARE.match(s) and not HIRA.search(s)
                        and buf[-1].startswith(('「', '（', '『'))
                        and norm_name(s) in NAME_SET):
                    drops['name-tag'] = drops.get('name-tag', 0) + 1
                    ntag += 1
                    if ntag >= 2:
                        dual_name.append((name, idx, s))
                    continue
                buf.append(s)
            # ★ 框内「非末行就已用 」 收尾」＝作者笔误（本作 23,657 框里仅 1 处）。
            #   一框一行的成行法会把两行合并，那个多余的 」 就落在行中间 ⇒ 记下来供人工确认，
            #   **不自动删标点**（源侧标点只登记不改，见 skill `S6-line-integrity.md`）。
            _fwd = list(reversed(buf))
            for _k in range(len(_fwd) - 1):
                if _fwd[_k].endswith('」') and '「' not in _fwd[_k + 1]:
                    mid_close.append((name, idx, _fwd))
                    break
            txt = ''.join(reversed(buf))
            while txt.startswith('「「'):       # 断屏残余：两条注释各带一个「
                txt = '「' + txt[2:]
            why = 'comment' if txt else ('stage-only' if stage else 'no-comment')
            if txt:
                txt = strip_speaker(txt)
                if not txt:                     # 独立名札（`・ローズ`）→ 丢弃
                    drops['speaker-label'] = drops.get('speaker-label', 0) + 1
                    why = 'speaker-label'
            if txt:
                txt = strip_speaker(strip_dev_fragment(strip_note_head(strip_nametag(txt))))
            if txt:
                _drop = classify_drop(txt)
                if _drop:
                    drops[_drop] = drops.get(_drop, 0) + 1
                    dsamples.setdefault(_drop, []).append(txt[:60])
                    txt, why = '', _drop
            if not txt:
                reasons[why] = reasons.get(why, 0) + 1
            rows.append((name, idx, txt, why))

    open(a.out, 'w', encoding='utf-8').write('\n'.join('%s\t%d\t%s\t%s' % r for r in rows))
    have = [r for r in rows if r[2]]
    print('CMsg %d  有正文 %d  无正文 %d' % (len(rows), len(have), len(rows) - len(have)))
    print('残余原因', reasons)
    print('剔除', drops)
    if dual_name:
        print('单框出现 ≥2 个名札 %d 处（作者改稿残留；名札已剔、正文保留）：' % len(dual_name))
        for nm, i, t in dual_name[:8]:
            print('   %s #%d 第二个名札=%r' % (nm, i, t))
    if mid_close:
        print('框内「非末行已用 」 收尾」%d 处（作者笔误；一框一行合并后行中会出现孤立 」）：' % len(mid_close))
        for nm, i, r in mid_close[:8]:
            print('   %s #%d %r' % (nm, i, ''.join(r)[:78]))
    if a.final:
        with open(a.final, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(r[2] for r in have))
        print('成品 ->', a.final, len(have), '行')


if __name__ == '__main__':
    main()
