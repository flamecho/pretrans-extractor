# -*- coding: utf-8 -*-
"""ユア・メモリーズオフ～Girl's Style～ (PSP-JP, ULJM05435, MAGES. 2008)
SCENE00.AFS → 全文本提取。

载体：CRI AFS 归档（203 entries），每 entry = 一个场景块。
块内：二进制表（含名字池/立绘表）+ **文本池（NUL 分段）**。

记录（＝一次点击 = 一行）的判定：
    段内含终止命令  %K（通常）/ %W（演出框）/ %V（演出框）
    尾部 %P / %N 只是「清屏 / 续行」差异，均属同一次点击
    %K%p  = 该框之后紧跟选项；选项串本身无任何控制码
    %N %n = 框内软换行（同一框的多行用 NUL 分段，须拼接）
其余命令：%FS/%FE（字体）%S0xx/%O0xx（样式）%LC/%LE（色）%t0xx（歌词时序）%CFxxxx（色）
          %D（数值）%s/%d（格式串，仅系统块）
名札内嵌在记录首部：【海】… 【俊一＃】…（＃=心の声，(声)/(ラ) 等变体）；按规范剥离。

用法： python scripts/yourmo_extract.py [--afs <path>] [--out <txt>]
"""
import struct, re, os, argparse

CMD_RE = re.compile(
    r'%(?:KP|KN|Kp|FE|FS|LE|LC|S0\d\d|O0\d\d|t\d\d\d|CF[0-9A-Fa-f]{3,6}'
    r'|T[12]|[KPNpDnsdWV])'
)
# 记录终止命令（= 一次点击结束）
TERM_RE = re.compile(r'%[KWV]')

# 非剧情块（系统/调试/占位）——逐条已核
EXCLUDE_BLOCKS = {
    0:   '选项总池（330 条，327 与内嵌选项重复）+ 名字池',
    1:   '空/表',
    2:   '章节跳转说明（系统 UI）',
    3:   '空',
    4:   '分支名表（共通３月１日『天そば』…）+ 调试（タイトルＮｏ／選択肢Ｎｏ）',
    5:   '字体表（%CF/%CE）',
    6:   '立绘调试菜单（キャラクター%p / 服装 / 顔 / ポーズ）',
    7:   '立绘调试菜单',
    8:   '表', 9: '空', 10: '空', 11: '空', 12: '空', 13: '表',
    14:  '全是【%s】占位，无正文',
    15:  '全是【%s】占位，无正文',
    16:  '好感度 debug 提示 + 选项 debug 一览（２月１２日の選択肢…）',
    # 17 保留：内含序章夢境演出（%V 结尾的 %S064%FS%LC… 文本），
    #    只黑名单掉 3 条开发测试台词（录音指示），见 EXCLUDE_LINES
}

# 逐条黑名单（原文精确匹配）
EXCLUDE_LINES = {
    '「チェック、テス……」',
    '「すいません……やっぱり、ここは赤抜いて、青メインで切り替え少なめで」',
    '「あっやべ……なあ、ここってこっちでいくんだっけ？」',
}

NAME_RE = re.compile(r'^【[^】]{0,40}】')
GOOD_RE = re.compile(r'・(?:好感度|恋度) ?\+')
JP_RE = re.compile(r'[ぁ-んァ-ヶ一-龯]')
KANA_RE = re.compile(r'[ぁ-んァ-ヶー]')

# 原文笔误的**整行定值修复**（非正则泛修）。本作仅一处：
# blk68 秀巳台词缺结尾「」，原始记录即 `【秀巳】「けど、…悪くない気もしたよ%K%P`（下一框另起）
FIXUPS = {
    '「けど、春フェスみたいなでかいステージに、ああいう派手な、いかにも目立ちたがりなヤツがいるのも、けっこう、悪くない気もしたよ':
        '「けど、春フェスみたいなでかいステージに、ああいう派手な、いかにも目立ちたがりなヤツがいるのも、けっこう、悪くない気もしたよ」',
}


def clean(raw, stats):
    """一条原始记录 → 纯文本（返回 None 则丢弃）"""
    if GOOD_RE.search(raw):
        stats['drop_goodwill'] += 1
        return None
    if any(0xE000 <= ord(c) <= 0xF8FF for c in raw):
        stats['drop_pua'] += 1
        return None
    t = CMD_RE.sub('', raw)
    t = NAME_RE.sub('', t.strip())
    t = t.replace('├┤', '――')
    t = t.strip().strip('\u3000').strip()
    return t or None


def keep_line(line):
    """框文本合法性：挡掉块尾二进制碎片，保留纯标点/全角/英文台词"""
    if re.search(r'[\uff61-\uff9f]', line):        # 半角假名 = 化け/垃圾
        return False
    if re.search(r'[\x00-\x08\x0b-\x1f]', line):   # 控制符
        return False
    if JP_RE.search(line):
        return True
    if re.search(r'[…‥「」『』？！。、・―～]', line):
        return True
    if re.search(r'[\uff01-\uff60]', line):        # 全角标点/拉丁/数字
        return True
    # 纯 ASCII：英文信件/歌词（くーた 的书简），以「多词成句」为判据
    if len(line) >= 6 and ' ' in line:
        return True
    return False


