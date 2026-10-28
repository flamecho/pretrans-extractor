#!/usr/bin/env python3
"""tennis_extract.py -- [PS2-JP] テニスの王子様 RUSH & DREAM! 全文本提取.

链路:
  SCRIPT.HD/BIN  ->  .s 条目
  .s = 8 字节循环键 XOR(锚定: 明文 "PACK"+u32 0)  ->  PACK 容器(1 条目)
  PACK 条目 flags=2  ->  tkl type-2 解压  ->  SCPT 脚本
  SCPT: "SCPT"|0|u32 codeStart(0x20)|u32 codeLen|... |u32 B=表B偏移
        表B: [u32 count][u32 blockLen][count×8B]  (块尾 +1 即消息区起点)
        消息区: NUL 分隔的 cp932 串, 形如 "　<名前>,本文" (换行 = 0x0A)
  选项: 名字段为空 => 「,『选项1』\\n『选项2』」一行一项

行规则: 一次点击 = 一行；名札(逗号前)丢弃；同串内 0x0A 软换行合并。
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tennis_scan import load_scriptbin, get_scpt

OUT = '提取结果/[PS2-JP]テニスの王子様 RUSH & DREAM !.txt'

# 外字：0x8490/0x8491 (JIS 第7区 ю/я 槽) 在 329 处全部紧跟「選抜」= 全国選抜
GAIJI = {b'\x84\x90\x84\x91': '全国'}

MACRO = {
    'playername': '赤月 巴',
    'lastname': '赤月',
    'firstname': '巴',
    'nickname': '巴',
}

SKIP_FILES = {'anime_test.s', 'transition.s'}          # 开发样例脚本
PLACEHOLDER = re.compile(r'^「選択肢[０-９0-9]+」')
DEBUG = re.compile(r'^(イベント開始|ＥＶ[０-９]{3}_[０-９]{2})')
DEBUG_EV = re.compile(r'^EV[0-9]{3,4}(?:_[0-9]{2})?[：:]')


def decode_msg(raw):
    for k, v in GAIJI.items():
        raw = raw.replace(k, v.encode('cp932'))
    return raw.decode('cp932')


def expand_macros(t):
    def rep(m):
        k = m.group(1)
        return MACRO.get(k, k)
    return re.sub(r'<([^<>\n]{1,12})>', rep, t)


def join_lines(body):
    parts = [p.strip('　 \t') for p in body.split('\n')]
    parts = [p for p in parts if p != '']
    return ''.join(parts)


def main():
    names, offs, sizes, f = load_scriptbin()
    targets = []
    for nm in names:
        if nm.endswith('.s') and nm not in SKIP_FILES:
            targets.append(nm)

    def sortkey(n):
        return n
    targets.sort(key=sortkey)

    lines = []
    stats = {'msg': 0, 'dlg': 0, 'opt': 0, 'skip': 0}
    for nm in targets:
        i = names.index(nm)
        f.seek(offs[i])
        d = f.read(sizes[i])
        try:
            inner, sc = get_scpt(d)
        except Exception:
            continue
        if len(sc) < 0x20 or sc[:4] != b'SCPT':
            continue
        h = struct.unpack_from('<8I', sc, 0)
        B = h[6]
        if B == 0 or B + 8 > len(sc):
            continue
        blen = struct.unpack_from('<I', sc, B + 4)[0]
        bs = B + blen + 1
        blob = sc[bs:]
        p = 0
        while p < len(blob):
            e = blob.find(b'\x00', p)
            if e < 0:
                e = len(blob)
            seg = blob[p:e]
            p = e + 1
            if not seg:
                continue
            try:
                t = decode_msg(seg)
            except Exception:
                stats['skip'] += 1
                continue
            stats['msg'] += 1
            head, sep, body = t.partition(',')
            if not sep:
                stats['skip'] += 1
                continue
            if DEBUG.match(t.split('\n')[0]):
                stats['skip'] += 1
                continue
            if head.strip('　 ') == '':
                # 选项组（空名字段）；非引号开头的行 = 调试/系统串，丢弃
                for ln in body.split('\n'):
                    ln = ln.strip('　 \t')
                    if not ln or PLACEHOLDER.match(ln):
                        continue
                    if ln[0] not in '『「' and DEBUG_EV.match(ln):
                        stats['skip'] += 1
                        continue
                    lines.append(expand_macros(ln))
                    stats['opt'] += 1
            else:
                ln = join_lines(body)
                if not ln:
                    stats['skip'] += 1
                    continue
                lines.append(expand_macros(ln))
                stats['dlg'] += 1

    os.makedirs('提取结果', exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as o:
        o.write('\n'.join(lines) + '\n')
    print('lines', len(lines), stats)


if __name__ == '__main__':
    main()
