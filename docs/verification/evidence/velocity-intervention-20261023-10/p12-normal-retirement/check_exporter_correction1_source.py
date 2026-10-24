"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Authorized compiler-free AST/name/source checks. Never executes the exporter.
"""
import ast
import builtins
import hashlib
import json
import os
from pathlib import Path

D=Path(__file__).resolve().parent
path=D/'readonly_export_closed_current_owner.py'
raw=path.read_bytes()
before=(D/'readonly_export_closed_current_owner.pre-list-correction.py').read_bytes()
old=b'all_# Existing37-name consumer is blocked: current exact owner has an unknown final\n'
new=b'all_names=sorted(os.listdir(ROOT));assert len(all_names)<=4096\n# Existing37-name consumer is blocked: current exact owner has an unknown final\n'
assert before.count(old)==1 and raw==before.replace(old,new), 'one exact bounded correction only'
tree=ast.parse(raw,str(path))
assignments=[(i,n) for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='all_names' for t in n.targets)]
assert len(assignments)==1
index,node=assignments[0]
expected_assign=ast.parse('all_names=sorted(os.listdir(ROOT))').body[0]
expected_guard=ast.parse('assert len(all_names)<=4096').body[0]
assert ast.dump(node,include_attributes=False)==ast.dump(expected_assign,include_attributes=False)
assert ast.dump(tree.body[index+1],include_attributes=False)==ast.dump(expected_guard,include_attributes=False)
uses=[i for i,n in enumerate(tree.body) if any(isinstance(x,ast.Name) and isinstance(x.ctx,ast.Load) and x.id=='all_names' for x in ast.walk(n))]
assert uses and index<min(uses) and not any(isinstance(n,ast.Name) and n.id=='all_' for n in ast.walk(tree))
defined={n.id for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store)}
for n in ast.walk(tree):
 if isinstance(n,(ast.Import,ast.ImportFrom)):
  defined.update(alias.asname or alias.name.split('.')[0] for alias in n.names)
loaded={n.id for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
assert not loaded-defined-set(dir(builtins)), 'unbound source names: '+repr(loaded-defined-set(dir(builtins)))
assert b"ROOT=Path('/home/holden/mckernel-work/l12s8e1/p.owner-63bdc7731c34491eb430ddb34b094d5b')" in raw
for binding in (b'before.st_size<=8*2**20',b'total<=8*2**20',b'len(encoded.encode())+1<=16*2**20',b'assert sorted(os.listdir(ROOT))==all_names'):
 assert binding in raw
for n in ast.walk(tree):
 if isinstance(n,ast.Import):
  assert all(alias.name in {'base64','hashlib','json','os','stat'} for alias in n.names)
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='os':
  assert n.func.attr in {'listdir','open','fdopen','fstat'}, 'unexpected os action'
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
 'status':'PASS_COMPILER_FREE_AST_NAME_SOURCE_CHECKS_ONLY','source_sha256':hashlib.sha256(raw).hexdigest(),
 'checks':['exact one-line restoration plus separate comment; all other bytes unchanged',
           'Python AST parses without executing source','one exact all_names assignment with immediate4096 guard',
           'all_names assignment precedes every use and no all_ expression remains','no unbound AST load names',
           'current ROOT/stable listing and8MiB/16MiB caps retained; no extra os action'],
 'exporter_executed':False,'root_operations':0,'Docker_operations':0,'proc_queries':0,'compiler_invoked':False,
 'physical_clearance':False}
fd=os.open(D/'SOURCE-CHECKS.CORRECTION1.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as stream:
 json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps(result,sort_keys=True))
