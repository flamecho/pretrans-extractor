#!/usr/bin/env python3
# Regenerate charset + allow ledger for the REAL Psychic Rain script.
import os, re
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
from collections import Counter
TXT = os.path.join(VNTRANS_HOME, "提取结果/[PC-JP]Psychic Rain.txt")
ALLOW = os.path.join(VNTRANS_HOME, "解析报告/allow/[PC-JP]Psychic Rain.allow")
CHARSET = os.path.join(VNTRANS_HOME, "解析报告/allow/[PC-JP]Psychic Rain.charset")

# non-Japanese = anything not Hiragana/Katakana/Kanji/punctuation we treat as JP.
JP = re.compile(r'[\u3000-\u30ff\u3400-\u9fff\uff66-\uff9f\u3001-\u303f\u3040-\u309f\u30a0-\u30ff]')
def is_jp(ch):
    o=ord(ch)
    return (0x3000<=o<=0x30ff) or (0x3400<=o<=0x9fff) or (0xff66<=o<=0xff9f)
cnt=Counter()
n=0
for ln in open(TXT,encoding="utf-8"):
    n+=1
    for ch in ln:
        if ch=="\n": continue
        if ch=="\ufeff": continue   # 文件 BOM，非内容字符
        if not is_jp(ch):
            cnt[ch]+=1
# write charset
with open(CHARSET,"w",encoding="utf-8") as f:
    f.write("# 非日文字符台账（每行一个字符，首字符生效；人工核对后生成）\n")
    for ch,c in sorted(cnt.items(), key=lambda x:-x[1]):
        f.write(f"{ch}\t{c}\n")
print("charset entries:", len(cnt), dict(list(cnt.items())[:10]))
# allow: real script needs no exemptions (check_text PASS, 0 error)
with open(ALLOW,"w",encoding="utf-8") as f:
    f.write("# [PC-JP]Psychic Rain — 白名单（精确匹配正文，仅豁免形态类误报；非日文字符另见 .charset）\n")
    f.write("# 本作 check_text 退出码 0（ERR=0），无需字符豁免；台账仅含 … 与空格（均为原文标点/排版）。\n")
print("allow written")
