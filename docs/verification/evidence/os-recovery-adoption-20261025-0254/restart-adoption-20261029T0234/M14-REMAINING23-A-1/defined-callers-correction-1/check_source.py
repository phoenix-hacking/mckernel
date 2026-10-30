#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Static source checks; does not compile, run providers, or authorize native work.
"""
from pathlib import Path
import hashlib,re
p=Path(__file__).resolve().parent
root=p.parent.parent
contract=root/'M14-REMAINING23-DEFINED-CALLER-CONTRACT-1/ROOT-CONTRACTS.APPROVED.json'
assert hashlib.sha256(contract.read_bytes()).hexdigest()=='534c4df211bcf940f19191607d8d3d26d426e2f82d3bfaa7f392c41fe06df19e'
execs=(p/'do_execveat.defined-arity.PRIVATE.rs.inc').read_text()
p1=execs[execs.index('let request_ptr = request.as_mut_ptr();'):execs.index('let mut ret = do_syscall(')]
p2=execs[execs.index('// Preserve initialized args3..5 exactly'):execs.index('ret = do_syscall(',execs.index('// Preserve initialized args3..5 exactly'))]
assert re.findall(r'\(\*request_ptr\)\.(number|args\[\d\])',p1)==['number','args[0]','args[1]','args[2]','args[3]','args[4]','args[5]']
assert re.findall(r'\(\*request_ptr\)\.(number|args\[\d\])',p2)==['number','args[0]','args[1]','args[2]']
assert '((*request_ptr).args[5]), 0)' in p1
assert 'dirfd as CLong as CULong' in p1 and 'flags as CLong as CULong' in p1
assert 'MaybeUninit::<SyscallRequest>::uninit()' in execs and 'assume_init' not in execs
assert 'TransportSeed' not in execs and 'phase1_request_init_v1' not in execs and 'phase2_request_init_v1' not in execs
assert 'errno: %ld' in execs and 'stack, ret: %ld' in execs
assert '((*request_ptr).rtid)' not in execs and '((*request_ptr).ttid)' not in execs and '((*request_ptr).valid)' not in execs
host=Path('/home/holden/mckernel/executer/user/rust/mcexec_helpers.rs').read_text()
f1=host[host.index('pub unsafe extern "C" fn act_execve_phase1('):host.index('pub unsafe extern "C" fn act_execve_phase2(')]
f2=host[host.index('pub unsafe extern "C" fn act_execve_phase2('):host.index('pub unsafe extern "C" fn mcexec_finish_main_image_body(')]
assert set(re.findall(r'\(\*w\)\.sr\.args\[(\d)\]',f1))=={'1','2','3','4'}
assert set(re.findall(r'\(\*w\)\.sr\.args\[(\d)\]',f2))=={'1','2'}
xpmem_path=root/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree/xpmem_helpers.rs'
assert hashlib.sha256(xpmem_path.read_bytes()).hexdigest()=='e8c7970b672c724f14da2eb0a12fdbcd11df62f824422a5f8a98da4364328255'
xpmem=xpmem_path.read_text()
private=(p/'xpmem-reserved-update.PROVIDER.PRIVATE.rs.inc').read_text()
canonical=xpmem[xpmem.index('static XPMEM_FAULT_PROCESS_RANGE_OPS:'):xpmem.index('#[no_mangle]',xpmem.index('static XPMEM_FAULT_PROCESS_RANGE_OPS:'))]
candidate=private[private.index('static OPS:'):private.index('unsafe extern "C" fn fault(')]
fields=lambda s:dict(re.findall(r'(\w+_fn):\s*Some\((\w+)\)',s))
a,b=fields(canonical),fields(candidate)
assert len(a)==len(b)==25 and set(a)==set(b)
assert all(a[k]==b[k] for k in a if k!='ensure_valid_fn')
assert b['ensure_valid_fn']=='ensure_valid'
assert 'src_vm, null_mut(), vaddr' in private and '(*process).pid, null_mut()' in private
registry=(p/'range-reservation.PROVIDER.PRIVATE.rs.inc').read_text()
for name in ['reserve_write','f03_mmap_range_conflicts_write_v1','release']:
 assert 'fn '+name+'(' in registry
assert 'AtomicBool::new(false)' in registry and 'AtomicPtr::new(null_mut())' in registry
assert 'range.is_null() || (*cur).range == range' in registry
mmap=(p/'do_mmap.reservation.PROVIDER-WIRED.PRIVATE.rs.inc').read_text()
part=mmap[mmap.index('let xpmem = unsafe'):mmap.index('// Population uses only scalar')]
seq=['MaybeUninit::<Reservation>::uninit()', 'reservation::reserve_write(',
     'ihk_rwspinlock_write_unlock_noirq', 'f03_mmap_xpmem_update_reserved_v1',
     'if error != 0', 'reservation::release(']
pos=0
for v in seq:pos=part.index(v,pos)+len(v)
assert 'panic!("mmap reservation registration invariant")' in part
for f in ['do_execveat.defined-arity.PRIVATE.rs.inc','execveat.REAL-C-ABI.PROPOSED.inc',
          'range-reservation.PROVIDER.PRIVATE.rs.inc','xpmem-reserved-update.PROVIDER.PRIVATE.rs.inc',
          'do_mmap.reservation.PROVIDER-WIRED.PRIVATE.rs.inc']:
 print(f,hashlib.sha256((p/f).read_bytes()).hexdigest())
print('PASS static approved fields, executor arities, callback equality, reservation flow; no compile or runtime')
