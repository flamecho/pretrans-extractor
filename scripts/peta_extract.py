"""ペット探偵Y's (AMEDEO, RealLive) 文本提取。

L0 判据：
- 页结束 = 0:3:17 pause（R_COMMAND_MOD=0 ⇒ 点击后清页）/ 151 msgHide / 152 msgClear /
  161 msgHideAll / 162 msgClearAll / 210 page / 102 TextWindow（切窗清页）。
- 0:3:3 par、0:3:201 br = 同一次点击内的排版换行 ⇒ 合并。
- 全库无页内点击码（205/206/207 均无待收文本）。
- 1:10:0 = Str 模块 strcpy(dest, "文本")：含日文的常量被引擎作为消息文本显示
  （章节标题、迷你游戏台词），ASCII 常量是资源名 ⇒ 只收含非 ASCII 的。
- 名札【】在页首 ⇒ 去【】冠在台词前（WINDOW.000.NAME_MOD=1 实际渲染）。
- ＊Ａ/＊Ｂ/＊Ｇ 由 GAMEEXE.INI #NAME.A/B/G 展开。
- 调试串（コマンドエラー 等）与 ％Ｚ 宏残留不收。
"""
import sys, os, re, json, collections, hashlib
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, os.path.join(VNTRANS_HOME, 'tools'))
from rl_decomp import read_toc, scenario, decompress
from rl_parse import Parser

WORK = os.path.join(VNTRANS_HOME, '_work_peta')
ROOT = VNTRANS_HOME
TITLE = "[PC-JP]ペット探偵Y's"

SEEN = os.path.join(WORK, 'iso', 'Seen.txt')
GAMEEXE = os.path.join(WORK, 'iso', 'gameexe.ini')

cfg = open(GAMEEXE, 'rb').read().decode('cp932')
NAMES = dict(re.findall(r'^#NAME\.([A-Z]+)="([^"]*)"', cfg, re.M))
assert NAMES.get('A') == '二葉', NAMES
assert NAMES.get('B') == '裕香', NAMES
assert NAMES.get('G') == 'ゴキブリ', NAMES
assert re.search(r'^#WINDOW\.000\.NAME_MOD=1\s*$', cfg, re.M)
assert re.search(r'^#WINDOW\.000\.R_COMMAND_MOD=0\s*$', cfg, re.M)

PAGE_END = {(17, 0), (151, 0), (152, 0), (161, 0), (162, 0), (210, 0), (102, 0), (102, 1)}
SOFT_BREAK = {(3, 0), (201, 0)}
DEBUG_PREFIX = ('（コマンドエラー）', '（裏返しコマンドが多すぎ）')

# 1:10:0 的日文常量（strcpy 到 strS[]）都是「由 DC 直接绘制」的图层文字，不是消息框正文：
#  - SEEN0003 章名、SEEN0007 回想菜单标题 → 1:4:0（Sys:title = 窗口标题栏）。
#  - SEEN0050/51/52 = ミニゲーム驱动器（本体 Textout 只有「（コマンドエラー）」调试串）。
#  - SEEN0053/54/55 = ミニゲーム解説台词表（strS[1200+i]），由 1:10:0 依次拷进 strS[1000]，
#    引擎用 DC 文本例程绘制（RealLive.exe 0xB4150 只认 #d/#c/#s/#r 等绘图码，
#    不产生消息框等待/清页语义）。小游戏与系统 UI 一律不收（同 00-rules §要收/不收）。
UI_TITLE_SCENES = {3, 7}
MINIGAME_SCENES = {50, 51, 52, 53, 54, 55}



def unquote(b):
    out = bytearray()
    i = 0
    quoted = False
    while i < len(b):
        c = b[i]
        if c == 0x22:
            quoted = not quoted
            i += 1
            continue
        if quoted and c == 0x5C and i + 1 < len(b) and b[i + 1] == 0x22:
            out.append(0x22)
            i += 2
            continue
        n = 2 if (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF) else 1
        out.extend(b[i:i + n])
        i += n
    return out.decode('cp932')


def is_quoted(b):
    return b[:1] == b'"' and b[-1:] == b'"'


CTRL = re.compile(r'#[0-9RTWD]')


def strip_codes(s):
    return CTRL.sub('', s)


def expand(s):
    return (s.replace('＊Ａ', NAMES['A'])
             .replace('＊Ｂ', NAMES['B'])
             .replace('＊Ｇ', NAMES['G']))


