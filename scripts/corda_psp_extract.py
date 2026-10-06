#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
金色のコルダ (PSP) 剧本/文本提取器  (自包含, 无外部依赖)
================================================================
解码 : 汉字 = cp932 双字节;
       假名/标点 = 单字节半角片假名 0xA1-0xDF (实际渲染为平假名)
文本段 : `20 <len>` 或 `25 <len>` + len 字节 (自定界)
码流 :
   5d 00 00           行内换行
   5d 01/02/03 00     文本框结束 -> 一次点击结束
   5d 04 00           文本框开始
   5d 05/08/14/17/11/2d 00   文本框设置
   5d <field> 00  [5b <entity:u16> 00]   插入「实体 <entity> 的 <field> 字段」

运行期插入模型 (实测):
   `5d <field> 00` 后紧随 `5b <entity> 00` (= 后缀式操作数);
   实体 0x400-0x7E2 = NPC, 其 姓/名 见 RUNTIME.DAT 对照表;
   实体 0x2E-0x38    = 主要角色 (ID↔角色 尚未定位);
   字段 0x0d=姓, 0x1a=名, 0x2a=場所, 0x2c/0x1d/0x0c=数, 0x1c/0x1e=スキル,
        0x22/0x23=アイテム, 0x09=用語マーカー(无内容), 其余=用語
   无法确定值者输出语义标签 〔人物〕/〔場所〕/〔数〕/〔スキル〕/〔アイテム〕/〔用語〕
   单字节 0xA0 = 零宽标记 -> 删除
字体替换槽 (cp932 西里尔/希腊位) -> 按键/记号 映射

