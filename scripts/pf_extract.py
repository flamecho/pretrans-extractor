# -*- coding: utf-8 -*-
"""[NS-JP] ピオフィオーレの晩鐘 -ricordo- —— STCM2L 文本提取

## 容器链
  dump/01005F700DC56000/romfs/CONTENTS/
    STORY.cpk   → SCRIPT/*.DAT ×107（全部同一构建串 `STCM2L Apr 12 2018 18:22:39`）
    SYSTEM.cpk  → DATABASE/dbDictionary.gbin（用語辞典）、dbEntryScript.gbin（脚本顺序表）

## 本作的特殊点：**opcode 基数逐文件变化**
  同一构建串下，正文/名字窗/立绘位置的 opcode 每个脚本都不一样（相邻文件常差 0x10），
  例如 101.DAT 正文 `0x51604`、100.DAT 正文 `0x51614`；450〜560.DAT 正文又是 `0xf9b4`；
  名字窗 101 是 `0x4f318`、560 是 `0x101c0`。⇒ 无法用一张全局表，必须**逐文件探测**。

## 逐文件探测判据（全部结构化，不看字数/内容长短）
  1. 候选记录 = `n>=1` 且 `p0 == i+16+12n+16`（p0 正好指向尾部 4×u32 之后的内联字符串对象）
     且**尾部第 2 个 u32 == 0x12b**（= 「本记录带显示文本」标记；立绘位置/旗标分别是 0x96/0xc8/0xf6）
     且 p0 处的串是日文；末参数不是 `sureN`（排除选项记录）。
  2. **名字窗 op** = 候选记录中「下一条记录也是候选记录、且 op 不同」比例最高的那个
     （名字窗永远紧接在正文之前）——101.DAT 实测 726/741。
  3. **正文 op** = 其余候选 op 全部（同一文件可能有多个，如 450.DAT 的 `0xf9b4` 与 `0x51604` 并存）。

## 表（由探测得到，供参考）
  | 用途 | opcode |
  |---|---|
  | 正文 | 逐文件：`0x51604`/`0x51614`（大多）·`0xf9b4`（450〜454・550〜554・560） |
  | 名字窗 | 逐文件：`0x4f318`/`0x4f328`/`0x101c0` … |
  | 选项 | `0x10f64`(351)・`0x10f74`(40)・`0x668e4`(4)：n=4/5，末参 `sureN`，倒数第二参是 `d`/`e` 单字母类型 |
  | 等待点击 / goto / 转移 | `0x1f4` ／ `0x6` ／ `switch`(n=2,p0='switch') |
  | 立绘位置 / 旗标（不收） | `0x5ebc`/`0x5ecc`（`位置＿xxx`）·`0x628c`（`色変化判定`）·`0x60a4`（`好感度_xxx`） |

## 宏（默认名来自 `0_init.DAT 0x03b884` 的三条 `0x165c4` 记录）
  `0x165c4 [1]'リリアーナ'` / `[2]'アドルナート'` / `[3]'リリィ'`
  ⇒ `#Name[1]`→リリアーナ、`#Name[2]`→アドルナート、`#Name[3]`→リリィ
     配对校验：含 `#Name[1]` 的 118 串里，替换 リリアーナ 后 **55** 条与既有字面行完全相同（换 リリィ 只 3 条）；
     含 `#Name[3]` 的 414 串里替换 リリィ 命中 **241**；含 `#Name[2]` 的 40 串三槽整体替换命中 **18**（反序 0）。
"""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cr_extract as C

BUILD = 'STCM2L Apr 12 2018 18:22:39'
TAG = 'pf'
SRC = os.path.join(VNTRANS_HOME, '_w_pf/story')
DB = os.path.join(VNTRANS_HOME, '_w_pf/db')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]ピオフィオーレの晩鐘 -ricordo-.txt')
SKIP = {'900.DAT'}   # 開発用のシーンジャンプメニュー（`ファイルを選択して下さい。` + `【Vita】/【Switch】` ラベル 15 行）

HERO = 'リリアーナ'
NAMES = {'#Name[1]': 'リリアーナ', '#Name[2]': 'アドルナート', '#Name[3]': 'リリィ'}

C.HERO = HERO
C.FLUSH_OTHERS = True   # 本构建：除正文外任何记录都收框（0x51894 等 = 等待/语音）
C.GOTO_PLAIN = True     # 0x6 = 文本块结束（一文件上百次），不是 if/else 分支

RUBY = re.compile(r'#Ruby\[([^,\]]*),([^\]]*)\]')
RUBY2 = re.compile(r'([\u4e00-\u9fff])\[([\u3041-\u309f\u30a1-\u30ff\u30fc]{1,10})\]')
JP = re.compile(r'[\u3040-\u30ff]')


def clean(t):
    for k, v in NAMES.items():
        t = t.replace(k, v)
    t = RUBY.sub(r'\1', t)
    t = RUBY2.sub(r'\1', t)
    t = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', t)          # #Color[n] 等
    t = re.sub(r'</?(?:ruby|color|size|speed)[^>]*>', '', t)
    t = t.replace('\\n', '').replace('\r', '')
    t = t.replace('\u3000', ' ')
    return re.sub(r'[ \t]+', ' ', t).strip()


C.clean = clean

TEXT_MARK = 0x12B   # 尾部第 2 个 u32：带显示文本


