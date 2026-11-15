# -*- coding: utf-8 -*-
"""[NS-JP]スタットコール 救命恋愛24時（Romance MD Always On Call）文本提取

## 容器链
  .nsp（PFS0 entry 24 B，非标准 16 B ⇒ 只有 nstool 提得对）
  → Program NCA 4b32f658…（NCA3 / Titlekey crypto / keygen 17）
  → romfs（本作用模拟器 dump 的 romfs：eden/dump/0100C9C01E960000/romfs）
  → Data/StreamingAssets/aa/Switch/2ee3b1db….bundle = Naninovel 编译后的 Script 集合（894 = 447 ja + 447 en）

## 引擎：Naninovel（Unity 视觉小说插件）
  Script 的每个 MonoBehaviour = 一个 .nani 脚本；raw 里是**命令流**：
    [u64 lineNumber][commandClass string][namespace][assembly]… [text][author]
  命令类名：CMsg（显示文本）/ CChara（立绘）/ CWaitKeyOrTime / CBack / CPlayBGM …
  ★ **CMsg 块 = 一次显示 = 一行**；块内第一个非 ASCII 串 = 正文，紧跟的第二个 = 作者（独立名字窗 ⇒ 剔）

## 输出
  行 = 正文（作者剔除）；作者表单独导出供核对
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

BUNDLE = (r'<本地路径>'
          r'Data/StreamingAssets/aa/Switch/2ee3b1db902fe6714f591ccbdfc149b2.bundle')

CMD = re.compile(r'(?:C[A-Z][A-Za-z]{1,20}|AddChoice)')   # 选项命令是 `AddChoice`，不带 C 前缀
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# ── 主角名 ──────────────────────────────────────────────────────────────
# 本作主角名是玩家输入的两个 Naninovel 变量（游戏内无默认值，vndb 主角条目只有 "Protagonist"）：
#   {G_FamilyNameja} = 姓   {G_GivenNameja} = 名
# 交付口径（用户 2026-10-29 指定）：一律换成「主人公」；姓与名**紧挨着**时只出一个「主人公」。
# 实测形态只有两种：严格相邻 `{G_FamilyNameja}{G_GivenNameja}`（53 处）、
# 以及中间夹假名的「{G_GivenNameja}さんが{G_FamilyNameja}の家」（1 处，不是姓名连写 ⇒ 各出一个）。
HERO = '主人公'
HERO_PAIR = re.compile(r'\{G_FamilyNameja\}[ \u3000]{0,1}\{G_GivenNameja\}')   # 姓+名连写
HERO_VAR = re.compile(r'\{(?:G_FamilyNameja|G_GivenNameja)\}')


def heroize(s):
    s = HERO_PAIR.sub(HERO, s)      # 必须先把「姓+名」并成一个，否则会得到「主人公主人公」
    return HERO_VAR.sub(HERO, s)


def strings(raw):
    """扫描序列化串（u32 长度 + UTF-8），返回 [(offset, byte_len, text)]"""
    out = []
    i, n = 0, len(raw)
    while i + 4 <= n:
        L = struct.unpack_from('<I', raw, i)[0]
        if 1 <= L <= 2000 and i + 4 + L <= n:
            b = raw[i + 4:i + 4 + L]
            try:
                s = b.decode('utf-8')
            except UnicodeDecodeError:
                i += 1
                continue
            if all(c == '\n' or c >= ' ' for c in s):
                out.append((i, L, s))
                i += 4 + L
                continue
        i += 1
    return out


def obj_name(raw):
    L = struct.unpack_from('<I', raw, 0x1C)[0]
    return raw[0x20:0x20 + L].decode('utf-8', 'replace')


SN = re.compile(r'\d{9,12}(?:_\d+)?(?:ja|en)')


def parse(raw):
    """返回 [(text, author)]，只取 CMsg 块。

    块结构（实测，obj 1 @0xc1a4）：
        CMsg | Naninovel.Commands | Assembly-CSharp | <scriptName> | u64 lineHash | <text> | … | <author>
    text 位置 = align4(scriptName 结束) + 8；scriptName 为空行时不占位，text 长度 = 0
    """
    import bisect
    ss = strings(raw)
    pos = [o for o, _, _ in ss]
    cmds = [(off, s) for off, L, s in ss if CMD.fullmatch(s)]
    rows = []
    for k, (off, name) in enumerate(cmds):
        if name not in ('CMsg', 'AddChoice'):
            continue
        end = cmds[k + 1][0] if k + 1 < len(cmds) else len(raw)
        a, b = bisect.bisect_right(pos, off), bisect.bisect_left(pos, end)
        block = ss[a:b]
        text, t_end, author = '', off, ''
        # 每个参数都自带 scriptName 前缀；text 的参数 = 某个 scriptName 之后 align4+8 处「确实是串起点」的那个
        for o, sname in [(o, sname) for o, L_, sname in block if SN.fullmatch(sname)]:
            t_off = ((o + 4 + len(sname.encode('utf-8')) + 3) // 4) * 4 + 8
            if t_off + 4 > end:
                continue
            L = struct.unpack_from('<I', raw, t_off)[0]
            if not (0 < L <= 2000 and t_off + 4 + L <= end):
                continue
            try:
                cand = raw[t_off + 4:t_off + 4 + L].decode('utf-8')
            except UnicodeDecodeError:
                continue
            if SN.fullmatch(cand):      # 这一层还是 scriptName（text 参数为空时）
                continue
            if not JP.search(cand):
                continue
            text, t_end = cand, t_off + 4 + L
            break
        # text 之后的第一个非 ASCII 短串 = author（独立名字窗）
        rest = [(o, sname) for o, L_, sname in block
                if o >= t_end and not sname.isascii() and JP.search(sname) and len(sname) <= 30]
        if rest:
            author = rest[0][1]
        if text and JP.search(text):
            rows.append((text, author, name))
    return rows


def main():
    import UnityPy
    env = UnityPy.load(BUNDLE)
    ms = [o for o in env.objects if o.type.name == 'MonoBehaviour']
    scripts = []
    for o in ms:
        raw = o.get_raw_data()
        nm = obj_name(raw)
        if nm.endswith('ja'):
            scripts.append((nm, raw))
    scripts.sort(key=lambda x: x[0])
    print('ja scripts', len(scripts), file=sys.stderr)

    lines, authors = [], {}
    for nm, raw in scripts:
        for text, author, kind in parse(raw):
            text = heroize(text.replace('\n', ''))
            if not text.strip():
                continue
            lines.append(text)
            if author:
                authors[author] = authors.get(author, 0) + 1

    out = os.path.join(VNTRANS_HOME, "提取结果/[NS-JP]スタットコール 救命恋愛24時.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('lines', len(lines), 'authors', len(authors))
    for a, c in sorted(authors.items(), key=lambda x: -x[1])[:30]:
        print('  %-10s %d' % (a, c))


if __name__ == '__main__':
    main()
