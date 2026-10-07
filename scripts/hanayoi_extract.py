import struct, sys, os, re

# ============================================================================
#  花宵ロマネスク (PS2) 剧本提取 —— 解码表
#
#  引擎自研「字符码 = 有效 SJIS 字符序索引」编码：
#    code 0x0000..0x00CF : SJIS 0x8140.. 起的符号/标点（SJIS 1 字节区之后的有效 2 字节符号）
#                          （code 0x0001='、' 0x0002='。' 0x001B='ー' 0x0023='…' 0x0029='（' …）
#    code 0x00D0..0x0122 : 平假名 83 字（SJIS 0x829F..0x82F1）
#    code 0x0123..0x01A8 : 片假名及后续有效 SJIS 字符（SJIS 0x8340.. 有效序，跳过 0x837F）
#    code 0x01EA..        : 汉字（SJIS 汉字区 0x889F.. 有效序）
#  控制码 = >= 0xF000；0x0000 = 全角空格标记；0x0010 = 命令操作数
# ============================================================================

def _valid(lead_range, trail_range):
    out = []
    for lead in lead_range:
        for trail in trail_range:
            try:
                ch = bytes([lead, trail]).decode('cp932')
                if len(ch) == 1:
                    out.append(ch)
            except Exception:
                pass
    return out

TRAIL = list(range(0x40, 0x7F)) + list(range(0x80, 0xFD))

# 全有效 SJIS 2 字节字符（按码位序）——引擎的字符码即此表的索引
_L = []
for _lead in list(range(0x81, 0xA0)) + list(range(0xE0, 0xFC)):
    for _trail in TRAIL:
        try:
            _ch = bytes([_lead, _trail]).decode('cp932')
            if len(_ch) == 1:
                _L.append(_ch)
        except Exception:
            pass

SYMS = _valid([0x81], TRAIL)                       # 0x8140..0x81FC
HIRA = _valid([0x82], list(range(0x9F, 0xF2)))     # 0x829F..0x82F1
KATA = _valid([0x83], TRAIL)                       # 0x8340..(0x837F 跳过)

SYM_BASE, HIRA_BASE, KATA_BASE = 0x0000, 0x00D0, 0x0123

# 主人公名插入宏（玩家可改名）：FFE6 = 苗字、FFE7 = 名前。
# 默认名 = 「桐原珠美」（位于 eboot 默认名表 @0x152810，与 vndb 主人公 Kirihara Tamami 一致）。
NAME_SEI = '桐原'
NAME_MEI = '珠美'

# 汉字表 (SJIS 汉字区有效序)
_K = []
for lead in list(range(0x81, 0xA0)) + list(range(0xE0, 0xFC)):
    for trail in TRAIL:
        try:
            ch = bytes([lead, trail]).decode('cp932')
            if len(ch) == 1 and '\u4e00' <= ch <= '\u9fff':
                _K.append(ch)
        except Exception:
            pass
KANJI = _K
KANJI_BASE = 0x01EA

# ---------------------------------------------------------------------------
# 二级汉字块修正（索引 0x0DF4 起，= SJIS 0x989F 起，共 3390 槽）
#
# 引擎字符表的二级汉字块为**私有排序**（既非 SJIS/Unicode/JIS 序，随游戏字体走），
# 直接用 cp932 枚举序会整体误读。以下映射为逐字经**文内语境/文内注音**佐证的结果
# （表内每字均有明确搭配或注音，非猜测）。键 = cp932 枚举序在该块的槽位。
# 未列入者：该块内未被本作文本使用，或尚待佐证。
# ---------------------------------------------------------------------------
_LV2_FIX = {
    0: '―',  1: '菫',  2: '枷',  3: '奢',  4: '睨',  5: '璧',  6: '凛',  7: '舐',
    8: '囁',  9: '頷', 10: '儚', 11: '杞', 12: '鬱', 13: '嘲', 14: '呟', 15: '騙',
   16: '踪', 17: '宥', 18: '唸', 19: '嗚', 20: '蕾', 21: '訝', 22: '嘔', 23: '霹',
   24: '靂', 25: '絆', 26: '罠', 27: '揉', 28: '埃', 29: '躊', 30: '躇',
   32: '拗', 33: '腑', 34: '痺', 35: '眩', 36: '暈', 37: '嘆', 38: '諍', 39: '几',
   40: '柩', 41: '遥', 42: '審', 44: '綺', 45: '嗅', 48: '淹', 50: '佇',
   52: '痙', 53: '攣', 54: '轢', 55: '曖', 56: '琥', 57: '珀', 58: '傲', 59: '梳',
   60: '辟', 61: '躾', 65: '覗',
    # 31(仞) / 46(佻) / 51(來)：各仅 1 处，语境不足，待佐证 —— 暂保留 cp932 误读。
}
for _slot, _ch in _LV2_FIX.items():
    _L[0x0DF4 + _slot] = _ch

