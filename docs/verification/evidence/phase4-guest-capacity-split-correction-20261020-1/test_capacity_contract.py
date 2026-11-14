"""Pure capacity decision and metadata-path checks; no Docker or ownership."""
from pathlib import Path
import copy,json,types,tempfile,ast
N=Path(__file__).resolve().parent
owner=types.ModuleType('capacity_fixture');owner.__file__=str(N/'current_fullcrate_owner.py')
exec(compile(Path(owner.__file__).read_bytes(),owner.__file__,'exec'),owner.__dict__)
ast.parse((N/'root-run-current-crates-once.py').read_bytes())
run=Path(owner.__file__).read_text().split('def run(',1)[1]
assert run.index('capacity_before_ownership')<run.index('acquire_heavy_operation')
record=lambda name:{'path':'/scratch/'+name,'device':202,'direct_scratch_child':True,'symlink':False,'escape':False}
host=lambda name:{'path':'/host/'+name,'device':101,'symlink':False,'escape':False}
base={'host_dev':101,'scratch_dev':202,'records':[record(x)for x in ('lease','common','shared')],
      'host_paths':[host(x)for x in ('source','work','evidence','outercapture','admission','output','home','tmp','systemtmp')],
      'docker':host('dockerdata'),'limits':(33554432,33554432),'free':{'host':50000000000,'scratch':14281474048}}
r=owner.capacity_decision(**base);assert r['budgets']=={'host':1543503872,'scratch':771751936}
assert r['floors']=={'host':17179869184,'scratch':12884901888}
checks=[]
def reject(change):
 row=copy.deepcopy(base);change(row)
 try:owner.capacity_decision(**row)
 except RuntimeError:checks.append(True)
 else:raise AssertionError('invalid finite contract accepted')
reject(lambda x:x['host_paths'][0].update(device=202))
reject(lambda x:x['docker'].update(device=202))
reject(lambda x:x['records'][0].update(device=101))
reject(lambda x:x['records'][0].update(direct_scratch_child=False))
reject(lambda x:x['host_paths'][0].update(symlink=True))
reject(lambda x:x['host_paths'][0].update(escape=True))
reject(lambda x:x.update(limits=(-1,33554432)))
reject(lambda x:x.update(limits=(33554432,-1)))
reject(lambda x:x.update(limits=(33554433,33554433)))
reject(lambda x:x['free'].update(host=17179869184+1543503872-1))
reject(lambda x:x['free'].update(scratch=12884901888+771751936-1))
with tempfile.TemporaryDirectory(prefix='capacity-metadata-',dir=N) as temp:
 root=Path(temp);(root/'real').mkdir();(root/'alias').symlink_to(root/'real',target_is_directory=True)
 assert owner.checked_location(str(root/'real'/'future'))['device']==root.stat().st_dev
 for value in (str(root/'alias'/'future'),str(root)+'/real/../escape'):
  try:owner.checked_location(value)
  except RuntimeError:checks.append(True)
  else:raise AssertionError('symlink/noncanonical path accepted')
for name in ('work','owner-evidence','actual-root-owner-1','capacity-admission'):
 assert not (N/name).exists()
print(json.dumps({'status':'PASS_PURE_CAPACITY_AND_REAL_METADATA_PATH_CHECKS','positive_full_roots':1,'negative_vectors':len(checks),'Docker_calls':0,'ownership_records':0,'source_copies':0,'compilers':0}))
