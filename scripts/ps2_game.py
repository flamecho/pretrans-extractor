import struct, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ps2_scene import extract_records, VAR_NAMES
import ps2_vm

PUNC = re.compile(r'[。、！＠？…「」『』（）]')
HIRA = re.compile(r'[\u3040-\u309f]')


def keep(t):
    return bool(PUNC.search(t)) or (bool(HIRA.search(t)) and len(t) >= 4)


def build_file_vm(path):
    """VM-level extraction: one line per message box (one click)."""
    try:
        return ps2_vm.extract_lines(open(path, 'rb').read(), VAR_NAMES)
    except Exception:
        return None


def build_file_flat(path):
    """Legacy flat-record extraction (fallback)."""
    out = []
    join_next = False
    for kind, t in extract_records(open(path, 'rb').read()):
        if kind == 'var':
            if out:
                out[-1] += t
            else:
                out.append(t)
            join_next = True
            continue
        if kind == 'code':
            continue
        if join_next:
            out[-1] += t
            join_next = False
        elif out and (t.startswith('\u3000') or t.startswith(' ')):
            out[-1] += t
        else:
            if keep(t):
                out.append(t)
    return out


def build(scene_dir):
    files = sorted(glob.glob(os.path.join(scene_dir, '*')))
    out = []
    vm_ok = vm_fail = 0
    for p in files:
        lines = build_file_vm(p)
        if lines is None:
            vm_fail += 1
            lines = build_file_flat(p)
        else:
            vm_ok += 1
        out.extend(lines)
    print(f'vm_ok={vm_ok} vm_fail={vm_fail}')
    return out


if __name__ == '__main__':
    lines = build(sys.argv[1])
    with open(sys.argv[2], 'w', encoding='utf-8-sig') as f:
        for t in lines:
            f.write(t + '\n')
    print('lines:', len(lines))
