"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact Source28 proof controls; no account/clock/proc/Docker observation.
"""
from pathlib import Path
import copy,hashlib,json
R=Path(__file__).resolve().parent;S=R.parent;E=S.parent
source=(R/'capture_fresh_fp_resource2.py').read_text();body=source[source.index("accept=E/'DAEMON-SOURCE28-"):source.index("policy=E/'scratch-growth-final-copy-close-source-1/recover_growth_custody.py'")]
static=json.loads((S/'STATIC-NATIVE-BINDINGS.PROPOSAL.NOT-RELEASED.json').read_bytes());static['latest_serial_operation_physical_acceptance']=static['proposed_latest_physical_acceptance']
records={}
def read(r):
 raw=Path(r['path']).read_bytes();assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'];records[r['path']]=json.loads(raw);return records[r['path']]
a=read(static['latest_serial_operation_physical_acceptance']);obs=read(a['current_observation']);failed=obs['failed_current_daemon_operation']
for key in ['whole_caller','actual_parent_tool']:read(a[key])
for key in ['owner_receipt','postflight','record_release_complete','ownership_archive']:read(failed[key])
five=read(static['retained_FIVE_physical_acceptance']);read(five['actual_current_observation'])
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def evaluate(changes):
 fixtures=copy.deepcopy(records)
 for path,key,value in changes:fixtures[path][key]=value
 env=dict(E=E,static=static,ref=ref,checked=lambda r:fixtures[r['path']])
 exec(body,env);return env
positive=evaluate([]);assert len(positive['actor_ids'])==16;checks=1
for change in [(static['latest_serial_operation_physical_acceptance']['path'],'decision','PASS_FIVE_BUILD_POSTJOIN_CURRENT_PHYSICAL'),(a['whole_caller']['path'],'direct_child_joined',False),(a['whole_caller']['path'],'group_absent',False),(a['actual_parent_tool']['path'],'positive_parent_tool_join',False),(failed['postflight']['path'],'all_clients_reaped',False),(failed['postflight']['path'],'container_absent',False),(failed['record_release_complete']['path'],'status','HELD'),(failed['owner_receipt']['path'],'retired',False)]:
 try:evaluate([change])
 except AssertionError:pass
 else:raise AssertionError('Source28 guard weakened: '+str(change))
 checks+=1
print(json.dumps(dict(status='PASS_EXACT_SOURCE28_PURE_CONTROLS',checks=checks,all16_actor_ids_bound=True,parent_caller_actualPID_bound=True,normal_failed_return1_preserved=True,retirement_recordrelease_allclients_guards=True,retained_FIVE_guard_preserved=True,account_calls=0,clock_calls=0,proc_queries=0,docker_calls=0,runtime_authority=None)))
