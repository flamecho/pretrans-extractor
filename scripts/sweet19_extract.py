#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[JP]Sweet 19 Pain —— ComicPly (ICM95 / CmdVer=14) 全文本提取

源链路：
  [JP]Sweet 19 Pain.exe (RAR5 SFX, 密码 otoame)
    -> sweet19pain.iso (ISO9660, CD-BRIDGE)
       -> sweet.cpf (ComicPly 容器: 二进制资源目录 + 明文脚本)
          -> 脚本区段 (Shift-JIS): <Head> + <Book> + <Page> + 命令
             - MsgDlg "..."  = 对话 (一次点击=一个文本框=一行)
             - SelectDlg "选A","$N$","选B","$M$",... = 选项

提取规则（vn-custom-bytecode-text §0）：
  - 一次点击 = 一个文本框 = 一行；框内换行(#) 合并进同一行。
  - 富文本标记 <clBlue>/<clRed>/<clBlack>… 成行前剥净。
  - 选项一行一条、按序（图片式无字选项跳过）。
  - 排除：Graphic(图像文件名) / System / PageJump / Music* / 二进制资源块。

用法：
  python scripts/sweet19_extract.py
"""
import os, re, sys
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())

CPF = os.path.join(VNTRANS_HOME, "_work_sweet19/iso/sweet.cpf")
OUT = os.path.join(VNTRANS_HOME, "提取结果/[JP]Sweet 19 Pain.txt")

# 内联富文本 / 颜色标记（ComicPly 用 <clBlue> 等）
TAG = re.compile(r'<cl[A-Za-z0-9_]*>')
# 半角引号 ｢｣ ＝ 全角「」的半角同字族；源混用（全角开+半角闭），统一为全角「」
# 以便引号配对与下游翻译工具兼容（不改变引号语义）。
HALF_Q = str.maketrans('｢｣', '「」')

def clean_text(s: str) -> str:
    s = TAG.sub('', s)          # 剥 <clXXX> 颜色标记
    s = s.translate(HALF_Q)     # 半角引号 → 全角
    s = s.replace('#', '')      # 框内换行 -> 合并
    s = s.replace('\r', '').replace('\n', ' ')
    return s.strip()

def extract():
    d = open(CPF, 'rb').read()
    # 脚本区段起点：第一个 <Head
    head = d.find(b'<Head')
    if head < 0:
        # 退化：直接用整文件找 MsgDlg（理论上不会到这里）
        head = 0
    body = d[head:]

    # 收集所有 MsgDlg 与 SelectDlg 的匹配位置，按出现顺序处理
    msg_re = re.compile(rb'MsgDlg\s*"([^"]*)"')
    sel_re = re.compile(rb'SelectDlg\s*(.*?)(?:\r?\n|$)', re.S)

    # 先收集位置
    msg_matches = [(m.start(), 'msg', m) for m in msg_re.finditer(body)]
    sel_matches = [(m.start(), 'sel', m) for m in sel_re.finditer(body)]
    all_m = sorted(msg_matches + sel_matches, key=lambda x: x[0])

    lines = []
    n_msg = 0
    n_opt = 0
    for _, kind, m in all_m:
        if kind == 'msg':
            raw = m.group(1)
            s = raw.decode('cp932', 'replace')
            t = clean_text(s)
            if t:
                lines.append(t)
                n_msg += 1
        else:
            # SelectDlg 行：取整行，抽取选择项（非 $N$ / 非 /选项）
            line = m.group(1)
            # 找到所有引号串
            strs = re.findall(rb'"([^"]*)"', line)
            for sr in strs:
                s = sr.decode('cp932', 'replace').strip()
                if not s:
                    continue
                if s.startswith('$') and s.endswith('$') and len(s) >= 3:
                    continue  # 分支目标 $N$
                if s.startswith('/'):
                    continue  # /POS /COLOR /SIZE /WIN 等选项
                t = clean_text(s)
                if t:
                    lines.append(t)
                    n_opt += 1

    # 写 UTF-8 BOM / 纯 LF
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\ufeff')
        f.write('\n'.join(lines))
        if lines:
            f.write('\n')
    print(f"MsgDlg(对话行): {n_msg}")
    print(f"SelectDlg(选项行): {n_opt}")
    print(f"总输出行数: {len(lines)}")
    print(f"输出: {OUT}")

if __name__ == '__main__':
    extract()
