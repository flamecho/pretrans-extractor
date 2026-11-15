#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""群青ノ雪 (KiriKiri/KAG3) 文本提取
- 容器: data.xp3 (标准 XP3, xp3.py 读索引)
- 脚本: scenario/*.ks (cp932)
- 页界: @p (p 宏 = 一次点击/一页) ；@cm/@pageend 也作清屏界
- 说话人: [台詞 X] => @name X (名字窗) + @word/@ch 引擎自动「」括号。
          2026-11-08 修订: 名札一律保留 -> 名前+「台词」(括号类型按 brackets 参数复原)
- 合并: 同页内多次点击的文本(裸换行/[l][r])=软换行 => 合并为一行
- 选项: 本作 選択肢 宏未在主剧本调用 => 无正文选项
- 富文本: [rb ...] 振り仮名 => 剥净, 保留本体汉字
"""
import sys, os, io, json, re
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
import xp3

XP3 = os.path.join(VNTRANS_HOME, '_work_gunjo/body/Gunjou no yuki/[150217]GNY/群青ノ雪/群青ノ雪/data.xp3')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[PC-JP]群青ノ雪.txt')

# 主剧本(正文/extra 内容)
INCLUDE_PREFIX = [
    'scenario/【冬真】', 'scenario/【原田】', 'scenario/【司】', 'scenario/【藤間】',
    'scenario/【１章】', 'scenario/【２章】', 'scenario/分岐用',
    'scenario/【おまけ】', 'scenario/【無料版】',
]
EXCLUDE_NAME = {
    'scenario/TitleMenu.ks','scenario/SaveMenu.ks','scenario/LoadMenu.ks',
    'scenario/ConfigMenu.ks','scenario/CGMenu.ks','scenario/ExtraMenu.ks',
    'scenario/Chart.ks','scenario/スクリプトマニュアル.ks','scenario/デバッグスクリプト.ks',
    'scenario/Endroll.ks','scenario/スタッフロール.ks',
}

PAGE_BREAK_CMD = {'@p','@cm','@pageend','@jump','@call','@er','@return','@s'}
TAG_BREAK = {'[p]','[np]','[cm]','[r]','[l]'}

_RB = re.compile(r'\[/?rb[^]]*\]')                 # 振り仮名 ruby, 剥净
_NAME = re.compile(r'\[台詞\s+(\S+)(?:\s+brackets=([^\]]+))?\]')
_BRK = {'「':'」', '（':'）', '『':'』'}

def decode(b):
    for enc in ('utf-8-sig','utf-8','cp932','shift_jis'):
        try: return b.decode(enc)
        except Exception: pass
    return b.decode('cp932','replace')

def parse(text):
    pages=[]; buf=[]; cur_name=None; cur_open='「'
    lines_seen=0; text_lines=0
    def flush():
        nonlocal buf, cur_name, cur_open
        if buf:
            body=''.join(buf)
            if cur_name is not None:
                body = cur_name + cur_open + body + _BRK.get(cur_open,'」')
            pages.append(body)
        buf=[]; cur_name=None; cur_open='「'
    for raw in text.split('\n'):
        s = raw.rstrip('\r').strip()
        lines_seen += 1
        if not s: continue
        if s.startswith(';'):   continue   # 注释
        if s.startswith('*'):   continue   # label
        if s.startswith('@'):
            if s.split()[0] in PAGE_BREAK_CMD: flush()
            continue
        if s.startswith('['):
            m=_NAME.match(s)
            if m:
                cur_name=m.group(1)
                b=m.group(2)
                # 括号规范化：ASCII/curly 引号(作者用 brackets=" ) 归一为日文「，与末尾」配平
                if b and b[0] in _BRK:
                    cur_open = b[0]
                else:
                    cur_open = '「'
                continue
            if s in TAG_BREAK: flush()
            continue
        sc = _RB.sub('', s)                      # 剥 ruby
        if not sc: continue
        text_lines += 1
        buf.append(sc)
    flush()
    return pages, lines_seen, text_lines

def main():
    x = xp3.XP3(XP3)
    ks = sorted([n for n in x.files if n.lower().endswith('.ks')])
    all_lines=[]; stats=[]
    included=excluded=0
    for n in ks:
        t = decode(x.read(n))
        if any(n.startswith(p) for p in INCLUDE_PREFIX) and n not in EXCLUDE_NAME:
            pages,ls,tl = parse(t); included+=1
            stats.append((n,'INCLUDE',len(pages),ls,tl)); all_lines.extend(pages)
        else:
            _,ls,tl = parse(t); excluded+=1
            stats.append((n,'EXCLUDE',0,ls,tl))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT,'w',encoding='utf-8',newline='\n') as f:
        f.write('\ufeff')
        for ln in all_lines: f.write(ln+'\n')
    print('INCLUDE',included,'EXCLUDE',excluded,'pages',len(all_lines))
    with io.open(os.path.join(VNTRANS_HOME, '_work_gunjo/stats.json'),'w',encoding='utf-8') as f:
        json.dump(stats,f,ensure_ascii=False,indent=1)

if __name__ == '__main__':
    main()
