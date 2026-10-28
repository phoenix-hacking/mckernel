"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Refresh private source-only refs after bounded source edits. No runtime or new authority.
"""
from pathlib import Path
import hashlib,importlib.util,json
D=Path(__file__).resolve().parent;C=D/'cohort';E=D.parent

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def adapt(v):
 if isinstance(v,dict):
  if set(v)=={'path','bytes','sha256'} and v['path'].startswith(str(C)+'/') and Path(v['path']).exists():return ref(v['path'])
  return {k:adapt(x)for k,x in v.items()}
 if isinstance(v,list):return[adapt(x)for x in v]
 return v

def main():
 runtime=read(C/'ROOT-OPERATION-BINDINGS.TEMPLATE.NOT-AUTHORITY.json')
 spec=importlib.util.spec_from_file_location('frozen117subjects',C/'runtime_guard.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 runtime['expected_subjects']=module.subjects();write(C/'ROOT-OPERATION-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',runtime)
 for p in C.glob('*TEMPLATE*.json'):write(p,adapt(read(p)))
 manifest=read(C/'PREPARATION-MANIFEST.json');manifest['files']=[ref(r['path'])for r in manifest['files']];write(C/'PREPARATION-MANIFEST.json',manifest)
 plan=read(C/'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json')
 plan['cached_source_refs']=[dict(actual=ref(r['actual']['path']),fetched_equivalent_path=r['fetched_equivalent_path'])for r in plan['cached_source_refs']]
 plan['actual123source_rehash']=False;plan.pop('actual122source_rehash',None)
 write(C/'PUBLICATION-ROWS.SOURCE-PLAN.NOT-AUTHORITY.json',plan)
 print(json.dumps(dict(status='FROZEN_SOURCE_REFS_NOT_AUTHORITY',manifest=ref(C/'PREPARATION-MANIFEST.json'))))
if __name__=='__main__':main()
