from pathlib import Path
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import subprocess, json, collections, sys, zlib

WORK = Path(__file__).resolve().parent.parent / '_work_step'
WORK.mkdir(exist_ok=True)
SOURCE = Path(os.path.join(VNTRANS_HOME, '还没做/[PC-JP]STEP -二人の関係は一歩ずつ-.rar'))
ZIP = r'C:\Program Files\7-Zip\7z.exe'
stage = sys.argv[1]
if stage == 'list':
    p = subprocess.run([ZIP, 'l', '-slt', '-sccUTF-8', '-potoame', str(SOURCE)], capture_output=True, check=True)
    listing = p.stdout.decode('utf-8').replace('\r\n', '\n')
    (WORK / 'archive_listing.txt').write_text(listing, encoding='utf-8', newline='\n')
    records = []
    for block in listing.split('----------', 1)[1].strip().split('\n\n'):
        record = dict(line.split(' = ', 1) for line in block.splitlines() if ' = ' in line)
        if 'Path' not in record:
            continue
        name = record['Path'].replace('\\', '/')
        assert not name.startswith('/') and ':' not in name and '..' not in name.split('/'), name
        assert not any(record.get(k) for k in ('Symbolic Link', 'Hard Link', 'Copy Link')), name
        records.append(record)
    (WORK / 'archive_members.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    files = [r for r in records if r['Folder'] == '-']
    print(json.dumps({'source': str(SOURCE), 'archive_bytes': SOURCE.stat().st_size, 'files': len(files), 'folders': len(records)-len(files), 'unpacked_bytes': sum(int(r['Size']) for r in files), 'extensions': dict(collections.Counter(Path(r['Path']).suffix.lower() for r in files)), 'ancillary_files': [r['Path'] for r in files if Path(r['Path']).suffix.lower() in ('.ini','.html','.txt','.bat','.cmd','.reg','.nfo')], 'dlc_update_matches': [r['Path'] for r in records if any(s in r['Path'].lower() for s in ('dlc','追加','add','extra','特典','bonus','update','patch'))]}, ensure_ascii=False, indent=2))
elif stage == 'extract':
    with (WORK / 'extract.log').open('wb') as log:
        p = subprocess.run([ZIP, 'x', '-y', '-sccUTF-8', '-potoame', '-o'+str(WORK/'source'), str(SOURCE)], stdout=log, stderr=subprocess.STDOUT)
    print((WORK/'extract.log').read_text(encoding='utf-8')[-2000:])
    assert p.returncode == 0, p.returncode
elif stage == 'audit':
    records = json.loads((WORK / 'archive_members.json').read_text(encoding='utf-8'))
    files = [r for r in records if r['Folder'] == '-']
    disk_files = list((WORK/'source').rglob('*'))
    assert sum(p.is_file() for p in disk_files) == len(files)
    audited = []
    texts = []
    for r in files:
        p = WORK/'source'/Path(r['Path'])
        b = p.read_bytes()
        crc = f'{zlib.crc32(b):08X}'
        assert len(b) == int(r['Size']) and crc == r['CRC'], p
        entry = {'path':r['Path'], 'bytes':len(b), 'crc':crc, 'head':b[:32].hex()}
        if p.suffix.lower() in ('.ini','.html','.txt','.bat','.cmd','.reg','.nfo') and p.name.upper() != 'SEEN.TXT':
            entry['disposition'] = '配置与手册：已完整读取'
            texts.append('FILE: '+r['Path']+'\n'+b.decode('cp932'))
        elif p.name.upper() == 'SEEN.TXT': entry['disposition'] = '剧情脚本容器：用于提取'
        elif p.suffix.lower() == '.exe': entry['disposition'] = '引擎可执行文件：版本与静态证据'
        else: entry['disposition'] = '图像或音频资源：已读取并核对CRC，仅备查'
        audited.append(entry)
    (WORK/'source_audit.json').write_text(json.dumps(audited, ensure_ascii=False, indent=2), encoding='utf-8')
    (WORK/'ancillary.txt').write_text('\n\n'.join(texts), encoding='utf-8', newline='\n')
    print(json.dumps({'files_checked':len(audited), 'crc_failures':0, 'ancillary_count':len(texts), 'extension_counts':dict(collections.Counter(Path(r['path']).suffix.lower() for r in audited))}, ensure_ascii=False))
else:
    raise ValueError(stage)
