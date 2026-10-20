from pathlib import Path
import shutil,re,hashlib,json
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel')
B=Path('/home/holden/mckernel-work/host-preparation/phase5-runnable-child-parent-wait-20261020-1/runtime-fixture-1')
OLD=Path('/home/holden/mckernel-work/host-preparation/current-v6-fork-adoption-20261020-1/phase4-revoke-ack-correction-1/guest-fixture-1/actual-phase4.rs')
F=P/'fixture';F.mkdir();rows=[]
def digest(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
for p in B.glob('*.rs'):
 if p.name!='actual-phase5.rs':shutil.copyfile(p,F/p.name)
for name in ['abi.rs','fork_control_guest.rs','fork_control_registry.rs','fork_child_credits.rs','fork_constructed_credits.rs','fork_final_ack.rs','fork_runnable_child.rs']:
 src=R/'kernel/rust'/name;shutil.copyfile(src,F/name);rows.append({'current_production':digest(src),'fixture':digest(F/name),'whole_module_equal':True})
def function(text,name):
 m=re.search(r'(?m)^(?:pub(?:\([^\n]+?\))? )?(?:unsafe )?(?:extern "C" )?fn '+name+r'\(',text);assert m,name
 begin=text.index('{',m.start());depth=1;i=begin+1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[m.start():i]
# This current production body is compiled. Its unexercised final-VM callback
# fails closed; no runtime provider or runtime destruction proof is claimed.
source=(R/'kernel/rust/process_helpers.rs').read_text();body=function(source,'release_thread_runtime_final_checked')
with (F/'process_helpers.rs').open('a')as f:f.write('\n'+body+'\nunsafe extern "C" fn process_release_vm_final_checked_bridge(_: *mut c_void)->CInt{panic!("runtime-final VM callback outside normal-fork test scope")}\n')
rows.append({'source':str(R/'kernel/rust/process_helpers.rs'),'item':'release_thread_runtime_final_checked','sha256':hashlib.sha256(body.encode()).hexdigest(),'actual_body_equal':True})
with (F/'x86_cpu_helpers.rs').open('a')as f:f.write('\npub unsafe fn cpu_interrupt_disabled()->i32{0}\n')
text=OLD.read_text().replace('phase4_tests','phase5_tests')
text=text.replace('mod application_rpc;mod application_syscall;','mod application_rpc;mod application_syscall;mod sched_helpers;mod syscall_policy;mod lock_helpers;')
text=text.replace('pub unsafe fn set(p:', 'pub unsafe fn preempt_disable(){} pub unsafe fn preempt_enable(){}\n pub unsafe fn set(p:')
text=text.replace('mod x86_memory_helpers{','mod x86_memory_helpers{pub unsafe fn write_process_vm(_: *mut crate::abi::ProcessVm,_:*mut core::ffi::c_void,_:*const core::ffi::c_void,_:usize)->i32{panic!("runtime VM write outside normal-fork test scope")}')
text=text.replace('mod phase5_tests{','mod phase5_tests{\n pub fn mode()->usize{panic!("runtime scheduler outside normal-fork test scope")}pub fn target()->*mut crate::abi::CpuLocalVar{panic!("runtime scheduler outside normal-fork test scope")}pub fn queued(){panic!("runtime scheduler outside normal-fork test scope")}')
# Fault occurs after all real checked destructive consumer calls, before final
# transport certainty. Mode 5 fails transport; mode 6 returns scalar 0 without
# executing the actual response observer.
text=text.replace('if MODE.load(Ordering::SeqCst)==3{frame[120]^=1;}','if MODE.load(Ordering::SeqCst)==3{frame[120]^=1;}\n   if MODE.load(Ordering::SeqCst)==5{return -5;}\n   if MODE.load(Ordering::SeqCst)==6{return 0;}')
# Existing baseline tests remain preserved but new test selection is explicit.
insert=r'''
 #[test]fn finalack_uncertainty_transport_error_retains_exact_owners(){unsafe{uncertain(5,-5)}}
 #[test]fn finalack_uncertainty_missing_publication_retains_exact_owners(){unsafe{uncertain(6,-13)}}
 unsafe fn uncertain(mode:usize,error:i32){
  let(out,parent,before)=run(mode);assert_eq!((out.disposition,out.error),(1,error));
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst)),(1,1,1,1));
  assert_eq!(CALLS.load(Ordering::SeqCst),3);assert_eq!(CPU.load(Ordering::SeqCst),0);assert_eq!((*parent).refcount.counter,2);
  assert_eq!(mem_helpers::live(),before+5);
  let owners=fork_control_guest::uncertainty_owners(out.handle).expect("retained allocation remains discoverable");
  assert!(owners.iter().all(|p|*p!=0));
  let mut unique=owners.to_vec();unique.sort();unique.dedup();assert_eq!(unique.len(),4);
  // A repeated actual production terminal call cannot reacquire the graph
  // permit, repeat destructive callbacks or manufacture successful retirement.
  assert_eq!(fork_control_guest::retry_final_ack(out.handle),-13);
  assert_eq!(fork_control_guest::uncertainty_owners(out.handle),Some(owners));
  assert_eq!(mem_helpers::live(),before+5);assert_eq!((*parent).refcount.counter,2);
  assert_eq!(CALLS.load(Ordering::SeqCst),3);assert_eq!(CPU.load(Ordering::SeqCst),0);
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst)),(1,1,1,1));
 }
 #[test]fn finalack_uncertainty_success_retires_once_and_retry_cannot_free(){unsafe{
  let(out,parent,before)=run(0);assert_eq!((out.disposition,out.error),(2,-11));
  assert_eq!(mem_helpers::live(),before);assert_eq!((*parent).refcount.counter,1);assert_eq!(CPU.load(Ordering::SeqCst),1);
  assert_eq!(fork_control_guest::retry_final_ack(out.handle),-2);
  assert_eq!(mem_helpers::live(),before);assert_eq!((*parent).refcount.counter,1);assert_eq!(CPU.load(Ordering::SeqCst),1);
  assert_eq!(CALLS.load(Ordering::SeqCst),3);
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst)),(1,1,1,1));
 }}
'''
text=text.rstrip();assert text[-1]=='}';text=text[:-1]+insert+'}\n';(F/'actual-finalack.rs').write_text(text)
with (F/'fork_control_guest.rs').open('a')as f:f.write(r'''
// Test-only readout: production Carrier layout and real registry visit.
pub(crate) unsafe fn uncertainty_owners(handle:Handle)->Option<[usize;4]>{let mut result=None;
 let rc=registry::visit(handle,|p|{let c=p.as_ref();assert_eq!(c.phase,RETAINED);
 assert!(c.owned_credits.as_ref().is_some_and(|v|v.retirement_complete(false)));
 assert_eq!(c.control.state,RETAINED);
 assert!(c.owned_request.is_some());
 result=Some([c.request,
 c.retired_control.as_ref().unwrap().request.as_ptr()as usize,
 c.control.owned_request.as_ref().unwrap().request.as_ptr()as usize,c as *const Carrier as usize]);0});
 if rc==0{result}else{None}}
pub(crate) unsafe fn retry_final_ack(handle:Handle)->i32{destroy_and_ack_current(handle)}
''')
(P/'SOURCE-BINDING.json').write_text(json.dumps({'current_whole_modules_before_test_append':rows,'old_actual_body_harness':digest(OLD),'adapters':['existing clone constructor and VM-release callback','host physical identity and final transport fault injection','unprivileged single-thread preempt and IF context','unexecuted runtime-final VM/write/runqueue paths panic; no runtime proof'],'tests':'finalack_uncertainty_ only','source_modifications':'none; test-only accessors appended to private guest copy'},indent=2)+'\n')
print('Prepared private current consumer with 3 focused tests; no compiler execution.')
