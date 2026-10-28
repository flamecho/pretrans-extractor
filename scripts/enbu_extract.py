#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""戦場の円舞曲 for Nintendo Switch —— 全文本提取器

引擎：Idea Factory **STCM2L**（magic `STCM2L May 30 2012 14:17:58`，CP932，Switch 版）
链路：NSP → PFS0 → Program NCA（titlekey crypto, keygen 15）→ RomFS
      → CONTENTS/GAME.cpk（CRI CPK）→ script/NNNN（720 本）

记录格式（本作实证；与「ニル・アドミラリ」同族，但终止符顺序不同）：
  [KIND][k][size][p...][0x40000000][0x40000000] ... [0][L/4][1][L][cp932 text][pad]
  * 文本节点以「L 字段前 3 格 = (0, L/4, 1)」+ 首 2 组指针为 0x40000000 签名扫描
  * **框终止符** = `[0][0x4BB][0][0x10]`（16B，紧跟正文节点之后）
  * **同框软换行** = 相邻正文节点字节间隙恰为 4（只有一个 0 字），句意跨节点连续
    （实证：`…部屋に戻って`｜`くると、ユリアナが明るく笑った。`）⇒ 合并成一行（L1）
  * KIND：0x4BA 正文 / 0x4BC 名札（丢） / 0x4C0 章一覧（每本重复 35 条＝章节跳转表，剔）
          选项 = `select` 命令前紧邻的 k=3 记录串（0x4CF 与 0x1Dxxx 两种首字段）

成行：**一次点击＝一个框＝一行**；选项一行一条，插在其所属框之后（文件内字节序）。

版式＝**单版**：gap=4 的同框多段是**框内换行（排版换行，非语义断行）**，
按「一次点击＝一行」直接删换行拼接，不拆段、不另出 `A,B,C,ABC`。
"""
import os
import re
import sys
import glob
import struct

TERM = bytes.fromhex('00000000bb0400000000000010000000')   # [0][0x4BB][0][0x10]
BODY, NAME, CHAP = 0x4BA, 0x4BC, 0x4C0
HERO = 'ラン'          # 主角（vndb v14917，Nameable，默认 ラン；ユリアナ 是室友配角）

RE_NAME = re.compile(r'#Name\[(\d+)\]')
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')

# 每本开头共通块：系统提示（SHOP／魔石／ルート開放）——系统通知，剔
TOAST = re.compile(r'^(SHOPが開放されました。|Ancient Memoriesが開放されました。|'
                   r'魔石を[０-９]+個手に入れました。|.*のルートが開放されました。|'
                   r'Ancient Memoriesに(大きな)?変化が起きたようです。)$')
# 调试 / 开发用串（脚本尾部成块的 デバッグ遷移 一览、NV 探索选单）
DEBUG = re.compile(r'デバッグ|【NV探索】|処理開始|^ＣＥＲＯ|＠おまけ|ルートへ$')
# 选项过滤：调试菜单里的角色名／章节跳转表整组丢弃
OPT_DBG = re.compile(r'デバッグ|遷移|ＣＥＲＯ|ルートへ$|【|＠|^共通$|^他$|サブキャラ選択$')


def scan(d):
    """→ [(off, KIND, k, end, text)]，按字节序。"""
    n = len(d)
    out = []
    i = 0
    while i + 40 <= n:
        k = struct.unpack_from('<I', d, i + 4)[0]
        if 1 <= k <= 8:
            iL = i + 24 + 12 * k
            if iL + 4 <= n:
                L = struct.unpack_from('<I', d, iL)[0]
                if (4 <= L <= 0x20000 and L % 4 == 0 and iL + 4 + L <= n
                        and struct.unpack_from('<I', d, iL - 12)[0] == 0
                        and struct.unpack_from('<I', d, iL - 8)[0] == L // 4
                        and struct.unpack_from('<I', d, iL - 4)[0] == 1
                        and struct.unpack_from('<I', d, i + 16)[0] == 0x40000000
                        and struct.unpack_from('<I', d, i + 20)[0] == 0x40000000):
                    txt = d[iL + 4:iL + 4 + L].rstrip(b'\x00').decode('cp932', 'replace')
                    out.append((i, struct.unpack_from('<I', d, i)[0], k, iL + 4 + L, txt))
                    i = iL + 4 + L
                    continue
        i += 1
    return out


RE_CTRL = re.compile(r'[\x00-\x1f\x7f]')


def clean(t):
    t = RE_CTRL.sub('', t)                    # 文中夹杂的格式控制字（实证脚本 875 有一处 \t）
    t = RE_NAME.sub(HERO, t)
    return t.strip()


def extract(path):
    """→ [('B', [段…]) | ('O', [选项…]), ...]（正文与选项混排，按文件内字节序）"""
    d = open(path, 'rb').read()
    nodes = scan(d)
    lines, box = [], []
    skip_opts = False                                     # 调试菜单：其选项一并丢
    for idx, (off, kind, k, end, txt) in enumerate(nodes):
        if kind == BODY:
            if DEBUG.search(txt):
                skip_opts = True
            else:
                skip_opts = False
            box.append(txt)
            if d[end:end + 16] == TERM:                  # 终止符 ⇒ 本框结束
                lines.append(('B', box)); box = []
            else:                                         # 无终止符：看下一节点是否同框续写
                nxt = nodes[idx + 1] if idx + 1 < len(nodes) else None
                if not (nxt and nxt[1] == BODY and nxt[0] - end == 4):
                    lines.append(('B', box)); box = []
            continue
        if box:
            lines.append(('B', box)); box = []
        if txt == 'select':
            grp, j = [], idx - 1
            while j >= 0:
                o2, k2, kk, e2, t2 = nodes[j]
                if k2 in (BODY, NAME) or off - o2 > 4096:
                    break
                if kk == 3:
                    grp.append(t2)
                j -= 1
            grp.reverse()
            if (grp and not skip_opts
                    and all(JP.search(t) and not OPT_DBG.search(t) for t in grp)):
                lines.append(('O', grp))
    if box:
        lines.append(('B', box))
    return lines


def render(items):
    """一次点击＝一行：框内各段按字节序拼接（框内换行为排版换行）。"""
    out = []
    for kind, payload in items:
        if kind == 'O':
            out.extend(t for t in map(clean, payload) if t and not DEBUG.search(t))
            continue
        segs = [s for s in map(clean, payload) if s]
        if not segs or any(DEBUG.search(s) for s in segs):
            continue                                      # 调试块整框丢，不留残段
        out.append(''.join(segs))
    while out and TOAST.match(out[0]):                    # 开头系统提示块
        out.pop(0)
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else '_work_enbu/script/script'
    out = sys.argv[2] if len(sys.argv) > 2 else '提取结果/[NS-JP]戦場の円舞曲 for Nintendo Switch.txt'
    files = sorted(glob.glob(os.path.join(src, '*')), key=lambda p: int(os.path.basename(p)))
    out_lines = []
    for p in files:
        out_lines.extend(render(extract(p)))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out_lines) + '\n')
    print('[+] %s : %d 行' % (out, len(out_lines)))


if __name__ == '__main__':
    main()
