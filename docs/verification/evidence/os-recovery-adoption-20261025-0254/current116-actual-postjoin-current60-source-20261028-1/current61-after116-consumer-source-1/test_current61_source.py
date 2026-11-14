"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure prospective Root61 fixture; genuine Root61 readiness remains unbound.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json
D=Path(__file__).resolve().parent;E=D.parent.parent
spec=importlib.util.spec_from_file_location('unbound_current61_source',D/'observe_current61.TEMPLATE.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=[]
def reject(call,label):
 try:call()
 except (ValueError,AssertionError,KeyError):checks.append(label)
 else:raise AssertionError('negative accepted '+label)
reject(lambda:m.validate_current(None),'unbound actual Root61 refuses readiness')
m.PINS=json.loads((D/'RETAINED-ACTUAL-PINS.json').read_bytes())
old=m.load(m.PINS['current60_source'],'actual_current60_data_only');rows,_common,actors=old.validate_current();assert len(actors)==53
capture=m.checked(m.PINS['capture2']);joined=m.checked(m.PINS['capture2_join'])
assert joined['pid']==1907223 and int(joined['birth'])==96691234 and joined['positive_direct_wait4_join'] is True and joined['returncode']==0 and joined['streams_closed'] is True and joined['process_group_absent'] is True and not joined['remaining_group_members'] and not joined['group_observation_errors']
checks.append('actual Root60/capture2/ownedCPU0join retained data authenticates')
free_path=E/'new-window-observer-guard-independent-review-20261028-1/CURRENT116-POSTJOIN-REVIEW-1/CURRENT-FREE.json';free_ref=m.ref(free_path);free=json.loads(free_path.read_bytes())
# This copied ledger is a prospective parser fixture only, never persisted as Root61.
ledger=copy.deepcopy(rows['ledger60']);ledger['current_physical_clearance_pending']=False;ledger['latest_accepted_free_boundary']=free_ref
m.CURRENT=dict(latest_free=free_ref)
assert m.validate_adoption(ledger,free,capture,rows['ledger60'])
checks.append('genuine independentfree/capture2 with explicitly prospective ledger fixture validates parser')
for label,edit in [
 ('reject extra consumednonce',lambda l,f,c:l['consumed_nonces'].append('f'*32)),
 ('reject pendingphysical',lambda l,f,c:l.__setitem__('current_physical_clearance_pending',True)),
 ('reject nativeasordinary',lambda l,f,c:l['current_native_operation'].__setitem__('nonce','f'*32)),
 ('reject nonindependent receipt',lambda l,f,c:f.__setitem__('independent',False)),
 ('reject capture1 substitution',lambda l,f,c:f.__setitem__('actual_capture_number',1)),
 ('reject capture1 acceptance',lambda l,f,c:f.__setitem__('capture1_accepted',True)),
 ('reject wrongcapturebytes',lambda l,f,c:f['actual_postjoin_observation'].__setitem__('sha256','0'*64)),
 ('reject newbuildrelabelnative',lambda l,f,c:f.__setitem__('native_operation_reclassified_as_ordinary',True)),
 ('reject custodyactive',lambda l,f,c:f.__setitem__('active_shared_records_absent',False)),
 ('reject capturecleanup',lambda l,f,c:c.__setitem__('signals_cleanup_workloads',1)),
 ('reject missingactor',lambda l,f,c:c['all53_prior_and_new_actors_absent'].pop()),
]:
 l,f,c=copy.deepcopy((ledger,free,capture));edit(l,f,c);reject(lambda:m.validate_adoption(l,f,c,rows['ledger60']),label)
for path in [D/'observe_current61.TEMPLATE.py',D/'bind_current61.py']:ast.parse(path.read_bytes())
old227=E/'m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/original227-contract-case-correction-source-1/process227.RETAINED-COMPOSE.CONTRACT-BOUND.json';manifest=json.loads(old227.read_bytes());overlay=json.loads(Path(manifest['staging']['overlay_manifest']['path']).read_bytes())
assert manifest['artifacts']['mckernel_image']['sha256']==overlay['final_map']['images/mckernel.img']['sha256']=='60e62f97ef48ecaf14174af1c5b75d7181969f439c1b45c618d6c16d4bc40d57'
checks.append('original227actualkernel manifest and embeddedoverlay areCURRENT11060e, not116')
result=dict(scope=__doc__.splitlines()[0],decision='PASS_UNBOUND_CURRENT61_SOURCE_CONTROLS_ACTUAL61_READINESS_NULL',count=len(checks),checks=checks,actual_Root61=None,actual_bound_observer=None,actual_independent_current_free=free_ref,runtime_authority=None,guard_calls=0,observations=0)
with (D/'PURE-CONTROLS.json').open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
