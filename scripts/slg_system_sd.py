"""SLG System 系（Unicorn-B 2005「Heartner Hearts!」）文本提取器。

数据来源（不是打包容器，是**安装后的散文件**）：InstallShield 包 → `HEARTNER_HEARTS/`：
  · `main/main.sd`  **剧本流**（2.6 MB，cp932 ＋ 二进制操作码）
  · `main/keyword.dat` **用語辞典**（cp932 纯文本，`@見出し` ＋ 换行连续解説，空行分隔）
  · `main/main.ev`  141 条章題（不在本工具输出内）；`main.cg`／`main.lb`／`main.sw` 为资源表/标签/开关

## `main.sd` 的记录格式（L0：字段自带行数）

```
27 <u32 seq> <name> 00 <n> <line1> 00 <line2> 00 … <lineN> 00 29
```
· `0x27` ＝ **文本记录开始**，随后 `u32 seq`（全篇 0 起单调递增，0 违例 ⇒ 顺序可信）
· `<name>` ＝ **独立名字窗**的字符串（cp932、NUL 结尾；空串＝无名字窗/旁白）
· `<n>` ＝ **本框的行数**（实测 1..6：1 行 15,898 ／ 2 行 6,314 ／ 3 行 2,964 ／ 4 行 320 ／ 5 行 218 ／ 6 行 122）
  ⇒ **框内换行一律合并成一行**（n 是引擎给的字段，不是字数猜的）
· `0x29` ＝ **记录终止**（一次点击＝一个文本框）
· 正文里的 `>NNN` / `<NNN`（N 为 1–3 位数字，成对出现，110/210/310/910…）＝**行内标记**（着色/样式），剥除

判据自检：① 边界是字节里的 `27 <u32> 00 n … 00 29`，字段名清楚；② 25,836 条记录 seq 全篇单调；
③ 两段失败样本（`27` 误命中的噪声）被 `n∈1..6` ＋ `00 29` 双条件排除。

用法：
  python scripts/slg_system_sd.py --root <HEARTNER_HEARTS 目录> --out 成品.txt [--raw raw目录]
"""
import argparse
import io
import os
import re
import sys

TAG = re.compile(r'[<>][0-9!+\-]{1,4}')
TEXT_OP = re.compile(rb'\x01')


def records(path):
    """严格解析 main.sd → [(seq, name, [line,…], offset)]；顺序＝文件顺序。"""
    d = io.open(path, 'rb').read()
    out, i = [], 0
    while True:
        p = d.find(b'\x27', i)
        if p < 0 or p + 6 > len(d):
            break
        i = p + 1
        seq = int.from_bytes(d[p + 1:p + 5], 'little')
        if seq > 2000000:
            continue
        ne = d.find(b'\x00', p + 5)
        if ne < 0 or ne - p > 70:          # 名字窗上限 60 B，超了必是噪声命中
            continue
        q = ne + 1
        n = d[q]
        if n not in (1, 2, 3, 4, 5, 6):
            continue
        r, lines, ok = q + 1, [], True
        for _ in range(n):
            e = d.find(b'\x00', r)
            if e < 0:
                ok = False
                break
            lines.append(d[r:e])
            r = e + 1
        if not ok or d[r:r + 1] != b'\x29':
            continue
        out.append((seq, d[p + 5:ne].decode('cp932', 'replace'),
                    [x.decode('cp932', 'replace') for x in lines], p))
        i = r + 1
    return out


def glossary(path):
    """用語辞典：`@見出し` 起条，后续行（含空行分段）并成一条（框内换行合并）。"""
    t = io.open(path, 'rb').read().decode('cp932', 'replace').replace('\r\n', '\n')
    rows, cur = [], None
    for ln in t.split('\n'):
        s = ln.strip()
        if s.startswith('@'):
            if cur:
                rows.append(cur)
            cur = [s[1:].strip()]
        elif cur is not None:
            if s:
                cur.append(s.lstrip('\u3000'))
    if cur:
        rows.append(cur)
    if not rows:
        return []
    head, body = rows[0][0], rows[0][1:]
    return ['【%s】%s' % (r[0], ''.join(r[1:])) for r in rows]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='HEARTNER_HEARTS 目录（含 main/ 与 keyword.dat）')
    ap.add_argument('--out', help='成品 txt（UTF-8 BOM ＋ 纯 LF）')
    ap.add_argument('--raw', help='同时导出记录级原文（seq\tname\tn\t每行用 ／ 分隔）')
    ap.add_argument('--no-glossary', action='store_true', help='不并入用語辞典')
    a = ap.parse_args()

    sd = os.path.join(a.root, 'main', 'main.sd')
    kw = os.path.join(a.root, 'main', 'keyword.dat')
    if not os.path.isfile(kw):
        kw = os.path.join(a.root, 'keyword.dat')
    recs = records(sd)
    # `END` 是脚本的终止标记：它之后只剩空记录与开发笔记（「ラベルジャンプで各ラベルに飛んでください」）
    for k, (seq, name, lines, off) in enumerate(recs):
        if ''.join(lines).strip() == 'END':
            recs = recs[:k]
            break
    rows, names = [], {}
    for seq, name, lines, off in recs:
        txt = ''.join(TAG.sub('', x) for x in lines).strip('\u3000')
        if not txt:
            continue
        rows.append(txt)
        names[name] = names.get(name, 0) + 1

    if a.raw:
        os.makedirs(a.raw, exist_ok=True)
        with io.open(os.path.join(a.raw, 'records.tsv'), 'w',
                     encoding='utf-8', newline='\n') as f:
            for seq, name, lines, off in recs:
                f.write('%d\t%s\t%d\t%s\n' % (seq, name, len(lines),
                                              '／'.join(TAG.sub('', x) for x in lines)))

    g = []
    if not a.no_glossary and os.path.isfile(kw):
        g = glossary(kw)

    if not a.out:
        print('records %d / rows %d / glossary %d' % (len(recs), len(rows), len(g)),
              file=sys.stderr)
        return
    with io.open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
        for s in rows:
            f.write(s + '\n')
        for s in g:
            f.write(s + '\n')
    L = sorted(len(x) for x in rows)
    print('记录 %d / 正文 %d 行 / 用語 %d 条 → 合计 %d 行；名字 %d 种'
          % (len(recs), len(rows), len(g), len(rows) + len(g), len(names)), file=sys.stderr)
    print('正文最长 %d / 中位 %d' % (L[-1], L[len(L) // 2]), file=sys.stderr)
    print('名字 top: %s' % sorted(names.items(), key=lambda x: -x[1])[:8], file=sys.stderr)


if __name__ == '__main__':
    main()
