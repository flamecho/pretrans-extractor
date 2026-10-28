#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""バクダン★ハンダン（PSP / ULJM-06057，Otomate 2012-06-14）全文本提取

容器：ISO9660 → PSP_GAME/USRDIR/UNION.CPK（CRI CPK v7）→ 462 个 CRILAYLA 压缩 STCM2L
      （生成串 `STCM2L Oct  7 2010 17:55:27`）；编码＝明文 cp932，无自建字符集。
      `python scripts/iso9660.py extract <iso> <outdir> PSP_GAME/USRDIR/UNION.CPK`
      `python scripts/cpk.py`（同目录 cpk.py 的 CPK.raw() 自动解 CRILAYLA）

STCM2L 指令流（本作实测；与 キミカレ / いっしょにごはん 同族，cmd 集须逐作重统计）
  op = [u32 size][payload]
  payload = k×12B 槽 [u32 val][0xff000000][0xff000000]
          + 文本记录 ×m  [0][L/4][1][L][cp932 text + NUL pad]
          + 12B 尾 [0][cmd][flag]
  ★ 硬校验：k 由槽特征前进定界、文本记录按 [0][L/4][1][L] 自定界、尾必须 u32==0 且
    「槽长+记录长+12 == payload 长」全等，否则整条 op 判非文本（不当文本猜）。

★★ 断框判据（L1，本作主判据）：**尾部 flag 字段**
     s==1 且含 1 条日文记录 ⇒ 该 op 是正文片段；
        flag == 1  ⇒ 同框续行（不清框）
        flag != 1  ⇒ **框末＝一次点击结束**
     实测对应：0xd2/flag1 续行 24,686 ｜ 0xd3/flag0 框末 20,733 ｜
               0x35/flag2 框末 5 ｜ 0xe7/flag3 框末 146 ｜ 0x33/flag2 = 调试(処理開始) 剔除
  名札：0xd4 = 说话人名字窗开始（带 0/1/2 槽脸部参数），其后紧跟的 1 条短文本即名札
        （全库 15,291 个 0xd4 中 14,699 个紧跟名札记录＝96.1%；余为「清空名字窗」）
        名札有独立名字窗 ⇒ 丢弃，不加说话人前缀。
  选项：s>=3 且 1 条记录（0xe7/0xec/0xe6/0x01ae），组以 0xe6(s<=1) 收、`select`(0x33) 锚定。
        另有一类 3 槽选项（0x01ae，舞台选择菜单）与「もう一度チャレンジする／タイトルに戻る」
        游戏结束菜单（463 次固定组）属系统 UI ⇒ 剔除（报告登记）。

主角：稲船 沙希（vndb v10115，Nameable）——正文以 #Name[1]（稲船）/#Name[2]（沙希）宏出现，
      名札记录形如 `#Name[1]#Name[2]`。

