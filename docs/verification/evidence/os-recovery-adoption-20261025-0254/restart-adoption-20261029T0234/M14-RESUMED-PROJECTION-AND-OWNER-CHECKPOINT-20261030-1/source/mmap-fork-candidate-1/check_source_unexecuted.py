#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Static regression assertions only; not run by implementation worker.
from pathlib import Path
p=Path(__file__).resolve().parent
m=(p/'do_mmap/do_mmap-continuous.PRIVATE.rs.inc').read_text()
f=(p/'do_fork/do_fork-lifetime.PRIVATE.rs.inc').read_text()
d=(p/'do_mmap/lock-downgrade.PRIVATE.rs.inc').read_text()
assert 'counter.store(1, Ordering::Release)' in d
assert 'preempt_enable();' not in d and 'preempt_disable();' not in d
assert m.index('write_locked = true;') < m.index('unsafe { initialize_straight(process, private_data) }')
assert 'ihk_rwspinlock_write_unlock_noirq(lock.cast())' not in m
assert 'f03_mmap_write_to_read_noirq_v1' not in m
last_unlock=m.index('ihk_rwspinlock_read_unlock_noirq(lock.cast())')
assert '(*range)' not in m[last_unlock:]
assert '(*(*old_process).ppid_parent).pid' not in f
pin=f.index('if let Err(value) = pin_child_before_graph_publication(new)')
publish=f.index('f03_clone_publish_thread_process_v1(new, old_process, new_process, flags)')
callback=f.index('(f03_fork_origins_v1.ptrace_report)(old, new, ptrace_event)')
enqueue=f.index('let child_tid = f03_clone_finish_report_enqueue_v1(')
release=f.index('crate::process_helpers::release_thread(new);',enqueue)
assert pin < publish < callback < enqueue < release
assert f[release:].split('return child_tid as CLong as CULong;',1)[0].count('(*new)')==0
assert 'fn f03_clone_finish_report_enqueue_v1' not in f
print('PASS private source ordering assertions; no compile/native qualification')
