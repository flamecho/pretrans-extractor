# -*- coding: utf-8 -*-
"""
Lucian Bee's: Evil Violet (PSP, 2010, 5pb) —— 全文本提取
=======================================================
链路：ISO9660 → PSP_GAME/USRDIR/DATA0.AFS (CRI AFS, 16 成员)
      → 成员[7] = SCENE00.AFS (AFS, 127 成员) → 成员[16..74] = 剧情场景 (.ALS 变体)

.ALS 结构（本作实测）
  [0x00..0x1C 头] [0x20.. 代码区（16 位 opcode 流，字符串内联）] [文本池]
  文本池起点 = 代码区最后一次 `0D 02` 之后；每条文本为 NUL 结尾 cp932 串，
  池尾以 `90 90 XX` 三字节标记 + 24B 收尾结束。

文本记录
  消息：`【名前】本文 %K %P`（%K 恒 1 次/串 ⇒ 一消息＝一文本框＝一次点击）
  选项：无 %K 的串，成组连续出现，按池内顺序即流程顺序
控制码
  %K 待键 | %P/%p 清框（台词） | %N 清框（地文）/行首=先清框 | %O032 清框变体
  %n 框内软换行（合并） | %IF0=名(アンナ) | %IL0=姓(ヒイラギ) | %L1/%T2=扉文模板
  ├┤(84A5 84A7) 非文本记号，147 处，删除（见报告〔未確定〕）
用法：
  python scripts/lucianv_extract.py <DATA0.AFS> <输出 txt>
"""
import struct
import re
import sys

SCENE_MEMBER = 7          # DATA0.AFS 内 SCENE00.AFS
SCENE_RANGE = range(16, 75)   # 剧情场景（0-15 系统/UI，75+ 空壳）
NAME = {'%IF0': 'アンナ', '%IL0': 'ヒイラギ'}
JP = re.compile('[\u3041-\u309f\u30a1-\u30fa\u4e00-\u9fff]')
NAME_HEAD = re.compile('^\u3010[^\u3011]{1,20}\u3011')


def afs_list(buf):
    assert buf[:4] == b'AFS\x00', buf[:4]
    c = struct.unpack('<I', buf[4:8])[0]
    return [struct.unpack('<II', buf[8 + i * 8:16 + i * 8]) for i in range(c)]


def parse_pool(b, st):
    """从 st 起按 NUL 结尾串读到池尾标记；返回 [(off, text)]
    判据：池内串为连续 cp932 文本；遇到池尾标记 `90 90 XX`、控制字符或解码失败即止。
    （不能用「含假名/汉字」筛，否则 `ＯＫ` 一类纯全角选项会截断整池）"""
    n = len(b)
    i = st
    out = []
    while i < n:
        if b[i] == 0:
            i += 1
            continue
        j = i
        while j < n and b[j] != 0:
            j += 1
        if j >= n:
            break
        if b[i:i + 2] == b'\x90\x90':      # 池尾标记 90 90 XX
            break
        try:
            t = b[i:j].decode('cp932')
        except UnicodeDecodeError:
            break
        if any(ord(c) < 0x20 or 0x7f <= ord(c) <= 0x9f for c in t):
            break
        out.append((i, t))
        i = j + 1
    # 池尾 24B 收尾区（1 字节标记 + 0 + 若干 0/小整数）会被读成单字串 ⇒ 只从末尾剥
    # （不可用固定位置阈值：末条正文可能就起始于末尾 40B 内）
    while out and len(out[-1][1]) <= 1:
        out.pop()
    return out


def clean(t):
    t = t.split('%K')[0]
    for k, v in NAME.items():               # 名字宏必须在删控制码之前替换
        t = t.replace(k, v)
    t = re.sub(r'%[A-Za-z][0-9A-Fa-f]{0,8}', '', t)   # 余下控制码全删
    t = t.replace('%n', '')
    t = t.replace('\n', '')
    t = t.strip('\u3000 ')
    m = NAME_HEAD.match(t)
    if m:                                   # 名札只在本串开头剥一次
        t = t[m.end():].lstrip('\u3000 ')
    return t


def main():
    src, outp = sys.argv[1], sys.argv[2]
    data = open(src, 'rb').read()
    top = afs_list(data)
    o, s = top[SCENE_MEMBER]
    scenes = afs_list(data[o:o + s])

    lines = []
    stat = {'msg': 0, 'opt': 0, 'token': 0}
    per_scene = []
    for idx in SCENE_RANGE:
        so, ss = scenes[idx]
        b = data[o + so:o + so + ss]
        k = b.find(b'%K')
        if k < 0:
            continue
        st = b.rfind(b'\r\x02', 0, k) + 2
        recs = parse_pool(b, st)
        nm = no = 0
        for off, t in recs:
            if '%K' in t:
                nm += 1
                v = clean(t)
                if v:
                    lines.append(v)
            else:
                if '%L1' in t or '%T2' in t or t.strip('%N') == '':
                    stat['token'] += 1
                    continue
                no += 1
                v = clean(t)
                if v:
                    lines.append(v)
        stat['msg'] += nm
        stat['opt'] += no
        per_scene.append((idx, nm, no))

    with open(outp, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines))
        f.write('\n')
    print('场景数', len(per_scene), '消息', stat['msg'], '选项', stat['opt'],
          '模板token', stat['token'], '合计行', len(lines))
    print('每场景', per_scene)


if __name__ == '__main__':
    main()
