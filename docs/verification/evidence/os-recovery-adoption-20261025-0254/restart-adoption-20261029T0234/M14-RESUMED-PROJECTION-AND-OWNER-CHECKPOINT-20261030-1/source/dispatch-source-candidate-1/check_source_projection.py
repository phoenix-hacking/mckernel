"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
UNRUN regression source: exact source-binding, caller writes, and rebase checks.
No compiler, container, runtime, native or service capability is requested here.
"""
from pathlib import Path
import hashlib,json,re,difflib
D=Path(__file__).resolve().parent
inputs=json.loads((D/'INPUTS.json').read_text())['inputs']
for row in inputs:
    assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
repo=Path('/home/holden/mckernel')
e=repo/'docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234'
c=(D/'postimage/kernel/syscall.c').read_text()
r=(D/'COMBINED-RUST-BODIES.rs.inc').read_text()
for name in ['DO-SYSCALL','UTIL-THREAD']:
    p=e/f'M14-LARGE-{name}-REUSE-1'
    body=(p/'RUST-BODY.REUSED.rs.inc').read_text()
    assert r.count(body)==1
    # Every line inserted by each original packet still appears contiguously.
    old=(repo/'kernel/syscall.c').read_text().splitlines(True)
    new=(p/'syscall.PRIVATE.c').read_text().splitlines(True)
    for tag,a,b,x,y in difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes():
        if tag!='equal':assert ''.join(new[x:y]) in c
ctor=(D/'postimage/kernel/rust/f03_request_constructors.rs').read_text()
assert 'MaybeUninit::<SyscallRequest>::uninit()' in ctor
assert 'align(64)' not in ctor and '.assume_init' not in ctor
for slot in range(6):assert f'slots.add({slot}).write(args[{slot}]);' in ctor
assert '[arg0, arg1, 0, 0, 0, 0]' in ctor
assert '[arg0, arg1, arg2, 0, 0, 0]' in ctor
assert '[pid as CULong, 0, options as CULong, 0, 0, 0]' in ctor
assert not re.search(r'\(\*request\)\.(rtid|ttid|valid)\).*write',ctor)
util=r[r.index('mod f03_util_thread_whole_v1'):]
assert util.index('write_volatile(addr_of_mut!((*thread).uti_state), *constants.add(3)') < util.index('write_volatile(addr_of_mut!((*request).args[5]), 0)') < util.index('let rc = existing_do_syscall(')
assert util.count('write_volatile(field_ptr::<')==12
assert util.index('(*layout).refill_tid') < util.index('release(context, (*origins).context_free)')
h=(D/'mcexec_util_thread_body.PRIVATE.rs.inc').read_text()
assert h.count('(*uti_desc).uti_info = uti_info;')==1
assert h.index('mcexec_util_thread_param_large_bridge()') < h.index('(*uti_desc).uti_info = uti_info;')
assert h.index('mcexec_util_thread_attr_error_bridge(errno_value)') < h.index('(*uti_desc).uti_info = uti_info;')
assert h.index('(*uti_desc).uti_info = uti_info;') < h.index('(*uti_desc).start_syscall_intercept = 1;') < h.index('mcexec_util_thread_switch_ctx_bridge(')
assert '(*uti_desc).uti_info = 0' not in h
assert r.index('syscall_offload_wait_reply(request, response_ptr, cpu, thread)') < r.index('read_volatile(addr_of!((*response_ptr).ret))')
print('PASS source projection only; no ABI/codegen/lifetime/default/native acceptance')
