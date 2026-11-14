"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only exact selected-file adoption guard. No source writes or workload.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel')
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
 plan=json.loads((D/'COHERENT-NEXT-SOURCE-PLAN.NOT-GRANTED.json').read_text())
 for relative,row in plan['source_preimages'].items():assert ref(R/relative)==row,(relative,'canonical preimage changed')
 for relative,row in plan['source_postimages'].items():
  assert ref(Path(row['path']))==row,(relative,'private postimage changed')
  if relative not in plan['source_preimages']:assert not (R/relative).exists() and not (R/relative).is_symlink(),(relative,'new canonical path occupied')
 print(json.dumps(dict(scope=__doc__.splitlines()[0],status='PASS_EXACT_SEVEN_CANONICAL_PREIMAGES_AND_SEVEN_NEW_PATH_ABSENCES_NOT_ADOPTION',runtime_authority=None,canonical_writes=0)))
if __name__=='__main__':main()
