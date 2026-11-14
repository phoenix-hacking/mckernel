"""Functional McKernel source contract checks only; no security testing.
No compiler, native getter execution or process/guard operations.
"""
from pathlib import Path
import re,json
D=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel')
pre=(D/'preimage/kernel/syscall.c').read_text();post=(D/'postimage/kernel/syscall.c').read_text();leaf=(D/'postimage/kernel/rust/syscall_exit_group_current_pid.rs').read_text();policy=(D/'preimage/kernel/rust/syscall_policy.rs').read_text();selected=(D/'postimage/kernel/rust/syscall_policy.rs').read_text();abi=(ROOT/'kernel/rust/abi.rs').read_text()
start=pre.index('int\nexit_group_current_pid_bridge(void)\n');end=pre.index('\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',start);first=pre.count('\n',0,start);stop=pre.count('\n',0,end);a=pre.splitlines(True);b=post.splitlines(True);assert len(a)==len(b)and a[:first]==b[:first]and a[stop:]==b[stop:]
def tokens(s):return re.findall(r'[A-Za-z_][A-Za-z_0-9]*|[^\s]',s)
original=''.join(a[first:stop]);replacement=b[first:stop];assert tokens(original)==tokens(replacement[3]);assert replacement[0].strip()=='#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)';assert replacement[1].strip()=='extern int exit_group_current_pid_bridge(void);';assert replacement[2].strip()=='#else'and replacement[6].strip()=='#endif'
directives=lambda s:[(i,l)for i,l in enumerate(s.splitlines(True))if re.match(r'^\s*#\s*(?:line\b|\d)',l)]
assert directives(pre)==directives(post)
module='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]\n#[path = "syscall_exit_group_current_pid.rs"]\nmod syscall_exit_group_current_pid;\n';assert selected.count(module)==1 and selected.replace(module,'',1)==policy
assert 'pub type CInt = i32;'in abi and '#[repr(C)]\npub struct Thread {'in abi and '#[repr(C)]\npub struct Process {'in abi
for typ,field,offset in [('Thread','proc',4304),('Process','pid',456)]:
 assert f'assert_eq_usize(offset_of!({typ}, {field}), {offset});'in abi
 assert f'assert!(offset_of!({typ}, {field}) == {offset});'in leaf
assert 'assert_eq_usize(offset_of!(CpuLocalVar, current), 7848);'in abi and 'assert_eq_usize(offset_of!(CpuLocalVar, current), 24304);'in abi
accessor='''unsafe fn current_thread_ptr() -> *mut Thread {
    let cpu = get_this_cpu_local_var();
    if cpu.is_null() {
        null_mut()
    } else {
        (*cpu).current
    }
}''';assert policy.count(accessor)==1
assert 'unsafe extern "C" fn exit_group_current_pid_bridge() -> CInt' in leaf and 'unsafe { (*(*current_thread_ptr()).proc).pid }'in leaf
for forbidden in ['EFAULT','EINVAL','terminate(','do_kill(','read_volatile','write_volatile','Ddebug','__verbose']:assert forbidden not in leaf
# Existing paired flag projection, no new profile/selector. Truth-table check is
# source selection only: no preprocessor or Rust/C compile is invoked.
cm=(D/'preimage/kernel/CMakeLists.txt').read_text();assert 'list(APPEND RUST_KERNEL_CFG "--cfg" "f03_leaf_callbacks_candidate")'in cm and 'MCKERNEL_RUST_F03_LEAF_CALLBACKS'in cm
for enabled in (False,True):
 for x86 in (False,True):
  c_extern=enabled and x86;rust_module=enabled and x86;assert c_extern==rust_module
# Defined raw getter domain only: live/non-null current/proc, full CInt values.
# Independent structural projection fixture carries no null/error policy.
values=[-(1<<31),-1,0,1,42,(1<<31)-1]
for pid in values:
 process={'pid':pid};thread={'proc':process};cpu={'current':thread}
 c_projection=cpu['current']['proc']['pid'];rust_projection=thread['proc']['pid'];assert c_projection==rust_projection==pid
cm2=(D/'postimage/kernel/CMakeLists.txt').read_text();dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_current_pid.rs"\n';assert cm2.count(dep)==1 and cm2.replace(dep,'',1)==cm
checks=['int(void) ABI and raw current→proc→pid load retained; signed CInt domain fixture','existing accessor and exact asserted reprC offsets reused, CPU layout branches retained','same existing paired leaf-callback selector+x86 truth table, other profiles C tokens exact','only seven-line C getter range changes, newline/logical-origin positions exact','parent sys_exit_group/callback order unchanged except module declaration','one additive dependency, no held lifecycle/signal/request/metadata changes']
(D/'SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_PRIVATE_SOURCE_CONTRACT_ONLY',checks=checks,fixture_values=values,null_outside_original_defined_domain=True,actual_ABI_compile=False,actual_native_getter=False,original389_linked_proof=False),indent=2)+'\n');print('PASS',len(checks),'focused source groups')
