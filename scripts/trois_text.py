# -*- coding: utf-8 -*-
"""
アンジェリーク トロワ (PS2, SLPM_620.22, 2000 Koei/Ruby Party) 正文＋选项提取

源: ISO 根目录 EMBINS.VVV（9,189,376 B）—— 代码与 rodata 混排的模块镜像，
    正文＝其内的 cp932 NUL 结尾字符串池（0x12f0 起，至 0x8c3504）。

结构结论（2026-10-18 实测）:
  * 一条 NUL 结尾字符串 = 一个 message box = 一次点击
  * 串内 '\\n' = 同一框内的显示行；末尾 '\\n\\n' = 框结束（空行）
  * 选择肢框: 「问题行 + 若干以全角空格(0x8140)开头的选项行」且以单个 '\\n' 结尾
  * 主角名处被拆成「前后两段 + NUL 空位」：空位 1..8 B，下一段以
    。！？、」』） 或 の（前段以 （　、… 结尾时）开头 ⇒ 空位是名字槽，填默认名
  * 无 %s / #GD 之类可见宏

用法:
  python scripts/trois_text.py <EMBINS.VVV> <out.txt>
"""
import os
import re
import sys

HIRA = re.compile(r'[ぁ-んァ-ヴ一-龥]')
NAME = 'アンジェリーク'
NAME_NEXT = set('。！？、」』）')
NAME_PREV = set('（\u3000、…「')
PARTICLES = set('のとはがをにもでへやか')
MAXGAP = 16
# 系统/UI 文本（帮助・设定・改名报错）—— 按口径不收，整行精确匹配剔除
EXCLUDE = {
    'ただし、イベント中やセーブ中などは見ることができません。',
    '環境を整えたいときは「設定」を選択してください。',
    '申し訳ありません、女王陛下。その名前は、使用できません。',
}


def islead(b):
    return (0x81 <= b <= 0x9f) or (0xe0 <= b <= 0xfc)


def istrail(b):
    return (0x40 <= b <= 0x7e) or (0x80 <= b <= 0xfc)


def scan(d):
    """返回 [(start, end, text)]：end 指向终止 NUL"""
    n = len(d)
    out = []
    i = 0
    while i < n:
        if not (islead(d[i]) and i + 1 < n and istrail(d[i + 1])):
            i += 1
            continue
        j = i
        buf = []
        while j < n:
            b = d[j]
            if islead(b) and j + 1 < n and istrail(d[j + 1]):
                buf.append(d[j:j + 2])
                j += 2
            elif b == 0x0a:
                buf.append(b'\n')
                j += 1
            elif 0x20 <= b < 0x7f:
                buf.append(d[j:j + 1])
                j += 1
            else:
                break
        if j < n and d[j] == 0 and j > i:
            try:
                t = b''.join(buf).decode('cp932')
            except UnicodeDecodeError:
                t = None
            if t:
                out.append((i, j, t))
                i = j
                continue
        i += 1
    return out


def join_names(recs, d):
    """把被名字槽切断的相邻记录合并（槽内填 NAME），返回 [start, end, text, merged]"""
    out = []
    nslot = 0
    last_pfx = None
    for start, end, t in recs:
        if out:
            pend, pt, pm = out[-1][1], out[-1][2], out[-1][3]
            gap = start - pend
            nxt = t[:1]
            filler = d[pend:start]
            # ★ 助词判据只在上段以「（」「　」收尾时成立：以「…」「、」收尾时
            #   后面跟助词多半是另一句（`ジュリアス様…` / `はい。`），插名会造出错句
            named = (nxt in NAME_NEXT
                     or (nxt in PARTICLES and pt and pt[-1] in '\u3000（'))
            if 0 < gap <= MAXGAP and set(filler) <= {0, 0x0a} and named and not pm:
                last_pfx = pt          # 记住「名字之前的整段」，供并列变体复用
                out[-1][1] = end
                out[-1][2] = pt + NAME + t
                out[-1][3] = True
                nslot += 1
                continue
            # 并列变体：同一前缀 + 名字 + 另一条「。…」后缀（原作把后缀按分支各存一条）
            # ⇒ 每条都补回「前缀＋名字」，否则成品会出现行首「。」
            if (last_pfx is not None and nxt in NAME_NEXT and 0 < gap <= MAXGAP
                    and set(filler) <= {0}):
                out.append([start, end, last_pfx + NAME + t, True])
                continue
            # 半句残片：必须「下段含闭括号」才合，否则赠礼 reaction 那种并列变体表会被串成一行
            # 只看「上段括号未闭合」：★ 不能只凭「上段以 　/（ 收尾」就合，
            # 否则两条各自闭合成句的心声（…しまう）\n　 ／ （私の宇宙に…） 会被并成一行
            frag = (bool(pt) and '）' in t and pt.count('（') > pt.count('）'))
            if 0 < gap <= MAXGAP and set(filler) <= {0, 0x0a} and frag and not pm:
                out[-1][1] = end
                out[-1][2] = pt + t
                out[-1][3] = True
                continue
        if t[:1] not in NAME_NEXT:
            last_pfx = None
        out.append([start, end, t, False])
    return out, nslot


