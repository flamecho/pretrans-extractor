#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""CRAZY CHA!N -エルピスの鎖- (Nintendo Switch) 全文本提取

作品: オトメイト / アイディアファクトリー, 2026-07-09, 女性向け恋愛ADV
引擎: Unity (IL2CPP) + 自研 ADV  —— 剧本为纯文本脚本 `Data/StreamingAssets/Script/EV###-###.h`

链路:
  XCI → (HFS0 手工解析) → NCA(Program) → hactool -t nca --romfsdir= → RomFS
  → Data/StreamingAssets/Script/*.h (UTF-8 BOM, CRLF) + Setting/*.csv

脚本格式:
  SET_TALK( <ch>, <win>, "<話者名>", <voice>, "<正文>" )   一次点击 = 一个文本框
  @REWORD( ... )   ← 玩家改过主角名时替换显示的「名前差分」版（默认名时不显示，故默认不收）
  CHOICE_JUMP( <key>, DIVxxxx, ... )  ← 选项正文在 Setting/CHOICE.csv（按 key 取）
  // 行 / /* */ 块 = 制作注释, 不收
正文内标记:
  `\`            = 框内软换行 → 合并（`\　` 连全角空格一并合并掉）
  `$語$`         = 用語强调 → 去 `$`（保留词）
  `#字#[よみ]`   = ルビ → 去读音保留基底字
  `&`            = 主角名占位 → 默认名「ソフィア」
  `\"`           = 个别脚本的错写（开头引号前多一个 `\`）

用法:
  python scripts/crazychain_extract.py \
      --romfs _work_ccn/romfs --outdir 提取结果 [--no-title] [--with-reword]
"""
import os
import re
import csv
import io
import sys
import argparse
import collections

BS = chr(92)
DEFAULT_NAME = 'ソフィア'          # 主角默认名（脚本内 `&` / 話者名 `&`）
STRIP_PLUS = False                 # 名札の姓名区切`+`を本文から除去（勿ノ怪契リ型）
INCLUDE_TITLE = True               # `扉文`(Setting/EV_TITLE.csv 第5列) 是否收（直接上屏的标题卡）

DROPPED = []                       # 源侧截断、无法显示的语句
TALK_RE = re.compile(r'^(@?)(SET_TALK|REWORD)\s*\(')
CMD_RE = re.compile(r'^[A-Z][A-Z0-9_]*\s*\(')
DQ_RE = re.compile(r'(?<!\\)"')          # 未转义的引号（`\"` 是数据错写的软换行）


def qcount(s):
    return len(DQ_RE.findall(s))
CHOICE_RE = re.compile(r'^CHOICE_JUMP\s*\(')


# ---------------------------------------------------------------- 文本变换
def strip_ruby(s):
    """`#基底#[よみ]` → `基底`；基底不含引号/空白/等号#（防误伤）

    另有数据错写 `基底#[よみ]`（缺前导 `#`，如 `#"陽菜#[ひな]`）⇒ 第二遍补剥。
    """
    s = re.sub(r'#([^#"\'=' + BS + r'\s]+)#\[[^\]]*\]', r'\1', s)
    return re.sub(r'([^#\s"\']+)#\[[^\]]*\]', r'\1', s)


def transform(txt, name, strip_plus=False):
    """正文规范化：去转义 / 合并软换行 / 去标记 / 代入主角名"""
    txt = txt.replace(BS + '"', '"' if not strip_plus else '')  # 个别脚本的错写
    txt = txt.replace(BS + '\u3000', '')             # 换行 + 全角空格缩进 → 一并合并
    txt = txt.replace(BS, '')                        # 软换行 → 合并
    txt = strip_ruby(txt)                            # ルビ → 基底字
    txt = txt.replace('$', '')                       # 用語强调标记
    txt = txt.replace('&', name)                     # 主角名
    if strip_plus:
        txt = txt.replace('+', '')                   # 名札の姓名区切`+`（本文では素の姓名）
    return txt.strip()


