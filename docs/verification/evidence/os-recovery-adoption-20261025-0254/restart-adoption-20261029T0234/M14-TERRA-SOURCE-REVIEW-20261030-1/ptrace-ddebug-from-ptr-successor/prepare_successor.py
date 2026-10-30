from pathlib import Path
base=Path.cwd()
old='ptrace-ddebug-atomic-candidate-terra-20261030-1'
new='ptrace-ddebug-from-ptr-successor-terra-20261030-1'
p=base/'postimage/kernel/rust/syscall_ptrace_wakeup_logger.rs'
s=p.read_text().replace('use core::ptr::addr_of;', 'use core::ptr::{addr_of, addr_of_mut};')
s=s.replace('    assert!(size_of::<AtomicDdebug>() == 32);\n    assert!(align_of::<AtomicDdebug>() == 8);\n    assert!(offset_of!(AtomicDdebug, line_flags) == 24);', '    assert!(align_of::<Ddebug>() >= align_of::<AtomicU32>());\n    assert!(offset_of!(Ddebug, line_flags) % align_of::<AtomicU32>() == 0);')
start=s.index('#[repr(C, align(8))]\nstruct AtomicDdebug')
end=s.index('#[used]',start)
s=s[:start]+s[end:]
s=s.replace('static mut WAKEUP_DEBUG: AtomicDdebug = AtomicDdebug {','static mut WAKEUP_DEBUG: Ddebug = Ddebug {')
s=s.replace('line_flags: AtomicU32::new(24429 | (INITIAL_FLAGS << 24)),','line_flags: 24429 | (INITIAL_FLAGS << 24),')
s=s.replace('&*addr_of!(WAKEUP_DEBUG.line_flags)','AtomicU32::from_ptr(addr_of_mut!(WAKEUP_DEBUG.line_flags))')
s=s.replace('// The registry uses only raw pointer identity and never reads the packed word\n// non-atomically for this descriptor. All fields have static image lifetime.','// The registry must route this exact descriptor to atomic accesses; ordinary\n// reads/writes of its packed word are forbidden while concurrent. Static\n// initialization precedes execution; the aligned object has image lifetime.')
p.write_text(s)
for rel in ['atomic_access_test.rs','sysfs-body-tests-1/sysfs_test.rs']:
 p=base/rel; t=p.read_text(); assert old in t; p.write_text(t.replace(old,new))
