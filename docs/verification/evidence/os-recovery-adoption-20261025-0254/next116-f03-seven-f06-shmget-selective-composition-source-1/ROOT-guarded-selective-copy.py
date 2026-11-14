"""Functional OS only; no security testing. Proposed Root adoption, not authority.
Root must have its actual source-adoption authority before --apply. No compiler.
"""
import argparse,json,runpy,shutil
from pathlib import Path
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
# Check EVERY preimage and postimage before the first write.
runpy.run_path(str(D/'check_selective_inputs.py'),run_name='__main__')
if a.apply:
 for row in json.loads((D/'SELECTIVE-EIGHT-SOURCE-MAP.json').read_text())['writes']:
  dst=Path('/home/holden/mckernel')/row['relative']
  shutil.copyfile(row['postimage']['path'],dst)
 print('Root selected8 copies complete; adoption receipt/export/origin/build still separate')
