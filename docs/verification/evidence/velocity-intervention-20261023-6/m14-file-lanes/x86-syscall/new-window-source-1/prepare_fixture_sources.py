from pathlib import Path
import hashlib,json
D=Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/new-window-source-1')
S=D/'fixture-source';S.mkdir(exist_ok=True)
for name,path in [('abi.rs','kernel/rust/abi.rs')]:
 (S/name).write_bytes(Path(path).read_bytes())
s=Path('kernel/rust/string.rs').read_text();a=s.index('#[no_mangle]\npub unsafe extern "C" fn __inline_memset(');b=s.index('\n}\n',a)+3
(S/'string.rs').write_text('use core::ffi::c_void;\nuse core::ptr::write_volatile;\nuse crate::abi::{CULong,SizeT};\n'+s[a:b])
s=Path('kernel/rust/debug.rs').read_text();a=s.index('#[repr(C)]\npub struct Ddebug');b=s.index('\n}\n',a)+3
(S/'debug.rs').write_text(s[a:b])
(S/'wakeup.FRAGMENT.rs').write_bytes((D/'candidate/do_kill_wakeup.FRAGMENT.rs').read_bytes())
(S/'original-wakeup.ACTUAL.inc').write_bytes((D/'reference/original-wakeup.ACTUAL.inc').read_bytes())
