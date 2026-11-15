#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[NS-JP]十鬼の絆 (Bond Of Ten Oni) STCM2L 文本提取。

【2026-10-28 实证结构】
容器：XCZ -> nsz -D -> XCI -> HCA(romfs; keygen=18, KAEK_17 槽2) -> common/stcm2/vol{1,2}/N
脚本：STCM2L（CP932；"STCM2L Apr 12 2018 ..."）
  文本记录 = [u32 0][u32 cnt][u32 1][u32 cnt*4][cp932 文本，尾 NUL 补足 cnt*4]
           sizeof = 16 + cnt*4，紧跟 16 字节 tag [a][tag][b][0x10]
  tag: 0x43 / 0x44 / 0x46 = 正文；0x01 = 标签「色変化判定」；0x3b/0x3e = 调试「処理開始」
  两条记录之间的 gap（不含后一条的 tag）：
    [0][0xD2][1][len][ptr][0xffffffff][0xffffffff]  => 同框续行（框内换行）
    [0][0xD3][0][0x20][2]...                        => 新框（= 一次点击）
  名札：新框首条记录、短、无人名标点、下一条为 d2 续行 => 独立名字窗 => 剔除
  富文本：#Color[n] / #Ruby[..] / #Name[0]（主角名内联）=> 剥标记、换名
用法:
  python scripts/oni_extract.py --dump          # 打印中间统计/抽样
  python scripts/oni_extract.py --out 提取结果/x.txt