def main():
    d = open(SEEN, 'rb').read()
    toc = read_toc(d)
    lines = []
    origins = []
    stats = collections.Counter()
    per_scene = []
    skipped_debug = []

    for sn in sorted(toc):
        off, ln = toc[sn]
        _, ver, co, dl, cl, s = scenario(d, off, ln)
        assert ver == 10002 and co + cl == ln, (sn, ver, co + cl, ln)
        code = decompress(s[co:co + cl], dl)
        assert len(code) == dl
        p = Parser(code)
        cur = []          # 当前页文本片段
        current_speaker = ''
        local_name = ''
        st = collections.Counter()
        start_line = len(lines)
        last_select_opts = None

        def flush(reason, at):
            nonlocal cur, current_speaker
            if not cur:
                current_speaker = ''
                return
            t = ''.join(cur).rstrip()
            cur = []
            speaker = current_speaker
            current_speaker = ''
            if not t.strip():
                st['empty_pages'] += 1
                return
            if t.startswith(DEBUG_PREFIX) or '％Ｚ' in t:
                skipped_debug.append({'scene': sn, 'at': hex(at), 'text': t[:40]})
                return
            if speaker:
                t = expand(speaker + t)
            else:
                t = expand(t)
            lines.append(t)
            origins.append({'line': len(lines), 'scene': sn, 'end': hex(at), 'reason': reason})
            st['pages'] += 1
            st['page_chars'] += len(t)

        while not p.eof():
            a = p.p
            k, v = p.read_element()
            if p.p <= a:
                break
            if k == 'text':
                t = unquote(v)
                if t.startswith('ＳｅｅｎＥｎｄ'):
                    flush('halt', a)
                    st['halts'] += 1
                    continue
                if not cur:
                    m = re.match(r'【([^】]*)】', t)
                    if m:
                        current_speaker = m.group(1)
                        t = t[m.end():]
                        st['name_tags'] += 1
                cur.append(t)
                st['text_records'] += 1
            elif k == 'func':
                mt, mo, op, ov, extra = v
                if (mo, op, ov) == (3, 17, 0) and mt == 0:
                    flush('pause', a)
                elif mt == 0 and (op, ov) in ((151, 0), (152, 0), (161, 0), (162, 0), (210, 0)):
                    flush(f'op{op}', a)
                elif mt == 0 and (op, ov) == (102, 0) or (mt == 0 and (op, ov) == (102, 1)):
                    flush('textwindow', a)
                elif mt == 1 and op == 1311 and ov == 0:
                    ps = extra.get('params', [])
                    if len(ps) >= 2:
                        try:
                            local_name = ps[1].decode('cp932').lstrip(',').strip()
                        except Exception:
                            pass
                elif (mt, mo, op, ov) == (1, 10, 0, 0):
                    # strcpy(dest, "文本")：含日文常量＝上屏消息
                    if sn in UI_TITLE_SCENES or sn in MINIGAME_SCENES:
                        st['ui_subtitle_skipped'] += 1
                        continue
                    ps = extra.get('params', [])
                    if len(ps) >= 2 and is_quoted(ps[1]):
                        txt = unquote(ps[1])
                        if any(ord(c) > 0x7F for c in txt):
                            flush('string_msg', a)
                            body = strip_codes(txt).strip()
                            if not body:
                                continue
                            if body.startswith(DEBUG_PREFIX) or '％Ｚ' in body:
                                skipped_debug.append({'scene': sn, 'at': hex(a), 'text': body[:40]})
                                continue
                            speaker = ''
                            m = re.match(r'【([^】]*)】', body)
                            if m:
                                speaker = m.group(1)
                                body = body[m.end():]
                            elif local_name:
                                speaker = local_name
                            body = expand(body)
                            line = (speaker + body) if speaker else body
                            lines.append(line)
                            origins.append({'line': len(lines), 'scene': sn, 'at': hex(a),
                                            'reason': 'string_msg', 'speaker': speaker})
                            st['string_msgs'] += 1
                            st['string_chars'] += len(line)
            elif k == 'select':
                opts = [unquote(o).strip() for o in v[4]['opts']]
                flush('select', a)
                if opts and opts != last_select_opts:
                    for oi, o in enumerate(opts):
                        if not o:
                            continue
                        if o.startswith(DEBUG_PREFIX) or '％Ｚ' in o:
                            skipped_debug.append({'scene': sn, 'at': hex(a), 'text': o[:40]})
                            continue
                        o = expand(o)
                        lines.append(o)
                        origins.append({'line': len(lines), 'scene': sn, 'at': hex(a),
                                        'reason': 'option', 'index': oi})
                        st['options'] += 1
                        st['option_chars'] += len(o)
                last_select_opts = opts or None

        flush('eof', len(code))
        per_scene.append({'scene': sn, 'lines': len(lines) - start_line, **dict(st)})

    assert len(lines) == len(origins)
    dest = os.path.join(WORK, 'candidate.txt')
    with open(dest, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')

    totals = collections.Counter()
    for st in per_scene:
        for k2, v2 in st.items():
            if isinstance(v2, int) and k2 not in ('scene', 'lines'):
                totals[k2] += v2
    result = {
        'title': TITLE, 'lines': len(lines), 'chars': sum(map(len, lines)),
        'bytes': os.path.getsize(dest),
        'sha256': hashlib.sha256(open(dest, 'rb').read()).hexdigest(),
        'totals': dict(totals), 'scenes': per_scene,
        'skipped_debug': skipped_debug,
    }
    open(os.path.join(WORK, 'extraction.json'), 'w', encoding='utf-8').write(
        json.dumps(result, ensure_ascii=False, indent=2))
    open(os.path.join(WORK, 'line_origins.json'), 'w', encoding='utf-8').write(
        json.dumps(origins, ensure_ascii=False))
    print(json.dumps({k: v for k, v in result.items() if k not in ('scenes', 'skipped_debug')},
                     ensure_ascii=False, indent=2))
    print('SCENES_WITH_TEXT', sum(1 for x in per_scene if x['lines']))
    print('DEBUG_SKIPPED', len(skipped_debug))
    print('SCENE_ROWS', json.dumps([x for x in per_scene if x['lines']], ensure_ascii=False)[:1500])


if __name__ == '__main__':
    main()
