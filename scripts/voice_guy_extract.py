import sys, os, re, collections
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
sys.path.insert(0, r'<本地路径>')
from rubymarshal.reader import load
from rubymarshal.classes import RubyObject

BASE = os.path.join(VNTRANS_HOME, '_work_voice_guy/rgss/Data')
OUT = os.path.join(VNTRANS_HOME, '提取结果/[JP]Voice(Guy×Luke) ガイルク.txt')
COLOR = re.compile(r'\\C\[[0-9]+\]')
CTRL = re.compile(r'\\[A-Za-z]+(?:\[[^\]]*\])?')

def decode(b):
    if isinstance(b, bytes):
        return b.decode('utf-8', 'replace')
    return str(b)

def lists_in(o):
    res = []
    def rec(x):
        if isinstance(x, RubyObject):
            for v in x.attributes.values(): rec(v)
        elif isinstance(x, list):
            if x and all(isinstance(y, RubyObject) and '@code' in y.attributes for y in x):
                res.append(x)
            else:
                for y in x: rec(y)
        elif isinstance(x, dict):
            for y in x.values(): rec(y)
    rec(o); return res

def map_order():
    mi = load(open(os.path.join(BASE, 'MapInfos.rxdata'), 'rb'))
    return sorted(mi.keys(), key=lambda k: mi[k].attributes.get('@order', 999))

def extract_map(mid):
    p = os.path.join(BASE, 'Map%03d.rxdata' % mid)
    o = load(open(p, 'rb'))
    events = o.attributes.get('@events') or {}
    out = []
    for eid in sorted(events):
        ev = events[eid]
        pages = ev.attributes.get('@pages') or []
        for pg in pages:
            lst = pg.attributes.get('@list') or []
            i = 0
            while i < len(lst):
                c = lst[i]; code = c.attributes.get('@code'); pr = c.attributes.get('@parameters') or []
                if code == 101:
                    lines = [decode(pr[0])] if pr else ['']
                    j = i + 1
                    while j < len(lst) and lst[j].attributes.get('@code') == 401:
                        p2 = lst[j].attributes.get('@parameters') or []
                        lines.append(decode(p2[0]) if p2 else '')
                        j += 1
                    text = ''.join(COLOR.sub('', x) for x in lines)
                    text = text.replace('\r', '').replace('\n', '')
                    if text.strip():
                        out.append(text)
                    i = j; continue
                if code == 102:
                    opts = pr[0] if pr else []
                    for x in opts:
                        s = COLOR.sub('', decode(x))
                        if s.strip(): out.append(s)
                i += 1
    return out

def is_system(s):
    if s.startswith('【') or s.startswith('※注意'):
        return True
    if s == '称号を変更しました。' or s == 'HP・TPが回復した。':
        return True
    if re.fullmatch(r'二周目を始める条件を満たしました。', s):
        return True
    if re.fullmatch(r'.+を手に入れた。', s):
        return True
    return False

def main():
    order = map_order()
    print('map order', order)
    lines = []; per = {}
    for mid in order:
        p = os.path.join(BASE, 'Map%03d.rxdata' % mid)
        if not os.path.exists(p):
            per[mid] = 0; continue
        t = [x for x in extract_map(mid) if not is_system(x)]; per[mid] = len(t); lines += t
    print('per map', per, 'total', len(lines))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print('wrote', OUT, len(lines))
    # stats
    print('quote totals', sum(x.count('「') for x in lines), sum(x.count('」') for x in lines))
    print('paren totals', sum(x.count('（') for x in lines), sum(x.count('）') for x in lines))
    print('open quote lines', sum(1 for x in lines if x.count('「') > x.count('」')))
    print('close quote lines', sum(1 for x in lines if x.count('」') > x.count('「')))
    print('open paren lines', sum(1 for x in lines if x.count('（') > x.count('）')))
    print('close paren lines', sum(1 for x in lines if x.count('）') > x.count('（')))
    print('empty', sum(1 for x in lines if not x.strip()))
    print('max len', max(len(x) for x in lines), 'median-ish', sorted(len(x) for x in lines)[len(lines)//2])

if __name__ == '__main__':
    main()
