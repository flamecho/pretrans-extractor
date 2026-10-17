# -*- coding: utf-8 -*-
"""裏語 薄桜鬼 (PSP ULJM06281) 剧本提取器 —— LZO1X 解压版
引擎: Design Factory + Zerodiv 自研

容器链: ISO9660 -> PSP_GAME/USRDIR/UMD.CPK -> event.enc (248 个 .evt 脚本)
event.enc: u32 count + 12B/条 {u32 size|0x80000000(压缩标志), u32 size2(解压后大小), u32 offset}
           entry 数据经 LZO1X-1 解压后 = 指令流
指令格式: [u32 cmd][u32 len][len 字节 data]
  cmd=0x2f  台词正文
  cmd=0x21  选项
  cmd=0x2d  说话人名 (按规范丢弃, 不加前缀)
  cmd=0x2e  地の文 (ナレーション/年表) —— **只收叙事句**, 系统/任务/道具/技能消息不收
  cmd=0x31/0x20 名字输入用字库 (不收)
文本: cp932, 以 00 00 结尾; 控制码 @<n>r 为着色标记; &pcl = 主角名(默认「梢」)
"""
import sys, os, struct, re, io
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())


def lzo1x_decompress(src, out_len):
    out = bytearray(out_len)
    op = 0
    ip = 0

    def ensure(k):
        if op + k > len(out):
            out.extend(b'\x00' * (op + k - len(out) + 4096))

    def copy_lit(cnt):
        nonlocal ip, op
        ensure(cnt)
        out[op:op + cnt] = src[ip:ip + cnt]
        op += cnt
        ip += cnt

    def copy_match(mpos, cnt):
        nonlocal op
        ensure(cnt)
        for _ in range(cnt):
            out[op] = out[mpos]
            op += 1
            mpos += 1

    if src[ip] > 17:
        t = src[ip] - 17
        ip += 1
        if t < 4:
            copy_lit(t)
            t = src[ip]; ip += 1
            state = 'match'
        else:
            copy_lit(t)
            state = 'first_literal_run'
    else:
        state = 'literal_run'
    while True:
        if state == 'literal_run':
            t = src[ip]; ip += 1
            if t >= 16:
                state = 'match'; continue
            if t == 0:
                while src[ip] == 0:
                    t += 255; ip += 1
                t += 15 + src[ip]; ip += 1
            copy_lit(t + 3)
            state = 'first_literal_run'; continue
        if state == 'first_literal_run':
            t = src[ip]; ip += 1
            if t >= 16:
                state = 'match'; continue
            mpos = op - 1 - 0x800 - (t >> 2) - (src[ip] << 2); ip += 1
            ensure(3)
            out[op] = out[mpos]; out[op + 1] = out[mpos + 1]; out[op + 2] = out[mpos + 2]
            op += 3
            t = src[ip - 2] & 3
            if t:
                copy_lit(t)
            state = 'literal_run'; continue
        if t >= 64:
            mpos = op - 1 - ((t >> 2) & 7) - (src[ip] << 3); ip += 1
            copy_match(mpos, ((t >> 5) - 1) + 2)
        elif t >= 32:
            t &= 31
            if t == 0:
                while src[ip] == 0:
                    t += 255; ip += 1
                t += 31 + src[ip]; ip += 1
            mpos = op - 1 - ((src[ip] >> 2) + (src[ip + 1] << 6)); ip += 2
            copy_match(mpos, t + 2)
        elif t >= 16:
            mpos = op - ((t & 8) << 11)
            t &= 7
            if t == 0:
                while src[ip] == 0:
                    t += 255; ip += 1
                t += 7 + src[ip]; ip += 1
            mpos -= (src[ip] >> 2) + (src[ip + 1] << 6); ip += 2
            if mpos == op:
                break
            mpos -= 0x4000
            copy_match(mpos, t + 2)
        else:
            mpos = op - 1 - (t >> 2) - (src[ip] << 2); ip += 1
            copy_match(mpos, 2)
        t = src[ip - 2] & 3
        if t:
            copy_lit(t)
            t = src[ip]; ip += 1
            state = 'match'
        else:
            state = 'literal_run'
    return bytes(out[:op])


TEXT_CMD = 0x2f      # 台词
OPT_CMD = 0x21       # 选项
NAME_CMD = 0x2d      # 说话人名
SYS_CMD = 0x2e       # 无说话人的文本框: 地の文(收) + 系统/任务/道具/技能消息(不收)
PCL = '梢'           # 主角默认名 (EBOOT 0x1c4308)
AT = re.compile(r'@\d+[a-z]')
LAT = lambda ch: bool(ch) and (0xFF10 <= ord(ch) <= 0xFF19      # 全角数字 ０-９
                               or 0xFF21 <= ord(ch) <= 0xFF3A  # 全角大写 Ａ-Ｚ
                               or 0xFF41 <= ord(ch) <= 0xFF5A)  # 全角小写 ａ-ｚ
