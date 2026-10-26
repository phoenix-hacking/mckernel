#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
AST/JSON-only checks: do not import caller, owner, capture, cleanup or protocol.
"""
import ast,hashlib,importlib.util,json
from pathlib import Path
D=Path(__file__).resolve().parent

def ref(path):
 path=Path(path);raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def literals(tree,name):
 values=[n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
 assert len(values)==1,name
 return ast.literal_eval(values[0])
class ClearConstants(ast.NodeTransformer):
 def visit_Constant(self,node):return ast.copy_location(ast.Constant(value='SOURCE_CONSTANT'),node)
def structures(tree):
 return [ast.dump(ClearConstants().visit(n),include_attributes=False) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
def references(x):
 if isinstance(x,dict):
  if set(x)=={'path','sha256','bytes'}:yield x
  else:
   for y in x.values():yield from references(y)
 elif isinstance(x,list):
  for y in x:yield from references(y)

def main():
 index=json.loads((D/'SOURCE-BINDING-INDEX.NOT-RELEASED.json').read_bytes());expected=index['request_expected'];assert not Path(expected['path']).exists()
 spec=importlib.util.spec_from_file_location('metadata_only',D/'materialize_successor_request.SOURCE-ONLY.NOT-RELEASED.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 raw=m.request_bytes();assert dict(path=str(m.TARGET),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==expected
 assert len(raw)<32<<20
 request=json.loads(raw);delta=json.loads((D.parent/'REQUEST-SUCCESSOR-EXACT-DELTA.SOURCE-ONLY.NOT-GRANTED.json').read_bytes());base=json.loads(Path(delta['base']['path']).read_bytes())
 assert {k for k in base if base[k]!=request[k]}=={r['pointer'][1:] for r in delta['replacements']}
 assert not Path(delta['namespace_root']).exists()
 checked=0
 for row in index['files']:
  assert ref(row['base']['path'])==row['base'] and ref(row['successor']['path'])==row['successor']
  path=Path(row['successor']['path']);data=path.read_bytes()
  if path.suffix=='.py':
   before=ast.parse(Path(row['base']['path']).read_bytes());after=ast.parse(data)
   assert structures(before)==structures(after),str(path)
   objects=[]
   for node in ast.walk(ast.parse(data)):
    if isinstance(node,ast.Dict):
     try:objects.append(ast.literal_eval(node))
     except (ValueError,TypeError,SyntaxError):pass
  else:objects=[json.loads(data)]
  for x in objects:
   for binding in references(x):
    if binding['path']==expected['path']:assert binding==expected
    elif binding['path'].startswith(str(D)):
     assert ref(binding['path'])==binding,binding
     checked+=1
 cfg=json.loads((D/'FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.ATTEMPT5.READONLY-SEED.json').read_bytes())
 caller=ast.parse((D/'run_frozen_current290_image_entry.ATTEMPT5.READONLY-SEED.py').read_bytes())
 assert literals(caller,'CONFIG_SHA')==ref(D/'FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.ATTEMPT5.READONLY-SEED.json')['sha256']
 fill=ast.parse((D/'fill_existing_current290_image_payload.ATTEMPT5.READONLY-SEED.py').read_bytes());assert literals(fill,'EXPECTED_REQUEST_SHA')==expected['sha256']
 assert literals(fill,'EXPECTED_NAMESPACE')[0]==delta['namespace_root']
 assert all(cfg[k] is None for k in ['physical','postjoin','namespace_initialization','new_post_shared_physical_consumer'])
 assert cfg['pins']['request']==expected
 assert cfg['pins']['driver']['sha256']=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
 assert cfg['pins']['owner']==delta['successor_owner']
 print(json.dumps(dict(status='PASS_SOURCE_BINDINGS_PENDING_REAL_PROOFS',files=len(index['files']),local_references=checked,function_structures_unchanged=True,request_bytes=len(raw),request_written=False,namespace_created=False,runtime_released=False),sort_keys=True))
if __name__=='__main__':main()
