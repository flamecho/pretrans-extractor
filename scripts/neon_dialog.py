#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ネオンクラッシュ -Echoes of the Lost- 正文提取（成品生成）。

★ 载体结论（2026-10-26 实证）：
  `CMsg.Text.value` = `作者号,语音资源名,语音变体名`（如 `18,@18_0036,@18_0036z`），**不含正文**；
  真日文正文 = 该 CMsg 前面**连续的若干条** `CommentScriptLine.commentText`（一行台词一条，按序直接拼接）。
  数据不在 `lines[]`（只有 {rid}），在 `references.RefIds[rid].data`（Unity `[SerializeReference]` 多态表），
  `CommandScriptLine` 还要再跟 `command:{rid}` 一跳才到 `CMsg`。

用法:
  python scripts/neon_dialog.py --il2cpp <main> --meta <global-metadata.dat> --bundle <bundle> \
      --out <all.tsv> [--final <成品.txt>]
输出:
  --out   : 脚本\t序号\tText.value\t正文\t分类   （全量，含空正文行，供核对）
  --final : 只写有正文的行，UTF-8 BOM + LF + 无空行（成品）
"""
import argparse
import re

import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

JP = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')
SKIP_HEAD = ('◆', '◇', '＝', '=', '■', '●', '＊', '*', '※')
SKIP_WORD = ('話者名', '演技', 'BGM', 'SE：', 'SE:', '登場人物', 'pg遷移', 'pg構築', '演出',
             '名前表記', '読み：', '読み:', '字幕', 'ルビ', '注釈', 'メモ')


def is_stage(s):
    if not s:
        return True
    if s.startswith(SKIP_HEAD):
        return True
    for w in SKIP_WORD:
        if s.startswith(w):
            return True
    return False


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


# ---- 行首制作标记（2026-10-27 实证：`回想ここまで…` / `立ち絵にモヤ——…` / `画面揺れ…`）----
# 这些标记与正文被拼进同一行，剥掉标记本身、正文一律保留。
STAGE_PREFIX = re.compile(
    r'^(?:回想(?:ここまで|ここから)|セリフ合成(?:ここまで|ここから)|'
    r'立ち絵(?:にモヤ|ナシで|なしで|IN|OUT)|立ち絵[：: ]|'
    r'画面揺れ|暗転|場面転換|'
    r'カットイン[^、。「]{0,8}|ポップアップ[^、。「]{0,6}|'
    r'BGM[^、。「]{0,8}|SE[：:][^、。「]{0,8})')


def strip_stage_prefix(t):
    """剥行首制作标记；无标记原样返回。反复剥直到稳定（可能连写两三个标记）。"""
    prev = None
    while prev != t:
        prev = t
        t = STAGE_PREFIX.sub('', t, count=1).lstrip('　 ')
    return t


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
    ap.add_argument('--il2cpp', required=True)
    ap.add_argument('--meta', required=True)
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--unity', default='2022.3.62f1')
    ap.add_argument('--out', required=True)
    ap.add_argument('--final')
    ap.add_argument('--keep-stage-block', action='store_true',
                    help='保留 Empty 前的注记块（默认丢弃；实测 29 处跨块拼接中 28 处是制作注记）')
    ap.add_argument('--stage-report',
                    help='把被丢弃的注记块逐条写到该文件，供人工复核')
    ap.add_argument('--skip', default='sandbox,test,EV99',
                    help='开发/调试脚本前缀，逗号分隔（默认 sandbox,test,EV99）')
    a = ap.parse_args()

    gen = TypeTreeGenerator(a.unity)
    gen.load_il2cpp(open(a.il2cpp, 'rb').read(), open(a.meta, 'rb').read())
    env = UnityPy.load(a.bundle)
    env.typetree_generator = gen

    scripts = []
    for o in env.objects:
        if o.type.name != 'MonoBehaviour':
            continue
        t = o.read_typetree()
        if 'references' in t and 'lines' in t:
            scripts.append(t)
    scripts.sort(key=lambda t: t.get('m_Name') or '')

    skip = tuple(x.strip() for x in a.skip.split(',') if x.strip())
    rows = []
    reasons = {}
    drops = {}
    dsamples = {}
    choice_cls = {}
    for t in scripts:
        if (t.get('m_Name') or '').startswith(skip):
            continue
        refs = {r['rid']: r for r in t['references']['RefIds']}
        seq = []
        for x in t['lines']:
            r = refs.get(x['rid'])
            if not r or 'data' not in r:
                continue
            cl, d = r['type']['class'], r['data']
            if cl not in ('CommentScriptLine', 'EmptyScriptLine'):
                choice_cls[cl] = choice_cls.get(cl, 0) + 1
            if cl == 'CommandScriptLine':
                s = refs.get((d.get('command') or {}).get('rid'))
                if s and 'data' in s:
                    cl, d = s['type']['class'], s['data']
            seq.append((cl, d))

        idx = 0
        for i, (cl, d) in enumerate(seq):
            if cl != 'CMsg':
                continue
            v = (d.get('Text') or {}).get('value') or ''
            txt, why = '', ''
            if JP.search(v):                      # 少数行正文直接内联
                txt, why = v.split(',', 1)[1] if ',' in v else v, 'inline'
            else:
                buf, seen_stage, stage_block = [], False, ''
                for j in range(i - 1, -1, -1):
                    cc, dd = seq[j]
                    if cc == 'EmptyScriptLine':
                        # 2026-10-27：EmptyScriptLine = 「演出注记块 / 显示正文块」的分界。
                        # Naninovel 作者用它把制作注记（立绘/画面/演技指示）与真正显示的正文隔开；
                        # 原先当「空行不打断」⇒ 注记被拼进正文（ネオンクラッシュ 实测 28 行）。
                        if buf:
                            stage_block = ''.join(reversed(buf))
                            buf = []
                        continue
                    if cc != 'CommentScriptLine':
                        break
                    s = (dd.get('commentText') or '').strip().lstrip('#').strip()
                    if not s:
                        continue
                    if is_stage(s):
                        seen_stage = True
                        break
                    m = re.match(r'^[^\s「」]{1,10}：(.*)$', s)   # 「画面演出：…」这类注记
                    if m:
                        tail = m.group(1)
                        if '「' in tail:                      # 「表示名：名前「台词」」→ 留台词段
                            s = tail
                        else:
                            seen_stage = True
                            break
                    if any(w in s for w in DEV_WORDS) and not s.rstrip().endswith(SENT_END):
                        drops['dev-comment'] = drops.get('dev-comment', 0) + 1
                        dsamples.setdefault('dev-comment', []).append(s[:50])
                        continue
                    if not JP.search(s):
                        break
                    buf.append(s)
                if buf:
                    txt, why = ''.join(reversed(buf)), 'comment'
                    if stage_block and not a.keep_stage_block:
                        drops['stage-block'] = drops.get('stage-block', 0) + 1
                        dsamples.setdefault('stage-block', []).append(stage_block[:60])
                        if a.stage_report:
                            with open(a.stage_report, 'a', encoding='utf-8') as fr:
                                fr.write(stage_block + '\n')
                elif seen_stage:
                    why = 'stage-only'
                else:
                    why = 'no-comment'
            if txt:
                txt = strip_speaker(txt)
            if txt:
                txt = strip_speaker(strip_dev_fragment(txt))
            if txt:
                txt = strip_stage_prefix(txt)
            if txt:
                d = classify_drop(txt)
                if d:
                    drops[d] = drops.get(d, 0) + 1
                    dsamples.setdefault(d, []).append(txt[:60])
                    txt, why = '', d
            if not txt:
                reasons[why] = reasons.get(why, 0) + 1
            idx += 1
            rows.append((t.get('m_Name'), idx, v, txt, why))

    open(a.out, 'w', encoding='utf-8').write(
        '\n'.join('%s\t%d\t%s\t%s\t%s' % r for r in rows))
    have = [r for r in rows if r[3]]
    print('CMsg %d  有正文 %d  无正文 %d' % (len(rows), len(have), len(rows) - len(have)))
    print('残余原因', reasons)
    print('剔除', drops)
    if a.final:
        with open(a.final, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(r[3] for r in have))
        print('成品 ->', a.final, len(have), '行')
    top = sorted(((k, v) for k, v in choice_cls.items()), key=lambda x: -x[1])[:12]
    print('行类 top（找选项）', top)


if __name__ == '__main__':
    main()
