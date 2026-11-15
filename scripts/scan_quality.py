import sys, zlib, re, collections
sys.path.insert(0, '/c/game/_Trans/tools')
import ariard_xp3 as A
import extract_choice_text as E

BAD_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd\ue000-\uf8ff'
                    r'\uac00-\ud7af\ud800-\udfff\u0400-\u04ff\u0e00-\u0e7f\u0600-\u06ff]')

def payloads(path):
    return E.load_payloads(path)

r = payloads(sys.argv[1]); r.update(payloads(sys.argv[2]))
stat = collections.Counter(); bad = []
for name, payload in sorted(r.items()):
    dec = E.descramble(payload)
    if dec is None:
        continue
    stat[name.split('.')[-1]] += 1
    nb = len(BAD_RE.findall(dec))
    if nb:
        bad.append((name, nb))
print('decoded by ext:', dict(stat))
print('files with bad chars:', len(bad))
for n, nb in sorted(bad, key=lambda z: -z[1])[:15]:
    print('  %5d  %s' % (nb, n))
# sample a dialogue file
import os
sample = [n for n in r if n.startswith('scenario/') and n.endswith('.ks')][:1]
if sample:
    dec = E.descramble(r[sample[0]])
    print('--- sample', sample[0], '---')
    print(dec[:300])