输出 : 一次点击(一个文本框) = 一行; 行内换行合并; UTF-8-BOM + 纯 LF
用法 : python corda_psp_extract.py <event_dir> <out.txt> [--npc npc_table.json] [--gloss] [<单文件.dat>]
"""
import os, sys, glob, re, json, unicodedata

# ---- 半角片假名 -> 平假名 / 标点 -----------------------------------------
def _build_hw():
    m = {0xA1: '。', 0xA2: '「', 0xA3: '」', 0xA4: '、', 0xA5: '・', 0xB0: 'ー'}
    for b in range(0xA6, 0xDE):
        fw = unicodedata.normalize('NFKC', bytes([b]).decode('cp932'))
        m[b] = chr(ord(fw) - 0x60) if (len(fw) == 1 and 0x30A1 <= ord(fw) <= 0x30F6) else fw
    m[0xDE] = '\u3099'; m[0xDF] = '\u309A'
    return m

HW = _build_hw()

ICON_PAIR = {'ЩЪ': '〔ＳＴＡＲＴ〕', 'ЫЬ': '〔ＳＥＬＥＣＴ〕'}
ICON = {
    'И': '○', 'Й': '×', 'К': '△', 'Л': '□',
    'М': '〔アナログパッド〕', 'О': '〔方向キー〕', 'П': '〔左右〕', 'Р': '〔上下〕',
    'С': 'Ｒ', 'Т': 'Ｌ',
    'α': '！', 'β': '？', 'γ': '♥', 'ε': '™',   # γ = 实心心形(♥), ε = 右上角 TM 标志 (用户确认)
    # δ 字形未确定 -> 保留
}

OP2 = {0x5d, 0x5b, 0x23, 0x46, 0x45}
OP3 = {0x7e}
OP1 = (set(range(0x00, 0x40)) | {0x40, 0x5c, 0x7f}) - OP2 - OP3

LINE_END = {0x00}
BOX_END = {0x01, 0x02, 0x03}
BOX_BEGIN = {0x04}
BOX_SETUP = {0x05, 0x08, 0x14, 0x17, 0x11, 0x2d}
FIELD_NAME = {0x0d: 0, 0x1a: 1}          # 0=姓, 1=名
# 主要角色实体 ID -> (姓, 名)   ★ 实测锚定:
#   0x2E=主人公 (「普通科の[1a]が…」=普通科の香穂子が…)
#   0x30=土浦   (「[0d]くんは普通科だから…」/「俺は[0d]。土浦梁太郎。」)
#   0x38=リリ   (台词大量「なのだ」「我輩」)
#   其余按 RUNTIME.DAT 称呼表顺序 (月森→土浦→志水→火原→柚木→冬海→天羽→金澤→王崎→リリ)
MAIN_CHAR = {
    0x2E: ('日野', '香穂子'),   # 主人公 (默认名, 游戏内可改)
    0x2F: ('月森', '蓮'),
    0x30: ('土浦', '梁太郎'),
    0x31: ('志水', '桂一'),
    0x32: ('火原', '和樹'),
    0x33: ('柚木', '梓馬'),
    0x34: ('冬海', '笙子'),
    0x35: ('天羽', '菜美'),
    0x36: ('金澤', '紘人'),
    0x37: ('王崎', '信武'),
    0x38: ('リリ', 'リリ'),
}
FIELD_LABEL = {0x0e: '〔人物〕', 0x20: '〔作曲者〕', 0x2a: '〔場所〕',
               0x2c: '〔数〕', 0x1d: '〔数〕', 0x0c: '〔数〕',
               0x1c: '〔スキル〕', 0x1e: '〔スキル〕',
               0x22: '〔アイテム〕', 0x23: '〔アイテム〕',
               0x1f: '〔用語〕', 0x25: '〔用語〕', 0x29: '〔用語〕', 0x0a: '〔用語〕',
               0x0b: '〔用語〕', 0x1b: '〔用語〕', 0x28: '〔用語〕', 0x24: '〔用語〕'}
DROP_INS = {0x09}
INSERT = set(FIELD_NAME) | set(FIELD_LABEL) | DROP_INS


def look_name(entity, idx, npc):
    """实体 -> (姓/名)[idx]; 未知返回 None"""
    if entity is None:
        return None
    e = MAIN_CHAR.get(entity)
    if e:
        return e[idx]
    r = npc.get(str(entity))
    if r:
        return r[idx]
    return None


def is_text(b):
    return (0x40 <= b <= 0x7e) or (0x80 <= b <= 0xfc)


def walk(data):
    """-> list of (kind, value, offset)"""
    ev, i, n = [], 0, len(data)
    while i < n:
        b = data[i]
        if b in (0x20, 0x25):
            ln = data[i+1]
            seg = data[i+2:i+2+ln]
            if len(seg) == ln and ln > 0 and all(is_text(x) for x in seg):
                ev.append(('TXT', seg, i)); i += 2 + ln; continue
        if b == 0x5d and i + 2 < n and data[i+2] == 0x00:
            ev.append(('TERM', data[i+1], i)); i += 3; continue
        if b == 0x5b and i + 2 < n and data[i+2] == 0x00:
            ev.append(('SET', data[i+1], i)); i += 3; continue
        if b in OP2:
            i += 3; continue
        if b in OP3:
            i += 4; continue
        if b in OP1:
            i += 2; continue
        i += 1
    return ev


def decode(seg):
    out, i = [], 0
    while i < len(seg):
        c = seg[i]
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc:
            out.append(seg[i:i+2].decode('cp932', errors='replace')); i += 2
        elif c == 0xA0:
            # 0xA0 = 省略号「…」; 若紧接 0xA1(。) 则并为句末省略号, 不再输出「。」
            while i < len(seg) and seg[i] == 0xA0:
                i += 1
            if i < len(seg) and seg[i] == 0xA1:
                i += 1
            out.append('…')
        elif c in HW:
            out.append(HW[c]); i += 1
        elif 0x20 <= c < 0x7f:
            out.append(chr(c)); i += 1
        else:
            i += 1
    return ''.join(out)


def apply_icons(s):
    for k, v in ICON_PAIR.items():
        s = s.replace(k, v)
    return ''.join(ICON.get(ch, ch) for ch in s)


_READ = r'[ぁ-んァ-ヾ゛゜ー・\u2010\u2015\uff0d\u301c\uff5e\u3099\u309a 　]'
GLOSS = re.compile(r'^(.{1,10}?)（(' + _READ + r'+)）(.*)$')
READ_INLINE = re.compile(r'(?<=[^\s（、。！？「」『』])（' + _READ + r'+）')


def to_gloss(s):
    m = GLOSS.match(s)
    if m:
        return '【%s】%s' % (m.group(1), READ_INLINE.sub('', m.group(3)))
    return READ_INLINE.sub('', s)


def parse_boxes(data, npc=None, gloss=False):
    boxes, lines, line = [], [], []
    npc = npc or {}
    ev = walk(data)

    def end_line():
        nonlocal line
        if line:
            lines.append(''.join(line)); line = []

    def end_box():
        nonlocal lines
        end_line()
        if lines:
            joined = ''.join(lines)
            # 辞書条目 (見出し語（読み）解説) 不能拆
            if len(lines) >= 8 and not GLOSS.match(joined):
                # 菜单框 (选择肢/列表): 一个框里塞了 8 段以上选项 -> 每条选项各占一行
                for ln in lines:
                    t = apply_icons(ln)
                    if t.strip('。.… 　\u3000'):
                        boxes.append(to_gloss(t) if gloss else t)
            else:
                t = apply_icons(joined)
                # 丢弃「空档」框: 全文只有句号/空白 (游戏中用在停顿处, 无内容)
                if t.strip('。.… 　\u3000'):
                    boxes.append(to_gloss(t) if gloss else t)
        lines = []

    for k, (kind, val, off) in enumerate(ev):
        if kind == 'TXT':
            line.append(decode(val))
        elif kind == 'TERM':
            if val in LINE_END:
                end_line()
            elif val in BOX_END:
                end_box()
            elif val in BOX_BEGIN:
                end_box()
            elif val in FIELD_NAME:
                ent = ev[k+1][1] if (k+1 < len(ev) and ev[k+1][0] == 'SET') else None
                nm = look_name(ent, FIELD_NAME[val], npc)
                line.append(nm if nm else '〔人物〕')
            elif val in FIELD_LABEL:
                line.append(FIELD_LABEL[val])
            else:
                pass
    end_box()
    return boxes


def main():
    argv = sys.argv[1:]
    gloss = '--gloss' in argv
    npc = {}
    if '--npc' in argv:
        i = argv.index('--npc')
        npc = json.load(open(argv[i + 1], encoding='utf-8'))
        del argv[i:i + 2]
    # 开发用检查脚本 (非玩家可见): 效果命令/立ち絵チェック/表示测试
    skip = set()
    if '--skip' in argv:
        i = argv.index('--skip')
        skip = set(argv[i + 1].split(','))
        del argv[i:i + 2]
    argv = [a for a in argv if not a.startswith('--')]
    src, outp = argv[0], argv[1]
    only = argv[2] if len(argv) > 2 else None
    files = ([os.path.join(src, only)] if only
             else sorted(glob.glob(os.path.join(src, '*.DAT'))))
    files = [p for p in files if os.path.basename(p) not in skip]
    out, n = [], 0
    for p in files:
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            continue
        for t in parse_boxes(open(p, 'rb').read(), npc=npc, gloss=gloss):
            out.append(t); n += 1
    with open(outp, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print(f'{len(files)} files, {n} lines -> {outp}')


if __name__ == '__main__':
    main()
