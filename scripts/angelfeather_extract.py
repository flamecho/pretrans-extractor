# -*- coding: utf-8 -*-
"""Angel's Feather (PC / BlueImpact 自研 AF 1.03 / BSF1) 全文本提取 —— 单文件自包含版

用法
    python angelfeather_extract.py --src "<安装树目录>" --out <输出.txt>
    python angelfeather_extract.py --src "<安装树>" --verify      # 只做闭合校验
    python angelfeather_extract.py ... -v                         # 逐脚本行数

四层链路
    外层  RAR5 SFX「[JP]Angel's Feather.exe」⇒ 已安装树
          （af.exe / af.log / movie/ / save/ / game00..04.dat）
    容器  game0X.dat = u32 dir_size ＋ 条目区
          [u32 entry_size(=16+名字含NUL)][u32 flag][u32 data_offset][u32 data_size][name\\0]
          数据区自 4+dir_size 起；闭合判据 4+dir_size+Σdata_size == 文件大小 且 offset 单调
    脚本  BSF1 = 魔数 ＋ 标签表 [name\\0][u32 绝对 offset]…（单项 0x00 终止，代码区起点 +1，
          offset == len(b) 是合法 EOF 空段）＋ 记录流
          记录  u16 op > 0x38 ⇒ 裸 cp932 C 串（一条显示行）
                u16 op <= 0x38 ⇒ [u16 op][u32 L][参数块 base=p+6, 长 L]
          遍历  必须从代码区起点**线性走到 EOF**；按标签分段会切断跨记录
    成行  L0（af.exe 反汇编）

成框判据（L0，2026-11-02 复核）
    · 成行函数 0x420740：call 0x419ae0 返非 0 ⇒ 不记；行号 <0 ⇒ 0x420840 新建记录
      （[+0]起、[+4]止、[+0x28]=strcpy(名字)）；行号 >=0 ⇒ 仅当 [0x69f17c] 非 0 才更新 [+4]
    · 文本框是**单例**：0x69ea1c 全 .text 无任何写指令（`cmp [0x69ea1c],0` 判「是否已创建」）
    · 断框 = 行号 0x68dd94 被置负/置 0，全 .text 仅 13 处写：
        10 处 -1 ← op 0x18@0x41e0ae / op 0x02@0x41e1c0 / op 0x01@0x41e32e
                 ＋ 0x418422 / 0x4195a8 / 0x41986b / 0x419ca3 / 0x41a8da
                 / 0x41a9bf / 0x4216fa（窗口/场景侧，非 op 入口）
        2 处 0  ← 0x418cfe（场景重置 0x418bf0 内，全库仅 0x40725f/0x40867d 调用，
                    **不由任何 op 触发**）、0x419df9（渲染时归零）
        1 处 ++ ← 0x41a627（渲染函数 0x419d90 尾部，每条 TEXT 画完 +1）
    · 渲染 0x419d90：行号 <0 ⇒ 归 0 ＋ 0x538fb0 清窗（新框）；行号 >0 ⇒ y = 行号*0x26+0xd
      （同框续行）；名字只在行号 0 用异色 0x69f180 画在文本框第 0 行，正文 +0xd 下移
      ⇒ 名字与正文**同一个文本框**（无独立名字窗）⇒ 保留，行首【名】
    · ★★ 「两条 TEXT 之间夹 op」**不等于**断框：op 0x30（JumpLabel，只改执行位置表与栈）、
      op 0x14（num16 → 0x69b3b4，音）、op 0x04（立绘，只置 0x69f104=0 与坐标）都不碰行号。
      真正的第二次点击必须在中间有 op 0x02（0x421830 等待点击）。
      实测：全库相邻 TEXT 紧邻 26 处；夹 op 但无 op01/02/18 的 204 处 ⇒ 全部同框须合并。

其他约定
    · 选项 = op 0x0f 的重复 strZ（每项建 0x69f400+i*0x18；已读橙 0xffc000 / 未读白 0xffffff）
    · ruby (基底/よみ) ⇒ 只留基底（引擎配置 MsgUseRuby）；@page 等内联码剥离
    · 排除：op 0x00 子码 5 的 430 条章节/场景名（存档 UI）、作者注记（；●◎※Ｓ＃・:）、
            命令残留（special, / break）、game01 的 data\\*.dat 系统数据、说明书 txt、
            game02 全图 / game03 全 mp3
    · 归档优先级 game00（补丁层较新）；x* 别版 147/150 被 op0e/0x12 真实引用 ⇒ 全收
    · 输出 UTF-8 with BOM + 纯 LF
"""
import collections
import os
import re
import struct
import sys

