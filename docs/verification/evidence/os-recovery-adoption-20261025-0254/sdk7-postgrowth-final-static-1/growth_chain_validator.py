"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed two-hop custody metadata and truthful post-growth serial-head composition.
No clocks, procfs, lock operations, signals, runtime owners or workload execution.
"""
import hashlib,json,types
from pathlib import Path
PARENT={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/sdk7-142g-consumer-successor-source-1/growth_successor.py', 'bytes': 7611, 'sha256': '696cab2d2f09be636650bc3aa7b590a8f4bee3ff730da3cf8abeea0deede61f7'}
PHASE_SOURCES=[{'recover_growth_custody.py': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/scratch-growth-postcheck-custody-recovery-source-1/recover_growth_custody.py', 'bytes': 16971, 'sha256': '4976f2dced932f670145a8aa03c35e596e7ebcf41b342351c4f69e6010f17b52'}, 'ofd_primitives.py': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/scratch-growth-postcheck-custody-recovery-source-1/ofd_primitives.py', 'bytes': 4830, 'sha256': 'd8061516ada688a956ebb134a977ae4cb69e4a1b36aaaeefaa0126323f12e818'}, 'ACTUAL-TARGET-PINS.json': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/scratch-growth-postcheck-custody-recovery-source-1/ACTUAL-TARGET-PINS.json', 'bytes': 4134, 'sha256': '86d827e59e90338311868c681c447e04b045c2e83c6b2282fdf0da6eb3681957'}}, {'recover_growth_custody.py': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/scratch-growth-final-copy-close-source-1/recover_growth_custody.py', 'bytes': 20587, 'sha256': '04b5c6af885baca472e99e590bf07ae360dacad95487709477cf3d2bf8d6c90a'}, 'ofd_primitives.py': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/scratch-growth-final-copy-close-source-1/ofd_primitives.py', 'bytes': 4830, 'sha256': 'd8061516ada688a956ebb134a977ae4cb69e4a1b36aaaeefaa0126323f12e818'}, 'ACTUAL-TARGET-PINS.json': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/scratch-growth-final-copy-close-source-1/ACTUAL-TARGET-PINS.json', 'bytes': 5199, 'sha256': '66cfa6a5487440a517be3aa3cce6f5b232268a6f1f87eed4001a8ef64f43467c'}, 'canonical_os_goal_credits.py': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/scratch-growth-final-copy-close-source-1/canonical_os_goal_credits.py', 'bytes': 5178, 'sha256': 'adf5187240ed8199746eef3b59b79d4d38c4ae8ac5821c8d8324833926b21ec3'}}]
TARGETS=(dict(pid=1281419,birth=85204892,parent=1281416,pgid=1281414,fd=4,origin=1281419),dict(pid=1289073,birth=85353159,parent=1289070,pgid=1289064,fd=4,origin=1281419))
CALLERS=((1281416,85204885,'40285'),(1289070,85353151,'44584'))
FINAL_SUCCESSOR=dict(pid=1294129,birth=85433672,parent=1294126,pgid=1294125,fd=4)
FINAL_TOOL='68172'
ORIGINAL_POSTCHECK_SHA='7de149914f225425a86dadcea5b44e6d09641db82e711544fd73dc77d9a341fc'
def need(ok,why):
 if not ok:raise ValueError(why)
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def ownref():
 p=Path(__file__).resolve();raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def parent_module():
 raw=Path(PARENT['path']).read_bytes();need(len(raw)==PARENT['bytes'] and hashlib.sha256(raw).hexdigest()==PARENT['sha256'],'frozen-parent696-source')
 m=types.ModuleType('_unchanged_growth696');m.__file__=PARENT['path'];exec(compile(raw,PARENT['path'],'exec'),m.__dict__);return m
def current_sources(bundle,origin,historical_map,load,adapter_ref):
 mapping,review,owner=parent_module().current_sources(bundle,origin,historical_map,load,adapter_ref)
 need(review['recovery_growth_validator']==ownref() and load(bundle['current_source_publication'])['recovery_growth_validator']==ownref(),'current-chain-validator-publication-and-review')
 return mapping,review,owner

def reviewed(review,decision,payload):
 need(review['decision']==decision and review['implementation_ownership'] is False and review['reviewer'] not in ('','/root',None) and review['payload_sha256']==hashlib.sha256(canonical(payload)).hexdigest(),'exact-independent-phase-review')
def join_evidence(doc,load,final=False):
 need(len(doc['actual_evidence'])>=2,'raw-parent-tool-join-evidence')
 rows=[json.loads(load(r,False)) for r in doc['actual_evidence']]
 waits=[row for row in rows if row.get('joined') is True and type(row.get('returncode')) is int]
 tools=[row for row in rows if type(row.get('exit_code')) is int and row['exit_code']==0]
 need(bool(waits) and bool(tools),'actual-positive-parent-wait-and-completed-tool')
 if final:need(any(row['returncode']==0 for row in waits),'final-helper-parent-return-zero')
 if 'actual_original_caller_returncode' in doc:need(any(row['returncode']==doc['actual_original_caller_returncode'] for row in waits),'preserve-actual-predecessor-returncode')

def joined(doc,target,exitref,index,load):
 pid,birth,tool=CALLERS[index]
 need(doc['decision']=='PASS_ACTUAL_OLD_GROWTH_CALLER_TOOL_JOIN' and doc['old_target']==target and doc['caller']==dict(pid=pid,birth=birth) and doc['tool_cell_id']==tool and doc['pidfd_exit']==exitref and all(doc[k] is True for k in ('caller_positive_wait','tool_positive_join','group_absent','closed_streams')),'genuine-corresponding-old-caller-tool-joins')
 join_evidence(doc,load)

def phase(hop,index,qualification,load):
 target=TARGETS[index];packet=load(hop['source_packet']);ready=load(hop['actual_copy']);retired=load(hop['pidfd_retirement'])
 need(hop['target']==target and packet['target']==target and packet['phase']=='COPY_ONLY' and packet['sources']==PHASE_SOURCES[index] and packet['copy_review']==hop['copy_review'] and packet['qualified_postconditions']==qualification,'exact-custody-hop-source-packet-target')
 for r in packet['sources'].values():load(r,False)
 reviewed(load(hop['copy_review']),'PASS_COPY_ONLY',{k:v for k,v in packet.items() if k!='copy_review'})
 need(ready['event']=='RAWREADY' and ready['source_packet']==hop['source_packet'] and ready['data']['old_target']==target and ready['data']['qualified_postconditions']==qualification and ready['data']['same_description_observed'] is True and ready['data']['lock_origin_pid']==1281419 and ready['data']['device']==27 and ready['data']['inode']==4 and ready['data']['holder_pid']==target['pid'] and ready['data']['holder_fd']==target['fd'] and ready['data']['lock']==['FLOCK','ADVISORY','WRITE','1281419','00:1b:4','0','EOF'],'actual-same-OFD-hop-with-immutable-origin')
 marker=load(ready['data']['consumed_copy']);need(marker['source_packet']==hop['source_packet'] and marker['copy_review']==hop['copy_review'],'actual-consumed-copy')
 need(retired['event']=='PIDFD-EXIT' and retired['source_packet']==hop['source_packet'] and retired['data']['ready']==hop['actual_copy'] and retired['data']['old_target']==target and retired['data']['positive_pidfd_exit'] is True and retired['data']['nonchild_waitpid_claim'] is False,'actual-hop-pidfd-exit-no-invented-wait')
 consumed=load(retired['data']['consumed_retire']);payload=consumed['payload']
 need(consumed['review']==hop['retire_review'] and payload['action']=='RETIRE' and payload['author']=='/root' and payload['target']==target and payload['source_packet']==hop['source_packet'] and payload['ready']==hop['actual_copy'] and payload['qualified_postconditions']==qualification and payload['signal']==9 and payload['target_pidfd_signal_count']==1 and retired['wall']<=payload['expires_wall']<=1793100290.0,'exact-consumed-one-pidfd-retirement')
 reviewed(load(hop['retire_review']),'PASS_RETIRE_ONLY',payload)
 joins=load(hop['old_actual_joins']);joined(joins,target,hop['pidfd_retirement'],index,load)
 own=ready['data']['successor'];need(ready['data']['retained_fd']==own['fd'] and retired['data']['retained_fd']==own['fd'] and ready['wall']<=retired['wall'],'exact-held-copy-fd-and-phase-order')
 need(all(type(own[k]) is int and own[k]>0 for k in ('pid','birth','parent','pgid')) and type(own['fd']) is int and own['fd']>=0,'positive-successor-identity')
 return packet,ready,retired,own

def custody_chain(growth,load):
 recovery=growth['custody_recovery'];need(recovery['schema']=='mckernel.scratch-growth-two-hop-custody-recovery.v1' and len(recovery['hops'])==2 and recovery['original_helper_normal_close_claim'] is False and recovery['predecessor_helper_normal_close_claim'] is False and recovery['original_postcheck_failure']['sha256']==ORIGINAL_POSTCHECK_SHA,'explicit-exact-two-hop-recovery')
 original=load(recovery['original_postcheck_failure']);fault=original['original_postcheck_fault_preserved']
 need(fault['event']=='QUARANTINE' and fault['data']['fd_closed'] is False and fault['data']['error']=="ValueError('automatic ext4 reserve ratio differs')" and original['reserve_before']==original['reserve_after']==288358,'original-failed-observer-and-reserve-preserved')
 qualification=recovery['qualified_online_postconditions'];qualified=load(qualification)
 need(qualified['decision']=='PASS_QUALIFIED_ONLINE_GROWTH_POSTCONDITIONS' and qualified['implementation_ownership'] is False and qualified['reviewer'] not in ('','/root',None) and qualified['original_readonly_proof']==recovery['original_postcheck_failure'] and qualified['absolute_reserved_blocks']==288358,'qualified-actual-online-growth')
 first,final=recovery['hops'];p0,r0,e0,s0=phase(first,0,qualification,load);p1,r1,e1,s1=phase(final,1,qualification,load)
 need({k:s0[k] for k in ('pid','birth','parent','pgid','fd')}=={k:TARGETS[1][k] for k in ('pid','birth','parent','pgid','fd')},'hop-continuity-current-custodian-not-lock-origin')
 need({k:s1[k] for k in FINAL_SUCCESSOR}==FINAL_SUCCESSOR,'exact-actual-final-custodian')
 quarantine=load(first['quarantine'])
 need(first['actual_normal_close'] is None and first['consumed_close'] is None and quarantine['event']=='QUARANTINE' and quarantine['source_packet']==first['source_packet'] and quarantine['data']['phase']=='RETIRED' and quarantine['data']['fd']==TARGETS[1]['fd'] and quarantine['data']['copy_possible'] is True and quarantine['data']['closed'] is False and quarantine['data']['error']=="ValueError('same account guard')",'first-helper-held-quarantine-no-false-close')
 failed=load(first['failed_close_attempt']);payload=failed['payload']
 need(payload['action']=='CLOSE' and payload['author']=='/root' and payload['target']==TARGETS[0] and payload['source_packet']==first['source_packet'] and payload['ready']==first['actual_copy'] and payload['pidfd_exit']==first['pidfd_retirement'],'preserved-unconsumed-first-close-attempt')
 reviewed(load(failed['review']),'PASS_CLOSE_ONLY',payload)
 pins=load(p1['actual_target_pins']);prior=pins['pins']
 need(p1['actual_target_pins']==PHASE_SOURCES[1]['ACTUAL-TARGET-PINS.json'] and prior['prior_actual_copy']==first['actual_copy'] and prior['prior_quarantine']==first['quarantine'] and prior['prior_pidfd_exit']==first['pidfd_retirement'] and prior['prior_old_actual_joins']==first['old_actual_joins'] and prior['prior_source_packet']==first['source_packet'] and prior['prior_recovery_source']==PHASE_SOURCES[0]['recover_growth_custody.py'] and prior['prior_ofd_source']==PHASE_SOURCES[0]['ofd_primitives.py'],'second-copy-actual-predecessor-pins')
 # Exact final source checks absence of first CONSUMED-CLOSE before acquisition;
 # its genuine reviewed RAWREADY binds that source/packet, never a JSON close claim.
 need(e0['wall']<=quarantine['wall']<=r1['wall']<=e1['wall'],'actual-two-hop-custody-order')
 closed=load(final['actual_normal_close']);consume=load(closed['data']['consumed_close']);payload=consume['payload']
 need(closed['event']=='NORMAL-CLOSE' and closed['source_packet']==final['source_packet'] and closed['data']['ready']==final['actual_copy'] and closed['data']['pidfd_exit']==final['pidfd_retirement'] and closed['data']['successor_fd_closed'] is True and closed['data']['original_helper_normal_close_claim'] is False and closed['data']['predecessor_helper_normal_close_claim'] is False,'only-final-actual-normal-close')
 need(consume['review']==final['close_review'] and payload['action']=='CLOSE' and payload['author']=='/root' and payload['target']==TARGETS[1] and payload['source_packet']==final['source_packet'] and payload['ready']==final['actual_copy'] and payload['pidfd_exit']==final['pidfd_retirement'] and payload['old_actual_joins']==final['old_actual_joins'] and payload['qualified_postconditions']==qualification and payload['current_fs_acceptance']==recovery['current_physical_acceptance'] and closed['wall']<=payload['expires_wall']<=1793100290.0,'exact-consumed-final-close')
 reviewed(load(final['close_review']),'PASS_CLOSE_ONLY',payload)
 joins=load(final['new_actual_joins']);need(joins['decision']=='PASS_ACTUAL_RECOVERY_CALLER_TOOL_JOIN' and joins['actual_normal_close']==final['actual_normal_close'] and joins['caller_pid']==s1['parent'] and joins['tool_cell_id']==FINAL_TOOL and all(joins[k] is True for k in ('caller_positive_wait','tool_positive_join','group_absent','closed_streams')) and len(joins['actual_evidence'])>=2,'genuine-final-helper-parent-tool-joins')
 join_evidence(joins,load,final=True)
 need(e1['wall']<=closed['wall'],'actual-final-close-after-pidfd-exit')
 release=load(growth['normal_fd_release'])
 need(closed['wall']<=release['closed_wall']<=growth['closed_wall'],'final-close-release-growth-order')
 need(release['actual_normal_close']==final['actual_normal_close'] and release['new_actual_joins']==final['new_actual_joins'] and release['successor']==s1 and release['original_helper_normal_close_claim'] is False and release['predecessor_helper_normal_close_claim'] is False,'normal-release-names-final-successor-only')
 physical=load(recovery['current_physical_acceptance'])
 need(physical['decision']=='PASS_RECOVERED_GROWTH_CURRENT_PHYSICAL' and physical['implementation_ownership'] is False and physical['reviewer'] not in ('','/root',None) and physical['ready']==final['actual_copy'] and physical['pidfd_exit']==final['pidfd_retirement'] and physical['old_actual_joins']==final['old_actual_joins'] and physical['qualified_postconditions']==qualification and physical['successor_fd_still_held'] is True,'exact-final-preclose-current-physical')
 return growth

def validate_growth_chain(bundle,head,latest,request,live,window,load):
 parent=parent_module()
 stage=load(bundle['accepted_growth_stage'])
 need(stage['schema']=='mckernel.sdk7.accepted-growth-stage.v1' and stage['growth_closure']==bundle['growth_closure'] and stage['native2_operation']['sha256']==parent.NATIVE2_SHA and stage['scope']=='historical accepted growth stage, not current admission','separate-accepted-growth-stage')
 stagebundle=dict(bundle,latest_operation=stage['native2_operation'])
 growth=parent.growth_chain(stagebundle,load(stage['operation_head']),load(stage['native2_operation']),request,load(stage['live_observation']),window,load)
 custody_chain(growth,load)
 need(head['schema']=='mckernel.serial-operation-head.v3' and head['latest_container_operation']==bundle['latest_operation'] and head['physical_prerequisites']==[bundle['growth_closure']] and head['accepted_growth_stage']==bundle['accepted_growth_stage'] and head['no_unlisted_intervening_operation'] is True and 'no_intervening_operation' not in head,'truthful-postgrowth-v3-head')
 consumed=head['consumed_nonces'];need(isinstance(consumed,list) and len(consumed)==len(set(consumed)) and request['nonce'] not in consumed and growth['nonce'] in consumed and latest['nonce'] in consumed,'complete-current-consumed-nonce-ledger')
 need(live['growth_closure']==bundle['growth_closure'] and live['actual_backing_identity']==parent.AFTER and live['latest_serial_operation']==head['latest_serial_operation'] and live['clock']['wall']>=load(growth['fresh_physical_acceptance'])['observed_wall'],'current-physical-after-growth')
 subsequent=head['container_operations_after_growth']
 if bundle['latest_operation']==stage['native2_operation']:
  need(subsequent==[] and head['latest_serial_operation']==bundle['growth_closure'],'no-invented-postgrowth-container')
 else:
  need(subsequent==[bundle['latest_operation']] and head['latest_serial_operation']==bundle['latest_operation'] and latest['schema']=='mckernel.owned-operation-closure.v1' and latest['status']=='PASS_OWNED_OPERATION_CLOSED' and latest['closed_wall']>=growth['closed_wall'] and latest['boot_id']==window['boot_id'] and all(latest[k] is True for k in ('direct_child_joined','group_absent','closed_streams','holder_retired')),'one-supported-postgrowth-container-closure')
  acceptance=load(latest['independent_retirement_acceptance'])
  need(acceptance['decision']=='PASS_ACTUAL_POSTGROWTH_CONTAINER_POSTJOIN_CURRENT_PHYSICAL' and acceptance['independent'] is True and acceptance['reviewer'] not in ('','/root',None) and acceptance['nonce']==latest['nonce'] and acceptance['actual']==latest['actual_postjoin'] and acceptance['caller_join']==latest['caller_join'] and acceptance['owner_export']==latest['owner_export'],'independent-exact-postgrowth-container-acceptance')
  actual=load(latest['actual_postjoin']);terminal=load(latest['terminal']);join=load(latest['caller_join'])
  need(actual['exact_container_absent']==latest['container']==terminal['container'] and actual['observed_at']>=latest['closed_wall'] and live['clock']['wall']>=actual['observed_at'] and join['joined'] is True and join['finished_at']<=actual['observed_at'],'actual-subsequent-container-and-join-provenance')
  need(terminal['state']['Running'] is False and terminal['state']['Paused'] is False and terminal['state']['Restarting'] is False and terminal['state']['Pid']==0 and actual['group_membership_observation']['errors']==[],'subsequent-container-nonrunning-and-resolved-groups')
 return growth
