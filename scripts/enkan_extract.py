#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
円環のメモーリア -カケラ灯し- (PSV / PCSG01167 / A'sRing & Dramatic Create) 全文本提取器
====================================================================
引擎：HuneX「Ogre」系（allscr.mrg + MZX0）—— 与 カレイドイヴ / マジきゅん 同族。
输入：PFS 解密后的目录（须含 image/allscr.mrg）。
输出：UTF-8(BOM) + 纯 LF，一次点击 = 一个文本框 = 一行。

allscr.mrg = 自包含 mrgd00 容器（count=174）：
  [0] 脚本名表（172 槽 ×32B，末槽空 → 171 名）
  [1] scr_adr.mrg（mrgd00，地址表，未用）  [2] 颜色小表
  [3..173] 171 个脚本本体，names[i] ↔ member[3+i]
descriptor(8B, u16×4)：off = 8+count*8 + so*0x800 + of；size = (su-1)//0x20*0x10000 + sz。
脚本 = MZX0 压缩（'MZX0'+u32 解压长+LZ77；字面字节 XOR 0xFF）。

指令（';' 分隔，`_CMD(args)`；右闭括号数随指令而异，取首个 '(' 后 rstrip(')')）：
  _ZM<id>(text)        一次点击 = 一个文本框的正文
  _SELR(idx,label,text) 选项（一行一条；text 空者 = 图片式选项，跳过）
  _LVCT(text)          章标题（扉文，上屏；与 _LVSV 同文 → 只取 LVCT）
  _MTLK(1,名前) / _VTLK(名前)  说话人名札（丢弃）
  其余（_VPLY 语音 / _SSPS 立绘 / _SBKD 背景 / _WCOE 窗口 / _ZZ,_ZY 标签 / …）忽略。
正文控制码：`^` = 框内软换行 → 合并（删）；`＄名` = 主角名占位符 → inline 替换为「紗結」。

排除脚本：ENMEMO(系统菜单/启动)、FUNCTION(共通函数库，唯一文本「は！？」已在正篇重复)、
           LX_DEBUG(调试)、MORGUE(触屏语音 UI 占位「タッチボイス」)。
主角默认名：香月 紗結（eboot.elf @0xb2bd4=香月 / @0xb2bdc=紗結；正文亦见「香月＄名」）。
用法： python enkan_extract.py <解密后的目录> <输出.txt>
"""
import struct, io, re, os, sys

HERO_GIVEN = '紗結'      # ＄名（姓氏在正文中写字面「香月」）
EXCLUDE = ('ENMEMO', 'FUNCTION', 'LX_DEBUG', 'MORGUE')


def mzx0_decompress(data, inlen, exlen, xorff=True):
    key = 0xFF
    out = bytearray()
    ring = [b'\xFF\xFF'] * 64 if xorff else [b'\x00\x00'] * 64
    rw = 0
    f = io.BytesIO(data)
    cl = 0
    last = b'\xFF\xFF' if xorff else b'\x00\x00'
    while len(out) < exlen:
        if f.tell() >= inlen:
            break
        if cl <= 0:
            cl = 0x1000
            last = b'\xFF\xFF' if xorff else b'\x00\x00'
        fl = f.read(1)[0]
        cl -= 1 if (fl & 3) == 2 else fl // 4 + 1
        if (fl & 3) == 0:
            out += last * ((fl // 4) + 1)
        elif (fl & 3) == 1:
            k = 2 * (f.read(1)[0] + 1)
            for _ in range(fl // 4 + 1):
                last = bytes(out[len(out) - k:len(out) - k + 2]); out += last
        elif (fl & 3) == 2:
            last = ring[fl // 4]; out += last
        else:
            for _ in range(fl // 4 + 1):
                b = f.read(2)
                if xorff:
                    b = bytes(x ^ key for x in b)
                last = bytes(b); ring[rw] = last; rw = (rw + 1) % 64; out += last
    del out[exlen:]
    return bytes(out)


def mrgd00_members(blob):
    assert blob[:6] == b'mrgd00', 'not mrgd00'
    cnt = struct.unpack('<H', blob[6:8])[0]
    base = 8 + cnt * 8
    out = []
    for i in range(cnt):
        so, of, su, sz = struct.unpack('<HHHH', blob[8 + i * 8:16 + i * 8])
        off = base + so * 0x800 + of
        size = (su - 1) // 0x20 * 0x10000 + sz if su else sz
        out.append(blob[off:off + size])
    return cnt, out


def load_scripts(data_dir):
    blob = open(os.path.join(data_dir, 'image', 'allscr.mrg'), 'rb').read()
    cnt, members = mrgd00_members(blob)
    nam = members[0]
    names = [nam[i:i + 32][:30].rstrip(b'\x00').decode('cp932', 'replace')
             for i in range(0, len(nam) - 31, 32)]
    names = [n for n in names if n]
    out = []
    for i, nm in enumerate(names):
        b = members[3 + i]
        if b[:4] == b'MZX0':
            ex = struct.unpack('<L', b[4:8])[0]
            raw = mzx0_decompress(b[8:], len(b) - 8, ex)
        else:
            raw = b
        out.append((nm, raw.decode('cp932', 'replace')))
    return out


def clean(t):
    t = t.replace('＄名', HERO_GIVEN)
    t = t.replace('^', '')      # 框内软换行 → 合并
    return t


COLON = re.compile(r'^[^\s。「、！？…‥（(【『」』）)〔〕［］《》〈〉]{1,8}[：:]')

# 原文笔误修正（整行定值表，勿用正则泛修；报告单列）—— 原始字节已确认
TYPO_FIX = {
    # L1796：源脚本用半角标点 ､ ｡（字节 0xA4/0xA1）→ 全角 、。
    '新茶の若芽を摘んだり挽いたりふるったりするように､あの人の手をつねったり袖をひいたり振られたり｡こんな風にじゃれ合えるのが若いうちの花だね｡':
        '新茶の若芽を摘んだり挽いたりふるったりするように、あの人の手をつねったり袖をひいたり振られたり。こんな風にじゃれ合えるのが若いうちの花だね。',
    # L23133：源脚本多一个右引号 」」（字节 8176×2）→ 去掉一个
    '「あぁ。ご、ごめん。で、相手は？　瑛太？　蓮？」」':
        '「あぁ。ご、ごめん。で、相手は？　瑛太？　蓮？」',
    # L23423：源脚本「、\神社」多一个孤立反斜杠（字节 0x5C）→ 去掉
    'こちらの姿が本来の蓮なのだから当然といえば当然なのだけど、\\神社にいる時よりも、学園で一緒に過ごしている方が多いから、正装姿の蓮の方が新鮮だった。':
        'こちらの姿が本来の蓮なのだから当然といえば当然なのだけど、神社にいる時よりも、学園で一緒に過ごしている方が多いから、正装姿の蓮の方が新鮮だった。',
}

# 注音（ルビ）：`<読み>基底語|` → 基底語（上屏显示的是基底语，読み为振り仮名）—— 全作仅 1 处
RUBY = re.compile(r'<([^<>]*)>([^<>|]*)\|')


def extract(data_dir):
    lines = []
    for nm, tx in load_scripts(data_dir):
        if nm in EXCLUDE:
            continue
        buf = None
        for tok in tx.split(';'):
            tok = tok.strip()
            mm = re.match(r'^_([A-Za-z0-9]+)\(', tok)
            if not mm:
                continue
            cmd, args = mm.group(1), tok[mm.end():].rstrip(')')
            if cmd.startswith('ZM'):
                if buf is not None:
                    lines.append(buf)
                buf = clean(args)
            elif cmd == 'SELR':
                if buf is not None:
                    lines.append(buf); buf = None
                parts = args.split(',', 2)
                txt = parts[2] if len(parts) >= 3 else ''
                if txt.strip():
                    lines.append(txt)
            elif cmd == 'LVCT':
                if buf is not None:
                    lines.append(buf); buf = None
                lines.append(args.strip())
            # _MTLK / _VTLK / 其余 → 丢弃
        if buf is not None:
            lines.append(buf)
    out = []
    for l in lines:
        l = COLON.sub('', l, count=1)
        l = RUBY.sub(r'\2', l)          # 注音 → 基底语
        l = TYPO_FIX.get(l, l)
        if l.strip():
            out.append(l)
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    data_dir = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else '円環のメモーリア_全文本.txt'
    lines = extract(data_dir)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('%d lines -> %s' % (len(lines), out_path))
