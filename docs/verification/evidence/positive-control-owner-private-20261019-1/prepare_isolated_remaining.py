from pathlib import Path
import sys,hashlib,json,difflib,re,ast
sys.path.insert(0,'/home/holden/mckernel');from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;A=P/'third-failed-inputs';A.mkdir(exist_ok=True);archive=[]
for n in ['actual-control-park-expert.rs','fixture-inputs-expert.json','run_control_check_expert.py','check-expert-proposal.json','actual-body-bindings-expert.json','fixture-expert-delta.patch','new-four-delivery-setup-review.json']:
 f=P/n;data=f.read_bytes();assert not(A/n).exists()or(A/n).read_bytes()==data;(A/n).write_bytes(data);archive.append({'consumed_path':str(f),'retained_path':str(A/n),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(A/'archive-map.json').write_text(json.dumps(archive,indent=2)+'\n')
s=(P/'actual-control-park-expert.rs').read_text();old=s
# Preserve every scenario body/assertion; remove only the reinitializing loop.
def split_test(name,loop_needle,cases):
 global s
 fn=balanced_item(s,'fn '+name+'(');loop=balanced_item(fn,loop_needle);body=loop[loop.index('{')+1:-1];new=[]
 for suffix,declaration in cases:new.append('fn '+name+'_'+suffix+'(){\n '+declaration+'\n'+body+'\n}')
 assert s.count(fn)==1;s=s.replace(fn,'\n#[test]'.join(new),1)
split_test('actual_control_wrong_identity_epoch_phase_and_overflow_have_no_transfer','for case in 0..4 {',[(name,'let case='+str(i)+';')for i,name in enumerate(['geometry','epoch','pending_phase','overflow'])])
split_test('actual_control_restore_conflict_retains_exact_claim_and_response_after_close','for replace_epoch in [false,true] {',[('phase','let replace_epoch=false;'),('epoch','let replace_epoch=true;')])
# The two old Request identities remain reserved even after first-RET Memory
# release. Only a third genuinely fresh, zero-initialized response is eligible.
needle=''' // first_return() proved zero response claims, then parkedcontrol owns ONLY
 // 0x1c00000. Admit below must itself prove 0x1b00000 is available again.
 bytes[120..128].copy_from_slice(&0x1b00000u64.to_le_bytes());'''
replacement=''' // The immutable original fixture initializes a16MiB arena at0x1000000.
 // Retained delivery identities1b/1c stay reserved regardless of Memoryclaims.
 // Third response1d is disjoint, aligned, and inside the initialized arena.
 bytes[120..128].copy_from_slice(&0x1d00000u64.to_le_bytes());'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle=''' assert_eq!(p.syscalls.open_worker(201),Err(EBUSY));let w=p.syscalls.open_worker(202).unwrap();
 p.syscalls.admit(request,|r|memory.syscall(r)).unwrap();'''
replacement=''' assert_eq!(p.syscalls.open_worker(201),Err(EBUSY));let w=p.syscalls.open_worker(202).unwrap();
 assert!(p.syscalls.fixture_response_identity_held(0x1b00000));
 assert!(p.syscalls.fixture_response_identity_held(0x1c00000));
 assert_eq!(request.response(),0x1d00000);assert!(!p.syscalls.fixture_response_identity_held(request.response()));
 p.syscalls.admit(request,|r|memory.syscall(r)).unwrap();'''
assert s.count(needle)==1;s=s.replace(needle,replacement)
# Explicit test-only private-table observation; actual admit_inner still makes
# the admission decision and must succeed without any identity-rule change.
needle='pub(crate) fn has_private_fork_response('
assert s.count(needle)==1;s=s.replace(needle,'''    #[cfg(test)] pub(crate) fn fixture_response_identity_held(&self,physical:u64)->bool{
        self.calls.iter().flatten().any(|call|call.delivery.request().response()==physical)
    }
'''+needle)
f=P/'actual-control-park-isolated.rs';f.write_text(s)
names=re.findall(r'#\[test\]fn (actual_control_[A-Za-z0-9_]+)\(',s);assert len(names)==8,names
oldrunner=(P/'run_control_check_expert.py').read_text();tree=ast.parse(oldrunner);node=next(n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='COMMANDS'for x in n.targets));lines=oldrunner.splitlines(True);command_source=''.join(lines[node.lineno-1:node.end_lineno]);compile_cmd="['compile',[RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(R/'actual-control-park-isolated.rs'),'-C','link-arg='+str(OLD/'guest.o'),'-C','link-arg='+str(OLD/'codec.o'),'-o',str(E/'actual')]]"
commands='COMMANDS=['+compile_cmd
labels=[]
for i,name in enumerate(names):
 label='scenario-'+str(i+1);labels.append(label);commands+=",['"+label+"',[str(E/'actual'),'--exact','consumer_fixture::actual::"+name+"','--test-threads=1','--nocapture']]"
commands+=']\n';runner=oldrunner.replace(command_source,commands,1).replace("E=R/'check-3'","E=R/'check-4'").replace("R/'fixture-inputs-expert.json'","R/'fixture-inputs-isolated.json'")
needle=" assert '4 passed; 0 failed' in(E/'affected-test.stdout').read_text()";assert needle in runner;runner=runner.replace(needle," for label in "+repr(labels)+":assert '1 passed; 0 failed' in(E/(label+'.stdout')).read_text()")
runner=runner.replace("'new_tests':4","'new_tests':8").replace("'commands':len(rows)","'commands':len(rows),'same_failure_family':True,'old51_executed':False")
f=P/'run_control_check_isolated.py';f.write_text(runner);ast.parse(runner)
inputs=json.loads((P/'fixture-inputs-expert.json').read_text());inputs['inputs']=[r for r in inputs['inputs']if Path(r['path']).name not in ['actual-control-park-expert.rs','run_control_check_expert.py']]
for f in [P/'actual-control-park-isolated.rs',P/'run_control_check_isolated.py',Path(__file__),Path('/home/holden/mckernel-work/scratch/native-fork-carrier-link-20261017-1/test-expert/guest/actual_guest.c')]:inputs['inputs'].append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
inputs['tests']=8;inputs['process_isolation']='One authentic once-only guest fixture per exactscenario process; no reset/no old51execution';inputs['expert_diagnosis']={'path':'/home/holden/mckernel-work/host-preparation/provider-ownership-review-20261019-1/POSITIVE-CONTROL-MAILBOX-IDENTITY-AND-PROCESS-ISOLATION-EXPERT-DIAGNOSIS.json','sha256':'a2e58ffad4ef9a565e531eb8d5dde7f8528b45362d975d4d16340afd6b61b2fb'}
(P/'fixture-inputs-isolated.json').write_text(json.dumps(inputs,indent=2)+'\n')
proposal=json.loads((P/'check-expert-proposal.json').read_text());proposal['status']='EXPERT_WHOLE_SETUP_CORRECTION_READY_NOT_RUN';proposal['argv'][-1]=str(P/'run_control_check_isolated.py');proposal['capture_stdout']=str(P/'whole-check-isolated.stdout');proposal['capture_stderr']=str(P/'whole-check-isolated.stderr');proposal['output']=str(P/'check-4');proposal['commands']=9;proposal['new_tests']=8;proposal['exact_scenario_names']=names;proposal['inner_argv']=[]
RUSTC='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc';OLD=Path('/home/holden/mckernel-work/scratch/native-fork-carrier-link-20261017-1/test-expert');E=P/'check-4'
proposal['inner_argv'].append([RUSTC,'--edition=2021','--test','-Wrust_2018_idioms','-Dwarnings',str(P/'actual-control-park-isolated.rs'),'-C','link-arg='+str(OLD/'guest.o'),'-C','link-arg='+str(OLD/'codec.o'),'-o',str(E/'actual')])
for name in names:proposal['inner_argv'].append([str(E/'actual'),'--exact','consumer_fixture::actual::'+name,'--test-threads=1','--nocapture'])
proposal['prior_failures']=[str(P/n)for n in ['whole-check.status.json','whole-check-correction.status.json','whole-check-expert.status.json']];proposal['expert_diagnosis']=inputs['expert_diagnosis'];proposal['inputs']=[]
for f in [P/'positive-control-park.patch',P/'source-pins.json',P/'fixture-inputs-isolated.json',P/'actual-control-park-isolated.rs',P/'run_control_check_isolated.py',A/'archive-map.json']:
 proposal['inputs'].append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(P/'check-isolated-proposal.json').write_text(json.dumps(proposal,indent=2)+'\n')
(P/'fixture-isolation-delta.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='expert-failed-fixture.rs',tofile='isolated-scenario-fixture.rs')))
measured=[]
for parent in ['check-1','check-2','check-3']:
 for f in (P/parent).glob('*.status.json'):
  r=json.loads(f.read_text());measured.append({'path':str(f),'elapsed_ns':r['elapsed_ns'],'returncode':r['returncode']})
(P/'isolated-resource-plan.json').write_text(json.dumps({'commands':9,'compile_once':True,'isolated_scenarios':8,'serial_jobs':1,'cpu':6,'as':1073741824,'cpu_seconds':30,'whole_inner_deadline':28,'outer_timeout':35,'outer_kill_grace':2,'filecap':33554432,'total_growth_cap':33554432,'arena_bytes_per_child':16*1024**2,'arena_physical':[0x1000000,0x2000000],'all_retained_response_identities':[0x1b00000,0x1c00000],'fresh_response':0x1d00000,'old_measured_commands':measured,'feasibility':'Existing same-profile compilation and actualfixture execution alreadycompleted; eight serial freshprocesses retain one16MiB arena perprocess and are bounded by SAME global28deadline. No aggregate-memory multiplication; stopfirstfailure/deadline, no runtimeguaranteeclaimed.','family_preserved':proposal['prior_failures']},indent=2)+'\n')
print('isolated_proposal_sha256',hashlib.sha256((P/'check-isolated-proposal.json').read_bytes()).hexdigest(),'commands',9,'scenarios',8)
