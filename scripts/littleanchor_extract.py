#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""リトルアンカー（PS2-JP / SLPS-25929 / Vridge）全文本提取。

链路：ISO9660 → DATA/SC.AFS（CRI AFS，457 条目 = 每个场景一个 .obj 槽）
      → 每条目内 u16 码流：FFF0 记录头 → 名字段 → FFFF → 正文 → FFFE 软换行 → FFFB/FFFD 点击

字符集：与 STORM LOVER / 花宵 / カスタムドライブ 同族（Vridge 自建 SJIS 索引码，
        0 偏移，code=CHARSET 下标）。code>=3456 为**本作自用字形槽**，逐位置定值。
控制码 >=0xF000；0xFFE6=姓（天城）/0xFFE7=名（藍澄）= 主人公名插入宏。
"""
import hashlib
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stormlover_charset import CHARSET as L

HERE = os.path.dirname(os.path.abspath(__file__))
AFS = os.path.join(HERE, '..', '_work_la', 'DATA', 'DATA', 'SC.AFS')
OUT = os.path.join(HERE, '..', '提取结果', '[PS2-JP]リトルアンカー.txt')

EOF_OP = (0xFFFB, 0xFFFD)      # 一次点击
SOFT_BREAK = 0xFFFE            # 框内软换行（合并）
SKIP_OP = 0xFFF3               # 演出记录（无正文）
MACRO = {0xFFE6: '天城', 0xFFE7: '藍澄'}

# 二级区（code>=3456）逐位置定值：全部由真实台词上下文定死（见报告 §5）
LV2 = {
    0x0D80: '―',   # 「結びつき始めた――そういうことだ」（恒双写）
    0x0D81: '几',   # 几帳面
    0x0D82: '刹',   # 刹那的
    0x0D83: '咎',   # お咎めなし／咎めている
    0x0D84: '嗤',   # こっそり嗤きます／ふと嗤く
    0x0D85: '俺',   # 俺の判断で（同句另一副本作 0x0D8A）
    0x0D88: '騒',   # 騒ってる
    0x0D89: '嗅',   # 嗅ぎ付けてくる
    0x0D8A: '私',   # 私の判断で（同句另一副本作 0x0D85）
    0x0D8B: '贄',   # 金のかかった贄／贄になる／私たちを贄にした
    0x0D8C: '埃',   # 埃だらけ
    0x0D8D: '墟',   # 廃墟
    0x0D8E: '救',   # 救って良かったって思えるね
    0x0D8F: '媚',   # 風光明媚
    0x0D90: '峙',   # 対峙
    0x0D91: '徊',   # 徘徊（与 0x0D92 连写）
    0x0D92: '徘',   # 徘徊
    0x0D93: '惧',   # 危惧
    0x0D94: '悧',   # 怜悧
    0x0D95: '慄',   # 戦慄
    0x0D96: '憑',   # 取り憑く
    0x0D97: '憫',   # 不憫なことだ
    0x0D98: '懺',   # 懺悔
    0x0D99: '虐',   # 大量虐殺兵器
    0x0D9A: '抉',   # 心の傷を抉る
    0x0D9B: '拗',   # 拗ねたり
    0x0D9C: '拿',   # 拿捕
    0x0D9D: '拮',   # 拮抗
    0x0D9E: '捏',   # 捏造映像
    0x0D9F: '揉',   # 揉め事／揉めてた
    0x0DA0: '攻',   # 攻め手
    0x0DA1: '摯',   # 真摯
    0x0DA2: '曖',   # 曖昧
    0x0DA4: '杞',   # 杞憂
    0x0DA5: '梳',   # 髪を梳かして
    0x0DA6: '楔',   # 小さな楔が打ち込まれた
    0x0DA7: '殲',   # 殲滅
    0x0DA8: '洒',   # 駄洒落
    0x0DA9: '淹',   # コーヒー淹れようとして
    0x0DAA: '激',   # 激烈な戦い
    0x0DAB: '卑',   # 卑な手段
    0x0DAC: '劣',   # 卑劣な手段
    0x0DAD: '珈',   # 混合珈琲
    0x0DAE: '琲',   # 混合珈琲
    0x0DB0: '璧',   # 完璧
    0x0DB1: '疇',   # 範疇
    0x0DB2: '痍',   # 満身創痍
    0x0DB3: '痺',   # 麻痺
    0x0DB4: '皺',   # 眉間に皺を寄せて
    0x0DB5: '盪',   # 脳震盪
    0x0DB6: '眈',   # 虎視眈々
    0x0DB7: '眩',   # 目眩
    0x0DB8: '睨',   # 睨みつける／睨まれる
    0x0DB9: '醒',   # 目を醒ませ
    0x0DBA: '竄',   # 改竄
    0x0DBC: '絆',   # 絆
    0x0DBD: '綺',   # 綺麗
    0x0DBE: '縷',   # 一縷の望み
    0x0DBF: '罠',   # 罠に陥れられた
    0x0DC0: '翔',   # 天翔ける銀の翼
    0x0DC1: '腑',   # 腑に落ちません／腑抜け
    0x0DC2: '膠',   # 膠着状態
    0x0DC3: '蔑',   # 蔑められた
    0x0DC4: '茹',   # パスタ茹でる
    0x0DC5: '藪',   # 藪から棒
    0x0DC6: '藉',   # 狼藉
    0x0DC7: '蠢',   # 蠢いていた
    0x0DC8: '褄',   # 辻褄
    0x0DCA: '詭',   # 詭弁
    0x0DCB: '戒',   # 戒めるべき
    0x0DCC: '煽',   # 煽う
    0x0DCD: '貪',   # 既得権益を貪る
    0x0DCE: '妨',   # 妨げる
    0x0DCF: '贅',   # 贅沢は敵
    0x0DD0: '贖',   # 贖罪
    0x0DD2: '〔未解析〕',  # 「奪うことに[DD2][DD1]いや恐怖を覚える」→ 未定
    0x0DD1: '〔未解析〕',
    0x0DD3: '響',   # 今のはちょっと響いて／響いた？
    0x0DD4: '〔未解析〕',  # 「歴史的[DD5][DD4]を実現」→ 未定
    0x0DD5: '〔未解析〕',
    0x0DD6: '鏤',   # 宝石を鏤めたような
    0x0DD7: '闊',   # 迂闊
    0x0DD8: '卑',   # 卑劣
    0x0DD9: '隕',   # 隕石
    0x0DDA: '頷',   # 頷ける／こくりと頷く
    0x0DDB: '狙',   # 狙されちゃ
    0x0DDC: '騙',   # 騙った連中
    0x0DDD: '鴦',   # 鴛鴦茶
    0x0DDE: '遥',   # 遥々
}


def decode(code):
    if code in MACRO:
        return MACRO[code]
    if code in LV2:
        return LV2[code]
    if 0 < code < 3456 and code < len(L):
        return L[code]
    if code in (0,):
        return ''
    return '〔未解析〕'


def parse_entries(d):
    n = struct.unpack_from('<I', d, 4)[0]
    out = []
    for i in range(n):
        o, s = struct.unpack_from('<II', d, 8 + i * 8)
        out.append(d[o:o + s])
    return out


def entry_names(d):
    n = struct.unpack_from('<I', d, 4)[0]
    o, s = struct.unpack_from('<II', d, 8 + (n - 1) * 8)
    base = o + s
    names = []
    for i in range(n):
        r = d[base + i * 0x30: base + (i + 1) * 0x30]
        names.append(r[:0x20].split(b'\0')[0].decode('latin1'))
    return names


def records(buf):
    """yield (name_codes, body_codes) —— 一条 = 一个文本框 = 一次点击"""
    v = list(struct.unpack_from('<%dH' % (len(buf) // 2), buf, 0))
    starts = [k for k, x in enumerate(v) if x == 0xFFF0]
    for j, st in enumerate(starts):
        en = starts[j + 1] if j + 1 < len(starts) else len(v)
        seg = v[st:en]
        if SKIP_OP in seg or 0xFFFF not in seg:
            continue
        fi = seg.index(0xFFFF)
        name = [x for x in seg[2:fi] if 0 < x < 0xF000]
        body = []
        for x in seg[fi + 1:]:
            if x in EOF_OP:
                break
            body.append(x)
        yield name, body


def body_text(body):
    out = []
    for x in body:
        if x == SOFT_BREAK:
            continue
        if x in MACRO:
            out.append(MACRO[x])
            continue
        if x >= 0xF000:
            continue          # 框内命令（实测正文内只有 FFE6/FFE7 以外的装饰码）
        out.append(decode(x))
    return ''.join(out)


def build():
    d = open(AFS, 'rb').read()
    ents = parse_entries(d)
    names = entry_names(d)
    lines = []
    seen = {}
    stat = {'dup_files': 0, 'recs': 0}
    for i, buf in enumerate(ents):
        if i == 0:            # LA_BTL_DATE：纯演出槽，无正文
            continue
        h = hashlib.md5(buf).hexdigest()
        if h in seen:
            stat['dup_files'] += 1
            continue
        seen[h] = names[i] if i < len(names) else str(i)
        for name, body in records(buf):
            t = body_text(body)
            if not t:
                continue
            stat['recs'] += 1
            lines.append(t)
    return lines, stat


if __name__ == '__main__':
    lines, stat = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        for t in lines:
            f.write(t + '\n')
    print('lines', len(lines), stat)
