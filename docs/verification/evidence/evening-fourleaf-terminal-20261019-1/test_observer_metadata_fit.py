"""Actual observer.main metadata path/currentgate under256MiB softAS; root effects stubbed."""
from pathlib import Path
import types,json,hashlib,resource,builtins,sys
T=Path(__file__).resolve().parent;F=T/'observer-metadata-fit-1';F.mkdir()
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(F/'pre-execution-source-map.json').write_text(json.dumps({x:ref(T/x) for x in ['test_observer_metadata_fit.py','observe_four_leaf_image_retirement.py','cleanup_fourleaf.py']},indent=2)+'\n')
p=T/'observe_four_leaf_image_retirement.py';m=types.ModuleType(p.stem);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__)
class StopBeforeRootEffects(Exception):pass
realexec=builtins.exec;realset=resource.setrlimit;events=[]
def effects_omitted(code,namespace):
 realexec(code,namespace)
 if 'typed_source_binding' in namespace and 'configure' in namespace:
  def stop(*a,**k):events.append('STOP_BEFORE_ROOT_DIRECTORY_LOCK_OR_OBSERVATION');raise StopBeforeRootEffects()
  namespace['directory']=stop
 else:events.append('ACTUAL_SHARED_GATE_LOADED')
def limits(which,pair):
 if which==resource.RLIMIT_AS:
  assert pair==(268435456,2147483648);realset(which,(268435456,1073741824));events.append('ACTUAL_SOFT256MiB_HARD1GiB')
 else:realset(which,pair)
m.exec=effects_omitted;m.resource.setrlimit=limits;m.os.getuid=lambda:0;m.os.geteuid=lambda:0;m.validate_observation_release=lambda *a:events.append('ROOT_RELEASE_VALIDATION_STUBBED_NO_AUTHORITY')
args=['--git-commit','0'*40,'--git-tree','0'*40,'--observation-release',str(T/'PENDING-root-release.json'),'--observation-release-sha256','0'*64]
try:m.main(args)
except StopBeforeRootEffects:pass
else:raise AssertionError('did not stop before root effects')
assert 'ACTUAL_SHARED_GATE_LOADED' in events and events[-1]=='STOP_BEFORE_ROOT_DIRECTORY_LOCK_OR_OBSERVATION'
raw=Path('/proc/self/status').read_text();vm=[l for l in raw.splitlines() if l.startswith(('VmPeak:','VmSize:','VmRSS:'))]
(F/'summary.json').write_text(json.dumps(dict(status='PASS_ACTUAL_OBSERVER_MAIN_METADATA_AND_SHARED_GATE_SOFT256MiB_ONLY',events=events,address_space=resource.getrlimit(resource.RLIMIT_AS),current_process_memory=vm,root_effects=0,subprocess_calls=0,actual_observer_outputs=0,source=ref(p)),indent=2)+'\n');print('PASS observer.main/sharedgate actualsoft256MiB; stoppedbefore rootlock/effects')
