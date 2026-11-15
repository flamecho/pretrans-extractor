# -*- coding: utf-8 -*-
"""[NS-JP]マツリカの炯 -kEi- 天命胤異伝 全文本提取

容器链（全部用工具）：
  .nsz --nsz -D--> .nsp --hactool -t pfs0--> *.nca
  Program NCA e8291ea6…（Titlekey crypto，titlekey 在 .tik 0x180 的明文 16 字节）
  --hactool --romfsdir--> romfs/common/{script.memfs, script.membody}

容器结构：
  script.memfs    = RSON 索引：头部 + [偏移/长度表] + [UTF-16 文件名表，节点 `88 XX` + 名字]
  script.membody  = `RZ\0<type>` 头 + zlib 的 130 个块，**每块 = 一个文件**（顺序与名字表一致）
  文件 = /_bytecode/EV*/EV*.tatc（128 个 = 剧本字节码 + filelist.json + script.armd）

.tatc：
  `c1 ab de c0 | "KUV " | ...` 头 + 命令名表 + 字节码
  **字符串池 = 2 字节对齐的 UTF-16LE 串，以对齐的 `00 00` 结束**
  ★ 关键坑：`\r\n\u3000` 的字节是 `0d 00 0a 00 00 30`，中间两字节是 `00 00`，
    用字节 `find(b'\x00\x00')` 会误判成串结束 ⇒ **必须按 2 字节步进扫描**。

成行判据（L0）：**一个 UTF-16 串 = 一屏 = 一次点击**。
  串内的 `\r\n` 是框内换行 ⇒ 合并；串内 `#P(x,y)` 是同屏分段坐标 ⇒ 删标记保内容。
  这是数据里真实存在的边界，不是按字数/容量/括号配平切。

附带结构：
  选项块：`SltDel` → [`SLT<n>_A` ][选项文本] [`SltAdd`] [`SLT<n>_B`][选项文本] … [`<组号>`][`SltRun`]
    ⇒ **选项文本 = 紧跟 `SLT<n>_[ABC]` 标签之后的那个串**（结构判据）。
    ★ 旧写法把 `SltAdd` 后面第 2 个串当选项文本 —— 那是**下一个选项**，且每组首选项被漏掉。
  `【X5】/【N5】/【M5】` = 选项组元数据前缀（字母＝类型、数字＝档位），**屏幕上是纯文本**
    ⇒ 选项行必须剥掉这个前缀，不得原样留。
  `GAMESTR_DictWords` → [見出し][解説]  用語辞典，并入末尾
  名字 = ≤10 字纯汉字/假名/全角空格，且**下一串以 `「` 开头** ⇒ 剔除（独立名字窗）
  名字串若误判会吃正文，故只在「下一串以「开头」时判
"""
import os, re, sys, json
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

ROOT = os.path.join(VNTRANS_HOME, '_w_mtj/tatc')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[NS-JP]マツリカの炯 -kEi- 天命胤異伝.txt')
HEROINE = 'ナーヤ'

JP = re.compile(r'[ぁ-んァ-ヶー一-龥]')
HIRA = re.compile(r'[ぁ-ん]')
OKCH = re.compile(r'[ぁ-んァ-ヶー一-龥、。！？」』（）…―・：；「」『』【】〜～　'
                  r'Ａ-Ｚａ-ｚ０-９\u3000\x20-\x7e\r\n\t]')
NAME_ONLY = re.compile(r'^[ぁ-んァ-ヶー一-龥\u3000]{1,10}$')
SLTID = re.compile(r'^SLT\d+_[ABC]$')          # 选项槽标签；`_END` 不是槽，是块尾
OPTPRE = re.compile(r'^【[XNM]\d+】')            # 选项组元数据前缀（不显示）


def strings(d):
    """按 2 字节对齐扫描，遇到对齐的 00 00 结束。返回 [(偏移, 串)]"""
    out = []
    i = 0
    n = len(d)
    while i + 1 < n:
        if d[i] == 0 and d[i + 1] == 0:
            i += 2
            continue
        j = i
        while j + 1 < n and not (d[j] == 0 and d[j + 1] == 0):
            j += 2
        raw = d[i:j]
        try:
            s = raw.decode('utf-16-le')
        except UnicodeDecodeError:
            s = ''
        out.append((i, s))
        i = j + 2
    return out


