# -*- coding: utf-8 -*-
"""[JP]TameBoy（「シナリオくん」1.9x ／ .st1）全文本提取驱动。

链路：RAR5 SFX(otoame) → tameboy.exe → シナリオのデータ/*.st1（cp932 明文 XOR 0x65）
      → 命令解析 → 「一次文本显示＝一框＝一行」成行。

L0 判据（见 memory `engines/scenario-kun.md` §4）：
  · 一条 `＃セリフ`（或 `＃文字` 起头的新文本）＝一次显示＝一次点击＝一个框；
    其后的**连续正文行是该框的排版折行 ⇒ 合并进同一行**。
  · `追加` 参数（`＃セリフ 追加` / `＃文字 … 追加`）＝**并入上一框**（不另计点击）⇒ 仍是一行。
  · `＃セリフオフ` / `＃人物` / `＃絵` / `＃音` / `＃時間待ち` / `＃選択` 等命令＝结束当前框。
  · `＃選択` 后的正文行＝选项（一行一条）。
  · `＃クリック待ち`：本作全部紧跟图像/人物命令（CG 鉴赏等的「点击换图」），
    **不在任何文本框内部** ⇒ 不构成「一框多次点击」。

用法：
    python scripts/tameboy_extract.py --src "<[JP]TameBoy 目录>" --verify
    python scripts/tameboy_extract.py --src "<...>" --out "提取结果/[JP]TameBoy.txt"
"""
import argparse
import os
import re

# 流程顺序：平賀１ 的调度链（プロローグ→真夜中→初オナニー→初日から→1..7日目→イベント判定→エンディング判定），
# 分支剧本按选项顺序；CG 场景脚本按其首次被日程脚本引用的顺序；最后是标题菜单的人物紹介。
FLOW = [
    'プロローグ', '過去', '真夜中の秘め事', '初オナニー', '初日から', '優しくお初', '激しくお初',
    '１日目', '２日目', '３日目', '４日目', '５日目', '６日目', '７日目',
    'ふたば１日目', 'ふたば２日目', 'ふたば３日目', 'ふたば４日目', 'ふたば５日目', 'ふたば６日目', 'ふたば７日目',
    'わかば１日目', 'わかば２日目', 'わかば３日目', 'わかば４日目', 'わかば５日目', 'わかば６日目', 'わかば７日目',
]
CG_ORDER = [
    'ふたばバイブ１', 'ふたば自慰１', 'ふたばフェラ１', 'ふたばフェラ２', 'ふたば服愛撫１', 'ふたば服愛撫２',
    'ふたばみみ', 'ふたばうなじ１', 'ふたばなめ乳首１', 'ふたば舐めちん１',
    'ふたば正常位１', 'ふたば正常位２', 'ふたば正常位３', 'ふたば後背位１', 'ふたば後背位２',
    'ふたば騎乗位１', 'ふたば座位１', 'ふたば座位２', 'ふたば座位３',
    'わかばバイブ', 'わかばバイブ無', 'わかばオナニー', 'わかばフェラ', 'わかば６９', 'わかば愛撫', 'わかばちん',
    'わかば正常位', 'わかば正常位無', 'わかば後背位', 'わかば騎乗位', 'わかば騎乗位無', 'わかば座位',
]
TAIL = ['イベントＡ', 'イベントＢ', 'イベントＣ', 'イベントＤ', '家出', 'イベントＰ', 'イベントＷ',
        'エンドＡ', 'エンドＢ', 'エンドＣ', 'エンドＤ', 'おまけモード', 'メイド３Ｐ', '人物紹介']

# 系统 UI / 判定 / 变量初始化 / 画廊（不含正文）
EXCLUDE = ['アルバム', 'セーブしよう', 'イベント判定', 'エンディング判定',
           'パラメータ変数初期化', '完全変数初期化', '平賀１',
           'ふたば表情集', 'ふたばおでかけ表情集', 'ふたばえっちＣＧ', 'ふたばその他ＣＧ',
           'わかば表情集', 'わかばえっちＣＧ', 'わかばその他ＣＧ', 'その他ＣＧ']

TEXT_START = ('＃セリフ',)
TEXT_INLINE = ('＃文字',)
TEXT_WIN = ('＃文章',)


def decode(path):
    """XOR 0x65；★ 必须先把密文的 CRLF 折叠为 LF（写入端文本模式膨胀，见引擎册 §2）"""
    c = open(path, 'rb').read().replace(b'\r\n', b'\n')
    return bytes(b ^ 0x65 for b in c).decode('cp932', 'replace')


def head(line):
    return line.strip().split('\t')[0]


