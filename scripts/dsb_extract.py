#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Darling Special Backlash ～恋のエキゾースト・ヒート～ (PS2-JP, SLPM_656.53)
SC.BIN → 全文本（一次点击＝一行）

字节码（u16 LE；<0xFF00 = 字符码，>=0xFF00 = 指令）：
  FFF0 <u16 msgid> [name run]   一条消息（= 一框 = 一次点击）
  FFFF <run>                    正文框开始
  FFFE <run>                    框内软换行（合并）
  FFFB / FFFC / FFFD            框结束（点击点；三种收尾码同义）
  FFE6 / FFE7                   主角 名 / 姓 宏（默认 ひとみ / 香西）
  其他指令（FF65/FFC0/FFC2/FFF9…）各带 1–3 个字符码参数，不产正文

结构：
  [0x00] u32 表偏移 0x10
  [0x04] u32 消息数 0x3BED (=15341)
  [0x08] u32 次级表偏移 0xEFD0
  [0x0C] u32 ?
  [0x10] 15341 × u32 消息偏移（相对基址 0x10000）
  [0xEFD0..] 次级索引（239 条，指向 14518+ 的消息，辅助用途，未用）
  [0x10DCA..0x16221E] 消息正文流
  [0x16224C..] 选择肢池（150 条 FFFF 项）
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stormlover_charset import build_charset

CS = build_charset()
NC = len(CS)

MACRO = {0xFFE6: '香西', 0xFFE7: 'ひとみ'}   # 主角：香西 ひとみ（vndb c24864, Nameable）
INLINE = set(MACRO)

# JIS 二级区（码 ≥3456）在本作被整块移作**追加字形槽**（字形不在基础字库内，
# 逐作私有序）；逐槽定值由上下文仲裁，证据见解析报告 §5。未定值者 → 〔未解析〕。
SLOTS = {
    3457: '綺',   # 丐麗 → 綺麗
    3459: '涛',   # 怒个 → 怒涛
    3460: '躊',   # 丱丶 → 躊躇
    3461: '躇',
    3462: '洒',   # お丼落 → お洒落
    3463: '嬌',   # 愛丿 → 愛嬌
    3464: '璧',   # 完乂 → 完璧
    3465: '嘲',   # 自乖 → 自嘲
    3466: '乗',   # 走りが乘ってくる → 乗る
    3468: '鬱',   # 憂亅 → 憂鬱
    3469: '曖',   # 豫昧 → 曖昧
    3470: '奢',   # 亊らない → 奢らない
    3471: '激',   # 舒烈 → 激烈
    3472: '美',   # 弍しい → 美しい
    3473: '睨',   # 于みつける → 睨みつける
    3474: '皺',   # 眉間に亞を寄せて → 皺
    3476: '高',   # 亠慢 → 高慢
    3481: '惧',   # 絶滅危从種 → 危惧種
    3482: '縁',   # 疾斗との仍 → 縁
    3484: '摯',   # 真仆 → 真摯
    3486: '峙',   # 対仗 → 対峙
    3490: '緻',   # 价密 → 緻密
    3492: '埒',   # 不佚／佚があかない → 埒
    3493: '憑',   # 信估性 → 信憑性
    3494: '咤',   # 叱佛 → 叱咤
    3495: '頷',   # 佝いた → 頷いた
    3488: '憔',   # とても憔仟していて → 憔悴（LT.BIN 字形：忄＋隹＋灬）
    3489: '悴',   # 同上（忄＋亠＋从＋十）；证据见解析报告「未解析位修复」
}
# 3458（丕: 宿泊先の地名「?沢」）／3467（亂: 温泉名「?越温泉」）→ 〔未解析〕
# （字形已取出，见报告；两处候选互斥未收敛，按纪律不猜）
UNDEC = '\u3014\u672a\u89e3\u6790\u3015'

DECOR = set('\u3000\uFFE3\uFF3F\uFFE0\uFFE1\uFF5E\u30FB\uFF0F\uFF3C\uFFE2 '
            '\uFF1F\uFF01\u3001\u3002')

MSG_OFF = 0x10
MSG_N = 0x3BED
BASE = 0x10000
POOL_START = 0x16224C


def dec(c):
    if c >= 3456:                 # 二级区＝追加字形槽，未定值即〔未解析〕
        return SLOTS.get(c, UNDEC)
    if c < NC:
        return CS[c]
    return UNDEC