# ⚠ 只含**字母/数字**：全角标点(！？，／ 等 U+FF01-FF0F)不参与 —— 否则日文「！　」后的折行空格会被误留

# ── 本引擎的 opcode 表（同一引擎，不同作品整体平移） ──────────────────
# 无印版 → 暁の調べ：台词/选项/人名/无说话人文框 **全部 +5**
#   (0x2f→0x34, 0x21→0x26, 0x2d→0x32, 0x2e→0x33；字库 0x31/0x20→0x36/0x25)
OPCODES = {
    # txt=台词 opt=选项 name=说话人名 sys=无说话人文框(地の文/系统消息) font=名字输入用字库
    'urakata':  dict(txt=0x2f, opt=0x21, name=0x2d, sys=0x2e, font=(0x31, 0x20)),
    'akatsuki': dict(txt=0x34, opt=0x26, name=0x32, sys=0x33, font=(0x36, 0x25)),
}
DEBUG_KW = {
    'urakata': ('ＮＰＣ\u3000確認', '好感度アップ', '好感度ＵＰエフェクトテスト',
                'エフェクトテスト', 'テスト終了', '更新日\u3000'),
    'akatsuki': ('口パクテスト', 'シーン再生テスト'),
}
# 系统/任务/道具/技能/仲间 消息关键词 —— 无说话人文框块命中即判为系统消息, 不收
# (依据: 两作该 opcode 的全部唯一值均逐个人工过目 —— 无印 244 个命中 4 句 / 暁 15 个命中 6 块)
SYS_KW = ('覚えました', '入手しました', '仲間', '受領', '依頼', '装備', '所持', 'レベル',
          'ショップ', 'よろず屋', 'アイコン', '文を', 'に加えます', 'を外します',
          '話しかけて', '購入', 'ください', 'ますか', 'ですか', 'ましょう', 'ません',
          'ました', '進行します', '追加されました', '選択できるようになりました',
          '選択可能になりました')
# 立绘指令词表 (游戏以台词形式内嵌立绘指令, 非正文)
POSE = {'バストアップ', '全身', 'アップ', '正面', '横', '羅刹', '刀構え',
        '隊服', '私服', '制服', '着物', '斜め', '後ろ', '半身', 'バスト',
        '構え', '立ち', '座り', '顔'}
FACE = {'通常', '焦り', '驚き', '怒り・睨み', '怒り', '睨み', '頬笑み', '呆れ',
        '挑発', '疑問', '悲しみ・辛い', '悲しみ', '照れ', '狂気', '笑顔', '困り',
        '泣き', '笑い', '真剣', '不機嫌', '驚愕', '照れ笑い', '冷静', '無表情'}
LIE_WORDS = POSE | FACE


def is_lie(t):
    parts = [p for p in t.strip('「」').split('\u3000') if p]
    return bool(parts) and all(p in LIE_WORDS for p in parts)


def clean(t):
    if is_lie(t):
        return None                # 纯立绘/表情词块 (保护性判据: 要求**所有**分段都是部位/表情词;
    #                              实测两作命中 0 —— 立绘控制实为 opcode 0x105+资源名, 非文本)
    # ⚠ 曾用子串判据 `'全身' in t` —— 会把正文「私は全身が熱くなっていくのを…」整句丢掉(无印 12 条)
    t = AT.sub('', t)              # 去 @Nr 着色码
    t = t.replace('&pcl', PCL)     # 主角名 inline
    # 全角空格 \u3000 有两义: ① **折行标记**(日文, 块首/句末标点后) → 去
    #                        ② **词间空格**(全角拉丁文, 如 「Ｐｌｅａｓｅ　ｔｅｌｌ　ｍｅ」) → 保留
    out = []
    n = len(t)
    for i, ch in enumerate(t):
        if ch != '\u3000':
            out.append(ch)
            continue
        a = t[i - 1] if i else ''
        b = t[i + 1] if i + 1 < n else ''
        # 保留条件: 两侧都是全角拉丁; 或位于块首而下一字为全角拉丁(跨块词间距, 由 join() 决定)
        if (LAT(a) and LAT(b)) or (i == 0 and LAT(b)):
            out.append(ch)
    return ''.join(out)


