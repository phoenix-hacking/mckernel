"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Cheap byte/source contract check, no live guard or effects.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json
D=Path(__file__).resolve().parent;C=D/'cohort'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def main():
 count=0
 def walk(v):
  nonlocal count
  if isinstance(v,dict):
   if set(v)=={'path','bytes','sha256'}:
    if v['path'].startswith('/home/holden/'):
     assert ref(v['path'])==v;count+=1
   else:
    for x in v.values():walk(x)
  elif isinstance(v,list):
   for x in v:walk(x)
 for p in C.glob('*TEMPLATE*.json'):walk(read(p))
 walk(read(C/'PREPARATION-MANIFEST.json'))
 for row in read(C/'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json')['cached_source_refs']:walk(row['actual'])
 for p in list(C.glob('*.py'))+list(D.glob('*.py')):ast.parse(p.read_bytes(),filename=str(p))
 spec=importlib.util.spec_from_file_location('contract117runtime',C/'runtime_guard.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 assert read(C/'ROOT-OPERATION-BINDINGS.TEMPLATE.NOT-AUTHORITY.json')['expected_subjects']==m.subjects()
 assert not (C/'ROOT-OPERATION-BINDINGS.json').exists()
 assert not (C/'ROOT-ACTUAL-CURRENT-BOUNDARY.json').exists()
 assert not (D/'ROOT61-RUNTIME-DEPENDENCIES.json').exists()
 print(json.dumps(dict(status='PASS_SOURCE_CONTRACT_ONLY',byte_refs=count,source_helpers=len(list(C.glob('*.py'))),actual_operations=0)))
if __name__=='__main__':main()
