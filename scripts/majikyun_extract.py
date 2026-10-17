#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マジきゅんっ！ルネッサンス (PSV / PCSG00852 / HuneX & BROCCOLI) 全文本提取器
====================================================================
输入：PFS 解密后的 data 目录（须含 allscr.mrg）。
输出：UTF-8(BOM) + 纯 LF 的全文本 txt，一次点击 = 一个文本框 = 一行。

引擎：HuneX「Ogre」系（与 カレイドイヴ 同族，但脚本容器布局与 @n 语义不同）。
  allscr.mrg = 自包含 mrgd00 容器（count=87）：
    [0]  scr.nam      = 脚本名表（84 条 × 32B：30 字符 CP932 名 + \\x00 pad + \\r\\n）
    [1]  scr_adr.mrg  = 地址表（mrgd00，未使用；offset 由 descriptor 直接给出）
    [2]  颜色/字体小表（非文本）
    [3..86]           = 84 个脚本本体，names[i] ↔ member[3+i]
  mrgd00 descriptor（8B，小端 u16 ×4）：sector_off, offset, ssize_upper, size
    real_offset = 8 + count*8 + sector_off*0x800 + offset
    real_size   = (ssize_upper-1)//0x20*0x10000 + size
  脚本 = MZX0 压缩流（4B 'MZX0' + u32 解压长度 + LZ77 数据；字面字节 XOR 0xFF）。

脚本指令以 ';' 分隔，形如 `_CMD(args)`（右闭括号数随指令而异）：
  _ZM<id>(text)   一个文本框的正文
  _MSAD(text)     同一文本框的续接（**本作 41 个 MSAD 全部前置为 `_ZM(...@n)`，1:1 配对**）
  _MTLK1(,名前)    说话人名札（丢弃；姓/名之间为未映射分隔符 0xEC4C）
  _SELR(idx,text[,val]) 选项（一行一条；text 为空者 = 立绘式图片选项，跳过）
  _PSSM(idx,text) ミニシナリオ（MINISCENARIO）正文
  _PRAM(idx,charid,text) メール（DEVMAIL）正文
  _LVSV(n)        章节索引（标题以 CG 图 ec_title0n 上屏，无文字）→ 丢弃
控制码：`^`=框内软换行(合并)；`@n`=框内暂停(与后续 _MSAD 同框 → 合并)；
        `@w<n>`/`@h<n>`=窗口演出；`@r`/`@e`=收尾标记 —— 全部删除。
        0xEC4C = 姓名分隔符（19217 实例全在 姓|名 之间）→ 空格。
        U+FF65(･) → U+30FB(・)（全作仅 1 处笔误，其余 569 处均用 ・）。
        ＊Ａ/＊Ｂ = 主角姓/名占位符（→ 愛ヶ咲 / 小花，inline；默认名取自 eboot 名字输入表）。