def join(a, b):
    """块合并: 日文折行直接接; 全角拉丁跨块则保留词间空格"""
    if b[:1] == '\u3000':
        if LAT(a[-1:]):
            return a + b
        return a + b.lstrip('\u3000')
    return a + b


def is_narration(t):
    """无说话人文框块判定: 是否为地の文 (叙事/年表)。系统/任务/道具/技能消息一律不收。
    判据两条: ① 不含系统消息关键词 ② 以「。」收尾(= 完整叙事句)。
    实测命中 —— 无印版 26 块: 「文久三年――京。」「――安政五年。」「――同年、冬。」「今は何もないようだ。」；
                暁の調べ 6 块: 「――そして京は、文久四年を迎える。」「――１８６４年。」＋同上三部年表。"""
    if any(k in t for k in SYS_KW):
        return False
    return t.endswith('。')


def is_text(d):
    b = d.split(b'\x00')[0]        # 文本以 NUL 收尾, 后面是对齐填充
    if len(b) < 2:
        return None
    if any(c < 0x20 and c not in (0x0a, 0x0d, 0x09) for c in b):
        return None
    try:
        t = b.decode('cp932')
    except Exception:
        return None
    if not any(0x3040 <= ord(c) <= 0x30ff or 0x4e00 <= ord(c) <= 0x9fff
               or 0xff01 <= ord(c) <= 0xff5e          # 全角拉丁(如 「Ｐｌｅａｓｅ　ｔｅｌｌ　ｍｅ」)
               or c in '…‥「」『』（）〈〉《》？！?!。、，,ー〜～・･' for c in t):
        return None
    return t


def extract(base, title='urakata'):
    op = OPCODES[title]
    TEXT_CMD, OPT_CMD, SYS_CMD = op['txt'], op['opt'], op['sys']
    debug_kw = DEBUG_KW[title]
    raw = open(os.path.join(base, 'event.enc'), 'rb').read()
    cnt = struct.unpack_from('<I', raw, 0)[0]
    lines = []
    for i in range(cnt):
        a, b, off = struct.unpack_from('<III', raw, 0x10 + 12 * i)
        size = a & 0x7fffffff
        ent = lzo1x_decompress(raw[off:off + size], b) if (a >> 31) & 1 else raw[off:off + size]
        if any(k.encode('cp932') in ent for k in debug_kw):
            continue                   # 调试 entry, 整体丢弃
        pos = 0
        pend = None
        while pos + 8 <= len(ent):
            cmd, ln = struct.unpack_from('<II', ent, pos)
            if pos + 8 + ln > len(ent):
                break
            d = ent[pos + 8:pos + 8 + ln]
            if cmd in (TEXT_CMD, OPT_CMD):
                t = is_text(d)
                if t is not None:
                    t = clean(t)
                    if t is None:      # 立绘指令, 跳过
                        pos += 8 + ln
                        continue
                    if pend is not None and cmd == TEXT_CMD:
                        pend = join(pend, t)   # 紧邻两段合并 (同一文本框软换行)
                    else:
                        if pend:
                            lines.append(pend)
                        pend = t
                    pos += 8 + ln
                    continue
            if cmd == SYS_CMD:
                t = is_text(d)
                if t is not None and is_narration(t):
                    t = clean(t)
                    if t:
                        if pend:
                            lines.append(pend)
                            pend = None
                        lines.append(t)     # 地の文 → 独立成行 (排除系统消息后所剩极少)
                    pos += 8 + ln
                    continue
            if pend:
                lines.append(pend)
                pend = None
            pos += 8 + ln
        if pend:
            lines.append(pend)
    # 收尾清理
    out = []
    for t in lines:
        t = t.strip()
        if t:
            out.append(t)
    return out


if __name__ == '__main__':
    # 用法: python urakata_extract.py <out_dir> <out.txt> [title]
    #   title: urakata(無印, 默认) | akatsuki(暁の調べ)
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.join(VNTRANS_HOME, '_work_hak/out1')
    outpath = sys.argv[2] if len(sys.argv) > 2 else os.path.join(VNTRANS_HOME, '_work_hak/裏語薄桜鬼_new.txt')
    title = sys.argv[3] if len(sys.argv) > 3 else 'urakata'
    L = extract(base, title)
    with io.open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    n = sum(len(x) for x in L)
    print('%s -> %d 行 / %d 字' % (outpath, len(L), n))
    tail = sum(1 for x in L if x[-1] in '。！？…」』')
    print('句末标点结尾 %.1f%% | PCL替换 %d | 残留@ %d | 残留& %d'
          % (100 * tail / max(len(L), 1), sum(1 for x in L if PCL in x),
             sum(x.count('@') for x in L), sum(x.count('&') for x in L)))
