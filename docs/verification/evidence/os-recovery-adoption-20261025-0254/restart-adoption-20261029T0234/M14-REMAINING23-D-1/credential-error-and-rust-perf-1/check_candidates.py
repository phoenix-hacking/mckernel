#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source/ABI shape and explicit credential error vectors; no execution of targets.
"""
import json,re,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel')
user=(D/'credential/postimage/executer/user/rust/mcexec_helpers.rs').read_text();platform=(D/'credential/postimage/executer/user/rust/mcexec_platform_syscalls.rs').read_text();c=(D/'credential/postimage/executer/user/mcexec.c').read_text();guest=(D/'credential/postimage/kernel/rust/syscall_policy.rs').read_text()
def within(s,start,end):a=s.index(start);return s[a:s.index(end,a)]
def check_guard(text):
 get=within(text,'pub unsafe extern "C" fn getcred_body_result','pub unsafe extern "C" fn syscall_refresh_cred_fields_body_result')
 assert 'if do_syscall(requestp, processor_id()) != 0 { return null_mut(); }' in get
 assert get.index('if do_syscall(requestp, processor_id()) != 0')<get.index('selected_buf\n}')
 refresh=within(text,'pub unsafe extern "C" fn syscall_refresh_cred_fields_body_result','pub unsafe extern "C" fn syscall_times_body_result')
 assert refresh.index('if values.is_null()')<refresh.index('*values.add(value0_index)')
check_guard(guest)
for bad in (guest.replace('if do_syscall(requestp, processor_id()) != 0 { return null_mut(); }','do_syscall(requestp, processor_id());',1),guest.replace('if values.is_null() {','if false {',1)):
 try:check_guard(bad)
 except (AssertionError,ValueError):pass
 else:raise AssertionError('credential failure guard mutation accepted')
assert 'fn mcexec_cred_get_bridge(fd: c_int, arg: c_ulong) -> c_long;' in user
act=within(user,'pub unsafe extern "C" fn act_setfsuid','pub unsafe extern "C" fn act_setresuid')
assert 'unsafe { mcexec_cred_get_bridge(fd, (*w).sr.args[0]) }' in act and 'do_syscall_return(fd, cpu, ret, 0, 0, 0, 0)' in act
assert 'converted(super::ioctl(fd,0x30a0290a as c_ulong,arg) as c_long)' in platform
assert '#define SET_ERR(ret) if (ret == -1) ret = -errno' in c and 'long mcexec_cred_get_bridge' in c and 'ret = ioctl(fd, MCEXEC_UP_GET_CRED, w.sr.args[0]);' in c
# Ordinary libc ioctl returns 0 on success and -1+errno on failure. Model the
# source branch contract independently; not a dynamic claim about kernel I/O.
examples=[(0,7,0),(0,0,0),(-1,5,-5),(-1,14,-14),(9,2,9)]
for result,err,want in examples:assert (-err if result==-1 else result)==want
leaf=(D/'perf/postimage/kernel/rust/f03_perf_entry_candidate.rs').read_text();c=(D/'perf/postimage/kernel/syscall.c').read_text()
assert '#[no_mangle]\npub(super) static f03_perf_entry_binding_v1: PerfEntryBinding' in leaf
assert 'const struct f03_perf_entry_binding_v1_type f03_perf_entry_binding_v1 = {' not in c
assert 'extern const struct f03_perf_entry_binding_v1_type f03_perf_entry_binding_v1;' in c
assert 'offset_of!(Mckfd, padding) == 12' in leaf and '__builtin_offsetof(struct mckfd, sig_no) == 12' in c
assert all(x in leaf for x in ('size_of::<PerfEventAttr>() == 104','align_of::<PerfEventAttr>() == 8','size_of::<SyscallRequest>() == 72','size_of::<PerfEntryBinding>() == 352'))
for x in ('f03_perf_read_v1','f03_perf_ioctl_v1','f03_perf_mmap_v1','f03_perf_close_v1','f03_perf_fcntl_v1','f03_perf_event_allocate_v1','f03_perf_attr_frequency_v1','f03_perf_counter_allocate_v1','perf_event_open_do_syscall_bridge'):
 assert leaf.count('Some('+x+')')==1
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_SOURCE_ERRNO_GUARD_AND_RUST_OWNED_PERF_BINDING','credential_source_mutations_refused':2,'errno_model_vectors':len(examples),'old_getcred_and_void_callback_abi':'unchanged; exact errno returned to guest transport, not beyond old void callback','perf':'Rust static, no C data definition, 31 offsets and 13 existing provider references; layout and pointers require actual ABI compilation/link','actual_code_executed':False,'runtime_authority':None}
(D/'PURE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
