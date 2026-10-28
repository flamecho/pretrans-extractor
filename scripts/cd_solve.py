#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""カスタムドライブ `FF0C`（相手役の下名）定位器 —— 报告 §11 的可重跑证据/落地依据。

★★结论（§11.1）：`FF0C`＝**当前对话相手（その場で向かって話している相手）の下名**，
   运行时变量。它不等于「最近说话的人」（0113 当着遠藤悟的面指流風），
   也不等于「条目固定的路线角色」（0993 与璃斗同行却指紫音）。
   可静态利用的判据只有三条，全部是排除法：
     (1) 同框内**被字面点名**的人不是 `FF0C`（`璃斗はともかく、《X》も…` ⇒ X≠璃斗）
     （2）`FF0C` 的取值只可能是 3 名攻略对象之一（`CAST_MAIN`）；その他角色只作「被点名者」排除
     （3）同一 FF42 场景内只有 1 名攻略对象出现 ⇒ 必是他
   余下框只能用「章＝路线块」的条目级插值（A/B），并接受四判据检验。

用法：
  python scripts/cd_solve.py stat | check | sample N | dump | cache
"""
import os, sys, re, bisect, json
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK
from vridge_psp_run import toks, words_to_text, plate_spans
from vridge_cs_customdrive import (CPK as CPK_PATH, CHARSET, SPECIAL, CAST,
                                   PROTAG_GIVEN)

c = CPK(CPK_PATH)
E = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
           key=lambda e: int(e['name']))
GIVEN = dict(CAST)
SUR = {f: f.replace(g, '') for f, g in GIVEN.items() if g and g in f}
MAIN = ('神無木紫音', '黛流風', '東真璃斗')      # 3 名攻略対象（vndb v10623 / 名札分布）
PROTAG = '沙耶'
FEMALE = {'柊木かんな', '坂下祭'}                # 女教师／主角的女性好友
GS = {GIVEN[m]: m for m in MAIN}
SS = {SUR[m]: m for m in MAIN if len(SUR[m]) >= 2}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                     '_work_customdrive', '_cd_frames.json')


def entry_frames(d):
    tk = toks(d)
    n = len(tk)
    starts, spks = plate_spans(tk, CHARSET, SPECIAL, PROTAG_GIVEN)
    out = []
    for i, st in enumerate(starts):
        body = []
        for j in range(st, n):
            op, run = tk[j]
            if j > st and op in (0xFFFF, 0xFFFB):
                break
            body.append((op, run))
        out.append((st, spks[i], body))
    return tk, out


def render(body, fill='《X》'):
    o = []
    for op, run in body:
        if op == 0xFF0C:
            o.append(fill + words_to_text(run, CHARSET, SPECIAL))
        elif op == 0xFFE6:
            o.append('国府田')
        elif op == 0xFFE7:
            o.append('沙耶')
        elif op == 0xFF0D:
            o.append('私')
        elif op in (0xFFFF, 0xFFFE) or op < 0xFF00:
            o.append(words_to_text(run, CHARSET, SPECIAL))
    return ''.join(o).replace('\u3000', ' ').strip()


def build():
    res = []
    for e in E:
        tk, fr = entry_frames(c.raw(e))
        scenes, frames = [], []
        for st, sp, body in fr:
            isff = any(op == 0xFF0C for op, _ in body)
            istitle = any(op == 0xFF42 for op, _ in body)
            frames.append({'st': st, 'spk': sp, 'ff': isff, 'title': istitle,
                           'text': render(body) if isff else ''})
            if istitle:
                scenes.append(st)
        mail = set()
        for st, sp, body in fr:
            if sp and sp.startswith('メール（'):
                m = re.match(r'メール（([^（]+)', sp)
                if m:
                    mail.add(m.group(1))
        res.append({'name': e['name'], 'scenes': scenes, 'frames': frames,
                    'mail': sorted(mail), 'nff': sum(f['ff'] for f in frames)})
    return res


def load():
    if os.path.exists(CACHE):
        with open(CACHE, encoding='utf-8') as f:
            return json.load(f)
    ents = build()
    with open(CACHE, 'w', encoding='utf-8') as f:
        json.dump(ents, f, ensure_ascii=False)
    return ents


def scene_of(x, st):
    i = bisect.bisect_right(x['scenes'], st) - 1
    lo = x['scenes'][i] if i >= 0 else 0
    hi = x['scenes'][i + 1] if i + 1 < len(x['scenes']) else 10 ** 12
    return lo, hi


def solve(ents):
    """→ 每条目 {'fill': 条目级|None, 'how': str, 'strong': {fi: p}, 'per': {fi: p}}

    强度序（check/fill_of 按此取）：
      strong (0) 男角说话的框 ⇒ 对方＝主角； (5) 框内写「メール」⇒ 发信人
      条目级 A 锚点 / B 章插值
      per    (3) 场景内唯一攻略对象；(4) 最近攻略对象说话人
    """
    n = len(ents)
    ent_main, out = [], []
    for x in ents:
        ent_main.append({f['spk'] for f in x['frames'] if f['spk'] in MAIN})
    anchor = [next(iter(s)) if len(s) == 1 else None for s in ent_main]
    idxs = [i for i in range(n) if anchor[i]]
    for i, x in enumerate(ents):
        o = {'fill': None, 'how': '', 'strong': {}, 'per': {}}
        if anchor[i]:
            o['fill'], o['how'] = anchor[i], 'A 锚点(条目内唯一攻略对象)'
        else:
            L = [j for j in idxs if j < i]
            R = [j for j in idxs if j > i]
            l = anchor[L[-1]] if L else None
            r = anchor[R[0]] if R else None
            if l and r and l == r:
                o['fill'], o['how'] = l, 'B 插值(左右一致)'
            elif l and not r:
                o['fill'], o['how'] = l, 'B 插值(左)'
            elif r and not l:
                o['fill'], o['how'] = r, 'B 插值(右)'
            else:
                o['how'] = 'C 章交界'
        last = None
        for fi, f in enumerate(x['frames']):
            if f['spk'] in MAIN:
                last_after = f['spk']
            else:
                last_after = None
            if f['ff']:
                rest = f['text'].replace('《X》', '')
                named = {GS[g] for g in GS if g in rest} | {SS[s2] for s2 in SS if s2 in rest}
                lo, hi = scene_of(x, f['st'])
                present = {g['spk'] for g in x['frames']
                           if lo <= g['st'] < hi and g['spk'] in MAIN}
                if not present:
                    present = set(ent_main[i])
                cand = present - named
                if f['spk'] in GIVEN:                       # (0)
                    o['strong'][fi] = PROTAG
                    o['how'] += '|(0)男角说话→主角名'
                elif 'メール' in f['text'] and len(x.get('mail') or []) == 1 \
                        and x['mail'][0] in MAIN:           # (5)
                    o['strong'][fi] = x['mail'][0]
                    o['how'] += '|(5)邮件发信人'
                elif len(cand) == 1:                        # (3)
                    o['per'][fi] = next(iter(cand))
                    o['how'] += '|(3)场景唯一'
                elif last in cand:                          # (4)
                    o['per'][fi] = last
                    o['how'] += '|(4)最近攻略对象'
            if last_after:
                last = last_after
        # (5′) 邮件名札＝条目级锚点（同条目相手役恒定，已由 A/B 与 149/150 标题核验支撑）
        mailv = {o['strong'][fi] for fi in o['strong'] if o['strong'][fi] != PROTAG}
        if o['fill'] is None and len(mailv) == 1:
            o['fill'] = next(iter(mailv))
            o['how'] += '|(5b)邮件锚点'
        vals = set(list(o['per'].values()) + list(o['strong'].values()))
        if o['fill'] is None and vals and len(vals) == 1 \
                and len(o['per']) + len(o['strong']) == x['nff']:
            o['fill'] = next(iter(vals))
        out.append(o)
    return out


def fill_of(x, o, fi):
    return o['strong'].get(fi) or o['fill'] or o['per'].get(fi)


def check(ents, out):
    bad = defaultdict(list)
    tot = cov = 0
    for x, o in zip(ents, out):
        for fi, f in enumerate(x['frames']):
            if not f['ff']:
                continue
            tot += 1
            p = fill_of(x, o, fi)
            if not p:
                continue
            cov += 1
            rest = f['text'].replace('《X》', '')
            if GIVEN.get(p, p) in rest:
                bad['① 同框并列本人下名'].append((x['name'], f['text'], CAST.get(p, p)))
            if re.search(r'私は君の先輩|年上なのよ|先輩なのよ', f['text']) and p == '神無木紫音':
                bad['② 年上自称↔3年生'].append((x['name'], f['text'], CAST[p]))
            if re.search(r'私\s*と\s*《X》', f['text']) and p == PROTAG:
                bad['③ 私と私'].append((x['name'], f['text'], CAST.get(p, p)))
            if p in FEMALE:
                bad['④ 女性角色作相手役'].append((x['name'], f['text'], CAST[p]))
    return bad, tot, cov


if __name__ == '__main__':
    ents = load() if sys.argv[1] != 'cache' else build()
    if sys.argv[1] == 'cache':
        with open(CACHE, 'w', encoding='utf-8') as f:
            json.dump(ents, f, ensure_ascii=False)
        print('cached', len(ents))
        sys.exit()
    out = solve(ents)
    cmd = sys.argv[1]
    if cmd == 'stat':
        bad, tot, cov = check(ents, out)
        print('FF0C 框 %d，定人 %d（%.2f%%），未定 %d' % (tot, cov, cov * 100.0 / tot, tot - cov))
        print(Counter(o['how'].split('|')[0] for o in out).most_common())
        fc = Counter()
        for x, o in zip(ents, out):
            for fi, f in enumerate(x['frames']):
                if f['ff']:
                    p = fill_of(x, o, fi)
                    if p:
                        fc[CAST.get(p, p)] += 1
        print('填值(按框)：', fc.most_common())
        print('反例：', {k: len(v) for k, v in bad.items()} or '无')
        un = [(x['name'], x['nff']) for x, o in zip(ents, out)
              if x['nff'] and not all(fill_of(x, o, fi) for fi, f in enumerate(x['frames']) if f['ff'])]
        print('未定条目 %d：%s' % (len(un), un))
    elif cmd == 'check':
        bad, tot, cov = check(ents, out)
        print('定人 %d/%d' % (cov, tot))
        if not bad:
            print('四判据：0 反例')
        for k, v in sorted(bad.items()):
            print('%-26s %d' % (k, len(v)))
            for r in v[:12]:
                print('   ', r)
    elif cmd == 'sample':
        k = int(sys.argv[2])
        n = 0
        for x, o in zip(ents, out):
            for fi, f in enumerate(x['frames']):
                if not f['ff']:
                    continue
                p = fill_of(x, o, fi)
                print('%s %-10s %s' % (x['name'], CAST.get(p, p) if p else '—', f['text']))
                n += 1
                if n >= k:
                    sys.exit()
    elif cmd == 'dump':
        for x, o in zip(ents, out):
            if x['nff']:
                print('%s %-10s %-34s ff=%d' % (x['name'],
                      CAST.get(o['fill'], o['fill']) if o['fill'] else '-', o['how'], x['nff']))
