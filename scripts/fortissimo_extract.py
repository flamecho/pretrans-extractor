#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《フォルティッシモ》 (PS Vita / PCSG01131 / KADOKAWA x Otomate / 2018-03-08) 全文本提取

完整管线
--------
  1) 解 PKG (PSN 原始包, 含 NoNpDrm 结构):
       scripts/pkg2zip.exe -x <pkg> <zRIF>
       zRIF 需自备（见 references/third-party.md）
       ⚠ 日文路径会让 pkg2zip 失败 -> 用 8.3 短路径 (_PSV-J~2/JP0031~1.PKG)
  2) 解密 PFS:
       <psvdec>/bin/win64/psvpfsparser.exe \
           -i app/PCSG01131 -o dec -z "<zRIF>" -f cma.henkaku.xyz
       ⚠ 需要放行网络 cma.henkaku.xyz:80 (否则报 "expected value" 假错误)
       成功标志: keystone: matched retail hmac
  3) 解 CPK (CRI CPK, 头部/ITOC 被 CRI UTF-XOR 加密):
       python scripts/cpk_v1.py dec/USRDIR/sc.cpk cpk_sc
       ⚠ cpk.py 里的 utf_decrypt 用的是 (m>>8)&0xFF —— 本作须用 cpk_v1.py 的 m&0xFF
  4) 本脚本:
       python scripts/fortissimo_extract.py cpk_sc <outdir> [--keep-custom-name]
  5) ★ 外部核对 (强制, 不得省略):
       提取完成后, 用 vndb 核对全部**人名**, 用官方站/攻略 wiki 核对**歌名/乐队/品牌**。
       「读得通」≠「字对」—— 字体替换槽会让通顺的句子里藏错字。
       本地解出「武居拓仭」「赤星英佗奈」, 读起来毫无破绽; 查 vndb v18212 才知道应为
       「武居拓**眞**」「赤星英**莉**奈」, 两处都是替换槽 (合计 ~3,400 字)。
       做法: ① 先出说话人姓名表 → 逐条贴 vndb 比对; ② 命中替换槽/非日文字符的行逐条比对;
             ③ 以外部资料为准 → 补进 EXC 重跑; ④ 查不到就保留原码 + 报告单列, 不硬猜;
             ⑤ 反向校验: 外部资料给的字若在输出里找不到 → 还有未发现的槽位。

文本格式 (逆向结论)
------------------
 * 剧本全部在 sc.cpk 的 152 个文件里 (其余 CPK 均为图/音/影, 无文本)。
 * 文件 ID 顺序 = 剧本顺序 (0000 = 序章, ... 0151)。
 * 文本块 = u16(LE) 码流, 一个块 = 一个文本框 = 一次点击:
       ... [可选 0xff95 + 3 操作数] ... [可选 姓名] 0xffff [正文] (0xfffe [正文])* 0xfffb
   0xfffe = 框内换行 (合并掉) ; 0xffff = 姓名/正文 分隔 ; 0xfffb = 块结束。
 * 字库 = JIS X 0208 (EUC-JP kuten 序), 码 -> 字:
       码 < 0x1EB : 索引 = 码 (<0x08F) 或 码+1
       码 >= 0x1EB: 索引 = 码+33
   (与 Bad Apple Wars 同一套表, 已验证)
 * 主人公名占位: 0xffe6 = 姓 (藤咲) ; 0xffe7 = 名 (ふたば)
       二者相邻 = 全名「藤咲ふたば」; 游戏中默认名即此。
 * 姓名分支: 每处按称呼分叉的台词都有**紧邻两条**:
       前一条 = 默认名版 (直接写死「藤咲…」)
       后一条 = 自定义名版 (写成 0xffe6/0xffe7 占位)
   主角名既已统一按默认名还原 -> 后一条属重复 -> 默认丢弃
   (--keep-custom-name 可两版都保留)。