def is_choice_para(t):
    """特例（全篇 1 例）：双换行结尾，且 ≥2 条缩进行以「）」收尾 ⇒ 带括注的选项块。
    选项行会软换行，故按「以 ）收尾」判定一条选项的结束。"""
    if not t.endswith('\n\n'):
        return False
    L = [x for x in t[:-1].split('\n') if x]
    if not (3 <= len(L) <= 6):
        return False
    if not all(x.startswith('\u3000') for x in L[1:]):
        return False
    return sum(1 for x in L[1:] if x.rstrip().endswith('）')) >= 2


def is_choice(t):
    """问题行 + 全角空格开头的选项行。
    - 单换行结尾：≥3 行即算（实测 3,213 块）
    - 双换行结尾：★ 只有「首行是完整问句/心声（以 ？…。 收尾）+ 2-3 条短选项」才算；
      否则是「一行长文被折成 3 行」的普通叙述（实测 180 例都是这种，别拆）
    """
    if not t.endswith('\n'):
        return False
    lines = t[:-1].split('\n')
    body = [x for x in lines[1:] if x]
    if len(body) < 2:
        return False
    if not all(x.startswith('\u3000') for x in body):
        return False
    if t.endswith('\n\n'):
        # 以「『 开头的是引用/台词转述（叙述），不是选项块
        if lines[0].lstrip().startswith(('「', '『')):
            return False
        return (len(body) <= 3
                and lines[0].rstrip().endswith(('？', '…', '。')))
    return 3 <= len(lines) <= 6


def fix_pairs(lines, maxlen=400):
    """括号/引号跨框：多开的并入下一行，多闭的并入上一行（引号配对＝行粒度探针）
    设长度上限，避免无配对行无限吞并"""
    pairs = [('「', '」')]
    for _ in range(200):
        changed = False
        i = 0
        while i < len(lines):
            hit = False
            for op, cl in pairs:
                dlt = lines[i].count(op) - lines[i].count(cl)
                # ★ 只与「含对应闭合符」的邻行合并，否则会连吞无关行（实测吞到 389 宽）
                if dlt > 0 and i + 1 < len(lines) and cl in lines[i + 1] \
                        and len(lines[i]) + len(lines[i + 1]) <= maxlen:
                    lines[i] += lines[i + 1]
                    del lines[i + 1]
                    changed = hit = True
                    break
                if dlt < 0 and i > 0 and op in lines[i - 1] \
                        and len(lines[i]) + len(lines[i - 1]) <= maxlen:
                    lines[i - 1] += lines[i]
                    del lines[i]
                    changed = hit = True
                    break
            if not hit:
                i += 1
        if not changed:
            break
    return lines


def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    d = open(src, 'rb').read()
    raw = scan(d)
    merged_recs, nslot = join_names(raw, d)
    recs = [r for r in merged_recs
            if len(HIRA.findall(r[2])) >= 2 and len(r[2]) >= 4]
    lines = []
    nch = 0
    for _s, _e, t, _m in recs:
        t = t.replace('\r', '')
        if is_choice_para(t):
            nch += 1
            L = [x for x in t[:-1].split('\n') if x]
            head = L[0].strip('\u3000 ')
            outs = ([head] if head else [])
            buf = ''
            for x in L[1:]:
                buf += x.strip('\u3000 ')
                if buf.endswith('）'):
                    outs.append(buf)
                    buf = ''
            if buf:
                outs.append(buf)
        elif is_choice(t):
            nch += 1
            body = [x for x in t[:-1].split('\n') if x]
            head = body[0].strip('\u3000 ')
            idx = 1
            # 问句本身可能折行：括号未闭合就把下一行并进来，直到闭合
            while idx < len(body) and head.count('（') > head.count('）'):
                head += body[idx].strip('\u3000 ')
                idx += 1
            outs = ([head] if head else [])
            outs += [o.strip('\u3000 ') for o in body[idx:] if o.strip('\u3000 ')]
        else:
            merged = ''.join(x.strip() for x in t.split('\n')).strip()
            outs = [merged] if merged else []
        for x in outs:
            if x in EXCLUDE:
                continue
            lines.append(x)
    lines = fix_pairs(lines)
    os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as fp:
        for x in lines:
            fp.write(x + '\n')
    print('records=%d slots=%d choices=%d lines=%d -> %s'
          % (len(recs), nslot, nch, len(lines), dst))


if __name__ == '__main__':
    main()
