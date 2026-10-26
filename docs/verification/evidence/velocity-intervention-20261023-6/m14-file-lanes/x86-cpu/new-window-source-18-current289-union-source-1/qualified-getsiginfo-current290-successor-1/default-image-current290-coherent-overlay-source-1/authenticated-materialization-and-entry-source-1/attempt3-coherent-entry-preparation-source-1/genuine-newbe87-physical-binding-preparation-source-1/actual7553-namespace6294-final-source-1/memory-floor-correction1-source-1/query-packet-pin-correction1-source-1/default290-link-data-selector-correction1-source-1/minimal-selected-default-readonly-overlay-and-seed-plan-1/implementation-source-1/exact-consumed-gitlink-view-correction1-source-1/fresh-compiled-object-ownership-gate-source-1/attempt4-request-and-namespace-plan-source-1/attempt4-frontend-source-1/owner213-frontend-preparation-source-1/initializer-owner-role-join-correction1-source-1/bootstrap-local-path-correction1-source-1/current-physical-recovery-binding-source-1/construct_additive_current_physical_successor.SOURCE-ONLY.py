"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Additive source construction; never executes a workload or evidence validator.
"""
import ast,copy,hashlib,json,re
from pathlib import Path
Z=Path(__file__).parent
Y=Z.parent
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
B=E/'owner15-failed-validation-reconciliation-source-1'
A=B/'actual-failed-validation-recovery-proc-eof-correction1'
def ref(p):
 p=Path(p);return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def put(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n');return ref(p)
oldb=json.loads((Y/'CURRENT-ATTEMPT4-REQUEST-ORIGINAL69-EXACT-ORIGIN-DELTA.json').read_bytes())
oldspec=json.loads(Path(oldb['physical_consumer_spec']['path']).read_bytes())
refs=json.loads((E/'ACTUAL-T-OWNER15-VALIDATION-FAILURE-REFERENCES.json').read_bytes())
R={
 'historical_spec':oldb['physical_consumer_spec'],
 'initial_held_state':ref(A/'INITIAL-HELD-STATE.json'),
 'namespace_initialization':oldspec['actual_namespace_initialization'],
 'completion':ref(E/'INDEPENDENT-OWNER15-FAILED-VALIDATION-RECOVERY-COMPLETION.json'),
 'postjoin':ref(B/'ROOT-ACTUAL-TOOL10088-JOIN-AND-CURRENT-PHYSICAL.json'),
 'failed_references':ref(E/'ACTUAL-T-OWNER15-VALIDATION-FAILURE-REFERENCES.json'),
 'source_order':ref(B/'SOURCE-ORDER-AND-ALGORITHM-FACTS.json'),
 'execution_review':ref(B/'INDEPENDENT-PROC-EOF-CORRECTION1-EXECUTION-REVIEW.json'),
 'prior_review':ref(B/'INDEPENDENT-FAILED-VALIDATION-RECOVERY-EXECUTION-REVIEW.json'),
 'grant':ref(B/'ROOT-PROC-EOF-CORRECTION1-RECOVERY-ONCE-GRANT.json'),
 'packet':ref(B/'FAILED-VALIDATION-RECOVERY.PROC-EOF-CORRECTION1.PACKET.NOT-GRANTED.json'),
 'source':ref(B/'failed_validation_recovery.proc-eof-correction1.py'),
 'action':ref(A/'FAILED-VALIDATION-RECOVERY.json'),
 'helper_join':ref(B/'REAL-PROC-EOF-RECOVERY.JOIN.json'),
 'metadata':ref(A/'SHARED-RECORD.ORIGINAL-METADATA.json'),
 'archive':ref(A/'SHARED-RECORD.ORIGINAL-BYTES'),
 'signal_budget':ref(A/'SIGNAL-BUDGET-CONSUMED.json'),
 'unlink_budget':ref(A/'SHARED-UNLINK-BUDGET-CONSUMED.json')}
adapter='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact recovered physical boundary; historical observations only, no live process checks/admission.
"""
from pathlib import Path
import ast,hashlib,json,types
R=__REFS__
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(value,message):
 if not value:raise RuntimeError('exact recovery current physical: '+message)
def raw(row):
 need(isinstance(row,dict) and set(row)=={'path','sha256','bytes'},'closed exact reference')
 p=Path(row['path']);v=p.read_bytes();need(len(v)==row['bytes'] and hashlib.sha256(v).hexdigest()==row['sha256'],'authenticated bytes '+p.name);return v
