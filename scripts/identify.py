#!/usr/bin/env python3
"""识别容器或引擎，输出依据、文档路径和建议命令。

python scripts/identify.py <file-or-dir>
python scripts/identify.py <file> --deep

--deep 增加熵与日文串抽样。优先使用脚本所在包；工作区副本使用已安装技能。
"""
import os, sys, collections

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if not os.path.isfile(os.path.join(SKILL_ROOT, 'SKILL.md')):
    SKILL_ROOT = os.path.expanduser('~/.workbuddy/skills/vn-custom-bytecode-text')

# (magic, offset(或 None=任意), 判定, 引擎 slug, 下一步)
SIG = [
    (b'MComprHD', 0, 'CHD 光盘镜像', 'engines/images.md', '使用 chdman 导出镜像后按扇区模式读取'),
    (b'ROM2', 0, 'Kalmia8/ACTGS 归档 ROM2', 'engines/rom2.md',
     'python scripts/rom2_extract.py {f} <outdir>   # 脚本＝main.snr'),
    (b'SNR ', 0, 'Kalmia8/ACTGS 脚本 SNR', 'engines/rom2.md',
     'python scripts/torimari_extract.py {f} out.txt'),
    (b'TXA4', 0, 'Kalmia8 纹理 TXA4（图像，无文本）', 'engines/rom2.md', '-'),
    (b'BUP4', 0, 'Kalmia8 立绘 BUP4（图像，无文本）', 'engines/rom2.md', '-'),
    (b'XP3', None, 'KiriKiri XP3', 'engines/kirikiri.md',
     'python scripts/xp3.py {f} <outdir>   # 若像乱码/半乱码 → 先看 references/engines/kirikiri.md 的 XOR 形态'),
    (b'CPK ', 0, 'CRI CPK', 'engines/cri-archives.md',
     'python scripts/cpk.py {f} <outdir>'),
    (b'@UTF', None, 'CRI @UTF 表', 'engines/cri-archives.md',
     'python scripts/cpk.py {f} <outdir>（不解压换 scripts/cpk_v1.py）'),
    (b'pf8', 0, 'Artemis Engine 归档 pf8', 'engines/artemis.md',
     'python scripts/artemis_pfs_extract.py {f} <outdir>'),
    (b'CDAR', 0, 'Koei CDAR', 'engines/koei-cdar.md',
     'python scripts/cdar_extract.py {f} <outdir>（v4 可能嵌套 CDAR）'),
    (b'STCM2L', 0, 'Idea Factory STCM2L 脚本', 'engines/stcm2l.md',
     'python scripts/stcm2l_extract.py {f} out.txt   # PSV 版注意 opcode 逐文件平移 Δ'),
    (b'UNI2', 0, 'CRI UNI2（PS2 侧容器，内含 STCM2L）', 'engines/stcm2l.md',
     'python scripts/pandora_extract.py {f} <outdir>'),
    (b'LIBP', 0, 'Malie LIBP 归档', 'engines/malie.md',
     'python scripts/malie_extract.py {f} <outdir>   # 注意块单位 1024/2048 自适应'),
    (b'ARC!', 0, 'MNP ARC! 归档', 'engines/mnp.md', 'python scripts/koigig_extract.py {f} <outdir>'),
    (b'PackFile', 0, 'BGI/Ethornell .arc', 'engines/bgi.md', 'python scripts/brothers_kiss_extract.py {f} <outdir>'),
    (b'NSAr', 0, 'NScripter .nsa', 'engines/nscripter.md', 'python scripts/innoextract/ 或自写 nsa 解包'),
    (b'PSAR', 0, 'PSARC', 'archives.md', 'python scripts/psarc_extract.py {f} <outdir>'),
    (b'NSAC', 0, 'NIS-NML NSAC', 'engines/nis-nml.md', 'python scripts/nsac.py {f} <outdir>'),
    (b'MZX0', 0, 'HuneX MZX0 压缩块（字面 XOR 0xFF）', 'engines/hunex-ogre.md', '解 MZX0 后再看是否 CP932 文本'),
    (b'AFS\0', 0, 'CRI AFS', 'engines/cri-archives.md', 'python scripts/hanayoi_afs.py {f} <outdir>'),
    (b'mrgd00', 0, 'HuneX mrg 容器', 'engines/hunex-ogre.md', 'python scripts/kaleido_extract.py {f} <outdir>'),
    (b'NPA\x01', 0, 'Nitroplus NPA 归档', 'engines/nitroplus.md', 'python scripts/lamento_extract.py {f} <outdir>'),
    (b'allscr', 0, 'HuneX allscr 脚本（MZX0 压缩）', 'engines/hunex-ogre.md', 'python scripts/kaleido_extract.py'),
    (b'CRPT', 0, 'Madoka GScript 容器', 'engines/index.md', 'python scripts/tsundere_extract.py {f} <outdir>'),
    (b'SPTHEADER', 0, 'System-NNN .spt 脚本', 'engines/system-nnn.md', 'python scripts/asakiyumemishi_extract.py {f} out.txt'),
    (b'PFS0', 0, 'Switch NSP（PFS0）', 'platforms/switch-nca.md', 'python scripts/ns_open.py {f} --romfs <o>'),
    (b'NCA3', 0, 'Switch NCA3', 'platforms/switch-nca.md', 'python scripts/ns_open.py {f} --romfs <o>'),
    (b'HEAD', 0, 'Switch XCI', 'platforms/switch-nca.md', 'python scripts/ns_open.py {f} --romfs <o>'),
    (b'SCE\0', 0, 'PSV/PSP SELF（eboot，需转 ELF）', 'platforms/psv-pfs.md',
     'python <psvdec>/util/self2elf.py -i {f} -o eboot.elf -k work.bin'),
    (b'Rar!\x1a\x07\x01', None, 'RAR5（可能是 SFX 内嵌，PE 段后开始）', None, 'PowerShell 调 7z 解（日文路径必须走 PowerShell）'),
    (b'PK\x03\x04', None, 'ZIP', None, '7z x（日文路径走 PowerShell）'),
]
DIR_HINTS = [
    ('eboot.bin', 'PSV/PSP 应用（配 sce_pfs/ 或 PCSGxxxxx/）', 'platforms/psv-pfs.md',
     '<psvdec>/bin/win64/psvpfsparser.exe -i <dir> -o dec -z <zRIF> -f cma.henkaku.xyz'),
    ('sce_pfs', 'PSV PFS（需 psvpfsparser 解密）', 'platforms/psv-pfs.md', '用上面的 psvpfsparser 命令'),
    ('data.rom', 'Kalmia8/ACTGS ROM2 归档', 'engines/rom2.md', 'python scripts/rom2_extract.py data.rom <outdir>'),
    ('exec.dat', 'Malie 剧本（MalieVita/PC 版 Malie）', 'engines/malie.md', 'python scripts/malie_extract.py / mysteria_extract.py'),
    ('nscript.dat', 'NScripter 脚本（XOR 0x84）', 'engines/nscripter.md', '看 references/engines/index.md'),
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
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        print(__doc__.strip())
        return 0
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
                if slug:
                    hits.append('  引擎文档: %s' % os.path.join(SKILL_ROOT, 'references', *slug.split('/')))
        if hits:
            print('\n'.join(hits))
        else:
            print('  (目录内无已知特征文件名；对主要文件逐个跑 identify)')
        return
    d = open(p, 'rb').read(1 << 20)
    size = os.path.getsize(p)
    hit = None
    for mg, off, what, slug, nxt in SIG:
        if off is None:
            continue
        pos = d.find(mg) if off is None else off
        if pos >= 0 and d[pos:pos + len(mg)] == mg:
            hit = (mg, pos, what, slug, nxt); break
    if hit is None and len(d) > 0x8005 and d[0x8001:0x8006] == b'CD001':
        hit = (b'CD001', 0x8001, 'ISO9660 光盘镜像', 'engines/images.md', '7z x 或 mount 后看目录')
    if hit is None:
        for mg, off, what, slug, nxt in SIG:
            if off is not None:
                continue
            pos = d.find(mg)
            if pos >= 0:
                hit = (mg, pos, what, slug, nxt)
                break
    ext = os.path.splitext(p)[1].lower()
    print('  size=%d  ext=%s' % (size, ext or '-'))
    if hit:
        mg, off, what, slug, nxt = hit
        print('  ✓ 判定: %s   (magic %s @0x%x)' % (what, mg[:10], off))
        if slug:
            print('  引擎文档: %s' % os.path.join(SKILL_ROOT, 'references', *slug.split('/')))
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
