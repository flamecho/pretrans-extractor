# -*- coding: utf-8 -*-
"""ISO9660 内指定 LBA 的 CPK 切出并解包 —— PSP（Zerodiv / CRI CPK 系）通用驱动

用法：
  python scripts/iso_cut_cpk.py <iso> <lba> <size> <outdir> [--cpk 名] [--skip a,b,...] [--all]

例（裏語 薄桜鬼 ～暁の調べ～）：
  python scripts/iso_cut_cpk.py "_work_ake/…(Japan).iso" 54512 196405376 _work_ake/out1

说明：
  - LBA/size 由 `scripts/_archive/tmp19/iso.py <iso>` 列出（找 `PSP_GAME/USRDIR/UMD.cpk`）。
  - 默认跳过纯资源目录（texture/movie/sound/npc/town/icon/anime_enemy），只出脚本与数据；
    加 `--all` 则全解。
  - 输出目录内会落一份 `<cpk 名>`（默认 umd.cpk）以便重跑时命中缓存。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpk import CPK

DEFAULT_SKIP = {'anime_enemy', 'texture', 'movie', 'sound', 'npc', 'town', 'icon'}


def cut(iso, lba, size, dest):
    if os.path.exists(dest) and os.path.getsize(dest) == size:
        print('[=] 复用已切出的 %s (%d B)' % (dest, size))
        return
    with open(iso, 'rb') as f, open(dest, 'wb') as o:
        f.seek(lba * 2048)
        left = size
        while left > 0:
            b = f.read(min(1 << 22, left))
            if not b:
                break
            o.write(b)
            left -= len(b)
    print('[+] 切出 %s -> %d B' % (dest, os.path.getsize(dest)))


def main(argv):
    if len(argv) < 5:
        print(__doc__)
        return 1
    iso, lba, size, outdir = argv[1], int(argv[2]), int(argv[3]), argv[4]
    cpk_name = 'umd.cpk'
    skip = set(DEFAULT_SKIP)
    if '--all' in argv:
        skip = set()
    if '--cpk' in argv:
        cpk_name = argv[argv.index('--cpk') + 1]
    if '--skip' in argv:
        skip = {x for x in argv[argv.index('--skip') + 1].split(',') if x}

    cpkp = os.path.join(outdir, cpk_name)
    os.makedirs(outdir, exist_ok=True)
    cut(iso, lba, size, cpkp)

    c = CPK(cpkp)
    n = 0
    for e in c.entries:
        nm = e.get('name') or ''
        if not nm or nm.split('/')[0] in skip:
            continue
        d = os.path.join(outdir, *nm.split('/'))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        with open(d, 'wb') as o:
            o.write(c.raw(e))
        n += 1
    print('[+] CPK 共 %d 条，解出 %d 个文件 -> %s' % (len(c.entries), n, outdir))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
