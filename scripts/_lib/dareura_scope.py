"""Resolve the replay jump from its source table, then build RealLive scope."""
import os
VNTRANS_HOME = os.environ.get('VNTRANS_HOME', os.getcwd())
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(os.environ.get('VNTRANS_HOME', os.getcwd()))))
from pathlib import Path as _ScriptPath
_SCRIPT_DIR = _ScriptPath(os.environ.get('VNTRANS_HOME', os.getcwd()))
from pathlib import Path
import json,re,struct,subprocess,sys
R=Path(os.environ.get('VNTRANS_HOME', os.getcwd()));W=R/'_work_dareura'
E=json.loads((W/'elements.json').read_text('utf-8'))
# SEEN0240: B04[B0b[0]*2+2] contains an encoded replay scene.
# At 0x873 it is loaded into B0b[1]. The goto_unless at 0xB58 skips
# decoding when value < 9999; larger values are divided by ten at 0xBA6.
# 0xBCD performs jump(B0b[1]). The remainder selects the replay flag.
lhs=bytes.fromhex('24045b240b5b24ff000000005d5c0224ff020000005c0024ff020000005d5c1e')
table=[]
for e in E:
    if e['scene']==240 and e['kind']=='expr':
        b=bytes.fromhex(e['hex'])
        if b.startswith(lhs):
            rhs=b[len(lhs):];assert len(rhs)==6 and rhs[:2]==b'$\xff'
            value=struct.unpack_from('<i',rhs,2)[0]
            table.append({'offset':e['offset'],'value':value,'target':value if value<9999 else value//10})
assert table
targets=sorted({r['target'] for r in table})
mapping={'240:3021':targets}
(W/'dynamic_map.json').write_text(json.dumps(mapping,indent=2),'utf-8')
(W/'replay_table.json').write_text(json.dumps(table,indent=2),'utf-8')
print('REPLAY TABLE',len(table),'TARGETS',len(targets),targets)
subprocess.run([sys.executable,'-B','-X','utf8',str((_SCRIPT_DIR / '_lib/happygift_flow.py')),
                '--work',str(W),'--start','10','--dynamic-map',str(W/'dynamic_map.json')],check=True)
