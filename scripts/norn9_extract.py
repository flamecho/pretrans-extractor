# -*- coding: utf-8 -*-
"""Norn9 ～Norn + Nonette～ Act Tune  (PSV, PCSG00833) 剧本文本提取

容器链路
  NoNpDrm(加密) -> psvpfsparser(-z zRIF) -> data/STORY.cpk  [CRI CPK]
  CPK 内 SCRIPT/*.DAT (88) = 剧本; SCRIPT/init/*.DAT (7) = 系统初始化(无正文)
  脚本格式 = STCM2L (Idea Factory)

STCM2L 结构
  0x00  'STCM2L <date>'  0x20 export_addr  0x24 export_len  0x2c collection_addr
  0x50  'GLOBAL_DATA\\0'  0x5c.. globals   CODE_START_(+12) → 指令流
  指令 = [u32 is_call][u32 opcode][u32 nparams][u32 length] + nparams*[p0,p1,p2]
         + data (局部指针 p0 指向本指令内的数据区)
  字符串参数 = p0 为局部指针 → 目标处 [0][L/4][1][L][utf8 text][pad]
  每个文件一个常量偏移 delta (= text_op - 0xcf9c, 见下)，全部 opcode 同步平移。
  归一化后：
     0xcf9c push 文本 (对白/旁白)
     0xd698 push 人名 (丢弃)
     0xe090 选项 (p0=选项文本, p1=目标标签)
     0x236c 章节标签 / 0x5414,0x4b24,0x4cfc,0x4ed4 等 = flag (不显示)
  文本变量：#Name[1]=こはる / #Name[2]=深琴 / #Name[3]=七海 (三名女主，可改名)
            #Scale[..] = 演出缩放，丢弃

输出：一次点击=一行；不加说话人前缀；保留日文；UTF-8-BOM / LF。
"""
import struct
import re
import os
import sys
import glob

GOTO_OP = 0x000006        # goto（builtin，不随 delta 平移）
WAIT_OP = 0x01F4          # 换框/等待点击（builtin，不随 delta 平移）

TEXT_OP = 0xCF9C          # push text
NAME_OP = 0xD698          # push speaker name
OPT_OP = 0xE090           # choice option
REF = TEXT_OP             # delta reference

HEROINE = {1: 'こはる', 2: '深琴', 3: '七海'}

RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_NAME_PH = re.compile(r'#Name\[(\d)\]')
RE_SCALE = re.compile(r'#Scale\[[^\]]*\]')


def parse(d):
    """返回 [(offset, is_call, opcode, nparams, length)]"""
    out = []
    export_addr = struct.unpack_from('<I', d, 0x20)[0]
    if d.find(b'CODE_START_') < 0:
        return out
    p = d.find(b'CODE_START_') + 12
    while p < export_addr:
        if p + 16 > len(d):
            break
        ic, op, np, ln = struct.unpack_from('<4I', d, p)
        if ln < 16 or ln % 4 or p + ln > len(d) or np > 0x100:
            break
        out.append((p, ic, op, np, ln))
        p += ln
    return out


def str_at(d, p, np, ln, k=0):
    """第 k 个参数的字符串值（p0 为局部指针且目标为 [0][L/4][1][L][text]）"""
    if k >= np:
        return None
    q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
    if not (p < q < p + ln) or q + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, q)
    if c != 1 or b != L // 4 or not (0 < L <= 0x2000) or q + 16 + L > len(d):
        return None
    try:
        return d[q + 16:q + 16 + L].rstrip(b'\x00').decode('utf-8')
    except Exception:
        return None


def detect_delta(d, ins):
    """text_op = 含日文串且平均长度最大(去噪)的 opcode；delta = text_op - 0xcf9c"""
    sets = {}
    for (p, ic, op, np, ln) in ins:
        for k in range(np):
            s = str_at(d, p, np, ln, k)
            if s and RE_JP.search(s) and not any(ord(c) < 0x20 for c in s):
                sets.setdefault(op, set()).add(s)
    best = None
    for op, ss in sets.items():
        if len(ss) >= 4:
            av = sum(len(x) for x in ss) / len(ss)
            if best is None or av > best[0]:
                best = (av, op)
    if best is None:
        return 0
    return best[1] - REF


def clean(s):
    s = RE_SCALE.sub('', s)
    s = RE_NAME_PH.sub(lambda m: HEROINE.get(int(m.group(1)), m.group(0)), s)
    return s