def args(line):
    parts = line.strip().split('\t')
    return [x for x in parts[1:] if x]


def body_lines(lines, i):
    """取命令后的连续正文行：遇到空行或下一条 ＃命令即停（空行是命令分隔符，
    绝不能把后面的变量赋值行（`ふたば快楽＝…`）或参数行吞进正文）"""
    out = []
    j = i + 1
    while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('＃'):
        s = lines[j].strip('\u3000 \t\r\n')
        if s:
            out.append(s)
        j += 1
    return out, j


def parse_script(text, skip_staffroll=True):
    """返回 (units, stats)；units: [{kind: 'text'/'opt', text}]"""
    lines = text.split('\n')
    units = []
    cur = None            # 当前文本框（字符串列表）
    stats = {'click_in_box': 0, 'new_box': 0, 'append': 0, 'empty': 0}

    def flush():
        nonlocal cur
        if cur:
            s = ''.join(cur).replace('\t', '').strip('\u3000 ')
            if s:
                units.append({'kind': 'text', 'text': s})
            else:
                stats['empty'] += 1
        cur = None

    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith('／／') or s.startswith('//'):
            i += 1
            continue
        if not s.startswith('＃'):
            # 自由正文（只在 ＃選択 块内被当成选项；其余忽略）
            i += 1
            continue
        h = head(lines[i])
        a = args(lines[i])
        add = '追加' in a

        if h == '＃選択':
            flush()
            opts, j = body_lines(lines, i)
            for o in opts:
                units.append({'kind': 'opt', 'text': o})
            i = j
            continue
        if h in ('＃セリフ', '＃文字'):
            body, j = body_lines(lines, i)
            if h == '＃文字' and cur is not None:
                cur.extend(body); stats['append'] += 1   # 同框行内特效
            elif add and cur is not None:
                cur.extend(body); stats['append'] += 1   # 追加（可跨演出命令）
            elif add and cur is None and units and units[-1]['kind'] == 'text':
                units[-1]['text'] += ''.join(body); stats['append'] += 1
            else:
                flush(); cur = list(body); stats['new_box'] += 1
            i = j
            continue
        if h == '＃文章':
            body, j = body_lines(lines, i)
            if add and cur is not None:
                cur.extend(body); stats['append'] += 1
            else:
                flush(); cur = list(body); stats['new_box'] += 1
            i = j
            continue
        if h in ('＃文章オフ', '＃セリフオフ'):
            flush()
            i += 1
            continue
        if h in ('＃クリック待ち', '＃時間待ち'):
            # 两者都在「本次显示的文本已出现」之后等待（点击/定时），随后由下一条文本开始新框
            # ⇒ 不是「同一框内再点一次」；本作没有任何 `＃クリック待ち` 后紧跟 `追加` 的情形。
            flush()
            i += 1
            continue
        # 其它命令：不结束文本框（追加可能跨演出命令）；仅当出现新文本/选择/关闭时结算
        i += 1
    flush()
    if skip_staffroll:
        before = len(units)
        units = [u for u in units
                 if not ('キャラ設定・ＣＧ' in u['text'] or 'ＥＮＤ　Ｎｏ' in u['text']
                         or 'シナリオ・演出' in u['text'])]
        stats['staff_drop'] = before - len(units)
    else:
        stats['staff_drop'] = 0
    return units, stats


def parse_start_demo(text):
    """start.st1：只取 `＃ラベル オープニングデモ` → `＃ラベル タイトルへ` 之间的文本（标题菜单/存档说明不收）"""
    lines = text.split('\n')
    lo = hi = None
    for i, l in enumerate(lines):
        if l.strip() == '＃ラベル' and i + 1 < len(lines) and lines[i + 1].strip() == 'オープニングデモ':
            lo = i
        elif l.strip() == '＃ラベル' and i + 1 < len(lines) and lines[i + 1].strip() == 'タイトルへ':
            hi = i
            break
    if lo is None:
        return [], {'click_in_box': 0}
    return parse_script('\n'.join(lines[lo:hi if hi else len(lines)]), skip_staffroll=False)


def delta(s):
    return [s.count('「') - s.count('」'), s.count('（') - s.count('）')]


