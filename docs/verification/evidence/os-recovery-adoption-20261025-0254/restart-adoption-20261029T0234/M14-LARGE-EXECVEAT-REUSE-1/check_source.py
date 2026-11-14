#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source evidence only. Does not execute candidate code or replace ABI verification.
"""
from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent
pre=p.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1/preimage/kernel'
c=(pre/'syscall.c').read_text(); policy=(pre/'rust/syscall_policy.rs').read_text()
r=(p/'do_execveat.PRIVATE.rs.inc').read_text(); abi=(p/'REAL-C-ABI.PROPOSED.inc').read_text()
for x in ['f03_execveat_filename_admission_v1', 'f03_execveat_allocate_descriptor_v1',
          'f03_execveat_release_temporaries_v1', 'f03_munmap_all_current_v1',
          'f03_execveat_install_user_context_v1', 'f03_execveat_ptrace_report_v1',
          'f03_execveat_finish_switch_v1', 'exec_reset_signal_state_current_v1']:
    assert f'fn {x}(' in policy, x
assert '#line 7179' in c and '#line 7188' in c
lines=c.splitlines()
for physical, snippet, logical in [(7762,'dkprintf("execve(): ERROR: host failed',7600),
 (7768,'dkprintf("execve(): ELF desc received',7606),
 (7785,'kfilename = kmalloc_tracked',7623), (7790,'kfree_tracked(kfilename',7628),
 (7802,'kfilename = kmalloc_tracked',7640), (7807,'kfree_tracked(kfilename',7645),
 (7889,'dkprintf("execve(): switching',7727)]:
    assert snippet in lines[physical-1]
    assert logical == 7179 + physical - 7341
    assert str(logical) in abi
assert 'f03_execveat_C_ABI_v1[32]' in abi and 'f03_execveat_Rust_ABI_v1: [CULong; 32]' in r
body=r[r.index('pub unsafe extern "C" fn do_execveat('):]
sequence=['f03_execveat_filename_admission_v1(vm', 'f03_execveat_allocate_descriptor_v1(o.file',
'f03_execveat_phase1_request_init_v1(request', 'let mut ret = do_syscall(',
'flatten_strings_from_user((*desc).args', 'flatten_strings_from_user(null_mut()',
'f03_munmap_all_current_v1()', 'f03_execveat_install_user_context_v1(thread',
'prepare_process_ranges_args_envs(thread', 'super::clear_host_pte(',
'f03_execveat_phase2_request_init_v1(request', 'ret = do_syscall(',
'exec_reset_signal_state_current_v1(thread)', 'f03_execveat_ptrace_report_v1(thread',
'(*process).execed = 1', 'f03_execveat_release_temporaries_v1(envp_flat',
'f03_execveat_finish_switch_v1(thread']
start=0
for term in sequence:
    start=body.index(term,start)+len(term)
assert 'write_bytes(request' not in r
assert body.count('exec_preempt_enable();') == 2
assert body.count('let _ = exec_kill(') == 2
for name in ['do_execveat.PRIVATE.rs.inc','REAL-C-ABI.PROPOSED.inc']:
 print(name, hashlib.sha256((p/name).read_bytes()).hexdigest())
print('PASS selected source dependency, metadata mapping and transaction-order assertions; no compiler or runtime')
