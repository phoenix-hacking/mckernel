"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only constructor; never imports guardian or executor, grants or executes.
"""
from pathlib import Path
import argparse, ast, difflib, hashlib, json

D=Path(__file__).resolve().parent
P=D.parents[1]/'CURRENT118-normal-retirement-preparation-1/compatibility-source-1'
NEWSC=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1930-pacific-1')
def ref(p):
 p=Path(p).resolve();raw=p.read_bytes()
 return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(p,v):
 with p.open('x') as f:f.write(json.dumps(v,indent=2)+'\n')

def main():
 a=argparse.ArgumentParser();a.add_argument('--guardian',type=Path,required=True);a.add_argument('--guardian-sha256',required=True);args=a.parse_args()
 armed=NEWSC/'ACTUAL-CONTROLS-ARMED.json'
 assert armed.is_file(),'actual new controls must first be armed'
 guardian=ref(args.guardian);assert guardian['sha256']==args.guardian_sha256
 tree=ast.parse(Path(guardian['path']).read_text())
 assert any(isinstance(n,ast.FunctionDef) and n.name=='guard' and not n.args.args for n in tree.body),'required guard() API'
 oldbind=ref(P/'BINDINGS.json');assert oldbind['sha256']=='49c0deaafbe38894335577b5b1d0512aed6e5e297477d45c0b96295df6b554f8'
 oldexec=ref(P/'retire_exact_current118_stopped_container.py');assert oldexec['sha256']=='44fd69ba6d2a10282a73fd00c48a5cbdd420b30597538753347039cc9ffd36aa'
 b=json.loads(Path(oldbind['path']).read_text());assert guardian!=b['guardian']
 dest=D/'current-guardian-source-1';assert not dest.exists();dest.mkdir()
 before=json.dumps(b,indent=2)+'\n';b['guardian']=guardian;b['output_root_parent']=str(dest)
 put(dest/'BINDINGS.json',b);binding=ref(dest/'BINDINGS.json')
 code=Path(oldexec['path']).read_text();anchor="BINDINGS_SHA='"+oldbind['sha256']+"'";assert code.count(anchor)==1
 successor=code.replace(anchor,"BINDINGS_SHA='"+binding['sha256']+"'");ast.parse(successor)
 with (dest/'retire_exact_current118_stopped_container.py').open('x') as f:f.write(successor)
 with (dest/'MINIMAL-DIFF.patch').open('x') as f:
  for old,new,oldname,newname in [(before,json.dumps(b,indent=2)+'\n',oldbind['path'],str(dest/'BINDINGS.json')),(code,successor,oldexec['path'],str(dest/'retire_exact_current118_stopped_container.py'))]:
   f.writelines(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=oldname,tofile=newname))
 files=json.loads((P/'RUNTIME-FILES.json').read_text());files.update(executor=ref(dest/'retire_exact_current118_stopped_container.py'),bindings=binding,guardian=guardian)
 for row in files.values():assert ref(Path(row['path']))==row
 put(dest/'RUNTIME-FILES.json',files)
 put(dest/'SOURCE_READY.json',dict(scope=b['scope'],status='SOURCE_READY_PENDING_INDEPENDENT_SUCCESSOR_REVIEW_AND_PUBLICATION',runtime_authority=None,runtime_files=files,prior_source_ready=ref(P/'SOURCE_READY.json'),actual_armed_receipt=ref(armed),pure_tests_rerun_for_successor=False,sole_converter=b['wait_status_helper']))
 put(dest/'PREPARATION.NOT-AUTHORITY.json',dict(scope=b['scope'],runtime_authority=None,status='SOURCE_ONLY_REQUIRES_INDEPENDENT_GUARDIAN_AND_SUCCESSOR_REVIEW_AND_PUBLICATION',prior_bindings=oldbind,prior_executor=oldexec,new_guardian=guardian,actual_armed_receipt=ref(armed),bindings=binding,executor=ref(dest/'retire_exact_current118_stopped_container.py'),sole_converter=b['wait_status_helper'],cutoffs=b['cutoffs'],source_execution=0))
 print(str(dest))
if __name__=='__main__':main()
