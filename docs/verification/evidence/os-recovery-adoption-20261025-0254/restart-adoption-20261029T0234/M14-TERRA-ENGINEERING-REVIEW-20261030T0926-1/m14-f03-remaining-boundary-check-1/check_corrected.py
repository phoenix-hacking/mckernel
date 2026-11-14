#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only check, no compilation or project runtime.
"""
from pathlib import Path
import hashlib,json,re
p=Path(__file__).parent;root=p.parent.parent
c=root/'nonheld-generic-arch-host-preparation-1/src/kernel/syscall.c'
r=root/'f06-debug-constants-align32-host-1/src/kernel/rust/syscall_mprotect_host_vma.rs'
policy=root/'f06-debug-constants-align32-host-1/src/kernel/rust/syscall_policy.rs'
kfree=root/'f06-debug-constants-align32-host-1/src/kernel/rust/syscall_ptrace_detach_kfree.rs'
cmake=p.parent/'m14-root-and-nonheld-composite-1/postimage/kernel/CMakeLists.txt'
s=c.read_text();v=r.read_text();q=policy.read_text();m=cmake.read_text();k=kfree.read_text()
start=s.index('\ndo_mmap(const uintptr_t');end=s.index('\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nvoid munmap_write_lock_bridge',start);body=s[start:end]
call_lines=[i+1 for i,line in enumerate(s.splitlines()) if 'set_host_vma(' in line and 'do_mmap:set_host_vma' not in line]
assert len(re.findall(r'(?:error =|\(void\))set_host_vma\(',body))==3
assert 'mprotect_set_host_vma_bridge' in v and 'set_host_vma_body_result(start, len, prot, holding_lock)' in v
assert all(x in v for x in ('ihk_mc_syscall_set_arg0','ihk_mc_syscall_set_arg1','ihk_mc_syscall_set_arg2'))
start=q.index('pub extern "C" fn set_host_vma_body_result(');end=q.index('\n#[no_mangle]',start);under=q[start:end]
assert 'clear_host_pte_body_result(' in under and 'Some(syscall_policy_do_syscall3_bridge)' in under
assert 'ptrace_detach_kfree_bridge' in s and 'f03_ptrace_kfree_profile_119' in q
assert 'MCKERNEL_F03_PTRACE_KFREE_PROFILE_119_EXPERIMENTAL' not in m
assert 'crate::mem_helpers::kfree_tracked' in k
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
print(json.dumps({'status':'PASS_SOURCE_BOUNDARY_ONLY','do_mmap_call_count':3,'set_host_vma_source_lines':call_lines,'kfree_pair_selected_in_composite':False,'source_hashes':{str(f):sha(f) for f in (c,r,policy,kfree,cmake)}},indent=2))
