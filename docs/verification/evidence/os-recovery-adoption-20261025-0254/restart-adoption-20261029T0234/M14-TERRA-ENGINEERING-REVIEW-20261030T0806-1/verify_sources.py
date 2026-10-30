#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json
from pathlib import Path
base=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
p=base/'sdk21-nonheld13-data32-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json'
def h(x): return hashlib.sha256(x.read_bytes()).hexdigest()
assert h(p)=='e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3'
d=json.loads(p.read_bytes()); mounts={x['container']:Path(x['host']) for x in d['readonly_shared_inputs']}
rust=mounts['/src/kernel/rust']; arch=mounts['/src/arch/x86_64/kernel/syscall.c']; gen=mounts['/src/kernel/syscall.c']; cm=mounts['/src/kernel/CMakeLists.txt']
assert h(cm)==h(Path('preimage/CMakeLists.txt'))=='812d1e5e016b9cde8fa71c211be93efdc5bfb49dd6b3685cded47d595f27dcf5'
cmnew=Path('postimage/CMakeLists.txt').read_text(); a=arch.read_text(); g=gen.read_text(); lib=(rust/'lib.rs').read_text(); policy=(rust/'syscall_policy.rs').read_text()
sel=d['selectors']
for flag in sel['new_arch_C_flags']:
 k=flag.removeprefix('-D'); assert k in cmnew and k in a,k
for flag in sel['new_generic_C_flags']:
 k=flag.removeprefix('-D'); assert k in cmnew and k in g,k
for cfg in sel['new_rust_cfg']:
 assert cfg in cmnew and (cfg in lib or cfg in policy),cfg
for cfg in sel['overlapping_rust_cfgs_absent']:
 assert cfg not in cmnew,cfg
assert 'f06_signal_log_budget.rs' in cmnew and 'f06_debug_constants.rs' in cmnew
files=[cm,arch,gen]+[rust/x for x in ('lib.rs','syscall_policy.rs','f06_debug_constants.rs','f06_signal_log_budget.rs','f03_perf_entry_candidate.rs','f03_signal_forward_defined_candidate.rs','f03_request_constructors.rs')]
print('PASS exact profile/preimage, paired new selectors and retained exclusion/source dependencies')
for x in files: print(h(x),x)