"""
import argparse
import collections
import os
import re
import struct
import sys

SRC = '_w_oni/src/common/stcm2'
JP = re.compile(r'[\u3040-\u30ff\u4e00-\u9fff]')
HERO = '雪奈'          # #Name[0]
# vol1/0 的名字表（idx → 名字）：`#Name[n]` 就查这张表，别再猜
NAME_TAB = {0: '雪奈', 1: '千歳', 2: '千耶', 3: '千岳', 4: '秦', 5: '汐見爺', 6: '琴浦爺',
            7: '月島爺', 8: '千鬼丸', 9: '酒呑童子', 10: '八千代', 11: '秀', 12: '千羽',
            13: '徳川家康', 14: '石田三成', 15: '本多正信', 17: '島津豊久', 18: '島津義弘',
            19: '毛利元康', 20: '嶋左近', 21: 'その他'}
RE_TAG = re.compile(r'#(?:Color|Ruby|Kana|Name)\[[^\]]*\]')
RE_COLOR = re.compile(r'#Color\[\d+\]')
RE_RUBY = re.compile(r'#Ruby\[([^,\]]*),([^\]]*)\]')
RE_NAME0 = re.compile(r'#Name\[(\d+)\]')
TAG_TEXT = {0x43, 0x44, 0x46}
RES = re.compile(r'^[0-9A-Za-z_\-\.]+$')
# 章题「内部 ID」形态：含半角/全角阿拉伯数字 + 「章」，如「１章前０１」「千歳２章」「７章千歳０１」
RE_CHAP_ID = re.compile(r'^(?=.*[\d０-９])(?=.*章).{1,10}$')
# 变量名 / 解锁旗标名（`Ａルートフラグ１` `ルート判定Ｂ` `千歳end` `r_千歳end` `s_ノーマルopen`）
RE_FLAG = re.compile(r'(?:フラグ|ルート判定|画廊|解放$)|(?:end|ed|open)$|ルート$')
SKIP_REC = {('vol1/100', 0x1a218)}   # 「序章」：跳过序章确认弹窗的标题（与章题卡重复）
CONT = 0xD2          # 续行
NEW = 0xD3           # 新框


def load(path):
    """读全部文本记录，两种操作数形态都要收。

    A) 常规：前缀 `[slot][tag][seq][0x10]` + 串 `[0][cnt][1][cnt*4][cp932]`
    B) 引用：前缀 + `[0][1][1][4][串ID]` + 串 + **续行串** `[0][0][cnt][1][len][cp932]`（可多条）
       —— 早先只认 A，导致 B 形态的整框丢失（实测 vol1/105 @0x1aa7c：
       `「よう#Name[0]、　このクソ暑いのに…　薪割り、はかどってるか？」` 三行整框不见了）。
    返回 (串起点, cnt等价, 文本, tag, 是否自成整框)。
    """
    d = open(path, 'rb').read()
    n = len(d)
    out = []
    i = 0
    while i + 48 <= n:
        z, c, one, bl = struct.unpack_from('<IIII', d, i)
        if z == 0 and one == 1 and 1 <= c <= 0x200 and bl == c * 4 and i + 16 + bl <= n:
            tag = struct.unpack_from('<I', d, i - 12)[0]
            selfbox = False
            if tag not in TAG_TEXT and i >= 40:
                # B 形态：引用块 + 前缀在更前面
                # 布局：前缀16B [slot][tag][seq][0x10] + 引用块20B [0][1][1][4][串ID] + 串
                if struct.unpack_from('<IIII', d, i - 20) == (0, 1, 1, 4) \
                        and struct.unpack_from('<I', d, i - 24)[0] == 0x10 \
                        and struct.unpack_from('<I', d, i - 32)[0] in TAG_TEXT:
                    tag = struct.unpack_from('<I', d, i - 32)[0]
                    selfbox = True
            if tag in TAG_TEXT:
                segs = []
                k = i
                while k + 16 <= n:
                    zz, cc, oo, bb = struct.unpack_from('<IIII', d, k)
                    t = None
                    adv = 0
                    if zz == 0 and oo == 1 and 1 <= cc <= 0x200 and bb == cc * 4:
                        try:
                            t = d[k + 16:k + 16 + bb].decode('cp932').rstrip('\x00')
                        except UnicodeDecodeError:
                            t = None
                        adv = 16 + bb
                    elif (zz, cc) == (0, 0) and k + 20 <= n:
                        # 20 字节续行形态：[0][0][cnt][1][len][text]
                        c3, d3 = struct.unpack_from('<II', d, k + 8)
                        ln = struct.unpack_from('<I', d, k + 16)[0]
                        if c3 and d3 == 1 and 0 < ln <= 0x800 and k + 20 + ln <= n:
                            try:
                                t = d[k + 20:k + 20 + ln].decode('cp932').rstrip('\x00')
                            except UnicodeDecodeError:
                                t = None
                            adv = 20 + ln
                    if t is None:
                        break
                    # 首段本身不含日文（`0R` 这类字库/杂项串）⇒ 整条都不是正文，也不许往后链
                    if not segs and not JP.search(t):
                        break
                    # ★ 续行判据（宁严不宽，避免把字库/杂项串并进来：`襲` `0R` `)w` `|v` `蛆`）：
                    #   ① 以全角空格缩进开头（最常见）；或 ② 以句读/开引号开头（上一段以「、」或「…」收尾时）；
                    #   或 ③ 上一段明显未完（以 `、`/`…`/`―` 收尾）且本段含日文。
                    if segs:
                        pv = segs[-1]
                        ok = t[:1] in ('\u3000', '、', '。', '（', '『', '「', '【')
                        if not ok and pv[-1:] in ('、', '…', '―', ',') and len(t) >= 2 and JP.search(t):
                            ok = True
                        if not ok:
                            break
                    segs.append(t)
                    k += adv
                    if k + 16 <= n and struct.unpack_from('<I', d, k + 12)[0] == 0x10 \
                            and struct.unpack_from('<I', d, k + 4)[0] in TAG_TEXT:
                        break
                stxt = ''.join(segs)
                # ★ 名字变体：源里成对出现「彼女が持っていた刀は…」/「雪奈が持っていた刀は…」，
                #   前者是玩家改过名时的写法、后者是默认名写法。既然 #Name[0] 已代入默认名 `雪奈`，
                #   这里也取默认名那版（仅当同域内确实存在该变体时才换，不做全局替换）。
                if '彼女' in stxt:
                    alt = stxt.replace('彼女', '雪奈')
                    try:
                        if alt.encode('cp932') in d[max(0, i - 0x40):i + 0x300]:
                            stxt = alt
                    except UnicodeEncodeError:
                        pass
                if stxt and JP.search(stxt) and not RES.match(stxt) and not any(ord(ch) < 0x20 for ch in stxt):
                    out.append((i, (k - i - 16) // 4, stxt, tag, selfbox))
                    i = k
                    continue
        i += 4
    return d, out


def classify(mid):
    """mid = 上一条记录 end .. 本条 tag 起点。"""
    if not mid:
        return 'adj'
    if len(mid) >= 8:
        v = struct.unpack_from('<II', mid, 0)
        if v[0] == 0 and v[1] == CONT:
            return 'cont'
        if v[0] == 0 and v[1] == NEW:
            return 'new'
        if v[0] == 0 and v[1] == 0xE7:
            return 'opt'
    return 'other:' + mid[:12].hex()


def _shape_ok(s):
    if not s or len(s) > 8:
        return False
    if any(ch in '「」『』（）()、。！？…―・' for ch in s):
        return False
    return all('\u3040' <= ch <= '\u30ff' or '\u4e00' <= ch <= '\u9fff' or ch == '　' for ch in s)


def is_name(s, nxt, nxt_text=None):
    """名札 = 新框首条 + 人名形态 + 下一条是**以「（『开头的同框续行**（＝台词/心声框首段）。

    实测：`秦` → `「その出雲国も、…` (cont)；反例 `あの時感じた事を` → `　思い出していた。`
    —— 正文框首段同样是「短、无标点、后接续行」，只靠 nxt=='cont' 会把它当名札删掉（曾误删 800+ 条）。
    """
    if not _shape_ok(s) or any(ch in '章編序' for ch in s):
        return False
    return nxt == 'cont' and bool(nxt_text) and nxt_text[:1] in '「（『'


def _is_name_cell(t, names):
    return t and len(t) > 1 and t in names and _shape_ok(t) and not any(ch in '章編序' for ch in t)


def _paired(recs, k, names):
    """相邻的人名记录是否构成「选谁」选项组。

    两组反例都要区分（2026-10-28 实测）：
      · 选项组：`千歳/千耶/千岳/秦` 之后接 **章题或正文**（`四章前編`）⇒ 保留；
      · 名札对：`徳川　家康/本多　正信` 之后紧接 **台词「…」** ⇒ 两条都是名札，删。
    判据＝**人名组之后第一条正文是否以「开头**。
    """
    i, j = k, k
    me = recs[k][2]
    while i - 1 >= 0 and recs[i - 1][2] != me and _is_name_cell(recs[i - 1][2], names):
        i -= 1
    while j + 1 < len(recs) and recs[j + 1][2] != me and _is_name_cell(recs[j + 1][2], names):
        j += 1
    if i == j:
        return False
    nxt = recs[j + 1][2] if j + 1 < len(recs) else ''
    return not nxt.startswith('「')


def build_names(files):
    """高置信名札集合：出现在新框首条、形态合格、下一条为 cont。"""
    names = set()
    for p in files:
        d, recs = load(p)
        for k, (off, c, s, tag, _sb) in enumerate(recs):
            if k + 1 >= len(recs):
                continue
            mid = b'' if k == 0 else d[recs[k - 1][0] + 16 + recs[k - 1][1] * 4:off - 16]
            if classify(mid) in ('cont', 'adj'):
                continue
            nxt = classify(d[off + 16 + c * 4:recs[k + 1][0] - 16])
            if is_name(s, nxt, recs[k + 1][2]):
                names.add(s)
    return names


def clean(s):
    s = RE_RUBY.sub(lambda m: m.group(1), s)
    s = RE_COLOR.sub('', s)
    s = RE_NAME0.sub(lambda m: NAME_TAB.get(int(m.group(1)), ''), s)
    s = RE_TAG.sub('', s)
    return s


def walk(files, dump=False, names=frozenset()):
    lines = []
    stats = collections.Counter()
    for p in files:
        d, recs = load(p)
        key = os.path.basename(os.path.dirname(p)) + '/' + os.path.basename(p)
        cur = None          # 当前框的记录列表
        optmode = False     # 处在选项组内（首项 mid=0xE7，组内其余项 mid=变量设置）
        for k, (off, c, s, tag, _sb) in enumerate(recs):
            mid = b'' if k == 0 else d[recs[k - 1][0] + 16 + recs[k - 1][1] * 4:off - 16]
            kind = classify(mid)
            nxt = None
            nxt_text = None
            if k + 1 < len(recs):
                nxt = classify(d[off + 16 + c * 4:recs[k + 1][0] - 16])
                nxt_text = recs[k + 1][2]
            if (key, off) in SKIP_REC or RE_CHAP_ID.match(s) or (len(s) <= 14 and RE_FLAG.search(s)):
                stats['skip'] += 1
                if kind not in ('cont', 'adj') and cur is not None:
                    lines.append(''.join(cur))
                    cur = None
                continue
            if kind not in ('cont', 'adj') and cur is not None:
                lines.append(''.join(cur))
                cur = None
            if kind == 'opt':
                optmode = True
            elif kind in ('new', 'cont') or '章' in s or '編' in s:
                optmode = False
            if len(s) == 1 and s not in names:
                # 单字记录＝字库/名札变体槽（`丐` 紧贴 `秦` 名札之前；`あ` `づ` `ク` 等为字符表）
                stats['single'] += 1
                if kind not in ('cont', 'adj') and cur is not None:
                    lines.append(''.join(cur))
                    cur = None
                continue
            # 名札：① 后接同框续行（最强，不受选项组状态影响）② 白名单 + 孤立（名札独占一框）
            # 名札：① 后接同框续行（强判据，不受选项组影响）② 白名单 + 孤立
            if kind not in ('cont', 'adj') and (
                    is_name(s, nxt, nxt_text) or (
                        not _paired(recs, k, names) and s in names and _shape_ok(s)
                        and not any(ch in '章編序' for ch in s))):
                stats['name'] += 1
                continue
            # ★ 名札副本：同一条名札在源里常出现两次（vol2/354 @0x20a74 与 @0x20ecc 都是 `千鬼丸`），
            #   第一条按「后接续行」删掉后，第二条 mid=cont 会被当正文并吞掉后面整句心声。
            #   判据：本框还没有正文（cur 为空）+ 文本∈名单 + 前后无别的角色 ⇒ 仍是名札。
            if (cur is None and s in names and _shape_ok(s)
                    and not any(ch in '章編序' for ch in s)
                    and not _paired(recs, k, names)):
                stats['name'] += 1
                continue
            if cur is None:
                cur = [clean(s).lstrip('　')]
            else:
                cur.append(clean(s).lstrip('　'))
            stats['rec'] += 1
            stats['k_' + kind.split(':')[0]] += 1
            if dump and stats['rec'] <= 40:
                print('%-6s %s %-8s %r' % (os.path.basename(os.path.dirname(p)) + '/' + os.path.basename(p),
                                          hex(off), kind, s[:40]))
        if cur:
            lines.append(''.join(cur))
    # ★ 相邻完全相同的行：if/else 互斥分支各排一份（本作 36 处），只留一版。
    out = []
    for x in lines:
        if out and out[-1] == x:
            stats['dup'] += 1
            continue
        out.append(x)
    # ★ 名札被并入正文（`千岳「…」` / `千歳千歳「…」` / `千歳＆千耶「…」`）：去前缀保留引号
    RE_LEAD = re.compile(r'^([^\s「」（）]{1,16})「(.*)$')
    fixed = []
    for x in out:
        m = RE_LEAD.match(x)
        if m:
            lead = m.group(1)
            core = re.sub(r'^(.{2,8})\1$', r'\1', lead)          # 千歳千歳 -> 千歳
            parts = core.split('＆')
            if all(pt in names for pt in parts) and not any(ch in '章編序' for ch in core):
                stats['inline_name'] += 1
                x = '「' + m.group(2)
        fixed.append(x)
    out = fixed
    # ★ 孤立人名行（名札独占一框、前后都是正文）：删；
    #   连续 ≥2 个**不同**人名 ⇒ 「选谁」选项组，保留。
    res, i = [], 0
    while i < len(out):
        if out[i] in names:
            j = i
            while j < len(out) and out[j] in names:
                j += 1
            grp = out[i:j]
            if len(set(grp)) >= 2 and res and res[-1].rstrip().endswith(('？', '?')):
                res.extend(grp)          # 「选谁」选项组（前一行是问句）
            else:
                stats['name_iso'] += len(grp)
            i = j
            continue
        res.append(out[i])
        i += 1
    return [x for x in res if x.strip()], stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dump', action='store_true')
    ap.add_argument('--out')
    a = ap.parse_args()
    files = []
    for vol in ('vol1', 'vol2'):
        dd = os.path.join(SRC, vol)
        if not os.path.isdir(dd):
            continue
        for f in sorted(os.listdir(dd), key=lambda x: (len(x), x)):
            # 0..5 = 系统/变量表/ED・画廊解锁表，无正文
            if f.isdigit() and int(f) < 100:
                continue
            files.append(os.path.join(dd, f))
    print('[i] files', len(files))
    names = build_names(files)
    print('[i] 名札白名单', len(names), sorted(names)[:12])
    lines, stats = walk(files, a.dump, names)
    print('[i] stats', dict(stats))
    print('[i] lines', len(lines), 'chars', sum(len(x) for x in lines))
    longest = sorted(lines, key=len)[-3:]
    for x in longest:
        print('[max] %d %s' % (len(x), x[:80]))
    if a.out:
        with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as f:
            f.write('\n'.join(lines) + '\n')
        print('[ok]', a.out)


if __name__ == '__main__':
    main()