# ---------------------------------------------------------------------------
# 原作笔误修正（显式整行定值表；已用原始字节核对，非提取缺陷）
# ---------------------------------------------------------------------------
# ① 开引号「但原文漏写闭合 」（7 处）：原文件该消息末尾直接跟 0x00，无 」字节
POSTFIX_RQ = {
    '「じゃあ、お嬢さんの苦労を\u3000労うために、後でマッサージしてあげるよ',
    '「駆くん、千里くん。\u3000わたしは大丈夫ですから、\u3000みなさん仲良くしましょう！',
    '「いいえ、一緒に行きます。\u3000お手伝いしたいと言ったのは\u3000わたしですから',
    '「お前は……\u3000子供相手に何をしてるんだ',
    '「ほんと、キミって時々面白いよね',
    '「ああ、それは、\u3000ええと、確か……',
    '「唯一ここを突破出来た詰所の兵士は、\u3000頭が良いとも言っていました。こちらの動きを'
    '\u3000読み、連携することを知っているそうです',
}
# ② 全角「（」开头、却用半角「)」收尾（2 处，原文即如此）→ 统一为「）」
FULLWIDTH_PAREN = {
    '（そんな千里くんは、もう充分\u3000成長しています。みなさんも、'
    '\u3000それを認めてくださってるのに……)',
    '（「もっと後」……つまり私は)',
}


def apply_fixes(s):
    if s in POSTFIX_RQ:
        s = s + '」'
    if s in FULLWIDTH_PAREN:
        s = s[:-1] + '）'
    return s


def _best_segment(segs):
    """同一「点击」内由 goto 分隔的多个分支文本中选一个显示版。

    这些分支互斥（同一行按条件写成多个版本：名字占位符版 / 直写名版），
    实际只显示其一。优先：不含 #Name[ 占位符者；再取最长者。
    """
    if len(segs) == 1:
        return segs[0]
    def key(s):
        return (0 if RE_NAME_PH.search(s) else 1, len(s))
    return max(segs, key=key)


def extract_file(path):
    """返回 [line, ...]；line 为 str(正文) 或 ('OPT', text)"""
    d = open(path, 'rb').read()
    ins = parse(d)
    if not ins:
        return []
    delta = detect_delta(d, ins)
    text_op, name_op, opt_op = TEXT_OP + delta, NAME_OP + delta, OPT_OP + delta
    lines = []
    segs = []            # 当前点击内的分支段
    cur = []
    def end_seg():
        if cur:
            t = ''.join(cur)
            if t.strip():
                segs.append(t)
            del cur[:]
    def end_click():
        end_seg()
        if segs:
            lines.append(_best_segment(segs))
            del segs[:]
    n = len(ins)
    for i, (p, ic, op, np, ln) in enumerate(ins):
        if op == text_op:
            s = str_at(d, p, np, ln)
            if s is not None and s.strip():
                cur.append(s)
        elif op == opt_op:
            end_click()
            s = str_at(d, p, np, ln)
            if s is not None and s.strip():
                lines.append(('OPT', s))
        elif op == GOTO_OP:
            end_seg()
        elif op == WAIT_OP:
            # 换框。若紧跟 goto（跳过后面的文字）= 互斥分支的另一版：只断段、不断点击
            nxt = ins[i + 1][2] if i + 1 < n else None
            if nxt == GOTO_OP:
                end_seg()
            else:
                end_click()
    end_click()
    return lines


def wanted(f):
    n = os.path.basename(f).upper()
    return n.endswith('.DAT') and os.path.basename(os.path.dirname(f)).lower() != 'init'


def _norm_line(ln):
    if isinstance(ln, tuple):
        return ('OPT', apply_fixes(clean(ln[1]).strip(' \u3000\t')))
    return apply_fixes(clean(ln).strip(' \u3000\t'))


def find_common_head(per, min_files=8):
    """找出被多数文件重复作为开头的「共通导入块」（长度>=2 取最长）。
    返回 (block_lines_list, notice_line)"""
    import collections
    for L in range(10, 1, -1):
        cnt = collections.Counter(tuple(ls[:L]) for ls in per if len(ls) >= L)
        if not cnt:
            continue
        blk, c = cnt.most_common(1)[0]
        if c >= min_files:
            return list(blk), blk[0]
    return [], None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     '..', '_work_norn9', 'story', 'SCRIPT')
    out = sys.argv[2] if len(sys.argv) > 2 else None
    files = [f for f in sorted(glob.glob(os.path.join(src, '*.DAT'))) if wanted(f)]
    per = []
    for f in files:
        ls = [_norm_line(x) for x in extract_file(f)]
        per.append([x for x in ls if (x[1] if isinstance(x, tuple) else x)])
    head, notice = find_common_head(per)
    hset = set(head)
    if notice:
        hset.add(notice)
    # 去掉每个文件开头属于共通块的若干行（保留一次在全文最前）
    for i in range(len(per)):
        while per[i] and (per[i][0] if isinstance(per[i][0], str) else None) in hset:
            per[i].pop(0)
    all_lines = list(head)
    for ls in per:
        for x in ls:
            all_lines.append(x[1] if isinstance(x, tuple) else x)
    print('files=%d lines=%d head_block=%d' % (len(files), len(all_lines), len(head)))
    for h in head:
        print('   head:', h[:50])
    if out:
        with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
            fh.write('\n'.join(all_lines) + '\n')
        print('->', out)


if __name__ == '__main__':
    main()