RUBY = re.compile(r'[（(]([^（）()]{1,12})/([^（）()]{1,24})[）)]')
DEV_MARK = '；●◎※Ｓ＃・:'
CMD_HEAD = ('special,',)
CMD_EQ = ('break',)

UNG = {0x2f, 0x30, 0x31, 0x32, 0x34, 0x35, 0x36, 0x38}   # 无守卫族

STAT = collections.Counter()


# ───────────────────────── 容器层：game0X.dat ─────────────────────────
class Bad(Exception):
    pass


def parse_dat(path):
    """→ (bytes, dir_size, [(name, entry_off, data_off, data_size, flag)])"""
    with open(path, 'rb') as f:
        d = f.read()
    dirsize = struct.unpack_from('<I', d, 0)[0]
    ents, off = [], 4
    while off < 4 + dirsize:
        esz, flag, doff, dsz = struct.unpack_from('<4I', d, off)
        end = d.index(b'\x00', off + 16)
        name = d[off + 16:end].decode('cp932', 'replace')
        want = 16 + (end - off - 16) + 1
        if esz != want:
            raise Bad('entry_size 不符 @%d: %d != %d' % (off, esz, want))
        ents.append((name, off, doff, dsz, flag))
        off += esz
    if off != 4 + dirsize:
        raise Bad('目录未恰好走完: %d != %d' % (off, 4 + dirsize))
    return d, dirsize, ents


class Pool(object):
    """game00/01/04 的 .scr 索引；同名跨归档时 game00 优先"""

    def __init__(self, src):
        self.src = src
        self.cache = {}
        self.idx = None

    def index(self):
        if self.idx is None:
            self.idx = {}
            for fn in ('game00.dat', 'game01.dat', 'game04.dat'):
                p = os.path.join(self.src, fn)
                if not os.path.exists(p):
                    continue
                d, _, ents = parse_dat(p)
                self.cache[fn] = d
                for (n, _off, doff, dsz, _fl) in ents:
                    self.idx.setdefault(n, (fn, doff, dsz))
        return self.idx

    def get(self, name):
        fn, doff, dsz = self.index()[name]
        return self.cache[fn][doff:doff + dsz]


# ───────────────────────── 脚本层：BSF1 ─────────────────────────
def _cstr(b, p, end):
    q = b.find(b'\x00', p)
    if q < 0 or q >= end:
        raise Bad('cstr')
    return q + 1


def _nstr(b, p, end):
    if p + 4 > end:
        raise Bad('nstr hdr')
    n = struct.unpack_from('<I', b, p)[0]
    if n > 0x100:
        raise Bad('nstr big %d' % n)
    if p + 4 + n > end:
        raise Bad('nstr body')
    return p + 4 + n


def unguarded(op, b, p, end):
    """无守卫族：载荷由读取原语自己定长，L 只是参考"""
    if op == 0x2f:
        return _nstr(b, p, end)
    if op in (0x30, 0x38):
        return _cstr(b, p, end)
    if op in (0x31, 0x32, 0x35, 0x36):
        return _cstr(b, _nstr(b, p, end), end)
    if op == 0x34:
        if p + 2 > end:
            raise Bad('u16')
        return p + 2
    raise Bad('not ung')