用法：python scripts/bakudan_extract.py <stcm_dir> <out.txt>
"""
import os, re, struct, sys, glob, collections

HERO = {'#Name[1]': '稲船', '#Name[2]': '沙希'}
JP = re.compile(r'[\u3041-\u3096\u30a1-\u30fa\u4e00-\u9fff]')
TAGS = re.compile(r'#(?:Name|Color|Scale|Pos|Ruby|Kana|Font|Speed|Wait|SE|Flag|Var)\[[^\]]*\]')
KANA = re.compile(r'[\u3041-\u3096\u30a1-\u30fa]')
SYS = re.compile(r'^(?:主人公のセリフ|セリフその|[ＢＧＭＳＥＭＥ]\d+|色変化判定|好感度|処理開始|デバッグ|設定用フラグ|あいえふ)')
CAST_NAMES = {'稲船沙希', '調辺歩', '御手洗流星', '士道昴流', '芽御師航大', '若狭永遠', '卜部君麻呂',
              '黒子', '調辺マイ', 'ワルドブー', '魅神真', '稲船敬二', 'アナウンス', '？？？', '看護師',
              '医者', '車掌', '蛇足', '男性', '女性', '司会', '店主', '永遠＆航大', '黒子？', 'ワルドブー]'}
MENU = ({'もう一度チャレンジする', 'タイトルに戻る'},)   # 游戏结束菜单（系统 UI）
SYSMENU_CMD = {0x1ae}                                    # 舞台/路线选择菜单
DEBUG_CMD = {0x33}                                       # '処理開始'
NAMEBOX = 0xD4
TEXT_CMDS = {0xD2: 2, 0xD3: 2, 0x35: 1, 0xE7: 1}   # cmd -> 允许的最大槽数（0x35 s=2 是角色名表）


def ops_of(d):
    i = d.find(b'CODE_START')
    if i < 0:
        return []
    end = struct.unpack_from('<I', d, 0x20)[0]
    off = i + 24
    out = []
    while off + 4 <= end and off + 4 <= len(d):
        sz = struct.unpack_from('<I', d, off)[0]
        if sz < 4 or off + sz > len(d):
            break
        out.append(d[off + 4:off + sz])
        off += sz
    return out


def split(p):
    """-> (nslots, recs, (cmd,flag)|None)。None ⇒ 非文本 op。"""
    s = 0
    while len(p) - 12 * (s + 1) >= 12:
        w = struct.unpack_from('<III', p, 12 * s)
        if w[1] == 0xff000000 and w[2] == 0xff000000:
            s += 1
        else:
            break
    rest = p[12 * s:]
    if len(rest) < 12:
        return s, [], None
    A = struct.unpack_from('<I', rest, len(rest) - 12)[0]
    if A > 1:                      # 尾首字：0=builtin op / 1=import call（其后两字为 funcid,nparams）
        return s, [], None
    cmd, flag = struct.unpack_from('<II', rest, len(rest) - 8)
    mid = rest[:-12]
    recs, j = [], 0
    while j + 16 <= len(mid):
        a, b, c, L = struct.unpack_from('<IIII', mid, j)
        if a == 0 and b == L // 4 and c == 1 and 4 <= L <= 20000 and j + 16 + L <= len(mid):
            recs.append(mid[j + 16:j + 16 + L].split(b'\0')[0].decode('cp932', 'replace'))
            j += 16 + L
        else:
            break
    if j != len(mid):
        return s, [], None
    return s, recs, (cmd, flag, A)


def clean(t):
    for k, v in HERO.items():
        t = t.replace(k, v)
    t = TAGS.sub('', t)
    t = re.sub('[\uf8f0-\uf8f3\ufffd]', '', t)   # cp932 单字节高位/未定义 ⇒ 字形槽或控制码
    return t.replace('\u3000', '').strip() if t.startswith('\u3000') else t.strip()


def extract(d, st=None):
    sp = [split(p) for p in ops_of(d)]
    lines, opts = [], []
    cur = []
    want_name = False

    def flush():
        if cur:
            t = ''.join(cur).strip()
            if t:
                lines.append(t)
            del cur[:]

    def flush_opts():
        if opts:
            grp = set(opts)
            if not any(grp == m for m in MENU):
                lines.extend(opts)
            elif st is not None:
                st['sysmenu'] += 1
            del opts[:]

    for i, (s, recs, tg) in enumerate(sp):
        if tg is None:
            want_name = False
            continue
        cmd, flag, A = tg

        if cmd == NAMEBOX and A == 0:                      # 说话人名字窗开始
            flush()
            flush_opts()
            want_name = True
            continue

        if want_name:
            want_name = False
            if cmd == 0xd2 and len(recs) == 1 and not re.search(r'[「（『]', recs[0]):
                if st is not None:
                    st['name'] += 1
                continue

        # 名札（结构判定：单条记录、不含 「（『，且是 #Name 宏或裸角色名）⇒ 丢，并断框
        if len(recs) == 1:
            raw0 = recs[0].strip()
            if (not re.search(r'[「（『]', raw0)
                    and (re.fullmatch(r'(?:#Name\[\d\])+', raw0) or raw0 in CAST_NAMES)):
                flush()
                if st is not None:
                    st['name-plate'] += 1
                continue

        # 选项 / 菜单
        if s >= 3 and len(recs) == 1:
            x = clean(recs[0])
            if not x or x.isascii() or not KANA.search(x) or SYS.match(x) or (A == 0 and cmd in SYSMENU_CMD):
                if st is not None:
                    st['opt-skip'] += 1
                continue
            flush()
            opts.append(x)
            continue

        # 正文片段：(A=0 的 builtin 白名单) 或 (A=1 的 import call 但记录含假名＝上屏文本)
        if not recs:
            continue
        if A == 0:
            if cmd not in TEXT_CMDS or s > TEXT_CMDS[cmd]:
                continue
        else:
            if not any(KANA.search(x) for x in recs):
                continue
        # ★ A=1 的多记录同属一框（同一次点击的两行），按原序拼合（实测 8 例）
        seg = ''.join(clean(r) for r in recs)
        if not seg or seg.isascii() or SYS.match(seg) or cmd in DEBUG_CMD:
            if seg and (seg.isascii() or SYS.match(seg)):
                if st is not None:
                    st['sys/ascii'] += 1
            continue
        cur.append(seg)
        if flag != 1:                           # ★ 框末（一次点击）
            flush()
            flush_opts()
    flush()
    flush_opts()
    return lines


FIX_HALF = 0     # 半角 ')' 收尾（原文全半角混用）
FIX_QUOTE = 0    # 『…」 收尾（原文引号种别笔误）


def normalize(lines, st=None):
    """原文全半角/引号种别笔误的定值归一（不改字词；逐条计数并入报告）。"""
    out = []
    for t in lines:
        if '（' in t and t.count('（') > t.count('）') and ')' in t:
            k = t.count('（') - t.count('）')
            if t.count(')') == k:
                t = t.replace(')', '）')
                if st is not None:
                    st['fix-half-paren'] += k
        if t.startswith('（') and t.count('（') > t.count('）') and ')' not in t:
            t += '）'
            if st is not None:
                st['fix-append-paren'] += 1
        if t.startswith('『') and '』' not in t and t.endswith('」'):
            t = t[:-1] + '』'
            if st is not None:
                st['fix-quote-kind'] += 1
        out.append(t)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    files = sorted(glob.glob(os.path.join(src, '*.bin')), key=lambda p: int(os.path.basename(p).split('.')[0]))
    out, st = [], collections.Counter()
    nf = 0
    for p in files:
        d = open(p, 'rb').read()
        if not d.startswith(b'STCM'):
            continue
        ls = extract(d, st)
        if ls:
            nf += 1
            out.extend(ls)
    out = normalize(out, st)
    ded = []
    for s in out:
        if ded and ded[-1] == s:
            st['dup-adjacent'] += 1
            continue
        ded.append(s)
    with open(dst, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(ded) + '\n')
    print('files', nf, 'lines', len(out), '->dedup', len(ded))
    print('stats', dict(st))


if __name__ == '__main__':
    main()
