"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os
D=Path(__file__).resolve().parent;S=D.parent
spec=importlib.util.spec_from_file_location('owner',S/'native_diagnostic_container_owner.py');owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
obj=object.__new__(owner.DiagnosticOwner);obj.parent=Path(owner.HOST_OUTPUT['parent']);obj.manifest_path='/home/holden/mckernel-work/scratch/m07s1/m.json';obj.manifest_sha256='2b9115a45ddfffddeecf95f5d7c2da5670ef80272e34d8f2bdbdfe34f2c4de7e';obj.owner_sha=hashlib.sha256((S/'native_diagnostic_container_owner.py').read_bytes()).hexdigest();obj.nonce='1234567890abcdef1234567890abcdef';obj.name='not-created';obj.label='not-created'
argv=obj._create_argv()
def parse(argv):
 routes=[]
 for i,x in enumerate(argv[:-1]):
  if x=='--mount':
   fields=argv[i+1].split(',');kv=dict(p.split('=',1) for p in fields if '=' in p)
   assert kv['type']=='bind';src=Path(kv['src']);dst=Path(kv['dst']);assert src.is_absolute() and dst.is_absolute();assert src.resolve(strict=True)==src
   routes.append({'src':str(src),'dst':str(dst),'readonly':'readonly' in fields,'directory':src.is_dir()})
  elif x=='--tmpfs':routes.append({'src':None,'dst':argv[i+1].split(':',1)[0],'readonly':False,'directory':True})
 return routes
routes=parse(argv)
def visible(path,routes):
 path=Path(path);candidates=[r for r in routes if Path(r['dst'])==path or (r['directory'] and Path(r['dst']) in path.parents)]
 if not candidates:return None
 depth=max(len(Path(r['dst']).parts) for r in candidates);effective=[r for r in candidates if len(Path(r['dst']).parts)==depth]
 # Conflicting same-depth destinations are ambiguous regardless of argv order.
 if len({json.dumps(r,sort_keys=True) for r in effective})!=1:return None
 route=effective[0]
 if not route['readonly'] or route['src'] is None:return None
 mapped=Path(route['src'])/path.relative_to(route['dst'])
 if str(mapped)!=str(path) or not mapped.exists() or mapped.resolve(strict=True)!=mapped:return None
 return route
manifest=json.loads(Path(obj.manifest_path).read_bytes());inputs=set(owner.SOURCE_HASHES)|{owner.SELF,owner.RUNNER,obj.manifest_path,str(S/'native_diagnostic.py'),str(S/'native_diagnostic_backend.py'),str(S/'qmp_capture.py')}
inputs.update(ref['path'] for ref in manifest['artifacts'].values());inputs.update(ref['path'] for ref in manifest['staging'].values());inputs.update(ref['path'] for ref in manifest['modules']);inputs.update(manifest['cleanup_profile'][key]['path'] for key in ('consumer','provider'))
rows=[]
for path in sorted(inputs):
 route=visible(path,routes);assert route is not None,('unmounted/shadowed input',path);rows.append({'path':path,'effective_route':route})
missing='/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1'
assert visible(missing,routes) is None
# Actual P12 failed root is deliberately absent from M07 pins. Model minimal RO
# restoration as regression only, without adding unrelated roots to M07 source.
assert not any(Path(missing)==Path(p) or Path(missing) in Path(p).parents for p in owner.SOURCE_HASHES)
restored=routes+[{'src':missing,'dst':missing,'readonly':True,'directory':True}];assert visible(missing,restored) is not None
victim=str(S/'native_diagnostic.py');assert visible(victim,routes)
shadow=routes+[{'src':None,'dst':str(S),'readonly':False,'directory':True}];assert visible(victim,shadow) is None
remapped=routes+[{'src':str(S.parent/'typed-capsule-preparation-1'),'dst':str(S),'readonly':True,'directory':True}];assert visible(victim,remapped) is None
# A writable child hides a readonly ancestor even when the ancestor remains.
assert visible(victim,routes+[{'src':str(S),'dst':victim,'readonly':False,'directory':False}]) is None
result={'scope':__doc__,'status':'PASS_ACTUAL_M07_CREATEARGV_DESTINATION_RO_COVERAGE','owner_sha256':obj.owner_sha,'source_pin_count':len(owner.SOURCE_HASHES),'required_path_count':len(inputs),'actual_create_argv':argv,'effective_routes':rows,'negative_controls':['actual_P12_missing_root_uncovered','synthetic_tmpfs_same_destination_shadow','synthetic_foreign_RO_same_destination_shadow','synthetic_RW_child_shadow'],'positive_control':'Actual original P12 missing root becomes visible only after exact identity RO restoration in model; not added to unrelated M07 production mounts.','M07_source_correction_required':False,'production_sources_changed':False,'limits':['Source/argv destination model only; no Docker mount execution or container filesystem observation.','Image-provided /usr/bin/python3,stdlib and QEMU are not claimed HOSTbind inputs; original pinned image/QEMU controls remain.','No guest/native/release credit.'],'native_result':None}
fd=os.open(D/'COVERAGE-RESULT.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'status':result['status'],'source_pins':len(owner.SOURCE_HASHES),'required_paths':len(inputs),'correction_required':False}))