def scan(path):
    d = open(path, 'rb').read()
    u = lambda o: struct.unpack_from('<I', d, o)[0]
    ce = u(0x20)
    st = C.code_start(d, ce)
    if st is None:
        return None, None, None
    recs = []
    i = st
    while i + 16 <= ce:
        pre, op, n, ln = u(i), u(i + 4), u(i + 8), u(i + 12)
        if pre not in (0, 1) or ln < 16 or i + ln > ce:
            break
        recs.append(i)
        i += ln
    cand = {}
    for j, r in enumerate(recs):
        n, op, ln = u(r + 8), u(r + 4), u(r + 12)
        if n != 1:            # 显示文本记录一律 n==1（多参数的是立绘位置/旗标/资源名等参数串）
            continue
        pay = r + 16 + 12 * n
        p0 = u(r + 16)
        if p0 != pay + 16:
            continue
        if (ln - 12 * n - 32) < 0:
            continue
        if u(pay + 4) != TEXT_MARK:
            continue
        last = C.str_at(d, u(r + 16 + 12 * (n - 1)))
        if last and C.SURE.fullmatch(last):
            continue
        s = C.str_at(d, p0)
        if not s or not JP.search(s):
            continue
        cand.setdefault(op, []).append(j)
    if not cand:
        return d, recs, None
    # 名字窗：其记录「下一条也是候选、且 op 不同」的比例最高
    best, best_ratio = None, 0.0
    for op, js in cand.items():
        if len(js) < 5:
            continue
        ok = 0
        for j in js:
            if j + 1 < len(recs):
                nxt = u(recs[j + 1] + 4)
                if nxt != op and (nxt in cand):
                    ok += 1
        ratio = ok / len(js)
        if ratio > best_ratio:
            best, best_ratio = op, ratio
    name_op = best if best_ratio >= 0.6 else None
    texts = {op for op in cand if op != name_op}
    return d, recs, (texts, {name_op} if name_op else set())


def detect_all():
    ops = {}
    for f in sorted(os.listdir(SRC)):
        if not f.endswith('.DAT'):
            continue
        d, recs, got = scan(os.path.join(SRC, f))
        if got is None:
            print('[!] 探测失败', f, file=sys.stderr)
            continue
        ops[f] = got
        C.FILE_OPS[f] = got
    return ops


def option_ops():
    """选项 op：n>=4、末参 = `sureN`、且参数里有日文文本（倒数第二参是 `d`/`e` 之类的类型码）。"""
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
    """dbEntryScript.gbin：24B/行 × N（表长 = 串区起点 0xa20），行 = `[id][名称off][?]`。"""
    d = open(os.path.join(DB, 'dbEntryScript.gbin'), 'rb').read()
    b = d.find(b'/SCRIPT')
    assert b > 0, '顺序表串区未定位'
    out = []
    for i in range(b // 24):
        rid, noff, _ = struct.unpack_from('<3Q', d, i * 24)
        e = d.find(b'\x00', b + noff)
        nm = d[b + noff:e].decode('utf-8', 'replace') if 0 <= noff < len(d) - b else ''
        if nm.startswith('/SCRIPT/'):
            out.append((rid, os.path.basename(nm)))
    return out


def dictionary():
    """dbDictionary.gbin：24B/行（表长 = 串区起点 0x880，另有 16B 尾对齐），行 = `[id][名称off][说明off]`。"""
    d = open(os.path.join(DB, 'dbDictionary.gbin'), 'rb').read()
    m = re.search(rb'(?:[\xe3-\xe9][\x80-\xbf]{2}){3,}', d)
    assert m, '辞典串区起点未定位'
    B = m.start()
    nrows = B // 24
    starts, off = {}, 0
    while off < len(d) - B:
        e = d.find(b'\x00', B + off)
        if e < 0:
            break
        starts[off] = d[B + off:e].decode('utf-8', 'replace')
        off = (e - B) + 1
    rows = []
    for i in range(nrows):
        _id, noff, doff = struct.unpack_from('<3Q', d, i * 24)
        name, desc = starts.get(noff, ''), starts.get(doff, '')
        name = clean(name).strip()
        desc = desc.replace('#n', '')
        desc = RUBY.sub(r'\1', desc)
        desc = re.sub(r'#[A-Za-z]+\[[^\]]*\]', '', desc).replace('\u3000', ' ').strip()
        if name and desc:
            rows.append('【%s】%s' % (name, desc))
    return rows


def main():
    ops = detect_all()
    C.OPT_ALWAYS_OPS |= option_ops()
    C.OPT_SEEN = set()
    order = script_order()
    rows, stat, missing = [], {}, []
    for rid, nm in order:
        if nm in SKIP:
            continue
        p = os.path.join(SRC, nm)
        if not os.path.exists(p):
            missing.append(nm)
            continue
        b, r, nopt = C.parse_file(p, TAG)
        if r is None:
            missing.append(nm + '(起点未定位)')
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
    print('有正文的脚本 %d 个' % sum(1 for v in stat.values() if v[0]))
    print('其中选项 %d 条' % sum(v[1] for v in stat.values()))
    print('选项 op:', ['%#x' % o for o in sorted(C.OPT_ALWAYS_OPS)])
    print('正文 %d 行 + 用語辞典 %d 条 = %d 行 -> %s' % (n_body, len(dct), len(rows), OUT))


if __name__ == '__main__':
    main()
