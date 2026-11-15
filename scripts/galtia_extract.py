# -*- coding: utf-8 -*-
"""GALTIA（PIL/SLASH, Artemis Engine）剧本 → 成行

## 容器
- `GALTIA.exe`（2.85 GB）＝ RAR5 SFX，内含 `GALTIA.pfs`（984 MB）+ `GALTIA.pfs.000`（2.09 GB，全 ogg）。
- PFS 是 **pf6**（不是滄海天記的 pf8）：`"pf6" + u32 index_size + u32 count`，索引从 0x07 开始
  （= u32 count + 条目），数据区紧接 0x07+index_size。
  ★ 本作 **不加密**：条目数据是明文（PNG 就是 `89 50 4E 47`，TTF 就是 `00 01 00 00`）；
  照 pf8 的「SHA1 索引 → 全文件 XOR」会把人读坏。

## 剧本（scenario/**/*.txt，cp932）
行语法：
```
[命令 参数…]          命令（立绘 `[シン 通常]`、`[bg]`、`[bgm file="…"]`、`[title text="…"]` …）
#name 表示名,表情ID    名字窗内容（独立名字窗 ⇒ 不收）
*label                 跳转标签
//…  ;…               注释 / 被禁用的命令行
<其它非空行>            正文
```
**断框判据（L1）**：正文**块**（由命令行 / 空行 / 注释行分隔的连续正文行）= 一个文本框 = 一次点击；
块内物理换行 = 框内改行 ⇒ 合并。全集 49,250 块里块长只有 1/2/3 行（＝框高 3），无 4 连。

`[tips text="スラム"]スラム[/tips]` 是正文里的内联注释标记 ⇒ 去标签留内文。
`[title text="…"]` = 章タイトル（扉文，直接上屏）⇒ 单列一行。
`[sel_text text="…"]` = 选项 ⇒ 一行一条。

## 用語集（setting/galtia_*.csv）
`galtia_other.csv`（名前,page,no,flag,画像,説明,…）/ `galtia_world.csv`（no,地名,…,説明）/
`galtia_chara.csv`（名前,所属国）⇒ 末尾按 `【見出し語】解説` 并入。
"""
import io, os, re, sys, glob

TAG = re.compile(r'\[/?tips[^\]]*\]')          # 内联 tips 标记
CMD_ASCII = re.compile(r'^\[[A-Za-z_&][^\]\s]*')
ATTR = re.compile(r'(\w+)="([^"]*)"')


def attr_text(st, cmd):
    """`[cmd a="x" text="…"]` —— 属性顺序不固定（实测有 `file=` 在前），按名取值。"""
    if not st.startswith('[' + cmd):
        return None
    d = dict(ATTR.findall(st))
    return d.get('text')


def flush(cur, out):
    if not cur:
        return
    s = ''.join(cur).strip()
    if s:
        out.append(s)
    cur.clear()


def parse_scenario(path, out):
    s = open(path, 'rb').read().decode('cp932', 'replace')
    cur = []
    in_block = False                       # /* … */ 块注释（组内文本被显式关闭显示）
    for line in s.split('\n'):
        t = line.rstrip('\r')
        st = t.strip()
        if in_block:
            if '*/' in st:
                in_block = False
                flush(cur, out)
            continue
        if st.startswith('/*'):
            flush(cur, out)
            if '*/' not in st:
                in_block = True
            continue
        tv = attr_text(st, 'title')
        if tv is not None:
            flush(cur, out)
            out.append(tv)
            continue
        tv = attr_text(st, 'sel_text')
        if tv is not None:
            flush(cur, out)
            out.append(tv)
            continue
        # 命令行判据：`[` 顶格；或缩进但命令名是 ASCII（如 `\u3000[se file=…]`）。
        # `　[tips …]` 是正文里的内联标记，必须当正文（否则整块被当命令截断，丢 `」`）。
        inline_tips = st.startswith('[tips') or st.startswith('[/tips')
        is_cmd = (not inline_tips) and (t.startswith('[') or (st.startswith('[') and CMD_ASCII.match(st)))
        if (not st or st.startswith('//') or st.startswith(';')
                or is_cmd or st.startswith('#') or st.startswith('*')):
            flush(cur, out)
            continue
        cur.append(TAG.sub('', t))
    flush(cur, out)


def read_csv(path):
    s = open(path, 'rb').read().decode('cp932', 'replace')
    rows = []
    for line in s.split('\n'):
        t = line.rstrip('\r')
        if not t.strip() or t.lstrip().startswith('//'):
            continue
        rows.append(t.split(','))
    return rows


def load_glossary(setting_dir):
    out = []
    seen = set()

    def add(word, desc):
        w = word.strip()
        if not w or w in seen:
            return
        seen.add(w)
        out.append('【%s】%s' % (w, desc.strip()) if desc.strip() else '【%s】' % w)

    for r in read_csv(os.path.join(setting_dir, 'galtia_other.csv')):
        if len(r) >= 6:
            add(r[0], r[5])
    for r in read_csv(os.path.join(setting_dir, 'galtia_world.csv')):
        if len(r) >= 11:
            add(r[1], r[10])
    for r in read_csv(os.path.join(setting_dir, 'galtia_chara.csv')):
        if len(r) >= 2:
            add(r[0], r[1])
    return out


def main():
    root = sys.argv[1]                       # 解包后的 pfs 目录
    dst = sys.argv[2]
    sc_dir = os.path.join(root, 'scenario')
    files = sorted(p for p in glob.glob(os.path.join(sc_dir, '**', '*.txt'), recursive=True)
                   if '_test_' not in os.path.basename(p) and '_bench' not in os.path.basename(p))
    lines = []
    for p in files:
        parse_scenario(p, lines)
    story = len(lines)
    dic = load_glossary(os.path.join(root, 'setting'))
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        for r in lines:
            f.write(r + '\n')
        for r in dic:
            f.write(r + '\n')
    print('scenario files=%d story=%d glossary=%d total=%d' % (len(files), story, len(dic), story + len(dic)))


if __name__ == '__main__':
    main()
