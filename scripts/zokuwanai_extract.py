#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
罪喰い ~千の呪い、千の祈り~ for V (PSV / PCSG01019 / HuneX, dramatic create 2017) 全文本提取器
==============================================================================
引擎：HuneX「Ogre」系（allscr.mrg + MZX0）—— 与 カレイドイヴ / マジきゅん / 円環 / 赤い砂 同族。

输入：PFS 解密后的目录（须含 data/allscr.mrg）。
输出：UTF-8(BOM) + 纯 LF，一次点击 = 一个文本框 = 一行。

data/allscr.mrg = 自包含 mrgd00（count=118）：
  [0] 脚本名表（116 槽 ×32B，末槽空 → 115 名）
  [1] scr_adr.mrg（mrgd00 地址表，未用）  [2] 颜色小表
  [3..117] 115 个脚本本体，name(member i) = names[i-3]
descriptor(8B, u16×4)：off = 8+count*8 + so*0x800 + of；size = (su-1)//0x20*0x10000 + sz。
脚本 = MZX0 压缩（'MZX0'+u32 解压长+LZ77；字面字节 XOR 0xFF）。

指令（';' 分隔，`_CMD(args)`）：
  _ZM<id>("正文")      一次点击 = 一个文本框
  _MSAD("续文")         续接同框（前一条 _ZM 以 `^` 收尾）⇒ 合并成一行
  _SELR(idx,选项)       选项（一行一条）
  _MTLK1(,名前)         说话人名札（丢弃）
  _IF__(var,op,val,label) … _ZY<id>(label)   守卫块 —— 实测块内 0 条正文（纯逻辑）⇒ 忽略
  _LVSV(n)              章节号（存档/菜单用，丢弃）
  其余（_VPLY 语音 / _STFC 立绘 / _FADS / _PLDS / _STGS / _GOTO …）忽略。

正文控制码：`^` = 框内软换行 → 合并（删）；`＊Ｂ` = 主角名占位符 → inline 替换为 薫。
主角默认名：庵崎 薫（eboot.elf voice 設定表 0xd5b10「【庵崎　薫】のボイスを…」；Nameable，＊Ｂ=名）。
             ＊Ａ（姓=庵崎）本作未使用（0 处）。