_unknown = {}


def decode(code):
    if code >= 0xF000 or code == 0x0010:
        return None
    if code == 0x0000:
        return ''
    # piecewise index into the valid-SJIS char list
    if code <= 0x00CF:
        i = code
    elif code <= 0x01E9:
        i = code + 1
    else:
        i = code + 0x74
    if 0 <= i < len(_L):
        return _L[i]
    _unknown[code] = _unknown.get(code, 0) + 1
    return None


# ---------------------------------------------------------------------------
# 符号/数字/全角拉丁区错位修正（索引 0x0092..0x00CF）
#
# 引擎字体未收 ◯（cp932 0x81FC），该槽位缺失 ⇒ 其后各槽整体前移一位
# （表索引 k 的实际字形 = 表中第 k+1 个字形），至平假名区（0x00D1 ぁ）因补入 1 个
# 字形而复位于原序。故 0x0092..0x00CF 整体 −1 修正。
# 佐证：表 0x0092(◯)→实际「０」、0x0093(０)→「１」 … 0x009B(８)→「９」；
#       0x00A1(Ｅ)→「Ｆ」、0x00A7(Ｋ)→「Ｌ」、0x00AA(Ｎ)→「Ｏ」、0x00B0(Ｔ)→「Ｕ」。
# 上下文实证：`０◯分`→『１０分』、`２◯を過ぎて`→『３０を過ぎて』、`０８時`→『１９時』、
#        `４人家族`→『５人家族』、`Ｔターン`→『Ｕターン』、`ＮＫ風`→『ＯＬ風』、`『ＮＥＥ』`→『ＯＦＦ』。
# ---------------------------------------------------------------------------
_SYM_SNAPSHOT = list(_L)
for _k in range(0x0092, 0x00CF + 1):
    _L[_k] = _SYM_SNAPSHOT[_k + 1]


_KANA = re.compile('[\u3040-\u30ff\u4e00-\u9fff\u3005\u3006]')


def parse_boxes(data):
    """返回 (lines, unknown)。一条记录 = 一个文本框 = 一次点击。

    记录 = `FFF0 … ` 到下一个 `FFF0` 之间。记录内：
      * 首个 `FFFF` = 正文起点；其前为说话人名（按规范略去，不写入正文）。
      * `FFFE` = 框内换行 → 合并（不换行输出）。
      * `FFFE` 后继为 `FFFB`/`FFFD` = 记录终止标记（每条记录恰好一个）。
    控制码（>=0xF000）与参数分隔码 0x0010 跳过。"""
    n = len(data) // 2
    v = list(struct.unpack_from('<%dH' % n, data, 0))
    starts = [i for i, c in enumerate(v) if c == 0xFFF0]
    lines = []
    for ri, a in enumerate(starts):
        b = starts[ri + 1] if ri + 1 < len(starts) else n
        j = -1
        for i in range(a, b):
            if v[i] == 0xFFFF:
                j = i
                break
        if j < 0:
            continue
        buf = []
        i = j + 1
        while i < b:
            c = v[i]
            if c == 0xFFFE:
                nx = v[i + 1] if i + 1 < b else 0
                if nx in (0xFFFB, 0xFFFD):
                    break
                i += 1
                continue
            if c == 0xFFE6:
                buf.append(NAME_SEI); i += 1; continue
            if c == 0xFFE7:
                buf.append(NAME_MEI); i += 1; continue
            if c >= 0xF000 or c == 0x0010:
                i += 1
                continue
            ch = decode(c)
            if ch:
                buf.append(ch)
            i += 1
        t = ''.join(buf)
        if t.strip():
            lines.append(t)
    return lines, _unknown


def extract(paths):
    out = []
    for p in paths:
        d = open(p, 'rb').read()
        ls, _ = parse_boxes(d)
        out.extend(ls)
    return out


if __name__ == '__main__':
    outpath = sys.argv[1]
    lines = extract(sys.argv[2:])
    with open(outpath, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('lines:', len(lines))
    print('unknown codes:', sorted((hex(k), v) for k, v in _unknown.items()))
