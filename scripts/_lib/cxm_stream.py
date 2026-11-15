# -*- coding: utf-8 -*-
"""Collar x Malice (NS-JP) STCM2L `May 18 2015` 记录流（纯结构，零猜测）

记录框架：`[pre][TAG][N][size][payload...]`，**步进 = size（含 16 字节头）**

  pre = 0                     ⇒ 命令记录，TAG 即命令码
        0x1F4 / size 16       ⇒ 等待点击（段落末）
        0x3 / 0x6 / 0x0 …     ⇒ 分支、跳转、nop
  pre = 1, size = 16, 无文本  ⇒ 行尾空记录（tag 逐文件变，如 story2 = 0x478C0）
  pre = 1, 有文本            ⇒ 文本记录
        U(i+28)==0, U(i+36)==1, L=U(i+40), text 从 i+44 起，L = align4(len+1)

★ 断行判据（L0，见 S4-stcm2l-cases.md「一行 ＝ 一段连续 BODY 记录」）：
    **两条正文记录之间夹了任何非正文记录 ⇒ 新行**；
    **只有紧邻的两条正文记录才合并**（同一显示行被引擎拆成前后半段）。
  不用 0x1F4 切行（本作里它是段落级/页面级，稀疏且分布不均）；
  不用字数、行宽、框容量、括号配平 —— 那些都是渲染层猜测（SKILL.md 五条禁令）。
"""
import struct

U = lambda d, o: struct.unpack_from('<I', d, o)[0]

OP_WAIT = 0x1F4


def records(d):
    """返回 [(i, pre, tag, size, text|None)]，按文件偏移"""
    N = len(d)
    out = []
    i = 0x40
    while i + 16 <= N:
        pre, tag, n, size = U(d, i), U(d, i + 4), U(d, i + 8), U(d, i + 12)
        if size < 16 or i + size > N:
            i += 4
            continue
        txt = None
        if pre == 1 and U(d, i + 28) == 0 and U(d, i + 36) == 1:
            L = U(d, i + 40)
            if 4 <= L <= 16384 and not L & 3 and i + 44 + L <= N:
                raw = d[i + 44:i + 44 + L].rstrip(b'\x00')
                if raw and len(raw) <= L - 1:
                    try:
                        txt = raw.decode('utf-8')
                    except UnicodeDecodeError:
                        txt = None
                    if txt is not None and any(ord(c) < 0x20 for c in txt):
                        txt = None
        out.append((i, pre, tag, size, txt))
        i += size
    return out


def body_tags(rec):
    """正文 TAG 集 ＝ 由**两个结构量**选出（不看任何单条内容；一文件可有多个正文 TAG）：

    ① **相邻对数 ≥ 2**：同一显示行被引擎拆成前后半段时，两条记录**紧邻且同 TAG**。
       实测：正文 `0x4778C` 相邻 486 对 / `0xDAB0` 89 对 / `0x4359C` 26 对；
       系统通知（`MATERIALS` 登録、`が攻略可能になりました`）与名札、`sure` flag **全为 0 对**
       —— 它们每条独立成条，从不与同类相邻 ⇒ 自动落选。
    ② 前置过滤 **单字符流类型**：某些 TAG 的记录 `L` 恒为 4（`size=48`，只承载 1 个字符），
       是引擎字符集/字形调试页（`' '`、`'!'`、`'('`…）。`L=1` 比例 >0.9 ⇒ 属另一种记录类型，
       不可能是「行文本」，先排除。

    返回排序后的 TAG 列表；空列表 ⇒ 该文件没有正文（只有通知/资料/选项表）。
    """
    Ls = {}
    adj = {}
    prev = None
    for i, pre, tag, size, txt in rec:
        if txt is None:
            prev = None
            continue
        Ls.setdefault(tag, []).append(len(txt))
        if prev is not None and prev == tag:
            adj[tag] = adj.get(tag, 0) + 1
        prev = tag
    single = {t for t, v in Ls.items() if v and sum(1 for n in v if n == 1) / len(v) > 0.9}
    return sorted(t for t in Ls if t not in single and adj.get(t, 0) >= 2)
