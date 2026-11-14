from pathlib import Path
import sys,hashlib,json,shutil
sys.path.insert(0,'/home/holden/mckernel');from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;S=P/'source/host-kernel/native-rust';A=P/'first-failed-inputs';assert not A.exists();A.mkdir()
names=['actual-control-park.rs','fixture-link.rs','fixture-ingress.rs','prepare_fixture.py','run_control_check.py','fixture-inputs.json','check-proposal.json','actual-body-bindings.json','source-pins.json']
archive=[]
for n in names:
 data=(P/n).read_bytes();(A/n).write_bytes(data);archive.append({'consumed_path':str(P/n),'retained_path':str(A/n),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(A/'archive-map.json').write_text(json.dumps(archive,indent=2)+'\n')
f=P/'actual-control-park.rs';s=f.read_text();replacements=[]
def change(a,b,count=1):
 global s
 assert s.count(a)==count,(a[:70],s.count(a),count);s=s.replace(a,b);replacements.append({'needle':a[:100],'count':count})
# Compile the exact real ACK authorization dependency instead of a permissive stub.
actual=balanced_item((S/'smp_application.rs').read_text(),'fn authorize_fork_ack_return(')
change('fn authorize_fork_return(',actual+'\nfn authorize_fork_return(')
# This held branch counter is u32; current-main unrelated primitive uses usize.
change('->(usize,bool,bool,ForkPhase,u64)', '->(u32,bool,bool,ForkPhase,u64)')
change('parent_count(remote:&Remote,n:usize)', 'parent_count(remote:&Remote,n:u32)')
change('parent_count(&j.remote,usize::MAX)', 'parent_count(&j.remote,u32::MAX)')
change('f.link.as_ref().unwrap().last_sequence)', 'fork_link::control_sequence(f.link.as_ref().unwrap()))')
change('(p.fork_prepared_parent_refs,f.control.is_some(),false,', '(p.fork_prepared_parent_refs,f.control.is_some(),f.control.as_ref().is_some_and(fork_link::control_quarantined),')
change('struct Arc<T>{inner:std::sync::Arc<T>}', 'struct Arc<T>{inner:std::sync::Arc<T>}\nimpl<T> Arc<T>{fn strong_count(this:&Self)->usize{std::sync::Arc::strong_count(&this.inner)}}')
change('assert_eq!(state.0,2);assert!(state.1);\n  crate::smp_application::check_control_owned', 'assert_eq!(state.0,2);assert!(state.1&&state.2);\n  crate::smp_application::check_control_owned')
f.write_text(s)
f=P/'fixture-link.rs';s=f.read_text();s+='\n#[cfg(test)] pub(super) fn control_sequence(link:&ForkLinkRecord)->u64{link.last_sequence}\n#[cfg(test)] pub(super) fn control_quarantined(owner:&ForkControlOwner)->bool{owner.quarantined}\n';f.write_text(s)
# Runner changes ONLY fresh output path: same source/tool/limits/commands/filter.
f=P/'run_control_check_correction.py';s=(P/'run_control_check.py').read_text();assert "E=R/'check-1'"in s;s=s.replace("E=R/'check-1'","E=R/'check-2'");f.write_text(s)
inputs=json.loads((P/'fixture-inputs.json').read_text());skip={str(P/'run_control_check.py')};inputs['inputs']=[r for r in inputs['inputs']if r['path']not in skip]
for row in inputs['inputs']:
 f=Path(row['path']);row['sha256']=hashlib.sha256(f.read_bytes()).hexdigest();row['bytes']=f.stat().st_size
for f in [P/'run_control_check_correction.py',Path(__file__)]:inputs['inputs'].append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
inputs['fixture_correction']='Exact ACK authorization dependency; u32 counter; child-private read-only getters; stdArc refcount observer only; production8sources unchanged'
(P/'fixture-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
proposal=json.loads((P/'check-proposal.json').read_text());proposal['argv'][-1]=str(P/'run_control_check_correction.py');proposal['capture_stdout']=str(P/'whole-check-correction.stdout');proposal['capture_stderr']=str(P/'whole-check-correction.stderr');proposal['output']=str(P/'check-2');proposal['inputs']=[]
for f in [P/'positive-control-park.patch',P/'source-pins.json',P/'fixture-inputs.json',P/'actual-control-park.rs',P/'run_control_check_correction.py',A/'archive-map.json']:
 proposal['inputs'].append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(P/'check-correction-proposal.json').write_text(json.dumps(proposal,indent=2)+'\n');(P/'fixture-correction-delta.json').write_text(json.dumps({'status':'READY_NOT_RUN','production_source_unchanged':True,'first_failure':str(P/'whole-check.status.json'),'retained_inputs':str(A/'archive-map.json'),'changes':replacements,'new_source_dependency':{'name':'authorize_fork_ack_return','sha256':hashlib.sha256(actual.encode()).hexdigest()}},indent=2)+'\n')
print('fixture_corrections',len(replacements),'production_unchanged',True,'proposal_sha256',hashlib.sha256((P/'check-correction-proposal.json').read_bytes()).hexdigest())
