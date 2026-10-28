#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DYNAMIC CHORD feat.[rêve parfait] Remaster edition (NS-JP, 010076902126e000)
全文本提取 —— HuneX / UNAS「HESL + 外置 HDLG 文本表」链路。

容器链（本作实测）：
  XCI(HEAD) → secure 分区 HFS0 → Program NCA(Standard crypto) → hactool --romfsdir
    romfs/Data/StreamingAssets/script/script_dialog_ja.hdlg   ← 正文（UTF-8）
    romfs/Data/StreamingAssets/script/script_dialog_en.hdlg   ← 键名表（未翻译，用作索引/分段）
    romfs/Data/StreamingAssets/script/script.heslnk           ← 504 个 HLZS 压缩 HESE（不含日文）

HDL G 表结构（L1 记录自定界）：
  HLZS(0x20 头) → LZSS(dict 0x1000 / maxlen 0x12) →
  HDGL + ver(0x10000) + count + dataOffset + u32 offsets[count]
  字符串内联、NUL 结尾；<br>＝框内软换行（合并）；<firstname>/<lastname>＝主角名宏。

索引（en 表键名）分区：
  0–9        TRANS_M*   菜单占位（正文即键名）
  10         '　'
  11–116     TRANS_N*   名札表（105 个角色名，独立名字窗 ⇒ 整表丢弃）
  117–588    TRANS_S*   系统/UI（改名确认、存读档、章題一覧、Countdown 特典名）
  589–769    TRANS_T*   バカンスストーリー（Remaster 新增：ドラマCD脚本小说化，10 篇）
  770–40372  TRANS_W*   本篇正文（501 个块，块内行号 1..n 连续无缺口）

引擎回声（本作实测 488 条）：一条文本框之后常跟一条「已出现在上一框里的副本」——
等于上一框全文，或等于上一框的某个 <br> 段。判定为同一文本的重复副本 ⇒ 丢弃，
否则成品会整段重复。

用法:
  python scripts/dyc_extract.py [--romfs DIR] [--out 输出.txt] [--name 理央]
"""
import argparse
import os
import re
import struct
import sys

# ---------------------------------------------------------------- LZSS (HLZS)
def hlzs_decompress(buf, dec_size):
    dic = bytearray(0x1000)
    out = bytearray()
    flag8 = 1
    ip = 0
    dp = 0
    n = len(buf)
    while ip < n and len(out) < dec_size:
        if flag8 == 1:
            flag8 = buf[ip] | 0x100
            ip += 1
        f = flag8 & 1
        flag8 >>= 1
        if f:
            c = buf[ip]
            ip += 1
            out.append(c)
            dic[dp] = c
            dp = (dp + 1) & 0xFFF
        else:
            low = buf[ip]
            high = buf[ip + 1]
            ip += 2
            wp = (((high & 0xF0) << 4) | low) + 0x12
            ws = (high & 0x0F) + 3
            for i in range(ws):
                c = dic[(wp + i) & 0xFFF]
                out.append(c)
                dic[dp] = c
                dp = (dp + 1) & 0xFFF
    return bytes(out)


# ---------------------------------------------------------------- HDLG
def load_hdlg(path):
    raw = open(path, 'rb').read()
    base = raw.find(b'HLZS')
    assert base >= 0, 'no HLZS in %s' % path
    _m, _v, _enc, dec = struct.unpack_from('<4I', raw, base)
    body = hlzs_decompress(raw[base + 0x20:], dec)
    magic, _ver, cnt, dof = struct.unpack_from('<4sIII', body, 0)
    assert magic in (b'HDGL', b'HDLG'), magic
    offs = [struct.unpack_from('<I', body, 0x10 + 4 * i)[0] for i in range(cnt)]
    out = []
    for o in offs:
        p = dof + o
        if p >= len(body):
            out.append(None)
            continue
        e = body.find(b'\x00', p)
        if e < 0:
            e = len(body)
        out.append(body[p:e].decode('utf-8', 'replace'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--romfs', default='_work_dy/romfs')
    ap.add_argument('--out', default='提取结果/[NS-JP]DYNAMIC CHORD feat.[reve parfait] Remaster edition.txt')
    ap.add_argument('--name', default='理央')
    ap.add_argument('--surname', default='跡野')
    a = ap.parse_args()

    sc = os.path.join(a.romfs, 'Data', 'StreamingAssets', 'script')
    ja = load_hdlg(os.path.join(sc, 'script_dialog_ja.hdlg'))
    en = load_hdlg(os.path.join(sc, 'script_dialog_en.hdlg'))
    assert len(ja) == len(en), (len(ja), len(en))

    W, T = [], []
    for i, k in enumerate(en):
        if not k:
            continue
        if k.startswith('TRANS_W'):
            W.append(ja[i])
        elif k.startswith('TRANS_T'):
            T.append(ja[i])

    macros = {'<firstname>': a.name, '<lastname>': a.surname}

    # 系统通知：通关后弹出的「ENCORE シナリオが追加されました」解锁提示（8 条），
    # 属系统/UI 提示（非正文），按 §0 剔除。
    SYS = re.compile(r'^[^\s]{1,8}　[^\s]{1,8}のENCOREシナリオが追加されました。$')

    def render(t):
        # <br> ＝ 框内软换行 ⇒ 合并（不插字符）。
        # 例外：扉文标题卡换行处两侧都是拉丁字母/数字（如「3 years」+「Reon ...」）时
        # 直接相连会粘成一个词 ⇒ 用全角空格代替该换行（本作仅 3 条，见报告 §成行）。
        segs = t.split('<br>')
        out = segs[0]
        for seg in segs[1:]:
            if re.search(r'[A-Za-z0-9]$', out) and re.match(r'[A-Za-z]', seg):
                out += '\u3000' + seg
            else:
                out += seg
        t = out
        for k, v in macros.items():
            t = t.replace(k, v)
        return t.strip('\n').rstrip()

    def dedupe(seq):
        kept, echo = [], []
        for t in seq:
            if t is None:
                continue
            if kept:
                lp = kept[-1]
                if t == lp or t in lp.split('<br>'):
                    echo.append(t)
                    continue
            kept.append(t)
        return kept, echo

    Wk, Wecho = dedupe(W)
    Tk, Techo = dedupe(T)

    lines = []
    skipped_sys = 0
    for t in Wk + Tk:
        s = render(t or '')
        if not s or s == '\u3000':
            continue
        if SYS.match(s):
            skipped_sys += 1
            continue
        lines.append(s)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')

    print('[i] HDLG 条目=%d（W=%d / T=%d）' % (len(ja), len(W), len(T)))
    print('[i] 回声副本丢弃：W=%d / T=%d ；系统通知剔除=%d' % (len(Wecho), len(Techo), skipped_sys))
    print('[+] %s  行数=%d' % (a.out, len(lines)))


if __name__ == '__main__':
    main()