# ---------------------------------------------------------------- 参数拆分
def split_args(body):
    """按顶层逗号拆分（引号内的逗号不拆；`\\"` 视为字面引号，不切换状态）"""
    args, cur, inq, prev = [], '', False, ''
    for ch in body:
        if ch == '"' and prev != BS:
            inq = not inq
            cur += ch
            prev = ch
            continue
        if ch == ',' and not inq:
            args.append(cur)
            cur = ''
            prev = ch
            continue
        cur += ch
        prev = ch
    args.append(cur)
    return args


def unquote(a):
    """取引号内内容：**到第一个未转义的 `"` 为止**（引擎同口径）。

    ★2026-10-14：原实现「首尾各去一个引号」会把**数据错写**的尾随多余引号吃进正文。
    实例 EV006-004.h: `"「こんばんは、&。\\　…」""`（末尾多一个 `"`）⇒ 输出尾部多一个
    半角 `"`；同句 `@REWORD` 孪生行无此引号，可证是错写。改成「到首个闭合引号为止」后
    多余引号自然丢弃。`\\"`（个别脚本的开头错写）仍保留给 transform 还原成 `"`。
    """
    a = a.strip()
    if a.startswith('#' + '"'):                        # 数据错写：`#"本文"`（缺开头引号）
        a = a[1:]
    if a.startswith(BS + '"'):
        a = a[1:]
    if not a.startswith('"'):
        return a
    out, i = '', 1
    while i < len(a):
        if a[i] == BS and i + 1 < len(a):      # `\"` → 字面引号，交给 transform 处理
            out += a[i:i + 2]
            i += 2
            continue
        if a[i] == '"':
            return out
        out += a[i]
        i += 1
    return out                                # 无闭合引号 → 取到行尾


def load_lines(path):
    """读脚本 → 去块注释 → 组装完整语句（容忍跨行）"""
    raw = open(path, encoding='utf-8-sig').read()
    raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.S)
    out = []
    buf = ''
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith('//'):
            continue
        s = re.sub(r'\s*//.*$', '', s)       # 行尾注释
        if not s:
            continue
        # 上一句字符串尚未闭合，却遇到新命令 ⇒ 上一句是源侧截断（引擎无法解析、不上屏）
        if buf and CMD_RE.match(s):
            if qcount(buf) % 2:
                DROPPED.append(buf[:64])        # 字符串未闭合 ⇒ 不可解析、不上屏
            else:
                out.append(buf)                 # 仅缺 `)`，正文完整 ⇒ 收
            buf = ''
        buf = (buf + ' ' + s) if buf else s
        if buf.count('(') <= buf.count(')') and qcount(buf) % 2 == 0:
            out.append(buf)
            buf = ''
    if buf:
        if qcount(buf) % 2:
            DROPPED.append(buf[:64])       # 文件末尾仍未闭合
        else:
            out.append(buf)
    return out


# ---------------------------------------------------------------- CSV
def read_csv(path):
    return list(csv.reader(io.StringIO(open(path, encoding='utf-8-sig', newline='').read())))


def load_choices(setting):
    """key → [选项1, 选项2, ...]（问句已由脚本内 SET_TALK 覆盖，不收）"""
    out = collections.OrderedDict()
    cur = None
    for r in read_csv(os.path.join(setting, 'CHOICE.csv'))[1:]:
        if not r:
            continue
        if r[0]:
            cur = r[0]
            out[cur] = [r[3]] if len(r) > 3 else []
        elif cur and len(r) > 3 and r[3]:
            out[cur].append(r[3])
    return out


def load_titles(setting):
    """EV 文件 → 扉文"""
    out = {}
    for r in read_csv(os.path.join(setting, 'EV_TITLE.csv')):
        if len(r) > 4 and r[3]:
            out[r[3]] = r[4]
    return out


def load_order(setting, have):
    """STORYFLOW.csv 的文件名列 = 剧本流顺序（跳过不存在的 CHAP*）"""
    order = []
    for r in read_csv(os.path.join(setting, 'STORYFLOW.csv'))[1:]:
        if len(r) > 2 and r[2] and r[2] in have and r[2] not in order:
            order.append(r[2])
    rest = sorted(n for n in have if n not in order)
    return order + rest


