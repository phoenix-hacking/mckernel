"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure existing-owner mock regressions; no Docker, compiler, guard or guest execution.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,types
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'root-adopted-native-runtime-1/native_diagnostic_container_owner.py'
COMPILER='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load(HERE/'native_diagnostic_container_owner.py','readonly_owner_candidate_mock')
old=load(OLD,'readonly_owner_preimage_mock')
fixtures=load(Path('/home/holden/mckernel/scripts/tests/test_application_native_diagnostic_container_owner.py'),'retained_existing_owner_mock_fixtures')
fixtures.owner=m
rows=[]
def passed(name):rows.append(dict(case=name,result='PASS'))
def refuse(name,fn,exceptions=(m.OwnerError,)):
 try:fn()
 except exceptions:passed(name)
 else:raise AssertionError(name+' accepted')
assert len(old.SOURCE_HASHES)==143 and len(m.SOURCE_HASHES)==144
assert {k:v for k,v in m.SOURCE_HASHES.items() if k!=COMPILER}==old.SOURCE_HASHES
assert m.EXTRA_READONLY==old.EXTRA_READONLY+[COMPILER]
assert m.RUNNER==old.RUNNER
assert m.SOURCE_HASHES[COMPILER]=='028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1'
a=ast.parse(OLD.read_text());b=ast.parse((HERE/'native_diagnostic_container_owner.py').read_text())
assert [ast.dump(n) for n in a.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]==[ast.dump(n) for n in b.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
passed('old143 pins and all owner functions/classes byte-semantic AST unchanged; one exact compiler mount+pin')
obj=object.__new__(m.DiagnosticOwner)
obj.parent=Path('/mock/attempt-parent');obj.owner_sha='d'*64;obj.manifest_path='/mock/manifest.json';obj.manifest_sha256='e'*64;obj.nonce=fixtures.NONCE;obj.name='mckernel-native-diagnostic-'+obj.nonce;obj.label='mckernel.native-diagnostic.owner='+obj.nonce;obj.container=fixtures.CID
before=old.DiagnosticOwner._create_argv(obj);after=obj._create_argv();newmount=['--mount','type=bind,src='+COMPILER+',dst='+COMPILER+',readonly'];i=after.index(newmount[1]);without=after[:i-1]+after[i+1:];assert without==[m.SELF if x==old.SELF else x for x in before]
passed('complete create argv identical except new owner SELF and one exact readonly compiler mount')
row=fixtures.container(obj);row['HostConfig']['Ulimits'].append(dict(Name='fsize',Soft=33554432,Hard=33554432))
for path in m.EXTRA_READONLY:
 row['HostConfig']['Mounts'].append(dict(Type='bind',Source=path,Target=path,ReadOnly=True))
 row['Mounts'].append(dict(Type='bind',Source=path,Destination=path,RW=False,Propagation='rprivate'))
obj._profile(row,fixtures.image());passed('complete requested+actual container profile accepts one exact RO file and unchanged full config')
def profile_change(side,key,value,remove=False):
 r=copy.deepcopy(row);mounts=r['HostConfig']['Mounts'] if side=='requested' else r['Mounts'];index=next(i for i,x in enumerate(mounts) if x['Source']==COMPILER)
 if remove:mounts.pop(index)
 else:mounts[index][key]=value
 return obj._profile(r,fixtures.image())
refuse('missing requested compiler mount refuses',lambda:profile_change('requested','',None,True))
refuse('missing actual compiler mount refuses',lambda:profile_change('actual','',None,True))
refuse('requested compiler writable refuses',lambda:profile_change('requested','ReadOnly',False))
refuse('actual compiler writable refuses',lambda:profile_change('actual','RW',True))
refuse('different requested compiler source refuses',lambda:profile_change('requested','Source',COMPILER+'.other'))
refuse('different actual compiler destination refuses',lambda:profile_change('actual','Destination',COMPILER+'.other'))
# Existing bound_manifest source-pin predicate exercised with mocked reads/loader.
loader=types.SimpleNamespace(exec_module=lambda _:None);fake=types.SimpleNamespace(load_manifest=lambda _:dict(bound=True));spec=types.SimpleNamespace(loader=loader)
def digest(path):return m.SOURCE_HASHES[str(path)]
with patch.object(m,'_manifest_identity',return_value=None),patch.object(m,'_digest',side_effect=digest),patch.object(m.importlib.util,'spec_from_file_location',return_value=spec),patch.object(m.importlib.util,'module_from_spec',return_value=fake):
 assert m.bound_manifest('/mock/manifest.json','f'*64)[1]==dict(bound=True)
passed('all144 source pins precede complete manifest loader using existing bound_manifest')
def pin_failure(kind):
 def changed(path):
  if str(path)==COMPILER:
   if kind=='missing':raise FileNotFoundError(COMPILER)
   return '0'*64
  return digest(path)
 with patch.object(m,'_manifest_identity',return_value=None),patch.object(m,'_digest',side_effect=changed),patch.object(m.importlib.util,'spec_from_file_location',side_effect=AssertionError('loader reached before compiler pin')):
  m.bound_manifest('/mock/manifest.json','f'*64)
refuse('missing compiler file refuses before evaluator loader',lambda:pin_failure('missing'),(FileNotFoundError,))
refuse('different compiler hash refuses before evaluator loader',lambda:pin_failure('drift'))
(HERE/'PURE-MOCK-RESULT.json').write_text(json.dumps(dict(scope=__doc__,status='PASS_PURE_EXISTING_OWNER_MOCK_REGRESSION',count=len(rows),cases=rows,actual_Docker_compiler_guard_native_calls=0),indent=2)+'\n')
print(json.dumps(dict(status='PASS_PURE_EXISTING_OWNER_MOCK_REGRESSION',count=len(rows))))
