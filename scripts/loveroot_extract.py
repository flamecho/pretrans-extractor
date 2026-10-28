#!/usr/bin/env python3
"""loveroot_extract.py —— PS2『ラブルートゼロ kisskiss☆ラビリンス』(Dimple/Asgard 2010) 全文本抽出。

链路：ISO9660 → DATA/GAMESCR.PAC（剧本容器，无压缩、无加密）→ 块→页表→页文本。

容器结构（实证）：
  GAMESCR.PAC := 块(1..N) 顺序拼接，块 = [u16 tbl_off][u16 n_page][code][0e 00 00 00][页表][页数据]
    - tbl_off  ：页表相对「块起址」的偏移；页表起点 = 块起址 + tbl_off
    - n_page   ：页数；页表紧接页数据，且 tbl_off + 4*n_page == 首页偏移 ⇒ 自校验
    - 页表项   ：[u16 off][u16 len]，off 相对块起址，且 off[i]+len[i] == off[i+1]（链式）
    - 页数据   ：cp932 文本，页长上限 ≈100 B（≈50 全角），页内 'CR' = 软换行
  块 0 起址 0x000000，末块结束 = 文件长 0x11D584（闭合）。

指令层（正文相关）：
  0x38 <u16 名字ID>   设定当前说话人（有独立名字窗 ⇒ 不输出名字）
  0x14 <u16 页号>      显示一页（一次点击）
  0x15 <u16 语音ID> <u16 页号>   带语音显示一页（一次点击）
  0x5f <u16 n> 之后 n+1 组 [u16 页号][u32 跳转]  选择肢（末组跳转=0）
  ⇒ 页序 = 点击序（每块内 0..n_page-1 顺序引用，已逐块核对；选择肢页由 0x5f 引用，
     在页表中仍按正文位置排列，故顺序输出即得选项原文）。

文本内宏：CR=软换行(合并)｜P1=姓(安達)｜P2=名(八重子)｜NK=名(八重子)｜C1…C0=着色(剥)｜
          0x9873=彗／0x9874=里（自定义字槽，cp932 未分配区）
"""
import struct, re, sys, os

SRC = sys.argv[1] if len(sys.argv) > 1 else '_work_loveroot/x/DATA/GAMESCR.PAC'
OUT = sys.argv[2] if len(sys.argv) > 2 else '_work_loveroot/draft.txt'

d = open(SRC, 'rb').read()
n = len(d)

CUSTOM = {b'\x98\x73': '彗', b'\x98\x74': '里'}
MACRO = {'P1': '安達', 'P2': '八重子', 'NK': '八重子'}

# 系统/战斗提示（非剧情正文）：整块剔除（≥80% 命中）＋逐页剔除
SYS_PAGE = re.compile(r'(選択してください|隊列を変更します|ENの攻撃|NMポイント|^EN|キズナが深まり)')
SYS_BLK = re.compile(r'(キズナが深まり|必殺技|選択してください|隊列を変更します|隊列を選択|ENの攻撃|NMポイント|^EN)')
SKIP_BLOCKS = {531}  # 末块＝キズナ/必殺技 系统通知表（含技能名，无剧情）


def dec(seg):
    out = []
    i = 0
    while i < len(seg):
        if seg[i:i + 2] in CUSTOM:
            out.append(CUSTOM[seg[i:i + 2]])
            i += 2
            continue
        b = seg[i]
        if 0x81 <= b <= 0x9f or 0xe0 <= b <= 0xef:
            out.append(seg[i:i + 2].decode('cp932', 'replace'))
            i += 2
            continue
        out.append(chr(b))
        i += 1
    return ''.join(out)


def clean(t):
    t = t.replace('CR', '')
    t = re.sub(r'C[01]', '', t)
    for k, v in MACRO.items():
        t = t.replace(k, v)
    return t.strip(' 　')


def main():
    lines = []
    pages = kept = dropped = blocks = 0
    pos = 0
    bi = 0
    while pos + 4 <= n:
        t_off, cnt = struct.unpack_from('<HH', d, pos)
        tpos = pos + t_off
        if cnt == 0:
            pos = tpos
            bi += 1
            continue
        pgs = [struct.unpack_from('<HH', d, tpos + 4 * i) for i in range(cnt)]
        end = pos + pgs[-1][0] + pgs[-1][1]
        blocks += 1
        hits = sum(1 for o, l in pgs if SYS_BLK.search(dec(d[pos + o:pos + o + l])))
        if bi in SKIP_BLOCKS or hits * 10 >= len(pgs) * 8:
            dropped += cnt
            pos = end
            bi += 1
            continue
        for o, l in pgs:
            pages += 1
            t = dec(d[pos + o:pos + o + l])
            if SYS_PAGE.search(t):
                dropped += 1
                continue
            t = clean(t)
            if not t:
                dropped += 1
                continue
            lines.append(t)
            kept += 1
        pos = end
        bi += 1

    assert pos == n, '闭合失败: %x != %x' % (pos, n)
    print('blocks=%d pages=%d kept=%d dropped=%d lines=%d' % (blocks, pages, kept, dropped, len(lines)))
    with open(OUT, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