def load_dict(setting, name):
    """用語辞典 → 【見出し語】解説文"""
    rows = []
    for r in read_csv(os.path.join(setting, 'DICT.csv')):
        if len(r) < 3 or not r[1]:
            continue
        head = r[1].strip().replace('+', '') if STRIP_PLUS else r[1].strip()
        desc = r[2].replace('\r\n', '').replace('\n', '')
        desc = transform(desc, name, STRIP_PLUS)
        rows.append('【%s】%s' % (head, desc))
    return rows


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--romfs', default='_work_ccn/romfs')
    ap.add_argument('--outdir', default='提取结果')
    ap.add_argument('--name', default=DEFAULT_NAME)
    ap.add_argument('--out', default=None)
    ap.add_argument('--no-title', action='store_true', help='不收 扉文')
    ap.add_argument('--with-reword', action='store_true', help='收 @REWORD（改名差分）')
    ap.add_argument('--strip-plus', action='store_true', help='去正文中的姓名区切 `+`（名札专用符）')
    a = ap.parse_args()
    global STRIP_PLUS
    STRIP_PLUS = a.strip_plus

    sa = os.path.join(a.romfs, 'Data', 'StreamingAssets')
    script_dir = os.path.join(sa, 'Script')
    setting = os.path.join(sa, 'Setting')
    files = sorted(os.path.splitext(f)[0] for f in os.listdir(script_dir) if f.endswith('.h'))

    choices = load_choices(setting)
    titles = load_titles(setting)
    order = load_order(setting, set(files))

    lines = []
    stat = collections.Counter()
    missing = []
    for ev in order:
        if INCLUDE_TITLE and not a.no_title and ev in titles:
            t = transform(titles[ev], a.name, STRIP_PLUS)
            if t:
                lines.append(t)
                stat['扉文'] += 1
        for stmt in load_lines(os.path.join(script_dir, ev + '.h')):
            m = TALK_RE.match(stmt)
            if m:
                if m.group(2) == 'REWORD' and not a.with_reword:
                    stat['@REWORD(跳过)'] += 1
                    continue
                args = split_args(stmt[stmt.find('(') + 1:stmt.rfind(')')])
                if len(args) < 5:
                    stat['SET_TALK(异常行)'] += 1
                    continue
                txt = transform(unquote(args[4]), a.name, STRIP_PLUS)
                if txt:
                    lines.append(txt)
                    stat['SET_TALK/@REWORD'] += 1
                else:
                    stat['空文本'] += 1
                continue
            if CHOICE_RE.match(stmt):
                args = split_args(stmt[stmt.find('(') + 1:stmt.rfind(')')])
                key = unquote(args[0])
                n = len([x for x in args[1:] if x.strip() and x.strip() != 'NULL'])
                opts = choices.get(key)
                if opts is None:
                    missing.append(key)
                    continue
                if len(opts) != n:
                    missing.append('%s(opt %d vs jump %d)' % (key, len(opts), n))
                for o in opts[:n if n else len(opts)]:
                    txt = transform(o, a.name, STRIP_PLUS)
                    if txt:
                        lines.append(txt)
                        stat['选项'] += 1
                continue

    dict_lines = load_dict(setting, a.name)
    stat['用語辞典'] = len(dict_lines)

    out = a.out or os.path.join(a.outdir, 'CRAZY CHA!N -エルピスの鎖-_全文本.txt')
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with open(out, 'wb') as fh:
        body = '\n'.join(lines) + ('\n' if lines else '')
        if dict_lines:
            body += '\n'.join(dict_lines) + '\n'
        fh.write(b'\xef\xbb\xbf' + body.encode('utf-8'))

    print('输出:', out)
    print('总行数:', len(lines) + len(dict_lines))
    for k, v in stat.items():
        print('  %-18s %d' % (k, v))
    if missing:
        print('!! 选项 key 异常:', missing[:20])
    if DROPPED:
        print('!! 截断丢弃 %d 条（引号未闭合）:' % len(DROPPED), DROPPED[:3])


if __name__ == '__main__':
    main()
