#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stack OverFlowADV 3.00  SCRIPT.DAT 解析器
   —— 容器 / LZSS / .obj 三段结构 / 消息四元组 全链路

依据（全部来自实测反编译，非猜测）
  容器: 两种尾变体，只有尺寸字段的混淆方式不同，目录块本身同一套
        A（Happiness Cage）尾 12 字节 = [u32 dirCompLen][u32 dirRawLen][u32 unused]，各 XOR 0xF0F0F0F0
        B（アレクディスク）尾 8 字节  = [u32 dirCompLen][u32 dirRawLen]，各按位取反（^0xFFFFFFFF）
        [0, dirEnd-dirCompLen)  成员数据区
        [dirEnd-dirCompLen, dirEnd)  目录块（LZSS 压缩）
        目录解压后 = 成员数 × 0x50；记录 = [u8 idx][u8 rsv][u8 01][u8 01]
                                       [char name[0x40]][u32 off][u32 csize][u32 dsize]
  压缩: 标准 Okumura LZSS  N=4096 F=18 THRESHOLD=2 ring 预填 0 flags MSB-first
        bit=0 → 字面量 1 字节；bit=1 → u16 LE: len=(v&0xF)+3, off=v>>4
        （实现体 LOCPU.DLL 0x10001470，导出 DecodeLz 0x100019f0）
  .obj: 两种头，代码区与记录格式相同
        A: u32 dirOff @0 ; u16 strCount @4 ; {u32 off; u16 len}[strCount] @6
        B: u16 codeOff @0 ; u16 strCount @2 ; {u16 off; u16 len}[strCount] @4
        ...字符串池（明文 CP932，含结尾 NUL）...
        @codeOff: u32 n = 4 + fnCount*8 ; @codeOff+4: {u8 argc,u8 rsv,u16,u16,u16 opId}
        代码区 = @codeOff+n，4 字节定长记录 = [u16 arg][u8 op][u8 sub]
  消息: 每个文本框由 4 条 (op=0x80,sub=0x11) 组成 —— 依次取串 (名字, 正文, 语音, 空)
        池布局 = G 组三元组 (正文,语音,空) 之后紧跟 G 条名字；G = (op=0x00,sub=0x09) 条数
        即 正文=3g, 语音=3g+1, 空=3g+2, 名字=3G+g
        （个别文件末尾的框不发射名字串，此时按 a-3G 归位、缺的就是空名字）
  分支: (op=0x10,sub=0x01) 无条件跳 / (op=0x10,sub=0x02) 条件跳；arg = 跳过记录数（相对下一条）
  选项: (op=0x20,sub=0x11) arg=<变量号> = 选项结果分派块；
        紧贴在它之前、语音槽为空或纯数字（= 选项序号）的连续框就是选单（本作 81 组 169 项，
        与全库空语音框 165 + 数字语音框 4 严格闭合）。
  条件表达式字符串（如 "$13388 1 == "）只被 op=0x05/0x20 引用，不进正文。
