#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Completeness audit for CHOICE extraction.
Enumerates EVERY entry in data.xp3 + patch.xp3, classifies by extension
and whether it is KiriKiri-scrambled (.ks/.tjs text). Reports counts so we
can prove nothing text-bearing was dropped as noise.
"""
import sys, os, zlib, collections
sys.path.insert(0, '/c/game/_Trans/tools')
import ariard_xp3 as A

TEXT_EXT = ('.ks', '.tjs', '.txt', '.csv', '.ini', '.sav', '.asd', '.sli', '.scc')

def is_scrambled(payload):
    return payload[:2] == b'\xfe\xfe' and payload[3:5] == b'\xff\xfe'

def main():
    data_xp3, patch_xp3 = sys.argv[1], sys.argv[2]
    all_entries = {}
    for path in (data_xp3, patch_xp3):
        d, idx = A.load(path)
        for name, segs, adlr in A.parse(idx):
            parts = []
            ok = True
            for fl, off, orig, stored in segs:
                raw = d[off:off + stored]
                if fl == 1:
                    try:
                        raw = zlib.decompressobj().decompress(raw)
                    except Exception:
                        ok = False
                        break
                parts.append(raw)
            payload = b''.join(parts) if ok else None
            all_entries[name] = (payload, path)

    ext_counter = collections.Counter()
    scramble_counter = collections.Counter()  # by ext -> scrambled / plain / none
    plain_text_files = []   # text-ext entries that are NOT scrambled (could be dropped!)
    scrambled_text_files = []  # text-ext entries that ARE scrambled (should be decoded)
    binary_nonscramble = collections.Counter()  # ext -> count (not text, not scrambled)
    undecodable = []

    for name, (payload, src) in sorted(all_entries.items()):
        ext = os.path.splitext(name)[1].lower()
        ext_counter[ext] += 1
        if ext not in TEXT_EXT:
            binary_nonscramble[ext] += 1
            continue
        if payload is None:
            undecodable.append(name)
            continue
        if is_scrambled(payload):
            scramble_counter[ext + ':scrambled'] += 1
            scrambled_text_files.append(name)
        else:
            scramble_counter[ext + ':plain'] += 1
            plain_text_files.append((name, src, payload[:60]))

    print('=== TOTAL ENTRIES ===', len(all_entries))
    print('\n=== EXT COUNTS (all) ===')
    for k, v in ext_counter.most_common():
        print('  %-12s %d' % (k, v))
    print('\n=== TEXT-EXT: scrambled vs plain ===')
    for k, v in scramble_counter.most_common():
        print('  %-20s %d' % (k, v))
    print('\n=== BINARY / NON-TEXT EXT (not text-ext) ===')
    for k, v in binary_nonscramble.most_common():
        print('  %-12s %d' % (k, v))
    print('\n=== PLAIN (un-scrambled) text-ext files (would be SKIPPED by extractor) ===')
    print('  count =', len(plain_text_files))
    for name, src, head in plain_text_files[:40]:
        try:
            preview = head.decode('utf-16-le', 'replace').replace('\n', '\\n')[:40]
        except Exception:
            preview = repr(head[:20])
        print('  %-40s %s' % (name, preview))
    print('\n=== UNDECODABLE (decompress failed) ===', len(undecodable))
    for n in undecodable[:20]:
        print('  ', n)
    # Save the scrambled text file list for cross-check vs extracted_text
    with open('/c/game/_Trans/_work_choice/audit_scrambled_list.txt', 'w', encoding='utf-8') as g:
        for n in scrambled_text_files:
            g.write(n + '\n')
    print('\nwrote audit_scrambled_list.txt (%d scrambled text files)' % len(scrambled_text_files))

if __name__ == '__main__':
    main()