def auth(row):return json.loads(raw(row))
def validate_records(a,p,action,joined,metadata,archive,signal_budget,unlink_budget,facts,failed):
 need(a['schema']=='owner15.failed-validation-recovery-independent-completion.v1' and a['decision']=='PASS_FAILED_VALIDATION_RECOVERY_COMPLETION' and a['scope']==SCOPE and a['reviewer']=='/root/perf_review18h' and a['implementation_ownership'] is False,'exact independent completion')
 need(a['root_creator_join_and_physical_sha256']==R['postjoin']['sha256'] and a['action_result_sha256']==R['action']['sha256'] and a['helper_join_sha256']==R['helper_join']['sha256'],'completion action/join lineage')
 for k in ('execution_review','grant','packet','source'):need(a[k+'_sha256']==R[k]['sha256'],'exact execution lineage '+k)
 need(a['actions']==dict(normal_release=0,numeric_or_group_signals=0,pidfd_sigkill=1,positive_pidfd_POLLIN=True,shared_unlink=1,signal_returncode=0),'one exact recovery action budget')
 need(a['normal_cleanup_credit'] is False and a['new_heavy_admission'] is False and a['default_native_or_C_retirement_credit'] is False,'recovery only no admission/retirement')
 need(a['archive']==dict(bytes=268,bytes_sha256=R['archive']['sha256'],live_shared_path_absent=True,metadata_sha256=R['metadata']['sha256'],original_node=[1828,116861]),'exact archived shared record')
 need(a['creator_tool10088']==dict(completion_returned=True,exit_code=137) and a['retired_groups']==[997661,998188,1008846,1012434] and a['all_five_protected_births_alive'] is True and a['permanent_node']==[27,4] and a['permanent_unchanged_free'] is True,'independent historical postflight')
 need(p['scope']==SCOPE and p['status']=='ROOT_POSITIVE_CREATOR_JOIN_AND_POSTFLIGHT' and p['tool10088']==dict(operation='write_stdin empty poll',exit_code=137,completion_returned=True,stdout_bytes=0,original_quarantined_pid=997661,original_starttime='79134158'),'exact external creator completion')
 need(p['retired_groups']=={str(pid):[] for pid in a['retired_groups']} and p['after_probes_lock_rows']==[] and p['shared_record_live_absent'] is True,'four groups gone and shared absent')
 probes=p['permanent_unchanged_free_twice'];need(len(probes)==2 and probes[0]['at']<probes[1]['at'] and all(q['device']==27 and q['inode']==4 and q['nonblocking_acquired'] is True and q['sole_observed_holder']==1012465 for q in probes),'two exact unchanged permanent free observations')
 expected_protected={842938:('76277866',1311),842940:('76277874',842938),842942:('76277881',842940),843517:('76287450',1311),843520:('76287468',1311)}
 need(set(p['protected'])=={str(i) for i in expected_protected},'exact five historical protected identities')
 for pid,(birth,parent) in expected_protected.items():need(p['protected'][str(pid)]==dict(pid=pid,starttime=birth,parent=parent,state='S'),'historical protected birth '+str(pid))
 need(p['helper_join']==joined and joined['returncode']==0 and joined['direct_child_joined'] is True and joined['pid']==1012434 and joined['starttime']=='79405898' and joined['group_absent'] is True and joined['closed_streams'] is True,'exact helper creator join')
 need(p['action_result_sha256']==R['action']['sha256'] and p['new_heavy_admission'] is False and p['default_native_or_retirement_credit'] is False,'root postflight exact action scope')
 need(a['helper']==dict(group_absent=True,joined=True,pid=1012434,returncode=0,starttime='79405898',stderr_bytes=0,streams_closed=True,wall_seconds=joined['wall_seconds']),'independent helper join facts')
 archive_ref=dict(bytes_path=R['archive']['path'],metadata_path=R['metadata']['path'],metadata_sha256=R['metadata']['sha256'],raw_sha256=R['archive']['sha256'])
 need(p['shared_archive']==action['archive']==signal_budget['archive']==unlink_budget['archive']==archive_ref,'same durable archive before both consumed actions')
 need(action['scope']==SCOPE and action['status']=='FAILED_VALIDATION_RECOVERY' and action['action_budget_consumed']==dict(pidfd_sigkill=1,shared_unlink=1) and action['owner']==dict(pid=998188,returncode=1,starttime='79143668'),'exact failed owner action')
 target=dict(fd=3,parent=842942,pid=997661,starttime='79134158')
 need(action['target']==signal_budget['target']==target and action['signal']==dict(returncode=0,signal=9,syscall=424) and action['positive_exit']==dict(events=[[3,1]],pidfd_exit_ready=True),'exact single bound pidfd action and positive POLLIN')
 need(action['local_postflight'] is True and action['normal_cleanup_credit'] is False and action['new_heavy_admission'] is False and action['default_native_or_retirement_credit'] is False,'local recovery scope')
 post=action['postflight'];need(post['archive_valid'] is True and post['shared_absent'] is True and post['protected']==p['protected'] and post['permanent_unchanged_free_observations']==[dict(device=27,inode=4,nonblocking_acquired=True)]*2,'matching local historical postflight')
 need(signal_budget['calls_allowed']==1 and signal_budget['shared_unlinked'] is True and signal_budget['signal']==9 and signal_budget['syscall']==424 and unlink_budget['calls_allowed']==1 and unlink_budget['path']=='/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock' and unlink_budget['record']==metadata,'exact durable once-only budgets')
 need(len(archive)==268 and metadata['raw_hex']==archive.hex() and metadata['raw_sha256']==R['archive']['sha256'] and metadata['value']==json.loads(archive),'exact archived original bytes and decoded metadata')
 need(metadata['metadata']['st_dev']==1828 and metadata['metadata']['st_ino']==116861 and metadata['metadata']['st_size']==268 and metadata['metadata']['st_uid']==metadata['metadata']['st_gid']==1000 and metadata['metadata']['st_mode']==33152 and metadata['metadata']['st_nlink']==1,'exact original node identity')
 need(metadata['value']==dict(boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',device=1828,inode=116861,kind='image',pid=998188,request_sha256='576e75028709c54f3e644a6c2d15d542be2e4389e8814a35eebbea0820b58b50',schema='mckernel.heavy-operation.v1',starttime='79143668'),'exact failed-owner shared record')
 need(facts['owner_source']==failed['owner'] and facts['failure']==failed['owner_stderr'] and facts['joined_owner']==failed['owner_join'] and failed['joined_owner']==dict(pid=998188,starttime='79143668',returncode=1) and failed['owner_receipt_absent'] is True and failed['normal_cleanup_ready_absent'] is True,'failed owner interval lineage')
 need(facts['source_order']==dict(shared_acquire_line=2175,validate_line=2177,actual_failure_line=1996,common_acquire_line=2184,attempt_mkdir_line=2191,lease_acquire_line=2194,Docker_construction_line=2195),'exact acquisition then early validation failure order')
 return True

def validate(acceptance,postjoin):
 need(acceptance==R['completion'] and postjoin==R['postjoin'],'current refs must be exact recovered boundary, historical alone refused')
 spec=auth(R['historical_spec']);path=Path(spec['physical_validator']['path']);source=raw(spec['physical_validator']);m=types.ModuleType('historical_only_08860');m.__file__=str(path);exec(compile(source,str(path),'exec'),m.__dict__);need(m.validate(spec['actual_acceptance'],spec['actual_postjoin']) is True,'unchanged historical baseline validator')
 a=auth(acceptance);p=auth(postjoin);d={k:auth(R[k]) for k in ['action','helper_join','metadata','signal_budget','unlink_budget','source_order','failed_references','execution_review','prior_review','grant','packet']};raw(R['source'])
 need(d['execution_review']['prior_review_sha256']==R['prior_review']['sha256'] and d['execution_review']['decision']=='PASS_FAILED_VALIDATION_RECOVERY_EXECUTION' and d['execution_review']['implementation_ownership'] is False and d['execution_review']['action_budget']==dict(group_signal=0,normal_release=0,numeric_signal=0,permanent_mutations=0,pidfd_sigkill=1,shared_unlink=1),'independent bounded interval recovery execution review')
 failed=d['failed_references'];facts=d['source_order'];owner_source=raw(failed['owner']).decode();stderr=raw(failed['owner_stderr']).decode();oj=auth(failed['owner_join']);auth(failed['actual_owner_entry']);auth(failed['owner_process']);raw(failed['owner_stdout']);request=auth(failed['request']);raw(facts['shared_source'])
 held=auth(R['initial_held_state']);initialized=auth(R['namespace_initialization']);caller=held['caller'];guard=caller['guard']
 need(held['namespaces']==spec['namespace_identities']==initialized['identities'] and initialized['request']==failed['request'] and initialized['owner']==failed['owner'],'original three unchanged initialized namespace identities at held recovery boundary')
 need(held['boot_id']==caller['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' and caller['pid']==997661 and caller['starttime']=='79134158' and caller['parent']==842942 and caller['fd3_node']==[27,4] and caller['permanent_fds']==[3] and caller['children']==[] and caller['threads']==1 and caller['uid']==caller['gid']==1000 and caller['pgid']==caller['session']==997661,'exact original caller birth holds same permanent node')
 need(guard['source']==failed['caller']['path'] and guard['source_sha256']==failed['caller']['sha256'] and guard['pid']==caller['pid'] and guard['starttime']==caller['starttime'] and held['flocks']==[['FLOCK','ADVISORY','WRITE','997661','00:1b:4','0','EOF']] and held['permanent']==dict(device=27,gid=0,inode=4,mode=420,nlink=1,size=0,uid=0),'source-authenticated caller sole permanent lock during archive')
 expected_absent=[request[k] for k in ['common_exclusion_path','attempt_root','output_root','evidence_root','lease_path']]+[str(Path(request['owner_evidence_root'])/'owner-receipt.json'),str(Path(failed['capture_root'])/'ROOT-NORMAL-CLEANUP-COMPLETION-READY.json')]
 need(held['absent_paths']==expected_absent and held['owner_absent'] is True and held['shared_present'] is True and held['protected']==p['protected'],'exact historical absence and shared-held interval')
 raw(failed['caller'])
 need(oj['pid']==998188 and oj['starttime']=='79143668' and oj['returncode']==1 and oj['direct_child_joined'] is True and oj['group_absent'] is True and oj['closed_streams'] is True and oj['stderr']==failed['owner_stderr'] and oj['stdout']==failed['owner_stdout'],'original owner join actual failure')
 need(all(t in stderr for t in ['line 2177, in _reuse_run','line 1996, in _reuse_validate_request_base','self.validate()','common exclusion path differs or is retired']),'exact original traceback')
 lines=owner_source.splitlines();need('_SHARED_HEAVY_ENTRY_CONTRACT.acquire_heavy_operation(' in lines[2174] and 'self.validate()' in lines[2176] and 'common.acquire()' in lines[2183] and '_fail(common == COMMON_EXCLUSION' in lines[1995],'exact source statements before later effects')
 return validate_records(a,p,d['action'],d['helper_join'],d['metadata'],raw(R['archive']),d['signal_budget'],d['unlink_budget'],facts,failed)
'''
(Z/'validate_exact_failed_owner15_recovery_current_physical.SOURCE-ONLY.py').write_text(adapter.replace('__REFS__',repr(R)))
new_spec=copy.deepcopy(oldspec);new_spec.update(actual_acceptance=R['completion'],actual_postjoin=R['postjoin'],physical_validator=ref(Z/'validate_exact_failed_owner15_recovery_current_physical.SOURCE-ONLY.py'),approved_schema='owner15.failed-validation-recovery-independent-completion.v1',approved_decision='PASS_FAILED_VALIDATION_RECOVERY_COMPLETION',historical_baseline_spec=R['historical_spec'],status='EXACT_FAILED_VALIDATION_RECOVERY_BOUNDARY_NAMESPACE3_SOURCE_BINDING_NOT_ADMISSION',continuity_boundary=R['completion'],historical_protected_observations_only=True)
specref=put(Z/'ATTEMPT4-468813-11B6-RECOVERED-CURRENT-PHYSICAL-NAMESPACE.BINDING.json',new_spec)
exclude={'EXACT-INITIALIZER15-RUNTIME213-THREE-PURE-CONTROLS.NOT-GRANTED.json','test_exact_initializer15_runtime213_role_and_actual_producer.PURE.NOT-RUN.py'}
files=[p for p in Y.iterdir() if p.is_file() and p.suffix in ('.py','.json') and p.name not in exclude]
pathmap={str(p):str(Z/p.name) for p in files}
pathmap[str(Y)]=str(Z)
# Each path is substituted once using the longest matching original path, never cascading.
pattern=re.compile('|'.join(re.escape(k) for k in sorted(pathmap,key=len,reverse=True)))
hashmap={};done=set();active=set()
def replace_paths(s):return pattern.sub(lambda m:pathmap[m.group()],s)
def update_json(o):
 if isinstance(o,list):return [update_json(v) for v in o]
 if not isinstance(o,dict):return replace_paths(o) if isinstance(o,str) else o
 if set(o)=={'path','sha256','bytes'}:
  if o==oldspec['actual_acceptance']:return R['completion']
  if o==oldspec['actual_postjoin']:return R['postjoin']
  if o==oldb['physical_consumer_spec']:return specref
  q=replace_paths(o['path'])
  if q!=o['path'] and Path(q).is_file():return ref(q)
 return {k:update_json(v) for k,v in o.items()}
def build(p):
 if p.name in done:return
 if p.name in active:raise RuntimeError('source dependency cycle '+p.name)
 active.add(p.name);s=p.read_text()
 if p.name=='run_frozen_current290_image_entry.ATTEMPT4.READONLY-SEED.py':
  old="initialized['request'] == cfg['pins']['request'] and initialized['owner'] == cfg['pins']['owner'] and"
  new="initialized['request'] == cfg['pins']['request'] and binding_module.require_initializer_runtime_owner_roles(initialized, binding_module.data()) and"
  assert s.count(old)==1;s=s.replace(old,new)
 for q in files:
  if q!=p and (str(q) in s or ref(q)['sha256'] in s):build(q)
 dst=Z/p.name
 if p.suffix=='.json':
  o=update_json(json.loads(s))
  if p.name=='READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json':o.update(predecessor_READY=ref(p),current_physical_binding=specref,bootstrap_correction='Additive exact recovered physical consumer; tested owner-role and producer logic unchanged',future_current_physical=None)
  if p.name=='ROOT-PREPARATION-CONTEXT.ATTEMPT4.READONLY-SEED.PENDING-HOLDER-CLOCK-GRANTS.json':o['root_must_complete']='Continuity starts at exact468813/11b6 recovery completion; fresh current holder/ancestry/service/clock/aggregate/admission facts and independent release required. Historical protected births are archived observations only.'
  put(dst,o)
 else:
  # Update exact reference literals before substituting paths/standalone immutable SHA constants.
  edits=[]
  for node in ast.walk(ast.parse(s)):
   if isinstance(node,ast.Dict):
    try:o=ast.literal_eval(node)
    except (ValueError,TypeError,SyntaxError):continue
    if isinstance(o,dict) and set(o)=={'path','sha256','bytes'}:
     new=update_json(o)
     if new!=o:edits.append((node.lineno,node.col_offset,node.end_lineno,node.end_col_offset,repr(new)))
  lines=s.splitlines(keepends=True);offset=[0]
  for line in lines:offset.append(offset[-1]+len(line))
  # Transform original text chunks only; inserted successor refs never re-enter the map.
  combined=dict(pathmap);combined.update(hashmap)
  cpat=re.compile('|'.join(re.escape(k) for k in sorted(combined,key=len,reverse=True)))
  transform=lambda text:cpat.sub(lambda m:combined[m.group()],text)
  chunks=[];last=0
  for a,b,c,d,v in sorted(edits):
   begin=offset[a-1]+b;end=offset[c-1]+d
   chunks.extend([transform(s[last:begin]),v]);last=end
  chunks.append(transform(s[last:]));dst.write_text(''.join(chunks))
 hashmap[ref(p)['sha256']]=ref(dst)['sha256'];active.remove(p.name);done.add(p.name)
for p in files:build(p)
# These three role checks are unchanged from Y. The new control below exercises current facts.
oldtest=(Y/'test_exact_initializer15_runtime213_role_and_actual_producer.PURE.NOT-RUN.py').read_text()
tree=ast.parse(oldtest);lines=oldtest.splitlines(keepends=True)
for n in sorted([n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_') and n.name!='test_REAL_prepare_finish_emits_runtime213_and_retains_initializer15'],key=lambda n:n.lineno,reverse=True):del lines[n.lineno-1:n.end_lineno]
test=''.join(lines)
test=test.replace("shutil.copyfile(F['context']['path'],context)","doc=json.loads(Path(F['context']['path']).read_bytes());doc['actual_current_physical']=self.cfg['physical'];doc['actual_current_live_postjoin']=self.cfg['postjoin'];context.write_text(json.dumps(doc))")
test=test.replace("self.assertTrue(self.helper.require_initializer_runtime_owner_roles(self.initialized,self.b))","self.assertTrue(self.helper.require_initializer_runtime_owner_roles(self.initialized,self.b));self.assertEqual(final['current_physical'],self.cfg['physical']);self.assertEqual(final['current_live_postjoin'],self.cfg['postjoin']);self.assertTrue(self.caller.command_output_paths(self.cfg))")
extra=''' def bootstrap_to_transport_boundary(self,mutate_initialized=None,mutate_context=None,mutate_config=None):
  class BoundaryReached(Exception):pass
  with tempfile.TemporaryDirectory() as temporary:
   temp=Path(temporary);capture=temp/'disposable-caller-capture';config=Path(R['config']['path']);checksum=R['config']['sha256']
   if mutate_config is not None:
    bad=copy.deepcopy(self.cfg);mutate_config(bad);config=temp/'DISPOSABLE-CONFIG.json';config.write_text(json.dumps(bad));checksum=reference(config)['sha256']
   context=json.loads(Path(R['context_template']['path']).read_bytes());context.update(author='/root',disposable_fixture_only_no_authority=True);context['aggregate']['actual_no_other_heavy']=True;context['continuity']['no_heavy_since_latest_physical']=True
   if mutate_context is not None:mutate_context(context)
   cp=temp/'DISPOSABLE-CONTEXT.json';cp.write_text(json.dumps(context))
   initialized=copy.deepcopy(self.initialized);ir=self.cfg['namespace_initialization']
   if mutate_initialized is not None:
    mutate_initialized(initialized);ip=temp/'DISPOSABLE-INITIALIZER.json';ip.write_text(json.dumps(initialized));ir=reference(ip)
   review=temp/'DISPOSABLE-CLEANUP-REVIEW.json';review.write_text(json.dumps(dict(decision='PASS_SOURCE_EXISTING_SAME_OFD_IMAGE_CLEANUP',implementation_ownership=False,reviewer='/disposable-fixture-reviewer',source=R['cleanup'],same_OFD_transport='STDIN_FD0_SUDO_A',disposable_fixture_only_no_authority=True)))
   grant=temp/'DISPOSABLE-PREPARATION-GRANT.json';grant.write_text(json.dumps(dict(author='/root',decision='GRANT_CURRENT290_READONLY_PREPARATION',caller_sha256=R['caller']['sha256'],config_sha256=checksum,census_observer=R['corrected_census_observer'],existing_cleanup_source=R['cleanup'],existing_cleanup_source_review=reference(review),context=reference(cp),namespace_initialization=ir,disposable_fixture_only_no_authority=True)))
   calls=[]
   def boundary(argv,root,name):
    self.assertEqual(argv,self.cfg['commands']['five_observations']['argv']);self.assertEqual(root,capture);self.assertEqual(name,'five');calls.append(name);raise BoundaryReached()
   real_path=Path;real_getrlimit=self.caller.resource.getrlimit
   def virtual_getrlimit(which):return (self.caller.resource.RLIM_INFINITY,self.caller.resource.RLIM_INFINITY) if which==self.caller.resource.RLIMIT_CPU else real_getrlimit(which)
   def disposable_path(value,*args,**kwargs):return capture if str(value)==self.cfg['capture_root'] else real_path(value,*args,**kwargs)
   before=[(Path(row['path']).stat().st_dev,Path(row['path']).stat().st_ino,sorted(Path(row['path']).iterdir())) for row in self.initialized['identities']]
   with contextlib.ExitStack() as guards:
    guards.enter_context(mock.patch.object(self.caller,'Path',side_effect=disposable_path));guards.enter_context(mock.patch.object(self.caller,'captured',side_effect=boundary));lock=guards.enter_context(mock.patch.object(self.caller,'lock_functions',side_effect=AssertionError('no permanent lock')));guards.enter_context(mock.patch.object(self.caller.fcntl,'flock',side_effect=AssertionError('no flock')));guards.enter_context(mock.patch.object(self.caller.os,'sched_getaffinity',return_value={7}));guards.enter_context(mock.patch.object(self.caller.resource,'getrlimit',side_effect=virtual_getrlimit))
    if mutate_initialized is None and mutate_context is None and mutate_config is None:
     with self.assertRaises(BoundaryReached):self.caller.execute(grant,config,checksum)
     self.assertEqual(calls,['five']);self.assertTrue((capture/'PREPARATION-GRANT-REFERENCE.json').is_file())
    else:
     with self.assertRaises(RuntimeError):self.caller.execute(grant,config,checksum)
     self.assertEqual(calls,[])
    lock.assert_not_called()
   after=[(Path(row['path']).stat().st_dev,Path(row['path']).stat().st_ino,sorted(Path(row['path']).iterdir())) for row in self.initialized['identities']];self.assertEqual(before,after);self.assertFalse(Path(self.cfg['capture_root']).exists());self.assertFalse((HERE/'actual-readonly-admission-capture-1').exists())
 def test_real_new_runtime_physical_consumer_positive(self):
  self.assertTrue(self.helper.require_new_runtime_facts(self.cfg));self.bootstrap_to_transport_boundary()
  self.assertEqual(self.cfg['physical']['sha256'],'468813ec41d54d6549345a909ffd8ccbb0b25448ee31ac3d1f611870b6784cc3')
  self.assertEqual(self.cfg['postjoin']['sha256'],'11b6c7764641dfac0b63f09b0fef049fdab3326f2ee40aa9c72962962b402fd3')
 def test_old_only_wrong_binding_missing_join_and_mutated_recovery_refused(self):
  spec=json.loads(Path(self.b['physical_consumer_spec']['path']).read_bytes());adapter=load('exact_recovery_adapter',spec['physical_validator']);old=json.loads(Path(spec['historical_baseline_spec']['path']).read_bytes())
  for key,value in [('physical',old['actual_acceptance']),('postjoin',old['actual_postjoin']),('postjoin',self.cfg['physical'])]:
   bad=copy.deepcopy(self.cfg);bad[key]=value
   with self.subTest(binding=key),self.assertRaises(RuntimeError):self.helper.require_new_runtime_facts(bad)
  with self.assertRaises(RuntimeError):adapter.validate(old['actual_acceptance'],old['actual_postjoin'])
  self.bootstrap_to_transport_boundary(mutate_initialized=lambda d:d.update(owner=R['owner']))
  self.bootstrap_to_transport_boundary(mutate_context=lambda d:d.update(actual_current_physical=old['actual_acceptance']))
  self.bootstrap_to_transport_boundary(mutate_config=lambda d:d['pins'].update(owner=self.initialized['owner']))
  records=[adapter.auth(adapter.R[k]) for k in ['completion','postjoin','action','helper_join','metadata']];records+=[adapter.raw(adapter.R['archive'])];records +=[adapter.auth(adapter.R[k]) for k in ['signal_budget','unlink_budget','source_order','failed_references']]
  for index,mutate in [(1,lambda d:d.update(helper_join=None)),(0,lambda d:d.update(action_result_sha256='0'*64)),(2,lambda d:d.update(action_budget_consumed=dict(pidfd_sigkill=2,shared_unlink=1))),(4,lambda d:d['value'].update(pid=1)),(1,lambda d:d['retired_groups'].update({'998188':[1]}))]:
   bad=copy.deepcopy(records);mutate(bad[index])
   with self.subTest(record=index),self.assertRaises((RuntimeError,KeyError,TypeError)):adapter.validate_records(*bad)
'''
test=test.replace("if __name__=='__main__':",extra+"if __name__=='__main__':")
(Z/'test_exact_recovered_physical_and_producer.PURE.NOT-RUN.py').write_text(test)
put(Z/'EXACT-CURRENT-PHYSICAL-THREE-PURE-CONTROLS.NOT-GRANTED.json',dict(scope=oldb['scope'],status='SOURCE_ONLY_NOT_EXECUTED_NOT_GRANTED',test=ref(Z/'test_exact_recovered_physical_and_producer.PURE.NOT-RUN.py'),ready=ref(Z/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json'),physical_consumer_spec=specref,tests=3,test_environment_virtualization='Only caller sched_getaffinity->CPU7 and getrlimit(RLIMIT_CPU)->infinity; actual inherited controls remain enforced; other getrlimit values delegated',query_transport=False,compiler=False,native=False,module=False,cleanup=False))
print(json.dumps(dict(scope=oldb['scope'],status='SOURCE_CONSTRUCTION_ONLY',ready=ref(Z/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json'),spec=specref),indent=2))
