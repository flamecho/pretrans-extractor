#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""スチームプリズン -Beyond the Steam- (NS) → 全文本

链路：NSP → NCA → romfs/Data/StreamingAssets/script/script_dialog_ja.hdlg
  容器：`HLZS`(0x20 头) → LZSS(dict 0x1000) → `HDGL` + ver + count + dataOffset + u32 offsets[count]
  字符串内联、NUL 结尾；`<br>`＝框内软换行（合并）
  索引：`script_dialog_en.hdlg` 是同序英文字幕表（用于对齐/核对，不取）
排除：0–143 ＝ 系统解锁提示（`〜が解放されました／〜で解放されます`），非正文。
"""
import os
import re
import sys

sys.path.insert(0, 'tools')
from dyc_extract import load_hdlg

ROMFS = '_w_W3_steam2/romfs'
OUT = '提取结果/[NS-JP]スチームプリズン -Beyond the Steam-.txt'
START = 144              # 144 起才是正文（0–143 是系统解锁提示）
TAG = re.compile(r'<[^<>]{1,20}>')


def clean(s):
    s = re.sub(r'<ruby=[^>]*>', '', s)      # <ruby=よみ>本体</ruby> ⇒ 本体
    s = s.replace('</ruby>', '')
    s = re.sub(r'</?size[^>]*>', '', s)     # 字号标签
    s = s.replace('<br>', '')
    s = s.replace('\r', '').replace('\n', '')
    return s.strip()


def main():
    sc = os.path.join(ROMFS, 'Data/StreamingAssets/script')
    ja = load_hdlg(os.path.join(sc, 'script_dialog_ja.hdlg'))
    lines = []
    tags = set()
    for s in ja[START:]:
        if not s:
            continue
        for m in TAG.findall(s):
            tags.add(m)
        t = clean(s)
        if t:
            lines.append(t)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as w:
        w.write('\n'.join(lines) + '\n')
    print('条目 %d → 行 %d  剩余标签 %s' % (len(ja), len(lines), sorted(tags)[:8]))


if __name__ == '__main__':
    main()
