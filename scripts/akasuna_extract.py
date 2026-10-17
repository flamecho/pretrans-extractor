#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
赤い砂堕ちる月 (PSV / PCSG00780 / Landkarte & dramatic create 2016) 全文本提取器
==============================================================================
引擎：HuneX「Ogre」系（allscr.mrg + MZX0）—— 与 カレイドイヴ / マジきゅん / 円環 同族。

输入：PFS 解密后的目录（须含 data/allscr.mrg）。
输出：UTF-8(BOM) + 纯 LF，一次点击 = 一个文本框 = 一行。

data/allscr.mrg = 自包含 mrgd00 容器（count=158）：
  [0] 脚本名表（156 槽 ×32B，末槽空 → 155 名）
  [1] scr_adr.mrg（mrgd00，地址表，未用）  [2] 颜色小表
  [3..157] 155 个脚本本体，names[i] ↔ member[3+i]
descriptor(8B, u16×4)：off = 8+count*8 + so*0x800 + of；size = (su-1)//0x20*0x10000 + sz。
脚本 = MZX0 压缩（'MZX0'+u32 解压长+LZ77；字面字节 XOR 0xFF）。

指令（';' 分隔，`_CMD(args)`）：
  _ZM<id>("正文")        一次点击 = 一个文本框的正文（无 _MSAD / 无 @n）
  _SELR(idx,选项)        选项（1 逗号形）；_SELR(idx,选项,n)（2 逗号形，n=分支号）
  _MTLK(1,名前)          说话人名札（丢弃）
  _ATSV(3,1,"［n章…戦］")  战斗章保存标题（元数据，丢弃）
  _ASMB(...)/_ASBS/_ASBE/_ASBP/_ASBF/_ASSL/_ASSS  场景/战斗元数据、立绘（丢弃）
  _ASDG("…")             攻略提示（系统引导，丢弃）
 其余（_VPLY 语音 / _STFC 立绘 / _FADS …）忽略。

正文控制码：`^` = 框内软换行 → 合并（删）；`@c(r,g,b)` = 文字色 → 删；
            `<基底語,読み>` = 注音 → 取基底语；`＊Ｂ` = 主角名占位符 → inline 替换。
主角默认名：春霞（eboot.elf 结局名表 0xefcbc「汪明と火＄春霞」；Nameable）。

排除脚本：TEST_SCRIPT(开发菜单)、TEST_BATTLE(CG/回想选择调试：番号:NN/292 実名…)、
           START_SCRIPT/ROOT/MAP01_01(无正文)。
用法： python akasuna_extract.py <解密后的目录> <输出.txt>
"""
import struct, io, re, os, sys, unicodedata

HERO_GIVEN = '春霞'          # ＊Ｂ
EXCLUDE_SCRIPTS = {'TEST_SCRIPT', 'TEST_BATTLE', 'START_SCRIPT', 'ROOT', 'MAP01_01'}

AT_COLOR = re.compile(r'@c\([^)]*\)')     # @c(r,g,b) 文字色
RUBY = re.compile(r'<([^<>]*),[\u3040-\u309f\u30a0-\u30ffー]+>')   # <基底語,読み>


def norm_compat(t):
    """CJK 互换汉字（U+FA00–FAFF 等）→ 统一汉字（NFKC 只作用于这些码位，不动全角假名/标点）。
    本作 1 处：0xFA9C → U+FA10 塚 = 塚（U+585A）。仅做同一字的规范化，非改写。"""
    if not any(0xFA00 <= ord(c) <= 0xFAFF or 0x2F800 <= ord(c) <= 0x2FA1F for c in t):
        return t
    return ''.join(unicodedata.normalize('NFKC', c)
                   if (0xFA00 <= ord(c) <= 0xFAFF or 0x2F800 <= ord(c) <= 0x2FA1F) else c
                   for c in t)


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
    blob = open(os.path.join(data_dir, 'allscr.mrg'), 'rb').read()
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
    t = t.replace('＊Ｂ', HERO_GIVEN)
    t = AT_COLOR.sub('', t)
    t = RUBY.sub(r'\1', t)
    t = t.replace('^', '')       # 框内软换行 -> 合并
    return norm_compat(t)


ZM = re.compile(r'^_ZM[0-9a-fA-F]+\(("([^"]*)")?')
SELR = re.compile(r'^_SELR\((.*)\)?$')


def selr_text(args):
    """_SELR(idx,选项) 或 _SELR(idx,选项,n) → 选项文本"""
    parts = args.rstrip(')').split(',')
    if len(parts) <= 1:
        return ''
    if len(parts) >= 3 and re.fullmatch(r'[0-9a-fA-F]+', parts[-1].strip()):
        return ','.join(parts[1:-1])
    return ','.join(parts[1:])


TOKEN = re.compile(r'_([A-Za-z0-9_]+)\(([^;]*)')


def mutually_exclusive(c1, c2):
    """两条守卫条件是否互斥（同变量）：eq k / eq j(k≠j)，eq v / ne v。
    仅条件互斥才是同一点击的备选（5 性格、G241 相遇标记等）；
    条件相同的相邻守卫是两个独立跳块（体都要执行），不可丢。"""
    v1, o1, n1 = c1
    v2, o2, n2 = c2
    if v1 != v2:
        return False
    if o1 == 'eq' and o2 == 'eq':
        return n1 != n2
    if {o1, o2} == {'eq', 'ne'}:
        return n1 == n2
    return False


def extract(data_dir):
    """_IF__(变量,op,值,标签) … _ZY<id>(标签) = 守卫块；相邻且条件互斥的守卫 = 同一点击的备选
    ⇒ 只保留第一支（5 种性格 / G241 相遇标记 / 结局分歧）。"""
    lines = []
    for nm, tx in load_scripts(data_dir):
        if nm in EXCLUDE_SCRIPTS:
            continue
        toks = [(m.group(1), m.group(2)) for m in TOKEN.finditer(tx)]
        stack = []          # [(label, emit)]
        last_cond = {}      # depth -> 最近一个守卫的 (var,op,val)
        dirty = {}          # depth -> 自上次守卫关闭后是否出现过普通指令
        for cmd, args in toks:
            d = len(stack)
            if cmd == 'IF__':
                parts = args.rstrip(')').split(',')
                cond = (parts[0], parts[1], parts[2])
                emit = True
                if d in last_cond and not dirty.get(d, True):
                    emit = not mutually_exclusive(last_cond[d], cond)
                last_cond[d] = cond
                dirty[d] = False
                stack.append((parts[-1], emit))
                continue
            if cmd.startswith('ZY') and stack:
                lbl = args.rstrip(')')
                if stack[-1][0] == lbl:
                    stack.pop()
                else:                       # 防御：向下找匹配标签
                    for k in range(len(stack) - 1, -1, -1):
                        if stack[k][0] == lbl:
                            del stack[k:]
                            break
                dirty[len(stack)] = False
                continue
            dirty[d] = True
            if not all(s[1] for s in stack):
                continue
            if cmd.startswith('ZM'):
                m = re.match(r'^"([^"]*)"', args)
                if m:
                    s = clean(m.group(1))
                    if s.strip():
                        lines.append(s)
            elif cmd == 'SELR':
                s = clean(selr_text(args))
                if s.strip():
                    lines.append(s)
            # MTLK / ATSV / ASMB / ASDG / 其余 → 丢弃
    return lines


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    data_dir = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else '赤い砂堕ちる月_全文本.txt'
    lines = extract(data_dir)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('%d lines -> %s' % (len(lines), out_path))
