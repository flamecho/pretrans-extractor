#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NS 统一入口 —— 一条命令走完 XCI/NSP/NCA 的判定与解包，并**打印为什么选这条路**。

## 为什么需要它（2026-10-26 复盘）

`scripts/` 曾有 27 个 NS 相关脚本，其中大部分是「上一作不够用 ⇒ 再写一个」的迭代痕迹
（`nca_romfs` / `nca_stream_romfs` / `mist_romfs` / `redbell_romfs` / `ukronia_*` / `handsome_*` …）。
每次开工都要重新判断「这作该用哪个」，这就是绕弯路的来源。真正通用的只有 4 个：

| 场景 | 工具 |
|---|---|
| XCI 封装头不自洽（`hactool` 报 corrupt / NCA 起点错位） | `xci_hfs0.py` |
| NSP 大成员写全零 | `nsp_split.py` |
| hactool 不支持该 NCA（BKTR patch / 压缩） | `bktr_romfs.py` / `switch_nca.py`（纯 Python） |
| 其余 | `_sw/hactool.exe` |

本工具 = 上述 4 个的**调度器**：判类型 → 选路线 → 失败自动回退 → 打印决策链。

## 已知的「假失败」（别被吓到）

- `[WARN] prod.keys does not exist` / `Failed to load "prod.keys"`：hactool/nstool 总在**当前目录**找 keys，
  即使 `-k` 已指定别的文件。本工具固定 `cwd=_sw` 并显式 `-k merged.keys`。
- `Failed to match key "bis_key_00"` 一堆：keyset 里塞了**本机不需要**的键，只有 WARN 不是错。
- `XCI partition is corrupt`：多半只是 **hfs0_header_hash 校验**（需 `xci_header_key`），数据没坏 ⇒ 走 `xci_hfs0.py`。
- `Failed to read RomFS directory cache` / `Hash layer 3 failed`：patch NCA（crypt_type=4）或压缩 NCA ⇒ 不是密钥错。

## 用法

    python scripts/ns_open.py <xci|nsp|nca>                 # 判类型 + 列分区/NCA（只读，秒级）
    python scripts/ns_open.py <file> --nca DIR              # 只把 NCA 切到 DIR
    python scripts/ns_open.py <file> --romfs DIR            # 切 NCA 并导 romfs（大，可能数分钟）
    python scripts/ns_open.py <file> --keyset merged        # 换 keyset（默认 merged）
