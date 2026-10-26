"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic retained metadata only; no process, FD, root, owner, query or workload calls.
"""
import copy,hashlib,importlib.util,json,unittest
from pathlib import Path
import growth_chain_validator as v

def r(name):return dict(path='/fixture/'+name,bytes=1,sha256='0'*64)
def review(decision,payload):return dict(decision=decision,implementation_ownership=False,reviewer='independent-private-fixture',payload_sha256=hashlib.sha256(v.canonical(payload)).hexdigest())
def fixture():
 docs={};qual=r('qualified');original=r('original');original['sha256']=v.ORIGINAL_POSTCHECK_SHA
 docs[original['path']]=dict(original_postcheck_fault_preserved=dict(event='QUARANTINE',data=dict(fd_closed=False,error="ValueError('automatic ext4 reserve ratio differs')")),reserve_before=288358,reserve_after=288358)
 docs[qual['path']]=dict(decision='PASS_QUALIFIED_ONLINE_GROWTH_POSTCONDITIONS',implementation_ownership=False,reviewer='independent',original_readonly_proof=original,absolute_reserved_blocks=288358)
 hops=[]
 for i in (0,1):
  prefix='hop'+str(i);target=v.TARGETS[i];hop={k:r(prefix+'-'+k) for k in ('source_packet','copy_review','actual_copy','retire_review','pidfd_retirement','old_actual_joins')};hop['target']=target
  packet=dict(target=target,phase='COPY_ONLY',sources=v.PHASE_SOURCES[i],copy_review=hop['copy_review'],qualified_postconditions=qual,actual_target_pins=v.PHASE_SOURCES[i]['ACTUAL-TARGET-PINS.json'])
  docs[hop['source_packet']['path']]=packet;docs[hop['copy_review']['path']]=review('PASS_COPY_ONLY',{k:x for k,x in packet.items() if k!='copy_review'})
  successor=dict(pid=1289073,birth=85353159,parent=1289070,pgid=1289064,fd=4) if i==0 else dict(v.FINAL_SUCCESSOR)
  ready=dict(event='RAWREADY',wall=10+20*i,source_packet=hop['source_packet'],data=dict(old_target=target,qualified_postconditions=qual,same_description_observed=True,lock_origin_pid=1281419,device=27,inode=4,holder_pid=target['pid'],holder_fd=4,retained_fd=4,lock=['FLOCK','ADVISORY','WRITE','1281419','00:1b:4','0','EOF'],successor=successor,consumed_copy=r(prefix+'-copy')))
  docs[hop['actual_copy']['path']]=ready;docs[ready['data']['consumed_copy']['path']]=dict(source_packet=hop['source_packet'],copy_review=hop['copy_review'])
  payload=dict(action='RETIRE',author='/root',target=target,source_packet=hop['source_packet'],ready=hop['actual_copy'],qualified_postconditions=qual,signal=9,target_pidfd_signal_count=1,expires_wall=100)
  retired=dict(event='PIDFD-EXIT',wall=20+20*i,source_packet=hop['source_packet'],data=dict(ready=hop['actual_copy'],old_target=target,positive_pidfd_exit=True,nonchild_waitpid_claim=False,retained_fd=4,consumed_retire=r(prefix+'-retire')))
  docs[hop['pidfd_retirement']['path']]=retired;docs[retired['data']['consumed_retire']['path']]=dict(payload=payload,review=hop['retire_review']);docs[hop['retire_review']['path']]=review('PASS_RETIRE_ONLY',payload)
  pid,birth,tool=v.CALLERS[i]
  docs[hop['old_actual_joins']['path']]=dict(decision='PASS_ACTUAL_OLD_GROWTH_CALLER_TOOL_JOIN',old_target=target,caller=dict(pid=pid,birth=birth),tool_cell_id=tool,pidfd_exit=hop['pidfd_retirement'],caller_positive_wait=True,tool_positive_join=True,group_absent=True,closed_streams=True,actual_evidence=[r(prefix+'-tool'),r(prefix+'-parent')])
  docs[r(prefix+'-tool')['path']]=json.dumps(dict(exit_code=0)).encode();docs[r(prefix+'-parent')['path']]=json.dumps(dict(joined=True,returncode=-9)).encode()
  hops.append(hop)
 first,final=hops
 first.update(quarantine=r('first-quarantine'),failed_close_attempt=r('first-failed-close'),actual_normal_close=None,consumed_close=None)
 docs[first['quarantine']['path']]=dict(event='QUARANTINE',wall=21,source_packet=first['source_packet'],data=dict(phase='RETIRED',fd=4,copy_possible=True,closed=False,error="ValueError('same account guard')"))
 payload=dict(action='CLOSE',author='/root',target=v.TARGETS[0],source_packet=first['source_packet'],ready=first['actual_copy'],pidfd_exit=first['pidfd_retirement'])
 failed_review=r('first-failed-close-review');docs[first['failed_close_attempt']['path']]=dict(payload=payload,review=failed_review);docs[failed_review['path']]=review('PASS_CLOSE_ONLY',payload)
 docs[v.PHASE_SOURCES[1]['ACTUAL-TARGET-PINS.json']['path']]=dict(pins=dict(prior_actual_copy=first['actual_copy'],prior_quarantine=first['quarantine'],prior_pidfd_exit=first['pidfd_retirement'],prior_old_actual_joins=first['old_actual_joins'],prior_source_packet=first['source_packet'],prior_recovery_source=v.PHASE_SOURCES[0]['recover_growth_custody.py'],prior_ofd_source=v.PHASE_SOURCES[0]['ofd_primitives.py']))
 final.update(close_review=r('final-close-review'),actual_normal_close=r('final-close'),new_actual_joins=r('final-new-joins'))
 physical=r('final-preclose-physical')
 payload=dict(action='CLOSE',author='/root',target=v.TARGETS[1],source_packet=final['source_packet'],ready=final['actual_copy'],pidfd_exit=final['pidfd_retirement'],old_actual_joins=final['old_actual_joins'],qualified_postconditions=qual,current_fs_acceptance=physical,expires_wall=100)
 docs[final['close_review']['path']]=review('PASS_CLOSE_ONLY',payload);docs[r('final-close-consumed')['path']]=dict(payload=payload,review=final['close_review'])
 docs[final['actual_normal_close']['path']]=dict(event='NORMAL-CLOSE',wall=50,source_packet=final['source_packet'],data=dict(ready=final['actual_copy'],pidfd_exit=final['pidfd_retirement'],successor_fd_closed=True,original_helper_normal_close_claim=False,predecessor_helper_normal_close_claim=False,consumed_close=r('final-close-consumed')))
 docs[final['new_actual_joins']['path']]=dict(decision='PASS_ACTUAL_RECOVERY_CALLER_TOOL_JOIN',actual_normal_close=final['actual_normal_close'],caller_pid=v.FINAL_SUCCESSOR['parent'],tool_cell_id=v.FINAL_TOOL,caller_positive_wait=True,tool_positive_join=True,group_absent=True,closed_streams=True,actual_evidence=[r('final-tool'),r('final-parent')]);docs[r('final-tool')['path']]=json.dumps(dict(exit_code=0)).encode();docs[r('final-parent')['path']]=json.dumps(dict(joined=True,returncode=0)).encode()
 docs[physical['path']]=dict(decision='PASS_RECOVERED_GROWTH_CURRENT_PHYSICAL',implementation_ownership=False,reviewer='independent',ready=final['actual_copy'],pidfd_exit=final['pidfd_retirement'],old_actual_joins=final['old_actual_joins'],qualified_postconditions=qual,successor_fd_still_held=True)
 recovery=dict(schema='mckernel.scratch-growth-two-hop-custody-recovery.v1',hops=hops,original_helper_normal_close_claim=False,predecessor_helper_normal_close_claim=False,original_postcheck_failure=original,qualified_online_postconditions=qual,current_physical_acceptance=physical)
 growth=dict(custody_recovery=recovery,normal_fd_release=r('normal-fd-release'),closed_wall=102)
 docs[r('normal-fd-release')['path']]=dict(closed_wall=101,actual_normal_close=final['actual_normal_close'],new_actual_joins=final['new_actual_joins'],successor=docs[final['actual_copy']['path']]['data']['successor'],original_helper_normal_close_claim=False,predecessor_helper_normal_close_claim=False)
 for sources in v.PHASE_SOURCES:
  for ref in sources.values():docs.setdefault(ref['path'],b'fixture source bytes; not execution authority')
 return growth,docs

def load_from(docs):return lambda ref,*_:docs[ref['path']]
class Custody(unittest.TestCase):
 def test_exact_two_hops_preserve_origin_and_only_final_close(self):
  g,docs=fixture();self.assertIs(v.custody_chain(g,load_from(docs)),g)
  self.assertIsNone(g['custody_recovery']['hops'][0]['actual_normal_close'])
 def test_missing_hop_substitution_false_join_or_false_first_close_refused(self):
  cases=[('growth',['custody_recovery','hops'],[]),('growth',['custody_recovery','hops',0,'actual_normal_close'],r('fake-first-close')),('growth',['custody_recovery','hops',0,'consumed_close'],r('fake-first-consumed')),('docs',[r('hop1-old_actual_joins')['path'],'tool_positive_join'],False),('docs',[r('hop0-actual_copy')['path'],'data','lock_origin_pid'],1289073),('docs',[r('hop0-actual_copy')['path'],'data','successor','birth'],1),('docs',[r('final-close')['path'],'data','ready'],r('hop0-actual_copy')),('docs',[r('final-close')['path'],'data','predecessor_helper_normal_close_claim'],True),('docs',[r('hop1-retire')['path'],'review'],r('unrelated-review')),('docs',[r('first-quarantine')['path'],'data','closed'],True),('docs',[r('normal-fd-release')['path'],'successor'],dict(pid=1289073)),('docs',[r('final-new-joins')['path'],'closed_streams'],False),('docs',[r('final-new-joins')['path'],'caller_pid'],1289070),('docs',[r('final-new-joins')['path'],'tool_cell_id'],'44584'),('docs',[r('final-tool')['path']],json.dumps(dict(exit_code=1)).encode())]
  for where,path,value in cases:
   g,docs=copy.deepcopy(fixture());target=g if where=='growth' else docs
   for key in path[:-1]:target=target[key]
   target[path[-1]]=value
   with self.subTest(path=path),self.assertRaises((ValueError,KeyError)):v.custody_chain(g,load_from(docs))

def head_fixture():
 # Reuse the existing unchanged-parent synthetic geometry fixture, not its tests.
 p=Path(v.PARENT['path']).parent/'test_growth_successor.py';spec=importlib.util.spec_from_file_location('retained_geometry_fixture',p);m=importlib.util.module_from_spec(spec)
 import sys;sys.path.insert(0,str(p.parent));spec.loader.exec_module(m)
 f=m.Growth().fixture();bundle,stagehead,native,request,stagelive,window,parentdocs=f
 g,docs=fixture();parentdocs['growth']['custody_recovery']=g['custody_recovery'];parentdocs['normal_fd_release'].update(docs.pop(r('normal-fd-release')['path']))
 # Normalize synthetic ref paths from original fixture to the explicit dictionary.
 for name,value in parentdocs.items():docs[name]=value
 native_ref=bundle['latest_operation'];growth_ref=bundle['growth_closure']
 stage_ref=r('stage');bundle['accepted_growth_stage']=stage_ref
 docs[stage_ref['path']]=dict(schema='mckernel.sdk7.accepted-growth-stage.v1',growth_closure=growth_ref,native2_operation=native_ref,operation_head=r('stage-head'),live_observation=r('stage-live'),scope='historical accepted growth stage, not current admission')
 docs[r('stage-head')['path']]=stagehead;docs[r('stage-live')['path']]=stagelive;docs[native_ref['path']]=native
 head=dict(schema='mckernel.serial-operation-head.v3',latest_container_operation=native_ref,latest_serial_operation=growth_ref,physical_prerequisites=[growth_ref],accepted_growth_stage=stage_ref,no_unlisted_intervening_operation=True,consumed_nonces=['native','grow'],container_operations_after_growth=[])
 live=copy.deepcopy(stagelive)
 return bundle,head,native,request,live,window,docs
class Head(unittest.TestCase):
 def call(self,f):return v.validate_growth_chain(*f[:-1],load=load_from(f[-1]))
 def test_parent696_at_accepted_stage_then_truthful_growth_head(self):self.assertEqual(self.call(head_fixture())['after'],v.parent_module().AFTER)
 def memory(self):
  f=head_fixture();bundle,head,native,request,live,window,docs=f;memory=r('memory');bundle['latest_operation']=memory
  latest=dict(schema='mckernel.owned-operation-closure.v1',status='PASS_OWNED_OPERATION_CLOSED',nonce='memory',boot_id='boot',closed_wall=110,container='memoryCID',terminal=r('memory-terminal'),actual_postjoin=r('memory-postjoin'),caller_join=r('memory-join'),owner_export=r('memory-export'),independent_retirement_acceptance=r('memory-acceptance'),direct_child_joined=True,group_absent=True,closed_streams=True,holder_retired=True)
  f=list(f);f[2]=latest;docs[memory['path']]=latest
  head.update(latest_container_operation=memory,latest_serial_operation=memory,container_operations_after_growth=[memory],consumed_nonces=['native','grow','memory'])
  live.update(latest_serial_operation=memory,clock=dict(wall=112))
  docs[r('memory-acceptance')['path']]=dict(decision='PASS_ACTUAL_POSTGROWTH_CONTAINER_POSTJOIN_CURRENT_PHYSICAL',independent=True,reviewer='independent',nonce='memory',actual=latest['actual_postjoin'],caller_join=latest['caller_join'],owner_export=latest['owner_export'])
  docs[r('memory-postjoin')['path']]=dict(exact_container_absent='memoryCID',observed_at=111,group_membership_observation=dict(errors=[]));docs[r('memory-join')['path']]=dict(joined=True,finished_at=110.5);docs[r('memory-terminal')['path']]=dict(container='memoryCID',state=dict(Running=False,Paused=False,Restarting=False,Pid=0))
  return f
 def test_real_subsequent_container_does_not_relabel_growth_or_native2(self):
  f=self.memory();g=self.call(f);self.assertNotEqual(f[1]['latest_serial_operation'],f[0]['growth_closure']);self.assertEqual(g['previous_serial_operation']['sha256'],v.parent_module().NATIVE2_SHA)
 def test_stale_unsupported_or_unlisted_current_container_refused(self):
  cases=[(1,['no_unlisted_intervening_operation'],False),(1,['container_operations_after_growth'],[r('memory'),r('unlisted')]),(1,['latest_serial_operation'],r('growth')),(2,['closed_wall'],101),(2,['schema'],'unsupported'),(6,[r('memory-acceptance')['path'],'independent'],False),(6,[r('memory-acceptance')['path'],'actual'],r('old-postjoin')),(6,[r('memory-terminal')['path'],'state','Running'],True)]
  for index,path,value in cases:
   f=copy.deepcopy(self.memory());target=f[index]
   for key in path[:-1]:target=target[key]
   target[path[-1]]=value
   with self.subTest(path=path),self.assertRaises((ValueError,KeyError)):self.call(f)
if __name__=='__main__':unittest.main(verbosity=2)
