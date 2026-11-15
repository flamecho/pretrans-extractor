# -*- coding: utf-8 -*-
"""Macromedia Director（Afterburner 保护）→ 台本 CSV → 「一次点击 = 一行」。

适用范围：Director 作的 `.CXT`/`.DXR` 先用 ProjectorRays 解 Afterburner：
    pr.exe decompile <in.CXT> -o <out>
再把解出的文件喂给本工具：
    python director_stxt_text.py --in out1 out2 ... --out 成品.txt [--dump 记录表.txt]

结构判据（全部来自字段位置，不看文本内容）：
  STXT chunk：4CC 'TXTS'（Director 小端 RIFX 的 4CC 反序）| u32LE size |
              BE u32 0x0000000C | BE u32 textLen | BE u32 0x00000016 | text | 22 B trailer
  文本 = 一条长串，记录用 CR(0x0D) 分隔、字段用 ',' 分隔
  记录 = f0 ID ／ f1..f4 四个显示槽 ／ f5 次记录 ID ／ f6,f7,f8 槽1~3 的「选项」标志 ／ f10.. 资源
  断框：一条记录 = 一个消息框 = 一次点击（每记录只有 1 个 next）⇒ 4 个槽合并成一行
        反向验证：全库槽字数 ≤ 20 字（0 条 > 22）⇒ 槽 = 20 字宽文本框的一行
  选项：k = f6+f7+f8 中 '1' 的个数；槽 1..k 为选项，各占一行；槽 0 非名札时作提示行
  名札：槽 0 为「【…】」整字段 ⇒ 独立名字窗 ⇒ 剔除、不加前缀
"""
import argparse, io, json, re, struct, sys, collections

NAME_RE = re.compile(r'^【[^】]{1,20}】$')
ID_RE = re.compile(r'^[a-z]+[0-9]')
WS_LEAD = re.compile(r'^[\u3000 \t]+')
TRAILER = 22


def stxt_chunks(d):
    """返回 [(off, size, textBytes)]；只认 body 首字段 == 0x0C 的真 chunk（imap 条目会被排除）。"""
    out, n, p = [], len(d), 0
    while True:
        p = d.find(b'TXTS', p)
        if p < 0:
            return out
        if p + 20 <= n:
            size = struct.unpack_from('<I', d, p + 4)[0]
            a, tl, b = struct.unpack_from('>III', d, p + 8)
            body = p + 8
            if 0 < size <= n - body and a == 12 and b == 0x16:
                # 结构自校验：body == 12 + textLen + 22（对不上就不是 chunk 头）
                if tl + 12 + TRAILER == size:
                    out.append((p, size, d[body + 12:body + 12 + tl]))
        p += 4


def collect(paths):
    mem, recs = [], []
    for path in paths:
        d = open(path, 'rb').read()
        seen = set()
        for off, size, text in stxt_chunks(d):
            if text in seen or not text:
                continue
            seen.add(text)
            mem.append((path, off))
            for i, line in enumerate(text.decode('cp932', 'replace').split('\r')):
                if line.strip():
                    recs.append((path, off, i, line.split(',')))
    return mem, recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inputs', nargs='+', required=True)
    ap.add_argument('--out')
    ap.add_argument('--dump')
    ap.add_argument('--fields', type=int, default=43)
    a = ap.parse_args()

    mem, recs = collect(a.inputs)
    body = [r for r in recs if len(r[3]) == a.fields and ID_RE.match(r[3][0])]
    print('文本成员 %d ／ 记录 %d ／ 正文候选 %d（%d 字段且 ID 合规）／ 其余 %d'
          % (len(mem), len(recs), len(body), a.fields, len(recs) - len(body)))

    byid = {}
    conflict = 0
    for r in body:
        if r[3][0] in byid:
            conflict += r[3] != byid[r[3][0]][3]
        else:
            byid[r[3][0]] = r
    print('唯一记录 %d ／ 同 ID 冲突 %d' % (len(byid), conflict))

    lines, used = [], set()
    stat = collections.Counter()
    for path, off, i, fd in body:
        rid = fd[0]
        if rid in used:
            continue
        used.add(rid)
        fam = re.match(r'[a-z]+', rid).group(0)
        slots = list(fd[1:5])
        k = sum(1 for j in (6, 7, 8) if fd[j] == '1')
        if NAME_RE.match(slots[0]):
            slots[0] = ''
        if k:
            prompt = slots[0].strip()
            if prompt:
                lines.append(prompt)
                stat[fam] += 1
            for j in range(1, k + 1):
                if slots[j].strip():
                    lines.append(slots[j].strip())
                    stat[fam + ':opt'] += 1
        else:
            txt = slots[0].strip()
            for s in slots[1:]:
                txt += WS_LEAD.sub('', s)
            if txt.strip():
                lines.append(txt.strip())
                stat[fam] += 1

    opts = sum(v for k2, v in stat.items() if k2.endswith(':opt'))
    print('成品 %d 行（选项 %d ／ 字数 %d ／ 最长 %d）'
          % (len(lines), opts, sum(len(x) for x in lines), max(len(x) for x in lines)))
    if a.dump:
        with io.open(a.dump, 'w', encoding='utf-8', newline='\n') as f:
            for k in sorted(stat):
                f.write('%s\t%d\n' % (k, stat[k]))
        print('族统计 → %s' % a.dump)
    if a.out:
        with io.open(a.out, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('\n'.join(lines) + '\n')
        print('成品 → %s' % a.out)


if __name__ == '__main__':
    main()