def clean(s):
    # `#T<n>` 是**互斥变体层**：`#T1`=默认名版、`#T2`=改名版、`#T0`=共用基础。
    # 只保留「第一个非 0 层」+ 全部 0 层，两版不会拼在一起。
    if '#T' in s:
        parts = re.split(r'#T(\d)', s)
        segs = [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts), 2)]
        keep = []
        got_nz = False
        for n, t in segs:
            if n == 0:
                keep.append(t)
            elif not got_nz:
                keep.append(t)
                got_nz = True
        s = ''.join(keep)
    s = re.sub(r'#R\([^)]*\)', '', s)      # ruby 读音，保留后面紧跟的基底
    s = re.sub(r'#P\([^)]*\)', '', s)      # 同屏分段坐标
    s = re.sub(r'#C\([^)]*\)', '', s)      # 字色
    s = s.replace('#KW', '')
    s = s.replace('${FirstName}', HEROINE)
    # 框内换行（`\r\n`）与其后的缩进 `\u3000` 一起合并掉；行内其它 `\u3000` 保留
    s = re.sub(r'\r?\n\u3000?', '', s)
    return s.strip('\u3000').strip()


def is_text(s):
    return (bool(s) and len(s) >= 4 and JP.search(s)
            and all(OKCH.match(c) for c in s))


def build():
    rows = []
    dic = []
    st = {'files': 0, 'names': 0, 'dicts': 0, 'text': 0, 'opts': 0}
    for f in sorted(os.listdir(ROOT)):
        if not f.endswith('.tatc'):
            continue
        st['files'] += 1
        d = open(os.path.join(ROOT, f), 'rb').read()
        S = strings(d)
        n = len(S)
        # 选项槽：`SLT<n>_[ABC]` 标签**后面紧跟**的那个串 = 选项文本（结构判据）
        # 相邻两个标签（`SLT04_A` 后直接 `SLT04_B`）= 该槽无文本，不能把它当选项
        opt_at = {k + 1 for k in range(n - 1)
                  if SLTID.match(S[k][1]) and not SLTID.match(S[k + 1][1])}
        k = 0
        while k < n:
            pos, s = S[k]
            if s == 'GAMESTR_DictWords':
                # [見出し][解説]
                head = S[k + 1][1] if k + 1 < n else ''
                body = S[k + 2][1] if k + 2 < n else ''
                ch_, cb_ = clean(head), clean(body)
                # 见出し与解説都必须含日文（排除资源名/ID 混入）
                if ch_ and cb_ and JP.search(ch_) and JP.search(cb_):
                    dic.append(ch_)
                    dic.append(cb_)
                    st['dicts'] += 1
                k += 3
                continue
            if k in opt_at:
                # 选项：屏幕上是纯文本 ⇒ 剥掉【X5】这类组元数据前缀；不做 hira 门槛
                t = clean(OPTPRE.sub('', s))
                if t:
                    rows.append(t)
                    st['opts'] += 1
                    if len(t) > 40:
                        print('[warn] 长选项', f, repr(s)[:80])
                k += 1
                continue
            # 名字：短且下一串以「开头
            if (NAME_ONLY.match(s) and k + 1 < n and S[k + 1][1].startswith('「')):
                st['names'] += 1
                k += 1
                continue
            if is_text(s):
                t = clean(s)
                if t and HIRA.search(t):
                    rows.append(t)
                    st['text'] += 1
            k += 1
    return rows, dic, st


if __name__ == '__main__':
    rows, dic, st = build()
    # 相邻完全重复（同一文件内「同屏多版本」）去掉
    out = []
    for r in rows:
        if out and out[-1] == r:
            continue
        out.append(r)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')
        if dic:
            fh.write('\n'.join(dic) + '\n')
    st['rows'] = len(out)
    st['chars'] = sum(len(x) for x in out)
    st['dict_lines'] = len(dic)
    print(json.dumps(st, ensure_ascii=False))
