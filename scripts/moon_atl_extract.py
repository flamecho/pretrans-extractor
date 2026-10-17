#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""月ノ光太陽ノ影 (PC/ATL engine) 全文本提取

源：`scene.db` = SQLite（引擎 exe 内静态链 SQLite，SQL 形如
      SELECT text FROM talkText WHERE talkId=? AND sceneId=? ORDER BY phrase
      SELECT eval,text,no FROM choice WHERE sceneId=? AND choiceId=? ORDER BY no
      SELECT target,name FROM talk WHERE talkId=? and sceneId=?）
所以 scene.db 即运行时剧本库，无需解密 script.axr。

规则（见 skill §0）：
  · 一次点击 = 一行：按 scene → line.lineNo 顺序；type=1→talkText，type=6→choice
  · type=0(制作注记/SE)/2(二进制命令)/3,4(Lua脚本)/5(场景跳转) 全部跳过
  · 同一 talk 多 phrase（ORDER BY phrase）**顺序拼接**（本作 16 条有 phrase=1）
  · 行内 `\i`（对话起始样式符，恒在 `「` 后 index==1）剥除
  · 主角名宏（可改名，NameEditOnStart=1）：%NA00%→藤原(姓) %NA03%→美希(名) %NA01%→空
  · 不加说话人前缀；保留日文原文；输出 UTF-8 BOM / 纯 LF
"""
import sqlite3
import sys

NAME_MAP = {'%NA00%': '藤原', '%NA03%': '美希', '%NA01%': ''}

# 原作笔误修正表（**整行定值**，勿正则泛修；删掉表项即恢复原样）
# 判据＝原始 scene.db 里该 talk 就不存在收尾符，且相邻行均正常 ⇒ 作者漏写，非提取缺陷。
# 仅 FD《-Another Moon-》 scene22 两处（本篇无匹配）。
LINE_FIX = {
    '「とにかくねえ。彼女はもう俺と結婚して一緒に住んでるんだ。いい加減諦めてくれないかなあ。'
    'いつまでもねばねばねばねば納豆みたいにさ':
        '「とにかくねえ。彼女はもう俺と結婚して一緒に住んでるんだ。いい加減諦めてくれないかなあ。'
        'いつまでもねばねばねばねば納豆みたいにさ」',
    '「な、何を言ってるんだ君！？彼女は俺と婚約をした仲だぞ！　でたらめを言うんじゃない！':
        '「な、何を言ってるんだ君！？彼女は俺と婚約をした仲だぞ！　でたらめを言うんじゃない！」',
}


def dec(b):
    if b is None:
        return ''
    if isinstance(b, str):
        return b
    if isinstance(b, (int, float)):
        return str(b)
    return b.decode('cp932')


def clean(s):
    s = s.replace('\\i', '')
    for k, v in NAME_MAP.items():
        s = s.replace(k, v)
    s = s.replace('\r', '').replace('\n', '')
    return LINE_FIX.get(s, s)


def main():
    db = sys.argv[1] if len(sys.argv) > 1 else 'scene.db'
    out = sys.argv[2] if len(sys.argv) > 2 else 'out.txt'
    c = sqlite3.connect('file:%s?mode=ro&immutable=1' % db, uri=True)
    c.text_factory = lambda b: b

    lines = []
    n_talk = n_choice = n_super = 0
    for (sc,) in c.execute('select sceneId from scene order by sceneId'):
        # 引擎实际执行序 = `SELECT type,param FROM line WHERE sceneId=? AND lineNo=? ORDER BY type,param`
        # ⇒ 同一 lineNo 可有多行；type=1 多个时**逐个执行、后写覆盖前写** ⇒ 生效的是 param 最大者
        #   （旁证：本篇 scene125 lineNo0 = 空talk(param0) ＋ 正文talk(param11)，能正常显示；
        #     FD 的 328 组同 lineNo 双行 = 旧録音 X 系 vs 改稿新録音 Y 系，成批追加在原 talk 之后）
        rows = c.execute('select lineNo,type,param from line where sceneId=? '
                         'order by lineNo, type, param', (sc,)).fetchall()
        maxp = {}
        for _ln, ty, pa in rows:
            if ty == 1:
                maxp[_ln] = max(maxp.get(_ln, -1), int(dec(pa)))
        for _ln, ty, param in rows:
            if ty == 1:
                tid = int(dec(param))
                if tid != maxp[_ln]:
                    n_super += 1
                    continue
                rows2 = c.execute(
                    'select text from talkText where sceneId=? and talkId=? order by phrase',
                    (sc, tid)).fetchall()
                if not rows2:
                    continue
                txt = clean(''.join(dec(r[0]) for r in rows2))
                if txt:
                    lines.append(txt)
                    n_talk += 1
            elif ty == 6:
                cid = int(dec(param))
                seen = set()
                for (t,) in c.execute(
                        'select text from choice where sceneId=? and choiceId=? order by no',
                        (sc, cid)):
                    ct = clean(dec(t))
                    # 同组内同文案＝互斥备选（choice.eval = `return gameScene[N];` /
                    # `return not gameScene[N];`，只有条件为真的那一行会上屏；空 eval＝恒显示）
                    # ⇒ 组内按首现顺序取一（skill B7/B22「互斥分支同段取一」）
                    if ct and ct not in seen:
                        seen.add(ct)
                        lines.append(ct)
                        n_choice += 1

    with open(out, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    print('talk %d / choice %d / 被覆盖行 %d / total %d -> %s'
          % (n_talk, n_choice, n_super, len(lines), out))


if __name__ == '__main__':
    main()
