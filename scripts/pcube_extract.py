# -*- coding: utf-8 -*-
"""ピリオドキューブ ～鳥籠のアマデウス～ (PSV, PCSG00853) 剧本文本提取

容器链路
  NoNpDrm pkg (+work.bin) -> pkg2zip -x -> psvpfsparser -z <zRIF> -f cma.henkaku.xyz
  -> data/STORY.cpk [CRI CPK] -> story/scenario/*/*.DAT (77) + story/init/*.DAT (4)
  -> data/SYSTEM.cpk -> system/database/dbListWord.gbin = 用語辞典 (93 条)

STCM2L 结构
  0x00 'STCM2L <date>'  0x20 export_addr  'CODE_START_'+12 = 指令流起点
  指令 = [u32 ic][u32 op][u32 np][u32 len] + np*[p0,p1,p2] + data
  字符串参数 p0 为局部指针 -> [0][L/4][1][L][utf8 text][pad]（c==1、b==L/4 签名）

  opcode 全库恒定（无逐文件 Δ），字符串 UTF-8：
    0x14A68 正文（通常ウィンドウ）    名札 0x149D0 + 0x14D84
    0x14A88 正文（全画面地文/心の声） 名札 0x149F0 + 0x14DFC
    0x14AA8 正文（小窓/モノローグ）   名札 0x14A10 + 0x14E1C
    0x9FA4  章題カード（第N章 ○○ルート）
    0x13028/0x12F44/0x12F64/0x12F84/0x13048/0x13068 選択肢（末パラメータ＝sure数字 ラベル）
    0x1F4   等待点击＝一次点击（builtin）
    0x14930/0x14970 清框/開框（必与相邻 0x1F4 同组，不单独产生点击）
    0x6     goto＝段（互斥双写：直写名版 / #Name 版）
"""
import struct
import re
import os
import sys
import glob

TEXT_OPS = {0x14A68, 0x14A88, 0x14AA8}
NAME_OPS = {0x149D0, 0x149F0, 0x14A10}
OPT_OPS = {0x13028, 0x12F44, 0x12F64, 0x12F84, 0x13048, 0x13068}
TITLE_OP = 0x9FA4
WAIT_OP = 0x1F4
GOTO_OP = 0x6

# 名字表（story/init/init.DAT 的 0x342C 名表：0=花宮 1=かずは 2=カズハ）
NAME_TBL = {1: '花宮', 2: 'かずは', 3: 'カズハ'}

RE_JP = re.compile(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]')
RE_NAME = re.compile(r'#Name\[(\d)\]')
RE_WORD = re.compile(r'#Word\[\d+\]')
RE_COLOR = re.compile(r'#Color\[\d+\]')
RE_SCALE = re.compile(r'#Scale\[[^\]]*\]')
RE_LBL = re.compile(r'^sure\d+$')


def load(path):
    d = open(path, 'rb').read()
    if not d.startswith(b'STCM2L'):
        return d, []
    exp = struct.unpack_from('<I', d, 0x20)[0]
    i = d.find(b'CODE_START_')
    if i < 0:
        return d, []
    p = i + 12
    ins = []
    while p < exp:
        if p + 16 > len(d):
            break
        ic, op, np_, ln = struct.unpack_from('<4I', d, p)
        if ln < 16 or ln % 4 or p + ln > len(d) or np_ > 0x100:
            break
        ins.append((p, ic, op, np_, ln))
        p += ln
    return d, ins


def rec(d, p, k, ln):
    q = struct.unpack_from('<I', d, p + 16 + 12 * k)[0]
    if not (p < q < p + ln) or q + 16 > len(d):
        return None
    a, b, c, L = struct.unpack_from('<4I', d, q)
    if a != 0 or c != 1 or b != L // 4 or L <= 0 or L % 4 or L > 0x8000 or q + 16 + L > len(d):
        return None
    raw = d[q + 16:q + 16 + L]
    if not raw.endswith(b'\x00'):
        return None
    try:
        return raw.rstrip(b'\x00').decode('utf-8')
    except Exception:
        return None


def clean(s):
    s = RE_WORD.sub('', s)
    s = RE_COLOR.sub('', s)
    s = RE_SCALE.sub('', s)
    s = RE_NAME.sub(lambda m: NAME_TBL.get(int(m.group(1)), m.group(0)), s)
    return s


