"""誰にでも裏がある -True or Lie？-: use the checked RealLive reader.

Source defaults and window configuration are validated by happygift_extract;
control flow starts at GAMEEXE.INI SEEN_START=0010 in this release.
"""
from pathlib import Path
import argparse, subprocess, sys, shutil

ROOT = Path(__file__).resolve().parent.parent
TITLE = '[PC-JP]誰にでも裏がある -True or Lie？-'
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--source', type=Path, default=Path(r'C:\AMEDEO\DAREURA'))
ap.add_argument('--publish', action='store_true')
args = ap.parse_args()
for script,extra in [('happygift_inspect.py',['--source',str(args.source),'--work',str(ROOT/'_work_dareura')]),
                     ('dareura_scope.py',[])]:
    subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools'/script),*extra],check=True)
command = [sys.executable, '-B', '-X', 'utf8', str(ROOT/'scripts/happygift_extract.py'),
           '--source', str(args.source), '--work', str(ROOT/'_work_dareura'),
           '--title', TITLE, '--start', '10']
if args.publish:
    command.append('--publish')
subprocess.run(command, check=True)
if args.publish:
    destination=ROOT/'解析报告/allow'/f'{TITLE}.sources.json'
    destination.parent.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'_work_dareura/line_origins.json',destination)
