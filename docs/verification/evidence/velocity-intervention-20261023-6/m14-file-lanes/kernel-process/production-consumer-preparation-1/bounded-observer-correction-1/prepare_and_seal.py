"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind retained authority only; do not read/hash large objects/captures or execute ELF.
"""
from pathlib import Path
import ast,json,hashlib,stat
P=Path(__file__).resolve().parent;B=P.parent;SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def main():
 failure=B/'PRODUCTION-FIRST-FAILURE-1.json';assert pin(failure)['sha256']=='c7741bfcdfb778cee7a32834b0043c26194b4e4cc6cdc111af537a423915e1fb';fr=json.loads(failure.read_text());assert len(fr['records'])==14
 rf=B/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json';cf=B/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json';r=json.loads(rf.read_text())
 small=[pin(failure),pin(B/'run_production_once.py'),pin(rf),pin(cf),pin(B/'EXECUTABLE-READY.NOT-GRANTED.json'),pin(B/'ACTUAL-DEBUG-METADATA-ABI.json'),pin(Path(r['accepted_prior_Rust_symbols']['path'])),pin(B.parent/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json')];meta=list(fr['durable_objects'].values())
 for record in fr['records']:
  cmd=Path(record['command']['path']);assert pin(cmd)==record['command'];small.extend([pin(cmd),pin(cmd.parent/'whole-join.json')])
  for row in record['join']['captures'].values():
   meta.append(row)
   if row['size']<=1<<20:
    actual=pin(Path(row['path']));assert actual['sha256']==row['sha256'] and actual['bytes']==row['size'];small.append(actual)
 elfsrc=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-process-next/bounded-observer-correction-1/observe_retained_elf.py');assert pin(elfsrc)['sha256']=='d391d3d450282536049848e619925b2f1d92cb28b30032ad1e1b42204997cf15'
 ast.parse((P/'observe_retained_production.py').read_text());ast.parse((P/'run_observer_once.py').read_text())
 write(P/'INPUT-BINDINGS.json',dict(scope=SCOPE,small_pins=small,durable_metadata=meta,large_policy='Original c774 failure hash authenticates prior postjoin SHA and metadata; largeobjects/captures never rehashed. Compare stable device/inode/size/mtime/ctime/mode/uid/gid/nlink before and after offline consumer.',first_failure=pin(failure),ELF_source=pin(elfsrc),accepted_leaf=pin(B.parent/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),correction='Keep before==after and full brefs==arefs. Count only named vm_range_insert target_refs==1 in each actual caller; preserve GOT in full evidence/equality. Keep global partial target count2 and every provider/descriptor/source check.'))
 ready=dict(scope=SCOPE,status='ROOT_GRANTED_ONE_CPU0_PURE_RETAINED_OBSERVER_READY',observer=pin(P/'observe_retained_production.py'),bindings=pin(P/'INPUT-BINDINGS.json'),driver=pin(P/'run_observer_once.py'),original_failure=pin(failure),root_authority='Root adopts independent m14_build_release_review exact specification and grants ONE pure CPU0 retainedconsumer after seal; original c774/2655/raw14 immutable, no largeobjecthash/compiler/link/NM/readelf replay; first unexpected stop/no further correction.',profile=dict(CPU=0,jobs=1,AS=512<<20,CPU_seconds=10,wall_seconds=30,retirement_seconds=5,FSIZE=16<<20,NOFILE=128,core=0),canonical_mutations=0,old14commands_replayed=False)
 write(P/'EXECUTABLE-READY.json',ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(P/'EXECUTABLE-READY.json'),observer=ready['observer'],bindings=ready['bindings'],driver=ready['driver']),indent=2))
if __name__=='__main__':main()