def extract(path, folder='', seen_title=None):
    """-> [(kind, text)]  kind: 'T' 正文/章題, 'O' 选项"""
    d, ins = load(path)
    if seen_title is None:
        seen_title = set()
    out = []
    segs = []      # 同一点击内的互斥段
    cur = []

    def end_seg():
        if cur:
            t = clean(''.join(cur))
            if t.strip():
                segs.append(t)
            del cur[:]

    def end_click():
        end_seg()
        if segs:
            best = max(segs, key=lambda s: (len(s),))
            out.append(('T', best))
            del segs[:]

    for i, (p, ic, op, np_, ln) in enumerate(ins):
        if op in TEXT_OPS:
            s = rec(d, p, 0, ln)
            if s:
                cur.append(s)
        elif op == GOTO_OP:
            end_seg()
        elif op == WAIT_OP:
            end_click()
        elif op in OPT_OPS:
            end_click()
            best = None
            for k in range(np_):
                s = rec(d, p, k, ln)
                if s and RE_JP.search(s) and not RE_LBL.match(s):
                    if best is None or len(s) > len(best):
                        best = s
            if best:
                out.append(('O', clean(best).strip()))
        elif op == TITLE_OP:
            # 章題カードは 0x9FA4 直後が 0x9FF0（描画）＝真のカード。
            # 表内の分派用（前が Mif / 次が goto）は原則拾わないが、アストラム ルートだけは
            # この表形式でしか章題を持たない（全編 0x9FF0 は 1 個）ので、先頭ファイルで 1 度だけ採る。
            nxt = ins[i + 1][2] if i + 1 < len(ins) else None
            if nxt != 0x9FF0:
                if not (folder == '04_asu' and os.path.basename(path) == 'ch02_04_01.DAT'):
                    continue
            s = rec(d, p, 0, ln)
            if s and s.strip():
                t = clean(s).strip()
                if t not in seen_title:
                    seen_title.add(t)
                    end_click()
                    out.append(('T', t))
    end_click()
    return out


def glossary(path):
    """dbListWord.gbin：池 = [見出し][よみ][解説#n] × N（0x5E0 起，遇 GBNL 止）"""
    d = open(path, 'rb').read()
    p = 0x5E0
    strs = []
    while p < len(d):
        e = d.find(b'\x00', p)
        if e < 0:
            break
        s = d[p:e]
        if s == b'GBNL' or s.startswith(b'GBNL'):
            break
        try:
            strs.append(s.decode('utf-8'))
        except Exception:
            break
        p = e + 1
    out = []
    for i in range(0, len(strs) - 2, 3):
        head, yomi, desc = strs[i], strs[i + 1], strs[i + 2]
        if not head or not desc:
            continue
        desc = desc.replace('#n', '')
        out.append('【%s】%s' % (head, desc))
    return out


def script_order(gbin_script):
    """dbListScript.gbin 的 /scenario/... 串 = 游戏内脚本顺序表（prologue → 各ルート → おまけ）"""
    d = open(gbin_script, 'rb').read()
    seq = [m.group().decode('utf-8') for m in re.finditer(rb'/[\x20-\x7e]{4,}', d)]
    return [x.lstrip('/').replace('/', os.sep) for x in seq if x.startswith('/scenario/')]


def main():
    src = sys.argv[1]
    out = sys.argv[2]
    gbin = sys.argv[3] if len(sys.argv) > 3 else None
    allf = {os.path.relpath(f, src): f for f in glob.glob(os.path.join(src, 'scenario', '*', '*.DAT'))}
    files = []
    if gbin:
        for rel in script_order(os.path.join(os.path.dirname(gbin), 'dbListScript.gbin')):
            if rel in allf:
                files.append(allf.pop(rel))
    files += [allf[k] for k in sorted(allf)]
    lines = []
    nopt = 0
    seen_title = set()
    for f in files:
        folder = os.path.basename(os.path.dirname(f))
        for kind, s in extract(f, folder, seen_title):
            if kind == 'O':
                nopt += 1
            lines.append(s)
    gl = glossary(gbin) if gbin else []
    lines += gl
    print('files=%d lines=%d opt=%d glossary=%d' % (len(files), len(lines), nopt, len(gl)))
    with open(out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('->', out)


if __name__ == '__main__':
    main()