class Script:
    def __init__(self, path):
        self.d = open(path, 'rb').read()
        self.n = len(self.d) // 2
        self.w = struct.unpack('<%dH' % self.n, self.d)
        self.tab = struct.unpack_from('<%dI' % MSG_N, self.d, MSG_OFF)

    # ---------- 消息 ----------
    def msg_end(self, m):
        """消息区间：下一表项；末条以首个结束码为界（其后是选择肢池）"""
        if m + 1 < MSG_N:
            return (self.tab[m+1] + BASE) // 2
        i = (self.tab[m] + BASE) // 2
        while i < self.n and self.w[i] not in (0xFFFB, 0xFFFC, 0xFFFD):
            i += 1
        return i + 1

    def parse(self, m):
        w = self.w
        s = (self.tab[m] + BASE) // 2
        e = self.msg_end(m)
        assert w[s] == 0xFFF0, (m, hex(s))
        mid = w[s+1]
        i = s + 2
        nt = []
        while i < e and w[i] < 0xFF00:
            nt.append(w[i]); i += 1
        while i < e and w[i] in INLINE:
            nt.append(w[i]); i += 1
        boxes, cur, open_ = [], None, False
        while i < e:
            c = w[i]
            if c == 0xFFFF:
                if cur is not None:
                    boxes.append(cur)
                cur, open_ = [], True
                i += 1
                while i < e and w[i] < 0xFF00:
                    cur.append(dec(w[i])); i += 1
                while i < e and w[i] in INLINE:
                    cur.append(MACRO[w[i]]); i += 1
                    while i < e and w[i] < 0xFF00:
                        cur.append(dec(w[i])); i += 1
            elif c == 0xFFFE:
                i += 1
                if open_:
                    seg = []
                    while i < e and w[i] < 0xFF00:
                        seg.append(dec(w[i])); i += 1
                    while i < e and w[i] in INLINE:
                        seg.append(MACRO[w[i]]); i += 1
                        while i < e and w[i] < 0xFF00:
                            seg.append(dec(w[i])); i += 1
                    cur.append('\x01' + ''.join(seg))
                else:
                    while i < e and w[i] < 0xFF00:
                        i += 1
            elif c in (0xFFFB, 0xFFFC, 0xFFFD):
                if cur is not None:
                    boxes.append(cur); cur = None
                open_ = False; i += 1
            else:
                open_ = False; i += 1
        if cur is not None:
            boxes.append(cur)
        return mid, nt, [''.join(b) for b in boxes]

    # ---------- 选择肢池 ----------
    def pool(self):
        """返回 [(x, y, text)]；参数对 (0,y)/(4,a,b) 剥除（y 严格递增校验）"""
        w, n = self.w, self.n
        i = POOL_START // 2
        items = []
        while i < n:
            if w[i] == 0xFFFF:
                i += 1
                run = []
                while i < n and w[i] < 0xFF00:
                    run.append(w[i]); i += 1
                items.append(run)
            else:
                i += 1
        out, lasty = [], -1
        for run in items:
            if len(run) >= 2 and run[0] == 0 and run[1] > lasty:
                lasty = run[1]; run = run[2:]
            elif len(run) >= 3 and run[0] == 4:
                run = run[3:]
            out.append(''.join(dec(x) for x in run))
        return out


def is_decor(t):
    s = t.replace('\x01', '')
    return all(ch in DECOR for ch in s)


def main(sc_path, out_path):
    sc = Script(sc_path)
    lines = []
    stats = {'msg': 0, 'box': 0, 'decor': 0, 'two': 0}
    for m in range(MSG_N):
        stats['msg'] += 1
        mid, nt, boxes = sc.parse(m)
        real = []
        for b in boxes:
            stats['box'] += 1
            if is_decor(b):
                stats['decor'] += 1
                continue
            t = b.replace('\x01', '').strip()
            if t:
                real.append(t)
        if len(real) > 1:
            stats['two'] += 1
        lines.extend(real)

    opts = sc.pool()
    # 选择肢：17..148 中每组 3 项（第 3 槽为空），排除 32..64 的角色/好物菜单
    groups = []
    for k in range(17, len(opts) - 1, 3):
        g = opts[k:k+3]
        if 32 <= k <= 64:
            continue
        sel = [x for x in g if x.strip()
               and not (x.startswith('\u3000') and len(x) <= 2)]
        groups.append(sel)
    opt_lines = [x for g in groups for x in g]

    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines + opt_lines) + '\n')
    print('messages', stats['msg'], 'boxes', stats['box'], 'decor', stats['decor'],
          'multi-real', stats['two'])
    print('lines', len(lines), 'option groups', len(groups), 'option lines', len(opt_lines),
          'total', len(lines) + len(opt_lines))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(VNTRANS_HOME, '_work_dsb/iso/DATA/SC.BIN'),
         sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, '_work_dsb/out2.txt'))