"""
import argparse
import os
import re
import struct
import sys

XORKEY = 0xF0F0F0F0
REC = 0x50

# ---------------------------------------------------------------- 顺序表（本作）
# 来源＝SCRIPT.DAT 自带的章节路由表，不是按文件名排序：
#   main.obj   串序 = プロローグ / 01プロローグ / AP01 / 02アレク序章 / a0第一部
#   a0第一部〜第四部（G=0，无正文，串池就是章节跳转表）逐条列出各章脚本顺序
#   续篇 _2 由本篇末串引用：A5五章終了→A5五章終了_2、A6六章終了b→A6六章終了b_2
#   end.obj    串序 = エピローグ / AEアレク王様 / AEアレク旅 / AEプラチナ / AEサフィルス /
#                      AEジル / AEロード / AEプラム / AEカロール / AEルビイ / AEベリル
#   gameover.obj → S3バッドエンドa
# A3三章終了.obj = 空占位（0 串、2 条记录的 return），不收。
ALEX_ORDER = (
    '01プロローグ', '02アレク序章',
    'A1ロード出会い', 'A1ルビイ出会い', 'A1プラム出会い', 'A1カロール出会い',
    'A1ベリル出会い', 'A1ジル出会い', 'SAアレク天使バトルＡ', 'A1一章終了',
    'A2二章開始',
    'A2ルビイ編成1', 'A2ルビイ編成2', 'A2カロール編成1', 'A2カロール編成2',
    'A2ロード編成1', 'A2ロード編成2', 'A2プラム編成1', 'A2プラム編成2',
    'A2ベリル編成1', 'A2ベリル編成2', 'A2ジル編成1', 'A2ジル編成2',
    'SE編成サブa', 'A2二章終了',
    'A3三章開始', 'A3サフィルスフラグ2', 'A3プラチナフラグ1', 'A3プラチナフラグ2',
    'A3サフィルスフラグ1', 'A3ベリルフラグ1', 'A3ジルフラグ1', 'A3ロードフラグ1',
    'A3プラムフラグ1', 'A3カロールフラグ1', 'A3ルビイフラグ1', 'A3夢イベント1',
    'A3三章プロローグアレク', 'A3三章アレク祠内', 'A3三章エピローグアレク',
    'A4四章開始', 'A4回避不可1', 'A4回避不可2',
    'A4ルビイフラグ2', 'A4カロールフラグ2', 'A4ロードフラグ2', 'A4プラムフラグ2',
    'A4ベリルフラグ2', 'A4ジルフラグ2',
    'T0カロール＆アレク編改', 'T0アレク＆ロード', 'T0アレク＆ベリル', 'T0ジル＆アレク編改',
    'SBアレク天使バトルＢ', 'A4プラチナフラグ3', 'A4夢イベント2', 'A4回避不可4', 'A4四章終了',
    'A5五章開始', 'A5回避不可3', 'A5全体編成ｂ', 'A5全体編成ａ',
    'A6ベリル・ジル仲直り', 'A6プラム・ロード仲直り', 'A6ルビイ・カロール仲直り',
    'A5回避不可5', 'A5五章終了', 'A5五章終了_2',
    'A6六章開始', 'A6プラチナフラグ4', 'A6サフィルスフラグ4',
    'A6六章終了a', 'A6六章終了b', 'A6六章終了b_2', 'A6六章終了c',
    'AEアレク王様', 'AEアレク旅', 'AEプラチナ', 'AEサフィルス', 'AEジル', 'AEロード',
    'AEプラム', 'AEカロール', 'AEルビイ', 'AEベリル',
    'S3バッドエンドa',
)
SYSTEM = ('lib', 'sub', 'start', 'main', 'end', 'btl', 'gameover', 'A0汎用戦闘',
          'a0第一部', 'a0第二部', 'a0第三部', 'a0第四部')


# ---------------------------------------------------------------- LZSS
def lzss_decode(src, dst_size):
    N, F = 4096, 18
    ring = bytearray(N)
    r = N - F
    out = bytearray()
    i = 0
    n = len(src)
    flags = 0
    mask = 0
    while len(out) < dst_size:
        if mask == 0:
            if i >= n:
                raise ValueError('LZSS 源耗尽 @%d' % i)
            flags = src[i]
            i += 1
            mask = 0x80
        if flags & mask:
            if i + 1 >= n:
                raise ValueError('LZSS 匹配越界 @%d' % i)
            v = src[i] | (src[i + 1] << 8)
            i += 2
            ln = (v & 0xF) + 3
            off = v >> 4
            for _ in range(ln):
                c = ring[off]
                off = (off + 1) & 0xFFF
                out.append(c)
                ring[r] = c
                r = (r + 1) & 0xFFF
                if len(out) >= dst_size:
                    break
        else:
            if i >= n:
                raise ValueError('LZSS 字面量越界 @%d' % i)
            c = src[i]
            i += 1
            out.append(c)
            ring[r] = c
            r = (r + 1) & 0xFFF
        mask >>= 1
    return bytes(out), i


# ---------------------------------------------------------------- 容器
class ScriptDat:
    """容器尾变体：(tag, 尾长, 尺寸掩码)
      xor12 = Happiness Cage（上作）: 3×u32，各 XOR 0xF0F0F0F0
      not8  = アレクディスク（本作）: 2×u32，各按位取反（^0xFFFFFFFF）
    判据 = 目录块必须 LZSS 自闭合（used == csize）且长度是 0x50 整数倍、成员不越界。
    不做魔数猜测：两个变体都是代码级实测出来的，先试 xor12 再试 not8。"""
    VARIANTS = (('xor12', 12, XORKEY), ('not8', 8, 0xFFFFFFFF))

    def __init__(self, path):
        self.path = path
        self.raw = open(path, 'rb').read()
        d = self.raw
        if len(d) < 12:
            raise ValueError('文件太小')
        bad = []
        for tag, tail, key in self.VARIANTS:
            a, b = struct.unpack_from('<2I', d, len(d) - tail)
            self.dir_csize = a ^ key
            self.dir_dsize = b ^ key
            self.dir_end = len(d) - tail
            self.unused = (struct.unpack_from('<I', d, len(d) - 12)[0] ^ key) if tail == 12 else None
            try:
                self.data_end = self.dir_end - self.dir_csize
                if self.data_end < 0:
                    raise ValueError('目录长度 %d 越界' % self.dir_csize)
                self.members = self._read_dir()
                for m in self.members:
                    if m['off'] + m['csize'] > self.data_end:
                        raise ValueError('成员 %s 越界' % m['name'])
                self.variant = tag
                return
            except ValueError as e:
                bad.append('%s(%s)' % (tag, e))
        raise ValueError('容器尾不符：' + ' | '.join(bad))

    def _read_dir(self):
        d = self.raw
        comp = d[self.data_end:self.dir_end]
        raw, used = lzss_decode(comp, self.dir_dsize)
        if used != len(comp):
            raise ValueError('目录块未闭合 used=%d/%d' % (used, len(comp)))
        if len(raw) % REC:
            raise ValueError('目录长度 %d 非 0x50 整数倍' % len(raw))
        out = []
        for i in range(len(raw) // REC):
            e = raw[i * REC:(i + 1) * REC]
            name = e[4:4 + 0x40].split(b'\0')[0].decode('cp932')
            off, csize, dsize = struct.unpack_from('<3I', e, 4 + 0x40)
            out.append({'idx': e[0], 'name': name, 'off': off, 'csize': csize, 'dsize': dsize})
        return out

    def get(self, name):
        for m in self.members:
            if m['name'].lower() == name.lower():
                blob = self.raw[m['off']:m['off'] + m['csize']]
                data, used = lzss_decode(blob, m['dsize'])
                if used != m['csize']:
                    raise ValueError('%s 未闭合 used=%d/%d' % (name, used, m['csize']))
                return data
        raise KeyError(name)


# ---------------------------------------------------------------- .obj
class Obj:
    """两种 .obj 头：
      A（Happiness Cage）= u32 dirOff / u16 串数 / {u32 off; u16 len}[n] / 池 / u32 n + 函数表 8B + 代码
      B（アレクディスク）= u16 codeOff / u16 串数 / {u16 off; u16 len}[n] / 池 / u32 n + 函数表 8B + 代码
    两种都是：代码从 codeOff+u32@codeOff 起，4 B 定长 [u16 arg][u8 op][u8 sub]。"""
    VARIANTS = ('A', 'B')

    def __init__(self, data, name=''):
        self.data = data
        self.name = name
        bad = []
        for v in self.VARIANTS:
            try:
                (self._read_a if v == 'A' else self._read_b)()
                self.variant = v
                return
            except (struct.error, IndexError, ValueError) as e:
                bad.append('%s(%s)' % (v, e))
        raise ValueError('%s 头部不符：%s' % (name, ' | '.join(bad)))

    def _read_a(self):
        data = self.data
        self.dir_off = struct.unpack_from('<I', data, 0)[0]
        self.str_count = struct.unpack_from('<H', data, 4)[0]
        self.strs = []
        for i in range(self.str_count):
            o, l = struct.unpack_from('<I', data, 6 + i * 6)[0], struct.unpack_from('<H', data, 6 + i * 6 + 4)[0]
            if o + l > len(data):
                raise ValueError('串越界')
            self.strs.append(data[o:o + l])
        self._read_code(self.dir_off)
        if self.dir_off < 6 + self.str_count * 6:
            raise ValueError('目录与串表重叠')

    def _read_b(self):
        data = self.data
        code, cnt = struct.unpack_from('<2H', data, 0)
        if 4 + cnt * 4 > code or code > len(data):
            raise ValueError('头/串表越界')
        tab = [struct.unpack_from('<2H', data, 4 + i * 4) for i in range(cnt)]
        prev = 4 + cnt * 4
        self.strs = []
        for o, l in tab:
            if o < prev or o + l > code:
                raise ValueError('串 %d 越界 %d+%d' % (tab.index((o, l)), o, l))
            prev = o
            self.strs.append(data[o:o + l])
        self.dir_off = code
        self.str_count = cnt
        self._read_code(code)

    def _read_code(self, code_off):
        data = self.data
        n = struct.unpack_from('<I', data, code_off)[0]
        if n < 4 or (n - 4) % 8 or code_off + n > len(data):
            raise ValueError('函数目录异常 n=%d' % n)
        self.fn = (n - 4) // 8
        self.fns = []
        for i in range(self.fn):
            b = code_off + 4 + i * 8
            self.fns.append({'argc': data[b], 'op': struct.unpack_from('<H', data, b + 6)[0]})
        self.code0 = code_off + n
        if (len(data) - self.code0) % 4:
            raise ValueError('代码区长度非 4 的倍数')
        self.nrec = (len(data) - self.code0) // 4
        self.recs = []
        for i in range(self.nrec):
            b = self.code0 + i * 4
            self.recs.append((struct.unpack_from('<H', data, b)[0], data[b + 2], data[b + 3]))

    def text(self, i):
        return self.strs[i].rstrip(b'\0').decode('cp932')

    # ---- 消息抽取：四元组 (名字, 正文, 语音, 空)
    def messages(self):
        """G = 条数(op=0x00,sub=0x09) = 文本框数；
        正文/语音/空 = 串 3g / 3g+1 / 3g+2，名字 = 串 3G+g。
        自检 = 全部 80/11 里 a<3G 的那些必须恰好是 0..3G-1（本作末尾允许「无名字框」，
        此时名字槽不发射 80/11，故名字按 a-3G 归位，缺的就是空名字）。"""
        G = sum(1 for a, o, s in self.recs if (o, s) == (0x00, 0x09))
        if G == 0:
            return 0, []
        bodies, names = [], {}
        for a, o, s in self.recs:
            if (o, s) != (0x80, 0x11):
                continue
            if a >= 3 * G:
                names[a - 3 * G] = self.text(a)
            else:
                bodies.append(a)
        if bodies != list(range(3 * G)):
            raise ValueError('%s 正文下标不成序列（%d 条 / 3G=%d）' % (self.name, len(bodies), 3 * G))
        return G, [(names.get(g, ''), self.text(3 * g), self.text(3 * g + 1)) for g in range(G)]

    def stray(self):
        """未被任何 80/11 引用的字符串（条件表达式等），用于报告"""
        p80 = set(a for a, o, s in self.recs if (o, s) == (0x80, 0x11))
        return [(i, self.text(i)) for i in range(self.str_count) if i not in p80]

    # ---- 选择支：分派块（op=0x20,sub=0x11）前置的选单框
    #   判据只看代码与语音槽，不看正文内容：
    #     ① 记录 (0x20,0x11) 的 arg 是「选项结果变量」（本作是 $13388），即分派块；
    #     ② 它前面最近的那个 (0x00,0x09) 属于最后一个选项框；
    #     ③ 从该框往回数，语音槽为空或纯数字（= 选项序号）的连续框 = 一组选单。
    #   闭合验证（アレクディスク）：81 组 169 项 ＝ 全库空语音框 165 + 数字语音框 4，
    #   且不存在落在分派块之外的「空语音框」——精确闭合，无假阳性。
    #   旧作 Happiness Cage 用的是名字窗标记（`選択肢オートセーブ` / `●<ID>：<text>`），
    #   故保留 `_groups_by_name()` 作兜底：仅当本文件找不到任何分派块时启用。
    DISPATCH = (0x20, 0x11)
    BRANCH_LABEL = re.compile(r'^[●★]([^：]*)：(.*)$')
    CHOICE_MARK = '選択肢オートセーブ'
    # 正文内嵌的渲染控制码：P<数字>（本作只有 2 处，都是 P20…P0 / P5…P0 成对包裹，
    # 语音槽照常有值、画面只显示夹在中间的日文 ⇒ 属控制码，剥掉并记账）
    TEXT_CTRL = re.compile(r'P\d+')

    def choice_labels(self):
        """分岐入口标注串（●/★ + 全角冒号），仅用于报告"""
        out = []
        for s in self.strs:
            m = self.BRANCH_LABEL.match(s.rstrip(b'\0').decode('cp932'))
            if m:
                out.append((m.group(1), m.group(2)))
        return out

    def choice_groups(self, msgs):
        p09 = [i for i, r in enumerate(self.recs) if (r[1], r[2]) == (0x00, 0x09)]
        groups = []
        for d, r in enumerate(self.recs):
            if (r[1], r[2]) != self.DISPATCH:
                continue
            k = max([x for x in p09 if x < d], default=None)
            if k is None:
                continue
            g = p09.index(k)
            run = []
            while g >= 0 and msgs[g][1] and (msgs[g][2] == '' or msgs[g][2].isdigit()):
                run.append(g)
                g -= 1
            if run:
                groups.append(sorted(run))
        if not groups:
            return self._groups_by_name(msgs)
        return groups

    def _groups_by_name(self, msgs):
        """兜底（旧作）：正文与 `●<ID>：<text>` 的 text 相同，且连续成串"""
        opts = set(t for _, t in self.choice_labels())
        marked = set([self.CHOICE_MARK]) | set('●%s：%s' % (i, t) for i, t in self.choice_labels())

        def is_opt(g):
            name, body, _ = msgs[g]
            if body in opts:
                return True
            return name in marked and any(t.startswith(body + '（') for t in opts)

        groups, g = [], 0
        while g < len(msgs):
            if is_opt(g):
                run, start = [], g
                while g < len(msgs) and is_opt(g):
                    run.append(g)
                    g += 1
                groups.append(run)
                continue
            g += 1
        return groups

    def story(self):
        """返回 (正文行列表, 选项组列表, 框数)
        一次点击 = 一行，按代码顺序；选项本身就是正文串，就地留在原位置，不加任何前缀。
        （口径见 output.md §「要收 ② 选项（一行一条、按序）」：前缀会被 check_text 的
          名札判据误判，且属自造文本）"""
        G, msgs = self.messages()
        groups = [[self.TEXT_CTRL.sub('', msgs[g][1]) for g in run] for run in self.choice_groups(msgs)]
        lines = [self.TEXT_CTRL.sub('', msgs[g][1]) for g in range(G) if msgs[g][1]]
        return lines, groups, G


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description='Stack OverFlowADV 3.00 SCRIPT.DAT 解析')
    ap.add_argument('dat')
    ap.add_argument('--list', action='store_true', help='列出成员')
    ap.add_argument('--obj-out', metavar='DIR', help='解压 .obj 到目录')
    ap.add_argument('--text', metavar='OUT.txt', help='导出正文')
    ap.add_argument('--order', default='default',
                    help='正文导出顺序（成员名基名，逗号分隔）；default = 内置 ALEX_ORDER')
    ap.add_argument('--skip-system', action='store_true',
                    help='--report 时略过系统成员（lib/sub/start/main/end/btl/gameover/路由表）')
    ap.add_argument('--report', action='store_true', help='打印逐成员统计')
    args = ap.parse_args()

    sd = ScriptDat(args.dat)
    if args.list:
        print('容器尾 %s；目录块 %d B → %d B，成员 %d 个，数据区 %d B' % (
            sd.variant, sd.dir_csize, sd.dir_dsize, len(sd.members), sd.data_end))
        for m in sd.members:
            print('  %-2d %-16s off=%-8d csize=%-8d dsize=%d' % (
                m['idx'], m['name'], m['off'], m['csize'], m['dsize']))

    if args.obj_out:
        os.makedirs(args.obj_out, exist_ok=True)
        for m in sd.members:
            with open(os.path.join(args.obj_out, m['name']), 'wb') as f:
                f.write(sd.get(m['name']))

    if args.report:
        ng = ni = 0
        for m in sd.members:
            if args.skip_system and m['name'][:-4] in SYSTEM:
                continue
            ob = Obj(sd.get(m['name']), m['name'])
            try:
                G, msgs = ob.messages()
                groups = ob.choice_groups(msgs)
                st = ob.stray()
                ng += len(groups)
                ni += sum(len(x) for x in groups)
                print('  %-16s 串=%-5d 记录=%-6d 函数=%-3d 框=%-5d 选项=%d组%d项 余串=%d' % (
                    m['name'], ob.str_count, ob.nrec, ob.fn, G, len(groups),
                    sum(len(x) for x in groups), len(st)))
            except ValueError as e:
                print('  %-16s 串=%-5d 记录=%-6d 函数=%-3d 非剧本（%s）' % (
                    m['name'], ob.str_count, ob.nrec, ob.fn, e))
        print('  合计 选项 %d 组 %d 项' % (ng, ni))

    if args.text:
        lines = []
        ng = ni = 0
        order = ALEX_ORDER if args.order.strip().lower() == 'default' else args.order.split(',')
        for base in order:
            base = base.strip()
            if not base:
                continue
            nm = base if base.lower().endswith('.obj') else base + '.obj'
            ob = Obj(sd.get(nm), nm)
            sub, groups, G = ob.story()
            lines += sub
            ng += len(groups)
            ni += sum(len(x) for x in groups)
            print('  %-24s 框=%-5d 收行=%-5d 选项=%d组%d项' % (
                nm, G, len(sub), len(groups), sum(len(x) for x in groups)))
        print('  合计 %d 行 / 选项 %d 组 %d 项' % (len(lines), ng, ni))
        with open(args.text, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    sys.exit(main())