行首 `名前：` 前缀按交付规范剥离（DEVMAIL 有 4 行剧情内 `るの：`）。
纯空白文本框（`_PSSM(0,　)` 等）不产出行。
排除文件：TEST_SCRIPT（开发残留）、TEMPLATE（开发模板）、PROFILE（无文本指令，外部 *.mzx 加载）。
用法： python majikyun_extract.py <解密后的 data 目录> <输出.txt>
"""
import struct, io, re, sys, os

HERO_SURNAME = '愛ヶ咲'   # ＊Ａ（eboot @0xcd508 名字输入初始值）
HERO_GIVEN = '小花'       # ＊Ｂ（eboot @0xcd510）
EXCLUDE = ('TEST_SCRIPT', 'TEMPLATE', 'PROFILE')   # 开发残留 / 模板 / 无文本指令
NAME_SEP = '\xEC\x4C'.encode('latin-1') if False else b'\xec\x4c'   # 姓名分隔符（未映射）


def mzx0_decompress(data, inlen, exlen, xorff=True):
    """HuneX MZX0（LZ77 变体）解压；xorff=True 时字面字节 XOR 0xFF。"""
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
                last = bytes(out[len(out) - k:len(out) - k + 2])
                out += last
        elif (fl & 3) == 2:
            last = ring[fl // 4]
            out += last
        else:
            for _ in range(fl // 4 + 1):
                b = f.read(2)
                if xorff:
                    b = bytes(x ^ key for x in b)
                last = bytes(b)
                ring[rw] = last
                rw = (rw + 1) % 64
                out += last
    del out[exlen:]
    return bytes(out)


def mrgd00_members(blob):
    """解析 mrgd00 容器 → [bytes]。"""
    assert blob[:6] == b'mrgd00', 'not mrgd00'
    cnt = struct.unpack('<H', blob[6:8])[0]
    base = 8 + cnt * 8
    out = []
    for i in range(cnt):
        so, of, su, sz = struct.unpack('<HHHH', blob[8 + i * 8:16 + i * 8])
        off = base + so * 0x800 + of
        size = (su - 1) // 0x20 * 0x10000 + sz if su else sz
        out.append(blob[off:off + size])
    return out


def load_scripts(data_dir):
    """返回 [(name, script_text), ...]（按名表顺序）。"""
    blob = open(os.path.join(data_dir, 'allscr.mrg'), 'rb').read()
    members = mrgd00_members(blob)
    nam = members[0]
    names = [nam[i:i + 32][:30].rstrip(b'\x00').decode('cp932', 'replace')
             for i in range(0, len(nam) - 31, 32)]
    out = []
    for k, nm in enumerate(names):
        if 3 + k >= len(members) or not nm:
            continue
        b = members[3 + k]
        if b[:4] == b'MZX0':
            exlen = struct.unpack('<L', b[4:8])[0]
            raw = mzx0_decompress(b[8:], len(b) - 8, exlen)
        else:
            raw = b
        raw = raw.replace(NAME_SEP, b' ')                  # 姓名分隔符（未映射）→ 空格
        out.append((nm, raw.decode('cp932', 'replace')))
    return out


EFF = re.compile(r'@[whenr]\d*')          # 演出/暂停/收尾标记
COLON_PREFIX = re.compile(r'^[^\s。「、！？…‥（(【『」』）)〔〕［］《》〈〉]{1,8}[：:]')


def clean(t):
    t = t.replace('＊Ａ', HERO_SURNAME).replace('＊Ｂ', HERO_GIVEN)
    t = EFF.sub('', t)
    t = t.replace('^', '')                              # 框内软换行 -> 合并
    t = t.replace('\uff65', '\u30fb')                   # 半角中点 -> 全角
    return t


def selr_text(arg):
    """_SELR 的 args：idx,text 或 idx,text,val → 取 text；纯数字尾字段剥掉。"""
    parts = arg.split(',')
    if len(parts) >= 3 and re.fullmatch(r'-?\d+', parts[-1].strip()):
        parts = parts[:-1]
    return ','.join(parts[1:]) if len(parts) > 1 else ''


def extract(data_dir):
    lines = []
    for nm, tx in load_scripts(data_dir):
        if nm in EXCLUDE:
            continue
        buf = ''
        for tok in tx.split(';'):
            tok = tok.strip()
            mm = re.match(r'^_([A-Za-z0-9]+)\(', tok)
            if not mm:
                continue
            cmd, args = mm.group(1), tok[mm.end():].rstrip(')')
            if cmd.startswith('ZM') or cmd == 'MSAD' or cmd == 'PSSM' or cmd == 'PRAM':
                if (cmd.startswith('ZM') or cmd == 'PSSM' or cmd == 'PRAM') and buf:
                    lines.append(buf); buf = ''          # 新文本框：先落上一行
                if cmd == 'PSSM':
                    args = args.split(',', 1)[-1]
                elif cmd == 'PRAM':
                    args = args.split(',', 2)[-1]
                buf += clean(args)
            elif cmd == 'SELR':
                if buf:
                    lines.append(buf); buf = ''
                t = selr_text(args)
                if t:
                    lines.append(t)
        if buf:
            lines.append(buf)
    # 行级规范：去行首 `名前：`（说话人残留）、去纯空白行
    out = []
    for l in lines:
        l = COLON_PREFIX.sub('', l, count=1)
        if l.strip():
            out.append(l)
    # 跨"框"续句归并：某框以「起句但未收尾（「多于」）⇒ 该句必然续在下一框
    # （本作仅 MINISCENARIO 电话场景 1 处：通话被切断，`「…しな。` + `…見て――」` 分属两条 _PSSM）
    merged = []
    i = 0
    while i < len(out):
        cur = out[i]; i += 1
        while cur.startswith('「') and cur.count('「') > cur.count('」') and i < len(out):
            cur += out[i]; i += 1
        merged.append(cur)
    return merged


if __name__ == '__main__':
    argv = sys.argv[1:]
    if len(argv) < 2:
        print(__doc__); sys.exit(1)
    data_dir, out_path = argv[0], argv[1]
    lines = extract(data_dir)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('%d lines -> %s' % (len(lines), out_path))
