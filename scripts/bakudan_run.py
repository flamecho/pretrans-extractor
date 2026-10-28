#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""バクダン★ハンダン（PSP / ULJM-06057，Idea Factory / Otomate）—— 全文本提取。

容器链路
  ISO9660 -> PSP_GAME/USRDIR/UNION.CPK（CRI CPK v7）
    条目 3000–3430 / 40001–48835 / 50001–52451 / 54001–54056 / 56001–56240 / 64001–64002
    ⇒ 其中 **462 个是 CRILAYLA 压缩的 STCM2L**（`STCM2L Oct  7 2010`），其余是 GIM 图/音频
  STCM2L：`+0x00 "STCM2L <date>"`；`CODE_START_\0` 之后是 `[u32 size][payload]` 指令链
    文本记录（自定界，记录驱动扫描）：`[0][L/4][1][L]` + L 字节 cp932（NUL 填充）
    记录后紧跟 12B 分隔：`[0][cmd][flag]`
      cmd 0xd2 = **文本框开始（= 一次点击）**
      cmd 0xd3 = **同框内换行（合并）**
      其余 cmd（0x01 名表、0x02 名表、0x05 资源、0x6f/0x7a/0xd7…）= 演出/系统，跳过

编码：**明文 cp932**（无自建字符集）
主角：**稲船 沙希**（vndb v10115，Nameable）—— 正文中以 `#Name[1]`（姓）/`#Name[2]`（名）宏出现

用法：python scripts/bakudan_run.py <UNION.CPK> <out.txt>
"""
import os, sys, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK

NAME_SUB = {'#Name[1]': '稲船', '#Name[2]': '沙希'}

C_BOX, C_BR = 0xD2, 0xD3

# 说话人名札（行首 `名「…」` / `名（…）`；独立名字窗 ⇒ 丢弃，不加前缀）
CAST = ('稲船沙希', '調辺歩', '御手洗流星', '士道昴流', '芽御師航大', '若狭永遠',
        '卜部君麻呂', '黒子', '調辺マイ', 'ワルドブー', '魅神真', '？？？',
        'アナウンス', '稲船敬二', '看護師', '医者', '車掌', '蛇足', '男性',
        '黒子？', '司会', '声', '店主')
PUA = re.compile('[\uE000-\uF8FF]')
ASCII_ONLY = re.compile(r'^[\x20-\x7e]+$')


def scan(d):
    """-> [(cmd, text)]，cmd 取自文本记录后紧跟的 12B 分隔。"""
    n = len(d)
    i = 0
    out = []
    while i + 16 <= n:
        if d[i:i + 4] == b'\x00\x00\x00\x00' and d[i + 8:i + 12] == b'\x01\x00\x00\x00':
            nn = struct.unpack_from('<I', d, i + 4)[0]
            L = struct.unpack_from('<I', d, i + 12)[0]
            if 4 <= L <= 0x1000 and L % 4 == 0 and nn == L // 4 and i + 16 + L <= n:
                raw = d[i + 16:i + 16 + L].rstrip(b'\x00')
                try:
                    s = raw.decode('cp932')
                except Exception:
                    s = None
                if s and not any(ord(c) < 0x20 for c in s):
                    k = i + 16 + L
                    cmd = None
                    if d[k:k + 4] == b'\x00\x00\x00\x00':
                        cmd = struct.unpack_from('<I', d, k + 4)[0]
                    # 尾部 `[0][0xd3][0][0x10]` = 一次点击结束；`[0][0xd2][1]` = 同一次点击的续页
                    wait = d[k:k + 16] == b'\x00\x00\x00\x00\xd3\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00'
                    # 名札记录（cmd 0x01/0x02/0x03 的短串）＝说话人切换
                    named = (cmd in (1, 2, 3) and 1 <= len(s) <= 8
                             and not any(ch in s for ch in '「」。（）'))
                    out.append((cmd, s, wait, named))
                    i = k
                    continue
        i += 4
    return out


def usable(s):
    if not s or PUA.search(s) or ASCII_ONLY.match(s):
        return False
    return any('\u3041' <= c <= '\u3096' or '\u30a1' <= c <= '\u30fa'
               or '\u4e00' <= c <= '\u9fff' for c in s)


def sub_name(s):
    for k, v in NAME_SUB.items():
        s = s.replace(k, v)
    return s.replace('#n', '')


def extract(d):
    """按记录出框：0xd2=新框，0xd3=同框换行（合并）。

    ★ 本作脚本会把一句台词的「」跨框拆开（「…」占 2–3 次点击），故末尾再做一次
      「未闭合引号并入下一行」的兜底（仅在 totals 上补齐，见报告）。
    """
    lines, cur = [], None
    for cmd, s, wait, named in scan(d):
        if named:
            if cur:
                lines.append(cur)
                cur = None
            continue
        if cmd == C_BOX:
            if cur:
                lines.append(cur)
            cur = s
        elif cmd == C_BR:
            if cur is not None:
                cur += s.lstrip('\u3000')
        else:
            if cur:
                lines.append(cur)
            cur = None
    if cur:
        lines.append(cur)

    out = []
    for s in lines:
        s = sub_name(s).strip()
        if not usable(s):
            continue
        for nm in CAST:
            if s == nm:
                s = ''
                break
            if s.startswith(nm) and len(s) > len(nm) and s[len(nm)] in '「（(『':
                s = s[len(nm):]
                break
        if not s:
            continue
        s = re.sub(r'[A-Za-z0-9_]{3,}$', '', s).strip()
        if s in ('）', ')', '」', '』'):      # 半角括号残片
            continue
        if usable(s):
            out.append(s)

    # 兜底：行内引号/括号未闭合 ⇒ 与下一行合并（本作台词/心声跨框；限长 300 字防误并）
    def unclosed(t):
        return (t.count('「') > t.count('」') or t.count('（') > t.count('）')
                or t.count('『') > t.count('』'))

    merged = list(out)
    for _ in range(5):
        nxt, changed = [], False
        for s in merged:
            if nxt and (s.startswith(('」', '）', '』'))
                        or unclosed(nxt[-1])):
                if s.startswith('「') and nxt[-1].startswith('「'):
                    s = s[1:]
                nxt[-1] += s
                changed = True
            else:
                nxt.append(s)
        merged = nxt
        if not changed:
            break
    # 双写折叠：整句被原样发射两次（`A…A…` / `AA…B`）
    for i, t in enumerate(merged):
        h = len(t) // 2
        if h >= 6 and t[:h] == t[h:]:
            merged[i] = t[:h]
            continue
        for k in range(4, len(t) // 2 + 1):
            if t[:k] == t[k:2 * k]:
                merged[i] = t[:k] + t[2 * k:]
                break
    # 原文笔误：心声行的收尾用了半角 `)`（同框却写 `（`）⇒ 定值改为全角（登记于报告）
    fixed = []
    for t in merged:
        if '（' in t and ')' in t and ')' not in t.split('（')[0]:
            t = t.replace(')', '）')
        fixed.append(t)
    return fixed


def main():
    src, dst = sys.argv[1], sys.argv[2]
    c = CPK(src)
    entries = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
                     key=lambda e: int(e['name']))
    lines, nfile = [], 0
    for e in entries:
        d = c.raw(e)
        if d[:4] != b'STCM':
            continue
        nfile += 1
        lines.extend(extract(d))
    out = []
    for s in lines:
        if out and out[-1] == s:
            continue
        out.append(s)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('stcm files', nfile, 'lines', len(out), '->', dst)


if __name__ == '__main__':
    main()
