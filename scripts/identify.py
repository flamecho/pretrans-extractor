#!/usr/bin/env python3
"""identify.py —— 一眼判定「这是什么容器/引擎、下一步跑什么」。

用法:
  python scripts/identify.py <file-or-dir>
  python scripts/identify.py <file> --deep      # 额外做 熵 / 日文串抽样

输出极短（≤20 行）：判定 + 依据 + 建议命令。**先跑这个，再决定读哪份引擎文档。**
引擎细节：`.workbuddy/memory/ENGINES.md` → `engines/<slug>.md`
"""
import os, sys, collections

# (magic, offset(或 None=任意), 判定, 引擎 slug, 下一步)
SIG = [
    (b'ROM2', 0, 'Kalmia8/ACTGS 归档 ROM2', 'rom2-snr',
     'python scripts/rom2_extract.py {f} <outdir>   # 脚本＝main.snr'),
    (b'SNR ', 0, 'Kalmia8/ACTGS 脚本 SNR', 'rom2-snr',
     'python scripts/torimari_extract.py {f} out.txt'),
    (b'TXA4', 0, 'Kalmia8 纹理 TXA4（图像，无文本）', 'rom2-snr', '-'),
    (b'BUP4', 0, 'Kalmia8 立绘 BUP4（图像，无文本）', 'rom2-snr', '-'),
    (b'XP3', 0, 'KiriKiri XP3', 'kirikiri-xp3',
     'python scripts/xp3.py {f} <outdir>   # 若像乱码/半乱码 → 先看 engines/kirikiri-xp3.md 的 XOR 形态'),
    (b'@UTF', 0, 'CRI CPK', 'cri-cpk-afs',
     'python scripts/cpk.py {f} <outdir>（不解压换 scripts/cpk_v1.py）'),
    (b'pf8', 0, 'Artemis Engine 归档 pf8', 'misc-engines',
     'python scripts/artemis_pfs_extract.py {f} <outdir>'),
    (b'CDAR', 0, 'Koei CDAR', 'koei-cdar',
     'python scripts/cdar_extract.py {f} <outdir>（v4 可能嵌套 CDAR）'),
    (b'STCM2L', 0, 'Idea Factory STCM2L 脚本', 'idea-factory-stcm2l',
     'python scripts/stcm2l_extract.py {f} out.txt   # PSV 版注意 opcode 逐文件平移 Δ'),
    (b'UNI2', 0, 'CRI UNI2（PS2 侧容器，内含 STCM2L）', 'idea-factory-stcm2l',
     'python scripts/pandora_extract.py {f} <outdir>'),
    (b'LIBP', 0, 'Malie LIBP 归档', 'malie',
     'python scripts/malie_extract.py {f} <outdir>   # 注意块单位 1024/2048 自适应'),
    (b'ARC!', 0, 'MNP 归档（KoiGIG）', 'misc-engines', 'python scripts/koigig_extract.py {f} <outdir>'),
    (b'PackFile', 0, 'BGI/Ethornell .arc', 'misc-engines', 'python scripts/brothers_kiss_extract.py {f} <outdir>'),
    (b'NSAr', 0, 'NScripter .nsa', 'misc-engines', 'python scripts/innoextract/ 或自写 nsa 解包'),
    (b'PSAR', 0, 'PSARC', 'unity-adv', 'python scripts/psarc_extract.py {f} <outdir>'),
    (b'NSAC', 0, 'NIS-NML NSAC', 'misc-engines', 'python scripts/nsac.py {f} <outdir>'),
    (b'MZX0', 0, 'HuneX MZX0 压缩块（字面 XOR 0xFF）', 'hunex-ogre', '解 MZX0 后再看是否 CP932 文本'),
    (b'AFS\0', 0, 'CRI AFS', 'cri-cpk-afs', 'python scripts/hanayoi_afs.py {f} <outdir>'),
    (b'mrgd00', 0, 'HuneX mrg 容器', 'hunex-ogre', 'python scripts/kaleido_extract.py {f} <outdir>'),
    (b'NPA\x01', 0, 'Nitroplus NPA 归档', 'nitroplus', 'python scripts/lamento_extract.py {f} <outdir>'),
    (b'allscr', 0, 'HuneX allscr 脚本（MZX0 压缩）', 'hunex-ogre', 'python scripts/kaleido_extract.py'),
    (b'CRPT', 0, 'Madoka GScript 容器', 'misc-engines', 'python scripts/tsundere_extract.py {f} <outdir>'),
    (b'SPTHEADER', 0, 'System-NNN .spt 脚本', 'misc-engines', 'python scripts/asakiyumemishi_extract.py {f} out.txt'),
    (b'PFS0', 0, 'Switch NSP（PFS0）', 'switch-nca', 'hactool -t pfs0 --outdir=<o> {f}'),
    (b'NCA3', 0, 'Switch NCA3', 'switch-nca', 'hactool --keyset=<你的 prod.keys> -t nca --romfsdir=<o> {f}'),
    (b'HEAD', 0, 'Switch XCI', 'switch-nca', 'hactool --keyset=<你的 prod.keys> -t xci --securedir=<o> {f}'),
    (b'SCE\0', 0, 'PSV/PSP SELF（eboot，需转 ELF）', 'psv-pfs',
     'python <psvdec>/util/self2elf.py -i {f} -o eboot.elf -k work.bin'),
    (b'Rar!\x1a\x07\x01', 0, 'RAR5（可能是 SFX 内嵌，PE 段后开始）', None, 'PowerShell 调 7z 解（日文路径必须走 PowerShell）'),
    (b'PK\x03\x04', 0, 'ZIP', None, '7z x（日文路径走 PowerShell）'),
]
DIR_HINTS = [
    ('eboot.bin', 'PSV/PSP 应用（配 sce_pfs/ 或 PCSGxxxxx/）', 'psv-pfs',
     '<psvdec>/bin/win64/psvpfsparser.exe -i <dir> -o dec -z <zRIF> -f cma.henkaku.xyz'),
    ('sce_pfs', 'PSV PFS（需 psvpfsparser 解密）', 'psv-pfs', '用上面的 psvpfsparser 命令'),
    ('data.rom', 'Kalmia8/ACTGS ROM2 归档', 'rom2-snr', 'python scripts/rom2_extract.py data.rom <outdir>'),
    ('exec.dat', 'Malie 剧本（MalieVita/PC 版 Malie）', 'malie', 'python scripts/malie_extract.py / mysteria_extract.py'),
    ('nscript.dat', 'NScripter 脚本（XOR 0x84）', 'misc-engines', '看 engines/misc-engines.md'),
]
JP_EXT = {'.cpk': 'CRI CPK', '.xp3': 'KiriKiri XP3', '.arc': 'BGI .arc 或 Will .arc(看魔数)',
          '.nsa': 'NScripter', '.pck': 'Siglus', '.at9': 'ATRAC9 音频', '.mp4': '视频',
          '.txa': 'Kalmia8 纹理', '.bup': 'Kalmia8 立绘', '.msk': '掩码图', '.pic': '图像',
          '.snr': 'Kalmia8 脚本 SNR', '.wsc': 'WillPlus/AdvHD 脚本（rotl_8(c,6)）'}