"""
import os
import re
import sys
import struct

SURNAME = '藤咲'
GIVEN = 'ふたば'
LINE_SEP_KEEP = False

FF_LB = 0xFFFE    # 框内换行
FF_END = 0xFFFB   # 块结束
FF_SEP = 0xFFFF   # 姓名/正文 分隔
FF_SUR = 0xFFE6   # 姓 占位
FF_GIV = 0xFFE7   # 名 占位
FF_BOX = 0xFF95   # 部分块的文本框头 (0151)

LOWSHIFT = 0x08F
# 字体替换槽 (fon-substitution): 码 >= 0x1EB 时本想按 JIS 索引取字, 但本作字体把
# 0x0d80~0x0ddf 这一段 (JIS 第2水準的冷僻字) 改成了它自己需要的字形 —— 直接按
# cp932/JIS 取会得到「完仆(璧)」「麻仂(痺)」「叱丶激励(叱咤激励)」这类错字。
# 下表由上下文逐条核对得出 (括号内为佐证例句); 标 (?) 者未能确定, 保留原码。
EXC = {
    0x0d81: '乳',  # 牛乳   牛【】買ってきち/牛【】こぼさない
    0x0d82: '凛',  # 凛と   【】とした声に/【】々しく
    0x0d83: '認',  # 認める わたしを【】める様子
    0x0d85: '咤',  # 叱咤激励 オレの叱【】激励
    0x0d86: '裏',  # 裏声   妙な【】り声あげて
    0x0d87: '泣',  # 泣く   かわいく【】くから
    0x0d88: '喩',  # 比喩   部的な、比【】表現
    0x0d89: '嗅',  # 嗅ぎ回る 【】ぎまわる/【】ぎつける
    0x0d8b: '埒',  # 埒があかない 話していても【】があかない
    0x0d8c: '通',  # 思う通り 思う【】だろう
    0x0d8d: '奢',  # 華奢   こんなに華【】じゃん
    0x0d8e: '媚',  # 媚びを売る 【】びを売る奴
    0x0d8f: '揺',  # 動揺   小さな動【】が止まらない
    0x0d92: '諦',  # 諦める 結構【】めた/【】めに【】めて
    0x0d93: '剣',  # 真剣   真【】に取り組ん
    0x0d95: '梳',  # 髪を梳く ブラシ / 髪を【】くならいると（上下文推定）
    0x0d96: '藝',  # 文藝館 文【】館
    0x0d97: '鬱',  # 憂鬱   憂【】な気分
    0x0d98: '殷',  # 殷周秦 【】、周、秦、
    0x0d99: '淹',  # 淹れる お茶を【】れる/コーヒー【】れて
    0x0d9b: '淡',  # 淡々と 現場を【】々と照らし
    0x0d9c: '璧',  # 完璧   完【】な人
    0x0d9d: '痺',  # 麻痺   意識が麻【】していく
    0x0da0: '眞',  # 武居拓眞 (vndb c64146: 武居 拓眞 Takesue Takuma) —— 姓名牌里用到
    0x0da1: '産',  # 産毛   濃い【】毛
    0x0da3: '箋',  # 付箋   貼り付ける付【】/付【】、ですか？
    0x0da4: '華',  # 華麗   【】麗でまぶし/肌を【】麗に補正
    0x0da5: '隋',  # 隋     南北朝、【】、唐、五代/楊堅が【】を創始
    0x0da6: '撫',  # 撫でる ちょっと【】められた
    0x0da8: '莉',  # 赤星英莉奈 (vndb c64146: 赤星 英莉奈 Akaboshi Erina) —— 姓名牌里用到
    0x0da9: '藪',  # 藪から棒 【】から棒に
    0x0daa: '詭',  # 詭弁   【】弁だよ
    0x0dab: '強',  # 強欲   俺は【】欲なんだ
    0x0dad: '慮',  # 遠慮   もう【佻】【侘】しない = もう遠慮しない（上下文推定）
    0x0dae: '遠',  # 遠慮   （同上）
    0x0daf: '沈',  # 沈む   心が【】み始めて
    0x0db0: '辣',  # 辛辣   辛【】すぎる/辛【】な物言い
    0x0db1: '遽',  # 急遽   急【】追加して
    0x0db4: '颯',  # 颯爽   【】爽とあいさつ
    0x0db5: '毒',  # 毒舌   こんな【】舌になる
}
# 未确定 (保留原码, 报告中标注): 0x0d90 弍(『ＴＳＵＫＩ―~―』バンド名) /
#   0x0da7 佝(この~のジャム → コンポートの果物名) / 0x0db6 俔(『Ｉ ~ ＲＯＣＫ』)


JIS = []
for _k1 in range(0x21, 0x7F):
    for _k2 in range(0x21, 0x7F):
        try:
            JIS.append(bytes([_k1 + 0x80, _k2 + 0x80]).decode('euc_jp'))
        except Exception:
            pass


def ch(code):
    if code == FF_LB:
        return '\n'
    if code == FF_SUR:
        return SURNAME
    if code == FF_GIV:
        return GIVEN
    if code >= 0xFF00:
        return None
    if code in EXC:
        return EXC[code]
    i = code if code < LOWSHIFT else code + 1
    if code >= 0x1EB:
        i = code + 33
    return JIS[i] if 0 <= i < len(JIS) else None


def u16(b, i):
    return struct.unpack_from('<H', b, i)[0]


def block_texts(b):
    """返回 [(offset, text, had_name_placeholder), ...] —— 一个元素 = 一个文本框。"""
    out = []
    start = 0
    n = len(b)
    i = 0
    while i + 2 <= n:
        if u16(b, i) == FF_END:
            seg_start = start
            seg = [u16(b, k) for k in range(start, i, 2)]
            start = i + 2
            while seg and seg[-1] == FF_LB:          # 末尾换行
                seg.pop()
            idx = None
            for k in range(len(seg) - 1, -1, -1):    # 最后一枚 0xffff = 姓名/正文 分隔
                if seg[k] == FF_SEP:
                    idx = k
                    break
            tail = seg[idx + 1:] if idx is not None else seg
            # 砍掉前导控制码: 0xff95 文本框头 + 3 操作数
            p = 0
            if p < len(tail) and tail[p] == FF_BOX:
                p += 4
            # 只砍真正的控制码; 0xffe6/0xffe7 是名字占位, 必须保留
            while p < len(tail) and tail[p] >= 0xFF00 and tail[p] not in (FF_SUR, FF_GIV):
                p += 1
            tail = tail[p:]
            if not tail:
                continue
            had = any(v in (FF_SUR, FF_GIV) for v in tail)
            parts = []
            bad = False
            for v in tail:
                c = ch(v)
                if c is None:
                    bad = True
                    break
                parts.append(c)
            if bad:
                continue
            out.append((seg_start, ''.join(parts), had))
        i += 2
    return out


def norm(t):
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    if not LINE_SEP_KEEP:
        t = t.replace('\n', '')
    return t


def cpk_files(path):
    """解 CRI CPK, 返回 [(id, name, bytes), ...] 按 ID 顺序。"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cpk_v1 import CPK
    cpk = CPK(path)
    ents = [e for e in cpk.entries if e.get('id') is not None]
    ents.sort(key=lambda e: e['id'])
    out = []
    for e in ents:
        out.append((e['id'], e.get('name'), cpk.raw(e)))
    return out


