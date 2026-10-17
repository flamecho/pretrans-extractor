#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 PC 汉化补丁的 .snr（UTF-16LE KiriKiri 脚本）提取「剧情序」标尺。

用途：PSV 版（Orfre/DCVM）的 STR 池是 SJIS 排序的，行序丢失；
       而 PC 版同场景的 .snr 文本按**文件行序 = 剧情序**排列，且每行带语音 id
       （如 (AD1079) ←→ PSV 池里的 ad/ad1079）⇒ 可作定序标尺。

输出: <out.json>  { "<场景名>": {"chapter": "...", "lines": [{"t":正文,"name":名札,"voice":"AD1079"}, ...]} }
用法: python scripts/pc_snr_order.py <pc_snr_dir> <out.json>
"""
import sys, os, glob, re, json

DIRECTIVE = re.compile(r'^\s*[^\s【].*\(\s*"')          # 形如 背景("bg14a"); / 音楽再生("BGM01");
LINE_RE = re.compile(r'^【(?P<name>[^】]*)】(?:\((?P<voice>[A-Za-z0-9_]+)\))?(?P<body>.*)$')
INFO_RE = re.compile(r'インフォメーション\("([^"]*)"\)')
HERO = "\\1"                                            # 主人公名宏


def parse(path):
    t = open(path, 'rb').read().decode('utf-16le', 'replace')
    t = t.replace('\ufeff', '')
    m = INFO_RE.search(t)
    chapter = m.group(1) if m else ''
    out = []
    for raw in t.split('\n'):
        s = raw.strip('\r').strip()
        if not s:
            continue
        if s.startswith('//') or s.startswith(';'):
            continue
        if DIRECTIVE.match(s) or s.endswith(';'):       # 指令行
            continue
        mm = LINE_RE.match(s)
        if mm:
            body = mm.group('body')
            out.append({"t": body, "name": mm.group('name') or None,
                        "voice": mm.group('voice') or None})
        else:
            out.append({"t": s, "name": None, "voice": None})
    return chapter, out


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "_work_orfleur/pc_snr"
    out = sys.argv[2] if len(sys.argv) > 2 else "_work_orfleur/pc_order.json"
    data = {}
    for p in sorted(glob.glob(os.path.join(d, "*.snr"))):
        nm = os.path.basename(p)[:-4]
        ch, lines = parse(p)
        lines = [x for x in lines if x["t"] and len(x["t"]) > 1]
        data[nm] = {"chapter": ch, "lines": lines}
    with open(out, 'w', encoding='utf-8') as fp:
        json.dump(data, fp, ensure_ascii=False, indent=1)
    tot = sum(len(v["lines"]) for v in data.values())
    nv = sum(1 for v in data.values() for x in v["lines"] if x["voice"])
    print("scenes=%d lines=%d voiced=%d -> %s" % (len(data), tot, nv, out))


if __name__ == '__main__':
    main()
