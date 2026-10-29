"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only current binding of reviewed exact idle-owner pidfd retirement.
No historical release applies. Execution requires a new Root+independent release.
"""
from pathlib import Path
import argparse,ast,copy,ctypes,hashlib,importlib.util,json,os,re,resource,signal,stat,time
D=Path(__file__).resolve().parent
BINDINGS_SHA='0b54c1729651ca01ca51be63eeec84c798f562ce061af6fadaf3f9208e65fb15'
SELF=D/'retire_exact_failed_guard.py'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def need(ok,why):
 if not ok:raise RuntimeError(why)
def initial_load(path,expected,name):
 raw=Path(path).read_bytes();need(hashlib.sha256(raw).hexdigest()==expected,'exact source dependency')
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
raw=(D/'BINDINGS.json').read_bytes();need(hashlib.sha256(raw).hexdigest()==BINDINGS_SHA,'exact rebind source data')
B=json.loads(raw)
T=initial_load(B['transport_executor']['path'],B['transport_executor']['sha256'],'reviewed_current118_compatible_transport')
M=T.load(B['primitive'],'reviewed_exact_idle_guard_kernel_protocol')
PROFILE=T.authenticated(B['profile'],True)
TB=T.bindings();PACKET,PROTECTED,BUILD_PROFILE,CLAIM,PLAN,TERMINAL=T.validate_retained(TB)
GUARD=T.load(B['guardian'],'actual_restart_guard')
F=T.authenticated(B['reconciliation_facts'],True)
G=PROFILE['bound_guard'];STATE={}

def data():
 need(B['scope']==SCOPE and B['runtime_authority'] is None and PROFILE['runtime_authority'] is None,'preparation is not authority')
 for key in ['primitive','historical_profile','transport_executor','transport_bindings','portable_converter','guardian','controls','earliest_caps','reconciliation_facts','reconciliation_review']:T.authenticated(B[key])
 for key in ['controlled_cid_subject','pre_identity_correction_executor','failed_rebind_attempt']:T.authenticated(B[key])
 for key in ['publisher_alias_contract','pre_alias_correction_executor','actual_cid_leaf_read','preserved_full_callback_refusal']:T.authenticated(B[key])
 contract=T.authenticated(B['publisher_alias_contract'],True)
 for key in ['publisher_source','actual_publication','actual_reviewer_bindings']:T.authenticated(contract[key])
 pub=T.authenticated(contract['actual_publication'],True);reviewer=T.authenticated(contract['actual_reviewer_bindings'],True)
 need(pub['status'].startswith('PASS_FETCHED_CURRENT118_') and pub['runtime_authority'] is None and any(r['actual']==contract['publisher_source'] for r in pub['rows']) and reviewer['static_refs']['handoff_common']==contract['publisher_source'],'actual accepted publisher source contract')
 need(len(contract['pairs'])==6 and all(p['canonical'] in B['protected'] and p['alias']['path']==p['canonical']['path']+'.complete-source-'+str(p['publisher_pid']) and p['expected']['st_nlink']==2 for p in contract['pairs']),'only six fixed accepted publication pairs')

 need(T.reference(T.D/'BINDINGS.json')==B['transport_bindings'],'exact transport data')
 controls=T.authenticated(B['controls'],True)
 deny=[dict(role=k,pid=v['pid'],birth=v['start']) for k,v in controls['actors'].items()]
 need(B['deny_targets']==deny and len(deny)==6 and G['pid'] not in {x['pid'] for x in deny},'all actual model/guardian/monitor/phone targets denied')
 need((G['pid'],G['starttime'],G['parent_pid'],G['parent_birth'])==(2232651,'103343097',2232650,'103343093'),'only exact failed helper/parent')
 need(PROFILE['first_readonly_client']['status']=='UNKNOWN' and PROFILE['first_readonly_client']['positive_wait4'] is False and F['saved_client_status_unknown'] is True and F['saved_positive_wait4'] is False,'original client status remains UNKNOWN')
 return True

def controlled_cid_identity(path):
 # Only this exact retained CID receives the same permitted ordinary-read method
 # as the original fixed Python executable. No shared module/global is changed.
 need(Path(path)==Path(B['controlled_cid_subject']['path']),'exact controlled CID read exception only')
 tree=ast.parse(T.authenticated(B['primitive']))
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='file_identity')
 assignment=next(n for n in ast.walk(node) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='noatime' for t in n.targets))
 need(isinstance(assignment.value,ast.IfExp),'unchanged original read flag anchor')
 assignment.value.test=ast.BoolOp(op=ast.Or(),values=[assignment.value.test,ast.Compare(left=ast.Name(id='path',ctx=ast.Load()),ops=[ast.Eq()],comparators=[ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(B['controlled_cid_subject']['path'])],keywords=[])])])
 ast.fix_missing_locations(node);context=dict(vars(M))
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(SELF),'exec'),context)
 return context['file_identity'](Path(path))

def publisher_alias_identity(path):
 contract=T.authenticated(B['publisher_alias_contract'],True)
 pair=next((p for p in contract['pairs'] if p['canonical']['path']==str(path)),None)
 need(pair is not None,'only exact accepted publisher canonical row')
 tree=ast.parse(T.authenticated(B['primitive']))
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='file_identity')
 comparisons=[n for n in ast.walk(node) if isinstance(n,ast.Compare) and isinstance(n.left,ast.Attribute) and isinstance(n.left.value,ast.Name) and n.left.value.id=='before' and n.left.attr=='st_nlink' and len(n.comparators)==1 and isinstance(n.comparators[0],ast.Constant) and n.comparators[0].value==1]
 need(len(comparisons)==1 and pair['expected']['st_nlink']==contract['expected_nlink']==2,'exact original single-link shape anchor to fixed expected2')
 comparisons[0].comparators[0].value=2;ast.fix_missing_locations(node);context=dict(vars(M))
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(SELF),'exec'),context)
 rows=[]
 for key in ('canonical','alias'):
  subject=pair[key];T.authenticated(subject);p=Path(subject['path']);before=p.lstat()
  need(all(getattr(before,k)==v for k,v in pair['expected'].items()),'fixed accepted alias node/owner/mode/link/size/time identity')
  row,raw=context['file_identity'](p);after=p.lstat()
  need(raw is None and all(getattr(after,k)==v for k,v in pair['expected'].items()) and row['sha256']==subject['sha256'] and row['size']==subject['bytes'],'same original stable FD/linked-node/byte checks for both retained names')
  rows.append(row)
 need({k:v for k,v in rows[0].items() if k!='path'}=={k:v for k,v in rows[1].items() if k!='path'},'both exact names remain same protected inode')
 return rows[0],None

def protected_inputs(release,profile):
 data();T.validate_retained(TB);observed={}
 for r in B['protected']:
  T.authenticated(r);aliases=T.authenticated(B['publisher_alias_contract'],True)['pairs'];row,_=(controlled_cid_identity(Path(r['path'])) if r==B['controlled_cid_subject'] else publisher_alias_identity(Path(r['path'])) if any(p['canonical']==r for p in aliases) else M.file_identity(Path(r['path'])))
  need(row['sha256']==r['sha256'] and row['size']==r['bytes'],'protected original unchanged');observed[r['path']]=row
 need(release['protected_inputs']==B['protected'],'exact retained source/image/raw failure closure')
 receipt=T.authenticated(F['client_receipt'],True);uncertain=T.authenticated(F['uncertain'],True)
 need(receipt['positive_wait4'] is False and uncertain['commit_attempted'] is False,'failure is not converted into success')
 out=Path(F['uncertain']['path']).parent
 need(not os.path.lexists(out/'RM-ONCE-CLAIM.json') and not os.path.lexists(out/'RESULT.json'),'no intervening stopped-container mutation')
 return observed

ORIGINAL_GUARD_IDENTITY=M.guard_identity
def guard_identity(profile):
 result=ORIGINAL_GUARD_IDENTITY(profile);fields=M.proc_stat(G['pid'])
 need(int(fields[2])==G['pgrp'] and int(fields[3])==G['session'],'exact dedicated target pgrp/session')
 need(M.proc_bytes('/proc/%d/task/%d/children'%(G['pid'],G['pid'])).strip()==b'','target has no children')
 fd='/proc/%d/fd/%d'%(G['pid'],G['root_lock']['fd'])
 need(os.readlink(fd)==str(M.LOCK),'exact target FD4 link');node=os.stat(fd)
 need((node.st_dev,node.st_ino)==(27,4),'target FD4 same permanent inode')
 info=M.proc_bytes('/proc/%d/fdinfo/%d'%(G['pid'],G['root_lock']['fd'])).decode()
 need('FLOCK  ADVISORY  WRITE %d 00:1b:4 0 EOF'%G['pid'] in info,'FD4 exact kernel flock record')
 parent=M.proc_stat(G['parent_pid'])
 need(parent[19]==G['parent_birth'] and parent[0] not in ('Z','X','x') and int(parent[2])==G['parent_pgrp'] and int(parent[3])==G['parent_session'],'same live actual parent')
 need(os.readlink('/proc/%d/exe'%G['parent_pid'])==G['parent_exe'],'exact parent executable')
 status=dict(line.split(':',1) for line in M.proc_bytes('/proc/%d/status'%G['parent_pid']).decode().splitlines() if ':' in line)
 need(status['Uid'].split()==status['Gid'].split()==['1000']*4 and status['Threads'].strip()=='1','exact ordinary single-thread parent')
 need(M.proc_bytes('/proc/%d/task/%d/children'%(G['parent_pid'],G['parent_pid'])).split()==[str(G['pid']).encode()],'parent directly owns only target')
 M.require_lock_holder(G['pid']);need(M.proc_stat(G['pid'])[19]==G['starttime'],'target birth stable through extended identity')
 return dict(result,pgrp=G['pgrp'],session=G['session'],lock_fd=4,parent_birth=G['parent_birth'])

def safe(release):
 protected_inputs(release,PROFILE);now=GUARD.guard()
 need(all(a<c for a,c in zip(now,B['cutoffs'])),'actual current earliest/account/identity gate')
 return now

def final_before_signal(release,profile,proofs,requested):
 # All protected/source/guardian I/O precedes final direct stop/clock checks.
 safe(release);GUARD.guard();need(not requested,'new external termination request')
 now=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
 need(all(a<c for a,c in zip(now,B['cutoffs'])),'final signal earliest cutoff')
 need(all(0<=now[0]-p['clocks'][0]<=120 for p in proofs),'both fresh preproofs within original120s after prepared fsync')
 # Direct return to original attempted=True and sole pidfd syscall unit.

def process_code():
 normal=T.load(TB['normal'],'unchanged_full_current_process_census')
 code=T.process_source(normal,PACKET);anchor='    for arg in argv:\n'
 need(code.count(anchor)==1,'exact original publisher extension anchor')
 return code.replace(anchor,'    if '+repr(G['source'])+' in argv: return True\n'+anchor)

ORIGINAL_PROCESS_VALIDATOR=M.validate_process_report
def validate_process_report(report,challenge,caller,before,prior_query_pids=()):
 need(report['schema']=='fp-save-image.proc.v1' and 'groups' in report,'exact current full group-extended census')
 basic={k:v for k,v in report.items() if k!='groups'}
 # Schema adapter only: all unchanged historical full-census predicates execute.
 basic['schema']='scratch21.proc.v1';original_absent=M.ABSENT
 M.ABSENT=set(original_absent)|set(prior_query_pids)
 try:ORIGINAL_PROCESS_VALIDATOR(basic,challenge,caller,before)
 finally:M.ABSENT=original_absent
 need(len(report['groups'])==2,'two complete group snapshots')
 absent=set(M.ABSENT)|set(prior_query_pids)
 if not before:absent.add(G['pid'])
 for rows,groups in zip(report['snapshots'],report['groups']):
  need([x[:3] for x in groups]==rows,'full raw process/group rows correspond')
  for row in groups:
   need(len(row)==5 and all(type(row[i]) is int and row[i]>=0 for i in (0,1,3,4)) and row[2].isdigit(),'typed full group/session rows')
   need(not (set((row[0],row[3],row[4]))&absent),'prior actors/unknown client/target-after absent by PID/group/session')
 return True

def readonly(argv):
 process_prefix=['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',process_code()]
 if argv[:7]==process_prefix:
  need(len(argv)==10 and re.fullmatch('[0-9a-f]{48}',argv[7]) and argv[8:]==[str(os.getpid()),M.proc_stat(os.getpid())[19]],'exact challenge/caller/full-census argv')
 else:need(argv in [T.PREFIX+['inspect','--type','container',TB['cid']],T.PREFIX+['image','inspect',BUILD_PROFILE['inputs']['image']],T.PREFIX+['ps','-a','--no-trunc','--format','{{json .}}']],'only original exact readonly process/container/image/census commands')
 def final_query_gate(unused):
  safe(STATE['release']);GUARD.guard();STATE['commands'].signals.check()
  now=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
  need(all(a<c for a,c in zip(now,B['cutoffs'])),'final query pre-Popen earliest cutoff')
 STATE['commands'].before_popen=final_query_gate
 # Existing capture transport adds no signal or kill on timeout/uncertainty.
 r=STATE['commands'].exact(argv,30,check=True)
 need(r.returncode==0 and not STATE['commands'].client_retirement_unproven,'query client exact positive wait4/group/stream proof')
 return r

def snapshot(label,release,profile,before):
 inputs=protected_inputs(release,profile)
 if before:guard_identity(profile);locks=M.require_lock_holder(G['pid'])
 else:M.boot_check();locks=M.require_lock_holder(os.getpid())
 caller=[os.getpid(),M.proc_stat(os.getpid())[19]];challenge=os.urandom(24).hex()
 prior_query_pids=[x.pid for x in STATE['commands'].children]
 p=readonly(['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',process_code(),challenge,str(caller[0]),caller[1]])
 report=T.strict(p.stdout);validate_process_report(report,challenge,caller,before,prior_query_pids)
 inspected=T.strict(readonly(T.PREFIX+['inspect','--type','container',TB['cid']]).stdout)
 image=T.strict(readonly(T.PREFIX+['image','inspect',BUILD_PROFILE['inputs']['image']]).stdout)
 need(type(inspected) is list and len(inspected)==1 and type(image) is list and len(image)==1,'exact retained container/image reply')
 T.validate_profile(inspected[0],image[0],TB,PACKET,BUILD_PROFILE,CLAIM,TERMINAL)
 inventory=readonly(T.PREFIX+['ps','-a','--no-trunc','--format','{{json .}}'])
 T.validate_inventory(inventory.stdout,TB,True)
 # Fresh full raw command captures and JOINs are already durably retained.
 clocks=safe(release);M.boot_check()
 proof=dict(inputs=inputs,root_locks=locks,clocks=clocks,process=report,container=inspected,image=image,inventory=T.strict('['+','.join(inventory.stdout.splitlines())+']'),command_receipts=list(STATE['commands'].receipts))
 T.write_new(STATE['out']/(label+'.json'),proof);return proof

def runtime_files():
 rows=dict(executor=T.reference(SELF),bindings=T.reference(D/'BINDINGS.json'))
 rows.update({k:B[k] for k in ('profile','primitive','historical_profile','transport_executor','transport_bindings','portable_converter','guardian','reconciliation_facts','reconciliation_review')})
 rows.update({k:B[k] for k in ('pre_identity_correction_executor','failed_rebind_attempt')})
 rows.update({k:B[k] for k in ('publisher_alias_contract','pre_alias_correction_executor','actual_cid_leaf_read','preserved_full_callback_refusal')})
 return rows

def bind_stop_requests(requested):
 # The original protocol's deferred-signal latch is shared with the existing
 # no-signal query transport, so a new request prevents the next command too.
 STATE['commands'].signals.requested=requested

def bind_release(path,checksum):
 data();rr=T.reference(path);need(rr['sha256']==checksum,'exact current Root release');r=T.authenticated(rr,True)
 need(r['schema']=='mckernel.current118.failed-idle-helper.retirement-release.v1' and r['author']=='/root' and r['decision']=='GRANT_ONE_EXACT_IDLE_FAILED_HELPER_PIDFD_RETIREMENT','new current Root owner release only')
 need(type(r['maximum_invocations']) is int and r['maximum_invocations']==1 and r['signal_budget']==1 and r['target']==G and r['files']==runtime_files(),'exact one invocation/one pidfd target/source closure')
 need(r['protected_inputs']==B['protected'] and r['failed_client_status']=='UNKNOWN' and r['parent_positive_join_mandatory'] is True and r['container_mutations_allowed']==0 and r['records_released']==[],'failed client status/parent join/container/record boundaries')
 need(r['cutoffs']==B['cutoffs'] and r['credit_run_id']=='7f4af94a83b14cc08f97401f5891d965' and r['credit_ceiling']=='57774.852125' and r['minimum_cumulative_spent']=='22812.3311','immutable controls/credit')
 need(r['actual_control_authorities']==dict(controls=B['controls'],earliest_caps=B['earliest_caps']),'exact external current control authority refs')
 need(r['actual_account_identity_operation_admission_accepted'] is True and r['Root_attests_no_unlisted_intervening_operation'] is True,'fresh actual current operation/admission')
 operation=T.authenticated(r['current_operation'],True)
 need(operation['author']=='/root' and operation['operation']=='RETIRE_EXACT_FAILED_CURRENT118_IDLE_HELPER_ONLY' and operation['target']==G and operation['failed_client_status']=='UNKNOWN' and operation['container_mutations_allowed']==0,'exact actual current operation')
 review=T.authenticated(r['source_review'],True)
 need(review['decision']=='PASS_SOURCE' and review['independent'] is True and review['implementation_ownership'] is False and review['reviewer'] not in ('/root','/root/bfd_route') and review['files']==r['files'] and review['source_checkpoint']==r['source_checkpoint'],'independent exact source review')
 publication=T.authenticated(r['source_publication'],True)
 need(re.fullmatch('[0-9a-f]{40}',r['source_checkpoint']) and r['fetched_source_verified'] is True and publication['status'].startswith('PASS_FETCHED') and publication['commit']==r['source_checkpoint'] and publication['runtime_authority'] is None,'actual fetched source publication')
 published={x['actual']['path']:x['actual'] for x in publication['rows']}
 need(all(published.get(x['path'])==x for x in r['files'].values()),'exact published runtime dependencies')
 review=T.authenticated(r['execution_review'],True);payload={k:v for k,v in r.items() if k!='execution_review'}
 need(review['decision']=='PASS_EXECUTION' and review['independent'] is True and review['implementation_ownership'] is False and review['reviewer'] not in ('/root','/root/bfd_route') and review['release_payload_sha256']==hashlib.sha256(T.canonical(payload)).hexdigest(),'independent exact execution payload review')
 need((os.getuid(),os.geteuid(),os.getgid(),os.getegid())==(1000,1000,1000,1000) and os.uname().machine=='x86_64' and os.sched_getaffinity(0)=={0},'ordinary current x86_64 CPU0 profile')
 for kind,wanted in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:need(resource.getrlimit(kind)==(wanted,wanted),'exact reviewed execution rlimit')
 out=Path(r['output']);need(out.parent==D and re.fullmatch('actual-guard-retirement-[A-Za-z0-9_-]+',out.name) and not os.path.lexists(out),'fresh confined metadata only')
 for fixed in (M.PREPARED,M.COMPLETE,M.QUARANTINE):need(not os.path.lexists(fixed),'no replay of materialized protocol attempt')
 out.mkdir(mode=0o700);cls,_=T.transport(TB);STATE.update(release=r,out=out,commands=cls(out,T.Stop()))
 return r,PROFILE

def rebound_protocol(namespace=None):
 """Reuse original execution sequence; only current receipt types and final gate differ."""
 tree=ast.parse(T.authenticated(B['primitive']));node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
 class Rebind(ast.NodeTransformer):
  def visit_Constant(self,n):
   replacements={'scratch22-authority1.quarantine-recovery-prepared.v1':'mckernel.current118.failed-idle-helper.retirement-prepared.v1','scratch22-authority1.quarantine-recovery-complete.v1':'mckernel.current118.failed-idle-helper.retirement-complete.v1','COMPLETE_PROCESS_RECOVERY':'COMPLETE_FAILED_HELPER_RETIREMENT_PENDING_PARENT_JOIN','FAIL':'FAIL_UNKNOWN_CLIENT_STATUS'}
   if isinstance(n.value,str) and n.value in replacements:n.value=replacements[n.value]
   return n
  def visit_keyword(self,n):
   n=self.generic_visit(n)
   if n.arg=='build_status':n.arg='prior_retirement_status'
   return n
 node=Rebind().visit(node)
 stop_index=next(i for i,n in enumerate(node.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Tuple) and any(isinstance(x,ast.Name) and x.id=='requested' for x in t.elts) for t in n.targets))
 node.body.insert(stop_index+1,ast.parse('bind_stop_requests(requested)').body[0])
 # Locate the original try body by its direct attempted=True assignment.
 block=next(n for n in node.body if isinstance(n,ast.Try))
 index=next(i for i,n in enumerate(block.body) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='attempted' for x in n.targets))
 block.body.insert(index,ast.parse('final_before_signal(release,profile,[first,second],requested)').body[0])
 record=next(n for n in block.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='record' for x in n.targets))
 record.value.keywords.extend([ast.keyword(arg='parent_positive_join_required',value=ast.Constant(True)),ast.keyword(arg='current_free',value=ast.Constant(False)),ast.keyword(arg='old_readonly_client_status',value=ast.Constant('UNKNOWN'))])
 ast.fix_missing_locations(node);ctx=dict(vars(M)) if namespace is None else namespace
 ctx.update(bind_release=bind_release,snapshot=snapshot,final_before_signal=final_before_signal,bind_stop_requests=bind_stop_requests)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(SELF),'exec'),ctx);return ctx['execute'],node

def configure():
 M.PID=G['pid'];M.START=G['starttime'];M.PARENT=G['parent_pid'];M.PROFILE_SHA=B['profile']['sha256'];M.BOOT=B['boot']
 M.PREFIX=D/'guard-retirement-root1';M.PREPARED=Path(str(M.PREFIX)+'.prepared.json');M.COMPLETE=Path(str(M.PREFIX)+'.complete.json');M.QUARANTINE=Path(str(M.PREFIX)+'.quarantine.json')
 M.ABSENT={x['pid'] for x in B['prior_actors']}|{B['unknown_client']}
 M.ORIGINAL_FAILURE_SHA256={r['path']:r['sha256'] for r in B['protected']}
 M.guard_identity=guard_identity
configure()

def validate_parent_join(value):
 need(value['author']=='/root' and value['target_pid']==G['pid'] and value['target_birth']==G['starttime'] and value['parent_pid']==G['parent_pid'] and value['parent_birth']==G['parent_birth'],'exact Root actual parent/target join')
 need(value['positive_direct_parent_wait'] is True and value['returncode']==-signal.SIGKILL and value['streams_closed'] is True and value['tool_session']==90401,'actual positive parent wait/closed streams/tool completion')
 need(value['first_readonly_client_status']=='UNKNOWN','old client status remains unknown after owner retirement')
 return True

def main():
 p=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha256',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args();need(a.execute,'explicit new independently released operation only')
 execute,_=rebound_protocol();print(json.dumps(execute(a.release,a.release_sha256),sort_keys=True))
if __name__=='__main__':main()