def speaker_table(files):
    """姓名牌 (名札) 文本 —— 玩家在画面上能看到的话者称呼。"""
    names = {}
    for _name, data in files:
        st = 0
        for i in range(0, len(data) - 1, 2):
            if u16(data, i) != FF_END:
                continue
            seg = [u16(data, k) for k in range(st, i, 2)]
            st = i + 2
            idx = None
            for k in range(len(seg) - 1, -1, -1):
                if seg[k] == FF_SEP:
                    idx = k
                    break
            if idx is None:
                continue
            run = []
            for v in reversed(seg[:idx]):
                if v >= 0xFF00:
                    break
                c = ch(v)
                if c is None:
                    break
                run.append(c)
            run = list(reversed(run))
            if len(run) > 1:
                run = run[1:]          # 丢最前面那枚控制码操作数
            s = ''.join(run)
            if s:
                names[s] = names.get(s, 0) + 1

    def ok(s):
        if len(s) < 2:
            return False
        return all(('\u3040' <= c <= '\u30ff') or ('\u4e00' <= c <= '\u9fff')
                   or c == '\u3000' for c in s)

    return sorted(((k, v) for k, v in names.items() if ok(k)),
                  key=lambda x: -x[1])


def main():
    if len(sys.argv) < 3:
        sys.stderr.write(__doc__)
        sys.exit(2)
    srcdir = sys.argv[1]
    outdir = sys.argv[2]
    keep_custom = '--keep-custom-name' in sys.argv
    os.makedirs(outdir, exist_ok=True)

    # 收集: 目录模式 (cpk_sc/*) 或单个 CPK
    files = []
    if os.path.isdir(srcdir):
        for name in sorted(os.listdir(srcdir)):
            p = os.path.join(srcdir, name)
            if os.path.isfile(p):
                files.append((name, open(p, 'rb').read()))
    elif srcdir.lower().endswith('.cpk'):
        files = [('%04d' % i, d) for i, _, d in cpk_files(srcdir)]
    else:
        sys.stderr.write('需要 CPK 文件或已解包的目录\n')
        sys.exit(2)

    lines = []
    stats = []
    for name, data in files:
        blocks = block_texts(data)
        kept = []
        ncustom = 0
        for off, raw, had in blocks:
            t = norm(raw)
            if not t:
                continue
            if had and not keep_custom and kept and kept[-1] == t:
                ncustom += 1
                continue
            kept.append(t)
        lines.extend(kept)
        stats.append((name, len(blocks), len(kept), ncustom))

    story_path = os.path.join(outdir, 'フォルティッシモ_全文本.txt')
    with open(story_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    spk = speaker_table(files)
    spk_path = os.path.join(outdir, 'フォルティッシモ_話者名一覧.txt')
    with open(spk_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join('%s\t%d' % (k, v) for k, v in spk) + '\n')

    tot_b = sum(s[1] for s in stats)
    tot_k = sum(s[2] for s in stats)
    tot_c = sum(s[3] for s in stats)
    print('== 每个脚本: [文件, 块数, 保留, 丢弃的自定义名重复] ==')
    for name, nb, nk, nc in stats:
        if nb:
            print('  %-8s %5d %5d %4d' % (name, nb, nk, nc))
    print('  TOTAL 块=%d 保留=%d 丢重复=%d' % (tot_b, tot_k, tot_c))
    print('正文行数: %d -> %s' % (len(lines), story_path))
    print('话者名: %d 条 -> %s' % (len(spk), spk_path))


if __name__ == '__main__':
    main()
