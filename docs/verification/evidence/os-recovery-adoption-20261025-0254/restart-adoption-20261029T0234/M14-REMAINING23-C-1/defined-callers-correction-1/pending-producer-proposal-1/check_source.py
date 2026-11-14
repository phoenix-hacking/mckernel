from pathlib import Path
import hashlib,json
here=Path(__file__).resolve().parent;parent=here.parent.parent.parent
old=(parent/'M14-PRIVATE-NINE-LEAF-BATCH-1/postimage/kernel/rust/syscall_policy.rs').read_text();source=(here/'syscall_ptrace_setsiginfo_staged.PROPOSAL.rs').read_text()
assert 'pub unsafe extern "C" fn ptrace_setsiginfo_body_result(' in old
assert 'pub unsafe extern "C" fn f03_ptrace_setsiginfo_v1(' in old
orig=old[old.index('pub unsafe extern "C" fn ptrace_setsiginfo_body_result('):old.index('#[no_mangle]\npub unsafe extern "C" fn ptrace_wakeup_sig_body_result(')]
assert orig.index('PTRACE_SIGINFO_ALLOC_SENDSIG,\n                        allocated,') < orig.index('let copy_rc = unsafe { copy_from_user(scratch, data, info_size)')
assert source.count('syscall_copy_from_user_bridge(')==2
alloc=source.index('staged = unsafe { syscall_alloc_bridge(')
copy=source.index('let copy_rc = unsafe { syscall_copy_from_user_bridge(')
fill=source.index('copy_nonoverlapping(scratch.as_ptr().cast::<u8>()')
publish=source.index('rc = ptrace_setsiginfo_store_result(',fill)
clear=source.index('staged = core::ptr::null_mut(); // ownership transferred to slot',publish)
recv=source.index('if rc == 0 && (target & PTRACE_SIGINFO_STORE_RECVSIG)',clear)
free=source.index('if !staged.is_null() {',recv)
unlock=source.index('f03_ptrace_io_unlock(child)',free)
assert alloc<copy<fill<publish<clear<recv<free<unlock
assert 'ptrace_setsiginfo_target_result(status, (sendsig != 0) as CInt, (recvsig != 0) as CInt)' in source
assert 'PTRACE_SIGINFO_ALLOC_SENDSIG,\n                        staged as CULong, core::ptr::null(), 0' in source
assert 'crate::mem_helpers::kfree_tracked(staged.cast::<c_void>()' in source
assert 'concat!(file!(), "\\0")' in source
assert 'pub unsafe fn f03_ptrace_setsiginfo_staged_v2' in source and '#[no_mangle]' not in source and '#[export_name' not in source
# Contract model: describes intended decisions, not actual Rust execution.
def scenario(has_send,has_recv,alloc_ok,copy1_ok,copy2_ok=True):
 events=['find','target']; slot='old' if has_send else None; staged=False;rc=0
 if not has_send:
  events.append('allocate')
  if not alloc_ok:rc=-12
  else:staged=True
 if rc==0:
  events.append('copy_send')
  if not copy1_ok:rc=-14
  elif staged:
   events+=['fill_private','publish'];slot='new-valid';staged=False
  else:events+=['update_old'];slot='old-valid'
 if rc==0 and has_recv:
  events.append('copy_recv')
  if not copy2_ok:rc=-14
  else:events.append('update_recv')
 if staged:events.append('free_private')
 events.append('unlock');return rc,slot,events
assert scenario(False,False,False,True)==(-12,None,['find','target','allocate','unlock'])
assert scenario(False,False,True,False)==(-14,None,['find','target','allocate','copy_send','free_private','unlock'])
assert scenario(False,False,True,True)==(0,'new-valid',['find','target','allocate','copy_send','fill_private','publish','unlock'])
assert scenario(False,True,True,True,False)==(-14,'new-valid',['find','target','allocate','copy_send','fill_private','publish','copy_recv','unlock'])
assert scenario(True,False,True,False)==(-14,'old',['find','target','copy_send','unlock'])
def info(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
r={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'UNSELECTED_PRODUCER_CONTRACT_PROPOSAL','checks':['original fresh allocation published before copy in retained source','proposed fresh allocation copy-before-publish and exact cleanup edge','existing sendsig branch and separate recvsig second-copy order retained','five pure abstract failure/success contract vectors','no C ABI export or source selection'], 'candidate':info(here/'syscall_ptrace_setsiginfo_staged.PROPOSAL.rs'),'limitations':'The vectors model intended sequencing; they do not execute Rust, actual usercopy, allocator, concurrency, compiler or kernel. Root must approve the changed failure publication and allocator/free provenance, plus prove original slot exclusion/ownership, race handling and lifetime before integration.'}
(here/'SOURCE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