def strz_list(blob):
    """参数块里的重复 strZ（每项前 1 字节形态标记 0x30）"""
    out, p, n = [], 0, len(blob)
    while p < n:
        if blob[p] == 0x30:
            p += 1
            continue
        e = blob.find(b'\x00', p)
        if e < 0:
            out.append(blob[p:])
            break
        out.append(blob[p:e])
        p = e + 1
    return out


def labels(b):
    """→ ([(name, offset)], 代码区起点)"""
    if b[:4] != b'BSF1':
        raise Bad('magic')
    pos, ents, term = 4, [], False
    while True:
        e = b.find(b'\x00', pos)
        if e < 0 or e + 5 > len(b):
            break
        nm = b[pos:e]
        if not nm:                        # 单项 0x00 终止符
            term = True
            break
        if any(c < 0x20 or c > 0x7e for c in nm):
            break
        o = struct.unpack_from('<I', b, e + 1)[0]
        if o < e + 5 or o > len(b):       # == len(b) 是 EOF 空段，合法
            break
        ents.append((nm.decode('ascii'), o))
        pos = e + 5
    return ents, (pos + 1 if term else pos)


def walk(b, start, end):
    """→ [(kind, pos, payload)]；必须恰好走到 end（线性，不按标签分段）"""
    out, p = [], start
    while p < end:
        if p + 2 > end:
            raise Bad('tail at %x' % p)
        op = b[p] | (b[p + 1] << 8)
        if op > 0x38:
            q = b.find(b'\x00', p)
            if q < 0 or q >= end:
                raise Bad('text nul at %x' % p)
            out.append(('text', p, b[p:q]))
            p = q + 1
            continue
        if p + 6 > end:
            raise Bad('hdr at %x' % p)
        L = struct.unpack_from('<I', b, p + 2)[0]
        base = p + 6
        if op in UNG:
            q = unguarded(op, b, base, end)
            out.append(('op', p, (op, L, base, q, b[base:q])))
            p = q
            continue
        lim = base + L
        if lim > end:
            raise Bad('lim>end op%02x at %x (%d>%d)' % (op, p, lim, end))
        out.append(('op', p, (op, L, base, lim, b[base:lim])))
        p = lim
    if p != end:
        raise Bad('end mismatch')
    return out


# ───────────────────────── 成行层 ─────────────────────────
def clean(t):
    """ruby → 基底；剥 @page 等内联控制码"""
    t = RUBY.sub(r'\1', t)
    t = re.sub(r'@(page|clr|clear)\b', '', t)
    return t.strip('　')


def is_cmd(t):
    s = t.replace('　', '').lstrip(': ').strip()
    return s.startswith('@')


def is_dev(s):
    if s[:1] in DEV_MARK:
        return 'note'
    if s in CMD_EQ or s.startswith(CMD_HEAD):
        return 'cmd'
    return None


def build(b):
    """→ [('line', name_bytes, [texts]) | ('opt', [opts])]"""
    ents, code = labels(b)
    recs = walk(b, code, len(b))
    out, name, lines = [], b'', []

    def flush():
        nonlocal lines
        if lines:
            out.append(('line', name, lines))
            lines = []

    for kind, pos, pl in recs:
        if kind == 'text':
            t = pl.decode('cp932', 'replace')
            if is_cmd(t):
                continue
            t = clean(t)
            if not t:
                continue
            d = is_dev(t)
            if d:
                STAT['drop_' + d] += 1
                continue
            lines.append(t)
            continue
        op, L, base, q, blob = pl
        if op == 0x01:
            flush()
            ss = strz_list(blob)
            v = ss[0] if ss else b''
            name = b'' if v[:1] == b'*' else v
        elif op in (0x02, 0x18):
            flush()
        elif op == 0x0f:
            flush()
            opts = [clean(x.decode('cp932', 'replace')) for x in strz_list(blob)]
            opts = [x for x in opts if x]
            if opts:
                out.append(('opt', opts))
    flush()
    return out