def main():
    ap = argparse.ArgumentParser(description='[JP]TameBoy（シナリオくん .st1）文本提取')
    ap.add_argument('--src', required=True, help='[JP]TameBoy 目录（含 シナリオのデータ/）')
    ap.add_argument('--out')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--keep-name', action='store_true', default=True,
                    help='名前行保留内联（本引擎无独立名字窗证据；默认保留）')
    a = ap.parse_args()

    sce = os.path.join(a.src, 'シナリオのデータ')
    st = os.path.join(a.src, 'start.st1')
    all_units = []
    per = []

    def add(units, tag):
        for u in units:
            u['file'] = tag
            all_units.append(u)
        per.append((tag, sum(1 for u in units if u['kind'] == 'text'),
                    sum(1 for u in units if u['kind'] == 'opt')))

    demo, demo_st = parse_start_demo(decode(st)) if os.path.isfile(st) else ([], {'click_in_box': 0})
    add(demo, 'start.st1(デモ)')
    agg = {'click_in_box': 0, 'new_box': 0, 'append': 0, 'empty': 0, 'staff_drop': 0}
    for k, v in demo_st.items():
        agg[k] = agg.get(k, 0) + v

    for name in FLOW + CG_ORDER + TAIL:
        p = os.path.join(sce, name + '.st1')
        if not os.path.isfile(p):
            print('  ⚠ 缺剧本', name)
            continue
        units, st2 = parse_script(decode(p))
        for k, v in st2.items():
            agg[k] = agg.get(k, 0) + v
        add(units, name)
    click_in_box = agg['click_in_box']

    # 校验：缺失/未处置
    allfiles = {f[:-4] for f in os.listdir(sce) if f.endswith('.st1')}
    used = set(FLOW + CG_ORDER + TAIL)
    missing = sorted(allfiles - used - set(EXCLUDE))
    extra = sorted(used - allfiles)
    print('剧本文件 %d 个：使用 %d / 排除 %d（%s）' % (
        len(allfiles), len(used & allfiles), len(set(EXCLUDE) & allfiles), '、'.join(EXCLUDE)))
    if missing:
        print('  ⚠ 未处置文件：', missing)
    if extra:
        print('  ⚠ 清单里不存在的文件：', extra)

    # 双版判定：
    #   ① 一框多次点击＝`＃クリック待ち` 落在文本框内部（本作 0，见引擎册 §4）
    #   ② 跨行开口（「/（ 未闭合）：本作存在，但逐条核对源码后全部是**不同 ＃セリフ 框**
    #      （作者把一句拆到两次点击），若合并即造假「同框」⇒ 按用户口径**不合并**，只列段行
    groups = []
    i = 0
    while i < len(all_units):
        dq, dp = delta(all_units[i]['text'])
        if dq > 0 or dp > 0:
            gd = [dq, dp]; j = i + 1
            while j < len(all_units) and (gd[0] > 0 or gd[1] > 0) and j - i < 4:
                d2 = delta(all_units[j]['text'])
                gd[0] += d2[0]; gd[1] += d2[1]; j += 1
            if gd[0] == 0 and gd[1] == 0 and j - i >= 2:
                groups.append((i, j))
                i = j; continue
        i += 1
    unbal = [(k, u) for k, u in enumerate(all_units) if delta(u['text'])[0] != 0 or delta(u['text'])[1] != 0]
    print('同框多点击（＃クリック待ち 在框内）%d 处；跨框开口组 %d / 未平衡行 %d ⇒ %s' % (
        click_in_box, len(groups), len(unbal),
        '双版' if click_in_box else '单版（跨框开口组不合并）'))
    for (s, e) in groups:
        a1 = all_units[s]['text']
        b1 = all_units[e - 1]['text']
        print('  跨框组 #%d-#%d [%s] %r … %r' % (s, e - 1, all_units[s]['file'], a1[:34], b1[-34:]))

    lines = [u['text'] for u in all_units]

    print('--- 逐本（文本 / 选项）---')
    for tag, nt, no in per:
        if nt or no:
            print('  %-22s text=%-4d opt=%d' % (tag, nt, no))
    print('合计 %d 行 / %d 字（文本 %d ＋ 选项 %d）' % (
        len(lines), sum(len(x) for x in lines),
        sum(1 for u in all_units if u['kind'] == 'text'),
        sum(1 for u in all_units if u['kind'] == 'opt')))
    text_units = sum(1 for u in all_units if u['kind'] == 'text')
    print('自证：新起框 %d － 空框 %d － staff roll/剔除 %d ＝ 文本 %d（追加合并 %d 次并入）'
          % (agg['new_box'], agg['empty'], agg['new_box'] - agg['empty'] - text_units,
             text_units, agg['append']))

    if a.out and not a.verify:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, 'wb') as f:
            f.write(b'\xef\xbb\xbf' + ''.join(x + '\n' for x in lines).encode('utf-8'))
        print('写出 %s（%d B）' % (a.out, os.path.getsize(a.out)))


if __name__ == '__main__':
    main()
