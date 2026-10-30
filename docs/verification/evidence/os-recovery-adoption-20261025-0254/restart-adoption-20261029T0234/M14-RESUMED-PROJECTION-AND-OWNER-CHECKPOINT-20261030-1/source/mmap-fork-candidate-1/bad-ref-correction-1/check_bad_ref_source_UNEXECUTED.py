#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'do_fork-quarantine.PRIVATE.rs.inc').read_text()
start=s.index('if let Err(value) = pin_child_before_graph_publication(new)')
end=s.index('// The new pin keeps child/VM/process storage',start)
branch=s[start:end]
assert 'quarantine.retain_unknown(unknown);' in branch
assert 'return -super::EBUSY as CLong as CULong;' in branch
for forbidden in ["break 'prepared",'release_thread','release_cpuid','f03_clone_destroy','f03_clone_release','atomic_set']:
    assert forbidden not in branch,forbidden
assert s.index('PendingCloneQuarantine::reserve(flags & CLONE_VM != 0)') < s.index('let cpu = if helper')
assert s.index('let mut unknown = UnknownCloneRecord') < start
assert 'f03_do_fork_Rust_ABI_v1: [CULong; 46]' in s
c=(p/'REAL-HEADER-ABI-AND-ALLOCATED-CONSUMER.PRIVATE.c.inc').read_text()
assert 'f03_do_fork_C_ABI_v1[46]' in c
assert 'Process, update_lock' in s and 'Thread, refcount' in s and 'IhkAtomic, counter' in s
print('PASS static bad-ref quarantine branch/paired ABI checks; no runtime acceptance')
