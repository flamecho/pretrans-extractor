# -*- coding: utf-8 -*-
"""
Lucian Bee's: Justice Yellow (PSP, 2010, 5pb./HuneX) —— 全文本提取
================================================================
链路：ISO9660 → PSP_GAME/USRDIR/DATA0.AFS (CRI AFS, 16 成员)
      → 成员[7] = SCENE00.AFS (AFS, 113 成员) → 成员[16..62] = 剧情场景 (.ALS)

.ALS 结构（同 イビル ヴァイオレット）
  [0x00..0x1C 头] [0x20.. 代码区] [文本池]
  文本池起点 = 代码区最后一次 `0D 02` 之后（本作实为 `\r\x02`）；
  每条文本为 NUL 结尾 cp932 串，池尾 `90 90 XX` 标记 + 24B 收尾。

文本记录
  消息：`【名前】本文 %K %P`（%K 恒 1 次/串 ⇒ 一消息＝一文本框＝一次点击）
  选项：无 %K 的串，成组连续出现（本作每组 3 条），按池内顺序即流程顺序
控制码
  %K 待键 | %P/%p 清框 | %N 清框（地文） | %O032 清框变体
  %n 框内软换行（合并） | %IF0=名(アンナ) | %IL0=姓(ヒイラギ) | %L1/%T2=扉文模板
  ├┤(84A5 84A7) 罫線素片＝作者手绘装饰线，按原文保留（同前作口径）
用法：
  python scripts/lucianj_extract.py <DATA0.AFS> <输出 txt>
"""
import struct
import re
import sys

SCENE_MEMBER = 7              # DATA0.AFS 内 SCENE00.AFS
SCENE_RANGE = range(16, 63)   # 剧情场景：0-13 数据表/系统，14-15 名変/回想/プロローグ選択，63+ 空壳
NAME = {'%IF0': 'アンナ', '%IL0': 'ヒイラギ'}
NAME_HEAD = re.compile('^\u3010[^\u3011]{1,20}\u3011')


def afs_list(buf):
    assert buf[:4] == b'AFS\x00', buf[:4]
    c = struct.unpack('<I', buf[4:8])[0]
    return [struct.unpack('<II', buf[8 + i * 8:16 + i * 8]) for i in range(c)]


def parse_pool(b, st):
    """从 st 起按 NUL 结尾串读到池尾标记 `90 90`；返回 [(off, text)]。
    不能用「含假名/汉字」筛（全角选项会截断整池）；不能「遇单字即止」（池中夹数据表）。"""
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
        if b[i:i + 2] == b'\x90\x90':
            break
        try:
            t = b[i:j].decode('cp932')
        except UnicodeDecodeError:
            break
        if any(ord(c) < 0x20 or 0x7f <= ord(c) <= 0x9f for c in t):
            break
        out.append((i, t))
        i = j + 1
    # 池尾 24B 收尾区会被读成单字串 ⇒ 只从末尾剥 ≤1 字的尾项（不可用位置阈值）
    while out and len(out[-1][1]) <= 1:
        out.pop()
    return out


def clean(t):
    """一条串 → 一次点击一行。%K 逐处断行（本作 4 处串含两个 %K＝同框二次待键）。"""
    out = []
    for seg in t.split('%K'):
        for k, v in NAME.items():           # 名字宏必须在删控制码之前替换
            seg = seg.replace(k, v)
        seg = re.sub(r'%[A-Za-z][0-9A-Fa-f]{0,8}', '', seg)
        seg = seg.replace('%n', '').replace('\n', '').strip('\u3000 ')
        m = NAME_HEAD.match(seg)
        if m:                               # 名札只在本串开头剥一次
            seg = seg[m.end():].lstrip('\u3000 ')
        if seg:
            out.append(seg)
    return out


def main():
    src, outp = sys.argv[1], sys.argv[2]
    data = open(src, 'rb').read()
    top = afs_list(data)
    o, s = top[SCENE_MEMBER]
    scenes = afs_list(data[o:o + s])
    assert scenes[0] == (2048, 23356) or len(scenes) > 60, len(scenes)

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
                lines.extend(clean(t))
            else:
                if '%L1' in t or '%T2' in t or t.strip('%N') == '':
                    stat['token'] += 1
                    continue
                no += 1
                lines.extend(clean(t))
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