排除脚本：TEST_SCRIPT(开发菜单)、TEMPLATE(模板)。
用法： python zokuwanai_extract.py <解密后的目录> <输出.txt>
"""
import struct, io, re, os, sys

HERO_GIVEN = '薫'                 # ＊Ｂ
HERO_SURNAME = '庵崎'             # ＊Ａ（本作 0 处）
EXCLUDE_SCRIPTS = {'TEST_SCRIPT', 'TEMPLATE'}

# 正文控制码 / 注音
RUBY = re.compile(r'<([^<>,]{1,20}),[^<>,]{1,20}>')   # <基底語,読み> → 取基底語
ATCODE = re.compile(r'@[a-z][0-9a-z]*')               # @w1 / @h1 / @r （演出参数）

# 原文笔误（整行定值表修；勿正则泛修）：TOU_900 _ZM700da 多一个 」。
LINE_FIX = {
    '「『いつかお前に好きな女ができたら、そいつにはこんな暗い空は見せるなよ。満天の星空を見せてやれ』……と」」':
    '「『いつかお前に好きな女ができたら、そいつにはこんな暗い空は見せるなよ。満天の星空を見せてやれ』……と」',
}



def mzx0_decompress(data, inlen, exlen, xorff=True):
    """HuneX MZX0（LZ77 变体）解压；xorff=True 时字面字节 XOR 0xFF。"""
    key = 0xFF
    out = bytearray()
    ring = [b'\xFF\xFF'] * 64 if xorff else [b'\x00\x00'] * 64
    rw = 0
    f = io.BytesIO(data)
    pos = 0
    clear = 0
    last = b'\xFF\xFF' if xorff else b'\x00\x00'
    while len(out) < exlen and pos < inlen:
        if clear <= 0:
            clear = 0x1000
            last = b'\xFF\xFF' if xorff else b'\x00\x00'
        flags = f.read(1)[0]
        pos += 1
        clear -= 1 if (flags & 0x03) == 2 else flags // 4 + 1
        t = flags & 0x03
        if t == 0:
            out += last * ((flags // 4) + 1)
        elif t == 1:
            k = 2 * (f.read(1)[0] + 1); pos += 1
            for _ in range(flags // 4 + 1):
                last = bytes(out[-k:-k + 2]) if k <= len(out) else last
                out += last
        elif t == 2:
            last = ring[flags // 4]
            out += last
        else:
            for _ in range(flags // 4 + 1):
                b = f.read(2); pos += 2
                last = bytes(x ^ key for x in b) if xorff else b
                ring[rw] = last
                rw = (rw + 1) % 64
                out += last
    return bytes(out[:exlen])


def mrgd00_members(d):
    assert d[:6] == b'mrgd00', 'not mrgd00'
    n = struct.unpack_from('<H', d, 6)[0]
    base = 8 + n * 8
    out = []
    for i in range(n):
        so, of, su, sz = struct.unpack_from('<4H', d, 8 + i * 8)
        off = base + so * 0x800 + of
        size = (su - 1) // 0x20 * 0x10000 + sz
        out.append(d[off:off + size])
    return n, out


def load_scripts(dec_dir):
    """返回 [(name, text), ...]，按脚本索引序。"""
    raw = open(os.path.join(dec_dir, 'data', 'allscr.mrg'), 'rb').read()
    n, members = mrgd00_members(raw)
    nm = members[0]
    names = [nm[k:k + 32].rstrip(b'\0\r\n').decode('cp932', 'replace')
             for k in range(0, len(nm), 32)]
    out = []
    for i in range(3, n):
        name = names[i - 3] if i - 3 < len(names) else ''
        blob = members[i]
        if blob[:4] == b'MZX0':
            exlen = struct.unpack_from('<I', blob, 4)[0]
            blob = mzx0_decompress(blob[8:], len(blob) - 8, exlen)
        out.append((name, decode_script(blob)))
    return out


def decode_script(b):
    """脚本字节 → str。0xEC4E = 本引擎控制码（cp932 未映射），先换 0x00 占位再解码。"""
    return b.replace(b'\xec\x4e', b'\x00').decode('cp932', 'replace')


def clean(arg):
    """_CMD 的参数体 → 显示文本。"""
    t = arg.rstrip(')')          # 右闭括号数不等：全部 rstrip
    t = ATCODE.sub('', t)        # @w1/@h1/@r 演出码 → 删
    t = RUBY.sub(r'\1', t)       # <基底語,読み> → 基底語
    t = t.replace('^', '')       # 框内软换行 → 合并
    t = t.replace('\x00', '')    # 0xEC4E 控制码 → 删（行首、不可解码、非显示）
    t = t.replace('＊Ｂ', HERO_GIVEN).replace('＊Ａ', HERO_SURNAME)
    return t.strip()


def parse_text(script):
    """按「一次点击 = 一行」还原正文 + 选项。"""
    lines = []
    buf = None

    def flush():
        nonlocal buf
        if buf is not None and buf.strip():
            lines.append(LINE_FIX.get(buf.strip(), buf.strip()))
        buf = None

    for tok in script.split(';'):
        tok = tok.strip()
        if not tok.startswith('_'):
            continue
        p = tok.find('(')
        name = tok[:p] if p >= 0 else tok
        arg = tok[p + 1:] if p >= 0 else ''
        if name.startswith('_ZM'):
            flush()
            buf = clean(arg)
        elif name == '_MSAD':
            buf = (buf or '') + clean(arg)
        elif name == '_MTLK' or name.startswith('_MTLK'):
            pass
        elif name == '_SELR':
            flush()
            body = arg.split(',', 1)[1] if ',' in arg else arg
            txt = clean(body)
            if txt:
                lines.append(txt)
    flush()
    return lines


def main():
    dec_dir, out_path = sys.argv[1], sys.argv[2]
    scripts = load_scripts(dec_dir)
    total = 0
    res = []
    for name, script in scripts:
        if name in EXCLUDE_SCRIPTS:
            continue
        ls = parse_text(script)
        if ls:
            res.append((name, ls))
            total += len(ls)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        for name, ls in res:
            for line in ls:
                f.write(line + '\n')
    print('scripts with text: %d / %d ; lines: %d' % (len(res), len(scripts), total))


if __name__ == '__main__':
    main()