"""
import argparse
import glob
import io
import os
import re
import shutil
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SW = os.path.join(ROOT, '_sw')
HACTOOL = os.path.join(SW, 'hactool.exe')
TOOLS = os.path.join(ROOT, 'tools')
KEYSETS = {'merged': 'merged.keys', 'prod_fixed': 'prod_fixed.keys', 'prod': 'prod.keys'}


def log(msg):
    print(msg, flush=True)


def sniff(path):
    """只看魔数判类型；不依赖扩展名"""
    with open(path, 'rb') as f:
        f.seek(0x100)
        if f.read(4) == b'HEAD':
            return 'xci'
        f.seek(0)
        head = f.read(0x10000)
    if head[:4] == b'PFS0':
        return 'nsp'
    if b'NCZSECTN' in head[:0x20000]:
        return 'ncz'
    if head[:4] == b'NCA3' or head[0x200:0x204] == b'NCA3':
        return 'nca'
    if head[:4] == b'PFS0' or head[:4] == b'HFS0':
        return head[:4].decode().lower()
    return 'unknown'


def run(cmd, cwd=SW, timeout=600):
    """外部命令：cwd 固定在 _sw（避免 prod.keys 找不到的假警告）"""
    log('  $ %s' % ' '.join(cmd[1:]))
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return 124, '[timeout %ds]' % timeout


def keypath(name):
    f = KEYSETS.get(name, name)
    p = os.path.join(SW, f)
    if not os.path.exists(p):
        log('  ! keyset 不存在：%s' % p)
    return f  # 相对 SW，配合 cwd


# ---------------- XCI ----------------
def xci_list(path, keyset):
    rc, out = run([HACTOOL, '-t', 'xci', '-k', keypath(keyset), path],
                  timeout=180)
    rows = re.findall(r'secure:/([0-9a-f]+\.nca)\s+([0-9a-f]+)-([0-9a-f]+)', out)
    low = out.lower()
    corrupt = ('corrupt' in low) or ('partition is corrupt' in low) or ('hfs0_header_hash' in low)
    log('  hactool -t xci：%s，读到 %d 个 NCA%s' % ('OK' if rows else 'FAIL', len(rows),
                                                '（报 corrupt ⇒ 需手工切）' if corrupt else ''))
    return rows, corrupt


def xci_secure(path, outdir, keyset):
    """路线 A：hactool 直解 secure；失败回退路线 B（xci_hfs0 手工切）"""
    os.makedirs(outdir, exist_ok=True)
    rc, out = run([HACTOOL, '-t', 'xci', '-k', keypath(keyset), '--securedir', outdir, path],
                  timeout=1800)
    got = glob.glob(os.path.join(outdir, '*.nca'))
    if got:
        log('  [路线 A] hactool --securedir 成功，切出 %d 个 NCA' % len(got))
        return got
    log('  [路线 A 失败] %s ⇒ 回退路线 B：xci_hfs0.py 手工切'
        % ('corrupt' if 'corrupt' in out.lower() else 'no nca'))
    rc, out = run([sys.executable, os.path.join(TOOLS, 'xci_hfs0.py'), path, '--extract', outdir],
                  cwd=ROOT, timeout=1800)
    for l in out.split('\n'):
        if l.strip():
            log('    ' + l.strip()[:110])
    got = glob.glob(os.path.join(outdir, '*.nca'))
    log('  [路线 B] 切出 %d 个 NCA' % len(got))
    return got


# ---------------- NSP ----------------
def nsp_split(path, outdir):
    os.makedirs(outdir, exist_ok=True)
    rc, out = run([sys.executable, os.path.join(TOOLS, 'nsp_split.py'), path, outdir],
                  cwd=ROOT, timeout=1800)
    for l in out.split('\n')[-6:]:
        if l.strip():
            log('    ' + l.strip()[:110])
    return glob.glob(os.path.join(outdir, '*.nca'))


def tik_for(ncadir):
    tiks = glob.glob(os.path.join(ncadir, '*.tik'))
    if not tiks:
        return None
    with open(tiks[0], 'rb') as f:
        f.seek(0x180)
        return f.read(16).hex()


# ---------------- NCA → romfs ----------------
BAD_ROMFS = ('directory cache', 'hash layer', 'failed to read romfs', 'section is not encrypted with')


def nca_romfs(nca, outdir, keyset, titlekey=None):
    os.makedirs(outdir, exist_ok=True)
    cmd = [HACTOOL, '-t', 'nca', '-k', keypath(keyset)]
    if titlekey:
        cmd += ['--titlekey', titlekey]
    cmd += ['--romfsdir', outdir, nca]
    rc, out = run(cmd, timeout=3600)
    if glob.glob(os.path.join(outdir, '*')):
        log('  [路线 A] hactool --romfsdir 成功 → %s' % outdir)
        return True
    low = out.lower()
    if any(k in low for k in BAD_ROMFS):
        log('  [路线 A 失败] 命中 patch/压缩 NCA 特征 ⇒ 不是密钥问题')
        log('  [路线 B] bktr_romfs.py（BKTR 增量）或 switch_nca.py（纯 Python）')
        rc, out2 = run([sys.executable, os.path.join(TOOLS, 'bktr_romfs.py'), nca,
                        '--outdir', outdir, '--keyset', os.path.join(SW, keypath(keyset))],
                       cwd=ROOT, timeout=3600)
        for l in out2.split('\n')[:8]:
            if l.strip():
                log('    ' + l.strip()[:110])
        if glob.glob(os.path.join(outdir, '*')):
            log('  [路线 B] bktr_romfs 成功')
            return True
        log('  [路线 B 失败] ⇒ 若为加密 NCA 试：python scripts/switch_nca.py romfs <nca> <out> --keyset=%s'
            % os.path.join('_sw', keypath(keyset)))
        return False
    log('  [路线 A 失败] 其它原因，前 6 行日志：')
    for l in out.split('\n')[:6]:
        if l.strip():
            log('    ' + l.strip()[:110])
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--nca', metavar='DIR', help='只切 NCA 到 DIR')
    ap.add_argument('--romfs', metavar='DIR', help='切 NCA 并导 romfs 到 DIR')
    ap.add_argument('--keyset', default='merged', help='merged(默认)/prod_fixed/prod 或文件名')
    a = ap.parse_args()

    kind = sniff(a.path)
    size = os.path.getsize(a.path)
    log('== %s' % os.path.basename(a.path))
    log('   体积 %s ｜ 判型 %s' % (format(size, ','), kind))

    if kind == 'ncz':
        log('  ! NCZ（压缩 NCA）：hactool2020 / 1.4.0 / nstool1.9.2 全不支持，需 nsz 先解压')
        return 2
    if kind == 'unknown':
        log('  ! 判不出类型，先跑 scripts/identify.py 或 scripts/probe.py hex')
        return 2

    ncadir = a.nca or a.romfs
    if kind == 'xci':
        rows, _ = xci_list(a.path, a.keyset)
    elif kind == 'nsp':
        rows = []

    ncas = []
    if ncadir:
        if kind == 'xci':
            ncas = xci_secure(a.path, ncadir, a.keyset)
        elif kind == 'nsp':
            ncas = nsp_split(a.path, ncadir)
        else:
            ncas = [a.path]
        for n in ncas[:20]:
            log('    %-52s %10s B' % (os.path.basename(n), format(os.path.getsize(n), ',')))

    if a.romfs and ncas:
        tk = tik_for(ncadir) if kind == 'nsp' else None
        if tk:
            log('  titlekey ← %s.tik[0x180:0x190]' % os.path.splitext(os.path.basename(ncas[0]))[0])
        # 只解最大的那个（Program NCA 承载 romfs）
        main_nca = max(ncas, key=os.path.getsize)
        log('  解 romfs：%s' % os.path.basename(main_nca))
        ok = nca_romfs(main_nca, a.romfs, a.keyset, tk)
        return 0 if ok else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
