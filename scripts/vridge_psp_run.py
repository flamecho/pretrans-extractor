#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Vridge/D3P 系 PSP 作品（sc.cpk + lt.bin 自建字符集）通用提取器。

引擎族：STORM LOVER 系列 / プリンス・オブ・ストライド 同族
（USRDIR/sc.cpk：CPK v7，条目 = 0x2000 头 + u16 LE 码流；
  基础区 code<3456 = cp932 有效双字节码原码序，直接复用 stormlover_charset.CHARSET；
  二级区 code>=3456 = 本作自用字形槽，逐作独立 ⇒ 各作 charset 模块给 SPECIAL）

命令（与 STORM LOVER 夏恋!! 同族，实测）：
  FFF0 <style><NAME>  名札 → 丢弃
  FFFF <TEXT>         文本框开始（= 一次点击）
  FFFE <TEXT>         框内换行 → 合并
  FFFB                消息分隔
  FFE6 / FFE7         主角 姓 / 名 占位（宏）
  其余 >=0xFF00       参数/UI → 丢弃

用法：python scripts/vridge_psp_run.py <game> [--stat]
"""
import os, sys, struct, re, bisect
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK

UNDECODED = '\u3014\u672a\u89e3\u6790\u3015'

C_NAME, C_BOX, C_BR, C_SEP = 0xFFF0, 0xFFFF, 0xFFFE, 0xFFFB
INLINE = {C_BOX, C_BR, 0xFFE6, 0xFFE7, 0xFF0F}


def toks(d):
    N = len(d) // 2
    vals = struct.unpack_from('<%dH' % N, d, 0)
    out, run, cur = [], [], 0
    for v in vals:
        if v >= 0xFF00:
            out.append((cur, run))
            run = []
            cur = v
        else:
            run.append(v)
    out.append((cur, run))
    return out


def words_to_text(ws, CHARSET, SPECIAL):
    n = len(CHARSET)
    out = []
    for v in ws:
        if v in SPECIAL:
            out.append(SPECIAL[v])
        elif v < n:
            ch = CHARSET[v]
            o = ord(ch)
            if 0xE000 <= o <= 0xF8FF or ch == '\u3013':
                out.append(UNDECODED)
            else:
                out.append(ch)
        else:
            out.append(UNDECODED)
    return ''.join(out)


def plate_spans(tk, CHARSET, SPECIAL, protag_given):
    """→ (starts, spks)：每个框的起始 token 索引与该框说话人（无名札＝None）。

    名札 payload 就在 `(FFF0, run)` 元组内：run=[槽位号] 或 [槽位号, 名字码…]；
    len(run)<=1 且下一 op 为 FFE6/FFE7 ⇒ 主角（可改名）。
    """
    n = len(tk)
    starts, spks = [], []
    spk = None
    for k, (op, run) in enumerate(tk):
        if op == C_NAME:
            nxt = tk[k + 1][0] if k + 1 < n else 0
            if len(run) <= 1:
                spk = protag_given if nxt == 0xFFE6 else None
            else:
                s = words_to_text(run[1:], CHARSET, SPECIAL)
                spk = re.sub(r'（[^）]*）$', '', s) or None
            continue
        if op in (C_BOX, C_SEP):
            starts.append(k)
            spks.append(spk)
    return starts, spks


def plan_ff0c(tk, CHARSET, SPECIAL, CAST, protag_given, fallback):
    """0xFF0C（相手役の下名）逐 token 定值。返回 {token_index: 替换串}。

    只做**可排除**的判定（判据见报告 §10）：
      ① 该框说话人本身是可攻略角色 ⇒ 对话对方＝主角 ⇒ 填 protag_given
      ② 条目内具名男角只有 1 人 ⇒ 排除法填その下名
      其余 ⇒ 占位 fallback（禁猜）
    ★ 曾试过「多男角时取最近男角且主导率≥60%」的推断级，实测反例（条目 0001 的样本地带
      `あのね、〔X〕、一応私は君の先輩、年上なのよ？` 被误填成 3 年生 流風）⇒ 已废弃，一律占位。
    """
    idx = [k for k, (op, _) in enumerate(tk) if op == 0xFF0C]
    if not idx:
        return {}
    starts, spks = plate_spans(tk, CHARSET, SPECIAL, protag_given)
    mcnt = Counter(s for s in spks if s in CAST)
    only = next(iter(mcnt)) if len(mcnt) == 1 else None

    out = {}
    for k in idx:
        b = bisect.bisect_left(starts, k) - 1
        spk = spks[b] if 0 <= b < len(spks) else None
        if spk in CAST:
            out[k] = protag_given
        elif only:
            out[k] = CAST[only]
        else:
            out[k] = fallback
    return out


def extract_entry(d, CHARSET, SPECIAL, NAME_SUB, TITLE_OPS=(), PARTNER=None):
    tk = toks(d)
    plan = plan_ff0c(tk, CHARSET, SPECIAL, *PARTNER) if PARTNER else {}
    boxes, cur, in_name = [], None, False
    for k, (cmd, ws) in enumerate(tk):
        if cmd == C_NAME:
            in_name = True
            continue
        if cmd in TITLE_OPS:
            s = words_to_text(ws, CHARSET, SPECIAL).strip()
            if s:
                boxes.append([s])
            continue
        if cmd == C_SEP:
            in_name = False
            if cur is not None:
                boxes.append(cur)
            cur = None
            continue
        if cmd == C_BOX:
            in_name = False
            if cur is not None:
                boxes.append(cur)
            cur = [words_to_text(ws, CHARSET, SPECIAL)]
            continue
        if cmd == 0 or in_name:
            continue
        if cmd == C_BR:
            if cur is not None:
                cur.append(words_to_text(ws, CHARSET, SPECIAL))
            continue
        if cur is not None:
            if cmd == 0xFF0C:
                if PARTNER:                     # 未配置 CAST 的旧作：维持原口径（丢弃）
                    cur.append(plan.get(k, '〔相手役〕'))
                    if ws:
                        cur.append(words_to_text(ws, CHARSET, SPECIAL))
            elif cmd in NAME_SUB:
                cur.append(NAME_SUB[cmd])
                if ws:
                    cur.append(words_to_text(ws, CHARSET, SPECIAL))
            elif cmd in INLINE:
                cur.append(words_to_text(ws, CHARSET, SPECIAL))
    if cur is not None:
        boxes.append(cur)

    res = []
    for lines in boxes:
        s = ''.join([lines[0]] + [x.lstrip('\u3000') for x in lines[1:]])
        s = s.strip()
        if not s:
            continue
        res.append(s)
    return res


TEXT_PUNCT = set('\u3000\u3001\u3002\u300c\u300d\u300e\u300f\uff08\uff09\u3010\u3011'
                 '\uff01\uff1f\uff1a\uff1b\u2026\u2025\u30fb\u30fc\uff5e\uff0c\uff0e'
                 '\u2018\u2019\u201c\u201d\u3014\u3015\u2015\u2500\u2501\u2010\u2011'
                 '\u30f6\u30fb')


def _is_text_ch(ch):
    o = ord(ch)
    if 0x3041 <= o <= 0x30fa or 0x4e00 <= o <= 0x9fff:
        return True
    if 0xff10 <= o <= 0xff5a or 0x41 <= o <= 0x7a:
        return True
    return ch in TEXT_PUNCT


def _has_content(s):
    for ch in s:
        if ('\u3040' <= ch <= '\u30ff') or ('\u4e00' <= ch <= '\u9fff') \
           or ('\uff10' <= ch <= '\uff5a') or ('A' <= ch <= 'z') \
           or ('\u3014' <= ch <= '\u3015'):
            return True
    return False


# 系统/UI・演出残留
UI_JUNK = re.compile(
    r'\u2500-\u257f|\u9752[\u2580-\u259f]'
)


def clean_line(s):
    s = s.strip()
    s = s.lstrip('\u3000\u3001\u3002\uff0c\uff0e\u30fb')
    s = s.strip()
    return s


def keep(s):
    if not s:
        return False
    if UNDECODED in s:
        return False
    if UI_JUNK.search(s):
        return False
    # 回想/選択履歴の装飾行（行頭が全角空白＋句読点のみ）
    if re.match(r'^[\u3000]+[\u3001\u3002\uff0c\uff0e\u30fb]', s):
        return False
    # 纯符号残片（无假名/汉字且极短）：名表分隔符 `：`・`；`・`Ｍ＼` 之类
    if not any(('\u3041' <= c <= '\u3096') or ('\u30a1' <= c <= '\u30fa')
               or ('\u4e00' <= c <= '\u9fff') for c in s) and len(s) <= 2:
        return False
    body = s.replace('\u3000', '')
    if not body:
        return False
    if sum(1 for c in body if _is_text_ch(c)) < len(body) * 0.5:
        return False
    if len(body) == 1 and not _has_content(body):
        return False
    return _has_content(s)


def run(cpk_path, out_path, CHARSET, SPECIAL, NAME_SUB, drop_exact=(),
        title_ops=(), stat=False, partner=None):
    c = CPK(cpk_path)
    entries = sorted([e for e in c.entries if e['name'] and e['name'].isdigit()],
                     key=lambda e: int(e['name']))
    lines = []
    unknown = {}
    for e in entries:
        for s in extract_entry(c.raw(e), CHARSET, SPECIAL, NAME_SUB, title_ops, partner):
            if UNDECODED in s:
                for ch in s:
                    pass
                unknown['entry ' + e['name']] = unknown.get('entry ' + e['name'], 0) + s.count(UNDECODED)
                continue
            s = clean_line(s)
            if s in drop_exact:
                continue
            if keep(s):
                lines.append(s)
    # 双写折叠（紧邻重复）
    out = []
    for s in lines:
        if out and out[-1] == s:
            continue
        out.append(s)
    with open(out_path, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(out) + '\n')
    print('entries', len(entries), 'lines', len(out), '->', out_path)
    if unknown:
        print('  [warn] 未解析框 %d 个（条目 %d 个，均为非正文表区）'
              % (sum(unknown.values()), len(unknown)))


def main():
    import importlib
    game = sys.argv[1]
    mod = importlib.import_module('vridge_cs_' + game)
    partner = None
    if hasattr(mod, 'CAST'):
        partner = (mod.CAST, mod.PROTAG_GIVEN, mod.FF0C_FALLBACK)
    run(mod.CPK, mod.OUT, mod.CHARSET, mod.SPECIAL, mod.NAME_SUB,
        drop_exact=getattr(mod, 'DROP_EXACT', ()),
        title_ops=getattr(mod, 'TITLE_OPS', ()),
        partner=partner)


if __name__ == '__main__':
    main()
