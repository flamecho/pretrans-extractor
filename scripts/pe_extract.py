# -*- coding: utf-8 -*-
"""[NS-JP] ピオフィオーレの晩鐘 -Episodio1926- —— STCM2L 文本提取

## 容器链
  dump/01009E30120F4000/romfs/CONTENTS/
    STORY.cpk   → SCRIPT/*.DAT ×116（全部同一构建串 `STCM2L Apr 12 2018 18:22:39`）
    SYSTEM.cpk  → DATABASE/dbDictionary.gbin（用語辞典）、dbEntryScript.gbin（脚本顺序表）

## 逐文件探测（继承 `pf_extract.py` 的思路，标记值不同故不写死）
  本作正文记录：`n==1`、尾部 `[0x10c][0x135][id][0x10]`、内联串对象在 `pay+16`；
  空文本记录（同 op）尾部是 `[0x10c][0xfc][id][0x10]`、`len==44` 没有内联串。
  ⇒ 判据不依赖固定标记值：**`n==1` 且 `pay+16` 处能按内联串对象解析出日文** 即候选；
     正文 op = 候选里计数最多者（本作 78 个文件为 `0x5c3dc`，6 个为 `0x133b0`，1 个 `0x5c3ec`）
  名字窗：`n==2`，param0 → 内联串（`ニコラ`/`ラウル`…）、param1 是 1 字节代码；
     判定 = 「其记录的下一条是正文候选」比例最高者（本作 `0x570e0`）
  选项：`0x14960`，`n=4`：`[flag][文本][d|e 类型码][sureN]`

## 表（实测）
  | 用途 | opcode |
  |---|---|
  | 正文 | `0x5c3dc`（多数）/ `0x133b0` / `0x5c3ec`（逐文件） |
  | 名字窗 | `0x570e0` |
  | 选项 | `0x14960` |
  | 立绘位置 / 好感度（不收） | `0x6160`・`0x6530`（`位置＿xxx`）・`0x6348`（`好感度_xxx`） |
  | 等待/语音 | `0x51894` 类（`n=0`）；`0x6` = 文本块结束 |

## 宏（默认名表 `0_init.DAT 0x1a5e0`，三条 `0x1a5e0[n]` 记录）
  `[1]リリアーナ` / `[2]アドルナート` / `[3]リリィ`（与本篇、FD 完全一致）
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cr_extract as C

BUILD = 'STCM2L Apr 12 2018 18:22:39'
TAG = 'pe'
SRC = os.path.join(VNTRANS_HOME, '_w_pe/story')
DB = os.path.join(VNTRANS_HOME, '_w_pe/db')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]ピオフィオーレの晩鐘 -Episodio1926-.txt')

HERO = 'リリアーナ'
NAMES = {'#Name[1]': 'リリアーナ', '#Name[2]': 'アドルナート', '#Name[3]': 'リリィ'}
C.HERO = HERO
C.FLUSH_OTHERS = True    # 任何非正文记录都收框（等待/语音/演出）
C.GOTO_PLAIN = True      # 0x6 = 文本块结束，不是 if/else 分支

RUBY = re.compile(r'#Ruby\[([^,\]]*),([^\]]*)\]')
RUBY2 = re.compile(r'([\u4e00-\u9fff])\[([\u3041-\u309f\u30a1-\u30ff\u30fc]{1,10})\]')
JP = re.compile(r'[\u3040-\u30ff]')


def clean(t):
    for k, v in NAMES.items():
        t = t.replace(k, v)
    t = RUBY.sub(r'\1', t)
    t = RUBY2.sub(r'\1', t)
    t = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', t)
    t = re.sub(r'</?(?:ruby|color|size|speed)[^>]*>', '', t)
    t = t.replace('\\n', '').replace('\r', '')
    t = t.replace('\u3000', ' ')
    return re.sub(r'[ \t]+', ' ', t).strip()


C.clean = clean


def scan(path):
    """返回 (正文 op 集合, 名字窗 op 集合)。见文件头判据。"""
    d = open(path, 'rb').read()
    u = lambda o: struct.unpack_from('<I', d, o)[0]
    ce = u(0x20)
    st = C.code_start(d, ce)
    if st is None:
        return None
    recs = []
    i = st
    while i + 16 <= ce:
        pre, op, n, ln = u(i), u(i + 4), u(i + 8), u(i + 12)
        if pre not in (0, 1) or ln < 16 or i + ln > ce:
            break
        recs.append(i)
        i += ln
    textc = {}
    namec = {}
    for j, r in enumerate(recs):
        n, op, ln = u(r + 8), u(r + 4), u(r + 12)
        if n < 1:
            continue
        pay = r + 16 + 12 * n
        if n == 1 and ln - 12 * n - 32 >= 0:
            s = C.str_at(d, pay + 16)
            if s and JP.search(s):
                textc.setdefault(op, []).append(j)
        p0 = C.str_at(d, u(r + 16))
        if p0 and JP.search(p0):
            namec.setdefault(op, []).append(j)
    if not textc:
        return None
    top = max(len(v) for v in textc.values())
    texts = {op for op, js in textc.items() if len(js) >= 20 and len(js) >= 0.15 * top}
    # 名字窗：其记录的下一条是正文候选、且 op 不同
    best, best_ratio = None, 0.0
    for op, js in namec.items():
        if op in texts or len(js) < 5:
            continue
        ok = sum(1 for j in js if j + 1 < len(recs) and u(recs[j + 1] + 4) in texts)
        ratio = ok / len(js)
        if ratio > best_ratio:
            best, best_ratio = op, ratio
    names = {best} if best and best_ratio >= 0.6 else set()
    return (texts, names)


def detect_all():
    for f in sorted(os.listdir(SRC)):
        if not f.endswith('.DAT'):
            continue
        got = scan(os.path.join(SRC, f))
        if got is None:
            continue
        C.FILE_OPS[f] = got


def option_ops():
    found = set()
    for f in sorted(os.listdir(SRC)):
        d = open(os.path.join(SRC, f), 'rb').read()
        u = lambda o: struct.unpack_from('<I', d, o)[0]
        ce = u(0x20)
        st = C.code_start(d, ce)
        if st is None:
            continue
        i = st
        while i + 16 <= ce:
            pre, op, n, ln = u(i), u(i + 4), u(i + 8), u(i + 12)
            if pre not in (0, 1) or ln < 16 or i + ln > ce:
                break
            if n >= 3:
                ps = [C.str_at(d, u(i + 16 + 12 * k)) for k in range(n)]
                if ps and ps[-1] and C.SURE.fullmatch(ps[-1]) \
                        and any(x and JP.search(x) and not C.SURE.fullmatch(x) for x in ps):
                    found.add(op)
            i += ln
    return found


def script_order():
    """dbEntryScript.gbin：24B/行 × 112（串区 0xa90，另 16B 尾对齐），行 = `[id][名称off][?]`。"""
    d = open(os.path.join(DB, 'dbEntryScript.gbin'), 'rb').read()
    b = d.find(b'/SCRIPT')
    assert b > 0, '顺序表串区未定位'
    out = []
    for i in range(b // 24):
        rid, noff, _ = struct.unpack_from('<3Q', d, i * 24)
        if not 0 <= noff < len(d) - b:
            continue
        e = d.find(b'\x00', b + noff)
        nm = d[b + noff:e].decode('utf-8', 'replace')
        if nm.startswith('/SCRIPT/'):
            out.append((rid, os.path.basename(nm)))
    return out


def dictionary():
    """dbDictionary.gbin：**32B/行 × 116**（串区起点 0xe80），行 = `[id][?][名称off][说明off]`。"""
    d = open(os.path.join(DB, 'dbDictionary.gbin'), 'rb').read()
    m = re.search(rb'(?:[\xe3-\xe9][\x80-\xbf]{2}){3,}', d)
    assert m, '辞典串区起点未定位'
    B = m.start()
    assert B % 32 == 0, '辞典表长与串区起点不闭合: 0x%x' % B
    starts, off = {}, 0
    while off < len(d) - B:
        e = d.find(b'\x00', B + off)
        if e < 0:
            break
        starts[off] = d[B + off:e].decode('utf-8', 'replace')
        off = (e - B) + 1
    rows = []
    for i in range(B // 32):
        _id, _z, noff, doff = struct.unpack_from('<4Q', d, i * 32)
        name, desc = starts.get(noff, ''), starts.get(doff, '')
        name = clean(name).strip()
        desc = desc.replace('#n', '')
        desc = RUBY.sub(r'\1', desc)
        desc = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', desc).replace('\u3000', ' ').strip()
        if name and desc:
            rows.append('【%s】%s' % (name, desc))
    return rows


def main():
    detect_all()
    C.OPT_ALWAYS_OPS |= option_ops()
    C.OPT_SEEN = set()
    order = script_order()
    rows, stat, missing, menu = [], {}, [], []
    for rid, nm in order:
        p = os.path.join(SRC, nm)
        if not os.path.exists(p):
            missing.append(nm)
            continue
        b, r, nopt = C.parse_file(p, TAG)
        if r is None:
            missing.append(nm + '(起点未定位)')
            continue
        if r and nopt == len(r):
            menu.append(nm)          # 整份都是选项 ⇒ 菜单台本
            continue
        stat[nm] = (len(r), nopt)
        rows.extend(r)
    n_body = len(rows)
    dct = dictionary()
    rows.extend(dct)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(rows) + '\n')
    print('脚本 %d 个（顺序表）／缺 %d：%s' % (len(order), len(missing), missing[:5]))
    print('有正文的脚本 %d 个；整份剔除的菜单台本 %d 个：%s' % (
        sum(1 for v in stat.values() if v[0]), len(menu), ' '.join(menu)))
    print('其中选项 %d 条' % sum(v[1] for v in stat.values()))
    print('选项 op:', ['%#x' % o for o in sorted(C.OPT_ALWAYS_OPS)])
    print('正文 %d 行 + 用語辞典 %d 条 = %d 行 -> %s' % (n_body, len(dct), len(rows), OUT))


if __name__ == '__main__':
    main()
