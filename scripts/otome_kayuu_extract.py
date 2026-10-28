# -*- coding: utf-8 -*-
"""Otomate STCM2L · Switch「函数指针型」文本提取（燃えよ！乙女道士 ～華遊恋語～）

节点布局（实证）：
    [1][func][k][size] [p0][2.0][2.0] [p1][2.0][2.0] ... [p(k-1)][2.0][2.0]
    [op][kind][id][0x10] [0][L/4][1][L][utf8]
  * 头长 = 48 + 12k；参数指针 p_q 在 +0x10+12q；k=1 时 p0 即行内文本
  * 文本记录 [0][L/4][1][L][utf8] 自定界，L = align4(byte+1)
  * func 指针＝语义（跨文件稳定）：
      0x4C198 正文 ／ 0x16D6C 战斗速显正文(#Speed) ／ 0x18CF4 扉文・章题(#Scale)
      0x4B494·0x17550·0x17580 話者名（丢）／ 0xA1xx·0xA4xx·0x9D40 位置判定（丢）
      0x50988 視点変更 ／ 0x16DE4 次回予告・ルート選択（菜单，丢）／ 0x16D9C 地の文（测试，丢）
  * 选项：文本记录后 0x40B 内紧跟 ASCII 跳转标签 `sureN`（L1 自定界）⇒ 一行一条
  * 框（一次点击）：相邻正文记录（前一文本末端 == 后一节点起点）＝同框软换行 → 合并
"""
import sys, os, glob, struct, re

BODY = {0x4C198, 0x16D6C}
EFFECT = {0x18CF4}
NAME = {0x4B494, 0x17550, 0x17580}
SKIP_FILES = {'90.DAT', '99.DAT'}
JP = re.compile('[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
MACRO = re.compile(r'#[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]')
SURE = re.compile(rb'sure\d')
UI_DROP = {'共通をスキップしますか？'}
UI_OPT = {'スキップする', 'スキップしない'}


def text_rec(d, p0):
    """p0 -> (text, end) if [0][L/4][1][L][utf8]"""
    n = len(d)
    if p0 <= 4 or p0 + 16 > n: return None
    if struct.unpack_from('<I', d, p0)[0] != 0: return None
    L4 = struct.unpack_from('<I', d, p0 + 4)[0]
    L = struct.unpack_from('<I', d, p0 + 12)[0]
    if struct.unpack_from('<I', d, p0 + 8)[0] != 1 or L != 4 * L4 or not (4 <= L <= 8000): return None
    if p0 + 16 + L > n: return None
    try:
        return d[p0 + 16:p0 + 16 + L].split(b'\0')[0].decode('utf-8'), p0 + 16 + L
    except Exception:
        return None


def owner(d, i):
    for j in range(i - 44, i - 0x100, -4):
        if j < 0: break
        if struct.unpack_from('<I', d, j)[0] != 1: continue
        k = struct.unpack_from('<I', d, j + 8)[0]
        if not (1 <= k <= 8): continue
        return j, struct.unpack_from('<I', d, j + 4)[0]
    return None, None


def scan(path):
    d = open(path, 'rb').read()
    n = len(d)
    out = []
    for i in range(0x60, n - 8, 4):
        if struct.unpack_from('<I', d, i - 4)[0] != 1: continue
        L = struct.unpack_from('<I', d, i)[0]
        if not (4 <= L <= 8000) or i + 4 + L > n: continue
        if struct.unpack_from('<I', d, i - 8)[0] != L // 4: continue
        if struct.unpack_from('<I', d, i - 12)[0] != 0: continue
        try:
            s = d[i + 4:i + 4 + L].split(b'\0')[0].decode('utf-8')
        except Exception:
            continue
        if not JP.search(s): continue
        pre = struct.unpack_from('<I', d, i - 16)[0]
        te = i + 4 + L
        st, f = owner(d, i)
        opt = bool(SURE.search(d[te:te + 0x40]))
        out.append(dict(off=i, te=te, txt=s, pre=pre, start=st, func=f, opt=opt, inline=(pre == 0x10)))
    return out


def clean(s, hero):
    s = s.replace('#Name[1]', hero)
    s = MACRO.sub('', s)
    return s


def extract(script_dir, hero):
    lines = []
    for p in sorted(glob.glob(os.path.join(script_dir, '*.DAT')),
                    key=lambda x: (len(os.path.basename(x)), os.path.basename(x))):
        if os.path.basename(p) in SKIP_FILES: continue
        items = scan(p)
        cur = None
        for r in items:
            if r['opt']:
                if cur: lines.append(clean(cur[0], hero)); cur = None
                if r['txt'] in UI_OPT: continue
                lines.append(clean(r['txt'], hero))
                continue
            if r['func'] not in BODY and r['func'] not in EFFECT: continue
            if r['txt'] in UI_DROP: continue
            if not r['inline']: continue
            if cur and r['start'] is not None and r['start'] == cur[2]:
                cur = (cur[0] + r['txt'], cur[1], r['te'])
            else:
                if cur: lines.append(clean(cur[0], hero))
                cur = (r['txt'], r['start'], r['te'])
        if cur: lines.append(clean(cur[0], hero))
    return [x for x in lines if x.strip()]


if __name__ == '__main__':
    out = extract(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else 'シュンリン')
    if len(sys.argv) > 2 and sys.argv[2] != '-':
        with open(sys.argv[2], 'w', encoding='utf-8-sig', newline='\n') as fh:
            fh.write('\n'.join(out) + '\n')
    print('lines', len(out))
    for t in out[:10]: print('  ', t)