def ent(b):
    import math
    if not b:
        return 0.0
    c = collections.Counter(b); n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    p = sys.argv[1]
    deep = '--deep' in sys.argv
    print('== %s ==' % p)
    if os.path.isdir(p):
        names = set()
        for dp, dn, fn in os.walk(p):
            names.update(fn)
            if len(names) > 5000:
                break
        hits = []
        for k, what, slug, nxt in DIR_HINTS:
            if k in names:
                hits.append('  [dir] %-14s %s\n         → %s' % (k, what, nxt))
        if hits:
            print('\n'.join(hits))
        else:
            print('  (目录内无已知特征文件名；对主要文件逐个跑 identify)')
        return
    d = open(p, 'rb').read(1 << 20)
    size = os.path.getsize(p)
    hit = None
    for mg, off, what, slug, nxt in SIG:
        if d.find(mg) >= 0:
            hit = (mg, d.find(mg), what, slug, nxt); break
    if hit is None and len(d) > 0x8005 and d[0x8001:0x8006] == b'CD001':
        hit = (b'CD001', 0x8001, 'ISO9660 光盘镜像', None, '7z x 或 mount 后看目录')
    ext = os.path.splitext(p)[1].lower()
    print('  size=%d  ext=%s' % (size, ext or '-'))
    if hit:
        mg, off, what, slug, nxt = hit
        print('  ✓ 判定: %s   (magic %s @0x%x)' % (what, mg[:10], off))
        if slug:
            print('  引擎文档: .workbuddy/memory/engines/%s.md' % slug)
        print('  下一步: ' + nxt.format(f=p))
    else:
        e = ent(d[:1 << 16])
        print('  ? 前 1 MB 无已知魔数  熵=%.3f  %s' % (e, '明文/表结构' if e < 0.6 else ('压缩/代码' if e < 0.9 else '高度加密（先找密钥/确认加密层）')))
        if ext in JP_EXT:
            print('  线索: 扩展名 %s → %s' % (ext, JP_EXT[ext]))
        print('  下一步: python scripts/probe.py jp %s --top 20   # 看有没有裸 cp932' % p)
        print('          python scripts/probe.py strings %s --top 20' % p)
    if deep:
        print('  --- 深查 ---')
        print('  熵(64K)=%.3f' % ent(d[:1 << 16]))
        import re
        jp = re.findall(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc]){3,}', d[:1 << 18])
        print('  日文串(前 256 KB) 命中 %d 条%s' % (len(jp), ('，例: ' + jp[0].decode('cp932', 'replace')) if jp else ''))


if __name__ == '__main__':
    main()