def script_names(pool):
    """自然序（数字章号在前，x 别版靠后）"""
    def key(n):
        return [int(x) if x.isdigit() else x.lower()
                for x in re.split(r'(\d+)', n.replace('script\\', ''))]
    return sorted((n for n in pool.index() if n.lower().endswith('.scr')), key=key)


# ───────────────────────── CLI ─────────────────────────
def do_verify(src):
    print('== 归档闭合 ==')
    tot = 0
    for fn in ('game00.dat', 'game01.dat', 'game02.dat', 'game03.dat', 'game04.dat'):
        p = os.path.join(src, fn)
        if not os.path.exists(p):
            print('  %-11s 缺失' % fn)
            continue
        d, dirsize, ents = parse_dat(p)
        covered = sum(e[3] for e in ents)
        want = 4 + dirsize + covered
        mono = all(ents[i][2] + ents[i][3] <= ents[i + 1][2] for i in range(len(ents) - 1))
        ok = (want == len(d)) and mono
        print('  %-11s %12d  条目 %-6d %s  单调=%s'
              % (fn, len(d), len(ents), 'OK' if want == len(d) else
                 'MISMATCH(%d vs %d)' % (want, len(d)), mono))
        if ok:
            tot += 1
    print('  闭合 %d / 5' % tot)

    pool = Pool(src)
    names = script_names(pool)
    ok, bad = 0, []
    kinds = collections.Counter()
    for nm in names:
        try:
            b = pool.get(nm)
            _, code = labels(b)
            for k, _p, pl in walk(b, code, len(b)):
                kinds['text' if k == 'text' else 'op%02x' % pl[0]] += 1
            ok += 1
        except Bad as ex:
            bad.append((nm, str(ex)))
    print('== 脚本闭合 ==')
    print('  线性闭合 %d / %d' % (ok, len(names)))
    for x in bad[:10]:
        print('   ', x)
    print('== 记录构成 ==')
    for k, c in kinds.most_common(15):
        print('  %-6s %d' % (k, c))


def main():
    argv = sys.argv
    src = '.'
    if '--src' in argv:
        src = argv[argv.index('--src') + 1]
    out = None
    if '--out' in argv:
        out = argv[argv.index('--out') + 1]
    if '--verify' in argv:
        do_verify(src)
        if out is None:
            return

    pool = Pool(src)
    lines_out, per = [], []
    for nm in script_names(pool):
        items = build(pool.get(nm))
        nl = no = 0
        for it in items:
            if it[0] == 'line':
                name, texts = it[1], it[2]
                body = ''.join(texts)
                if not body:
                    continue
                n = name.decode('cp932', 'replace').strip('　') if name else ''
                lines_out.append('【%s】%s' % (n, body) if n else body)
                nl += 1
                STAT['named' if n else 'plain'] += 1
                STAT['rows'] += len(texts)
            else:
                for o in it[1]:
                    lines_out.append(o)
                    no += 1
        per.append((nm, nl, no))

    data = '\n'.join(lines_out) + '\n'
    if out is None:
        out = "[JP]Angel's Feather.txt"
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(data)
    print('脚本 %d 个' % len(per))
    print('输出行 %d（正文框 %d / 选项 %d / 框内行 %d）'
          % (len(lines_out), STAT['named'] + STAT['plain'],
             sum(x[2] for x in per), STAT['rows']))
    print('带名字 %d / 旁白 %d' % (STAT['named'], STAT['plain']))
    print('已剔除：作者注记 %d / 命令残留 %d' % (STAT['drop_note'], STAT['drop_cmd']))
    print('→', out, os.path.getsize(out), 'B')
    if '-v' in argv:
        for nm, a, c in per:
            print('  %-42s line=%-5d opt=%d' % (nm, a, c))


if __name__ == '__main__':
    main()