def plausible(t):
    """续行段是否像正文（挡掉表区二进制碎片）"""
    if len(t) < 4 or len(KANA_RE.findall(t)) < 2:
        return False
    for c in t:
        o = ord(c)
        if 0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF or 0xFF01 <= o <= 0xFF60:
            continue
        if c in '、。「」『』（）()…‥―‐−─～〜！？!?・：；♪☆★○●◎◇◆□■△▲▽▼※→←↑↓℃\u3000':
            continue
        if 0x20 <= o <= 0x7E:
            continue
        return False
    return True


def extract(data, stats):
    n = struct.unpack('<I', data[4:8])[0]
    ents = [struct.unpack('<II', data[8 + 8 * i:16 + 8 * i]) for i in range(n)]
    lines = []
    for idx, (off, size) in enumerate(ents):
        if idx in EXCLUDE_BLOCKS:
            stats['skip_block'] += 1
            continue
        blk = data[off:off + size]
        segs, p = [], 0
        while p < len(blk):
            e = blk.find(b'\0', p)
            if e < 0:
                e = len(blk)
            segs.append(blk[p:e])
            p = e + 1
        # 文本池起点 = 第一个含终止命令的段（之前是名字池/表）
        first = None
        for k, s in enumerate(segs):
            if TERM_RE.search(s.decode('cp932', 'replace')):
                first = k
                break
        if first is None:
            stats['skip_block'] += 1
            continue
        # 向前回退：允许跳过「纯命令段/空段」，把夹在命令区里的内联正文纳入
        # （实证 blk199 3514 `【スタッフ１】「５・４・３――」%N`，其后 %O032 才是文本池）
        j, steps = first - 1, 0
        while j >= 0 and steps < 20:
            try:
                pt = segs[j].decode('cp932')
            except UnicodeDecodeError:
                break
            bare = CMD_RE.sub('', pt).strip().strip('\u3000').strip()
            if not bare:
                j -= 1
                steps += 1
                continue
            if JP_RE.search(bare) and len(bare) >= 4:
                first = j
                j -= 1
                steps += 1
                continue
            break
        buf = []
        pending_opt = False
        for k in range(first, len(segs)):
            seg = segs[k]
            if not seg:
                continue
            try:
                raw = seg.decode('cp932')
            except UnicodeDecodeError:
                stats['undecodable'] += 1
                continue
            # 终止判据：含 %K/%W/%V；或仅以 %N 收尾且带正文（blk199 スタッフ１「５・４・３――」%N）
            if TERM_RE.search(raw) or (raw.rstrip().endswith('%N')
                                       and JP_RE.search(CMD_RE.sub('', raw))):
                pending_opt = raw.rstrip().endswith('%p')
                t = clean(raw, stats)
                if t:
                    buf.append(t)
                line = ''.join(buf).strip().strip('\u3000').strip()
                buf = []
                if line and line in EXCLUDE_LINES:
                    stats['drop_junk'] += 1
                elif line and keep_line(line):
                    lines.append(line)
                    stats['say'] += 1
                elif line:
                    stats['drop_junk'] += 1

                continue
                continue
            if pending_opt:
                if not JP_RE.search(raw):
                    continue
                t = clean(raw, stats)
                if not t or t.startswith('【'):
                    pending_opt = False
                    continue
                lines.append(t)
                stats['opt'] += 1
                continue
            # 同一框的续行（框内软换行 / 样式命令夹在中间）
            t = clean(raw, stats)
            if t and plausible(t):
                buf.append(t)
                stats['cont'] += 1
    return [FIXUPS.get(l, l) for l in lines]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--afs', default='_src_yourmo/PSP_GAME/USRDIR/SCENE00.AFS')
    ap.add_argument('--out', default='提取结果/ユア・メモリーズオフ_全文本.txt')
    a = ap.parse_args()
    stats = dict(skip_block=0, undecodable=0, drop_goodwill=0, drop_pua=0,
                 say=0, opt=0, cont=0, drop_junk=0)
    data = open(a.afs, 'rb').read()
    lines = extract(data, stats)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8-sig', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('lines=%d  say=%d opt=%d cont_merged=%d' % (len(lines), stats['say'],
                                                     stats['opt'], stats['cont']))
    print('dropped: goodwill=%d pua=%d junk=%d undecodable_seg=%d skipped_blocks=%d'
          % (stats['drop_goodwill'], stats['drop_pua'], stats['drop_junk'],
             stats['undecodable'], stats['skip_block']))
    print('out:', a.out)


if __name__ == '__main__':
    main()
