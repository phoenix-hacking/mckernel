"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run only after Root's final actual reviewed dependency materialization. Pure metadata
traversal: no observe(), guard(), proc, query, workload, or synthetic source binding.
"""
from pathlib import Path
import hashlib,importlib.util,json
D=Path(__file__).resolve().parent;H=D/'recursive-current62/history'
def ref(p):
 p=Path(p).resolve();b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
outer=load(D/'observe_current64_current118_postjoin.py','actual_final_outer');recur=outer.load(outer.PINS['runtime_base_source'],'actual_final_recursive');assert recur.ref(recur.HERE/'history/observe_bfd_current61.py')==recur.PINS['history_runtime_source']
sixtyone=recur.load(recur.PINS['history_runtime_source'],'actual_final_61');assert sixtyone.ref(H/'observe_bfd_current60_history.py')==sixtyone.PINS['current60_source']
# This invokes the exact unmodified historical validator and authenticates all
# of its real data. It follows the same static source constant as observe().
ledger,free,ext,actors=sixtyone.validate_current(sixtyone.CURRENT)
sixty=sixtyone.load(sixtyone.PINS['current60_source'],'actual_final_60');assert Path(sixty.__file__).resolve()==H/'observe_bfd_current60_history.py'
rows,common,oldactors=sixty.validate_current();assert Path(common.__file__).resolve()==H/'observe_bfd_root59_history.py' and sixty.PINS['common']==ref(H/'observe_bfd_root59_history.py')
dep=H/'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json';bindings=json.loads(dep.read_bytes());assert sixty.PINS['common_dependencies']==ref(dep) and bindings['observer']==ref(H/'observe_bfd_root59_history.py')
# Existing API only configures authenticated exact source/review metadata; its
# returned guard and physical objects are never asked to observe or execute.
common.configured_dependencies(bindings)
root61=json.loads((H/'ROOT61-RUNTIME-DEPENDENCIES.json').read_bytes());assert root61['observer']==ref(H/'observe_bfd_current61.py') and root61['guard_configuration']==bindings['account_window_guard_configuration']
ret=outer.validate_retained();bound=json.loads((D/'BATCH-OUTER-BINDINGS.json').read_bytes());outer.attach_custody(bound,ret);outer.validate_pending_ledger(outer.checked(bound['ledger']),ret);assert len(ret['actors'])==143 and len(ret['actors'])+15==158
print(json.dumps(dict(status='PASS_FINAL_ACTUAL_61_60_COMMON_CONFIGURED_METADATA_ROUTING',history61=ref(H/'observe_bfd_current61.py'),current60=ref(H/'observe_bfd_current60_history.py'),actual_pins=ref(H/'ACTUAL-PINS.json'),root59=ref(H/'observe_bfd_root59_history.py'),common_dependencies=ref(dep),history61_dependencies=ref(H/'ROOT61-RUNTIME-DEPENDENCIES.json'),outer_bindings=ref(D/'BATCH-OUTER-BINDINGS.json'),historical_actors=len(actors),current_frontier=158,nonces=len(outer.checked(bound['ledger'])['consumed_nonces']),guard_observe_or_external_queries=0,runtime_authority=None),indent=2))
